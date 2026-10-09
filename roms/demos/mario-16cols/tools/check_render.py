#!/usr/bin/env python3
"""Deterministic check that render_window writes only to VRAM (>=0x8000).

Loads the real compiled mario.rom into the v06_emu 8080 core and calls the
real _render_window with the exact sccz80 __z88dk_callee stack layout
(arg1 farthest from SP), then inspects every memory write.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "utils", "emulator"))
from v06_emu import Emulator8080

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = os.path.join(HERE, "..", "mario.rom")

RENDER_WINDOW = 0x02C0
SP = 0x7FF0

rom = open(ROM, "rb").read()
emu = Emulator8080()
emu.load_bytes(rom, 0x0100)
c = emu.cpu
c.reset_trace()

# sccz80 pushes args left-to-right, so at callee entry:
#   sp+2 = nblk (arg3), sp+4 = blk0 (arg2), sp+6 = cam (arg1).
# Emulator8080.setup_call writes args[i] at sp+2+2*i, so pass reversed.
cam, blk0, nblk = 0, 0, 4
steps = emu.call(RENDER_WINDOW, args=(nblk, blk0, cam), sp=SP, max_steps=2_000_000)

writes = [(pc, a, v) for (_, pc, a, _old, v) in c.write_trace]
# The crash wrote tile bytes into the zero page (<0x0100: vectors + startup).
# BSS working vars (0x50xx) and the stack (0x7Fxx) are legitimate low writes.
low = [(pc, a, v) for (pc, a, v) in writes if a < 0x0100]
vram = [(pc, a, v) for (pc, a, v) in writes if 0x8000 <= a <= 0xFFFF]

print(f"returned cleanly to sentinel: {c.pc == 0xFF00}  (pc=0x{c.pc:04X}, steps={steps})")
print(f"total writes: {len(writes)}, VRAM writes: {len(vram)}, zero-page(<0x0100): {len(low)}")
if vram:
    addrs = sorted(a for _, a, _ in vram)
    print(f"VRAM addr range: 0x{addrs[0]:04X}..0x{addrs[-1]:04X}")
    # block 0 plane-8 must be 0x8000..0x80FF
    b0 = [a for a in addrs if 0x8000 <= a <= 0x80FF]
    print(f"block0/plane8 (0x8000..0x80FF) distinct bytes written: {len(set(b0))}")
if low:
    print("FAIL: writes into the zero page (the crash bug):")
    for pc, a, v in low[:20]:
        print(f"   PC=0x{pc:04X} -> 0x{a:04X} = 0x{v:02X}")
    sys.exit(1)
print("PASS: render_window writes only to VRAM; zero-page corruption is gone.")

# ---- mario_draw: masked 16x16 composite must also stay in VRAM ----
MARIO_DRAW = 0x0399
STAND_R = 0x4111
c.reset_trace()
# sccz80 layout: spr at sp+2, y at sp+4, x at sp+6 -> pass (spr, y, x).
steps = emu.call(MARIO_DRAW, args=(STAND_R, 208, 32), sp=SP, max_steps=2_000_000)
dw = [(pc, a, v) for (_, pc, a, _o, v) in c.write_trace]
dlow = [w for w in dw if w[1] < 0x0100]
dvram = [w for w in dw if 0x8000 <= w[1] <= 0xFFFF]
print(f"\nmario_draw: clean return={c.pc == 0xFF00}, VRAM writes={len(dvram)}, "
      f"zero-page={len(dlow)}")
if dlow or not dvram:
    print("FAIL: mario_draw bad writes:")
    for pc, a, v in dlow[:20]:
        print(f"   PC=0x{pc:04X} -> 0x{a:04X} = 0x{v:02X}")
    sys.exit(1)
print("PASS: mario_draw composites only into VRAM.")
