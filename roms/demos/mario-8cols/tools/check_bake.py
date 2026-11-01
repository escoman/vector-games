#!/usr/bin/env python3
"""check_bake.py — валидация печки окна тремя независимыми источниками.

Для каждой базы окна окно печётся тремя способами:
  1. _bake_cols из СОБРАННОГО ROM (ASM по таблице спанов);
  2. Python-копия bake_cols из profile_scroll.py (модель профилировщика);
  3. карта, развёрнутая из assets/objects.json (префабы + экземпляры) —
     источник истины, не зависящий ни от спанов, ни от ASM.
Расхождение (1)-(3) значит, что ROM нарисует не тот уровень; (1)-(2) — что
profile_scroll.py считает стоимость по неправильной карте.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prefablib as PL                                        # noqa: E402
from profile_scroll import (Rom, parse_incs, bake_cols, HERE,
                            new_cpu, call_cdecl, set_stride)  # noqa: E402


def load_map(cols, rows):
    """Карта, которую ROM обязан нарисовать: развёртка списка экземпляров."""
    prefabs = PL.load_prefabs()
    oc, orw, inst = PL.load_instances()
    if inst is None:
        sys.exit("нет assets/objects.json — не из чего строить эталон")
    if (oc, orw) != (cols, rows):
        sys.exit(f"objects.json: {oc}x{orw} != level.inc {cols}x{rows}")
    return PL.expand_by_blocks(cols, rows, prefabs, inst)


def main():
    rom = Rom(HERE / "mario-8c.rom", HERE / "mario-8c.map")
    lv = parse_incs(HERE / "include" / "level.inc")
    rows, wcols = lv["ROWS"], lv["WIN_COLS"]
    a = {k: rom.at(k) for k in ("_tile_win", "_tile_win_base", "_tile_stride",
                                "_bake_cols", "_bake_window", "_bake_clear")}
    cpu = new_cpu(rom)
    set_stride(cpu, rom, rows)
    world = load_map(lv["COLS"], rows)
    span = lv["pf_span_ofs"][-1]      # смещение за последней колонкой таблицы
    print(f"карта {lv['COLS']}x{rows}, спанов {span} Б, колонок в окне {wcols}")
    nbad = 0
    bases = list(range(0, lv["COLS"], lv["WIN_STEP"]))
    for base in bases:
        # --- ROM ---
        cpu.mem[a["_tile_win"]:a["_tile_win"] + wcols * rows] = bytes(wcols * rows)
        cpu.ww(a["_tile_win_base"], base)
        call_cdecl(cpu, a["_bake_cols"], [base, base + wcols])
        asm = list(cpu.mem[a["_tile_win"]:a["_tile_win"] + wcols * rows])
        # --- Python-модель ---
        py = [0] * (wcols * rows)
        bake_cols(py, base, base, base + wcols, lv)
        # --- эталон из объектов (за правым краем карты — небо) ---
        ref = [0] * (wcols * rows)
        for c in range(wcols):
            wc = base + c
            if wc < lv["COLS"]:
                ref[c * rows:(c + 1) * rows] = world[wc * rows:(wc + 1) * rows]
        d_asm = [i for i in range(len(ref)) if asm[i] != ref[i]]
        d_py = [i for i in range(len(ref)) if py[i] != ref[i]]
        nz = sum(1 for v in ref if v)
        status = "OK" if not d_asm and not d_py else (
            f"ROM!=карта {len(d_asm)}, py!=карта {len(d_py)}")
        print(f"base={base:>4}: nonzero тайлов {nz:>5}, {status}")
        if d_asm or d_py:
            nbad += 1
            for i in (d_asm or d_py)[:10]:
                print(f"   col={i // rows:>3} row={i % rows:>3}: "
                      f"карта={ref[i]:>3} py={py[i]:>3} asm={asm[i]:>3}")
    print(f"\nбаз проверено {len(bases)}, расхождений {nbad}")
    return 1 if nbad else 0


if __name__ == "__main__":
    sys.exit(main())
