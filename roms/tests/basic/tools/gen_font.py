#!/usr/bin/env python3
"""Извлечь шрифт BASIC и собрать basic_font.asm для теста roms/tests/basic.

Шрифт BASIC (Вектор-06Ц, BASIC 2.997) лежит в RAM-образе реконструкции
`roms/redesign/basic/src/basic_new.r0m` (org 0x0000, значит смещение в
файле = адрес) по адресу 0x379F: 128 глифов x 5 байт. Формат — СТОЛБЦАМИ:
байт x (0..4) задаёт вертикальную колонку глифа, бит0 = верхний пиксель,
бит7 = нижний. Ровно этот формат и эти байты подтверждены живым прогоном
см. ../trace_glyph.py (diff VRAM на эталонном BASIC).

Инструмент ничего не поворачивает и не правит — перекладывает 640 байт
как есть в `defb`, чтобы рендерер теста сам делал transpose.

    python3 tools/gen_font.py            # пишет ../basic_font.asm
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BASIC_TEST = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(BASIC_TEST, "..", "..", ".."))
ROM = os.path.join(REPO, "roms", "redesign", "basic", "src", "basic_new.r0m")
OUT = os.path.join(BASIC_TEST, "basic_font.asm")

FONT_ADDR = 0x379F
GLYPHS, COLS = 128, 5
BYTES = GLYPHS * COLS

data = open(ROM, "rb").read()
if len(data) < FONT_ADDR + BYTES:
    raise SystemExit("образ %s короче, чем 0x%X+%d" % (ROM, FONT_ADDR, BYTES))
font = data[FONT_ADDR:FONT_ADDR + BYTES]

lines = []
lines.append(";")
lines.append("; basic_font.asm — шрифт BASIC 2.997 (Вектор-06Ц), 128 глифов x 5 байт.")
lines.append("; Формат: СТОЛБЦАМИ, байт x (0..4) = вертикальная колонка,")
lines.append("; бит0 = верхний пиксель .. бит7 = нижний. Источник байтов —")
lines.append("; basic_new.r0m @0x379F (подтверждено tools/trace_glyph.py на живом BASIC).")
lines.append("; Сгенерировано tools/gen_font.py, руками не править.")
lines.append(";")
lines.append("        SECTION code_clib")
lines.append("        PUBLIC  _basic_font")
lines.append("")
lines.append("_basic_font:")

for g in range(GLYPHS):
    cols = font[g * COLS:(g + 1) * COLS]
    hexs = ",".join("0x%02X" % b for b in cols)
    ch = chr(g) if 32 <= g < 127 else "?"
    lines.append("        defb    %s          ; %3d '%s'" % (hexs, g, ch))

open(OUT, "w").write("\n".join(lines) + "\n")
print("%s: %d глифов x %d байт = %d байт" % (OUT, GLYPHS, COLS, BYTES))
