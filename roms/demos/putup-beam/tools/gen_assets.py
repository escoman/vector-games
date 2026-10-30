#!/usr/bin/env python3
"""Конвертер ассетов демо putup-beam: глифы putup -> 16x16 SPR_FORMAT.

Вход — asm-данные roms/games/putup (DEFB-потоки, без ROM/map):
  * data_glyph_block_unpacked.asm + data_glyph_ptr_table.asm — глифы Tier-2
    (бит0 указателя = тег compact: 8 Б только плоскость 0x8000; иначе raw
    32 Б = [П3×8][П2×8][П1×8][П0×8], байт 0 = НИЖНЯЯ строка экрана);
  * data_tile_graphics.asm — 22 записи карт-тайлов [TL,TR,BL,BR] (порядок
    доказан func_draw_tile_to_buf.asm);
  * data_tile_table_26DE.asm — записи объектов: [0..6] кадры героя
    (idx = work_const + 3*move_dir - 1), [7]/[10] светлая/тёмная фазы выхода,
    [8] погонщик;
  * data_level_01.asm — коды клеток (какие bg-тайлы нужны);
  * func_main_init.asm — data_palette (16 байт BBGGGRRR).

Выход — assets.inc (в корне демо):
  * bg_tile_NNN / bg_tiles[25] — ПЛОСКИЕ дескрипторы 16x16 клеток: ВСЕ 4
    плоскости, SHIFT=0/LEN=16 без обрезки (erase обязан перезаписывать
    клетку целиком). Индексы 22/23 — светлая/тёмная фазы выхода,
    [24] — bg_lock_key: СИНТЕЗИРОВАННЫЙ «замок с вставленным ключом»
    (в putup замка нет — рисуем по палитре игры; код 24 = закрытый выход);
  * hero_N_v0/v1 — MASK-дескрипторы кадров героя: маска = П0 (¬S, как
    entry+24 в func_render_tile_vram_or), цвет = все 4 плоскости verbatim
    (композиция (dst&m)|c побайтно совпадает с OR-рендером putup);
  * enemy_<вид>_<фаза>_v0/v1 — плоские дескрипторы врагов (обрезка нулевых
    строк): walker = tg[20]/tg[19] (state1/state2 putup), crow =
    tg[18]/tg[17], heli = tg[15]/tg[16] (два положения ротора);
  * *_v1 — вариант со сдвигом вправо на 4px (3 столбца; выметенные нибли:
    маска 0xF, цвет 0). Субшаг 8px = v0 на x+8, 12px = v1 на x+8.

Гейт: round-trip — каждый дескриптор декодируется обратно в пиксели и
сверяется с эталоном, собранным из глифов putup (логика render_glyphs.py).

Запуск: python3 tools/gen_assets.py [--png preview.png]
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.dirname(HERE)
PUTUP = os.path.join(DEMO, "..", "..", "games", "putup")
OUT_INC = os.path.join(DEMO, "assets.inc")

DEFB_HEX = re.compile(r"(?<![0-9A-Za-z_])0?([0-9A-Fa-f]{1,3})h(?![0-9A-Za-z_])")
PTR_WORD = re.compile(r"data_glyph_block\+(\d+)")


def hexvals(line):
    return [int(t, 16) for t in DEFB_HEX.findall(line.split(";")[0])]


def parse_table(path, label, expect=None):
    """DEFB-поток после метки label -> список байтов."""
    vals, seen = [], False
    for line in open(path, encoding="utf-8"):
        if line.startswith(label):
            seen = True
            continue
        if seen and line.strip().startswith("DEFB"):
            vals += hexvals(line)
    if not seen:
        sys.exit("%s: метка %s не найдена" % (path, label))
    if expect and len(vals) < expect:
        sys.exit("%s: %d байт, ожидалось >= %d" % (path, len(vals), expect))
    return vals


def parse_glyphs():
    """-> {glyph: (kind, planes)}; planes = [П3,П2,П1,П0] по 8 байт (байт 0 = низ)."""
    stream = parse_table(os.path.join(PUTUP, "asm", "data",
                                      "data_glyph_block_unpacked.asm"),
                         "data_glyph_block")
    ptrs = []
    in_table = False
    for line in open(os.path.join(PUTUP, "asm", "data",
                                  "data_glyph_ptr_table.asm"), encoding="utf-8"):
        if line.startswith("data_glyph_ptr_table"):
            in_table = True
        if in_table:
            ptrs += [int(t, 10) for t in PTR_WORD.findall(line)]
    if len(ptrs) != 256:
        sys.exit("ptr_table: %d слов, ожидалось 256" % len(ptrs))
    glyphs = {}
    for g, w in enumerate(ptrs):
        kind = "compact" if (w & 1) else "raw"
        size = 8 if kind == "compact" else 32
        off = (w & 0xFFFE) if kind == "compact" else w
        chunk = stream[off:off + size]
        if len(chunk) != size:
            sys.exit("глиф %d (%s @+%d): байтов %d < %d" %
                     (g, kind, off, len(chunk), size))
        planes = [bytes(chunk[i * 8:(i + 1) * 8]) for i in range(4)] \
            if kind == "raw" else [bytes(chunk), bytes(8), bytes(8), bytes(8)]
        glyphs[g] = (kind, planes)
    return glyphs


def parse_palette():
    txt = open(os.path.join(PUTUP, "asm", "funcs", "func_main_init.asm"),
               encoding="utf-8").read()
    tail = txt.split("data_palette:", 1)[1].split("func_main_init:", 1)[0]
    vals = [v for line in tail.splitlines() for v in hexvals(line)]
    if len(vals) != 16:
        sys.exit("палитра: %d значений, ожидалось 16" % len(vals))
    return vals


# ---------- сборка 16x16 из записи [TL,TR,BL,BR] ----------

def tile_cols(glyphs, codes):
    """Запись 2x2 -> cols[pi] = (left16, right16), байты СВЕРХУ вниз.

    Байт 0 глифа = нижняя строка экрана (render_glyphs.py), поэтому
    переворачиваем: TL[7..0] ++ BL[7..0]."""
    tl, tr, bl, br = (glyphs[c] for c in codes)
    cols = []
    for pi in range(4):
        left = tl[1][pi][::-1] + bl[1][pi][::-1]
        right = tr[1][pi][::-1] + br[1][pi][::-1]
        cols.append((bytes(left), bytes(right)))
    return cols


def trim(col16):
    """(SHIFT, LEN, data): первая/последняя ненулевая строка; пусто -> LEN=0."""
    nz = [i for i, b in enumerate(col16) if b]
    if not nz:
        return 0, 0, b""
    s, e = nz[0], nz[-1]
    return s, e - s + 1, col16[s:e + 1]


def shift4_cols(left, right, vac):
    """Сдвиг 16px-строки вправо на 4px -> 3 столбца по 8px (24 бита/строка).

    vac — биты выметенных ниблей (маска: 0xF0000F, цвет: 0)."""
    out = [bytearray(), bytearray(), bytearray()]
    for r in range(16):
        v = ((left[r] << 8 | right[r]) << 4) | vac
        out[0].append((v >> 16) & 0xFF)
        out[1].append((v >> 8) & 0xFF)
        out[2].append(v & 0xFF)
    return [bytes(c) for c in out]


# ---------- синтезированный тайл «замок с вставленным ключом» ----------
# В putup замка нет (ключ 0x72 — предмет-бонус, выход — только табличка
# EXIT), поэтому закрытый выход демо рисуется здесь по палитре игры:
# g/8 — серый корпус (idx 8), W — белая дужка/блик (14), y — ключ (10),
# 0/. — фон и замочная скважина (0). Код клетки 24 (см. main.c CODE_LOCK).
LOCK_ART = [
    "................",
    ".......WWWWWW...",
    ".......W....W...",
    ".......W....W...",
    ".......W....W...",
    ".......W....W...",
    "....ggggggggggg.",
    "....gWWWWWWWWWg.",
    "....g888888888g.",
    "....g888888888g.",
    ".yy.g888800888g.",
    "y..yg888800888g.",
    "y..yyyyyyy8888g.",
    "y..yyyyyyy8888g.",
    ".yy.g888888888g.",
    "....ggggggggggg.",
]
LOCK_COLORS = {".": 0, "0": 0, "g": 8, "8": 8, "W": 14, "y": 10}


def art_cols(art, colors):
    """16x16 индексов палитры -> cols[pi] = (left8, right8), СВЕРХУ вниз
    (тот же формат, что tile_cols, — дальше идёт обычная сборка/round-trip)."""
    for y, row in enumerate(art):
        if len(row) != 16:
            sys.exit("арт, строка %d: %d символов, нужно 16" % (y, len(row)))
    cols = []
    for pi in range(4):
        left, right = bytearray(), bytearray()
        for y in range(16):
            l = r = 0
            for x in range(16):
                if colors[art[y][x]] & (1 << pi):
                    if x < 8:
                        l |= 0x80 >> x
                    else:
                        r |= 0x80 >> (x - 8)
            left.append(l)
            right.append(r)
        cols.append((bytes(left), bytes(right)))
    return cols


# ---------- построение дескрипторов ----------

def build_flat(cols, ncols, do_trim):
    """Плоский spr_blit-дескриптор: [FLAGS,COLS,DEPTH] + по П3..П0 столбцы."""
    body = bytearray()
    depth = 0
    for pi in range(4):
        for c in range(ncols):
            if do_trim:
                s, l, d = trim(cols[pi][c])
            else:
                s, l, d = 0, 16, cols[pi][c]
            depth = max(depth, s + l)
            body += bytes([s, l]) + d
    return bytes([0x0F, ncols, depth]) + bytes(body)


def build_mask(mcols, pcols, ncols):
    """MASK-дескриптор: TABLE [0,16] на столбец, маска ПЕРВЫМ блоком, затем
    4 плоскости цвета (порядок П3..П0). Без обрезки (LEN=16 <= 28)."""
    head = bytes([0x1F, ncols, 16])
    table = b"".join(bytes([0, 16]) for _ in range(ncols))
    data = b"".join(mcols) + b"".join(b"".join(pc) for pc in pcols)
    return head + table + data


def hero_variant(cols, shift):
    """v0: 2 столбца verbatim; v1: сдвиг 4px — 3 столбца, маска выметенных 0xF."""
    if shift == 0:
        mcols = [cols[3][0], cols[3][1]]
        pcols = [[cols[pi][0], cols[pi][1]] for pi in range(4)]
        return build_mask(mcols, pcols, 2)
    mcols = shift4_cols(cols[3][0], cols[3][1], 0xF0000F)
    pcols = [shift4_cols(cols[pi][0], cols[pi][1], 0) for pi in range(4)]
    return build_mask(mcols, pcols, 3)


def flat_variant(cols, shift):
    """v0: 2 столбца с обрезкой; v1: сдвиг 4px — 3 столбца с обрезкой."""
    if shift == 0:
        return build_flat(cols, 2, do_trim=True)
    scols = [shift4_cols(cols[pi][0], cols[pi][1], 0) for pi in range(4)]
    out = bytearray()
    depth = 0
    for pi in range(4):
        for c in range(3):
            s, l, d = trim(scols[pi][c])
            depth = max(depth, s + l)
            out += bytes([s, l]) + d
    return bytes([0x0F, 3, depth]) + bytes(out)


# ---------- round-trip: декодирование дескриптора обратно в пиксели ----------

def decode_flat(desc):
    """-> grid[pi][col] = [16 байт] (нули вне прогона)."""
    flags, ncols = desc[0], desc[1]
    assert flags == 0x0F, "flat: FLAGS=%02X" % flags
    grid = [[[0] * 16 for _ in range(ncols)] for _ in range(4)]
    off = 3
    for pi in range(4):
        for c in range(ncols):
            s, l = desc[off], desc[off + 1]
            grid[pi][c][s:s + l] = list(desc[off + 2:off + 2 + l])
            off += 2 + l
    return grid


def decode_mask(desc):
    """-> (mask[ncols][16], color[4][ncols][16])."""
    flags, ncols = desc[0], desc[1]
    assert flags == 0x1F, "mask: FLAGS=%02X" % flags
    off = 3 + 2 * ncols
    mask = [list(desc[off + c * 16:off + (c + 1) * 16]) for c in range(ncols)]
    off += ncols * 16
    color = []
    for pi in range(4):
        color.append([list(desc[off + c * 16:off + (c + 1) * 16])
                      for c in range(ncols)])
        off += ncols * 16
    return mask, color


def expect_cols(cols, shift):
    """Эталон: shift=0 -> cols как есть (2 столбца); shift=4 -> 3 столбца."""
    if shift == 0:
        return [[list(cols[pi][c]) for c in range(2)] for pi in range(4)]
    return [[list(c) for c in shift4_cols(cols[pi][0], cols[pi][1], 0)]
            for pi in range(4)]


def grids_equal(a, b):
    return len(a) == len(b) and all(x == y for ga, gb in zip(a, b)
                                    for x, y in zip(ga, gb))


# ---------- общее с редактором уровня (tools/level_editor.py) ----------

# bg-коды: всё, что есть в уровне, + ВСЕ предметы putup (07h — яйцо-бонус,
# 0Ah..0Dh — фрукты: вишни/яблоко/ананас/виноград, 0Eh — кольцо), чтобы
# карта могла использовать любой вид (в level_01 есть только 10h/11h).
BG_FIXED = {0, 1, 7, 10, 11, 12, 13, 14}

# виды врагов: (имя, записи data_tile_graphics по фазам). walker = state1/2
# putup (направление), crow = ворона (направление), heli = два положения ротора.
ENEMY_RECORDS = (("enemy_walker", (20, 19)),
                 ("enemy_crow", (18, 17)),
                 ("enemy_heli", (15, 16)))


def bg_codes(lvl):
    """Коды клеток, для которых печатаются bg-тайлы (порядок = bg_tile_NNN)."""
    return sorted(BG_FIXED | set(lvl[:176]))


def editor_gfx():
    """Графика для редактора уровня: -> (palette, клетки, актёры).

    клетки = {код: cols} — ровно те коды, что печатает main() (bg_codes()),
    плюс 22/23 (фазы выхода) и 24 (замок). актёры = {"hero": [cols x7],
    "enemy": [[cols по фазам] по видам]} — для маркеров спавнов на карте.
    """
    glyphs = parse_glyphs()
    palette = parse_palette()
    tg = parse_table(os.path.join(PUTUP, "asm", "data",
                                  "data_tile_graphics.asm"),
                     "data_tile_graphics", expect=88)
    tg_records = [tg[i * 4:i * 4 + 4] for i in range(22)]
    tt = parse_table(os.path.join(PUTUP, "asm", "data",
                                  "data_tile_table_26DE.asm"),
                     "data_tile_table_26DE", expect=44)
    tt_records = [tt[i * 4:i * 4 + 4] for i in range(11)]
    lvl = parse_table(os.path.join(PUTUP, "asm", "data", "data_level_01.asm"),
                      "data_level_01", expect=176)
    cells = {c: tile_cols(glyphs, tg_records[c]) for c in bg_codes(lvl)}
    cells[22] = tile_cols(glyphs, tt_records[7])
    cells[23] = tile_cols(glyphs, tt_records[10])
    cells[24] = art_cols(LOCK_ART, LOCK_COLORS)
    actors = {"hero": [tile_cols(glyphs, tt_records[r]) for r in range(7)],
              "enemy": [[tile_cols(glyphs, tg_records[ph]) for ph in recs]
                        for _name, recs in ENEMY_RECORDS]}
    return palette, cells, actors


# ---------- генерация assets.inc ----------


def c_array(name, data):
    lines = ["static const unsigned char %s[] = {" % name]
    for i in range(0, len(data), 16):
        lines.append("    " + ", ".join("0x%02X" % b
                                        for b in data[i:i + 16]) + ",")
    lines.append("};")
    return "\n".join(lines)


def render_preview(path, items, palette):
    """Лист-превью: (name, cols) в палитре putup, 16x16 на элемент."""
    from PIL import Image, ImageDraw
    rgb = [((b & 7) * 255 // 7, ((b >> 3) & 7) * 255 // 7,
            ((b >> 6) & 3) * 255 // 3) for b in palette]
    S, per = 3, 16 * 3 + 12
    img = Image.new("RGB", (per * 4 + 8, per * ((len(items) + 3) // 4) + 8),
                    (40, 40, 40))
    dr = ImageDraw.Draw(img)
    for i, (name, cols) in enumerate(items):
        row, col = divmod(i, 4)
        x0, y0 = 8 + col * per, 8 + row * per
        for y in range(16):
            for xb in range(2):
                for bit in range(8):
                    m = 0x80 >> bit
                    idx = sum((8 >> pi) if cols[pi][xb][y] & m else 0
                              for pi in range(4))
                    dr.rectangle([x0 + (xb * 8 + bit) * S, y0 + y * S,
                                  x0 + (xb * 8 + bit) * S + S - 1,
                                  y0 + y * S + S - 1], fill=rgb[idx])
        dr.text((x0, y0 + 48 + 1), name, fill=(200, 200, 200))
    img.save(path)
    print("превью: %s" % path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", help="сохранить лист-превью (нужен PIL)")
    args = ap.parse_args()

    glyphs = parse_glyphs()
    palette = parse_palette()
    tg = parse_table(os.path.join(PUTUP, "asm", "data",
                                  "data_tile_graphics.asm"),
                     "data_tile_graphics", expect=88)
    tg_records = [tg[i * 4:i * 4 + 4] for i in range(22)]
    tt = parse_table(os.path.join(PUTUP, "asm", "data",
                                  "data_tile_table_26DE.asm"),
                     "data_tile_table_26DE", expect=44)
    tt_records = [tt[i * 4:i * 4 + 4] for i in range(11)]
    lvl = parse_table(os.path.join(PUTUP, "asm", "data",
                                   "data_level_01.asm"),
                      "data_level_01", expect=176)

    # маска героя требует raw-глифов (П0 = ¬S); проверить до генерации
    for r in range(7):
        for c in tt_records[r]:
            if glyphs[c][0] != "raw":
                sys.exit("кадр героя [%d]: глиф %d compact — нет плоскости маски"
                         % (r, c))

    codes = bg_codes(lvl)
    errors = []
    preview = []
    total = 0
    parts = ["/* assets.inc — АВТОГЕНЕРАЦИЯ: tools/gen_assets.py, не править.",
             " * Клетка карты putup 2x2 глифа 8x8 -> ОДИН дескриптор 16x16",
             " * SPR_FORMAT (docs/SPR_FORMAT.MD). Байты дескриптора — сверху",
             " * вниз (ядро пишет dcx h); байт 0 глифа putup — нижняя строка.",
             " */",
             "#ifndef ASSETS_INC",
             "#define ASSETS_INC",
             ""]

    # --- bg-тайлы: все 4 плоскости, без обрезки (erase = полная перезапись) ---
    parts.append("/* Фон: плоские 16x16 клетки. bg_tiles[0..21] = коды тайлов")
    parts.append(" * putup, [22] = светлая фаза выхода (tile_table[7]),")
    parts.append(" * [23] = тёмная (tile_table[10], мигание), [24] = замок с")
    parts.append(" * вставленным ключом (синтез: bg_lock_key, закрытый выход). */")
    bg_have = {}
    bg_sets = [("bg_tile_%03X" % c, tile_cols(glyphs, tg_records[c]))
               for c in codes]
    bg_sets += [("bg_exit_light", tile_cols(glyphs, tt_records[7])),
                ("bg_exit_dark", tile_cols(glyphs, tt_records[10])),
                ("bg_lock_key", art_cols(LOCK_ART, LOCK_COLORS))]
    for sym, cols in bg_sets:
        desc = build_flat(cols, 2, do_trim=False)
        if not grids_equal(decode_flat(desc), expect_cols(cols, 0)):
            errors.append("round-trip %s" % sym)
        bg_have[sym] = desc
        total += len(desc)
        preview.append((sym, cols))
        parts.append(c_array(sym, desc))
        parts.append("")
    ptrs = [("bg_tile_%03X" % c if c in codes else "bg_tile_000")
            for c in range(22)]
    ptrs += ["bg_exit_light", "bg_exit_dark", "bg_lock_key"]
    parts.append("static const unsigned char *const bg_tiles[25] = {")
    for i in range(0, 25, 5):
        parts.append("    " + ", ".join(ptrs[i:i + 5]) + ",")
    parts.append("};")
    parts.append("")

    # --- герой: 7 кадров x {v0, v1} mask-дескрипторы ---
    parts.append("/* Герой: mask-дескрипторы (spr_blit_mask). Маска = П0 (¬S),")
    parts.append(" * цвет = все 4 плоскости verbatim — композиция (dst&m)|c")
    parts.append(" * побайтно равна func_render_tile_vram_or putup.")
    parts.append(" * Кадр idx = work_const + 3*move_dir - 1: 0,1 = шаг вправо,")
    parts.append(" * 2 = стойка вправо, 3,4 = шаг влево, 5 = стойка влево, 6 = доп.")
    parts.append(" * v1 = сдвиг 4px вправо (3 столбца); субшаг X: 0->v0@x,")
    parts.append(" * 4->v1@x, 8->v0@(x+8), 12->v1@(x+8). */")
    hero_tabs = []
    for r in range(7):
        cols = tile_cols(glyphs, tt_records[r])
        preview.append(("hero_%d" % r, cols))
        syms = []
        for v, shift in ((0, 0), (1, 4)):
            sym = "hero_%d_v%d" % (r, v)
            desc = hero_variant(cols, shift)
            mask, color = decode_mask(desc)
            ecolor = expect_cols(cols, shift)
            emask = ecolor[3] if shift == 0 else \
                [list(c) for c in shift4_cols(cols[3][0], cols[3][1], 0xF0000F)]
            if mask != emask or not grids_equal(color, ecolor):
                errors.append("round-trip %s" % sym)
            syms.append(sym)
            total += len(desc)
            parts.append(c_array(sym, desc))
            parts.append("")
        hero_tabs.append(syms)
    parts.append("static const unsigned char *const hero_frames[7][2] = {")
    for syms in hero_tabs:
        parts.append("    { %s, %s }," % tuple(syms))
    parts.append("};")
    parts.append("")

    # --- враги: три вида x 2 фазы x {v0, v1}, плоские + v1 ---
    parts.append("/* Враги: плоские дескрипторы (spr_blit), обрезка нулевых")
    parts.append(" * строк. enemy_frames[вид][фаза][субшаг]: walker = tg[20]/")
    parts.append(" * tg[19] (направление, state1/state2 putup), crow = tg[18]/") 
    parts.append(" * tg[17] (направление), heli = tg[15]/tg[16] (фазы ротора).")
    parts.append(" * Субшаги X — как у героя. */")
    enemy_tabs = []
    for name, recs in ENEMY_RECORDS:
        for ph, rec in enumerate(recs):
            cols = tile_cols(glyphs, tg_records[rec])
            preview.append(("%s_%d" % (name, ph), cols))
            syms = []
            for v, shift in ((0, 0), (1, 4)):
                sym = "%s_%d_v%d" % (name, ph, v)
                desc = flat_variant(cols, shift)
                if not grids_equal(decode_flat(desc), expect_cols(cols, shift)):
                    errors.append("round-trip %s" % sym)
                syms.append(sym)
                total += len(desc)
                parts.append(c_array(sym, desc))
                parts.append("")
            enemy_tabs.append(syms)
    parts.append("static const unsigned char *const enemy_frames[3][2][2] = {")
    for t in range(3):
        parts.append("    {")
        for ph in range(2):
            parts.append("        { %s, %s }," % tuple(enemy_tabs[t * 2 + ph]))
        parts.append("    },")
    parts.append("};")
    parts.append("")

    # --- палитра putup ---
    parts.append("/* data_palette putup (BBGGGRRR): E000-инверсия запечена в")
    parts.append(" * глифы и компенсирована свапом слотов — писать verbatim. */")
    parts.append(c_array("asset_palette", bytes(palette)))
    parts.append("")
    parts.append("#endif /* ASSETS_INC */")

    if errors:
        for e in errors:
            print("FAIL:", e)
        sys.exit(1)

    with open(OUT_INC, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print("assets.inc: %d байт данных (bg=%d, герой=7x2, враги=3x2x2)" %
          (total, len(bg_have)))
    print("round-trip: OK")
    print("bg-коды level_01: %s" % ", ".join("%02Xh" % c for c in codes))

    if args.png:
        render_preview(args.png, preview, palette)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
