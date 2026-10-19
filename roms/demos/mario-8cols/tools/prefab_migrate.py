#!/usr/bin/env python3
"""prefab_migrate.py — перенос карты из прямоугольников в экземпляры префабов.

Вход:  assets/objects.json (v1: список rect'ов {t,x,y,w,h}) + assets/prefabs.json.
Выход: assets/objects.json (v2: список экземпляров {pf,x,y[,w][,h]}) и
       дополненный assets/prefabs.json (узнанные узоры + «Тайл N» в «одиночных»).

Как узнаём префабы:

  1. Эталон — развёрнутая старая карта (gen_assets.expand_objects). Новый список
     обязан развернуться в НЕЁ байт-в-байт, поэтому качество распознавания
     влияет только на размер ROM, но не на картинку.
  2. Ручная библиотека (монета, кирпич, ?-блок, перегородка, облака, куст,
     площадка, трубы, земля/стена).
  3. Автоматические узоры: каждую строку (и каждый столбец) карты режем на
     максимальные прогоны непустых клеток и ищем ВНУТРИ прогона периодическое
     окно `левый край + период×k + правый край`. Из окна строится тянущийся
     префаб, а соседние ряды с тем же окном сливаются в полосу. Так из рельефа
     сами собой получаются «холм 38·41·47», «шахматка земли 4/8», «колонна 51».
  4. Скан по якорям (сначала колонки, затем строки): для каждого якоря
     перебираем подходящие префабы, тянущиеся расчитываем на все правдоподобные
     размеры. Нули паттерна ничего не пишут, а непустые клетки требуют
     свободной карты: старая карта — разбиение, поэтому наложение всегда дороже.
  5. Проходов два: «по клеткам» (берёт наибольшее совпадение) и «по байтам»
     (берёт то, что уменьшает образ: сравнение с ценой тех же rect'ов
     поодиночке, 4 Б + доля варианта). Победитель — кто дал меньше байт.
  6. Остатки — прямоугольники одного тайла (тот же cover_rectangles), каждый
     становится экземпляром авто-префаба «Тайл N» (1×1, тянется по обеим осям).
  7. Экономия честная: вариант платится один раз (3 Б + 5 Б на прямоугольник),
     экземпляр — 4 Б. Варианты, которые выходят дороже одиночных rect'ов,
     распускаем в остатки и сравниваем итоговые байты (см. dissolve).

Сверка: экземпляры обязаны развернуться в эталон байт-в-байт (она же —
картинка), лимиты формата проверяются до записи.

  python3 tools/prefab_migrate.py              # отчёт, файлы не трогаем
  python3 tools/prefab_migrate.py --debug      # + узнанные узоры и варианты
  python3 tools/prefab_migrate.py --out-objects OUT.json --out-prefabs PF.json \
          --apply                              # запись в OUT/PF (проверка)
  python3 tools/prefab_migrate.py --apply --force   # запись в assets/ (этап 4)
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prefablib as P                                      # noqa: E402
import gen_assets as G                                     # noqa: E402
from objects_from_grid import cover_rectangles             # noqa: E402

# ---- Параметры распознавания ------------------------------------------------
MAX_EDGE = 3          # сколько колонок слева/справа прогона считаем краем окна
MAX_PERIOD = 6        # максимальный период повторяющегося окна
MIN_REPEAT = 2        # середина прогона должна вмещать окно больше одного раза
MAX_GROW_W = 96       # потолок выращивания (карта 320 колонок)
MAX_GROW_H = 32
MAX_SIZES = 12        # сколько размеров перебирать для «оконного» префаба
MAX_ROUNDS = 6        # раундов роспуска невыгодных вариантов

# Секции ручной библиотеки (в старом JSON поля section нет).
SECTION_BY_NAME = {
    "Монетка": "блоки", "Кубик «?»": "блоки", "Кирпич": "блоки",
    "Перегородка": "блоки", "Площадка зелёная": "блоки",
    "Земля (тянется)": "рельеф", "Стена (тянется)": "рельеф",
    "Облачко с лицом": "декор", "Облако 1 бугор": "декор",
    "Облако 2 бугра": "декор", "Облако 3 бугра": "декор",
    "Облако (тянется)": "декор", "Куст (тянется)": "декор",
    "Труба вверх": "декор", "Труба вниз": "декор",
}

MAPS = {}               # (id кандидата, w, h) -> (row_idx, col_idx) движка stretch


# ---------------------------------------------------------------------------
# Эталонная карта
# ---------------------------------------------------------------------------

class Ref:
    """Развёрнутая rect'ами карта: доступ (x,y) -> тайл, вне карты = 0."""

    def __init__(self, cols, rows, grid):
        self.cols, self.rows, self.g = cols, rows, grid

    def at(self, x, y):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            return self.g[x * self.rows + y]
        return 0


