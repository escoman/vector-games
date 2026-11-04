#!/usr/bin/env python3
"""
bin2inc.py — сборка бинарного артефакта в .inc-массив для z80asm.

Предназначен для stage-2 загрузчика: `make loader2` собирает
lib/boot/loader_stage2.asm в плоский bin (ORG 0E000h) и превращает его в
lib/boot/loader_stage2.inc, который loader.asm подтягивает через INCLUDE
(тот же порядок, что у шрифтов: default_8x8.inc подключается из pr.asm).

Использование:
    python3 utils/bin2inc.py INPUT.bin OUTPUT.inc --label МЕТКА [--max N]
        [--equ ИМЯ_размера] [--origin 0xe000]

    --label   имя метки массива (в z80asm регистр значим!)
    --max     бюджет в байтах: сборка падает, если bin длиннее (ступенька
              loader2 — 512, область 0xE000..0xE1FF)
    --equ     имя константы размера (по умолчанию <LABEL>_SIZE)
    --origin  адрес, под который собран bin — только для комментария,
              сам bin нулями до org не дополняется (z80asm -b)

Массив подключается INCLUDE'ом внутрь модуля-потребителя (как шрифты),
поэтому метка и EQU-константа видимы в нём без линковки.
"""
import argparse
import os
import sys

PER_LINE = 16


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--label', required=True)
    ap.add_argument('--max', type=int, default=0,
                    help='бюджет байтов, 0 — не проверять')
    ap.add_argument('--equ', default=None)
    ap.add_argument('--origin', default=None)
    a = ap.parse_args()

    data = open(a.src, 'rb').read()
    if not data:
        print('%s: пустой вход' % a.src, file=sys.stderr)
        return 1
    if a.max and len(data) > a.max:
        print('%s: %d байта, бюджет %d — не помещается'
              % (a.src, len(data), a.max), file=sys.stderr)
        return 1

    size_name = a.equ or (a.label.upper() + '_SIZE')
    rel = os.path.relpath(a.src, os.path.dirname(os.path.abspath(__file__)) + '/..')

    out = []
    out.append(';')
    out.append('; %s — сгенерировано из %s (utils/bin2inc.py), НЕ ПРАВИТЬ.'
               % (os.path.basename(a.dst), rel))
    out.append(';')
    if a.origin:
        out.append('; Собран под ORG %s: метки разрешены в абсолютные адреса'
                   ' этой' % a.origin)
    out.append('; области, поэтому массив копируется в память побайтово без')
    out.append('; релопации. docs/LOADER_TZ.MD.')
    out.append(';')
    out.append('%s:' % a.label)
    for i in range(0, len(data), PER_LINE):
        chunk = data[i:i + PER_LINE]
        out.append('        db      ' + ', '.join('0%02Xh' % b for b in chunk))
    out.append('%s      equ     %d           ; размер blob, байт'
               % (size_name, len(data)))
    out.append('')

    open(a.dst, 'w', encoding='utf-8').write('\n'.join(out))
    print('%s: %d байт -> %s (%s = %d)'
          % (a.src, len(data), a.dst, size_name, len(data)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
