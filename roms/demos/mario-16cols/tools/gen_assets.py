#!/usr/bin/env python3
"""
gen_assets.py — ассеты демки Mario 16-цвет для Вектора-06Ц.

Читает src/tiles.png (карта уровня SMB 1-1), src/tiles.json (твёрдость тайлов,
вариант C) и src/mario.png (лента из 18 спрайтов Small Mario), квантует
всё в ОДНУ общую 16-цветную палитру Вектора и пишет:

  src/level.inc   — палитра, тайлсет 8x8 (4 плоскости), тайлкарта уровня,
                    tile_nz (карта непустых плоскостей тайла), pair_top
                    (верхняя «грязная» строка пары соседних колонок) и таблицу
                    твёрдости tile_solid[тайл] (см. load_tile_solid);
  src/mario.inc   — спрайты Small Mario 16x16 с маской (вправо/влево).

Формат Вектора (256x256, 16 цветов, 4 битовые плоскости):
  плоскость вес 8 -> 0x8000, вес 4 -> 0xA000, вес 2 -> 0xC000, вес 1 -> 0xE000;
  внутри плоскости блок = x/8 (256 байт), байт i хранит строку y = 255 - i
  (строки сверху вниз идут по УБЫВАЮЩЕМУ адресу), старший бит = левый пиксель.

Тайл 8x8: 4 плоскости по 8 байт (строки 0..7 сверху вниз), порядок плоскостей
вес 8,4,2,1. Итого 32 байта на тайл.

Тайлкарта: tilemap[col*ROWS + row] — индекс тайла; колонками, чтобы экранный
блок (столбец из 8 пикселей, 32 тайла по высоте) читался 32 подряд идущими
байтами. Тайл 0 — пустой (чистое небо = индекс 0), он никогда не пишется в VRAM.

Спрайт 16x16: 8 прогонов (плоскость x колонка блока) по 16 пар (keep, set);
res = (old & keep) ^ set. Прозрачность = keep 0xFF, set 0x00 -> байт не трогаем.
Итого 256 байт.
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
GROUND_ROWS = 2         # нижние строки тайлкарты — полоска земли (не «небо»)
VEC_BYTES = 0x8000      # размер видеопамяти (для проверки)

# ---- Общая палитра: индекс -> байт порта 0C (RRRGGGBB) ----------------------
# НЕБО = ИНДЕКС 0. Это главное требование раскладки: тайл, целиком состоящий из
# неба, становится нулевым (все 4 плоскости = 0x00), поэтому:
#   * индекс 0 зарезервирован под пустой тайл (см. build_level),
#   * sky-области не рисуются вообще (gfx_clear(0) их уже залил),
#   * при скролле сравнение старых/новых тайлов даёт пропуск целых ячеек.
#
# Порядок остальных индексов подобран перебором (8! раскладок) по числу VRAM-
# записей на шаг скролла: одиночные биты (1,2,4,8) отданы самым частым цветам —
# чёрному контуру, коричневой земле, тёмно-зелёному и белому (облака). Такая
# раскладка даёт 2835 записей/шаг против 3877 у «просто поменять местами 0 и 3».
PALETTE = [
    0xFD,   # 0  небо        (ФОН: пустой тайл, не рисуется)
    0x00,   # 1  чёрный      (контур, ямы)          бит 1
    0xB7,   # 2  коричневый  (земля)                бит 2
    0x67,   # 3  оранжевый   (кирпич)         биты 1+2
    0x2A,   # 4  зелёный тёмный                    бит 4
    0x73,   # 5  зелёный светлый (кусты/трубы) биты 1+4
    0x0D,   # 6  красный     (Марио: кепка/штаны) биты 2+4
    0xF7,   # 7  кожа        (Марио: лицо/руки) биты 1+2+4
    0xFF,   # 8  белый       (облака/цифры)    бит 8
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

    # Тайл 0 ЗАРЕЗЕРВИРОВАН под пустой (чистое небо = индекс 0 = все плоскости 0).
    # Он никогда не записывается в VRAM, а render_window использует его как
    # эталон при первой отрисовке экрана.
    tileset = [bytes(TILE * 4)]
    tilemap_index = {bytes(TILE * 4): 0}

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

    # tile_nz[t] — 4-битная карта НЕПУСТЫХ плоскостей тайла (бит p = 1, если в
    # плоскости p есть хотя бы один ненулевой байт). render_window не трогает
    # плоскость, если она пуста и в старом, и в новом тайле: писать нечего.
    tile_nz = bytearray()
    for t in tileset:
        m = 0
        for p in range(4):
            if any(t[p * TILE + r] for r in range(TILE)):
                m |= 1 << p
        tile_nz.append(m)

    # --- Матовая зона канваса ------------------------------------------------
    # Холст tiles.png за нарисованным уровнем — чистый (0,0,0), quantize даёт
    # ему индекс 1 = ЧЁРНЫЙ, и пустота за замком скроллится как чёрная стена
    # (плюс чёрная полоса-артефакт от склейки картинки на верхнем крае полосы).
    # Небо обязано быть индексом 0, поэтому обесцвечиваем его обратно:
    # tile_nz == 0x08 означает «в тайле непустая только плоскость веса 1»,
    # то есть пиксели либо небо (0), либо чёрный (1) — других цветов нет.
    # Идём строго от row 0 и останавливаемся на первом тайле с другим цветом:
    # пустой тайл дырку в матовке не пробивает, иначе съелись бы чёрные ямы
    # в земле (они как раз состоят из того же тайла, но начинаются не сверху).
    matte = 0
    for cx in range(cols):
        base = cx * rows
        cy = 0
        while cy < rows and tilemap[base + cy] and tile_nz[tilemap[base + cy]] == 0x08:
            tilemap[base + cy] = 0
            matte += 1
            cy += 1
        # Первая колонка, где матовка легла от верха до самой земли, — это край
        # арта: дальше только канвас и дорисованная «в холостую» полоска земли.
        if cy >= rows - GROUND_ROWS and cx < cols - 1:
            cols = cx
            tilemap = tilemap[:cols * rows]
            print(f"level: арт кончается на колонке {cols}, остальное срезано "
                  f"(MAX_CAM в main.c считает камеру отсюда)")
            break
    print(f"level: матовка канваса -> небо в {matte} ячейках тайлкарты")

    # pair_top[c] = min(col_top[c], col_top[c+1]) — самая верхняя строка, где в
    # паре соседних колонок вообще есть содержимое. Строки выше гарантированно
    # пусты обе -> сравнение там можно не начинать (экономия ~30 kT на шаг).
    def col_top(cx):
        for cy in range(rows):
            if tilemap[cx * rows + cy]:
                return cy
        return rows

    pair_top = bytearray(min(col_top(cx), col_top(cx + 1)) for cx in range(cols - 1))

    print(f"level: {cols}x{rows} тайлов ({cols * TILE}x{BAND_H} px из {W}x{H}), "
          f"уникальных тайлов: {len(tileset)}, пустой тайл = 0")
    return cols, rows, tileset, bytes(tilemap), bytes(tile_nz), bytes(pair_top)


# ---------------------------------------------------------------------------
# Уровень из редакторских файлов: src/level.json + src/tiles/*.png + tiles.json
# ---------------------------------------------------------------------------
# Это источник истины для сборки ROM: раскладка из level.json, графика из
# tile-PNG, твёрдость из tiles.json. tiles.png служит только затравкой
# (tools/export_assets.py), ROM из него больше не строится.

def png_to_tile(path):
    """8x8 PNG -> 32-байтный тайл (4 плоскости). Точный обратный ход export."""
    im = Image.open(path).convert("RGB")
    px = im.load()
    planes = [bytearray(TILE) for _ in range(4)]      # вес 8,4,2,1
    for r in range(TILE):
        b8 = b4 = b2 = b1 = 0
        for c in range(TILE):
            idx = quantize(px[c, r])
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


def _compute_tile_nz(tileset):
    nz = bytearray()
    for t in tileset:
        m = 0
        for p in range(4):
            if any(t[p * TILE + r] for r in range(TILE)):
                m |= 1 << p
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
    tiles = sorted(tj["tiles"], key=lambda t: t["index"])
    tileset = []
    for i, t in enumerate(tiles):
        if int(t["index"]) != i:
            sys.exit(f"tiles.json: дыра/порядок индексов (ожидался {i})")
        tileset.append(png_to_tile(os.path.join(SRC, t["file"])))
    if tileset[0] != bytes(TILE * 4):
        sys.exit("tiles.json: тайл 0 должен быть пустым (небо)")
    tile_nz = _compute_tile_nz(tileset)
    pair_top = _compute_pair_top(cols, rows, tilemap)
    print(f"level(editor): {cols}x{rows}, тайлов в наборе: {len(tileset)}")
    return cols, rows, tileset, bytes(tilemap), bytes(tile_nz), bytes(pair_top)


# ---------------------------------------------------------------------------
# Коллизии: вариант C — твёрдость как СВОЙСТВО ТАЙЛА (src/tiles.json)
# ---------------------------------------------------------------------------
# Каждый тайл несёт битовую маску:
#   COLL_PLAT (1) — опора сверху: на него встают, но проходят сбоку/снизу
#                   (коробки, монетные блоки, поверхность земли).
#   COLL_WALL (2) — непроходимо: блокирует и горизонталь, и голову (трубы,
#                   кирпич, тело земли).
# Значение 3 = и то, и другое (земля/кирпич: сверху опора, по бокам стена).
# tiles.json редактируется в level-редакторе; tiles2.png больше НЕ нужен.

import json                                  # noqa: E402

COLL_PLAT, COLL_WALL = 1, 2


def load_tile_solid(n_tiles):
    """src/tiles.json -> bytes длины n_tiles, каждый = маска COLL_*.

    Индекс массива = индекс тайла в tileset (порядок задаёт build_level).
    """
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
# Спрайты Small Mario: 16x16 с маской, вправо и зеркально влево
# ---------------------------------------------------------------------------

# src/mario.png — лента из 18 спрайтов Small Mario 16x16, пронумерованы 1..18.
# Смысл каждого номера — в src/mario.txt. БАЗОВЫЕ СПРАЙТЫ СМОТРЯТ ВЛЕВО
# (кожа лица смещена влево; #08 «в камеру» и #17 «спиной» — симметричны).
# Значит _l рисуем как есть, _r — зеркалом.
MARIO_TOP = 14          # верх спрайтовой полосы (строки 14..29)
MARIO_PITCH = 18        # шаг ячейки по X
MARIO_X0 = 0            # левый край 16-px окна внутри ячейки
MARIO_SIZE = 16
# Прозрачны: фон ячейки (68,145,190) и поле листа (41,88,124).
MARIO_BG = [(68, 145, 190), (41, 88, 124)]

# Кадр анимации -> номер спрайта в mario.png (1..18). См. src/mario.txt.
# stand/walk0/walk2/duck сознательно указывают на одну ячейку #1: это один и
# тот же побайтово массив, write_sprites оставит от него ОДИН образ, а прочие
# имена сделает #define-алиасами (экономия ROM). skid (#7) в игру не выводится —
# не генерируем вовсе.
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
    """grid[16][16] индексов палитры, None — прозрачный. num = номер 1..18.

    Прозрачность — по двум фоновым цветам ленты (фон ячейки и поле листа);
    сам Марио (чёрный контур / красный / кожа) ни с одним не совпадает.
    """
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
                row.append(quantize(p))
        grid.append(row)
    return grid


def grid_to_sprite(grid, mirror=False):
    """grid[16][16] -> 256 байт: 8 прогонов по 16 пар (keep, set).

    Прогон = (плоскость p, колонка блока c), строки 0..15 сверху вниз; порядок
    прогонов p = 0..3 (веса 8,4,2,1), внутри него c = 0..1. Пара описывает ОДИН
    байт VRAM: res = (old & keep) ^ set, где keep = ~mask, set = plane & mask.

    Такой формат выбран под регистровый цикл 8080: за один шаг читается два
    соседних байта спрайта (HL++) и один байт VRAM (DE--), никаких третьих
    указателей не нужно. Порядок байт совпадает с порядком адресов VRAM:
    (база_плоскости[p] + blk + c) << 8 | (255 - y - r), т.е. адрес байта
    УБЫВАЕТ вместе со строкой.
    """
    if mirror:
        grid = [list(reversed(row)) for row in grid]
    out = bytearray(256)
    k = 0
    for w in (8, 4, 2, 1):              # плоскости вес 8,4,2,1
        for c in range(2):              # левая/правая колонка по 8 пикселей
            for r in range(16):         # строки сверху вниз
                mb = pb = 0
                for b in range(8):
                    bit = 7 - b
                    idx = grid[r][c * 8 + b]
                    if idx is None:
                        continue        # прозрачный пиксель
                    mb |= 1 << bit
                    if idx & w:
                        pb |= 1 << bit
                out[k] = mb ^ 0xFF      # keep: сбрасывает покрытые биты
                out[k + 1] = pb & mb    # set: выставляет биты спрайта
                k += 2
    return bytes(out)


def build_sprites():
    im = Image.open(os.path.join(SRC, "mario.png")).convert("RGB")
    px = im.load()
    out = {}
    for name, num in FRAMES.items():
        grid = extract_cell(px, num)
        # Базовый спрайт смотрит ВЛЕВО: _l — как есть, _r — зеркало.
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
        f.write("/* Автоген: tools/gen_assets.py из tiles.png/tiles.json. Не править руками. */\n\n")
        f.write(f"#define LEVEL_COLS   {cols}\n")
        f.write(f"#define LEVEL_ROWS   {rows}\n")
        f.write(f"#define LEVEL_TILE_W {cols*TILE}\n")
        f.write(f"#define LEVEL_TILE_H {rows*TILE}\n")
        f.write(f"#define TILESET_N    {len(tileset)}\n")
        f.write("#define TILE_EMPTY   0         /* чистое небо, все плоскости 0 */\n\n")
        fmt_array(f, "level_palette", bytes(PALETTE))
        joined = b"".join(tileset)
        fmt_array(f, "tileset", joined)
        fmt_array(f, "tilemap", tilemap)
        fmt_array(f, "tile_nz", tile_nz)      # карта непустых плоскостей на тайл
        fmt_array(f, "pair_top", pair_top)    # верхdiff'а на пару соседних колонок
        # Твёрдость как свойство тайла (вариант C). Индекс = тайл; биты COLL_*.
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
        f.write("/* Автоген: tools/gen_assets.py из mario.png. Не править руками. */\n")
        f.write("/* Спрайт 16x16: 8 прогонов (плоскость 8,4,2,1 x колонка 0,1) по 16 "
                "пар (keep,set). Дубликаты кадров — #define-алиасы одного образа. */\n\n")
        f.write("#define MARIO_W 16\n#define MARIO_H 16\n")
        f.write("#define MARIO_BYTES 256\n")
        f.write("#define MARIO_SNAP 128      /* снимок VRAM под спрайтом */\n\n")
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