# ---------------------------------------------------------------------------
# Кандидаты
# ---------------------------------------------------------------------------

class Cand:
    """Претендент на роль объекта: префаб + смещение его «якорной» клетки."""

    def __init__(self, pf, source, reuse=1):
        self.pf = pf
        self.name = pf["name"]
        self.source = source             # "библиотека" | "узор" | "одиночные"
        self.reuse = reuse               # сколько полос карты дали этот узор
        self.pat = tuple(tuple(row) for row in pf["grid"])
        self.pw, self.ph = len(self.pat[0]), len(self.pat)
        self.sx, self.sy = pf.get("stretch_x"), pf.get("stretch_y")
        self.dr = self.dc = self.t0 = 0      # первая непустая клетка паттерна
        for r in range(self.ph):
            for c in range(self.pw):
                if self.pat[r][c]:
                    self.dr, self.dc, self.t0 = r, c, self.pat[r][c]
                    break
            if self.t0:
                break
        self.native = P.stamp_size(pf, self.pw, self.ph)
        self._rc = {}

    def rects(self, w, h):
        """Разложение штампа (w,h) на прямоугольники — кэш по размеру."""
        key = (w, h)
        if key not in self._rc:
            self._rc[key] = [{"t": o["t"], "w": o["w"], "h": o["h"]}
                             for o in P.stamp_objects(self.pf, 0, 0, w, h)]
        return self._rc[key]

    def maps(self, w, h):
        """Индексы строк/столбцов паттерна для размера (w,h) — как stamp_cells.

        Кэш по (w,h), а не по имени: у автоузоров имена говорящие и могут
        повторяться («Узор 68·69·70…» для разных полос), путать их нельзя.
        """
        key = (w, h)
        m = MAPS.get((id(self), key))
        if m is None:
            m = (P.stretch_axis(self.ph, self.sy, h),
                 P.stretch_axis(self.pw, self.sx, w))
            MAPS[(id(self), key)] = m
        return m

    def cell(self, w, h, c, r):
        ri, ci = self.maps(w, h)
        return self.pat[ri[r]][ci[c]]

    def __repr__(self):
        return "%-20s %d×%d sx=%-9s sy=%-6s rect=%d reuse=%d [%s]" % (
            self.name, self.pw, self.ph, str(self.sx), str(self.sy),
            len(self.rects(*self.native)), self.reuse, self.source)


def stable(spec):
    """Префикс-устойчивая ось: размер L использует те же индексы, что и L+1.

    None (не тянется) и "all" — устойчивы: прирост ширины добавляет колонку и не
    трогает прежние. 9-slice (int k) и окно [a,b] — нет: хвост уезжает вправо,
    поэтому для них нельзя «расти с нативного размера», надо перебирать
    правдоподобные размеры (см. widths/heights).
    """
    return spec is None or spec == "all"


def fundamental(seq):
    """Прогон -> (a, p, c): левый край a, период окна p, правый край c.

    Окно a..a+p-1 замощает середину прогона (stretch_axis с [a,b] делает ровно
    это), крайние a и c колонок остаются как нарисованы. Ищем самое узкое
    окно — оно и есть префаб, а весь прогон становится одним экземпляром.
    Требование p < len(середины) отсекает «мнимую» периодичность, где окном
    объявлена вся середина (иначе любой набор трёх тайлов «тянулся» бы).
    """
    n = len(seq)
    best = None
    for a in range(min(n, MAX_EDGE) + 1):
        for c in range(min(n - a, MAX_EDGE) + 1):
            mid = seq[a:n - c]
            if len(mid) < MIN_REPEAT:
                continue
            for p in range(1, min(len(mid), MAX_PERIOD)):
                if all(mid[i] == mid[i % p] for i in range(len(mid))):
                    if best is None or (a + p + c) < sum(best):
                        best = (a, p, c)
                    break
    return best


def slice_row(seq, dec):
    """Прогон -> нативный ряд паттерна: левый край + одно окно + правый край."""
    if dec is None:
        return list(seq)
    a, p, c = dec
    n = len(seq)
    return list(seq[:a]) + list(seq[a:a + p]) + (list(seq[n - c:]) if c else [])


