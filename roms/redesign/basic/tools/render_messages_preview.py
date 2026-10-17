#!/usr/bin/env python3
"""Рендер пула сообщений об ошибках НАСТОЯЩИМ шрифтом знакогенератора.

Каждая строка пула (Stage 8, data_error_messages @ 0x2465) печатается побайтно
через растр data_glyph_block (Stage 7, 0x379F): код -> 5 колонок x 7 видимых
бит. Это «то, что реально покажет экран», — независимая проверка и кодов
кириллицы (104=Х / 118=Ж), и порядка строк пула.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/render_messages_preview.py
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage7_glyphs import GLYPH_ADDR, GLYPH_STRIDE
from stage8_data import MSG_ADDR, KEYWORD_ADDR, decode_strings

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_OUT = "roms/redesign/basic/reports/messages_preview.png"

SCALE = 3          # пикселей на «бит» растра
CELLW = GLYPH_STRIDE * SCALE + SCALE   # ширина глифа + межсимвольный зазор
LINEH = 8 * SCALE + 8                  # высота строки текста


def _cols(image, code):
    off = GLYPH_ADDR + (code & 0x7F) * GLYPH_STRIDE
    return [image[off + x] for x in range(GLYPH_STRIDE)]


def draw_text(d, image, x, y, raw, ink=(235, 235, 235)):
    """Печатаем raw-байты строки (bit7-терминаторы игнорируются кодом &0x7F)."""
    cx = x
    for b in raw:
        code = b & 0x7F
        if code == 0x0D or code == 0x0A:      # CR/LF — перевод строки не рисуем
            continue
        for col in range(GLYPH_STRIDE):
            bits = _cols(image, code)[col]
            for row in range(8):
                if (bits >> row) & 1:
                    px = cx + col * SCALE
                    py = y + row * SCALE
                    d.rectangle([px, py, px + SCALE - 1, py + SCALE - 1],
                                fill=ink)
        cx += CELLW
    return cx


def render(image, out_path):
    strings = decode_strings(image, MSG_ADDR, KEYWORD_ADDR - 1)
    n = len(strings)
    widest = max((len(s) for _, s in strings), default=16)
    canvas = Image.new("RGB", (widest * CELLW + 20, n * LINEH + 12),
                       (24, 24, 28))
    d = ImageDraw.Draw(canvas)
    for i, (addr, raw) in enumerate(strings):
        y = 6 + i * LINEH
        d.line([(0, y - 2), (canvas.size[0], y - 2)], fill=(60, 60, 66))
        draw_text(d, image, 6, y, raw)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    canvas.save(out_path)
    return out_path, canvas.size, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    with open(args.rom, "rb") as fh:
        image = fh.read()
    out, size, n = render(image, args.out)
    print("записан %s (%dx%d, %d строк пула)" % (out, size[0], size[1], n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
