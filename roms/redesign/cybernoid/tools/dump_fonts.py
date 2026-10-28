#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dump_fonts.py — выгрузка экранного шрифта Cybernoid в font.png.

Источник: `src/cybernoid_unpacked.r0m` (RAM-образ после самораспаковки,
org 0x0000, смещение в файле == адрес). Блок глифов — RDB-объект
`data_glyph_block` (метка 0x3780).

Формат глифа установлен ЭМПИРИЧЕСКИ изолированным прогоном func_render_glyph
через отладчик (см. .scratch/render_probe.py): копир func_111A читает 32 байта
от `метка + код*32 - 8` и раскладывает их в одну битовую плоскость VRAM.
Значит глиф = 16×16 монохромный, посточно, по 2 байта на строку:
  байт[2r]   = пиксели 0..7  строки r (MSB = левый пиксель),
  байт[2r+1] = пиксели 8..15 строки r,
строка 0 — верхняя. 16 строк × 16 пикселей = 256 бит = 32 байта.
Цвет (какая из 4 плоскостей) задаёт курсор вызывающего, в самом глифе — 1 бит.

Решётка: все глифы подряд (по умолчанию 0x00..0xFF) сеткой 16×16, каждый
подписан кодом. ROM-специфично (адрес блока), поэтому в tools/, а не utils/.
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("нужен Pillow (python3 -m pip install pillow)")

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = os.path.join(HERE, "..", "src", "cybernoid_unpacked.r0m")
GLYPH_LABEL = 0x3780        # метка data_glyph_block
READ_SHIFT = -8             # копир читает на 8 байт раньше метки
GLYPH_BYTES = 32
GW = GH = 16                # 16×16 моно
COLS = 16                   # глифов в строке решётки
SCALE = 3
GAP = 1
LABEL_H = 11


def glyph_bitmap(data, code):
    base = GLYPH_LABEL + code * GLYPH_BYTES + READ_SHIFT
    raw = data[base:base + GLYPH_BYTES]
    rows = []
    for r in range(GH):
        left = raw[2 * r] if 2 * r < len(raw) else 0
        right = raw[2 * r + 1] if 2 * r + 1 < len(raw) else 0
        line = []
        for c in range(GW):
            if c < 8:
                bit = (left >> (7 - c)) & 1
            else:
                bit = (right >> (7 - (c - 8))) & 1
            line.append(bit)
        rows.append(line)
    return rows


def render(data, lo, hi, out_path):
    n = hi - lo + 1
    rows = (n + COLS - 1) // COLS
    cw, ch = GW * SCALE, GH * SCALE
    cell_w, cell_h = cw + GAP, ch + GAP + LABEL_H
    img = Image.new("L", (COLS * cell_w + GAP, rows * cell_h + GAP), 255)
    draw = ImageDraw.Draw(img)
    for i in range(n):
        code = lo + i
        r, c = divmod(i, COLS)
        ox = GAP + c * cell_w
        oy = GAP + r * cell_h
        for y, line in enumerate(glyph_bitmap(data, code)):
            for x, bit in enumerate(line):
                if bit:
                    for dy in range(SCALE):
                        for dx in range(SCALE):
                            img.putpixel((ox + x * SCALE + dx,
                                          oy + y * SCALE + dy), 0)
        label = "%02X" % code
        if 0x21 <= code <= 0x7E:
            label += " " + chr(code)
        draw.text((ox + 1, oy + ch + 1), label, fill=110)
    img.save(out_path)
    print("%s: глифы 0x%02X..0x%02X (%d шт), сетка %d×%d, масштаб ×%d → %s"
          % (os.path.basename(out_path), lo, hi, n, COLS, rows, SCALE, out_path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="lo", type=lambda s: int(s, 0), default=0x00)
    ap.add_argument("--to", dest="hi", type=lambda s: int(s, 0), default=0xFF)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "font.png"))
    args = ap.parse_args()
    with open(ROM, "rb") as f:
        data = f.read()
    render(data, args.lo, args.hi, args.out)


if __name__ == "__main__":
    main()
