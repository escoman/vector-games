#!/usr/bin/env python3
"""gen_assets.py — ассеты демки Mario double-buffering (Вектор-06Ц).

Источник: assets/raccoon_mario.png — лист поз енота-Марио (все влево), нарезанный
автором; сверху встроено имя «Raccoon Mario», внизу запечены ID поз 01..21.
Берём первые 8 поз (они же 8 фаз из raccoon_mario.txt), каждая ~24x46 px.
Результат — include/sprites.inc и include/tiles.inc (подключаемые данные сборки).

Экран демки — 256x256x16, но на каждый буфер (пару плоскостей) приходится
4 цвета: логический индекс пикселя 0..3. Палитра сконцентрирована на Марио
(у него 3 цвета: красный, розовый, чёрный), четвёртый — цвет неба:

    лог.0 = голубой (небо/фон; для спрайта = прозрачность)
    лог.1 = красный (комбинезон/кепка)
    лог.2 = розовый (лицо/перчатки; текст)
    лог.3 = чёрный  (контур/обувь)

Форматы, которые печатает этот генератор (читает их main.c):

  спрайт (16 шт: 8 фаз × {лево, право}) — тайл-ПРЕФАБ:
    [0]=wcells [1]=hcells [2]=hpix=32 [3]=nTiles,
    затем nTiles записей: [pos] + 8 троек (opaque,b0,b1).
    pos = (col << 2) | row, где col=0..wcells-1, row=0..hcells-1 — координата
    непустого тайла 8x8. Тайл хранится ТОЛЬКО если в нём хоть один пиксель
    непрозрачен (есть op!=0); полностью пустые тайлы вырезаны.
    Бит 7 = ЛЕВЫЙ пиксель клетки (как в VRAM Вектора). opaque — маска ненулевых
    (непрозрачных) пикселей; b0/b1 — плоскости веса 1 и веса 2 логического цвета.
    Право — зеркало лева (реверс побитово в байте + реверс порядка клеток).

  тайл земли (1 шт, 8x8, без прозрачности):
    8 пар (b0,b1) — по байту на строку каждой из двух плоскостей.

    python3 tools/gen_assets.py
"""
import os
import glob
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
ASSETS = os.path.join(ROOT, 'assets')    # сырьё: лист поз png
OUT = os.path.join(ROOT, 'include')      # результат: данные для сборки
SHEET = os.path.join(ASSETS, 'raccoon_mario.png')
# Тайл-донор поверхности — из соседней демки mario-8cols.
DONOR_TILES = os.path.abspath(os.path.join(
    HERE, '..', '..', 'mario-8cols', 'src', 'tiles'))

# Полоса тел поз: y=20..51 (32 px = 4 клетки). Выше (y<20) — встроенное имя
# «Raccoon Mario», в зазоре y=52..57 пусто, ниже (y>=58) — запечённые ID поз.
# Одна и та же вертикальная рамка для всех поз => стопы на ряду 51, без джитжа.
BAND_TOP, BAND_BOT = 20, 51
N_POSES = 21               # всего поз на листе
MAIN_POSES = 8             # поз основной анимации (01-08)
TURN_IDS = [17, 18]        # 0-based индексы поз поворота (18, 19 на листе)
RUN_IDS = [10, 11, 12]     # 0-based индексы поз бега (11, 12, 13 на листе)
CELL = 8
HCELLS = 4                 # 32 px по высоте
HPX = HCELLS * CELL

# 4 цвета экрана: (R,G,B) r,g=0..7 b=0..3 и байт порта V06_RGB = (b<<6)|(g<<3)|r.
PAL = [
    ((3, 5, 3), None),     # 0 голубой — небо/фон (для спрайта = прозрачность)
    ((7, 0, 0), None),     # 1 красный
    ((7, 6, 3), None),     # 2 розовый
    ((0, 0, 0), None),     # 3 чёрный
]


def vec(rgb):
    r, g, b = rgb
    return (b << 6) | (g << 3) | r


PAL_RGB = [p[0] for p in PAL]
PAL_VEC = [vec(c) for c in PAL_RGB]
# 3-битные цвета палитры в 8-битный масштаб для честного сравнения с источником.
PAL_255 = [(r * 36, g * 36, b * 85) for (r, g, b) in PAL_RGB]

# Индексы PNG, которые НЕ относятся к Марио -> прозрачность (лог. 0):
#   0 = (41,88,124) тёмно-синий фон листа (зазоры между позами)
#   2 = (68,145,190) голубая прозрачная канва вокруг самого спрайта
#  13 = (192,223,255) светло-голубой (в позах не встречается, на всякий случай)
# Сам Марио в позах: 3=персик(лицо), 4=чёрный(контур), 6=красный(костюм).
TRANSPARENT_IDX = {0, 2, 13}


def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def quant(rgb):
    """Ближайший логический цвет 1..3 (0 — резерв под прозрачность)."""
    best, bi = 1e9, 1
    for i in (1, 2, 3):
        d = dist2(rgb, PAL_255[i])
        if d < best:
            best, bi = d, i
    return bi


