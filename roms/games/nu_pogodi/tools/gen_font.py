#!/usr/bin/env python3
"""gen_font.py — кириллический шрифт 8x8 для «Ну, погоди!» (Вектор-06Ц).

Собирает src/font.asm: тот же набор кодов, что у шрифта по умолчанию
(lib/gfx/fonts/default_8x8.inc), но вместо латинских букв A..Z в глифы
положены русские из шрифта игры PUTUP (roms/tests/fonts/putup_font.asm).

Английские буквы в игре не нужны, поэтому код латинской буквы рендерится
транслитерированной кириллицей: чтобы в тексте ROM было видно, какая надпись
выводится, строки пишутся латиницей-транслитом и на экране становятся русскими:

    "IGRA"  -> ИГРА      "PAUZA" -> ПАУЗА     "DOM"  -> ДОМ
    "KLAV"  -> КЛАВ      "OTMENA"-> ОТМЕНА     "ZAB"  -> ЗАБ
    "VERH"  -> ВЕРХ      "VNIZ"  -> ВНИЗ       "STR"  -> СТР

Цифры, пробел и знаки (< - > : . , и т.д.) остаются как в дефолтном шрифте:
табло счёта — спрайты, а не текст, но знаки нужны для подписей клавиш ← →.

Шрифт подключается как шрифт по умолчанию: pr.asm собирается с
-Ca-DFONT_EXTERNAL и берёт font_chars/font8x8 как EXTERN из src/font.asm.

    python3 tools/gen_font.py            # перегенерить src/font.asm
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))

DEFAULT_INC = os.path.join(ROOT, 'lib/gfx/fonts/default_8x8.inc')
PUTUP_ASM = os.path.join(ROOT, 'roms/tests/fonts/putup_font.asm')
OUT = os.path.join(ROOT, 'roms/games/nu_pogodi/src/font.asm')

# Латинская буква кода -> русская буква (транслитерация, той же формы).
# Q/X/... подобраны так, чтобы все нужные игре слова собрались; неиспользуемые
# буквы просто занимают свободные глифы. В шрифте PUTUP нет Ч — её не просим.
LAT2CYR = {
    'A': 'А', 'B': 'Б', 'C': 'Ц', 'D': 'Д', 'E': 'Е', 'F': 'Ф', 'G': 'Г',
    'H': 'Х', 'I': 'И', 'J': 'Й', 'K': 'К', 'L': 'Л', 'M': 'М', 'N': 'Н',
    'O': 'О', 'P': 'П', 'Q': 'Ъ', 'R': 'Р', 'S': 'С', 'T': 'Т', 'U': 'У',
    'V': 'В', 'W': 'Ш', 'X': 'Щ', 'Y': 'Ы', 'Z': 'З',
}

GLYPH_RE = re.compile(r'defb\s+' +
                      r'((?:0x[0-9A-Fa-f]{2}\s*,?\s*){8})')


def parse_default(path):
    """font_chars (в порядке глифов) + список 8-байтных глифов того же порядка."""
    text = open(path, encoding='utf-8').read()
    # Таблица имён: defm "..." (может быть несколько defm/defb до defb 0).
    m = re.search(r'font_chars:\s*(.*?)\n\s*defb\s+0\b', text, re.S)
    body = m.group(1)
    chars = ''
    for s in re.findall(r'defm\s+"((?:[^"\\]|\\.)*)"', body):
        chars += s.encode().decode('unicode_escape')
    for c in re.findall(r"defb\s+'(.)'", body):
        chars += c
    for b in re.findall(r'defb\s+0x([0-9A-Fa-f]{2})', body):
        chars += chr(int(b, 16))
    # Глифы: каждая defb-строка с 8 байтами.
    glyphs = []
    gblock = text[text.index('font8x8:'):]
    for mm in GLYPH_RE.finditer(gblock):
        vals = [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', mm.group(1))]
        if len(vals) == 8:
            glyphs.append(vals)
    assert len(chars) == len(glyphs), (len(chars), len(glyphs))
    return chars, glyphs


def parse_putup_cyrillic(path):
    """{'А': [8 байт], ...} из секции с комментарием 'X (KOI8-R)'."""
    out = {}
    for line in open(path, encoding='utf-8'):
        if 'KOI8-R' not in line:
            continue
        mm = GLYPH_RE.search(line)
        if not mm:
            continue
        vals = [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', mm.group(1))]
        label = re.search(r"'(.)\s", line)
        if len(vals) == 8 and label:
            out[label.group(1)] = vals
    return out


def emit(chars, glyphs, cyr):
    lines = [""";
; font.asm — кириллический шрифт 8x8 «Ну, погоди!».
;
; СГЕНЕРИРОВАНО tools/gen_font.py — руками не править.
;
; Коды и порядок — как в lib/gfx/fonts/default_8x8.inc, но вместо латинских
; букв A..Z лежат русские из шрифта PUTUP (транслитерация: код 'R' рисует Р,
; 'P' рисует П, ...). Цифры и знаки — из дефолтного шрифта.
;
; pr.asm подключает этот шрифт как шрифт по умолчанию при сборке с
; -Ca-DFONT_EXTERNAL (см. Makefile): обе метки объявлены здесь как PUBLIC.
;
        SECTION code_clib
        PUBLIC  font_chars
        PUBLIC  font8x8

font_chars:
"""]
    # Таблица имён: печатаемые (кроме " и \) — defm-запятками, остальные — defb.
    run = ''
    for ch in chars:
        if 0x20 <= ord(ch) <= 0x7E and ch not in '"\\':
            run += ch
            continue
        if run:
            lines.append('        defm    "%s"\n' % run)
            run = ''
        if ch == '"':
            lines.append('        defb    \'"\'\n')
        else:
            lines.append('        defb    0x%02X\n' % ord(ch))
    if run:
        lines.append('        defm    "%s"\n' % run)
    lines.append('        defb    0\n\n')
    lines.append('; Глифы 8x8: строка 0 — верхняя, бит 7 — левый пиксель.\n')
    lines.append('font8x8:\n')
    for ch, g in zip(chars, glyphs):
        cyr_name = LAT2CYR.get(ch)
        data = cyr[cyr_name] if cyr_name else g
        note = ''
        if cyr_name:
            note = '  ; %s <- %s' % (cyr_name, ch)
        else:
            note = "  ; '%s'" % ch if ch != ' ' else '  ; space'
        lines.append('        defb    ' +
                     ', '.join('0x%02X' % v for v in data) + note + '\n')
    return ''.join(lines)


def main():
    chars, glyphs = parse_default(DEFAULT_INC)
    cyr = parse_putup_cyrillic(PUTUP_ASM)
    need = set(LAT2CYR.values())
    missing = need - set(cyr)
    assert not missing, 'нет глифов PUTUP для: %s' % ''.join(sorted(missing))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(emit(chars, glyphs, cyr))
    print('%s: %d глифов, %d букв заменено на кириллицу'
          % (OUT, len(glyphs), len(LAT2CYR)))


if __name__ == '__main__':
    main()
