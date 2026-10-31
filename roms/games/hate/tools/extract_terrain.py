"""Снять из снапшота HATE данные рельефа меню.

Источник: mid-mission снапшот zx-disasm (tmp/run10_56000.z80). Скрипт вырезает
два куска памяти и кладёт их в assets/:

  assets/ring_8000.bin     — кольцевой буфер $8000-$BFFF (16 КБ). Это и есть
                             рельеф целиком: страницы кольца = столбцы сцены,
                             уже без логотипа, меню и приборной панели (они
                             рисуются на экран поверх, в кольцо не попадают);
  assets/terrain_mask.bin  — окно вывода: точка входа блиттера + лесенка
                             $D5B2 (формат ниже).

ОКНО ВЫВОДА, А НЕ СИЛУЭТ. $D5B2 — готовый список адресов экрана, по которому
ходит блиттер $D2E3 (ENGINE.MD §3.5): 8 байт кольца на каждое слово списка,
вверх по экрану. Поэтому рельеф на экране — не «весь столбец», а только те
клетки, что перечислены в списке: столбец 0 заполнен от низа (y=191) до y=103,
столбец 31 — от y=7 до y=103. Кадр без этой маски даёт три полосы мусора
вместо одной ленты ландшафта.

Формат terrain_mask.bin:

    +0  .. +1   off(0) — смещение столбца 0 в кольце, мл. байт первый;
    +2  .. +65  по столбцам x = 0..31: (ktop, kbot) — верхняя и нижняя клетки
                из списка, нумерация сверху, каждая клетка = 8 строк (0..23).

off(0) считается по состоянию блиттера, а не подбором: перед первым столбцом
он ставит DE = $80 + ($C32E) + (($C32F) & $7F), ($C32F) & $FE (младший байт
столбца, §3.5). Дальше off(x+1) = off(x) + $1FC — это уже знает gen_terrain.

Запуск (нужен skoolkit рядом с zx-disasm):

    python3 tools/extract_terrain.py [путь-к-снапшоту]

По умолчанию берётся zx-disasm/games/hate/tmp/run10_56000.z80 — соседний
с vector-games каталог проектов; руками .bin не правятся.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.dirname(HERE)
ASSETS = os.path.join(PORT, 'assets')
DEFAULT_SNAP = os.path.abspath(os.path.join(
    PORT, '..', '..', '..', '..', 'zx-disasm', 'games', 'hate', 'tmp', 'run10_56000.z80'))
SKOOLKIT = os.path.abspath(os.path.join(
    PORT, '..', '..', '..', '..', 'zx-disasm', 'skoolkit'))

if SKOOLKIT not in sys.path:
    sys.path.insert(0, SKOOLKIT)

from skoolkit.snapshot import get_snapshot   # noqa: E402

RING_ADDR = 0x8000
RING_LEN = 0x4000
COLS = 32             # байтовых столбцов экрана ZX
CELLS = 24            # клеток по 8 строк в столбце (192 строки)

BLIT_LIST = 0xD5B2    # SP блиттера: список адресов экрана (слова)
BLIT_PAGE = 0xC32E    # номер страницы кольца: D = $80 + этот байт + ...
BLIT_HALF = 0xC32F    # половина страницы: E = байт & $FE

# Четыре первых слова списка — заглушки $0800 («писать в ПЗУ и забыть»), они
# тоже двигают источник: первая клетка читается со смещения off(0) + 28
# (первая заглушка — блок из 4 байт, три следующие — по 8).
LIST_PREFIX = 4 + 3 * 8


def decode(word):
    """Слово списка -> (столбец, строка) экрана ZX; None — не адрес экрана."""
    if not 0x4000 <= word < 0x5800:
        return None
    d = word - 0x4000
    x = d & 31
    # адрес ZX: $4000 + (y&$C0)*32 + (y&7)*256 + (y&$38)*4 + x
    y = (((d >> 11) & 7) << 6) | ((d >> 2) & 0x38) | ((d >> 8) & 7)
    return x, y


def blit_list(mem):
    """Список $D5B2 -> (x, y) по каждому слову, до $FFFF."""
    out = []
    for i in range(600):
        w = mem[BLIT_LIST + 2 * i] | (mem[BLIT_LIST + 2 * i + 1] << 8)
        if w == 0xFFFF:
            return out
        d = decode(w)
        if d is not None:
            out.append(d)
    raise SystemExit('список $D5B2 без терминатора $FFFF')


def window(cells):
    """Клетки одного столбца -> (ktop, kbot) в нумерации сверху."""
    ks = [y // 8 for _, y in cells]
    return min(ks), max(ks)


def anchor(mem):
    """Смещение столбца 0 в кольце по состоянию блиттера перед кадром."""
    d = 0x80 + mem[BLIT_PAGE] + (mem[BLIT_HALF] & 0x7F)
    e = mem[BLIT_HALF] & 0xFE
    return (d * 256 + e - RING_ADDR + LIST_PREFIX) & (RING_LEN - 1)


def main(snap):
    mem = bytes(get_snapshot(snap))
    ring = mem[RING_ADDR:RING_ADDR + RING_LEN]
    assert len(ring) == RING_LEN

    by_col = [[] for _ in range(COLS)]
    for x, y in blit_list(mem):
        by_col[x].append((x, y))
    assert all(by_col), 'в списке $D5B2 есть пустые столбцы'

    rows = [window(c) for c in by_col]
    for x, (top, bot) in enumerate(rows):
        assert 0 <= top <= bot < CELLS, 'столбец %d: окно %d..%d' % (x, top, bot)

    off0 = anchor(mem)
    mask = bytearray([off0 & 0xFF, off0 >> 8])
    for top, bot in rows:
        mask += bytes((top, bot))

    out_ring = os.path.join(ASSETS, 'ring_8000.bin')
    out_mask = os.path.join(ASSETS, 'terrain_mask.bin')
    with open(out_ring, 'wb') as f:
        f.write(ring)
    with open(out_mask, 'wb') as f:
        f.write(bytes(mask))

    print('%s: кольцо %d Б, окно %d столбцов' % (os.path.basename(snap), len(ring), COLS))
    print('  off(0) = $%04X  (страница $%02X, половина $%02X, +%d заглушки)'
          % (off0, mem[BLIT_PAGE], mem[BLIT_HALF], LIST_PREFIX))
    print('  клетки окна по столбцам: %d' % sum(b - t + 1 for t, b in rows))
    for i in range(0, COLS, 8):
        print('  x=%2d..%2d: %s' % (i, i + 7, ' '.join('%d..%d' % r for r in rows[i:i + 8])))
    print('  ->', os.path.relpath(out_ring, PORT))
    print('  ->', os.path.relpath(out_mask, PORT))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SNAP)