def bands_along(ref, along, across, get):
    """Максимальные прогоны вдоль оси, сливаемые в полосы одинаковой структуры.

    -> [(i0, j0, [seq, ...], dec)]: i0 — старт прогона, j0 — первый ряд полосы,
    seq — прогоны соседних рядов, dec — окно повтора (или None для фиксированного
    ряда). Ряды сливаем только при одинаковых i0, длине и окне: так две строки
    холма (38·41…47 и 39·42…48) становятся одним двухстрочным префабом.
    """
    runs = defaultdict(list)
    for j in range(across):
        i = 0
        while i < along:
            if not get(ref, i, j):
                i += 1
                continue
            i0 = i
            seq = []
            while i < along and get(ref, i, j):
                seq.append(get(ref, i, j))
                i += 1
            runs[(i0, len(seq), fundamental(seq))].append((j, seq))
    out = []
    for (i0, ln, dec), lst in runs.items():
        lst.sort()
        cur = None
        for j, seq in lst:
            if cur is not None and cur[1] + len(cur[2]) == j and len(seq) == ln:
                cur[2].append(seq)              # полоса продолжается
            else:
                cur = [i0, j, [seq], dec]
                out.append(cur)
    return out


def vperiod(rows):
    """Период набора строк: q < len(rows), иначе None."""
    n = len(rows)
    for q in range(1, n):
        if all(rows[i] == rows[i % q] for i in range(n)):
            return q
    return None


def mine(ref):
    """Автоузоры карты -> кандидаты (полосы вдоль строк и вдоль столбцов)."""
    found = []
    for axis in ("h", "v"):
        get = ((lambda r, i, j: r.at(i, j)) if axis == "h"
               else (lambda r, i, j: r.at(j, i)))
        bands = bands_along(ref, ref.cols if axis == "h" else ref.rows,
                            ref.rows if axis == "h" else ref.cols, get)
        for i0, j0, rows, dec in bands:
            pat = [slice_row(seq, dec) for seq in rows]
            along_spec = None
            if dec is not None:
                a, p, c = dec
                along_spec = "all" if (a == 0 and c == 0) else [a, a + p - 1]
            cross_spec = None
            q = vperiod(pat)
            if q:
                pat = pat[:q]
                cross_spec = "all"
            if axis == "v":                 # прогон был вдоль Y -> stretch_y
                pat = [list(col) for col in zip(*pat)]
                pf = {"grid": pat, "stretch_x": cross_spec,
                      "stretch_y": along_spec}
            else:
                pf = {"grid": pat, "stretch_x": along_spec,
                      "stretch_y": cross_spec}
            if len(pat) == 1 and len(pat[0]) == 1:
                continue                    # одиночный тайл — дело остатков
            if len(pat) > MAX_GROW_H or len(pat[0]) > MAX_GROW_W:
                continue
            pf["section"] = "рельеф"
            pf["min_w"] = len(pat[0])
            pf["min_h"] = len(pat)
            found.append(pf)
    by = {}
    for pf in found:
        key = (tuple(tuple(r) for r in pf["grid"]), str(pf["stretch_x"]),
               str(pf["stretch_y"]))
        e = by.setdefault(key, [pf, 0])
        e[1] += 1
    out = []
    for pf, reuse in by.values():
        tiles = sorted({t for row in pf["grid"] for t in row if t})
        pf["name"] = "Узор " + "·".join(str(t) for t in tiles[:3])
        if len(tiles) > 3:
            pf["name"] += "+%d" % (len(tiles) - 3)
        out.append(Cand(pf, "узор", reuse))
    return out


def unique_names(cands):
    """Имя префаба — ключ экземпляра, дубликаты недопустимы.

    Молча подставляем счётчик: «Узор 4·8», «Узор 4·8 2». Меняем и Cand.name, и
    pf["name"]: по имени ищут префаб build_variants/expand_instances.
    """
    seen = set()
    for cd in cands:
        base = cd.name
        k = 1
        while cd.name in seen:
            k += 1
            cd.name = cd.pf["name"] = "%s %d" % (base, k)
        seen.add(cd.name)
    return cands


def load_library(path=P.PREFAB_FILE):
    """Ручная библиотека -> кандидаты (+ секции, которых в старом JSON нет)."""
    out = []
    for pf in P.load_prefabs(path):
        pf.setdefault("section", SECTION_BY_NAME.get(pf["name"], "декор"))
        out.append(Cand(pf, "библиотека"))
    return out


def singles_for(ref):
    """Авто-префабы «Тайл N» по всем тайлам карты (тянутся по обеим осям)."""
    return [Cand(P.single_tile_stretchable(t), "одиночные")
            for t in sorted({v for v in ref.g if v})]


# ---------------------------------------------------------------------------
# Скан: якорь -> лучший кандидат
# ---------------------------------------------------------------------------

