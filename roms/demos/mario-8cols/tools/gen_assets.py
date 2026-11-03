#!/usr/bin/env python3
"""
gen_assets.py — ассеты демки Mario 8-цвет (сплит по плоскостям) для Вектора-06Ц.

Отличие от mario-16cols: 4 битовые плоскости поделены на ДВА слоя.
  * ФОН     — старшие 2 бита цвета: плоскости вес 8 (0x8000) и вес 4 (0xA000).
              4 цвета: небо / чёрный / белый / зелёный (с дизерингом).
  * ПЕРСОНАЖ — младшие 2 бита: плоскости вес 2 (0xC000) и вес 1 (0xE000).
              3 цвета: красный / розовый / чёрный (код 0 = прозрачность).

Итоговый индекс палитры = bg*4 + ch. Палитра разложена так, что спрайт побеждает
фон без маскирования: при ch=0 показываем цвет фона BG[bg], при ch=1..3 — цвет
спрайта CH[ch] (один и тот же RGB во всех четырёх «рядах» bg). Пустой пиксель =
индекс 0 = небо, поэтому тайл из чистого неба = все нули и в VRAM не пишется.

Источник истины: assets/objects.json (список экземпляров префабов, схема v2) +
assets/prefabs.json (библиотека), assets/tiles/*.png (графика тайлов),
assets/tiles.json (твёрдость, вариант C), assets/mario.png (лента спрайтов Mario),
assets/palette.json (финальные цвета: 4 кода фона + 4 кода персонажа).
assets/level.json — плоская сетка, из которой исторически выросли объекты; она
обязана побайтово совпадать с развёрнутым списком экземпляров (чекпоинт
паритета tools/check_parity.py).

Выход:
  include/level.inc  — палитра (16 слотов из palette.json), тайлсет 8x8
                   (2 плоскости, 16 Б), спаны колонок (pf_spans +
                   pf_span_ofs: то, что печётся в окно), tile_nz (2 бита),
                   pair_top, раны разности (rw_run_ofs/rw_run_data),
                   tile_solid;
  include/mario.inc  — спрайты 16x16 (2 плоскости, 64 Б, без маски).

Формат Вектора (256x256, блок = x/8 = 256 байт, байт i = строка y=255-i,
старший бит = левый пиксель).
"""

import os
import sys
import json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")     # сырьё/дизайн (json/png/tiles)
INCLUDE = os.path.join(HERE, "..", "include")   # генерируемые .inc
sys.path.insert(0, HERE)
import prefablib as PL                                     # noqa: E402

# ---- Геометрия уровня -------------------------------------------------------
BAND_TOP = 176          # верх видимой полосы уровня (нативные пиксели tiles.png)
BAND_H = 256            # высота полосы = экран
TILE = 8                # сторона тайла, px
TILE_BYTES = TILE * 2   # тайл фона = 2 плоскости по 8 байт
VEC_BYTES = 0x8000      # размер видеопамяти (для проверки)

# ---- Палитра 4+4: фон (старшие 2 бита) + персонаж (младшие 2 бита) ----------
# Байт порта 0C = RRRGGGBB. Источник истины — assets/palette.json (редактируется
# руками): 4 кода фона + 4 кода персонажа. Порядок элементов в файле задаёт код
# цвета, имена нужны дизерингу (green/sky в bg_quantize). Из этих же цветов
# считается BG_RGB/CH_RGB, поэтому правка цвета перепекает и фон, и спрайты.
PALETTE_FILE = os.path.join(ASSETS, "palette.json")

# Имена, без которых не работают ветки квантования; порядок — код цвета.
BG_NAMES = ("sky", "black", "white", "green")   # коды фона (bg) 0..3
CH_NAMES = ("transparent", "red", "pink", "black")


def load_palette(path=PALETTE_FILE):
    """assets/palette.json -> (BG_LIST, CH_LIST); ch[0] = None (прозрачность)."""
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    lists = []
    for layer, names, key in (("bg", BG_NAMES, "bg"), ("ch", CH_NAMES, "ch")):
        got = doc[key]
        if len(got) != 4:
            sys.exit(f"{os.path.basename(path)}: {key} должен ровно 4 кода "
                     f"(2 бита слоя), найдено {len(got)}")
        pal = []
        for item in got:
            v = item["vec"]
            if v is None:
                pal.append(None)              # прозрачность, код без цвета
                continue
            code = v if isinstance(v, int) else int(v, 0)
            if not 0 <= code <= 0xFF:
                sys.exit(f"{os.path.basename(path)}: {layer} {item['name']}: "
                         f"{v} не байт порта 0C")
            pal.append(code)
        if [i["name"] for i in got] != list(names):
            sys.exit(f"{os.path.basename(path)}: {layer} — имена обязаны идти "
                     f"по порядку {', '.join(names)} (порядок = код цвета)")
        lists.append(pal)
    if lists[1][0] is not None:
        sys.exit(f"{os.path.basename(path)}: ch[0] обязан быть null — "
                 f"это прозрачность спрайта (код 0 = пустой пиксель)")
    return lists


