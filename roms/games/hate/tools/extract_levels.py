"""Извлечь байт-код карт всех 10 уровней H.A.T.E. и отрендерить «ленту» уровня.

Модель (снимок zx-disasm/games/hate/tmp/run10_56000.z80, ENGINE.MD §3.3):

  $CF04        таблица уровней: на уровень 4 байта, слово 0 — указатель на
               скрипт, слово 1 — указатель на «сопроводительные» данные;
               терминатор таблицы — $FFFF.
  скрипт       байты-коды «частей», читаются с (указатель+1), конец — $FF;
  $C8EA+2*A    часть A = список пар (low,high) — указателей на записи столбцов,
               конец списка — high = 0;
  запись       15 байт кодов клеток (шаг записей 18 байт, сдвиг на 1 байт =
               подъём колодки на одну клетку);
  клетка       8 байт из банка $C400 + 8*код (или «дорожная» клетка $C4B8/$C4C0
               для самой нижней клетки страницы).

Столбец ландшафта = 16 клеток = 128 байт. Рендер ленты: столбец c рисуется
полосой 8 px по x, байт i столбца — строкой y = база - 4*c - i (уклон ленты
4 px на столбец, как в кольце: off(x+1) = off(x) + $1FC).

Запуск:  python3 tools/extract_levels.py [снимок] [имя.png]
"""
import os
import sys

sys.path.insert(0, '/home/alexey/Projects/zx-disasm/skoolkit')
from skoolkit.snapshot import get_snapshot  # noqa: E402

from PIL import Image  # noqa: E402

SNAP = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/alexey/Projects/zx-disasm/games/hate/tmp/run10_56000.z80'
OUT = sys.argv[2] if len(sys.argv) > 2 else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..',
                 '..', '.scratch', 'hate_levels_ribbon.png')
mem = bytes(get_snapshot(SNAP))
b = mem.__getitem__


def w(a):
    return b(a) | (b(a + 1) << 8)


BANK = 0xC400
PARTS = 0xC8EA
QUEUE = 0xCA43
CELLS = 16                    # клеток в столбце
ROAD = (0xC4B8, 0xC4C0)       # «дорожная» нижняя клетка, две фазы


def cell_bytes(src):
    """8 байт клетки из адреса банка."""
    return [mem[src + i] for i in range(8)]


# --- таблица частей -------------------------------------------------------
part_cols = {}                # код -> список указателей на записи столбцов
code = 0
while PARTS + 2 * code + 1 < QUEUE:
    a = PARTS + 2 * code
    ptrs = []
    while b(a + 1) != 0 and len(ptrs) <= 64:
        ptrs.append(w(a))
        a += 2
    part_cols[code] = ptrs
    code += 1
MAXCODE = max(k for k, v in part_cols.items() if v)
print('таблица частей: коды 0..%d, непустых %d, ссылок на столбцы %d'
      % (MAXCODE, sum(1 for v in part_cols.values() if v),
         sum(len(v) for v in part_cols.values())))

# --- таблица уровней ------------------------------------------------------
levels = []
a = 0xCF04
while w(a) != 0xFFFF:
    script, other = w(a), w(a + 2)
    p = script + 1
    codes = []
    while b(p) != 0xFF:
        codes.append(b(p))
        p += 1
    cols = []
    for c in codes:
        cols.extend(part_cols.get(c, []))
    levels.append((script, other, codes, cols))
    a += 4
print('уровней: %d' % len(levels))
for i, (s, o, codes, cols) in enumerate(levels):
    print('  ур %2d: скрипт $%04X, пар $%04X, кодов %d, столбцов %d'
          % (i + 1, s, o, len(codes), len(cols)))

# --- столбец -> 16 кодов клеток ------------------------------------------
def column_cells(ptr, page):
    """Запись столбца: 15 кодов + дорожная клетка снизу (фаза по номеру)."""
    rec = [mem[ptr + i] for i in range(15)]
    road = ROAD[1] if ((page >> 1) + 1) & 3 == 0 else ROAD[0]
    return [road] + [BANK + 8 * c for c in rec]   # адреса клеток, снизу вверх


# --- рендер ленты ---------------------------------------------------------
BAND = CELLS * 8              # 128 байт на столбец
SLOPE = 4                     # px подъёма на столбец
MARGIN = 192                  # запас сверху
COLORS = [1, 2, 3, 4]         # свой палитры: тёмно-жёлтый, голубой, зелёный,
                              # пурпурный — по кругу на номер уровня


def render(level_idx):
    """Лента уровня: столбец c — 8 px по x, байт i — строка y = база - 4c - i."""
    _, _, _, cols = levels[level_idx]
    n = len(cols)
    W, H = n * 8, BAND + SLOPE * (n - 1) + MARGIN + 1
    img = Image.new('P', (W, H), 0)
    pal = [0, 0, 0, 204, 204, 0, 0, 255, 255, 0, 255, 0, 255, 0, 255]
    img.putpalette(pal + [0] * (768 - len(pal)))
    px = img.load()
    col = COLORS[level_idx % 4]
    for c, ptr in enumerate(cols):
        cells = column_cells(ptr, c)
        ytop = MARGIN + BAND + SLOPE * (n - 1 - c)
        for k, src in enumerate(cells):
            pat = cell_bytes(src)
            for i in range(8):
                bits = pat[i]
                if not bits:
                    continue
                y = ytop - (8 * k + i)
                for j in range(8):
                    if bits & (0x80 >> j):
                        px[c * 8 + j, y] = col
    return img


imgs = []
for i in range(len(levels)):
    img = render(i)
    imgs.append(img)
    print('ур %d: лента %dx%d' % (i + 1, img.size[0], img.size[1]))
    stem, ext = os.path.splitext(OUT)
    img.save('%s_%02d%s' % (stem, i + 1, ext))

# смонтировать все 10 лент столбцом
W = max(im.size[0] for im in imgs)
H = sum(im.size[1] + 20 for im in imgs)
mont = Image.new('RGB', (W, H), (0, 0, 0))
y = 0
for im in imgs:
    mont.paste(im.convert('RGB'), (0, y))
    y += im.size[1] + 20
mont.save(OUT)
print('сохранено:', OUT, mont.size)