class Scan:
    """Жадное распознавание: состояние покрытия + список экземпляров.

    Режим "cells" (проход A) схлопывает карту максимально, чтобы узнать, как
    часто встречается каждый размер варианта. Режим "gain" (проход B) берёт
    только то сворачивание, которое реально уменьшает образ: сравнение идёт не с
    v1 (5 Б на rect), а со «стратегией B» — unmatched rect'ы всё равно станут
    экземплярами «Тайл t», а их вариант оплатится один на всех.
    """

    def __init__(self, ref, cands, base, mode="cells", amort=None):
        self.ref = ref
        self.base = base
        self.mode = mode
        self.amort = amort or {}
        self.covered = bytearray(ref.cols * ref.rows)
        self.inst = []
        self.groups = defaultdict(lambda: defaultdict(list))
        for cd in cands:
            # якорь привязан к ПЕРВОЙ непустой клетке паттерна: у облака верхний
            # левый угол — небо, и по «тайлу якоря» его было бы не найти
            self.groups[(cd.dr, cd.dc)][cd.t0].append(cd)

    def match(self, cd, w, h, x, y):
        """Штамп ложится в (x,y): непустые клетки равны эталону и ещё не заняты.

        Нули паттерна не смотрим вовсе (это небо). Требование «клетки свободны»
        безопасно: старая карта — разбиение, rect'ы в ней не перекрываются,
        поэтому решение без наложений всегда не дороже решения с наложениями.
        """
        ref = self.ref
        if x < 0 or y < 0 or x + w > ref.cols or y + h > ref.rows:
            return False
        rows = ref.rows
        ri, ci = cd.maps(w, h)
        for r in range(h):
            for c in range(w):
                t = cd.pat[ri[r]][ci[c]]
                if t and (t != ref.at(x + c, y + r) or
                          self.covered[(x + c) * rows + y + r]):
                    return False
        return True

    def widths(self, cd, x, y, h):
        """Правдоподобные ширины в (x,y) при данной высоте, по убыванию."""
        ref = self.ref
        cap = min(MAX_GROW_W, ref.cols - x, P.MAX_COLS)
        lo = cd.native[0]
        if cap < lo:
            return []
        if cd.sx is None:
            return [lo]                       # ось не тянется: размер один
        if cd.sx == "all":
            w = lo
            while w + 1 <= cap and self.match(cd, w + 1, h, x, y):
                w += 1
            return [w]
        # «оконный»/9-slice префаб: хвост уезжает с шириной, поэтому рост от
        # нативного размера неверен — перебираем ширины, у которых ПРАВАЯ
        # колонка штампа совпадает с картой (это уже почти единственный кандидат)
        out = []
        for w in range(cap, lo - 1, -1):
            ri, ci = cd.maps(w, h)
            last = ci[w - 1]
            if all((t := cd.pat[ri[r]][last]) == 0 or t == ref.at(x + w - 1,
                                                                  y + r)
                   for r in range(h)):
                out.append(w)
                if len(out) >= MAX_SIZES:
                    break
        return out

    def heights(self, cd, x, y, w):
        """Правдоподобные высоты в (x,y) при данной ширине, по убыванию."""
        ref = self.ref
        cap = min(MAX_GROW_H, ref.rows - y, P.MAX_ROWS)
        lo = cd.native[1]
        if cap < lo:
            return []
        if cd.sy is None:
            return [lo]
        if cd.sy == "all":
            h = lo
            while h + 1 <= cap and self.match(cd, w, h + 1, x, y):
                h += 1
            return [h]
        out = []
        for h in range(cap, lo - 1, -1):
            ri, ci = cd.maps(w, h)
            last = ri[h - 1]
            if all((t := cd.pat[last][ci[c]]) == 0 or t == ref.at(x + c,
                                                                  y + h - 1)
                   for c in range(w)):
                out.append(h)
                if len(out) >= MAX_SIZES:
                    break
        return out

    def fit(self, cd, x, y):
        """Наибольшая (w,h), целиком совпавшая с картой, или None."""
        if stable(cd.sx) and stable(cd.sy):
            # обе оси индексно-устойчивы: жадный рост по (+1,0),(0,+1),(+1,+1)
            w, h = cd.native
            if not self.match(cd, w, h, x, y):
                return None
            while True:
                nxt = None
                for dw, dh in ((1, 0), (0, 1), (1, 1)):
                    if (dw and cd.sx is None) or (dh and cd.sy is None):
                        continue
                    if self.match(cd, w + dw, h + dh, x, y):
                        nxt = (w + dw, h + dh)
                        break
                if nxt is None:
                    return (w, h)
                w, h = nxt
        for w in self.widths(cd, x, y, cd.ph):
            for h in self.heights(cd, x, y, w):
                if self.match(cd, w, h, x, y):
                    return (w, h)
        return None

    def mark(self, cd, w, h, x, y):
        rows = self.ref.rows
        ri, ci = cd.maps(w, h)
        for r in range(h):
            for c in range(w):
                if cd.pat[ri[r]][ci[c]]:
                    self.covered[(x + c) * rows + y + r] = 1

    def place(self, cd, x, y, w, h):
        """Экземпляр в список (порядок вставки = z-order) + пометка покрытия."""
        inst = {"pf": cd.name, "x": x, "y": y}
        if w != cd.native[0]:
            inst["w"] = w
        if h != cd.native[1]:
            inst["h"] = h
        self.mark(cd, w, h, x, y)
        self.inst.append(inst)

    def score(self, cd, w, h):
        """Пригодность установки (чем больше, тем лучше) или None, если ставить
        невыгодно."""
        rects = cd.rects(w, h)
        cells = sum(o["w"] * o["h"] for o in rects)
        if self.mode == "cells":
            return (cells, cd.source == "библиотека", w * h, -len(rects))
        n = max(1, self.amort.get((cd.name, w, h), 1))
        gain = collapse_gain(rects, n, self.base)
        if gain <= 0:
            return None
        return (gain, cd.source == "библиотека", cells, -len(rects))

    def best_at(self, x, y):
        """Лучший кандидат, чья первая непустая клетка — это (x,y)."""
        t0 = self.ref.at(x, y)
        if not t0 or self.covered[x * self.ref.rows + y]:
            return None
        best = None
        for (dr, dc), byt in self.groups.items():
            ax, ay = x - dc, y - dr
            for cd in byt.get(t0, ()):
                wh = self.fit(cd, ax, ay)
                if wh is None:
                    continue
                sc = self.score(cd, wh[0], wh[1])
                if sc is None or (best is not None and sc <= best[0]):
                    continue
                best = (sc, cd, ax, ay, wh[0], wh[1])
        return best

    def run(self):
        """Обход по колонкам, затем строкам: порядок обхода = порядок списка."""
        for x in range(self.ref.cols):
            for y in range(self.ref.rows):
                b = self.best_at(x, y)
                if b:
                    _, cd, ax, ay, w, h = b
                    self.place(cd, ax, ay, w, h)
        return self.inst


