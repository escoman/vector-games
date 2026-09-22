#!/usr/bin/env python3
"""PUTUP → лист глифов PNG: конкретные символы растром из живого шрифта.

Специфичное для PUTUP (карта «символ → глиф» и подписи) живёт здесь; сам
разбор 8×8-растра по плоскостям переиспользуется из общего
`analyze.glyph_scan` (ТЗ §23 — Python рисует то, что нашёл, а «это буква А»
здесь никто не распознаёт: порядок глифов — детерминированный факт ROM).

Факты из Stage 7 (`reports/Stage7.md`, всё MCP-подтверждено):
  * блок глифов — RAM @0x6000, 256 глифов × 32 байта (4 плоскости × 8 строк);
  * строится в рантайме `func_load_glyph_block` из упакованного шрифта @0x3041,
    поэтому читаем RUNTIME после прогона, а не образ ROM;
  * индекс глифа = код символа: рендерер берёт word[0x0600 + char*2] =
    0x6000 + char*32; кодировка — KOI8-R (в нём цифры/A–Z совпадают с ASCII);
  * плоскости 0/1/2 = битмап символа, plane3 = ~plane0 (инверс-фон).

Что рисуем на выходе (по ТЗ пользователя):
  * каждая буква — отдельный столбец 8×32 пикселя = 32 байта глифа;
    это 4 плоскости столбиком (plane0 строки 0–7, plane1 8–15, plane2 16–23,
    plane3 24–31), каждая окрашена своим цветом — «полная 4-плоскостная палитра»;
  * порядок строк каждой плоскости перевёрнут (row0↔row7): на экране Vector-06C
    глифы стоят на голове относительно прямого порядка байт в таблице;
  * два листа: латиница/цифры (0–9 A–Z) и кириллица (А–Я KOI8-R).

    python3 roms/redesign/putup/tools/glyph_sheet.py
    python3 roms/redesign/putup/tools/glyph_sheet.py --chars "ФЫВ" --no-cyrillic
"""
from __future__ import annotations

import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if os.path.join(REPO, "utils") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "utils"))

from analyze.mcp_session import open_session          # noqa: E402
from analyze.memory_diff import RuntimeSource         # noqa: E402
from analyze.probe import run_for                     # noqa: E402
from analyze.glyph_scan import glyph_planes, _load_pil  # noqa: E402

GLYPH_BLOCK = 0x6000       # RAM-адрес начала блока глифов
GLYPH_STRIDE = 32          # 4 плоскости × 8 строк × 1 байт
GLYPH_W = GLYPH_H = 8
PLANES = 4
COLUMN_H = GLYPH_H * PLANES          # 32 — высота столбца на глиф

# Цвет каждой плоскости — читаемость; настоящая палитра железа здесь не утверждается.
PLANE_COLORS = [(0, 0, 255), (0, 160, 0), (220, 0, 0), (150, 0, 150)]
BG = (255, 255, 255)

LATIN = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CYRILLIC = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def char_index(ch):
    """Индекс глифа = байт символа в KOI8-R (латиница/цифры там же, где ASCII)."""
    try:
        return ch.encode("koi8-r")[0]
    except (UnicodeEncodeError, LookupError):
        return ord(ch) & 0xFF


def stacked_column(data, index, flip=True):
    """Глиф №index → столбец 8×32: 4 плоскости столбиком, каждая 8×8.

    Возвращает список из 32 строк по 8 значений: 0=фон, 1..4 = плоскость 0..3.
    flip=True переворачивает порядок строк внутри каждой плоскости (row0↔row7).
    """
    start = index * GLYPH_STRIDE
    planes = glyph_planes(data, start, GLYPH_W, GLYPH_H, "planar", GLYPH_STRIDE)
    column = []
    for plane in range(PLANES):
        rows = planes[plane] if plane < len(planes) else []
        rows = list(rows)[:GLYPH_H]
        if flip:
            rows = rows[::-1]
        for y in range(GLYPH_H):
            line = rows[y] if y < len(rows) else []
            column.append([1 + plane if (x < len(line) and line[x]) else 0
                           for x in range(GLYPH_W)])
    return column


def load_block(rom, org, seconds, cache, server):
    """Один RUNTIME-заезд: прогон ROM (строит блок) и чтение всего блока."""
    session, cache_obj = open_session(rom=rom, org=org, server=server,
                                      cache_dir=cache)
    try:
        run_for(session, cache_obj, rom=rom, org=org, seconds=seconds)
        source = RuntimeSource(session, cache_obj)
        data = source.read(GLYPH_BLOCK, GLYPH_BLOCK + 256 * GLYPH_STRIDE - 1)
        return list(data), session.stats()["total_calls"]
    finally:
        session.close()


