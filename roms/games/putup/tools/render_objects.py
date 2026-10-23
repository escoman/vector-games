#!/usr/bin/env python3
"""Вывод всех игровых объектов (тайлов 2x2) во всех фазах в PNG.

Объекты движка рисуются тайлами 2x2: запись = 4 кода глифов (TL,TR,BL,BR),
порядок подтверждён func_render_tile_vram (0x1BA8) и func_enemy_build_cache
(var_ed_gcodes: строка0 = коды[0],[1], строка1 = коды[2],[3]). Два источника
истины видов/фаз:

  * asm/data/data_tile_table_26DE.asm — 11 записей объектов/игрока
    (индекс x4 = var_obj_type_idx): кадры героя [0..7], спец-выход [8], пусто [9],
    тёмный выход/мигание [10] (Фаза 4).
  * asm/data/data_tile_graphics.asm — 22 записи тайл-карты (индекс x4 = байт
    карты уровня / слот спавна): стены, платформы, обе фазы огня (0x75/0xFE),
    яйца/фрукты/кольцо, кадры анимации шага врага (var_page_flip+0Eh/10h).

Коды глиф-блока и палитра читаются теми же парсерами, что и render_glyphs.py
(импорт из того же каталога tools/): compact/raw тег по data_glyph_ptr_table,
палитра 16 слотов BBGGGRRR из func_main_init. Инверсия E000 запечена в данных —
рендер побайтовый, без XOR.

Использование: python3 tools/render_objects.py [-o objects.png] [--scale 6]
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

sys.path.insert(0, HERE)
from render_glyphs import (  # noqa: E402
    GLYPHS_ASM, PTR_ASM, MAIN_ASM, parse_block, parse_palette, glyph_pixels,
    DEFB_HEX,
)

OBJ_ASM = os.path.join(PROJ, "asm", "data", "data_tile_table_26DE.asm")
MAP_ASM = os.path.join(PROJ, "asm", "data", "data_tile_graphics.asm")

# Роль символа по коду (ALGORITHM.MD §0) — только логически значимые коды.
ROLES = {
    0x20: "пусто", 0x60: "безопас. блок", 0x6D: "низ предметов",
    0x6E: "фрукт n", 0x6F: "фрукт o", 0x70: "фрукт p", 0x71: "фрукт q",
    0x72: "яйцо/бонус r", 0x73: "кольцо s", 0x74: "выход t",
    0x75: "огонь A", 0x76: "граница v", 0x77: "стена w", 0x78: "стена x",
    0xFE: "огонь B", 0x00: "NUL",
}
# Подписи записей объекта (из комментариев data_tile_table_26DE + func_game_update).
OBJ_TAGS = {
    8: "спец: выход/пусто", 9: "пусто (пробелы)",
    10: "тёмный выход (мигание)",
}


def hexvals(line):
    return [int(t, 16) for t in DEFB_HEX.findall(line.split(";")[0])]


def read_records(path, expect):
    """Собирает поток DEFB-кодов и режет на записи по 4 -> [ [c0,c1,c2,c3], ... ]."""
    stream = []
    for line in open(path, encoding="utf-8"):
        stream += hexvals(line)
    whole = len(stream) - len(stream) % 4          # целые записи по 4 (хвост отбрасываем)
    recs = [stream[i:i + 4] for i in range(0, whole, 4)]
    if expect and len(recs) != expect:
        print("внимание: %s: записей %d, ожидалось %d (остаток %d Б)" %
              (os.path.basename(path), len(recs), expect, len(stream) % 4))
    return recs


def tile_pixels(codes, glyphs):
    """Запись 2x2 -> 16x16 плоский список индексов палитры (row-major)."""
    g = [glyph_pixels(*glyphs[c]) for c in codes]      # 4x (8x8)
    px = []
    for band, (a, b) in enumerate([(g[0], g[1]), (g[2], g[3])]):  # (TL,TR),(BL,BR)
        for row in range(8):
            px += a[row * 8:row * 8 + 8] + b[row * 8:row * 8 + 8]
    return px


def record_label(codes):
    """Краткая роль записи по кодам: уникальные логические символы внутри."""
    roles = []
    for c in codes:
        r = ROLES.get(c)
        if r and r not in roles:
            roles.append(r)
    if not roles:
        return "графика"
    return ", ".join(roles[:2]) + (" …" if len(roles) > 2 else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(PROJ, "objects.png"))
    ap.add_argument("--scale", type=int, default=6, help="пикселей на пиксель тайла")
    ap.add_argument("--cols", type=int, default=11, help="записей в ряду сетки тайл-карты")
    args = ap.parse_args()

    from PIL import Image, ImageDraw, ImageFont

    def load_font(px):
        """TrueType с кириллицей; фолбэк — дефолтный битмап (тогда ASCII)."""
        for path in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ):
            try:
                return ImageFont.truetype(path, px)
            except OSError:
                continue
        return ImageFont.load_default()

    f_cap, f_hdr = load_font(10), load_font(15)

    glyphs, _ = parse_block(GLYPHS_ASM)
    palette = parse_palette(MAIN_ASM)
    S = args.scale
    TS = 16 * S                                   # размер тайла 2x2 (16x16 px)
    pad_x, pad_y = 6, 30                          # поля подписи под тайлом
    cell_w = max(TS + pad_x, 132)                # шире тайла, чтобы подпись не налазила
    cell_h = TS + pad_y
    head_h = 30

    obj_recs = read_records(OBJ_ASM, 11)
    map_recs = read_records(MAP_ASM, 22)

    # Объектные записи — в один ряд (их 11).
    obj_cols = min(len(obj_recs), 11)
    W = max(obj_cols, args.cols) * cell_w + pad_x
    H = head_h + ((len(obj_recs) + obj_cols - 1) // obj_cols) * cell_h \
        + head_h + ((len(map_recs) + args.cols - 1) // args.cols) * cell_h + pad_x
    img = Image.new("RGB", (W, H), (40, 40, 40))
    dr = ImageDraw.Draw(img)

    def draw_tile(x, y, codes, cap):
        px = tile_pixels(codes, glyphs)
        for yy in range(16):
            for xx in range(16):
                c = palette[px[yy * 16 + xx]]
                dr.rectangle([x + xx * S, y + yy * S,
                              x + xx * S + S - 1, y + yy * S + S - 1], fill=c)
        dr.rectangle([x, y, x + TS - 1, y + TS - 1], outline=(90, 90, 90))
        dr.text((x, y + TS + 2), cap[0], fill=(220, 220, 220), font=f_cap)
        if cap[1]:
            dr.text((x, y + TS + 12), cap[1], fill=(150, 200, 150), font=f_cap)

    # --- Секция 1: data_tile_table_26DE (объекты/герой/фазы выхода) ---
    y = 4
    dr.text((pad_x, y), "data_tile_table_26DE — объекты/игрок (%d записей)"
            % len(obj_recs), fill=(255, 220, 120), font=f_hdr)
    y += head_h
    for i, codes in enumerate(obj_recs):
        col, row = i % obj_cols, i // obj_cols
        x = pad_x + col * cell_w
        cap = ("[%d] %s" % (i, " ".join("%02X" % c for c in codes)),
               OBJ_TAGS.get(i, record_label(codes)))
        draw_tile(x, y + row * cell_h, codes, cap)

    # --- Секция 2: data_tile_graphics (тайл-карта: стены/огонь/предметы/враги) ---
    y += ((len(obj_recs) + obj_cols - 1) // obj_cols) * cell_h + 4
    dr.text((pad_x, y), "data_tile_graphics — тайл-карта (%d записей)"
            % len(map_recs), fill=(255, 220, 120), font=f_hdr)
    y += head_h
    for i, codes in enumerate(map_recs):
        col, row = i % args.cols, i // args.cols
        x = pad_x + col * cell_w
        cap = ("[%d] %s" % (i, " ".join("%02X" % c for c in codes)),
               record_label(codes))
        draw_tile(x, y + row * cell_h, codes, cap)

    img.save(args.out)
    print("объектов: %d (tile_table) + %d (tile_graphics), сохранено: %s (%dx%d)"
          % (len(obj_recs), len(map_recs), args.out, img.width, img.height))


if __name__ == "__main__":
    main()
