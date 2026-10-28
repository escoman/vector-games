#!/usr/bin/env python3
"""
check_map.py — страховка раскладки: символы, для которых в коде предполагается
выровненный абсолютный адрес, действительно лежат на границе страницы.

Два места, где fire.asm считает адрес страницы нулевым:
  _fire_buf — шаг строки 256 ⇒ переход на следующую строку это «inr h»;
  _pt       — таблица упаковки читается как «lxi h,_pt / mov l,a».
ALIGN внутри SECTION работает относительно начала секции, а линкер может
поставить секцию куда угодно (code_clib в fire3 встал на $0182). Проверка
дешёвая и ловит молчаливую мешанину на экране.

Запуск:  python3 tools/check_map.py fire3.map _fire_buf _pt
"""
import re
import sys

HERE = __import__('os').path.dirname(__import__('os').path.abspath(__file__))


def parse(map_path):
    syms = {}
    pat = re.compile(r'^\s*([A-Za-z_][\w.]*)\s*=\s*\$([0-9A-Fa-f]+)\s*;')
    with open(map_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = pat.match(line)
            if m:
                syms.setdefault(m.group(1), int(m.group(2), 16))
    return syms


def main():
    if len(sys.argv) < 2:
        print('usage: check_map.py MAP [SYMBOL ...]', file=sys.stderr)
        return 2
    syms = parse(sys.argv[1])
    wanted = sys.argv[2:] or ['_fire_buf', '_pt']
    bad = []
    for name in wanted:
        key = name if name.startswith('_') else '_' + name
        addr = syms.get(key)
        if addr is None:
            bad.append('%s: не найден в карте' % key)
            continue
        if addr & 0xFF:
            bad.append('%s = $%04X — не выровнен по 256' % (key, addr))
        else:
            print('  ok  %-12s $%04X' % (key, addr))
    if bad:
        print('ALIGN CHECK FAILED:', file=sys.stderr)
        for b in bad:
            print('  ' + b, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