# ---------------------------------------------------------------------------
# Экономика: остатки и роспуск невыгодных вариантов
# ---------------------------------------------------------------------------

def covered_from(ref, by_name, instances):
    """Карта покрытия (1 = клетку закрыл экземпляр) в порядке списка."""
    cov = bytearray(ref.cols * ref.rows)
    for inst in instances:
        cd = by_name[inst["pf"]]
        w, h = P.instance_size(cd.pf, inst)
        ri, ci = cd.maps(w, h)
        x, y = int(inst["x"]), int(inst["y"])
        for r in range(h):
            for c in range(w):
                if cd.pat[ri[r]][ci[c]]:
                    cov[(x + c) * ref.rows + y + r] = 1
    return cov


def leftover_instances(ref, cov, used):
    """Непокрытые непустые клетки -> экземпляры «Тайл N» прямоугольниками."""
    rest = bytearray(ref.cols * ref.rows)
    for i, t in enumerate(ref.g):
        if t and not cov[i]:
            rest[i] = t
    out = []
    for o in cover_rectangles(ref.cols, ref.rows, rest):
        used.add(o["t"])
        inst = {"pf": "Тайл %d" % o["t"], "x": o["x"], "y": o["y"]}
        if o["w"] != 1:
            inst["w"] = o["w"]
        if o["h"] != 1:
            inst["h"] = o["h"]
        out.append(inst)
    return out


def strategy_b(objects, hist):
    """Смета «не сворачивать ничего»: каждый rect v1 -> экземпляр «Тайл t».

    Это потолок расходов без свёрток: карта станет легче v1 ровно на столько,
    на сколько свёртки композитов и прогонов дают больший выигрыш, чем стоит
    одиночный экземпляр.
    """
    return (P.INST_BYTES * len(objects)
            + (P.VAR_BYTES + P.RECT_BYTES) * len(hist))


def rect_hist(objects):
    """Частота размеров rect'ов старой карты — для сметы «не сворачивать ничего»."""
    return Counter((o["t"], o["w"], o["h"]) for o in objects)


class Base:
    """Оценка «сколько стоило бы не сворачивать» по старой карте.

    Несвёрнутый rect остаётся ровно тем, чем был, но в новых байтах: 4 Б на
    экземпляр плюс (3+5) Б варианта, делённые на число rect'ов такого размера.

    Знаменатель — число rect'ов этого ТАЙЛА во всей карте, а не числа rect'ов
    ровно такого размера: после роспуска соседние клетки того же тайла сливаются
    в один rect, и оценивать несуществующий размер как «12 Б за одиночку» —
    подарок, из-за которого соглашаешься на свёртку, которая дороже.
    """

    def __init__(self, objects):
        self.size = rect_hist(objects)
        self.tile = Counter(o["t"] for o in objects)

    def cost(self, o):
        return P.INST_BYTES + (P.VAR_BYTES + P.RECT_BYTES) / \
            max(1, self.tile[o["t"]])


