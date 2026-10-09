#!/usr/bin/env python3
"""
gen_assets.py — ассеты демки Mario 16-цвет для Вектора-06Ц.

Читает src/tiles.png (карта уровня SMB 1-1) и src/sprites.png (лист спрайтов),
квантует всё в ОДНУ общую 16-цветную палитру Вектора и пишет:

  src/level.inc   — палитра, тайлсет 8x8 (4 плоскости), тайлкарта уровня;
  src/mario.inc   — спрайты Small Mario 16x16 с маской (вправо/влево).

Формат Вектора (256x256, 16 цветов, 4 битовые плоскости):
  плоскость вес 8 -> 0x8000, вес 4 -> 0xA000, вес 2 -> 0xC000, вес 1 -> 0xE000;
  внутри плоскости блок = x/8 (256 байт), байт i хранит строку y = 255 - i
  (строки сверху вниз идут по УБЫВАЮЩЕМУ адресу), старший бит = левый пиксель.

Тайл 8x8: 4 плоскости по 8 байт (строки 0..7 сверху вниз), порядок плоскостей
вес 8,4,2,1. Итого 32 байта на тайл.

Тайлкарта: tilemap[col*ROWS + row] — индекс тайла; колонками, чтобы экранный
блок (столбец из 8 пикселей, 32 тайла по высоте) читался 32 подряд идущими
байтами.

Спрайт 16x16: сначала маска (32 байта, колонками: col0 строки 0..15, col1
строки 0..15), затем 4 плоскости по 32 байта тем же порядком. Итого 160 байт.
"""

import os
import sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")

# ---- Геометрия уровня -------------------------------------------------------
BAND_TOP = 176          # верх видимой полосы уровня (нативные пиксели tiles.png)
BAND_H = 256            # высота полосы = экран
TILE = 8
VEC_BYTES = 0x8000      # размер видеопамяти (для проверки)

# ---- Общая палитра: индекс -> байт порта 0C (RRRGGGBB) ----------------------
# Собрана из цветов фона (небо/земля/кирпич/кусты/белый/чёрный) и Марио
# (красный, кожа). Индекс 0 = чёрный (заливка gfx_clear).
PALETTE = [
    0x00,   # 0  чёрный      (контур, ямы)
    0x0D,   # 1  красный     (Марио: кепка/штаны)
    0xF7,   # 2  кожа        (Марио: лицо/руки)
    0xFD,   # 3  небо        (голубой фон)
    0xB7,   # 4  коричневый  (земля)
    0x67,   # 5  оранжевый   (кирпич)
    0x2A,   # 6  зелёный тёмный
    0x73,   # 7  зелёный светлый (кусты/трубы)
    0xFF,   # 8  белый       (облака/цифры)
    0x00,   # 9  (не используется)
    0x00,   # 10
    0x00,   # 11
    0x00,   # 12
    0x00,   # 13
    0x00,   # 14
    0x00,   # 15
]

# Цвет прозрачности спрайт-листа (стальной фон листа) — не входит в палитру.
SHEET_BG = (41, 88, 124)


def to_rgb(vec):
    """Байт палитры Вектора -> приблизительный 24-бит RGB (для расстояний)."""
    r = (vec & 7) * 255 // 7
    g = ((vec >> 3) & 7) * 255 // 7
    b = ((vec >> 6) & 3) * 255 // 3
    return (r, g, b)


PAL_RGB = [to_rgb(v) for v in PALETTE]


def quantize(rgb):
    """24-бит RGB -> ближайший индекс палитры (по евклидову расстоянию)."""
    best, bestd = 0, 1 << 30
    for i, (pr, pg, pb) in enumerate(PAL_RGB):
        d = (rgb[0] - pr) ** 2 + (rgb[1] - pg) ** 2 + (rgb[2] - pb) ** 2
        if d < bestd:
            best, bestd = i, d
    return best


# ---------------------------------------------------------------------------
# Уровень: тайлсет + тайлкарта
# ---------------------------------------------------------------------------

def build_level():
    im = Image.open(os.path.join(SRC, "tiles.png")).convert("RGB")
    W, H = im.size
    px = im.load()
    cols = W // TILE
    rows = BAND_H // TILE
    band_bottom = min(BAND_TOP + BAND_H, H)

    tileset = []          # список 32-байтных тайлов
    tilemap_index = {}    # bytes -> индекс

    def tile_at(cx, cy):
        """cx,cy — координаты тайла. Вернуть 32-байтное представление."""
        planes = [bytearray(TILE) for _ in range(4)]   # вес 8,4,2,1
        for r in range(TILE):
            y = BAND_TOP + cy * TILE + r
            b8 = b4 = b2 = b1 = 0
            for c in range(TILE):
                x = cx * TILE + c
                idx = quantize(px[x, y]) if y < band_bottom else 0
                bit = 7 - c
                if idx & 8: b8 |= 1 << bit
                if idx & 4: b4 |= 1 << bit
                if idx & 2: b2 |= 1 << bit
                if idx & 1: b1 |= 1 << bit
            planes[0][r] = b8
            planes[1][r] = b4
            planes[2][r] = b2
            planes[3][r] = b1
        return bytes(planes[0] + planes[1] + planes[2] + planes[3])

    # Тайлкарта храним колонками: tilemap[col*rows + row]
    tilemap = bytearray(cols * rows)
    for cx in range(cols):
        for cy in range(rows):
            data = tile_at(cx, cy)
            ti = tilemap_index.get(data)
            if ti is None:
                ti = len(tileset)
                tilemap_index[data] = ti
                tileset.append(data)
            tilemap[cx * rows + cy] = ti

    print(f"level: {cols}x{rows} тайлов ({W}x{BAND_H} px), "
          f"уникальных тайлов: {len(tileset)}")
    return cols, rows, tileset, bytes(tilemap)


