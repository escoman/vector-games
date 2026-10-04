#!/usr/bin/env python3
"""Генератор range_fonts.asm — шрифты режима прямого индекса для теста fonts.

Вход:  lib/gfx/fonts/default_16x8.inc и lib/gfx/fonts/default_thin.inc —
       библиотечные шрифты 512-режимов (таблица имён + глифы).

Выход: roms/tests/fonts/range_fonts.asm с двумя дескрипторами, у которых
chars = 0, то есть режим прямого индекса по коду символа:

    глиф = glyphs + (код - first_code) * шаг, шаг = 16 и 8 байта.

Берём только цифры 0x30..0x39: в таблице имён дефолтного шрифта они идут
подряд («...XYZ0123456789-:...»), поэтому десять глифов вырезаются одним
куском, и проверять непрерывность генератору обязанность, а не сюрприз.
Коды вне диапазона рендер пропускает, ничего не затирая.

Запуск:  python3 tools/gen_range_fonts.py
"""
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
LIB = HERE.parents[3] / 'lib' / 'gfx' / 'fonts'
OUT = HERE.parent / 'range_fonts.asm'

FONTS = [
    # (метка таблицы имён, метка глифов, шаг глифа, файл)
    ('font_chars_512', 'font16x8', 16, 'default_16x8.inc'),
    ('font_chars_512t', 'font_thin', 8, 'default_thin.inc'),
]

FIRST, LAST = 0x30, 0x39


def after_label(src, label):
    """Строки после строки-метки `<label>:`.

    Имя именно вся строка: в default_thin.inc `font_thin:` встречается и в
    комментарии, поэтому `split` по подстроке резал бы не там.
    """
    lines = src.split('\n')
    for i, ln in enumerate(lines):
        if ln.strip() == f'{label}:':
            return '\n'.join(lines[i + 1:])
    raise ValueError(f'метка {label}: не найдена')


def name_table(src, label):
    """Таблица имён: defm-строки плюс defb-байты, терминатор 0."""
    body = after_label(src, label)
    codes = []
    for ln in body.split('\n'):
        ln = ln.strip()
        if ln.startswith(';') or not ln:
            if codes:
                break
            continue
        if ln.startswith('defm'):
            codes += [ord(c) for c in re.findall(r'"([^"]*)"', ln)[0]]
            continue
        if ln.startswith('defb'):
            v = ln.split(None, 1)[1].rstrip(',').strip()
            if v == '0':
                break
            codes.append(ord(v.strip(chr(39))[0]) if v[0] == chr(39)
                         else int(v, 16))
            continue
        break
    return codes


def glyph_data(src, label, stride):
    """Данные глифов подряд, байт за байтом (комментарии-имена пропускаем)."""
    body = after_label(src, label)
    data = []
    for ln in body.split('\n'):
        ln = ln.strip()
        if not ln or ln.startswith(';'):
            continue
        if not ln.startswith('defb'):
            break                        # следующая метка/секция — данные кончились
        for tok in re.findall(r'0x([0-9A-Fa-f]{2})', ln):
            data.append(int(tok, 16))
        if len(data) >= stride * 64:      # хватит с запасом
            break
    return data


def digits_slice(codes, data, stride, label):
    """Глифы цифр + проверка, что коды 0x30..0x39 идут подряд."""
    pos = codes.index(FIRST)
    got = codes[pos:pos + (LAST - FIRST + 1)]
    assert got == list(range(FIRST, LAST + 1)), \
        f'{label}: цифры не подряд в таблице имён: {got}'
    return data[pos * stride:(pos + len(got)) * stride]


lines = []
lines.append(';')
lines.append('; range_fonts.asm — шрифты режима прямого индекса (chars = 0) для')
lines.append('; теста roms/tests/fonts. Цифры 0x30..0x39, вырезанные из')
lines.append('; библиотечных шрифтов 512-режима: 16x8 (pr512.asm) и 4x8 тонкий')
lines.append('; (pr512t.asm). Таблицы имён у таких дескрипторов нет вовсе, глиф')
lines.append('; берётся как glyphs + (код - first_code) * шаг, а коды вне')
lines.append('; диапазона пропускуются: клетка остаётся нетронутой.')
lines.append(';')
lines.append('; Сгенерировано tools/gen_range_fonts.py из lib/gfx/fonts/default_*.inc,')
lines.append('; руками не править.')
lines.append(';')
lines.append('        SECTION code_clib')

blocks = []
for chars_label, glyphs_label, stride, fname in FONTS:
    src = (LIB / fname).read_text(encoding='utf-8')
    codes = name_table(src, chars_label)
    data = glyph_data(src, glyphs_label, stride)
    digits = digits_slice(codes, data, stride, chars_label)
    assert len(digits) == (LAST - FIRST + 1) * stride, len(digits)

    name = 'digits_16x8' if stride == 16 else 'digits_thin'
    blocks.append((name, stride, digits, chars_label, glyphs_label, fname))

lines.append('')
for name, stride, digits, chars_label, glyphs_label, fname in blocks:
    lines.append('; ---------------------------------------------------------------')
    lines.append(f'; {name}: {len(digits) // stride} глифов по {stride} байт '
                 f'(источник — {fname}, {glyphs_label})')
    lines.append('; ---------------------------------------------------------------')
    lines.append('')
    lines.append(f'{name}_glyphs:')
    for i in range(len(digits) // stride):
        body = ', '.join(f'0x{b:02X}' for b in digits[i * stride:(i + 1) * stride])
        lines.append(f'        defb    {body} ; \'{chr(FIRST + i)}\'')
    lines.append('')
    lines.append(f'_{name}:')
    lines.append('        defw    0                       ; chars = 0: прямой индекс')
    lines.append(f'        defw    {name}_glyphs')
    lines.append('        defw    0x30                    ; first_code')
    lines.append('        defw    0x39                    ; last_code')
    lines.append('')

pubs = [f'        PUBLIC  _{name}' for name, *_ in blocks]
lines = lines[:11] + pubs + lines[11:]

OUT.write_text('\n'.join(lines), encoding='utf-8')
for name, stride, digits, *_ in blocks:
    print(f'{OUT.name}: {name} — {len(digits) // stride} глифов '
          f'по {stride} байт = {len(digits)} байт данных, индекс 0 байт')