def collapse_gain(rects, n, base):
    """Экономия в байтах от свёртки набора rect'ов в n экземпляров одного варианта."""
    return (sum(base.cost(o) for o in rects) * n
            - (P.INST_BYTES * n + P.VAR_BYTES + P.RECT_BYTES * len(rects)))


def too_expensive(v, base):
    """Свёртка варианта дороже, чем его rect'ы поодиночке?

    Ориентир — не v1 (5 Б на rect), а «стратегия B»: каждый rect всё равно
    станет экземпляром «Тайл t» своего размера, поэтому сравнение честное только
    по новым байтам. Шахматка земли (rect на каждую клетку, длина встречи
    уникальна) проигрывает, кирпич (4 rect'а на 18 экземпляров) выигрывает.
    """
    return collapse_gain(v["rects"], v["n"], base) < 0


def bad_variants(variants, base):
    """Ключи (имя,w,h) убыточных вариантов, которые надо распустить в остатки.

    Одно-rect'ные варианты не трогаем: распустить их — это те же самые rect'ы,
    то же покрытие и те же байты, только лишняя работа.
    """
    return {(v["name"], v["w"], v["h"]) for v in variants
            if len(v["rects"]) > 1 and too_expensive(v, base)}


def finalize(ref, by_name, pool, instances, left):
    """Додать остатки и посчитать (экземпляры, покрытие, варианты, байты).

    `left` — сюда дописываются тайлы, из которых собраны остатки (для отчёта).
    """
    cov = covered_from(ref, by_name, instances)
    full = instances + leftover_instances(ref, cov, left)
    variants, _ = P.build_variants(pool, full)
    return full, cov, variants, P.level_bytes(full, variants)


def dissolve(ref, by_name, pool, base, inst, trace=None):
    """Распускать убыточные варианты, пока карта не начнёт тяжелеть."""
    left = set()
    best = None
    for _ in range(MAX_ROUNDS):
        full, cov, variants, nbytes = finalize(ref, by_name, pool, inst, left)
        if best is None or nbytes < best[3]:
            best = (full, cov, variants, nbytes, inst)
        bad = bad_variants(variants, base)
        if not bad:
            break
        keep = [i for i in inst
                if (i["pf"],) + P.instance_size(by_name[i["pf"]].pf, i)
                not in bad]
        if len(keep) == len(inst):
            break
        f2, c2, v2, n2 = finalize(ref, by_name, pool, keep, set(left))
        if n2 >= nbytes:
            break
        if trace is not None:
            trace.extend(sorted("%s %dx%d" % z for z in bad))
        inst = keep
    return best + (left,)


def solve(ref, base, cands, trace=None):
    """Два жадных прохода скана и роспуск невыгодного; выбираем дешёвый.

    Критерий «сколько клеток добавляет установка» и критерий «сколько байтов
    экономит» выбирают разные свёртки, а честный арбитр — только пересчитанные
    байты образа, поэтому прогоняем оба и берём меньший. Первый проход заодно
    даёт амортизации для второго: как часто встречается каждый размер варианта.
    """
    by_name = {cd.name: cd for cd in cands}
    pool = [cd.pf for cd in cands]
    # «Тайл N» в скан не идут: их работа — остатки (тот же rect = тот же
    # экземпляр), но в словаре префабов они нужны
    scan_cands = [cd for cd in cands if cd.source != "одиночные"]
    cells = Scan(ref, scan_cands, base).run()
    amort = Counter((i["pf"],) + P.instance_size(by_name[i["pf"]].pf, i)
                    for i in cells)
    gain = Scan(ref, scan_cands, base, mode="gain", amort=amort).run()
    tried = []
    for name, inst in (("клетки", cells), ("байты", gain)):
        t2 = []
        res = dissolve(ref, by_name, pool, base, inst, t2)
        tried.append((res, len(inst), t2, name))
    (full, cov, variants, nbytes, inst, left), scanned, t2, winner = \
        min(tried, key=lambda z: z[0][3])
    if trace is not None:
        trace.extend(t2)
    return {"instances": full, "recognized": inst, "scanned": scanned,
            "covered": cov, "variants": variants, "bytes": nbytes,
            "leftover_tiles": left, "by_name": by_name, "pool": pool,
            "amort": amort, "base": base,
            "passes": [(nm, n, r[3]) for r, n, _, nm in tried],
            "winner": winner}


# ---------------------------------------------------------------------------
# Отчёт
# ---------------------------------------------------------------------------

