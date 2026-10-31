"""Снять из снапшота HATE дампы, из которых строится рельеф.

Источник: mid-mission снапшот zx-disasm (tmp/run10_56000.z80, кадр меню с
жёлтым ландшафтом). Скрипт вырезает два куска памяти и кладёт их в assets/:

  assets/ring_8000.bin  — кольцевой буфер $8000-$BFFF (16 КБ). Это и есть
                          рельеф целиком: страницы кольца = столбцы сцены,
                          уже без логотипа, меню и приборной панели (они
                          рисуются на экран поверх, в кольцо не попадают);
  assets/scr_4000.bin   — экран ZX $4000-$5AFF (6912 Б: битмап + атрибуты).
                          Нужен только для цветов клеток и для отбраковки
                          клеток, закрытых оверлеями.

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
SCR_ADDR = 0x4000
SCR_LEN = 0x1B00      # 6144 байт битмапа + 768 байт атрибутов


def main(snap):
    mem = bytes(get_snapshot(snap))
    ring = mem[RING_ADDR:RING_ADDR + RING_LEN]
    scr = mem[SCR_ADDR:SCR_ADDR + SCR_LEN]
    assert len(ring) == RING_LEN and len(scr) == SCR_LEN

    out_ring = os.path.join(ASSETS, 'ring_8000.bin')
    out_scr = os.path.join(ASSETS, 'scr_4000.bin')
    with open(out_ring, 'wb') as f:
        f.write(ring)
    with open(out_scr, 'wb') as f:
        f.write(scr)
    print('%s: кольцо %d Б, экран %d Б' % (os.path.basename(snap), len(ring), len(scr)))
    print('  ->', os.path.relpath(out_ring, PORT))
    print('  ->', os.path.relpath(out_scr, PORT))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SNAP)
