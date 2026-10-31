"""Собрать рельеф (жёлтый ландшафт меню) в include/terrain.inc.

Вход — дампы из assets/ (см. tools/extract_terrain.py):

  ring_8000.bin  — кольцо $8000-$BFFF, полная сцена без оверлеев;
  scr_4000.bin   — экран ZX (битмап + атрибуты).

Модель (ENGINE.MD §3.7): столбец экрана x — непрерывный кусок кольца

    scr(x, 191-n) = ring[(off(x) + n) mod $4000],   off(x+1) = off(x) + $1FC.

Отсюда каждый столбец — 24 клетки по 8 байт (192 строки), и вся картинка
кодируется как 32*24 ссылок на словарь уникальных 8-байтных клеток.
Смещение off(31) подбирается по кадру ZX (совпадение байтов столбца).

Цвет клетки — пара (чернила, бумага) из атрибутной плоскости ZX: блиттер
кладёт бит паттерна в цвет чернил, ноль — в цвет бумаги. Цвет берётся по
ПОЛОСЕ (строке), как атрибутный проход оригинала: самое частое значение
среди открытых клеток ряда (на кадре меню все 24 ряда дают 6/0).

Для Вектора это кодируется как ЧЕТЫРЕ варианта байта плоскости:
  0 = 00 (оба цвета с нулевым битом), 1 = FF (оба с единицей),
  2 = паттерн, 3 = ~паттерн.
Вариант применяется сразу при сборке блока, поэтому на каждой плоскости
получается свой словарь готовых байт и свой поток указателей, а
render.asm только копирует 8 байт и цвет на ходу не считает.

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
SCR = os.path.join(ASSETS, 'scr_4000.bin')

COLS = 32             # байтовых столбцов экрана
CELLS = 24            # клеток по 8 строк на столбец (192 строки ZX)
STEP = 0x1FC          # шаг кольца на столбец (две страницы назад, -4 байта)
RING_LEN = 0x4000

# ZX-цвет -> логический цвет Вектора (0 чёрный, 1 жёлтый, 2 белый, 3 красный)
CMAP = {0: 0, 6: 1, 4: 1, 7: 2, 5: 2, 1: 3, 2: 3, 3: 3}

# Палитра буфера (4 цвета, порядок = логический номер): земля меню жёлтая.
# Байт цвета Вектора — RRRGGGBB (см. V06_RGB в lib/v06.h):
#   (b << 6) | (g << 3) | r.
PAL4 = [
    (0x00, 'чёрный  — фон (paper ZX 0)'),
    (0x3F, 'жёлтый  — рельеф (ink ZX 6)'),
    (0xFF, 'белый   — ink ZX 7'),
    (0x07, 'красный — ink ZX 1/2/3'),
]


def load():
    ring = open(RING, 'rb').read()
    scr = open(SCR, 'rb').read()
    assert len(ring) == RING_LEN, 'ring_8000.bin: ожидалось 16384 Б'
    assert len(scr) == 6912, 'scr_4000.bin: ожидалось 6912 Б'
    return ring, scr


def screen(scr, x, y):
    return scr[(y & 0xC0) * 32 + (y & 7) * 256 + (y & 0x38) * 4 + x]


def attr(scr, cx, cy):
    return scr[6144 + cy * 32 + cx]


def ring_cell(ring, o, k):
    """8 байт клетки k (сверху вниз) столбца, стартующего со смещения o.

    Столбец кольца идёт СНИЗУ ВВЕРХ (n = 191-y): байт n — это строка
    y = 191-n, значит клетка k = строки 8k..8k+7 лежит в байтах
    o + 184-8k .. o + 191-8k, где байт j — строка 8k+7-j (верх клетки
    внутри блока последний).
    """
    base = o + 8 * (CELLS - 1 - k)
    return bytes(ring[(base + j) & 0x3FFF] for j in range(8))


def screen_cell(scr, x, k):
    """Те же 8 байт, но снятые с кадра ZX (для отбраковки оверлеев)."""
    return bytes(screen(scr, x, 8 * k + 7 - j) for j in range(8))


def fit_columns(ring, scr):
    """off(x) каждой колонки: якорь по x=31, дальше арифметическая прогрессия."""

    def score(x, o):
        return sum(ring[(o + n) & 0x3FFF] == screen(scr, x, 191 - n)
                   for n in range(192))

    anchor = max(range(RING_LEN), key=lambda o: score(31, o))
    offs, stats = [], []
    for x in range(COLS):
        pred = (anchor - STEP * (31 - x)) & 0x3FFF
        best = max((((pred + d) & 0x3FFF) for d in range(-4, 5)),
                   key=lambda o: score(x, o))
        offs.append(best)
        stats.append(score(x, best))
    for x in range(1, COLS):
        step = (offs[x] - offs[x - 1]) & 0x3FFF
        assert step == STEP, 'столбец %d: шаг %+d, ожидался +%d' % (x, step, STEP)
    return offs, stats


def build(ring, scr):
    offs, stats = fit_columns(ring, scr)
    cells = [[ring_cell(ring, offs[x], k) for k in range(CELLS)]
             for x in range(COLS)]
    exact = [[cells[x][k] == screen_cell(scr, x, k) for k in range(CELLS)]
             for x in range(COLS)]

    # Цвет — по ПОЛОСЕ, а не по клетке (TZ §3.3: цвет клетки задаёт строка,
    # как атрибутный проход оригинала). Берём самое частое значение среди
    # открытых клеток ряда: на кадре меню все 24 ряда дают 6/0 (жёлтый по
    # чёрному), единичные 2/0 и 7/0 — это оверлеи (логотип, текст).
    colours = [[None] * CELLS for _ in range(COLS)]
    for k in range(CELLS):
        votes = {}
        for x in range(COLS):
            if exact[x][k]:
                a = attr(scr, x, k)
                votes[a] = votes.get(a, 0) + 1
        if votes:
            best = max(votes, key=lambda a: votes[a])
            for x in range(COLS):
                colours[x][k] = best
    for k in range(CELLS):                 # ряд целиком под оверлеем
        if colours[0][k] is None:
            for d in range(1, CELLS):
                for kk in (k - d, k + d):
                    if 0 <= kk < CELLS and colours[0][kk] is not None:
                        for x in range(COLS):
                            colours[x][k] = colours[x][kk]
                        break
                if colours[0][k] is not None:
                    break
        assert colours[0][k] is not None, 'ряд %d без цвета' % k

    # Вариант байта плоскости для бита цвета (ink, paper — по одному биту):
    # 00/FF — цвет не зависит от паттерна, паттерн/~паттерн — зависит.
    def variant(ink, paper):
        if ink == paper:
            return 1 if ink else 0
        return 2 if ink else 3

    # Словарь ГОТОВЫХ байтов плоскостей: вариант цвета применён сразу, так
    # что render.asm только копирует 8 байт и цвет на ходу не считает.
    def block(cell, ink, paper):
        return bytes(plane_byte(variant(ink, paper), b) for b in cell)

    c1, c2 = [], []              # блоки плоскостей веса 1 и веса 2
    for x in range(COLS):
        for k in range(CELLS):
            a = colours[x][k]
            ink, paper = CMAP[a & 7], CMAP[(a >> 3) & 7]
            cell = cells[x][k]
            c1.append(block(cell, ink & 1, paper & 1))
            c2.append(block(cell, (ink >> 1) & 1, (paper >> 1) & 1))

    # словарь по частоте: одинаковые байты из разных клеток и плоскостей
    # схлопываются в один блок
    freq = {}
    for b in c1 + c2:
        freq[b] = freq.get(b, 0) + 1
    table = sorted(freq, key=lambda b: (-freq[b], b))
    index = {b: i for i, b in enumerate(table)}
    return (table, [index[b] for b in c1], [index[b] for b in c2],
            stats, sum(map(sum, exact)))


def emit(table, c1, c2, stats):
    lines = []
    w = lines.append
    w('; terrain.inc — рельеф меню H.A.T.E. для Вектора-06Ц.')
    w(';')
    w('; Сгенерировано tools/gen_terrain.py из assets/ring_8000.bin и')
    w('; assets/scr_4000.bin — руками не правится; включается из render.asm.')
    w(';')
    w('; Кольцо $8000-$BFFF держит готовую сцену (столбцы ландшафта) без')
    w('; оверлеев. Столбец экрана x читается из кольца со смещением')
    w('; off(x) = off(31) - $1FC*(31-x); off(31) подобрано по кадру ZX:')
    w('; совпадение байтов столбцов %d..%d из 192.' % (min(stats), max(stats)))
    w(';')
    w('; Картинка — 32 столбца по 24 клетки (строки 0..191 экрана). Поток —')
    w('; по столбцам, внутри столбца клетки идут СНИЗУ ВВЕРХ: позиция s')
    w('; потока ложится в VRAM по адресу base + x*256 + 64 + 8s, а это строки')
    w('; 191-8s .. 184-8s, то есть клетка k = 23-s нумерации сверху. Так байты')
    w('; пишутся по возрастанию адреса, как их и читает оригинал (снизу вверх).')
    w(';')
    w('; terrain_pat  — словарь %d готовых блоков по 8 байт: вариант цвета' % len(table))
    w(';                уже применён (00 / FF / паттерн / ~паттерн), так что')
    w(';                рендер только копирует байты и цвет не считает;')
    w('; terrain_c1   — %d указателей на блоки плоскости веса 1 (буфер A: E000);' % len(c1))
    w('; terrain_c2   — то же для плоскости веса 2 (C000). В буфер B обе')
    w(';                попадают копией A->B (gfx_dblbuf_copy_ab);')
    w('; terrain_pal4 — палитра буфера: 0 чёрный, 1 жёлтый, 2 белый, 3 красный')
    w(';                (зеркало CMAP: слот = логический цвет).')
    w(';                _terrain_pal4 — тот же адрес для C (sccz80: _).')
    w('')
    w('SECTION rodata_user')
    w('')
    w('PUBLIC terrain_pat')
    w('PUBLIC terrain_c1')
    w('PUBLIC terrain_c2')
    w('PUBLIC terrain_pal4')
    w('PUBLIC _terrain_pal4')
    w('PUBLIC terrain_cols')
    w('PUBLIC terrain_cells_per_col')
    w('')
    w('terrain_cols:           defb %d' % COLS)
    w('terrain_cells_per_col:  defb %d' % CELLS)
    w('')
    w('_terrain_pal4:')
    w('terrain_pal4:')
    for i, (p, why) in enumerate(PAL4):
        w('    defb 0x%02X                 ; %d: %s' % (p, i, why))
    w('')
    w('terrain_pat:')
    freq = [0] * len(table)
    for c in c1 + c2:
        freq[c] += 1
    for i, cell in enumerate(table):
        w('    defb %s            ; блок %d (%d шт.)'
          % (', '.join('0x%02X' % b for b in cell), i, freq[i]))
    for name, codes in (('terrain_c1:', c1), ('terrain_c2:', c2)):
        w('')
        w(name)
        for x in range(COLS):
            # позиция s в VRAM (64+8s) — это строки 191-8s..184-8s, т.е.
            # клетка k = CELLS-1-s из нумерации "сверху вниз"
            col = [codes[x * CELLS + CELLS - 1 - s] for s in range(CELLS)]
            for part in range(3):
                row = col[part * 8:part * 8 + 8]
                w('    defw %s%s' % (', '.join('terrain_pat + %d' % (8 * c)
                                           for c in row),
                                   '                    ; x=%d' % x
                                   if part == 0 else ''))
    with open(OUT, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def plane_byte(v, p):
    """Байт плоскости буфера для варианта v и байта паттерна p."""
    return (0x00, 0xFF, p, p ^ 0xFF)[v]


def preview(table, c1, c2):
    """Собрать картинку обратно из словаря и обоих потоков (сверка)."""
    from PIL import Image
    FIX = [(0, 0, 0), (224, 224, 0), (224, 224, 192), (224, 0, 0)]
    img = Image.new('RGB', (256, 256), (0, 0, 0))
    for x in range(COLS):
        for k in range(CELLS):
            b1 = table[c1[x * CELLS + k]]
            b2 = table[c2[x * CELLS + k]]
            for j in range(8):
                y = 8 * k + 7 - j
                for bit in range(8):
                    m = ((b1[j] >> (7 - bit)) & 1) | (((b2[j] >> (7 - bit)) & 1) << 1)
                    img.putpixel((x * 8 + bit, y), FIX[m])
    img.resize((512, 512), Image.NEAREST).save(PREVIEW)


def main():
    ring, scr = load()
    table, c1, c2, stats, nmatch = build(ring, scr)
    emit(table, c1, c2, stats)
    print('клетки: %d блоков, %d клеток; совпало с кадром %d из %d'
          % (len(table), len(c1), nmatch, len(c1)))
    print('ROM: словарь %d Б + потоки %d Б = %d Б'
          % (len(table) * 8, 2 * len(c1), len(table) * 8 + 2 * len(c1)))
    print('->', os.path.relpath(OUT, PORT))
    if '--preview' in sys.argv:
        preview(table, c1, c2)
        print('->', os.path.relpath(PREVIEW, PORT))


if __name__ == '__main__':
    main()
