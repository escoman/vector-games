#!/usr/bin/env python3
"""Рендер всех 128 глифов знакогенератора в PNG для визуальной сверки.

Карта кодов -> букв берётся из stage7_glyphs.CYRILLIC (источник истины),
растр — побайтово из образа basic.r0m по data_glyph_block (0x379F).
Формат глифа: 5 колонок x 8 бит (bit0=верх — служебный зазор, видимы
bit1..bit7 => шрифт 5x7). Коды 96..126 — кириллица, 33..95 — ASCII.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/render_glyphs_chart.py
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage7_glyphs import (CYRILLIC, GLYPH_ADDR, GLYPH_COUNT, GLYPH_STRIDE,
                           glyph_name)

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_OUT = "roms/redesign/basic/reports/glyphs_chart.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PER_ROW = 16


def _ascii_art(image, code):
    off = GLYPH_ADDR + (code & 0x7F) * GLYPH_STRIDE
    cols = [image[off + x] for x in range(GLYPH_STRIDE)]
    return [[(cols[x] >> r) & 1 for x in range(GLYPH_STRIDE)] for r in range(8)]


def render(image, out_path, scale=8, cell_pad=6, label_h=26):
    cell_w = GLYPH_STRIDE * scale + cell_pad * 2
    cell_h = 8 * scale + label_h
    rows = (GLYPH_COUNT + PER_ROW - 1) // PER_ROW
    canvas = Image.new("RGB", (PER_ROW * cell_w, rows * cell_h), (24, 24, 28))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(FONT, 13)
    except OSError:
        font = ImageFont.load_default()
    for code in range(GLYPH_COUNT):
        r, c = divmod(code, PER_ROW)
        x0, y0 = c * cell_w, r * cell_h
        art = _ascii_art(image, code)
        for row in range(8):
            for col in range(GLYPH_STRIDE):
                if art[row][col]:
                    px = x0 + cell_pad + col * scale
                    py = y0 + 2 + row * scale
                    d.rectangle([px, py, px + scale - 1, py + scale - 1],
                                fill=(235, 235, 235))
        if code in CYRILLIC:
            label = "%d %s" % (code, CYRILLIC[code])
            color = (240, 170, 70)
        elif code == 32:
            label, color = "32 sp", (120, 220, 120)
        elif code == 127:
            label, color = "127 blk", (120, 220, 120)
        elif 33 <= code <= 95:
            label, color = "%d %s" % (code, chr(code)), (120, 220, 120)
        else:
            label, color = "%d #%d" % (code, code), (150, 150, 170)
        d.text((x0 + 2, y0 + 8 * scale + 4), label, fill=color, font=font)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    canvas.save(out_path)
    return out_path, canvas.size


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    with open(args.rom, "rb") as fh:
        image = fh.read()
    out, size = render(image, args.out)
    print("записан %s (%dx%d, %d глифов)" % (out, size[0], size[1], GLYPH_COUNT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
