#!/usr/bin/env python3
"""Экспорт глифов шрифтов exolon в PNG-сетку.

Латиница (font1.png) — блок 0x2630, кириллица (font2.png) — блок 0x742D.
Каждый блок = 512 байт = 64 глифа по 8 байт (8×8 моно, MSB = левый пиксель).
Индекс глифа i ↔ ASCII-код 0x20+i (база-регистр на 0x100 ниже блока, см. Stage6).

Скрипт ROM-специфичный (адреса блоков exolon), поэтому в tools/, а не в utils/analyze.
"""
from __future__ import annotations

import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("нужен Pillow (python3 -m pip install pillow)")

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = os.path.join(HERE, "..", "src", "exolon.rom")
ORG = 0x0100
GLYPH_W = GLYPH_H = 8
COLS = 16          # 16 колонок × 4 ряда = 64 глифа
SCALE = 6
GAP = 2
LABEL_H = 14       # полоска под глифом с подписью кода

BLOCKS = [
    ("font1.png", 0x2630, "латиница"),
    ("font2.png", 0x742D, "кириллица"),
]


def read_bytes(data, addr, length):
    off = addr - ORG
    return data[off:off + length]


def render_font(data, block_addr, out_path, label):
    glyphs = read_bytes(data, block_addr, 64 * 8)
    rows = (64 + COLS - 1) // COLS
    cw = GLYPH_W * SCALE
    ch = GLYPH_H * SCALE
    cell_w = cw + GAP
    cell_h = ch + GAP + LABEL_H
    img = Image.new("L", (COLS * cell_w + GAP, rows * cell_h + GAP), 255)
    draw = ImageDraw.Draw(img)
    for i in range(64):
        r, c = divmod(i, COLS)
        ox = GAP + c * cell_w
        oy = GAP + r * cell_h
        for y in range(GLYPH_H):
            byte = glyphs[i * 8 + y]
            for x in range(GLYPH_W):
                ink = (byte >> (7 - x)) & 1
                if ink:
                    px, py = ox + x * SCALE, oy + y * SCALE
                    for dy in range(SCALE):
                        for dx in range(SCALE):
                            img.putpixel((px + dx, py + dy), 0)
        # подпись ASCII-кода (и печатного символа, если он печатается)
        code = 0x20 + i
        ch_ = chr(code)
        text = "%02X%s" % (code, (" " + ch_) if 0x21 <= code <= 0x7E else "")
        draw.text((ox, oy + ch + 1), text, fill=90)
    img.save(out_path)
    print("%-10s <- блок 0x%04X (%s): %d глифов, сетка %dx%d → %s"
          % (os.path.basename(out_path), block_addr, label, 64, COLS, rows,
             out_path))


def main():
    with open(ROM, "rb") as f:
        data = f.read()
    out_dir = os.path.join(HERE, "..")
    for name, addr, label in BLOCKS:
        render_font(data, addr, os.path.join(out_dir, name), label)


if __name__ == "__main__":
    main()
