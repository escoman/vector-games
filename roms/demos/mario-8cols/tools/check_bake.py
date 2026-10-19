#!/usr/bin/env python3
"""check_bake.py — валидация Python-копии bake_* против C-кода из собранного ROM.

Запекает окно на нескольких базах двумя способами (Python и _bake_groups из ROM)
и сверяет tile_win байт в байт. Если модели расходятся — профилировщик
profile_scroll.py считает стоимость по неправильной карте.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_scroll import (Rom, parse_incs, bake_window, bake_groups, HERE,
                            new_cpu, call_cdecl, set_stride)  # noqa: E402


def main():
    rom = Rom(HERE / "mario-8c.rom", HERE / "mario-8c.map")
    lv = parse_incs(HERE / "include" / "level.inc")
    rows = lv["ROWS"]
    a = {k: rom.at(k) for k in ("_tile_win", "_tile_win_base", "_tile_stride",
                                "_bake_groups", "_bake_window", "_bake_clear")}
    cpu = new_cpu(rom)
    set_stride(cpu, rom, rows)
    nbad = 0
    for base in (0, 32, 64, 96, 128, 256, 288):
        # C-модель
        cpu.mem[a["_tile_win"]:a["_tile_win"] + lv["WIN_COLS"] * rows] = bytes(
            lv["WIN_COLS"] * rows)
        cpu.ww(a["_tile_win_base"], base)
        call_cdecl(cpu, a["_bake_groups"], [base, base + lv["WIN_COLS"]])
        cwin = list(cpu.mem[a["_tile_win"]:a["_tile_win"] + lv["WIN_COLS"] * rows])
        # Python-модель
        py = bake_window(lv, base)
        diff = [i for i in range(len(py)) if py[i] != cwin[i]]
        nz = sum(1 for v in py if v)
        status = "OK " if not diff else f"RASXOD {len(diff)}"
        print(f"base={base:>4}: nonzero тайлов {nz:>5}, {status}")
        if diff:
            nbad += 1
            for i in diff[:10]:
                print(f"   col={i // rows:>3} row={i % rows:>3}: py={py[i]:>3} c={cwin[i]:>3}")
    print(f"\nрасхождений по базам: {nbad}")


if __name__ == "__main__":
    main()