def report(ref, res, objects, counts, bad, debug):
    cells = sum(1 for v in ref.g if v)
    hist = res["base"].size
    n_rects = len(objects)
    old = P.OBJ_BYTES * n_rects
    inst = res["instances"]
    variants = res["variants"]
    n_rect_var = sum(len(v["rects"]) for v in variants)
    base_b = strategy_b(objects, hist)
    print("карта: %d×%d, rect'ов v1: %d, непустых клеток: %d"
          % (ref.cols, ref.rows, n_rects, cells))
    print("распознано: %d экземпляров после скана, %d после роспуска, "
          "остатков прямоугольниками: %d (тайлов %d)"
          % (res["scanned"], len(res["recognized"]), len(inst) -
             len(res["recognized"]), len(res["leftover_tiles"])))
    print("экземпляров итого: %d, вариантов: %d, rect'ов в словаре: %d"
          % (len(inst), len(variants), n_rect_var))
    if bad:
        print("роспущено вариантов (свёртка дороже одиночных rect'ов): %s"
              % ", ".join(bad))
    print("байты: v1 %d·%d = %d Б  ->  v2 %d·%d + %d·%d + %d·%d = %d Б (%+d Б)"
          % (P.OBJ_BYTES, n_rects, old,
             P.INST_BYTES, len(inst),
             P.VAR_BYTES, len(variants),
             P.RECT_BYTES, n_rect_var, res["bytes"], res["bytes"] - old))
    print("без свёрток вообще было бы %d Б (%+d к v1): v2 выгоден ровно на "
          "композитах и прогонах"
          % (base_b, base_b - old))
    print("проходы скана: %s — выбран «%s»"
          % (", ".join("%s: %d экз. -> %d Б" % p for p in res["passes"]),
             res["winner"]))
    if len(variants) > P.VAR_ID_LO7:
        print("id варианта: %d > %d — 7 бит байта 0 не хватает; формат несёт "
              "12 бит (7 в байте 0 + 5 в байте резерва экземпляра, лимит %d)"
              % (len(variants), P.VAR_ID_LO7, P.MAX_VARIANTS))
    print()
    print("сколько экземпляров какого префаба:")
    per = defaultdict(lambda: [0, 0, 0, 0])      # экз, вар, rect, байты
    for v in variants:
        e = per[v["name"]]
        e[0] += v["n"]
        e[1] += 1
        e[2] += len(v["rects"])
        e[3] += (P.INST_BYTES * v["n"] + P.VAR_BYTES
                 + P.RECT_BYTES * len(v["rects"]))
    for nm, e in sorted(per.items(), key=lambda z: -z[1][3]):
        print("   %-22s %4d экз.  %3d вар.  %5d rect  %6d Б"
              % (nm, e[0], e[1], e[2], e[3]))
    if debug:
        print("\nкрупнейшие варианты (по числу rect'ов):")
        for v in sorted(variants, key=lambda v: -len(v["rects"]))[:30]:
            print("   %-22s %3d×%-3d %3d экз. %3d rect"
                  % (v["name"], v["w"], v["h"], v["n"], len(v["rects"])))
    print("\nостатки: %d прямоугольников, крупнейшие: %s"
          % (counts["left_rects"],
             ", ".join("%dx%d t%d в (%d,%d)"
                       % (o["w"], o["h"], o["t"], o["x"], o["y"])
                       for o in counts["left_big"])))


def leftover_stats(ref, cov, k=5):
    rest = bytearray(ref.cols * ref.rows)
    for i, t in enumerate(ref.g):
        if t and not cov[i]:
            rest[i] = t
    rects = cover_rectangles(ref.cols, ref.rows, rest)
    return {"left_rects": len(rects),
            "left_big": sorted(rects, key=lambda o: -o["w"] * o["h"])[:k]}


