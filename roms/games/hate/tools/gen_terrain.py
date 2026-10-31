"""Собрать рельеф меню (жёлтую ленту ландшафта) в include/terrain.inc.

Вход — дампы из assets/ (см. tools/extract_terrain.py):

  ring_8000.bin    — кольцо $8000-$BFFF, полная сцена без оверлеев;
  terrain_mask.bin — off(0) и окно вывода (ktop, kbot) по 32 столбцам.

Модель (ENGINE.MD §3.7): столбец экрана x — непрерывный кусок кольца

    scr(x, y) = ring[(off(x) + 191 - y) mod $4000],   off(x+1) = off(x) + $1FC.

Читается СНИЗУ ВВЕРХ: байт n = 191-y — строка y, поэтому клетка k (строки
8k..8k+7) — это 8 байт ring[off + 8*(23-k) .. +7], байт j = строка 8k+7-j.
Всё это уже проверено побайтово на кадре ZX (§ Stage 3 в TZ).

ОКНО, А НЕ ВЕСЬ СТОЛБЕЦ. Рисуются только клетки из лесенки $D5B2 (ENGINE.MD
§3.5): от ktop(x) до kbot(x). Раньше рисовались все 24 клетки столбца, и
«лишние» полосы давали в кадре три ленты мусора вместо одной ленты ландшафта.
Внутри окна картинка непрерывна — тёмная диагональная полоса между дальней и
ближней частью дороги принадлежит самой сцене (это байты 0 в кольце).

СТРОКИ 192..255 — ЧЁРНЫЕ. Экран Вектора — 256 строк, ZX — 192, поэтому на ZX
нижняя часть картинки обрезана кромкой. Продолжения сцены в кольце нет: байты
ПЕРЕД окном столбца (n = -1, -2, …) принадлежат предыдущему столбцу и другой
фазе прокрутки — попытка продлить окно вниз давала в кадре вторую, дублирующую
ленту рельефа со швом. Поэтому окно берётся ровно как в оригинале ($D5B2), а
низ экрана остаётся чёрным (там же зона панели меню).

ЦВЕТ. На кадре меню весь рельеф — жёлтая бумага по чёрному (атрибут ZX 6/0,
TZ §3.3). Жёлтый = логический цвет 1 = плоскость веса 1 (0xE000), значит в
плоскости веса 2 (0xC000) лента не пишет НИЧЕГО: там 0. Поэтому данные — это
просто байты кольца и один поток указателей (раньше было два: 00/FF/паттерн/
~паттерн под запечённый цвет). Плоскость 0xC000 заранее зачищается в main.c.

    python3 tools/gen_terrain.py [--preview]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.dirname(HERE)
ASSETS = os.path.join(PORT, 'assets')
OUT = os.path.join(PORT, 'include', 'terrain.inc')
PREVIEW = os.path.join(PORT, 'assets', 'terrain_preview.png')

RING = os.path.join(ASSETS, 'ring_8000.bin')
MASK = os.path.join(ASSETS, 'terrain_mask.bin')

COLS = 32             # байтовых столбцов экрана
ZX_CELLS = 24         # клеток по 8 строк в столбце ZX (192 строки)
STEP = 0x1FC          # шаг кольца на столбец (две страницы назад, -4 байта)
RING_LEN = 0x4000

# Палитра буфера (4 цвета, порядок = логический номер): земля меню жёлтая.
# Байт цвета Вектора — RRRGGGBB (см. V06_RGB в lib/v06.h):
#   (b << 6) | (g << 3) | r.
PAL4 = [
    (0x00, 'чёрный  — фон (paper ZX 0)'),
    (0x3F, 'жёлтый  — рельеф (ink ZX 6)'),
    (0xFF, 'белый   — ink ZX 7'),
    (0x07, 'красный — ink ZX 1/2/3'),
]
TERRAIN_COLOUR = 1    # логический цвет рельефа: жёлтый = бит 0 = 0xE000


def load():
    ring = open(RING, 'rb').read()
    mask = open(MASK, 'rb').read()
    assert len(ring) == RING_LEN, 'ring_8000.bin: ожидалось 16384 Б'
    assert len(mask) == 2 + 2 * COLS, 'terrain_mask.bin: ожидалось 66 Б'
    off0 = mask[0] | (mask[1] << 8)
    rows = [(mask[2 + 2 * x], mask[3 + 2 * x]) for x in range(COLS)]
    return ring, off0, rows


def ring_cell(ring, o, k):
    """8 байт клетки k (сверху вниз) столбца, стартующего со смещения o.

    Столбец кольца идёт СНИЗУ ВВЕРХ (n = 191-y): байт n — это строка
    y = 191-n, значит клетка k = строки 8k..8k+7 лежит в байтах
    o + 8*(23-k) .. o + 8*(23-k)+7, где байт j — строка 8k+7-j (верх
    клетки внутри блока последний). Для k > 23 смещение уходит в минус,
    т.е. попадает в предыдущий столбец кольца, — это НЕ продолжение сцены.
    """
    base = o + 8 * (ZX_CELLS - 1 - k)
    return bytes(ring[(base + j) & 0x3FFF] for j in range(8))


def build(ring, off0, rows):
    """Столбцы -> (словарь блоков, поток кодов, геометрия)."""
    cells = []          # блоки клеток всех столбцов, по столбцам
    geom = []           # (смещение старта в байтах столбца, клеток)
    for x in range(COLS):
        o = (off0 + STEP * x) & 0x3FFF
        ktop, kbot = rows[x]
        count = kbot - ktop + 1
        # Позиция s потока ложится в VRAM по адресу base + x*256 + start + 8s,
        # а байт строки y — по 255 - y; нижняя клетка kbot начинается со
        # строки 8*kbot, т.е. с байта 255 - (8*kbot + 7) = 248 - 8*kbot.
        start = 248 - 8 * kbot
        assert 0 <= start and start + 8 * count <= 256, \
            'столбец %d: старт %d + %d клеток не влезает в 256 Б' % (x, start, count)
        geom.append((start, count))
        # поток идёт СНИЗУ ВВЕРХ: клетки kbot, kbot-1, ..., ktop
        cells += [ring_cell(ring, o, k) for k in range(kbot, ktop - 1, -1)]

    freq = {}
    for b in cells:
        freq[b] = freq.get(b, 0) + 1
    table = sorted(freq, key=lambda b: (-freq[b], b))
    index = {b: i for i, b in enumerate(table)}
    return table, [index[b] for b in cells], geom


def emit(table, codes, geom):
    lines = []
    w = lines.append
    w('; terrain.inc — рельеф меню H.A.T.E. для Вектора-06Ц.')
    w(';')
    w('; Сгенерировано tools/gen_terrain.py из assets/ring_8000.bin и')
    w('; assets/terrain_mask.bin — руками не правится; включается из render.asm.')
    w(';')
    w('; Столбец экрана x читается из кольца $8000-$BFFF со смещением')
    w('; off(x) = off(0) + $1FC*x, СНИЗУ ВВЕРХ: байт n = строка 191-n.')
    w('; Рисуются только клетки окна ktop(x)..kbot(x) из лесенки $D5B2')
    w('; (ENGINE.MD §3.5) — ровно как в оригинале: в кольце нет продолжения')
    w('; сцены ниже 192-й строки (байты перед окном — предыдущий столбец),')
    w('; поэтому строки 192..255 экрана Вектора остаются чёрными.')
    w(';')
    w('; Весь рельеф — жёлтый (логический цвет 1) = плоскость веса 1 (0xE000).')
    w('; В плоскости веса 2 (0xC000) лента не пишет ничего, поэтому поток')
    w('; указателей один; блок = просто 8 байт кольца.')
    w(';')
    w('; terrain_pat  — словарь %d готовых блоков по 8 байт;' % len(table))
    w('; terrain_c1   — %d указателей на блоки в порядке вывода;' % len(codes))
    w('; terrain_geom — 32 пары (старт, клеток): старт — смещение байта нижней')
    w(';                клетки столбца в его 256-байтовой колонке VRAM;')
    w('; terrain_cols — число столбцов (32);')
    w('; terrain_pal4 — палитра буфера: 0 чёрный, 1 жёлтый, 2 белый, 3 красный')
    w(';                (слот = логический цвет);')
    w(';                _terrain_pal4 — тот же адрес для C (sccz80: _).')
    w('')
    w('SECTION rodata_user')
    w('')
    w('PUBLIC terrain_pat')
    w('PUBLIC terrain_c1')
    w('PUBLIC terrain_geom')
    w('PUBLIC terrain_pal4')
    w('PUBLIC _terrain_pal4')
    w('PUBLIC terrain_cols')
    w('')
    w('terrain_cols:           defb %d' % COLS)
    w('')
    w('_terrain_pal4:')
    w('terrain_pal4:')
    for i, (p, why) in enumerate(PAL4):
        w('    defb 0x%02X                 ; %d: %s' % (p, i, why))
    w('')
    w('terrain_pat:')
    freq = [0] * len(table)
    for c in codes:
        freq[c] += 1
    for i, cell in enumerate(table):
        w('    defb %s            ; блок %d (%d шт.)'
          % (', '.join('0x%02X' % b for b in cell), i, freq[i]))
    w('')
    w('; Геометрия: (старт байта нижней клетки, число клеток) по столбцам.')
    w('terrain_geom:')
    for x in range(COLS):
        start, count = geom[x]
        w('    defb %#04x, %2d            ; x=%d: строки %d..%d'
          % (start, count, x, 256 - start - 8 * count, 255 - start))
    w('')
    w('terrain_c1:')
    pos = 0
    for x in range(COLS):
        col = codes[pos:pos + geom[x][1]]
        pos += geom[x][1]
        for part in range(0, len(col), 4):
            row = col[part:part + 4]
            w('    defw %s%s' % (', '.join('terrain_pat + %d' % (8 * c) for c in row),
                                 '                    ; x=%d' % x
                                 if part == 0 else ''))
    with open(OUT, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def preview(table, codes, geom):
    """Собрать картинку обратно из словаря и потока (сверка глазами)."""
    from PIL import Image
    FIX = [(0, 0, 0), (224, 224, 0), (224, 224, 192), (224, 0, 0)]
    img = Image.new('RGB', (256, 256), (0, 0, 0))
    pos = 0
    for x in range(COLS):
        start, count = geom[x]
        for s in range(count):
            block = table[codes[pos]]
            pos += 1
            y0 = 255 - (start + 8 * s) - 7      # верхняя строка клетки
            for j in range(8):
                y = y0 + 7 - j                  # байт j — строка y0+7-j
                for bit in range(8):
                    on = (block[j] >> (7 - bit)) & 1
                    img.putpixel((x * 8 + bit, y), FIX[TERRAIN_COLOUR if on else 0])
    img.resize((512, 512), Image.NEAREST).save(PREVIEW)


def main():
    ring, off0, rows = load()
    table, codes, geom = build(ring, off0, rows)
    emit(table, codes, geom)
    print('off(0) = $%04X; клеток %d в %d блоках' % (off0, len(codes), len(table)))
    print('ROM: словарь %d Б + поток %d Б + геометрия %d Б = %d Б'
          % (len(table) * 8, 2 * len(codes), 2 * COLS,
             len(table) * 8 + 2 * len(codes) + 2 * COLS))
    print('окно по столбцам (строки): %s'
          % ' '.join('%d-%d' % (248 - g[0] - 8 * g[1] + 8, 248 - g[0] + 7) for g in geom))
    print('->', os.path.relpath(OUT, PORT))
    if '--preview' in sys.argv:
        preview(table, codes, geom)
        print('->', os.path.relpath(PREVIEW, PORT))


if __name__ == '__main__':
    main()
