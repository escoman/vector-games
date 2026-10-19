#!/usr/bin/env python3
"""Цвет-гейт: сравнение РАСКРАШЕННОГО экрана orig <-> new (не байт VRAM).

Зачем: когда представление в VRAM намеренно меняется (например, инверсия
плоскости E000 + компенсация палитрой) побайтовая сверка VRAM больше не годится
— плоскости разные, а КАРТИНКА та же. Этот инструмент восстанавливает итоговый
цвет каждого пикселя (4 битовые плоскости -> индекс цвета -> палитра ROM) и
сравнивает цветные изображения orig и new на совпадающих CPU-кадрах.

Маппинг плоскостей (docs/VECTOR_VERIFIED.md, VSDL): 0x8000=бит3(w8),
0xA000=бит2(w4), 0xC000=бит1(w2), 0xE000=бит0(w1); в байте бит7=левый пиксель.
Палитра: слот S = mem[0x08A3+S] (пишет func_vblank_isr OUT 02h/0Ch), 16 цветов.

Использование: python3 tools/compare_color.py [--new ROM] [--label C]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(PROJ, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "utils", "analyze"))

from mcp_session import McpSession, bytes_of  # noqa: E402

# переиспользуем кадровую механику compare_behavior.py (тот же каталог)
_spec = importlib.util.spec_from_file_location("cb", os.path.join(HERE, "compare_behavior.py"))
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)

PLANES = (0x8000, 0xA000, 0xC000, 0xE000)   # веса 8,4,2,1 (порядок = бит3..бит0)
WEIGHTS = (8, 4, 2, 1)
PALETTE_ADDR = 0x08A3
PALETTE_LEN = 16


def capture_vram(s):
    return bytes_of(s.call("debug_get_vram_bytes", {"address": 0x8000, "length": 32768}))


def capture_palette(s):
    return bytes_of(s.call("debug_read_memory_range", {"address": PALETTE_ADDR, "length": PALETTE_LEN}))


def decode_colors(vram, palette):
    """-> bytearray длиною 8192*8: итоговый цвет каждого пикселя (плоскость-байт,бит)."""
    rows = 8192
    out = bytearray(rows * 8)
    for i in range(rows):
        b3 = vram[i]                       # 0x8000 w8
        b2 = vram[8192 + i]                # 0xA000 w4
        b1 = vram[16384 + i]               # 0xC000 w1*... w2
        b0 = vram[24576 + i]               # 0xE000 w1
        for bit in range(8):
            m = 0x80 >> bit
            idx = (8 if b3 & m else 0) + (4 if b2 & m else 0) + (2 if b1 & m else 0) + (1 if b0 & m else 0)
            out[i * 8 + bit] = palette[idx]
    return out


def run_phase_cap(s, rom_path):
    """Оригинальный прогон compare_behavior + снимок палитры и плоскостей по фазам."""
    s.load_rom(rom_path, org=0x0100)
    palette = capture_palette(s)
    cb.run_frames(s, cb.WARMUP)
    caps = {}
    cb.run_frames(s, cb.F_TITLE)
    caps["title"] = (capture_vram(s), palette)
    s.call("debug_type_key", {"key": "SPACE"})
    cb.run_frames(s, cb.F_PLAY1)
    caps["play1"] = (capture_vram(s), palette)
    s.call("debug_type_key", {"key": "LEFT"})
    cb.run_frames(s, cb.F_LEFT)
    s.call("debug_type_key", {"key": "RIGHT"})
    cb.run_frames(s, cb.F_RIGHT)
    caps["play2"] = (capture_vram(s), palette)
    return caps


def count_diff(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", default=os.path.join(PROJ, "PUTUP_NEW.ROM"))
    ap.add_argument("--label", default="C")
    args = ap.parse_args()

    lines, result = [], {}
    with McpSession() as s:
        cap_o = run_phase_cap(s, cb.ORIG)
        cap_n = run_phase_cap(s, args.new)

    # плоскости: E000 должен инвертироваться, остальные — не меняться
    for ph in ("title", "play1", "play2"):
        vo, vn = cap_o[ph][0], cap_n[ph][0]
        pl = []
        for name, base in zip(("w8", "w4", "w2", "E000w1"), PLANES):
            o = vo[base - 0x8000: base - 0x8000 + 8192]
            n = vn[base - 0x8000: base - 0x8000 + 8192]
            pl.append("%s:%d" % (name, count_diff(o, n)))
        lines.append("плоскости %-6s diffs orig<>new  %s" % (ph, "  ".join(pl)))
        # цвета: ожидаем 0 расхождений
        co = decode_colors(vo, cap_o[ph][1])
        cn = decode_colors(vn, cap_n[ph][1])
        d = count_diff(co, cn)
        result["color_" + ph] = d
        lines.append("РАСКРАШЕНО %-6s: цвет-расхождений %d / %d" % (ph, d, len(co)))
    lines.append("палитра orig: %s" % cap_o["title"][1].hex())
    lines.append("палитра new : %s" % cap_n["title"][1].hex())
    ok = all(result["color_" + ph] == 0 for ph in ("title", "play1", "play2"))
    lines.append("ВЕРДИКТ: %s (картинка идентична)" % ("OK" if ok else "РАСХОЖДЕНИЕ ЦВЕТОВ"))
    print("\n".join(lines))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
