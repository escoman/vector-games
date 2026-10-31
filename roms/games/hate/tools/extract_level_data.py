"""Снять из снапшота H.A.T.E. данные карт уровней в assets/level_data.bin.

Источник — mid-mission снапшот zx-disasm (tmp/run10_56000.z80). Кусок
$C400-$CFFF содержит ВСЁ, что нужно движку рельефа, в одних и тех же
адресах, что и в оригинале:

  $C400-$C5FF  банк шаблонов клеток: 64 клетки по 8 байт, код клетки ->
               $C400 + 8*код. Из него же «дорожные» клетки $C4B8 (код 23) и
               $C4C0 (код 24);
  $C640-$C8xx  записи столбцов: 15 кодов клеток на столбец, шаг 18 байт;
               указатель, сдвинутый на 1..3 байта назад, = тот же столбец,
               поднятый на 1..3 клетки;
  $C8EA-$CA42  таблица частей: код части -> список указателей на записи
               столбцов, терминатор списка — старший байт 0;
  $CF04-...    таблица уровней (по 4 байта: скрипт + сопроводительные данные,
               терминатор $FFFF) и сами скрипты — байт-коды частей через $FF.

Формат — сырой срез памяти, базовый адрес $C400; читается gen_levels.py.

Запуск (нужен skoolkit рядом с zx-disasm):

    python3 tools/extract_level_data.py [путь-к-снапшоту]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.dirname(HERE)
ASSETS = os.path.join(PORT, 'assets')
DEFAULT_SNAP = os.path.abspath(os.path.join(
    PORT, '..', '..', '..', '..', 'zx-disasm', 'games', 'hate', 'tmp',
    'run10_56000.z80'))
SKOOLKIT = os.path.abspath(os.path.join(
    PORT, '..', '..', '..', '..', 'zx-disasm', 'skoolkit'))

if SKOOLKIT not in sys.path:
    sys.path.insert(0, SKOOLKIT)

from skoolkit.snapshot import get_snapshot   # noqa: E402

BASE = 0xC400
END = 0xD000


def main(snap):
    mem = bytes(get_snapshot(snap))
    blob = mem[BASE:END]
    assert len(blob) == END - BASE
    out = os.path.join(ASSETS, 'level_data.bin')
    with open(out, 'wb') as f:
        f.write(blob)
    print('%s: $%04X-$%04X -> %s (%d Б)'
          % (os.path.basename(snap), BASE, END, os.path.relpath(out, PORT),
             len(blob)))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SNAP)
