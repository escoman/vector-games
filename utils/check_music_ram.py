#!/usr/bin/env python3
"""check_music_ram.py — сборочный guard сжатых партитур Вектора-06Ц.

Проверяет, что распакованная партитура влезает в ОЗУ между концом образа
ROM и видеопамятью:

    0x0100 + rom_size + max_unpack  <=  ceiling

Образ ROM грузится в 0x0100, его вершина = 0x0100 + размер файла — это и
есть символ линкера __tail. Куча (lib/mem/heap.c) стартует от __tail, а
буфер распаковки (music_load_compressed) равен самому длинному треку, поэтому
сумма выше — минимальный адрес, до которого доходит распакованная музыка.
Потолок по умолчанию 0x8000 — начало видеопамяти и значение heap_top по
умолчанию; при heap_alloc он же приводит к возврату 0 (музыка молчит), но
здесь мы ловим переполнение ещё на этапе сборки.

Длины потоков берутся из сгенерированных mus2inc.py массивов
`<name>_streamlen[4]` (сумма четырёх длин = unpack_size песни).

Использование:
    python3 utils/check_music_ram.py ROM.rom rom_data/*_music.inc
    python3 utils/check_music_ram.py ROM.rom rom_data/*_music.inc --ceiling 0x8000

Код возврата: 0 — влезает, 1 — не влезает (сборку надо остановить),
2 — ошибка разбора/нет данных.
"""

import argparse
import os
import re
import sys

LOAD_ORIGIN = 0x0100

# static const unsigned int NAME_streamlen[4] = { a, b, c, d };
_STREAMLEN_RE = re.compile(
    r'_streamlen\[4\]\s*=\s*\{([^}]*)\}', re.S)


def unpack_size_of(inc_path):
    """Сумма длин четырёх потоков песни из .inc, или None если их нет
    (несжатая песня — guard не нужен)."""
    with open(inc_path, encoding='utf-8') as f:
        text = f.read()
    m = _STREAMLEN_RE.search(text)
    if not m:
        return None
    nums = re.findall(r'(\d+)u?', m.group(1))
    if len(nums) != 4:
        raise ValueError(f'{inc_path}: ожидалось 4 длины в _streamlen, '
                         f'найдено {len(nums)}')
    return sum(int(n) for n in nums)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('rom', help='образ ROM (.rom)')
    ap.add_argument('incs', nargs='+', help='сгенерированные *_music.inc')
    ap.add_argument('--ceiling', default='0x8000',
                    help='потолок ОЗУ (по умолчанию 0x8000 — видеопамять)')
    args = ap.parse_args()

    ceiling = int(args.ceiling, 0)
    if not os.path.isfile(args.rom):
        print(f'check_music_ram: ROM не найден: {args.rom}', file=sys.stderr)
        return 2

    rom_size = os.path.getsize(args.rom)
    image_top = LOAD_ORIGIN + rom_size      # = __tail

    sizes = {}
    for inc in args.incs:
        try:
            sz = unpack_size_of(inc)
        except (OSError, ValueError) as e:
            print(f'check_music_ram: {e}', file=sys.stderr)
            return 2
        if sz is not None:
            sizes[os.path.basename(inc)] = sz

    if not sizes:
        # Ни одной сжатой песни — guard не применим (несжатая сборка).
        print('check_music_ram: сжатых партитур нет — пропускаю.')
        return 0

    worst = max(sizes, key=sizes.get)
    max_unpack = sizes[worst]
    need_top = image_top + max_unpack
    margin = ceiling - need_top

    print(f'check_music_ram: образ {rom_size} байт, вершина __tail='
          f'0x{image_top:04X}')
    print(f'  самый длинный трек: {worst} = {max_unpack} байт после распаковки')
    print(f'  буфер: 0x{image_top:04X}..0x{need_top:04X}, потолок '
          f'0x{ceiling:04X}, запас {margin} байт')

    if margin < 0:
        print(f'ОШИБКА: распакованная музыка не влезает в ОЗУ — переполнение '
              f'на {-margin} байт выше 0x{ceiling:04X}. Уменьшите образ '
              f'(сожмите ещё ресурсы) или поднимите heap_top/потолок, если '
              f'верхние плоскости видеопамяти свободны.', file=sys.stderr)
        return 1

    print('  OK: распакованная партитура помещается до видеопамяти.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