def render_sheet(Image, chars, data, out, scale=6, columns=12, margin=8,
                 caption=18, flip=True):
    """Один PNG: столбцы 8×32 (4 плоскости цвет-в-цвет) с подписью символа."""
    cell_w = GLYPH_W * scale
    cell_h = COLUMN_H * scale
    cols = min(columns, len(chars))
    rows = math.ceil(len(chars) / cols)
    pitch_w = cell_w + margin * 2
    pitch_h = cell_h + caption + margin
    sheet = Image.new("RGB", (cols * pitch_w, rows * pitch_h), BG)
    try:
        from PIL import ImageDraw, ImageFont
        drawer = ImageDraw.Draw(sheet)
        font = ImageFont.load_default()
    except Exception:                                   # pragma: no cover
        drawer = font = None
    for i, ch in enumerate(chars):
        r, c = divmod(i, cols)
        ox, oy = c * pitch_w + margin, r * pitch_h + margin
        idx = char_index(ch)
        column = stacked_column(data, idx, flip=flip)
        for y in range(COLUMN_H):
            line = column[y]
            for x in range(GLYPH_W):
                v = line[x] if x < len(line) else 0
                if v:
                    color = PLANE_COLORS[v - 1]
                    for dy in range(scale):
                        for dx in range(scale):
                            sheet.putpixel((ox + x * scale + dx,
                                            oy + y * scale + dy), color)
        if drawer is not None:
            label = "%c %02X" % (ch, idx)
            bbox = drawer.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            drawer.text((ox + max(0, (cell_w - tw) // 2), oy + cell_h + 2),
                        label, fill=(0, 0, 0), font=font)
    sheet.save(out)
    return out


def parse_chars(text):
    return "".join(dict.fromkeys(text))   # без повторов, порядок сохраняем


def main(argv=None):
    p = argparse.ArgumentParser(prog="putup.glyph_sheet",
                                description="Лист глифов PUTUP → PNG "
                                            "(столбец 8×32 = 4 плоскости)")
    p.add_argument("--rom", default=os.path.join(HERE, "..", "src", "putup.rom"))
    p.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    p.add_argument("--chars", default=LATIN,
                   help="латынь/цифры (по умолчанию 0-9 A-Z)")
    p.add_argument("--cyrillic", default=CYRILLIC,
                   help="кириллица (по умолчанию А–Я с Ё)")
    p.add_argument("--no-cyrillic", dest="cyrillic", action="store_const",
                   const="", help="не делать кириллический лист")
    p.add_argument("--out", default=os.path.join(HERE, "..", "glyph_sheet.png"))
    p.add_argument("--out-cyrillic",
                   default=os.path.join(HERE, "..", "glyph_sheet_cyrillic.png"))
    p.add_argument("--run", type=float, default=3.0,
                   help="секунд прогона ROM перед чтением RAM (блок строится на старте)")
    p.add_argument("--scale", type=int, default=6)
    p.add_argument("--columns", type=int, default=12)
    p.add_argument("--no-flip", dest="flip", action="store_false",
                   help="оставить прямой порядок строк (по умолчанию — вертикальный переворот)")
    p.add_argument("--cache", default=os.path.join(HERE, "..", ".analyze"))
    p.add_argument("--server", default=None)
    p.set_defaults(flip=True)
    args = p.parse_args(argv)

    data, calls = load_block(args.rom, args.org, args.run, args.cache,
                             args.server)
    Image = _load_pil()
    made = []
    latin = parse_chars(args.chars)
    if latin:
        made.append(render_sheet(Image, latin, data, os.path.abspath(args.out),
                                 scale=args.scale, columns=args.columns,
                                 flip=args.flip))
    cyr = parse_chars(args.cyrillic)
    if cyr:
        made.append(render_sheet(Image, cyr, data,
                                 os.path.abspath(args.out_cyrillic),
                                 scale=args.scale, columns=args.columns,
                                 flip=args.flip))
    print("лист(ов): %d, блок: 0x%04X.. (RUNTIME), переворот: %s"
          % (len(made), GLYPH_BLOCK, "вкл" if args.flip else "выкл"))
    for path in made:
        print("  PNG:", path)
    print("# mcp calls: %d" % calls, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