def used_prefabs(cands, instances):
    """Библиотека на запись: вся ручная + только использованные узоры/одиночные."""
    used = {i["pf"] for i in instances}
    out = []
    for cd in cands:
        if cd.source == "библиотека" or cd.name in used:
            out.append(cd.pf)
    return out, [cd for cd in cands
                 if cd.source == "узор" and cd.name not in used]


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="перенос assets/objects.json v1 в список экземпляров префабов")
    ap.add_argument("--apply", action="store_true",
                    help="записать assets/objects.json и assets/prefabs.json")
    ap.add_argument("--debug", action="store_true",
                    help="печатать узнанные узоры и варианты")
    ap.add_argument("--objects", default=P.OBJECTS_FILE)
    ap.add_argument("--prefabs", default=P.PREFAB_FILE)
    ap.add_argument("--out-objects", default=None,
                    help="куда писать v2 (по умолчанию --objects)")
    ap.add_argument("--out-prefabs", default=None,
                    help="куда писать библиотеку (по умолчанию --prefabs)")
    ap.add_argument("--force", action="store_true",
                    help="разрешить запись в assets/ до этапа 4 (сборка сломается)")
    args = ap.parse_args()

    cols, rows, objects = G.load_objects()
    if objects is None:
        # assets/objects.json уже v2 (миграция выполнена) или его нет: эталон берём
        # из плоской сетки assets/level.json, а «старую смету» — из её же разбиения
        # на прямоугольники (ровно тот список, из которого когда-то вырос v1).
        lv = P.load_level()
        cols, rows = int(lv["cols"]), int(lv["rows"])
        objects = cover_rectangles(cols, rows, lv["grid"])
        print("эталон: assets/level.json (objects.json уже не v1) — %d rect'ов" %
              len(objects))
    ref = Ref(cols, rows, G.expand_objects(cols, rows, objects))

    lib = load_library(args.prefabs)
    auto = mine(ref)
    singles = singles_for(ref)
    cands = unique_names(lib + auto + singles)
    if args.debug:
        print("узнанные узоры (%d), самые переиспользуемые:" % len(auto))
        for cd in sorted(auto, key=lambda c: (-c.reuse, -c.native[0] *
                                             c.native[1]))[:30]:
            print("   %s" % cd)

    bad = []
    res = solve(ref, Base(objects), cands, bad)
    inst = res["instances"]

    # --- ворота: парити, лимиты, z-order ------------------------------------
    pool_pf = [cd.pf for cd in cands]
    new = P.expand_instances(cols, rows, pool_pf, inst)
    diffs = [(i, ref.g[i], new[i]) for i in range(cols * rows)
             if ref.g[i] != new[i]]
    errs = P.validate_instances(cols, rows, pool_pf, inst)
    blocks = P.expand_by_blocks(cols, rows, pool_pf, inst)
    zbad = sum(1 for i in range(cols * rows) if blocks[i] != new[i])

    report(ref, res, objects, leftover_stats(ref, res["covered"]), bad,
           args.debug)
    print("z-order: конфликтов блочной группировки: %d" % zbad)
    if diffs:
        print("ПАРИТИ: FAIL — %d расхождений (первые 10):" % len(diffs))
        for i, a, b in diffs[:10]:
            print("   col=%d row=%d: эталон %d != %d"
                  % (i // rows, i % rows, a, b))
    else:
        print("ПАРИТИ: PASS — экземпляры разворачиваются байт-в-байт в эталон")
    for e in errs[:10]:
        print("   ЛИМИТ: %s" % e)

    prefabs_out, dropped = used_prefabs(cands, inst)
    print("префабов на запись: %d (ручных %d, узоров %d, одиночных %d), "
          "не использовано узоров: %d"
          % (len(prefabs_out), len(lib),
             sum(1 for cd in auto if cd.name in {i["pf"] for i in inst}),
             sum(1 for pf in prefabs_out if pf.get("section") == "одиночные"),
             len(dropped)))

    if args.apply:
        if diffs or errs:
            sys.exit("ПАРИТИ/ЛИМИТЫ не прошли — ничего не пишем")
        o_path = args.out_objects or args.objects
        p_path = args.out_prefabs or args.prefabs
        if not args.force and (o_path == P.OBJECTS_FILE or
                               p_path == P.PREFAB_FILE):
            sys.exit("в assets/ объекты v2 пока нечем читать: gen_assets и main.c "
                     "переезжают на словарь вариантов этапом 4, до него сборка "
                     "сломается. Проверка — --out-objects/--out-prefabs, "
                     "запись в assets/ — с --force")
        P.save_instances(cols, rows, inst, o_path)
        P.save_prefabs(prefabs_out, p_path, comment=COMMENT)
        print("записано: %s (%d экземпляров), %s (%d префабов)"
              % (o_path, len(inst), p_path, len(prefabs_out)))
    else:
        print("(dry-run: файлы не тронуты; --apply — записать)")
    return 1 if (diffs or errs) else 0


COMMENT = [
    "Префабы (составные объекты) уровня Mario 8cols. Окно префабов —",
    "tools/prefab_editor.py, раскладка уровня — tools/level_editor.py, перенос",
    "старой карты — tools/prefab_migrate.py. Каждый префаб = паттерн тайлов",
    "(0 = пусто/небо) плюс режим растягивания: stretch_x/stretch_y = null (размер",
    "фиксирован), \"all\" (замостить циклически) или [a,b] — повторять ОКНО",
    "колонок/строк a..b, края остаются целыми. min_w/min_h — низкая граница",
    "резинки. section — группировка в палитре: рельеф / блоки / декор /",
    "одиночные (авто-префабы 1×1 по тайлам карты).",
    "assets/objects.json хранит список ЭКЗЕМПЛЯРОВ {pf,x,y[,w][,h]}; порядок списка =",
    "z-order (первый рисуется первым). При запекании окна экземпляр разворачивается",
    "в тайлы на лету — в ROM лежат словарь вариантов и список экземпляров.",
]


if __name__ == "__main__":
    sys.exit(main())
