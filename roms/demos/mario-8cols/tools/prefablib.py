#!/usr/bin/env python3
"""prefablib.py — общая библиотека префабов уровня Mario 8cols.

Здесь живёт всё, что не относится к конкретному окну: пути и лимиты сборки,
загрузка тайлов/префабов, движок растяжения (stretch) и разбивка штампа на
прямоугольники. Пользователи:

  * tools/level_editor.py  — окно уровня (ставит экземпляры префабов);
  * tools/prefab_editor.py — окно редактора префабов (рисует паттерны);
  * tools/prefab_migrate.py — перенос старой карты в экземпляры.

Чистой (без Tk/PIL) частью может пользоваться генератор и офлайн-проверки:
Image нужен только в load_tile_images(), он импортируется внутри функции.

Формат src/prefabs.json (v2):
  {"version": 2, "prefabs": [{"name", "grid", "section", "stretch_x",
                              "stretch_y", "min_w", "min_h"}, ...]}
grid — row-major сетка индексов тайлов, 0 = пусто (небо, не закрашиваем).
stretch_x / stretch_y:
  None   — ось не тянется (размер фиксирован);
  "all"  — замостить паттерн циклически (куст, чередование земли);
  int k  — 9-slice: 0..k — неизменяемая шапка, k повторяется, k+1.. — хвост;
  [a,b]  — повторять ОКНО колонок/строк a..b целиком (бугры облака),
           углы 0..a-1 и b+1.. остаются целыми.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "src"))
ROM = os.path.abspath(os.path.join(HERE, "..", "mario-8c.rom"))
MAP = os.path.abspath(os.path.join(HERE, "..", "mario-8c.map"))
LEVEL_INC = os.path.join(SRC, "level.inc")
PREFAB_FILE = os.path.join(SRC, "prefabs.json")
TILES_FILE = os.path.join(SRC, "tiles.json")
LEVEL_FILE = os.path.join(SRC, "level.json")
OBJECTS_FILE = os.path.join(SRC, "objects.json")

sys.path.insert(0, HERE)
from objects_from_grid import cover_rectangles            # noqa: E402

PREFAB_VERSION = 2

# Порядок секций в палитре префабов (неизвестная секция — в конец).
PF_SECTIONS = ("рельеф", "блоки", "декор", "одиночные")

TILE_PX = 8                  # сторона тайла в исходниках (src/tiles/*.png)
SKY = (13, 26, 43)
COLL_RED = (224, 58, 58)     # сплошной (wall)
COLL_BLUE = (58, 123, 224)   # платформа (platform)

# ---- Настоящие лимиты уровня (те же формулы, что в gen_assets.py) ----------
# Редактор обязан отсеять их ДО make: сборка падает на half-way, а перекос по
# ОЗУ вообще не ловится ничем, кроме «ROM не грузится».
MAX_COLS = 512               # x ≤ 511 (9-й бит в первом байте записи)
MAX_ROWS = 255               # y ≤ 255; tile_stride/cam_row — байт
MIN_COLS = 64                # RAM-окно tile_win = OBJ_WIN_COLS(64) колонок
MIN_ROWS = 32                # экран VIEW_ROWS = 32 строки, иначе камере тесно
TILEMAP_LIMIT = 65535        # cols*rows: 16-битная адресация тайлкарты (asm)
TILE_INDEX_LIMIT = 127       # tile: 7 бит в первом байте rect'а
MAX_VARIANTS = 4095          # id варианта: 7 бит байта 0 + 5 бит байта 3
                             # (байт 3 = резерв: старшие биты id + будущий mirror);
                             # карта требует >127 только из-за тайлов-одиночек
WIN_RAM_PER_ROW = 64         # tile_win[OBJ_WIN_COLS * LEVEL_ROWS] байт ОЗУ
OBJ_WIN_STEP = 32            # OBJ_WIN_BLOCKS = ceil(cols / step), +1 sentinel
OBJ_BYTES = 5                # старый формат: {flags,xlo,y,w,h} на прямоугольник
INST_BYTES = 4               # экземпляр: {variant|x8, xlo, y, reserved}
RECT_BYTES = 5               # прямоугольник варианта: {t,dx,dy,w,h}
VAR_BYTES = 3                # таблица варианта: ofs(u16) + n(u8)
IMAGE_LIMIT = 0x7FFF + 1 - 0x0100      # 32512: код+константы+BSS ниже VRAM


# ---------------------------------------------------------------------------
# Загрузка исходников
# ---------------------------------------------------------------------------

def defines(path=LEVEL_INC, names=("OBJ_WIN_COLS", "OBJ_WIN_STEP", "LEVEL_ROWS",
                                   "OBJ_COUNT")):
    """#define из сгенерированного level.inc — чтобы смета отталкивалась от
    ПОСЛЕДНЕЙ реальной сборки, а не от «предпоследней + догадка»."""
    try:
        with open(path) as f:
            txt = f.read()
    except OSError:
        return {}
    out = {}
    for n in names:
        m = re.search(r"#define\s+%s\s+(\d+)" % n, txt)
        if m:
            out[n] = int(m.group(1))
    return out


def load_level(path=LEVEL_FILE):
    """src/level.json (cols/rows/tile/grid) — размер карты и производная сетка."""
    if not os.path.isfile(path):
        sys.exit("Нет %s — сначала: python3 tools/export_assets.py" % path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_tiles(path=TILES_FILE):
    """src/tiles.json: список тайлов с их свойствами (wall/platform/transparent)."""
    if not os.path.isfile(path):
        sys.exit("Нет %s — сначала: python3 tools/export_assets.py" % path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tile_props(tiles=None):
    """{index: {"wall","platform","transparent"}} — для оверлея твёрдости."""
    meta = tiles if tiles is not None else load_tiles()
    out = {}
    for t in meta["tiles"]:
        out[int(t["index"])] = {"wall": bool(t.get("wall")),
                                "platform": bool(t.get("platform")),
                                "transparent": bool(t.get("transparent"))}
    return out


def load_tile_images(tiles=None, src=SRC):
    """Изображения тайлов src/tiles/*.png (index-мажорный список, нативный 8×8).

    Не масштабируем: зум — дело руки окна (редактор перерисовывает сетку под
    свой cell).
    """
    from PIL import Image                       # только тут: офлайну PIL не нужен
    meta = tiles if tiles is not None else load_tiles()
    imgs = []
    for t in meta["tiles"]:
        p = os.path.join(src, t["file"])
        imgs.append(Image.open(p).convert("RGB") if os.path.isfile(p)
                    else Image.new("RGB", (TILE_PX, TILE_PX), SKY))
    return imgs


def frame_color(tile):
    """wall приоритетнее платформы; ни того ни другого — без рамки."""
    if tile.get("wall"):
        return COLL_RED
    if tile.get("platform"):
        return COLL_BLUE
    return None


def load_prefabs(path=PREFAB_FILE, n_tiles=None):
    """src/prefabs.json -> список префабов.

    Битые/пустые паттерны и индексы вне набора тайлов выбрасываем молча:
    опечатка в JSON не должна ронять GUI на первом же превью. Файла нет —
    пустой список (окно редактора работает и без библиотеки).
    """
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if n_tiles is None:
        n_tiles = len(load_tiles()["tiles"])
    out = []
    for pf in data.get("prefabs", []):
        grid = pf.get("grid") or []
        if not grid or any(t < 0 or t >= n_tiles for row in grid for t in row):
            continue
        if len({len(row) for row in grid}) != 1:
            continue
        pf.setdefault("name", "Без имени")
        out.append(pf)
    return out


def prefab_comment(path=PREFAB_FILE):
    """Поле _comment библиотеки — чтобы окно префабов переносило его в новый
    файл, а не теряло при записи в чистый путь."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("_comment")
    except (OSError, ValueError):
        return None


def save_prefabs(prefabs, path=PREFAB_FILE, comment=None):
    """Атомарная запись библиотеки (tmp + replace), порядок ключей стабильный,
    чтобы diff не шумел от перестановки полей."""
    if comment is None and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                comment = json.load(f).get("_comment")
        except (OSError, ValueError):
            comment = None
    body = {"version": PREFAB_VERSION}
    if comment:
        body["_comment"] = comment
    keys = ("name", "section", "grid", "stretch_x", "stretch_y", "min_w", "min_h",
            "solid_hint")
    out = []
    for pf in prefabs:
        e = {k: pf[k] for k in keys if k in pf}
        out.append(e)
    body["prefabs"] = out
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def section_of(pf):
    return pf.get("section") or "декор"


def sort_key_prefabs(prefabs):
    """Порядок библиотеки: по секциям (PF_SECTIONS), внутри — как заведены."""
    idx = {s: i for i, s in enumerate(PF_SECTIONS)}
    return sorted(prefabs, key=lambda p: idx.get(section_of(p), len(idx)))


# ---------------------------------------------------------------------------
# Движок штампа: паттерн + растяжение -> сетка тайлов -> прямоугольники
# ---------------------------------------------------------------------------

def stretch_axis(n_src, spec, n_dst):
    """Индексы строк/столбцов паттерна для размера n_dst.

    spec: None      — размер фиксирован (ничего не тянем);
          "all"     — замостить циклически (куст: чередование колонок 30,32);
          int k     — 9-slice: 0..k слева/сверху, k повторяется, k+1.. справа/
                      снизу. Так тянутся тело трубы (k = строка тела: шапка
                      остаётся целой) и рамка площадки (k = средний слой);
          [a, b]    — повторять ОКНО колонок a..b целиком (облако: единичка
                      [23,26] — «бугор»; углы слева и справа остаются целыми).
    """
    n_dst = max(1, n_dst)
    if spec is None:
        return list(range(min(n_src, n_dst)))
    if spec == "all":
        return [i % n_src for i in range(n_dst)]
    if isinstance(spec, (list, tuple)):
        b = max(int(spec[0]), min(int(spec[1]), n_src - 1))
        a = max(0, min(int(spec[0]), b))
        unit = list(range(a, b + 1))
        mid = max(1, n_dst - (n_src - len(unit)))
        return (list(range(a)) + [unit[i % len(unit)] for i in range(mid)]
                + list(range(b + 1, n_src)))
    k = max(0, min(n_src - 1, int(spec)))
    return (list(range(k + 1)) + [k] * max(0, n_dst - n_src)
            + list(range(k + 1, n_src)))


def stamp_size(pf, w, h):
    """Желаемый размер штампа -> допустимый (тянутся только оси со stretch)."""
    pat = pf["grid"]
    ph, pw = len(pat), len(pat[0])
    if pf.get("stretch_x") is None:
        w = pw
    else:
        w = max(int(pf.get("min_w", pw)), w)
    if pf.get("stretch_y") is None:
        h = ph
    else:
        h = max(int(pf.get("min_h", ph)), h)
    return min(w, MAX_COLS), min(h, MAX_ROWS)


def stamp_cells(pf, w, h):
    """Штамп + размер -> row-major сетка тайлов (0 = пропуск, небо)."""
    pat = pf["grid"]
    ph, pw = len(pat), len(pat[0])
    w, h = stamp_size(pf, w, h)
    rows = stretch_axis(ph, pf.get("stretch_y"), h)
    cols = stretch_axis(pw, pf.get("stretch_x"), w)
    return [[pat[r][c] for c in cols] for r in rows]


def stamp_objects(pf, x, y, w, h, gid=None):
    """Штамп в точке (x,y) -> список прямоугольников {t,x,y,w,h}.

    Разбивка — та же cover_rectangles(), что строит карту из тайл-grid'а,
    поэтому набор прямоугольников идентичен ручной обводке тех же тайлов.
    gid (поле g) — только для редактора, генератор его не смотрит.
    """
    cells = stamp_cells(pf, w, h)
    sw, sh = len(cells[0]), len(cells)
    grid = [0] * (sw * sh)                            # col-major: grid[c*sh + r]
    for r in range(sh):
        for c in range(sw):
            grid[c * sh + r] = cells[r][c]
    out = []
    for o in cover_rectangles(sw, sh, grid):
        e = {"t": o["t"], "x": o["x"] + x, "y": o["y"] + y, "w": o["w"], "h": o["h"]}
        if gid is not None:
            e["g"] = gid
        out.append(e)
    return out


def stamp_points(pf, x0, y0, x1, y1, step_x, step_y, bounds=None):
    """Область + шаг -> [(точки вставки)] и размер копии («ряд/сетка с шагом»).

    В режиме повтора штамп НЕ растягивается: ставится нативным размером везде,
    где целиком влезает с шагом step_x по колонкам и step_y по строкам. Шаг 0 =
    ось не повторяется (копия одна). Узкую протяжку (ряд монет тянут по одной
    клетке высотой) расширяем до размера штампа — иначе однострочная область не
    вмещает двухстрочную монетку и из жеста не выходит ничего. bounds=(cols,rows)
    отсекает копии, не влезающие в карту (ряд не наезжает сам на себя у края).
    """
    w, h = stamp_size(pf, len(pf["grid"][0]), len(pf["grid"]))
    xa, ya, xb, yb = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
    xe, ye = max(xb, xa + w - 1), max(yb, ya + h - 1)
    if bounds:
        xe, ye = min(xe, bounds[0] - 1), min(ye, bounds[1] - 1)
    xs = list(range(xa, xe + 1, step_x)) if step_x > 0 else [xa]
    ys = list(range(ya, ye + 1, step_y)) if step_y > 0 else [ya]
    pts = [(x, y) for y in ys for x in xs
           if x + w <= xe + 1 and y + h <= ye + 1]
    return (pts or [(xa, ya)]), (w, h)


# ---------------------------------------------------------------------------
# Распознавание префабов в готовой сетке (перенос старой карты)
# ---------------------------------------------------------------------------

def match_grid(cells, grid, cols, rows, x, y, skip_empty=False):
    """Ляжет ли сетка cells (row-major) в карту grid в (x,y)?

    Кол-major карты: grid[c*rows + r]. Тайл 0 в паттерне — «пусто»: по умолчанию
    требуется, чтобы и в карте клетка была пуста (иначе облако закроет камень).
    skip_empty=True — нули игнорируются: тогда проверяется лишь, что паттерн
    не разрушил то, что уже стоит в карте.
    """
    h, w = len(cells), len(cells[0])
    if x < 0 or y < 0 or x + w > cols or y + h > rows:
        return False
    for c in range(w):
        base = (x + c) * rows + y
        for r in range(h):
            t = cells[r][c]
            g = grid[base + r]
            if t == 0:
                if not skip_empty and g != 0:
                    return False
            elif g != t:
                return False
    return True


def grow_fit(pf, grid, cols, rows, x, y, min_area=None, cap=None):
    """Наибольший размер префаба, целиком совпадающий с картой в (x,y).

    Жадное выращивание: пробуем (+1,0), (0,+1), (+1,+1) по осям со stretch и
    берём первую форму, которая всё ещё совпадает; не совпало — стоп. Это НЕ
    глобальный перебор всех (w,h): перебор по 20 000 кандидатов на каждый якорь
    для земли/стены не вписывается ни в какой бюджет, а жадный рост стоит
    O(шагов × площадь) и для прогона 76×2 даёт ~11k проверок клетки.

    Ограничение: форма, у которой совпадение «возобновляется» после колонки с
    чужим тайлом (облако с разрывом), не находится — такие места мигрируют
    одиночными тайлами. На корректность карты это не влияет, только на степень
    схлопывания. cap=(макс_ширина, макс_высота) — потолок роста (по умолчанию
    до края карты).
    Возвращает (w, h) или None, если даже нативный размер не лёг.
    """
    sx, sy = pf.get("stretch_x"), pf.get("stretch_y")
    w, h = stamp_size(pf, len(pf["grid"][0]), len(pf["grid"]))
    if cap is None:
        cap = (cols - x, rows - y)
    if not match_grid(stamp_cells(pf, w, h), grid, cols, rows, x, y):
        return None
    while True:
        nxt = None
        for (dw, dh) in ((1, 0), (0, 1), (1, 1)):
            nw, nh = w + dw, h + dh
            if (dw and sx is None) or (dh and sy is None):
                continue
            if nw > cap[0] or nh > cap[1] or nw > MAX_COLS or nh > MAX_ROWS:
                continue
            if stamp_size(pf, nw, nh) != (nw, nh):
                continue                       # ниже min_w/min_h не сжимаемся
            if match_grid(stamp_cells(pf, nw, nh), grid, cols, rows, x, y):
                nxt = (nw, nh)
                break
        if nxt is None:
            break
        w, h = nxt
    if min_area is not None and w * h < min_area:
        return None
    return (w, h)


def single_tile_prefab(t, name=None):
    """Авто-префаб «одиночный тайл» — 1×1, не тянется.

    Нужен, чтобы карта оставалась списком экземпляров ПРЕФАБОВ целиком: клетки,
    которые не удалось схлопнуть в узнаваемый объект, становятся экземплярами
    вот такого тайла и лежат в палитре в секции «одиночные».
    """
    return {"name": name or ("Тайл %d" % t), "section": "одиночные",
            "grid": [[int(t)]]}


def single_tile_stretchable(t, name=None):
    """Авто-префаб «одиночный тайл», тянущийся по обеим осям.

    Остатки распознавания — это прямоугольники одного тайла (cover_rectangles).
    Если такой тайл кладётся в карту как есть (индекс совпадает с эталоном в
    каждой клетке), то 1×1-паттерн с «all» по осям разворачивается в тот же
    прямоугольник одним экземпляром: 4 Б вместо 4 Б на каждую клетку.
    """
    pf = single_tile_prefab(t, name)
    pf["stretch_x"] = "all"
    pf["stretch_y"] = "all"
    return pf


# ---------------------------------------------------------------------------
# Модель уровня v2: src/objects.json = список экземпляров префабов
# ---------------------------------------------------------------------------

def instance_size(pf, inst):
    """Реальный размер экземпляра: нативный, если w/h не заданы."""
    pat = pf["grid"]
    w = int(inst["w"]) if "w" in inst else len(pat[0])
    h = int(inst["h"]) if "h" in inst else len(pat)
    return stamp_size(pf, w, h)


def load_instances(path=OBJECTS_FILE):
    """src/objects.json (v2) -> (cols, rows, instances); нет файла -> (None, None, None)."""
    if not os.path.isfile(path):
        return None, None, None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if int(data.get("version", 1)) != PREFAB_VERSION:
        sys.exit("%s: версия %s, а ожидается %d — сначала tools/prefab_migrate.py"
                 % (path, data.get("version"), PREFAB_VERSION))
    return int(data["cols"]), int(data["rows"]), data.get("instances", [])


def save_instances(cols, rows, instances, path=OBJECTS_FILE):
    """Атомарная запись списка экземпляров (схема v2)."""
    body = {"cols": cols, "rows": rows, "version": PREFAB_VERSION,
            "instances": instances}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def expand_instances(cols, rows, prefabs, instances):
    """Экземпляры -> tilemap col-major; рисуем СТРОГО по порядку списка.

    Порядок списка = z-order (поздние перекрывают ранние), нули паттерна не
    пишут (ровно как rect'ы варианта в ROM: cover_rectangles нули отбрасывает).
    """
    by_name = {pf["name"]: pf for pf in prefabs}
    grid = bytearray(cols * rows)
    for inst in instances:
        pf = by_name[inst["pf"]]
        w, h = instance_size(pf, inst)
        cells = stamp_cells(pf, w, h)
        x, y = int(inst["x"]), int(inst["y"])
        for r, row in enumerate(cells):
            base = y + r
            for c, t in enumerate(row):
                if t:
                    grid[(x + c) * rows + base] = t
    return grid


def expand_by_blocks(cols, rows, prefabs, instances):
    """Tilemap, собранная как в ROM: блоки по 32 колонки, внутри блока — z-order.

    Генератор сортирует экземпляры по (блок, порядок списка) и печёт послойно
    по блокам; если объект пересекает границу блока, его порядок наложения
    задаёт блок, а не список. Расхождение с expand_instances — это и есть
    «z-order конфликтует с блочной группировкой» (см. допущения плана).
    """
    by_name = {pf["name"]: pf for pf in prefabs}
    order = sorted(range(len(instances)),
                   key=lambda i: (int(instances[i]["x"]) // OBJ_WIN_STEP, i))
    grid = bytearray(cols * rows)
    for i in order:
        inst = instances[i]
        pf = by_name[inst["pf"]]
        w, h = instance_size(pf, inst)
        cells = stamp_cells(pf, w, h)
        x, y = int(inst["x"]), int(inst["y"])
        for r, row in enumerate(cells):
            for c, t in enumerate(row):
                if t:
                    grid[(x + c) * rows + y + r] = t
    return grid


def build_variants(prefabs, instances):
    """Словарь ROM: (префаб, w, h) -> вариант с его прямоугольниками.

    -> (variants, ids). variants[i] = {name, w, h, rects[{t,dx,dy,w,h}], n,
    cells} в порядке первого появления; ids[i] — номер варианта i-го экземпляра
    (нативный размер не различает варианты: все «Монетки 2×2» получают один id).
    """
    by_name = {pf["name"]: pf for pf in prefabs}
    index = {}
    variants = []
    ids = []
    for inst in instances:
        pf = by_name[inst["pf"]]
        w, h = instance_size(pf, inst)
        key = (pf["name"], w, h)
        vid = index.get(key)
        if vid is None:
            rects = [{"t": o["t"], "dx": o["x"], "dy": o["y"],
                      "w": o["w"], "h": o["h"]}
                     for o in stamp_objects(pf, 0, 0, w, h)]
            vid = len(variants)
            index[key] = vid
            variants.append({"name": pf["name"], "w": w, "h": h, "rects": rects,
                             "n": 0, "cells": sum(r["w"] * r["h"]
                                                  for r in rects)})
        variants[vid]["n"] += 1
        ids.append(vid)
    return variants, ids


def variants_bytes(variants):
    return sum(VAR_BYTES + RECT_BYTES * len(v["rects"]) for v in variants)


def level_bytes(instances, variants):
    """Смета ROM на уровень v2: экземпляр 4 Б + словарь вариантов."""
    return INST_BYTES * len(instances) + variants_bytes(variants)


def validate_instances(cols, rows, prefabs, instances, variants=None):
    """Ограничения компактного формата и карты -> список строк-ошибок (пусто = ок).

    То же, что проверяет gen_assets при записи: id варианта 12 бит, x 9 бит,
    y/w/h байты, экземпляр целиком внутри карты.
    """
    errs = []
    by_name = {pf["name"]: pf for pf in prefabs}
    if variants is None:
        variants, _ = build_variants(prefabs, instances)
    if len(variants) > MAX_VARIANTS:
        errs.append("вариантов %d > %d (id варианта 12 бит)"
                    % (len(variants), MAX_VARIANTS))
    for i, inst in enumerate(instances):
        pf = by_name.get(inst["pf"])
        if pf is None:
            errs.append("#%d: нет префаба %r в библиотеке" % (i, inst["pf"]))
            continue
        x, y = int(inst["x"]), int(inst["y"])
        w, h = instance_size(pf, inst)
        if not 0 <= x <= MAX_COLS - 1:
            errs.append("#%d x=%d: вне 0..%d" % (i, x, MAX_COLS - 1))
        if not 0 <= y <= MAX_ROWS - 1:
            errs.append("#%d y=%d: вне 0..%d" % (i, y, MAX_ROWS - 1))
        if not (0 < w <= MAX_COLS and 0 < h <= MAX_ROWS):
            errs.append("#%d размер %dx%d: вне лимитов" % (i, w, h))
        if x + w > cols or y + h > rows:
            errs.append("#%d (%s) %dx%d в (%d,%d) не влезает в %dx%d"
                        % (i, inst["pf"], w, h, x, y, cols, rows))
    return errs
