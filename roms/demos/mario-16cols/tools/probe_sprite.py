#!/usr/bin/env python3
"""Locate where the Mario sprite colours actually land in VRAM after a
mario_draw call, and dump the raw sprite bytes (mask + planes) to inspect the
packing.  Diagnostic only (MCP debugger unavailable)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "utils", "emulator"))
from v06_emu import Emulator8080

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = os.path.join(HERE, "..", "mario.rom")
RENDER_WINDOW = 0x02C0
MARIO_DRAW    = 0x0399
STAND_R       = 0x4111
SP            = 0x7FF0
PLANES = [(0x8000, 8), (0xA000, 4), (0xC000, 2), (0xE000, 1)]

rom = open(ROM, "rb").read()
emu = Emulator8080(); emu.load_bytes(rom, 0x0100); c = emu.cpu

# --- raw sprite bytes: mask[32] + 4 planes*32, col-major ---
spr = bytes(c.mem[STAND_R + i] for i in range(160))
mask = spr[:32]
print("mask bytes (col0 rows0-15, col1 rows0-15):")
for cidx in range(2):
    for r in range(16):
        b = mask[cidx*16 + r]
        print(f"  col{cidx} row{r:2d}: {b:08b}")
    print()

# --- render bg then draw stand at (x=32,y=208), then locate colours 1/2 ---
emu.call(RENDER_WINDOW, args=(32, 0, 0), sp=SP, max_steps=4_000_000)
before = bytearray(c.mem[0x8000:0x10000])
emu.call(MARIO_DRAW, args=(STAND_R, 208, 32), sp=SP, max_steps=2_000_000)


def pixel_idx(x, y):
    bx, col = x // 8, x % 8
    bitpos = 7 - col
    i = 255 - y
    idx = 0
    for base, w in PLANES:
        idx |= ((c.mem[base + bx*256 + i] >> bitpos) & 1) * w
    return idx


pts = [(x, y) for y in range(256) for x in range(256) if pixel_idx(x, y) in (1, 2)]
if pts:
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    print(f"Mario-colour pixels: n={len(pts)} x[{min(xs)}..{max(xs)}] y[{min(ys)}..{max(ys)}]")
else:
    print("NO Mario-colour (1/2) pixels anywhere -> sprite wrote nothing distinctive")

# Where did the draw call actually write?  Group by (plane, block).
from collections import Counter
c.reset_trace()
emu.call(MARIO_DRAW, args=(STAND_R, 208, 32), sp=SP, max_steps=2_000_000)
blocks = Counter()
for _s, _pc, a, _o, _v in c.write_trace:
    if a >= 0x8000:
        plane = (a - 0x8000) // 0x2000
        blk = (a % 0x2000) // 256
        blocks[(plane, blk)] += 1
print(f"writes per (plane,block) for x=32 (expect blocks 4,5): {dict(sorted(blocks.items()))}")


def ascii_region(x0, x1, y0, y1):
    print(f"region x={x0}..{x1-1}, rows {y0}..{y1-1}:")
    for y in range(y0, y1):
        print("  %3d |" % y + "".join(
            ".oO+*%$&@X1234567890"[pixel_idx(x, y)] if pixel_idx(x, y) < 16 else "?"
            for x in range(x0, x1)) + "|")


ascii_region(32, 48, 208, 224)