BG_LIST, CH_LIST = load_palette()
BG_SKY, BG_BLACK, BG_WHITE, BG_GREEN = range(4)     # небо, чёрный, белый, зелёный
CH_TRANSPARENT, CH_RED, CH_PINK, CH_BLACK = range(4)   # 0 = прозрачн, 1..3 = цвета


def build_palette():
    """16 слотов, индекс = bg*4 + ch. ch=0 -> цвет фона, ch>0 -> цвет спрайта."""
    pal = []
    for bg in range(4):
        for ch in range(4):
            pal.append(BG_LIST[bg] if ch == 0 else CH_LIST[ch])
    return pal


PALETTE = build_palette()

# Цвет прозрачности спрайт-листа (стальной фон листа) — не входит в палитру.
SHEET_BG = (41, 88, 124)


def to_rgb(vec):
    """Байт палитры Вектора -> приблизительный 24-бит RGB (для расстояний)."""
    r = (vec & 7) * 255 // 7
    g = ((vec >> 3) & 7) * 255 // 7
    b = ((vec >> 6) & 3) * 255 // 3
    return (r, g, b)


BG_RGB = [to_rgb(v) for v in BG_LIST]
CH_RGB = {c: to_rgb(CH_LIST[c]) for c in (CH_RED, CH_PINK, CH_BLACK)}


def _nearest(rgb, table):
    """Код ближайшего цвета из table: {код: RGB}."""
    best, bestd = None, 1 << 30
    for code, (pr, pg, pb) in table.items():
        d = (rgb[0] - pr) ** 2 + (rgb[1] - pg) ** 2 + (rgb[2] - pb) ** 2
        if d < bestd:
            best, bestd = code, d
    return best


# ---- Квантование фона с упорядоченным дизерингом ---------------------------
# Bayer 4x4 (0..15). Смещаем яркость пикселя на порог сетки и берём ближайший
# из 4 фоновых цветов: на границах зелёный<->белый и зелёный<->чёрный получается
# точечное смешение (светло-/тёмно-зелёный).
BAYER = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)
DITHER = 40            # сила дизеринга по яркости, 0 = плоское квантование


def _lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


# Яркости базового зелёного и неба — границы «светло-зелёного» дизеринга ниже.
_GREEN_LUM = _lum(BG_RGB[BG_GREEN])
_SKY_LUM = _lum(BG_RGB[BG_SKY])


def bg_quantize(rgb, x, y):
    """24-бит RGB -> код фона 0..3 с дизерингом Bayer по яркости.

    В 4-цветном фоне только ОДИН зелёный, а исходные кусты/трава/трубы рисуются
    двумя оттенками (тёмный корпус + светлые треугольники-узор). Светло-зелёного
    кода нет, поэтому второй оттенок имитируем шашечкой GREEN<->SKY по сетке
    Bayer: чем пиксель ярче базового зелёного, тем чаще выпадает cell неба —
    на глаз это более светлый зелёный. Ветку включаем только для зелёной
    семейства (g >= r): у кирпича/земли r > g, они идут прежним путём и не
    меняются.
    """
    off = (BAYER[y & 3][x & 3] / 16.0 - 0.5) * DITHER
    l = _lum(rgb)
    if l <= 1.0:
        s = 1.0
    else:
        nl = max(1.0, min(255.0, l + off))
        s = nl / l
    r2 = max(0, min(255, rgb[0] * s))
    g2 = max(0, min(255, rgb[1] * s))
    b2 = max(0, min(255, rgb[2] * s))
    table = {i: BG_RGB[i] for i in range(4)}
    code = _nearest((r2, g2, b2), table)
    # Светло-зелёные зоны зелёной семейства -> шашечка GREEN<->SKY.
    if code == BG_GREEN and rgb[1] >= rgb[0]:
        t = max(0.0, min(1.0, (l - _GREEN_LUM) / (_SKY_LUM - _GREEN_LUM)))
        if t >= (BAYER[y & 3][x & 3] + 0.5) / 16.0:
            return BG_SKY
    return code


