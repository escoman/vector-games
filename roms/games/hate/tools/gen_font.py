#!/usr/bin/env python3
"""gen_font.py — шрифт 8x8 H.A.T.E. из ZX-оригинала в include/font.asm.

Источник — `assets/font_6300.bin`: дамп шрифта оригинала по адресу $6300
(96 слотов по 8 байт, индекс = код символа − $20, как в рутине окна
$EE54: SUB $20 / ×8 / +$6300).

ЧТО ИЗ НЕГО БЕРЁМ. Осмысленно заполнены только слоты $20..$3A и
$40..$5A. Слоты $3B..$3F и $5B..$7F заняты не глифами, а строками движка
(«BEN DAGLISH», «WRITTEN BY», «COSTA PANAYI», «MUSIC BY») и графикой —
их в шрифт не берём. Круглых скобок в шрифте HATE нет вообще: на месте
$28/$29 лежат UDG, а знак копирайта — это код `@` ($40), им и набрана
строка «@1989 VORTEX SOFTWARE» в тайтле оригинала.

ФОРМАТ. Как в lib/gfx/fonts/default_8x8.inc: глиф = 8 байт, строка 0 —
верхняя, бит 7 — левый пиксель; font_chars перечисляет символы в том же
порядке и заканчивается нулём (индекс глифа = позиция в таблице).
pr.asm собирается с -Ca-DFONT_EXTERNAL и берёт эти две метки как EXTERN.

Использование:
    python3 tools/gen_font.py            # assets/font_6300.bin -> include/font.asm
    python3 tools/gen_font.py --preview  # + assets/font_preview.png (сверка)
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'assets' / 'font_6300.bin'
OUT = ROOT / 'include' / 'font.asm'
PREVIEW = ROOT / 'assets' / 'font_preview.png'

FIRST = 0x20                  # первый код в дампе: индекс = код - FIRST
# Знаки, которые реально есть в игре и нужны порту: пробел, цифры, ':' для
# HUD, знак копирайта (код '@' оригинала) и латиница.
CHARS = ' 0123456789:@ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# Контрольные глифы: смещение в дампе ловит главную ошибку — чтение не того
# слота (индекс = код, а не код - $20).
KNOWN = {
    ' ': '0000000000000000',
    'A': '0000081c367f6300',
    '0': '00003e6363633e00',
}


def load():
    data = SRC.read_bytes()
    if len(data) != 96 * 8:
        raise SystemExit('%s: ожидалось 768 байт шрифта, а там %d'
                         % (SRC.name, len(data)))
    glyphs = {}
    for ch in CHARS:
        off = (ord(ch) - FIRST) * 8
        glyphs[ch] = data[off:off + 8]
    for ch, want in KNOWN.items():
        got = glyphs[ch].hex()
        if got != want:
            raise SystemExit('глиф %r не совпал с эталоном: %s вместо %s'
                             % (ch, got, want))
    return glyphs


def emit(glyphs):
    lines = [
        ';',
        '; font.asm — шрифт 8x8 H.A.T.E. (Vortex, 1989) для Вектора-06Ц.',
        ';',
        '; СГЕНЕРИРОВАНО tools/gen_font.py — руками не править.',
        ';',
        '; Источник — assets/font_6300.bin: дамп шрифта оригинала по $6300',
        '; (96 слотов по 8 байт, индекс = код символа - $20 — так его адресует',
        '; рутина окна $EE54). Взяты только те слоты, где в оригинале лежат',
        '; глифы: пробел, цифры, \':\', латиница A-Z и знак копирайта — в',
        '; шрифте HATE это код \'@\' (им набрано «@1989 VORTEX SOFTWARE»).',
        '; Круглых скобок в шрифте нет: слоты $28/$29 — графика, не скобки.',
        ';',
        '; Формат — как lib/gfx/fonts/default_8x8.inc: глиф 8 байт, строка 0',
        '; верхняя, бит 7 левый пиксель; font_chars задаёт порядок глифов и',
        '; заканчивается нулём. pr.asm подключает это как шрифт по умолчанию',
        '; при сборке с -Ca-DFONT_EXTERNAL (см. Makefile).',
        ';',
        '        SECTION code_clib',
        '        PUBLIC  font_chars',
        '        PUBLIC  font8x8',
        '',
        'font_chars:',
        '        defm    "%s"' % CHARS,
        '        defb    0',
        '',
        '; Глифы 8x8: строка 0 — верхняя, бит 7 — левый пиксель.',
        'font8x8:',
    ]
    for ch in CHARS:
        label = "' '" if ch == ' ' else "'%s'" % ch
        if ch.isalpha() or ch.isdigit() or ch == ':':
            label += ' ($%02X)' % ord(ch)
        elif ch == '@':
            label += ' — знак копирайта, код оригинала'
        lines.append('        defb    %s  ; %s'
                     % (', '.join('0x%02X' % b for b in glyphs[ch]), label))
    lines.append('')
    OUT.write_text('\n'.join(lines), encoding='utf-8')
    return len(CHARS)


def preview(glyphs):
    """Лист глифов в 3x для сверки глазами."""
    scale, cell, label_h, cols = 3, 8 * 3, 12, 8
    rows = (len(CHARS) + cols - 1) // cols
    pad = 4
    w = cols * (cell + pad) + pad
    h = rows * (cell + label_h + pad) + pad
    im = Image.new('RGB', (w, h), (16, 16, 16))
    dr = ImageDraw.Draw(im)
    for i, ch in enumerate(CHARS):
        cx = pad + (i % cols) * (cell + pad)
        cy = pad + (i // cols) * (cell + label_h + pad)
        for y in range(8):
            row = glyphs[ch][y]
            for x in range(8):
                if row & (0x80 >> x):
                    dr.rectangle([cx + x * scale, cy + y * scale,
                                  cx + x * scale + scale - 1,
                                  cy + y * scale + scale - 1],
                                 fill=(0xD7, 0xD7, 0xD7))
        dr.text((cx, cy + cell + 1), repr(ch)[1:-1].upper() or '_',
                fill=(0x80, 0x80, 0x80))
    im.save(PREVIEW)
    return PREVIEW


def main():
    ap = argparse.ArgumentParser(description='шрифт HATE 8x8 → include/font.asm')
    ap.add_argument('--preview', action='store_true',
                    help='записать assets/font_preview.png для сверки')
    args = ap.parse_args()

    glyphs = load()
    n = emit(glyphs)
    print('%s -> %s: %d глифов, %d байт данных'
          % (SRC.relative_to(ROOT), OUT.relative_to(ROOT), n, n * 8))
    print('  знаки: %s' % ' '.join("'%s'" % c if c != ' ' else "' '" for c in CHARS))
    if args.preview:
        print('  превью: %s' % preview(glyphs))


if __name__ == '__main__':
    main()
