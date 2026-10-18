#!/usr/bin/env python3
"""Восстановление точного алгоритма вывода глифа шрифтом BASIC.

Шрифт BASIC (ROM @0x379F, 128 глифов x 5 байт) хранится СТОЛБЦАМИ:
  байт x (0..4) = вертикальная колонка, бит0 = верхний пиксель .. бит7 = нижний.
Кадр Вектора-06Ц (256x256) хранится СТРОКАМИ-байтами:
  один байт = 8 ГОРИЗОНТАЛЬНЫХ пикселей, бит7 = самый левый;
  адрес пикселя (X,Y) в плоскости = base + (X//8)*0x100 + (255 - Y).
Поэтому между форматом шрифта и кадром нужен поворот на 90° (transpose),
а горизонтальное позиционирование — попиксельное (ячейка 6px не кратна 8px).

Скрипт печатает ряд букв на эталонном READY и по diff-у VRAM показывает,
в какие байты/биты/пиксели ложатся биты каждой колонки глифа. Это и есть
экспериментально подтверждённое отображение «формат шрифта -> пиксели».

    PYTHONPATH=utils python3 roms/redesign/basic/tools/trace_glyph.py
    PYTHONPATH=utils python3 .../trace_glyph.py --word TIV
"""
from __future__ import annotations

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASIC = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(BASIC, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "utils"))

from analyze.mcp_session import bytes_of, open_session   # noqa: E402

ROM = os.path.join(BASIC, "src", "bas2997.rom")
ORG = 0x0100
FONT_ROM = 0x379F
FONT_GLYPHS, FONT_COLS = 128, 5
VRAM_LO, VRAM_LEN = 0x8000, 0x8000
CURSOR_VAR = 0x3D8D           # var_cursor_vram: HL текст.курсора (16 бит)
# Цветность шрифта (в каком порядке плоскости идут в дампе 0x8000..0xFFFF).
PLANE_BASES = [0xE000, 0xC000, 0xA000, 0x8000]


def read_mem(session, addr, length):
    return bytes_of(session.call("debug_read_memory_range",
                                 {"address": addr, "length": length}))


def vram_read(session):
    return bytes_of(session.call("debug_get_vram_bytes",
                                 {"address": VRAM_LO, "length": VRAM_LEN}))


def capture(session, blink_gap=0.4):
    v1 = vram_read(session)
    time.sleep(blink_gap)
    v2 = vram_read(session)
    blink = {i for i in range(min(len(v1), len(v2))) if v1[i] != v2[i]}
    return v1, blink


def decode_addr(off):
    """offset в 32К дампе -> (plane, X_in_byte(0..7), Y)."""
    addr = VRAM_LO + off
    plane = None
    for p in PLANE_BASES:
        if p <= addr < p + 0x2000:
            plane = p
            break
    if plane is None:
        return None
    rel = addr - plane
    col_byte = rel >> 8                 # (X//8)
    y = 255 - (rel & 0xFF)              # (255 - Y)
    return plane, col_byte, y


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trace_glyph")
    ap.add_argument("--word", default="TIV", help="буквы для трассы (A..Z)")
    ap.add_argument("--rom", default=ROM)
    ap.add_argument("--org", type=lambda s: int(s, 0), default=ORG)
    args = ap.parse_args(argv)

    font = None
    session, _ = open_session(rom=args.rom, org=args.org, cache=False)
    try:
        session.load_rom(args.rom, org=args.org)
        session.call("debug_run")
        time.sleep(3.0)

        font = read_mem(session, FONT_ROM, FONT_GLYPHS * FONT_COLS)
        cur0 = read_mem(session, CURSOR_VAR, 2)
        cursor0 = cur0[0] | (cur0[1] << 8)
        print("var_cursor_vram @%04X = %04X" % (CURSOR_VAR, cursor0))

        v_base, blink = capture(session)
        prev = v_base
        prev_cur = cursor0
        for ch in args.word.upper():
            if not ("A" <= ch <= "Z"):
                continue
            # набрать ОДНУ букву и ENTER-не надо: эхо появляется сразу
            session.call("debug_type_key", {"key": ch})
            time.sleep(0.5)
            v, b2 = capture(session)
            blink |= b2
            cur = read_mem(session, CURSOR_VAR, 2)
            cursor = cur[0] | (cur[1] << 8)

            code = ord(ch)
            cols = font[code * FONT_COLS:(code + 1) * FONT_COLS]
            print("\n=== '%s' (code %02X) cursor %04X -> %04X (step %d) ==="
                  % (ch, code, prev_cur, cursor, cursor - prev_cur))
            print("  font columns (x=0..4), бит0=верх: "
                  + " ".join("%d:%s" % (x, format(cols[x], "08b"))
                             for x in range(FONT_COLS)))

            # новые освещённые пиксели = diff с предыдущим кадром, кроме мигания
            changed = [i for i in range(VRAM_LEN)
                       if v[i] != prev[i] and i not in blink]
            # группировка по плоскости: возьмём одну непустую (все одинаковы в 2-цветном)
            pix = set()
            for i in changed:
                d = decode_addr(i)
                if not d:
                    continue
                plane, col_byte, y = d
                xor = v[i] ^ prev[i]
                for bx in range(8):
                    if xor & (0x80 >> bx):
                        pix.add((plane, col_byte * 8 + bx, y))
            byplane = {}
            for plane, x, y in sorted(pix):
                byplane.setdefault(plane, []).append((x, y))
            for plane, ps in byplane.items():
                xs = [p[0] for p in ps]
                ys = [p[1] for p in ps]
                print("  plane %04X: %d px, X=[%d..%d] Y=[%d..%d]"
                      % (plane, len(ps), min(xs), max(xs), min(ys), max(ys)))
                # карта пикселей для визуальной сверки с колонками
                grid = [[ps.count((x, y)) for x in range(min(xs), max(xs) + 1)]
                        for y in range(min(ys), max(ys) + 1)]
                top = min(ys)
                for row_i, row in enumerate(grid):
                    print("    Y=%3d |%s" % (top + row_i,
                          "".join("#" if c else "." for c in row)))
            prev = v
            prev_cur = cursor
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