def char_quantize(rgb):
    """24-бит RGB -> код персонажа 1..3 (ближайший из красный/розовый/чёрный)."""
    return _nearest(rgb, CH_RGB)


# ---------------------------------------------------------------------------
# Уровень из редакторских файлов: assets/level.json + assets/tiles/*.png + tiles.json
# ---------------------------------------------------------------------------
# Источник истины для сборки ROM: раскладка из level.json, графика из tile-PNG,
# твёрдость из tiles.json.

def png_to_tile(path):
    """8x8 PNG -> 16-байтный тайл ФОНА (2 плоскости: вес 8, вес 4).

    Код фона bg (0..3) раскладывается по плоскостям старших битов:
    бит1 (value 2) -> плоскость веса 8, бит0 (value 1) -> плоскость веса 4.
    Младшие 2 бита (персонаж) в тайлах фона всегда 0.
    """
    im = Image.open(path).convert("RGB")
    px = im.load()
    p8 = bytearray(TILE)      # вес 8 (0x8000) = bg bit1
    p4 = bytearray(TILE)      # вес 4 (0xA000) = bg bit0
    for r in range(TILE):
        b8 = b4 = 0
        for c in range(TILE):
            code = bg_quantize(px[c, r], c, r)
            bit = 7 - c
            if code & 2:
                b8 |= 1 << bit
            if code & 1:
                b4 |= 1 << bit
        p8[r] = b8
        p4[r] = b4
    return bytes(p8 + p4)


def _compute_tile_nz(tileset):
    """2-битная карта непустых плоскостей фона (бит0 = вес 8, бит1 = вес 4)."""
    nz = bytearray()
    for t in tileset:
        m = 0
        if any(t[r] for r in range(TILE)):
            m |= 1
        if any(t[TILE + r] for r in range(TILE)):
            m |= 2
        nz.append(m)
    return nz


RUN_PAD = 32                   # запас колонок таблицы ранов (ширина экрана)


def _diff_runs(tilemap, cols, rows):
    """(row,count)-раны: где колонка отличается от ЛЕВОЙ (для колонки 0 — от неба).

    Рендер разности ходит по этим ранам вместо построчного сравнения tile_win:
    430 ранов на 320 колонок против ~1.5 тыс. сравнений за шаг. Терминатор —
    пара (0,0): count=0 не бывает у настоящего рана. cols здесь — ширина карты
    ВМЕСТЕ с запасом RUN_PAD (см. build_level_editor).
    """
    sky = bytes(rows)
    data = bytearray()
    ofs = []
    for c in range(cols):
        ofs.append(len(data))
        cur = tilemap[c * rows:(c + 1) * rows]
        ref = tilemap[(c - 1) * rows:c * rows] if c else sky
        r = 0
        while r < rows:
            if cur[r] == ref[r]:
                r += 1
                continue
            r0 = r
            while r < rows and cur[r] != ref[r]:
                r += 1
            data += bytes((r0, r - r0))
        data += b"\x00\x00"            # терминатор колонки
    return ofs, bytes(data)


def _compute_pair_top(cols, rows, tilemap):
    def col_top(cx):
        for cy in range(rows):
            if tilemap[cx * rows + cy]:
                return cy
        return rows
    return bytearray(min(col_top(cx), col_top(cx + 1)) for cx in range(cols - 1))


