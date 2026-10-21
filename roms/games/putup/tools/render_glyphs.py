#!/usr/bin/env python3
"""Вывод всех 256 глифов блока data_glyph_block в PNG (диагностика/обзор графики).

Источник истины — asm/data/data_glyph_ptr_table.asm: слово = data_glyph_block+OFF,
бит0 OFF = ТЕГ compact (1 = 8-байтная маска плоскости 0x8000; 0 = raw 32 Б =
4 плоскости подряд). Сами байты читаются из потока DEFB в
asm/data/data_glyph_block_unpacked.asm. Палитру берёт из
data_palette в asm/funcs/func_main_init.asm (16 слотов BBGGGRRR: биты 7-6 B, 5-3 G, 2-0 R,
см. docs/VECTOR_VERIFIED.md §7.3.1).

Цвета пикселя = биты плоскостей с весами 8(0x8000),4(0xA000),2(0xC000),1(0xE000) —
как в tools/compare_color.py; инверсия E000 (Фаза 3) уже запечена в данных и
компенсируется свапом слотов палитры, поэтому рендер побайтовый, без XOR.

Использование: python3 tools/render_glyphs.py [-o glyphs.png] [--scale 4]
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

GLYPHS_ASM = os.path.join(PROJ, "asm", "data", "data_glyph_block_unpacked.asm")
PTR_ASM = os.path.join(PROJ, "asm", "data", "data_glyph_ptr_table.asm")
MAIN_ASM = os.path.join(PROJ, "asm", "funcs", "func_main_init.asm")

DEFB_HEX = re.compile(r"(?<![0-9A-Za-z_])0?([0-9A-Fa-f]{1,3})h(?![0-9A-Za-z_])")
PTR_WORD = re.compile(r"data_glyph_block\+(\d+)")


def hexvals(line):
    """DEFB-числа строки (0Nh/7Bh/Nh), комментарии ';' вырезаются."""
    return [int(t, 16) for t in DEFB_HEX.findall(line.split(";")[0])]


def parse_block(path):
    """-> {glyph: (kind, bytes)} по таблице указателей; поток DEFB — подряд."""
    stream = []
    for line in open(path, encoding="utf-8"):
        stream += hexvals(line)

    ptrs = []
    in_table = False
    for line in open(PTR_ASM, encoding="utf-8"):
        if line.startswith("data_glyph_ptr_table"):
            in_table = True
        if not in_table:
            continue
        ptrs += [int(t, 10) for t in PTR_WORD.findall(line)]
    if len(ptrs) != 256:
        sys.exit("ptr_table: %d слов, ожидалось 256" % len(ptrs))

    glyphs = {}
    for g, w in enumerate(ptrs):
        kind = "compact" if (w & 1) else "raw"
        size = 8 if kind == "compact" else 32
        off = w & 0xFFFE if kind == "compact" else w
        chunk = stream[off:off + size]
        if len(chunk) != size:
            sys.exit("глиф %d (%s @+%d): байтов %d < %d (всего в потоке %d)" %
                     (g, kind, off, len(chunk), size, len(stream)))
        glyphs[g] = (kind, bytes(chunk))
    return glyphs, len(stream)


def parse_palette(path):
    """16 байт data_palette -> [(r,g,b)] в 0..255."""
    txt = open(path, encoding="utf-8").read()
    tail = txt.split("data_palette:", 1)[1].split("func_main_init:", 1)[0]
    vals = [v for line in tail.splitlines() for v in hexvals(line)]
    if len(vals) != 16:
        sys.exit("палитра: %d значений, ожидалось 16" % len(vals))
    rgb = []
    for b in vals:
        blue = (b >> 6) & 3
        green = (b >> 3) & 7
        red = b & 7
        rgb.append((red * 255 // 7, green * 255 // 7, blue * 255 // 3))
    return rgb


def glyph_pixels(kind, data):
    """-> 8x8 список индексов палитры (row-major, верхняя строка первой).

    VRAM Вектора инвертирована по Y (адрес строки = 255 - Y, docs/VECTOR_VERIFIED.md
    §7.2), поэтому байт строки 0 глифа — НИЖНЯЯ строка на экране: разворачиваем
    порядок строк, как это делает обводка ЭЛТ снизу вверх.
    """
    planes = [data[0:8], data[8:16], data[16:24], data[24:32]] \
        if kind == "raw" else [data[0:8], bytes(8), bytes(8), bytes(8)]
    px = []
    for row in range(8):
        src = 7 - row                        # строка 0 данных = низ экрана
        for col in range(8):
            m = 0x80 >> col
            idx = (8 if planes[0][src] & m else 0) + (4 if planes[1][src] & m else 0) \
                + (2 if planes[2][src] & m else 0) + (1 if planes[3][src] & m else 0)
            px.append(idx)
    return px


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(PROJ, "glyphs.png"))
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--gap", type=int, default=2)
    args = ap.parse_args()

    from PIL import Image

    glyphs, nbytes = parse_block(GLYPHS_ASM)
    palette = parse_palette(MAIN_ASM)
    n_compact = sum(1 for k, _ in glyphs.values() if k == "compact")
    print("глифов: %d (compact=%d, raw=%d), поток DEFB = %d Б" %
          (len(glyphs), n_compact, len(glyphs) - n_compact, nbytes))

    S, G, COLS = args.scale, args.gap, 16
    cell = 8 * S
    per = cell + G + 20                    # +20 лекс. отступ подписей
    img = Image.new("RGB", (COLS * per + G, COLS * per + G), (52, 52, 52))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(img)
    for g in sorted(glyphs):
        kind, data = glyphs[g]
        row, col = divmod(g, COLS)
        x0 = G + col * per + 10
        y0 = G + row * per
        px = glyph_pixels(kind, data)
        for yy in range(8):
            for xx in range(8):
                c = palette[px[yy * 8 + xx]]
                dr.rectangle([x0 + xx * S, y0 + yy * S,
                              x0 + xx * S + S - 1, y0 + yy * S + S - 1], fill=c)
        dr.text((x0 - 8, y0 + 8 * S + 2), "%d" % g, fill=(200, 200, 200))
    img.save(args.out)
    print("сохранено: %s (%dx%d)" % (args.out, img.width, img.height))


if __name__ == "__main__":
    main()