def encode_cell(logical_rows):
    """logical_rows: список строк по 8 логических цветов (0..3).
    -> список троек (opaque,b0,b1), по одной на строку."""
    out = []
    for row in logical_rows:
        op = b0 = b1 = 0
        for k, c in enumerate(row):          # k=0 левый пиксель -> бит 7
            bit = 0x80 >> k
            if c != 0:
                op |= bit
                if c & 1:
                    b0 |= bit
                if c & 2:
                    b1 |= bit
        out.append((op, b0, b1))
    return out


def mirror_trip(cols):
    """Зеркало набора столбцов троек: реверс порядка клеток + побитовый реверс."""
    def revbyte(x):
        y = 0
        for i in range(8):
            if x & (1 << i):
                y |= 0x80 >> i
        return y
    return [[(revbyte(op), revbyte(b0), revbyte(b1)) for (op, b0, b1) in col]
            for col in reversed(cols)]


def shift_trip(trips):
    """Сдвиг на +4 px вправо — PREBAKE суб-пиксельного варианта.

    Выводной байт клетки c = high nibble <- low nibble клетки c-1
    (prev), low nibble <- high nibble клетки c (cur) — ровно то, что
    делал макрос SBYTE в render.asm во время вывода. Применяем к каждой
    из трёх компонент (op, b0, b1) независимо. Выход на 1 клетку шире
    (wcells+1): слева prev=zcol (нулi), справа для spill-колонки cur=zcol.

    Это даёт готовый префаб для dr_tile (быстрый путь), frac=4 на рантайме
    больше не нужен; весь draw идёт одним тяжьёным циклом dr_p0/dr_p1.
    """
    wc = len(trips)
    assert all(len(t) == HPX for t in trips)
    zero = [(0, 0, 0)] * HPX
    out = []
    for c in range(wc + 1):
        prev = trips[c - 1] if c - 1 >= 0 else zero
        cur = trips[c] if c < wc else zero
        col = []
        for r in range(HPX):
            op_p, b0_p, b1_p = prev[r]
            op_c, b0_c, b1_c = cur[r]
            op = ((op_p << 4) & 0xF0) | (op_c >> 4)
            b0 = ((b0_p << 4) & 0xF0) | (b0_c >> 4)
            b1 = ((b1_p << 4) & 0xF0) | (b1_c >> 4)
            col.append((op, b0, b1))
        out.append(col)
    return out


def seg_poses(px, w):
    """Старты колонок поз в полосе BAND_TOP..BAND_BOT (фон = индекс 0)."""
    def col_solid(x):
        return any(px[x, y] != 0 for y in range(BAND_TOP, BAND_BOT + 1))
    runs, start = [], None
    for x in range(w):
        if col_solid(x) and start is None:
            start = x
        elif not col_solid(x) and start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, w - 1))
    return runs[:N_POSES]


def emit_bytes(f, name, data):
    f.write('static const unsigned char %s[] = {\n' % name)
    for i in range(0, len(data), 12):
        f.write('    ' + ', '.join('0x%02X' % b for b in data[i:i + 12]) + ',\n')
    f.write('};\n\n')


def to_prefab(trips):
    """Колонки троек (по 32 строки) -> тайл-префаб: [wcells,hcells,hpix,nTiles]+
    записи [pos]+8 троек. Тайл (col,row) включается, только если в нём есть
    хоть один непрозрачный пиксель (какой-то op != 0). pos = (col<<2)|row."""
    wc = len(trips)
    recs = []
    for c in range(wc):
        col = trips[c]
        assert len(col) == HPX
        for t in range(HCELLS):
            rows = col[t * CELL:(t + 1) * CELL]        # 8 троек тайла 8x8
            if not any(op != 0 for (op, b0, b1) in rows):
                continue                                 # пустой тайл — вырезаем
            body = [b for (op, b0, b1) in rows for b in (op, b0, b1)]
            recs.append([(c << 2) | t] + body)           # 1 + 24 байта
    return [wc, HCELLS, HPX, len(recs)] + [b for r in recs for b in r]