def build_level_editor():
    """assets/objects.json v2 (экземпляры) + assets/prefabs.json -> модель уровня."""
    with open(os.path.join(ASSETS, "level.json")) as f:
        lv = json.load(f)
    with open(os.path.join(ASSETS, "tiles.json")) as f:
        tj = json.load(f)
    cols, rows = int(lv["cols"]), int(lv["rows"])
    # Источник карты — список экземпляров префабов. Плоскую сетку level.json
    # больше не сегментируем: ROM хранит не описание, а результат — спаны
    # колонок (см. prefablib.spans_of).
    prefabs = PL.load_prefabs()
    o_cols, o_rows, instances = PL.load_instances()
    if instances is None:
        sys.exit("нет assets/objects.json — уровень собирается из списка "
                 "экземпляров: python3 tools/prefab_migrate.py --apply --force "
                 "или tools/level_editor.py")
    if (o_cols, o_rows) != (cols, rows):
        sys.exit(f"objects.json: {o_cols}x{o_rows} != level.json {cols}x{rows}")
    errs = PL.validate_instances(cols, rows, prefabs, instances)
    if errs:
        sys.exit("objects.json: " + "; ".join(errs[:5]))
    variants = PL.build_variants(prefabs, instances)[0]
    # Сортировка списка: (32-колоночный блок, порядок в списке). Внутри блока
    # порядок списка = z-order (первый штампуется первым), между блоками порядок
    # задаёт блок — ровно так же, как это делал блочный словарь, поэтому карта
    # (а значит и спаны) от перехода на результат не поменялась.
    order = sorted(range(len(instances)),
                   key=lambda i: (int(instances[i]["x"]) // PL.OBJ_WIN_STEP, i))
    model = {"instances": [instances[i] for i in order]}
    # Картой «что лежит в tile_win» считаем то, что реально напечатает ROM,
    # то есть порядок групп. Он же равен порядку списка (z-order редактора),
    # если ни одна перекрывающаяся пара не пересекает границу 32 колонок.
    tilemap = PL.expand_instances(cols, rows, prefabs, model["instances"])
    zdiff = sum(1 for i, v in enumerate(PL.expand_instances(cols, rows,
                                                             prefabs, instances))
                if v != tilemap[i])
    if zdiff:
        print(f"ВНИМАНИЕ: z-order воюет с блочной группировкой в {zdiff} "
              f"клетках: на границе 32 колонок порядок наложения задаёт блок")
    if len(tilemap) != cols * rows:
        sys.exit("level: карта не соответствует cols*rows")
    # Ограничения адресации рендера (mario.asm, 8080, 16-битные указатели):
    #   * stride = LEVEL_ROWS и cam_row — байтовые (кольцо 256 строк = 32 ряда);
    #   * cam*stride < размер tilemap = cols*rows должен влезать в 16 бит.
    if rows > PL.MAX_ROWS:
        sys.exit(f"level.json: rows={rows} > {PL.MAX_ROWS} — stride/камера "
                 f"байтовые, кольцо вертикали 256 px")
    if cols * rows > 65535:
        sys.exit(f"level.json: cols*rows={cols*rows} > 65535 — тайлкарта не "
                 f"влезает в 16-битную адресацию (сделайте уже/ниже)")
    tiles = sorted(tj["tiles"], key=lambda t: t["index"])
    tileset = []
    for i, t in enumerate(tiles):
        if int(t["index"]) != i:
            sys.exit(f"tiles.json: дыра/порядок индексов (ожидался {i})")
        tileset.append(png_to_tile(os.path.join(ASSETS, t["file"])))
    if tileset[0] != bytes(TILE_BYTES):
        sys.exit("tiles.json: тайл 0 должен быть пустым (небо = все нули)")
    tile_nz = _compute_tile_nz(tileset)
    pair_top = _compute_pair_top(cols, rows, tilemap)
    # Раны разности печём по карте, СОВПАДАЮЩЕЙ с окном ROM (то же, что печёт
    # bake_cols):
    # рендер пишет ровно те клетки, где соседние колонки различаются, поэтому
    # расхождение модели и ROM означало бы неверные пиксели, а не «чуть больше
    # работы». expand_by_blocks — модель блочной группировки ROM.
    grid_rom = PL.expand_by_blocks(cols, rows, prefabs, model["instances"])
    if grid_rom != tilemap:
        print("ВНИМАНИЕ: expand_by_blocks != expand_instances — раны разности "
              "и pair_top построены по разным картам")
    # Таблица ранов шире карты на RUN_PAD колонок: рендер индексирует её как
    # cam+blk0 и при cam вплоть до LEVEL_COLS уходит за последнюю настоящую
    # колонку. Там окно пустое (ни один экземпляр не выходит за cols — это
    # проверяет validate_instances), поэтому «лишние» колонки — небо: свои
    # раны есть только у первой из них (разность с краем карты), остальные —
    # пустой список. Без запаса ROM читал бы соседние таблицы как раны.
    grid_pad = PL.expand_by_blocks(cols + RUN_PAD, rows, prefabs,
                                   model["instances"])
    run_ofs, run_data = _diff_runs(grid_pad, cols + RUN_PAD, rows)
    # Спаны — то, что ROM печёт в окно: словарь экземпляров ему больше не нужен
    # (см. prefablib.spans_of). Печём по той же карте, что и раны разности, то
    # есть по tilemap (= ROM-порядок блоков), а не по несортированному списку.
    spans, span_ofs = PL.spans_of(tilemap, cols, rows, pad=PL.OBJ_WIN_STEP)
    model["spans"] = (spans, span_ofs)
    model["tilemap"] = bytes(tilemap)
    print(f"level(editor): {cols}x{rows}, тайлов в наборе: {len(tileset)}, "
          f"тайл {TILE_BYTES} Б (2 плоскости), экземпляров: "
          f"{len(model['instances'])}, вариантов: {len(variants)}")
    print(f"  смета уровня: {PL.spans_bytes(spans, span_ofs)} Б (спаны "
          f"{len(spans)} + смещения 2×{len(span_ofs)}) — вместо словаря экземпляров")
    # ---- локи экранов (screen blocks 32×32) ----
    raw_blocks = lv.get("blocks", [])
    col_blks = (cols + 31) // 32
    row_blks = (rows + 31) // 32
    n_scr = col_blks * row_blks
    if len(raw_blocks) == n_scr:
        scr_blocks = bytes(raw_blocks)
    else:
        scr_blocks = bytes(n_scr)
    print(f"  экранная карта локов: {col_blks}×{row_blks} = {n_scr} байт")
    return (cols, rows, tileset, bytes(tilemap), bytes(tile_nz),
            bytes(pair_top), model, (run_ofs, bytes(run_data)),
            scr_blocks, col_blks, row_blks)


# ---------------------------------------------------------------------------
# Словарь экземпляров — УДАЛЁН
# ---------------------------------------------------------------------------
# Раньше здесь упаковывались pf_data (4 Б на экземпляр), pf_rects (5 Б на
# прямоугольник варианта), pf_var_ofs/pf_var_n и pf_start (группы блоков).
# Всё это читала ТОЛЬКО печка, поэтому в ROM теперь лежит её результат —
# спаны колонок (prefablib.spans_of, write_level). Список экземпляров остаётся
# источником истины в assets/objects.json: из него разворачивается карта, а
# из карты — спаны и таблица ранов. Проверка паритета редактора с генератором
# теперь тоже смотрит на карту (expand_by_blocks), а не на упаковку в 4 Б.


# ---------------------------------------------------------------------------
# Чтение старого формата (rect'ы) — нужно мигратору и чекпоинту паритета
# ---------------------------------------------------------------------------
# assets/objects.json версии 1 хранил уровень как набор объектов {t, x, y, w, h}.
# expand_objects разворачивает их обратно в tilemap col-major побайтово к той же
# карте, что и grid (чекпоинт паритета tools/check_parity.py). ROM этот формат
# больше не читает: v2 — словарь вариантов + список экземпляров.

def load_objects():
    """assets/objects.json v1 -> (cols, rows, objects); v2/нет файла -> None."""
    path = os.path.join(ASSETS, "objects.json")
    if not os.path.exists(path):
        return None, None, None
    with open(path, encoding="utf-8") as f:
        ov = json.load(f)
    if int(ov.get("version", 1)) != 1:
        return int(ov["cols"]), int(ov["rows"]), None
    return int(ov["cols"]), int(ov["rows"]), ov["objects"]


def expand_objects(cols, rows, objects):
    """Объекты -> bytearray tilemap[col*rows+row]. Одно-тайловые прямоугольники."""
    tilemap = bytearray(cols * rows)
    for o in objects:
        t = int(o["t"])
        x = int(o["x"])
        y = int(o["y"])
        w = int(o["w"])
        h = int(o["h"])
        for dx in range(w):
            base = (x + dx) * rows + y
            for dy in range(h):
                tilemap[base + dy] = t
    return tilemap


# ---------------------------------------------------------------------------
# Коллизии: вариант C — твёрдость как СВОЙСТВО ТАЙЛА (assets/tiles.json)
# ---------------------------------------------------------------------------
# COLL_PLAT (1) — опора сверху; COLL_WALL (2) — непроходимо; 3 — и то, и другое.
COLL_PLAT, COLL_WALL = 1, 2


def load_tile_solid(n_tiles):
    """assets/tiles.json -> bytes длины n_tiles, каждый = маска COLL_*."""
    path = os.path.join(ASSETS, "tiles.json")
    with open(path) as f:
        data = json.load(f)
    tiles = data["tiles"]
    if len(tiles) != n_tiles:
        sys.exit(f"tiles.json: {len(tiles)} тайлов, а tileset: {n_tiles} — "
                 f"пересоберите затравку (tools/export_assets.py)")
    solid = bytearray(n_tiles)
    for t in tiles:
        m = (COLL_WALL if t.get("wall") else 0) | (COLL_PLAT if t.get("platform") else 0)
        solid[t["index"]] = m
    nw = sum(1 for b in solid if b & COLL_WALL)
    np_ = sum(1 for b in solid if b & COLL_PLAT)
    print(f"collision (tile props): {n_tiles} тайлов, wall={nw} platform={np_}")
    return bytes(solid)


# ---------------------------------------------------------------------------
# Спрайты Small Mario: 16x16, 2 плоскости персонажа, без маски
# ---------------------------------------------------------------------------
# assets/mario.png — лента из 18 спрайтов Small Mario 16x16, пронумерованы 1..18.
# БАЗОВЫЕ СПРАЙТЫ СМОТРЯТ ВЛЕВО; _l рисуем как есть, _r — зеркалом.
MARIO_TOP = 14          # верх спрайтовой полосы (строки 14..29)
MARIO_PITCH = 18        # шаг ячейки по X
MARIO_X0 = 0            # левый край 16-px окна внутри ячейки
MARIO_SIZE = 16
MARIO_BYTES = MARIO_SIZE * MARIO_SIZE * 2 // 8   # 2 плоскости x 16x16 / 8 = 64
# Прозрачны: фон ячейки (68,145,190) и поле листа (41,88,124).
MARIO_BG = [(68, 145, 190), (41, 88, 124)]

# Кадр анимации -> номер спрайта в mario.png (1..18). stand/walk0/walk2/duck
# указывают на одну ячейку #1 — write_sprites оставит один образ, прочие имена
# станут #define-алиасами (экономия ROM).
FRAMES = {
    "stand": 1,   # 01 стоит/идёт влево
    "walk0": 1,   # 01
    "walk1": 2,   # 02 идёт влево
    "walk2": 1,   # 01  (походка чередует 01<->02)
    "jump":  3,   # 03 прыгает влево
    "duck":  1,   # у Small Mario нет приседа — используем стойку
}


def _near(p, key, tol=12):
    return abs(p[0] - key[0]) < tol and abs(p[1] - key[1]) < tol \
        and abs(p[2] - key[2]) < tol


def extract_cell(px, num):
    """grid[16][16] кодов персонажа (1..3), None — прозрачный."""
    x0 = MARIO_X0 + MARIO_PITCH * (num - 1)
    grid = []
    for r in range(MARIO_SIZE):
        y = MARIO_TOP + r
        row = []
        for c in range(MARIO_SIZE):
            p = px[x0 + c, y]
            if any(_near(p, bg) for bg in MARIO_BG):
                row.append(None)          # прозрачный пиксель
            else:
                row.append(char_quantize(p))
        grid.append(row)
    return grid


def grid_to_sprite(grid, mirror=False):
    """grid[16][16] -> 64 байта: 4 прогона по 16 байт (прямая запись, без маски).

    Порядок прогонов: плоскость (вес 2 @0xC000, затем вес 1 @0xE000) x колонка
    блока (0 = левые 8 px, 1 = правые 8 px), внутри — строки 0..15 сверху вниз.
    Байт = битовая маска пикселей колонки, у которых соответствующий бит кода ch
    установлен (ch bit1 -> плоскость веса 2, ch bit0 -> плоскость веса 1).
    Прозрачный пиксель (ch=0) не даёт единиц ни в одной плоскости.
    """
    if mirror:
        grid = [list(reversed(row)) for row in grid]
    out = bytearray(MARIO_BYTES)
    k = 0
    for w in (2, 1):                 # плоскость: вес 2, затем вес 1
        for c in range(2):           # левая/правая колонка по 8 пикселей
            for r in range(MARIO_SIZE):   # строки сверху вниз
                b = 0
                for i in range(8):
                    idx = grid[r][c * 8 + i]
                    if idx is None:
                        continue
                    if idx & w:
                        b |= 1 << (7 - i)
                out[k] = b
                k += 1
    return bytes(out)


def build_sprites():
    im = Image.open(os.path.join(ASSETS, "mario.png")).convert("RGB")
    px = im.load()
    out = {}
    for name, num in FRAMES.items():
        grid = extract_cell(px, num)
        out[name + "_l"] = grid_to_sprite(grid, mirror=False)
        out[name + "_r"] = grid_to_sprite(grid, mirror=True)
    return out


# ---------------------------------------------------------------------------
# Вывод .inc
# ---------------------------------------------------------------------------

def fmt_array(f, name, data, per_line=16):
    # Глобальные (не static): на них ссылается mario.asm через EXTERN _<name>.
    f.write(f"const unsigned char {name}[{len(data)}] = {{\n")
    for i in range(0, len(data), per_line):
        chunk = data[i:i + per_line]
        f.write("    " + ", ".join(f"0x{v:02X}" for v in chunk) + ",\n")
    f.write("};\n\n")


def fmt_array_u16(f, name, vals, per_line=10):
    # 16-битная таблица (unsigned int, little-endian). Читает C (bake_window);
    # rw_run_ofs читает ещё и mario.asm — как пару байт lo,hi.
    f.write(f"const unsigned int {name}[{len(vals)}] = {{\n")
    for i in range(0, len(vals), per_line):
        chunk = vals[i:i + per_line]
        f.write("    " + ", ".join(str(v) for v in chunk) + ",\n")
    f.write("};\n\n")


def write_level(cols, rows, tileset, tile_nz, pair_top, tile_solid, model, runs,
                scr_blocks, col_blks, row_blks):
    path = os.path.join(INCLUDE, "level.inc")
    spans, span_ofs = model["spans"]
    nblocks = (cols + PL.OBJ_WIN_STEP - 1) // PL.OBJ_WIN_STEP
    # Спаны — единственное, из чего ROM собирает окно. Дешёвая страховка: если
    # обратная развёртка не даёт ту же карту, ROM нарисует не то — падаем здесь.
    back = PL.spans_to_map(spans, span_ofs, cols, rows)
    if back != model["tilemap"]:
        bad = sum(1 for i in range(len(back)) if back[i] != model["tilemap"][i])
        sys.exit(f"спаны не разворачиваются обратно в карту: {bad} клеток")
    with open(path, "w") as f:
        f.write("/* Автоген: tools/gen_assets.py (Mario 8-col, сплит по плоскостям). "
                "Не править руками. */\n\n")
        f.write(f"#define LEVEL_COLS   {cols}\n")
        f.write(f"#define LEVEL_ROWS   {rows}\n")
        f.write(f"#define LEVEL_TILE_W {cols*TILE}\n")
        f.write(f"#define LEVEL_TILE_H {rows*TILE}\n")
        f.write(f"#define TILESET_N    {len(tileset)}\n")
        f.write(f"#define TILE_BYTES   {TILE_BYTES}   /* тайл фона = 2 плоскости */\n")
        f.write("#define TILE_EMPTY   0         /* чистое небо, обе плоскости 0 */\n\n")
        # Кольцевое RAM-окно тайлкарты (Фаза 3): печём OBJ_WIN_COLS колонок,
        # сдвиг окна шагом OBJ_WIN_STEP (<= половины окна), чтобы видимая
        # полоса [cam, cam+VIEW_BLOCKS] всегда лежала в запеченном окне.
        f.write("#define OBJ_WIN_COLS   64      /* колонок в RAM-окне tile_win */\n")
        f.write("#define OBJ_WIN_STEP   32      /* шаг сдвига окна (cam>>5<<5) */\n")
        f.write(f"#define OBJ_WIN_BLOCKS {nblocks}     /* ceil(LEVEL_COLS/OBJ_WIN_STEP) */\n")
        f.write(f"#define PF_SPAN_BYTES {len(spans)}   /* поток спанов (б) */\n")
        f.write(f"#define PF_SPAN_COLS {len(span_ofs)}    /* колонок в таблице смещений: LEVEL_COLS + OBJ_WIN_STEP */\n")
        f.write("/* Окно печётся из ПО-КОЛОНОЧНЫХ СПАНОВ — вертикальных прогонов\n"
                "   одинакового непустого тайла. Колонка c — отрезок\n"
                "   pf_spans[pf_span_ofs[c] .. pf_span_ofs[c+1]), записи:\n"
                "     {tile, 2*row}          — одиночная клетка,\n"
                "     {tile, 2*row|1, len}   — прогон len >= 2,\n"
                "     {0xFF}                 — конец колонки.\n"
                "   Развёртка в окне — bake_cols() из include/bake.asm. */\n")
        # Палитра берётся из assets/palette.json; слот = bg*4 + ch (см. build_palette).
        f.write("/* Палитра ниже — из assets/palette.json (слот = bg*4 + ch). */\n")
        fmt_array(f, "level_palette", bytes(PALETTE))
        joined = b"".join(tileset)
        fmt_array(f, "tileset", joined)
        fmt_array(f, "pf_spans", spans)            # спаны колонок: то, что печётся
        fmt_array_u16(f, "pf_span_ofs", span_ofs)  # колонка -> смещение в pf_spans
        fmt_array(f, "tile_nz", tile_nz)           # 2 бита: непустая плоскость веса 8 / 4
        fmt_array(f, "pair_top", pair_top)         # верх diff'а на пару соседних колонок
        # Таблица ранов разности (см. _diff_runs): рендер по ней знает, какие
        # строки колонки отличаются от левой, и не сканирует tile_win построчно.
        f.write("/* rw_run_ofs[колонка] — смещение в rw_run_data; раны — пары\n"
                "   (row, count), терминатор (0,0). Читает mario.asm\n"
                "   (быстрый путь render_window при |old_cam-cam| == 1). */\n")
        run_ofs, run_data = runs
        fmt_array_u16(f, "rw_run_ofs", run_ofs)
        fmt_array(f, "rw_run_data", run_data)
        f.write("\n/* Коллизии (assets/tiles.json): tile_solid[тайл] = маска COLL_*. */\n")
        f.write("#define COLL_WALL   2   /* непроходимо */\n")
        f.write("#define COLL_PLAT   1   /* one-way опора */\n\n")
        fmt_array(f, "tile_solid", tile_solid)
        # ---- локи экранов (screen locks) ----
        f.write("\n/* Локи экранов: битовая маска на ячейку 32×32 тайла.\n"
                "   Бит 0 (LOCK_R=1): камера не едет правее правого края экрана.\n"
                "   Бит 1 (LOCK_L=2): камера не едет левее левого края экрана.\n"
                "   Бит 2 (LOCK_D=4): камера не едет ниже нижнего края экрана.\n"
                "   Бит 3 (LOCK_U=8): камера не едет выше верхнего края экрана. */\n")
        f.write(f"#define SCR_COL_BLKS  {col_blks}\n")
        f.write(f"#define SCR_ROW_BLKS  {row_blks}\n")
        f.write("#define LOCK_R  1\n")
        f.write("#define LOCK_L  2\n")
        f.write("#define LOCK_D  4\n")
        f.write("#define LOCK_U  8\n\n")
        fmt_array(f, "scr_blocks", scr_blocks)
    print(f"  таблица спанов: {PL.spans_bytes(spans, span_ofs)} Б (поток "
          f"{len(spans)} + смещения {2 * len(span_ofs)})")
    print(f"wrote {path} ({os.path.getsize(path)} bytes)")


def write_sprites(sprites):
    path = os.path.join(INCLUDE, "mario.inc")
    order = []
    for name in FRAMES:
        order.append((name + "_r", sprites[name + "_r"]))
        order.append((name + "_l", sprites[name + "_l"]))
    seen = {}          # bytes -> канонический символ, уже выписанный
    uniq = 0
    with open(path, "w") as f:
        f.write("/* Автоген: tools/gen_assets.py из mario.png (Mario 8-col). "
                "Не править руками. */\n")
        f.write("/* Спрайт 16x16: 4 прогона (плоскость вес2,вес1 x колонка 0,1) "
                "по 16 байт. Прямая запись в плоскости персонажа, маски нет. */\n\n")
        f.write("#define MARIO_W 16\n#define MARIO_H 16\n")
        f.write(f"#define MARIO_BYTES {MARIO_BYTES}\n\n")
        for nm, data in order:
            sym = "mario_" + nm
            if data in seen:
                f.write(f"#define {sym:<18} {seen[data]}\n")
            else:
                seen[data] = sym
                uniq += 1
                f.write("\n")
                fmt_array(f, sym, data)
    print(f"wrote {path} ({os.path.getsize(path)} bytes), уникальных образов: {uniq}")


def main():
    cols, rows, tileset, tilemap, tile_nz, pair_top, model, runs, \
        scr_blocks, col_blks, row_blks = build_level_editor()
    tile_solid = load_tile_solid(len(tileset))
    sprites = build_sprites()
    write_level(cols, rows, tileset, tile_nz, pair_top, tile_solid, model, runs,
                scr_blocks, col_blks, row_blks)
    write_sprites(sprites)


if __name__ == "__main__":
    main()