# ---------------------------------------------------------------------------
# Спрайты Small Mario: 16x16 с маской, вправо и зеркально влево
# ---------------------------------------------------------------------------

# Ячейки в строке "Small Mario": x = 1 + 18*i, строки 16..31 (16 px).
MARIO_ROW_TOP = 16
MARIO_CELL_X0 = 1
MARIO_CELL_PITCH = 18
MARIO_CELL_W = 16

# Имена и номера ячеек (всё смотрит вправо; влево — зеркало).
FRAMES = {
    "stand": 0,
    "walk0": 1,
    "walk1": 2,
    "walk2": 3,
    "skid":  7,
    "jump":  8,
    "duck":  9,
}


def _near(p, key, tol=12):
    return abs(p[0] - key[0]) < tol and abs(p[1] - key[1]) < tol \
        and abs(p[2] - key[2]) < tol


def extract_cell(px, cell):
    """Вернуть grid[16][16] индексов палитры, либо None для прозрачного.

    Прозрачность — по цвету фона ВНУТРИ ячейки (угловой пиксель), а не по
    внешнему полю листа: фоны ячеек этого листа — (68,145,190), тогда как
    внешнее поле — (41,88,124). Сравниваем с обоими, чтобы надёжно.
    """
    x0 = MARIO_CELL_X0 + MARIO_CELL_PITCH * cell
    key = px[x0, MARIO_ROW_TOP]     # фон ячейки в левом верхнем углу
    grid = []
    for r in range(MARIO_CELL_W):
        y = MARIO_ROW_TOP + r
        row = []
        for c in range(MARIO_CELL_W):
            p = px[x0 + c, y]
            if _near(p, key) or _near(p, SHEET_BG):
                row.append(None)          # прозрачный пиксель
            else:
                row.append(quantize(p))
        grid.append(row)
    return grid


def grid_to_sprite(grid, mirror=False):
    """grid[16][16] -> 160 байт: mask(32) + 4 плоскости по 32, колонками."""
    if mirror:
        grid = [list(reversed(row)) for row in grid]
    mask = bytearray(32)
    planes = [bytearray(32) for _ in range(4)]   # вес 8,4,2,1
    # колонка-major: col0 строки 0..15, затем col1 строки 0..15
    for c in range(2):
        for r in range(16):
            off = c * 16 + r
            mb = p8 = p4 = p2 = p1 = 0
            for b in range(8):
                x = c * 8 + b
                bit = 7 - b
                idx = grid[r][x]
                if idx is None:
                    continue
                mb |= 1 << bit
                if idx & 8: p8 |= 1 << bit
                if idx & 4: p4 |= 1 << bit
                if idx & 2: p2 |= 1 << bit
                if idx & 1: p1 |= 1 << bit
            mask[off] = mb
            planes[0][off] = p8
            planes[1][off] = p4
            planes[2][off] = p2
            planes[3][off] = p1
    return bytes(mask + planes[0] + planes[1] + planes[2] + planes[3])


def build_sprites():
    im = Image.open(os.path.join(SRC, "sprites.png")).convert("RGB")
    px = im.load()
    out = {}
    for name, cell in FRAMES.items():
        grid = extract_cell(px, cell)
        out[name + "_r"] = grid_to_sprite(grid, mirror=False)
        out[name + "_l"] = grid_to_sprite(grid, mirror=True)
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


def write_level(cols, rows, tileset, tilemap):
    path = os.path.join(SRC, "level.inc")
    with open(path, "w") as f:
        f.write("/* Автоген: tools/gen_assets.py из tiles.png. Не править руками. */\n\n")
        f.write(f"#define LEVEL_COLS   {cols}\n")
        f.write(f"#define LEVEL_ROWS   {rows}\n")
        f.write(f"#define LEVEL_TILE_W {cols*TILE}\n")
        f.write(f"#define LEVEL_TILE_H {rows*TILE}\n")
        f.write(f"#define TILESET_N    {len(tileset)}\n\n")
        fmt_array(f, "level_palette", bytes(PALETTE))
        joined = b"".join(tileset)
        fmt_array(f, "tileset", joined)
        fmt_array(f, "tilemap", tilemap)
    print(f"wrote {path} ({os.path.getsize(path)} bytes)")


def write_sprites(sprites):
    path = os.path.join(SRC, "mario.inc")
    order = []
    for name in FRAMES:
        order.append((name + "_r", sprites[name + "_r"]))
        order.append((name + "_l", sprites[name + "_l"]))
    with open(path, "w") as f:
        f.write("/* Автоген: tools/gen_assets.py из sprites.png. Не править руками. */\n")
        f.write("/* Спрайт 16x16: mask[32] + 4 плоскости (вес 8,4,2,1) по 32, колонками. */\n\n")
        f.write("#define MARIO_W 16\n#define MARIO_H 16\n\n")
        for nm, data in order:
            fmt_array(f, "mario_" + nm, data)
    print(f"wrote {path} ({os.path.getsize(path)} bytes)")


def main():
    cols, rows, tileset, tilemap = build_level()
    sprites = build_sprites()
    write_level(cols, rows, tileset, tilemap)
    write_sprites(sprites)


if __name__ == "__main__":
    main()
