#!/usr/bin/env python3
"""romconsist.py — состав ROM Вектора-06Ц по разделам, файлам и символам.

Показывает, из чего складывается размер .rom: ресурсы (константы/rodata),
код программы (C), библиотечный код, runtime компилятора и данные. Даёт
разбивку по исходным файлам и крупнейшим символам — чтобы было видно, что
можно ужать (обычно это тяжёлые таблицы треков в rodata).

Источник данных — карта линкера, которую zcc пишет с ключом -m
(`make consist` в finally.mk пересобирает ROM с -m и вызывает этот скрипт).

Использование:
    python3 romconsist.py <файл.map> [--top N] [--min BYTES]

Аргументы:
    <файл.map>   карта линкера (zcc -m)
    --top N      сколько строк в списках «крупнейшие» (по умолчанию 15)
    --min BYTES  порог показа символа в байтах (по умолчанию 8)
"""

import argparse
import os
import re
import sys


# --- Разделы и их человекочитаемые имена -------------------------------
# kind: ROM — лежит в образе; RAM — только в ОЗУ; BOTH — инициализированные
# данные (заполнитель в ROM + копируется в ОЗУ на старте).
SECTION_INFO = {
    'rodata_compiler': ('Ресурсы/константы (rodata)', 'ROM'),
    'code_compiler':   ('Код программы (C)',          'ROM'),
    'code_clib':       ('Библиотеки (code_clib)',     'ROM'),
    'code_user':       ('Код (asm, code_user)',       'ROM'),
    'code_l_sccz80':   ('Runtime sccz80',             'ROM'),
    'data_compiler':   ('Данные (иниц., C)',          'BOTH'),
    'data_user':       ('Данные (иниц., asm)',        'BOTH'),
    'bss_compiler':    ('BSS (неиниц.)',              'RAM'),
    'bss_user':        ('BSS (неиниц., asm)',         'RAM'),
}
# Разделы, которые физически занимают место в образе ROM.
ROM_SECTIONS = {s for s, (_, k) in SECTION_INFO.items() if k in ('ROM', 'BOTH')}

# Строка вида:  NAME = $ADDR ; type, scope, def, module, section, source
LINE_RE = re.compile(r'^(\S+)\s*=\s*\$([0-9A-Fa-f]+)\s*;\s*(.*)$')


def is_section(name):
    return name.startswith('code_') or name.startswith('rodata_') or \
        name.startswith('data_') or name.startswith('bss_')


def short_src(src):
    """Приводит путь из карты к короткому виду относительно корня проекта."""
    src = src.split('::')[0]            # main.c::func::0::7:112 → main.c
    src = re.sub(r':\d+$', '', src)     # file.asm:25 → file.asm
    src = re.sub(r'^(\.\./)+', '', src)  # ../soundtracks/x.c → soundtracks/x.c
    if src.startswith('/'):
        low = src.lower()
        if '/lib/' in low:
            src = 'lib/' + src.split('/lib/', 1)[1]
        elif '/soundtracks/' in low:
            src = 'soundtracks/' + src.split('/soundtracks/', 1)[1]
        else:
            src = os.path.basename(src)
    return src or '?'


def parse_map(path):
    """Возвращает (agg, symbols, image_head, image_tail).

    agg[section] = {'head','size','tail'} — агрегаты __<section>_*.
    symbols[section] = [(addr, name, module, source), ...] — символы.
    """
    agg = {}
    symbols = {}
    head = tail = None
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = LINE_RE.match(line.strip())
            if not m:
                continue
            name = m.group(1)
            addr = int(m.group(2), 16)
            fields = [x.strip() for x in m.group(3).split(', ', 5)]
            # Глобальные границы образа.
            if name == '__head':
                head = addr
                continue
            if name == '__tail':
                tail = addr
                continue
            # Агрегаты раздела: __<section>_{head,size,tail}.
            if name.startswith('__') and '_' in name[2:]:
                base, _, which = name[2:].rpartition('_')
                if which in ('head', 'size', 'tail') and is_section(base):
                    agg.setdefault(base, {})[which] = addr
                    continue
            # Обычный символ: поля = type, scope, def, module, section, source.
            # Берём только реальные размещённые объекты (type=addr); константы
            # defc (type=const) имеют «адрес» = значение порта, не размер.
            if len(fields) >= 5 and fields[0] == 'addr':
                section = fields[4]
                module = fields[3]
                source = fields[5] if len(fields) >= 6 else ''
                if is_section(section):
                    symbols.setdefault(section, []).append(
                        (addr, name, module, source))
    return agg, symbols, head, tail


def symbol_sizes(section, items, agg):
    """Размер символа = адрес след. символа (или хвост раздела) минус его адрес."""
    items = sorted(items)
    sec_tail = agg.get(section, {}).get('tail')
    out = []
    for i, (addr, name, module, source) in enumerate(items):
        if i + 1 < len(items):
            size = items[i + 1][0] - addr
        elif sec_tail is not None:
            size = sec_tail - addr
        else:
            size = 0
        out.append((name, size, module, source))
    return out