def main():
    im = Image.open(SHEET)
    imrgb = im.convert('RGB')
    px = im.load()
    rgb = imrgb.load()
    w, h = im.size
    runs = seg_poses(px, w)
    assert len(runs) >= N_POSES, 'нашли %d поз, ожидали %d' % (len(runs), N_POSES)

    sprites = []            # (name, bytes)
    for pi in range(N_POSES):
        if pi >= MAIN_POSES and pi not in TURN_IDS and pi not in RUN_IDS:
            continue        # пропускаем ненужные позы
        x0, x1 = runs[pi]
        wpix = x1 - x0 + 1
        wcells = (wpix + CELL - 1) // CELL
        # логические цвета попиксельно в рамке wcells*8 × HPX; вертикаль —
        # абсолютная полоса BAND_TOP..BAND_BOT (общая для всех поз), горизонталь
        # — левый край позы прижат к колонке 0 (все позы смотрят влево).
        grid = [[0] * (wcells * CELL) for _ in range(HPX)]
        for sy in range(BAND_TOP, BAND_BOT + 1):
            for sx in range(x0, x1 + 1):
                idx = px[sx, sy]
                # фон листа И голубая канва спрайта -> прозрачность (лог. 0),
                # иначе канва квантовалась бы в розовый = «белые квадраты».
                c = 0 if idx in TRANSPARENT_IDX else quant(rgb[sx, sy])
                grid[sy - BAND_TOP][sx - x0] = c
        # кодируем тройки (opaque,b0,b1) в КОЛОНОЧНОМ порядке: для каждой
        # клетки-столбца — 32 пиксель-строки подряд (шаг 3 байта). Тогда
        # вывод в VRAM = линейный проход: data += 3, vram -= 1 (render.asm).
        # Лево — как в исходной позе; право — зеркало (реверс клеток + бит).
        trips = [encode_cell([grid[r][c * CELL:(c + 1) * CELL]
                              for r in range(HPX)])
                 for c in range(wcells)]
        assert all(len(t) == HPX for t in trips)
        # Пакуем в тайл-префаб: только непустые 8x8-тайлы. Лево — как в позе,
        # право — зеркало (реверс клеток + бит), уже по готовым колонкам троек.
        # Суб-пиксельный сдвиг +4 px считается НА РАНТАЙМЕ (render.asm,
        # SBYTE-стейджинг при rs_frac=4), поэтому отдельный _sh-префаб не
        # печатаем — экономим ~половину ROM на спрайтах Марио.
        sprites.append(('mario%d_l' % (pi + 1), to_prefab(trips)))
        sprites.append(('mario%d_r' % (pi + 1), to_prefab(mirror_trip(trips))))

    # ---- тайл земли: берём tile_001.png донора, квант в 4 цвета ----
    donor = os.path.join(DONOR_TILES, 'tile_001.png')
    t = Image.open(donor).convert('RGB')
    tpx = t.load()
    tile = []
    for r in range(8):
        row = [quant(tpx[c, r]) for c in range(8)]
        op, b0, b1 = encode_cell([row])[0]
        tile += [b0, b1]

    # ---- запись include/sprites.inc ----
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'sprites.inc'), 'w') as f:
        f.write('/* автоген: tools/gen_assets.py — НЕ править руками */\n\n')
        f.write('#define MARIO_NPOSE   %d\n' % MAIN_POSES)
        f.write('#define MARIO_HCELLS  %d\n' % HCELLS)
        f.write('#define MARIO_HPIX    %d\n\n' % HPX)
        for name, data in sprites:
            emit_bytes(f, name, data)
        f.write('/* таблица указателей: [фаза][направление] 0=лево 1=право */\n')
        f.write('static const unsigned char * const mario_frames[MARIO_NPOSE][2] = {\n')
        for pi in range(MAIN_POSES):
            f.write('    { mario%d_l, mario%d_r },\n' % (pi + 1, pi + 1))
        f.write('};\n\n')
        # Turn poses: stored separately, not indexed by facing
        f.write('/* поворот: [шаг 0..1][направление] 0=лево 1=право */\n')
        f.write('static const unsigned char * const mario_turn[2][2] = {\n')
        for ti, pi in enumerate(TURN_IDS):
            f.write('    { mario%d_l, mario%d_r },\n' % (pi + 1, pi + 1))
        f.write('};\n\n')
        # Run poses
        f.write('/* бег: [фаза 0..2][направление] 0=лево 1=право */\n')
        f.write('static const unsigned char * const mario_run[3][2] = {\n')
        for ri, pi in enumerate(RUN_IDS):
            f.write('    { mario%d_l, mario%d_r },\n' % (pi + 1, pi + 1))
        f.write('};\n')

    # ---- запись include/tiles.inc (палитра + тайл) ----
    # Тайл 8x8 = 16 байт; повторяем 4 раза (64 байта), чтобы asm-цикл
    # fg_run (32 ряда, шаг 2) читал из валидных данных без wrap-логики.
    tile_rep = tile * 4
    with open(os.path.join(OUT, 'tiles.inc'), 'w') as f:
        f.write('/* автоген: tools/gen_assets.py — НЕ править руками */\n\n')
        f.write('/* 4 цвета экрана: 0=голубой(небо), 1=красный, 2=розовый, 3=чёрный */\n')
        f.write('static const unsigned char screen_pal4[4] = {\n    %s\n};\n\n'
                % ', '.join('0x%02X' % v for v in PAL_VEC))
        f.write('/* тайл земли 8x8, x4 повтора = 32 ряда для fg_run */\n')
        emit_bytes(f, 'tile_ground', tile_rep)

    print('OK: %d спрайтов (фаз×2), тайл земли %d байт' % (len(sprites), len(tile)))
    print('палитра V06_RGB:', ['0x%02X' % v for v in PAL_VEC])


if __name__ == '__main__':
    main()
