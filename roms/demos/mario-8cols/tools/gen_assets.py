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

Источник истины: src/level.json (раскладка), src/tiles/*.png (графика тайлов),
src/tiles.json (твёрдость, вариант C), src/mario.png (лента спрайтов Mario).

Выход:
  src/level.inc  — палитра (16 слотов), тайлсет 8x8 (2 плоскости, 16 Б),
                   тайлкарта, tile_nz (2 бита), pair_top, tile_solid;
  src/mario.inc  — спрайты 16x16 (2 плоскости, 64 Б, без маски).

Формат Вектора (256x256, блок = x/8 = 256 байт, байт i = строка y=255-i,
старший бит = левый пиксель).
"""

import os
import sys
import json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")

# ---- Геометрия уровня -------------------------------------------------------
BAND_TOP = 176          # верх видимой полосы уровня (нативные пиксели tiles.png)
BAND_H = 256            # высота полосы = экран
TILE = 8                # сторона тайла, px
TILE_BYTES = TILE * 2   # тайл фона = 2 плоскости по 8 байт
VEC_BYTES = 0x8000      # размер видеопамяти (для проверки)

# ---- Палитра 4+4: фон (старшие 2 бита) + персонаж (младшие 2 бита) ----------
# Байт порта 0C = RRRGGGBB.
#
# Коды фона (bg = старшие 2 бита индекса): 0..3.
BG_SKY, BG_BLACK, BG_WHITE, BG_GREEN = 0, 1, 2, 3
BG_LIST = [0xFD, 0x00, 0xFF, 0x2A]        # небо, чёрный, белый, зелёный (база)

# Коды персонажа (ch = младшие 2 бита): 0 = прозрачно, 1..3 = цвета.
CH_RED, CH_PINK, CH_BLACK = 1, 2, 3
CH_LIST = [None, 0x0D, 0xF7, 0x00]        # прозрачн, красный, розовый(кожа), чёрный


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
# Уровень из редакторских файлов: src/level.json + src/tiles/*.png + tiles.json
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


def _compute_pair_top(cols, rows, tilemap):
    def col_top(cx):
        for cy in range(rows):
            if tilemap[cx * rows + cy]:
                return cy
        return rows
    return bytearray(min(col_top(cx), col_top(cx + 1)) for cx in range(cols - 1))


def build_level_editor():
    with open(os.path.join(SRC, "level.json")) as f:
        lv = json.load(f)
    with open(os.path.join(SRC, "tiles.json")) as f:
        tj = json.load(f)
    cols, rows = int(lv["cols"]), int(lv["rows"])
    tilemap = bytearray(lv["grid"])
    if len(tilemap) != cols * rows:
        sys.exit("level.json: grid не соответствует cols*rows")
    # Ограничения адресации рендера (mario.asm, 8080, 16-битные указатели):
    #   * stride = LEVEL_ROWS и cam_row — байтовые (кольцо 256 строк = 32 ряда);
    #   * cam*stride < размер tilemap = cols*rows должен влезать в 16 бит.
    if rows > 255:
        sys.exit(f"level.json: rows={rows} > 255 — stride/камера байтовые, "
                 f"кольцо вертикали 256 px")
    if cols * rows > 65535:
        sys.exit(f"level.json: cols*rows={cols*rows} > 65535 — тайлкарта не "
                 f"влезает в 16-битную адресацию (сделайте уже/ниже)")
    tiles = sorted(tj["tiles"], key=lambda t: t["index"])
    tileset = []
    for i, t in enumerate(tiles):
        if int(t["index"]) != i:
            sys.exit(f"tiles.json: дыра/порядок индексов (ожидался {i})")
        tileset.append(png_to_tile(os.path.join(SRC, t["file"])))
    if tileset[0] != bytes(TILE_BYTES):
        sys.exit("tiles.json: тайл 0 должен быть пустым (небо = все нули)")
    tile_nz = _compute_tile_nz(tileset)
    pair_top = _compute_pair_top(cols, rows, tilemap)
    print(f"level(editor): {cols}x{rows}, тайлов в наборе: {len(tileset)}, "
          f"тайл {TILE_BYTES} Б (2 плоскости)")
    return cols, rows, tileset, bytes(tilemap), bytes(tile_nz), bytes(pair_top)


# ---------------------------------------------------------------------------
# Коллизии: вариант C — твёрдость как СВОЙСТВО ТАЙЛА (src/tiles.json)
# ---------------------------------------------------------------------------
# COLL_PLAT (1) — опора сверху; COLL_WALL (2) — непроходимо; 3 — и то, и другое.
COLL_PLAT, COLL_WALL = 1, 2


def load_tile_solid(n_tiles):
    """src/tiles.json -> bytes длины n_tiles, каждый = маска COLL_*."""
    path = os.path.join(SRC, "tiles.json")
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
# src/mario.png — лента из 18 спрайтов Small Mario 16x16, пронумерованы 1..18.
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
    im = Image.open(os.path.join(SRC, "mario.png")).convert("RGB")
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


def write_level(cols, rows, tileset, tilemap, tile_nz, pair_top, tile_solid):
    path = os.path.join(SRC, "level.inc")
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
        fmt_array(f, "level_palette", bytes(PALETTE))
        joined = b"".join(tileset)
        fmt_array(f, "tileset", joined)
        fmt_array(f, "tilemap", tilemap)
        fmt_array(f, "tile_nz", tile_nz)      # 2 бита: непустая плоскость веса 8 / 4
        fmt_array(f, "pair_top", pair_top)    # верх diff'а на пару соседних колонок
        f.write("\n/* Коллизии (src/tiles.json): tile_solid[тайл] = маска COLL_*. */\n")
        f.write("#define COLL_WALL   2   /* непроходимо */\n")
        f.write("#define COLL_PLAT   1   /* one-way опора */\n\n")
        fmt_array(f, "tile_solid", tile_solid)
    print(f"wrote {path} ({os.path.getsize(path)} bytes)")


def write_sprites(sprites):
    path = os.path.join(SRC, "mario.inc")
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
    cols, rows, tileset, tilemap, tile_nz, pair_top = build_level_editor()
    tile_solid = load_tile_solid(len(tileset))
    sprites = build_sprites()
    write_level(cols, rows, tileset, tilemap, tile_nz, pair_top, tile_solid)
    write_sprites(sprites)


if __name__ == "__main__":
    main()