def fmt_table(rows, widths, headers):
    """Простой текстовой конкорд: rows = списки колонок (строки)."""
    line = '  ' + '  '.join(h.ljust(w) for h, w in zip(headers, widths))
    out = [line, '  ' + '  '.join('-' * w for w in widths)]
    for r in rows:
        out.append('  ' + '  '.join(str(c).ljust(w) for c, w in zip(r, widths)))
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description='Состав ROM по карте линкера.')
    ap.add_argument('map', help='файл .map (zcc -m)')
    ap.add_argument('--top', type=int, default=15, help='строк в топ-списках')
    ap.add_argument('--min', type=int, default=8, help='порог показа символа, байт')
    args = ap.parse_args()

    if not os.path.isfile(args.map):
        sys.stderr.write(f'Карта не найдена: {args.map}\n')
        return 2

    agg, symbols, head, tail = parse_map(args.map)

    # Размеры разделов: берём из агрегатов (это авторитетные числа линкера).
    sec_size = {s: a.get('size') for s, a in agg.items() if 'size' in a}
    total_image = (tail - head) if (head is not None and tail is not None) \
        else sum(sec_size.values())

    # Все размеры символов по разделам.
    sized = {}
    for s, items in symbols.items():
        sized[s] = symbol_sizes(s, items, agg)

    # --- Заголовок ---
    print(f'\nСостав ROM: {os.path.basename(args.map)[:-4]}.rom'
          f'   (образ {total_image} Б)')

    # --- 1. По разделам ---
    print('\n== По разделам ==')
    order = [s for s in SECTION_INFO if s in sec_size]
    order += [s for s in sorted(sec_size) if s not in SECTION_INFO]
    accounted = 0
    rows = []
    for s in order:
        size = sec_size[s]
        label, kind = SECTION_INFO.get(s, (s, '?'))
        if kind != 'RAM':
            accounted += size
        pct = f'{100.0 * size / total_image:5.1f}%' if total_image else ''
        rows.append([label, f'{size}', pct, {'ROM': 'ROM', 'RAM': 'RAM',
                                             'BOTH': 'ROM+ОЗУ'}.get(kind, kind)])
    residual = total_image - accounted
    if residual > 0:
        rows.append(['стартап + BSS/резерв', f'{residual}',
                     f'{100.0 * residual / total_image:5.1f}%' if total_image else ''])
    rows.append(['—' * 26, '—', '—', '—'])
    rows.append(['ОБРАЗ ROM', f'{total_image}', '100.0%' if total_image else ''])
    print(fmt_table(rows, [30, 7, 6, 8], ['раздел', 'байт', '%', 'где']))

    # --- 2. Крупнейшие файлы (только ROM: код + ресурсы + данные) ---
    by_file = {}
    for s in ROM_SECTIONS:
        for name, size, module, source in sized.get(s, []):
            key = short_src(source) or module or '?'
            by_file[key] = by_file.get(key, 0) + size
    print('\n== Крупнейшие файлы (в образе ROM) ==')
    frows = [[f'{n}', src] for src, n in
             sorted(by_file.items(), key=lambda kv: -kv[1])[:args.top]]
    print(fmt_table(frows, [8, 40], ['байт', 'файл']))

    # --- 3. Крупнейшие ресурсы (rodata) — обычно треки/картинки ---
    res = [r for s in SECTION_INFO if SECTION_INFO[s][1] == 'ROM'
           and s.startswith('rodata') for r in sized.get(s, [])]
    if res:
        print('\n== Крупнейшие ресурсы (rodata) ==')
        rrows = [[f'{n}', name, f'{short_src(src)}'] for name, n, _, src in
                 sorted(res, key=lambda t: -t[1])[:args.top] if n >= args.min]
        print(fmt_table(rrows, [8, 28, 34], ['байт', 'символ', 'файл']))

    # --- 4. Крупнейшие функции кода ---
    # Символы кода группируем по функции-владельцу: sccz80/copt дробят
    # тело одной C-функции на метки i_NN (цели переходов, инлайнинг).
    # Поле source несёт имя функции: «path.c::func::скоуп::NN:строка».
    # Для .asm метки осмысленные (font8x8, div_loop) — группировка по имени.
    code_by_owner = {}
    for s in [x for x in SECTION_INFO if x.startswith('code_')]:
        for name, size, module, source in sized.get(s, []):
            if '::' in source:
                owner = source.split('::')[1] or name
            else:
                owner = name
            key = (owner, short_src(source))
            code_by_owner[key] = code_by_owner.get(key, 0) + size
    if code_by_owner:
        print('\n== Крупнейшие функции (код) ==')
        crows = [[f'{sz}', owner, f'{f}'] for (owner, f), sz in
                 sorted(code_by_owner.items(), key=lambda kv: -kv[1])[:args.top]
                 if sz >= args.min]
        print(fmt_table(crows, [8, 26, 34], ['байт', 'функция', 'файл']))

    # --- Вердикт по лимиту 32 КБ ---
    LIMIT = 32768
    if total_image > LIMIT:
        over = total_image - LIMIT
        top_res = ''
        for src, n in sorted(by_file.items(), key=lambda kv: -kv[1]):
            if src.endswith('.inc') or 'rom_data' in src:
                top_res = f'; крупнейший ресурс — {src} ({n} Б)'
                break
        print(f'⚠  ОБРАЗ ПРЕВЫШАЕТ 32 КБ на {over} Б{top_res}')
    else:
        print(f'✓  в пределах 32 КБ (запас {LIMIT - total_image} Б)')

    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
