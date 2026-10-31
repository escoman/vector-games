#!/usr/bin/env python3
"""Дамп шрифта меню Cybernoid (Vector-06C) из ROM в PNG и INC.

Формат глифа: 8×8 монохромный, 8 байт на глиф.
  - База: 0x2700
  - Индексация: offset = 0x2700 + (code - 0x24) * 8
  - 1 байт на строку, MSB = левый пиксель
  - Строка 0 = верх глифа

Использование:
    python3 dump_menu_font.py [--from 0x20] [--to 0x7F] [--out menu_font.png]
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = os.path.join(HERE, "..", "src", "cybernoid_unpacked.r0m")

FONT_BASE = 0x2700
FONT_OFFSET = 0x24  # смещение индексации
GLYPH_BYTES = 8
GW = GH = 8

COLS = 16
SCALE = 4
GAP = 1
LABEL_H = 11


def glyph_bitmap(data, code):
    """Декодирует глиф в битовую карту 8×8."""
    offset = FONT_BASE + (code - FONT_OFFSET) * GLYPH_BYTES
    if offset < 0 or offset + GLYPH_BYTES > len(data):
        return [[0]*GW for _ in range(GH)]
    raw = data[offset:offset + GLYPH_BYTES]
    rows = []
    for r in range(GH):
        byte = raw[r]
        line = []
        for c in range(GW):
            bit = (byte >> (7 - c)) & 1
            line.append(bit)
        rows.append(line)
    return rows


def render_sheet(data, from_code, to_code):
    """Рендерит лист глифов в PIL.Image."""
    count = to_code - from_code + 1
    rows = (count + COLS - 1) // COLS
    cell_w = GW * SCALE + GAP * 2
    cell_h = GH * SCALE + GAP * 2 + LABEL_H
    img_w = COLS * cell_w + GAP
    img_h = rows * cell_h + GAP
    img = Image.new("RGB", (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 9)
    except:
        font = ImageFont.load_default()

    for idx in range(count):
        code = from_code + idx
        col = idx % COLS
        row = idx // COLS
        x0 = GAP + col * cell_w
        y0 = GAP + row * cell_h

        bmp = glyph_bitmap(data, code)
        for r in range(GH):
            for c in range(GW):
                if bmp[r][c]:
                    draw.rectangle(
                        [x0 + GAP + c*SCALE, y0 + GAP + r*SCALE,
                         x0 + GAP + (c+1)*SCALE - 1, y0 + GAP + (r+1)*SCALE - 1],
                        fill=(0, 0, 0)
                    )
        draw.text((x0 + GAP, y0 + GAP + GH*SCALE + 1), f"{code:02X}", fill=(100, 100, 100), font=font)

    return img


def export_inc(data, from_code, to_code, out_path):
    """Экспорт в INC-файл (z80asm format)."""
    with open(out_path, "w") as f:
        f.write("; Cybernoid menu font glyphs (8x8 mono, 8 bytes/glyph)\n")
        f.write(f"; Codes: 0x{from_code:02X}..0x{to_code:02X}\n")
        f.write(f"; Base address: 0x{FONT_BASE:04X}\n")
        f.write(f"; Indexing: offset = base + (code - 0x{FONT_OFFSET:02X}) * 8\n")
        f.write("; Format: 1 byte/row, MSB=left, row 0=top\n")
        f.write(";\n\n")
        f.write("data_menu_font:\n")
        for code in range(from_code, to_code + 1):
            offset = FONT_BASE + (code - FONT_OFFSET) * GLYPH_BYTES
            if offset < 0 or offset + GLYPH_BYTES > len(data):
                raw = b'\x00' * GLYPH_BYTES
            else:
                raw = data[offset:offset + GLYPH_BYTES]
            f.write(f"    ; char 0x{code:02X} ('{chr(code) if 32 <= code < 127 else '?'}')\n")
            bytes_str = ", ".join(f"0x{b:02X}" for b in raw)
            f.write(f"    defb {bytes_str}\n")
            f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Dump Cybernoid menu font to PNG and INC")
    parser.add_argument("--from", dest="from_code", type=lambda x: int(x, 0), default=0x20,
                        help="Start character code (hex, default 0x20)")
    parser.add_argument("--to", dest="to_code", type=lambda x: int(x, 0), default=0x7F,
                        help="End character code (hex, default 0x7F)")
    parser.add_argument("--out", default=os.path.join(HERE, "..", "menu_font.png"),
                        help="Output PNG path")
    parser.add_argument("--inc", default=os.path.join(HERE, "..", "asm", "data", "menu_font.inc"),
                        help="Output INC path")
    args = parser.parse_args()

    if not os.path.exists(ROM):
        print(f"ROM not found: {ROM}")
        return

    data = open(ROM, "rb").read()
    print(f"Рендерю глифы меню 0x{args.from_code:02X}..0x{args.to_code:02X}...")
    img = render_sheet(data, args.from_code, args.to_code)
    img.save(args.out)
    print(f"Сохранено: {args.out}")

    print(f"Экспорт в INC: {args.inc}...")
    os.makedirs(os.path.dirname(args.inc), exist_ok=True)
    export_inc(data, args.from_code, args.to_code, args.inc)
    print(f"Сохранено: {args.inc}")


if __name__ == "__main__":
    main()
