#!/usr/bin/env python3
"""Offline renderer: run the REAL mario.rom hot path in the v06_emu 8080 core,
capture the 4 VRAM bit-planes, reconstruct the 256x256 indexed frame and save a
PNG.  Also dumps an ASCII render of one sprite so the format/packing can be
eyeballed directly.  Used because the debugger MCP is unavailable.

Plane map (256x256, 16 colours): weight 8 -> 0x8000, 4 -> 0xA000, 2 -> 0xC000,
1 -> 0xE000.  Block = x/8 (256 bytes).  Byte index i stores row y = 255 - i.
bit7 of a byte = leftmost pixel of that 8px block.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "utils", "emulator"))
from v06_emu import Emulator8080
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = os.path.join(HERE, "..", "mario.rom")

RENDER_WINDOW = 0x02C0
MARIO_DRAW    = 0x0399
STAND_R       = 0x4111
WALK0_R       = 0x4251
JUMP_R        = 0x4751
DUCK_R        = 0x4891
LEVEL_PAL     = 0x0541
SP            = 0x7FF0

PLANES = [(0x8000, 8), (0xA000, 4), (0xC000, 2), (0xE000, 1)]

rom = open(ROM, "rb").read()
emu = Emulator8080()
emu.load_bytes(rom, 0x0100)
c = emu.cpu

# 1) full background: render_window(cam=0, blk0=0, nblk=32)
#    sccz80 layout -> setup_call args reversed: (nblk, blk0, cam)
c.reset_trace()
emu.call(RENDER_WINDOW, args=(32, 0, 0), sp=SP, max_steps=4_000_000)
print(f"render_window done: pc={c.pc:04X} (sentinel 0xFF00 = clean)")

# 2) composite sprites at screen positions (x=mblk*8, y=208)
#    callee layout: spr@sp+2, y@sp+4, x@sp+6 -> pass (spr, y, x)
for addr, name, x, y in [
    (STAND_R, "stand", 4*8, 208),
    (WALK0_R, "walk0", 8*8, 208),
    (JUMP_R,  "jump",  12*8, 150),
    (DUCK_R,  "duck",  16*8, 216),
]:
    emu.call(MARIO_DRAW, args=(addr, y, x), sp=SP, max_steps=2_000_000)
    print(f"mario_draw {name}: pc={c.pc:04X}")


def pixel_idx(x, y):
    bx, col = x // 8, x % 8
    bitpos = 7 - col               # bit7 = leftmost
    i = 255 - y                    # byte index for row y
    idx = 0
    for base, w in PLANES:
        b = (c.mem[base + bx*256 + i] >> bitpos) & 1
        idx |= b * w
    return idx


def pal_rgb(byte):
    r = (byte & 7) * 255 // 7
    g = ((byte >> 3) & 7) * 255 // 7
    bl = ((byte >> 6) & 3) * 255 // 3
    return (r, g, bl)


palette = [c.mem[LEVEL_PAL + j] for j in range(16)]

img = Image.new("RGB", (256, 256))
px = img.load()
for y in range(256):
    for x in range(256):
        px[x, y] = pal_rgb(palette[pixel_idx(x, y)])

out = os.path.join(HERE, "render_dump.png")
img.save(out)
print(f"wrote {out} ({os.path.getsize(out)} bytes)")

# ASCII view of the stand sprite region (rows 208..223, cols 32..47) as drawn.
print("\nstand sprite as rendered in VRAM (cols 32..47, rows 208..223):")
for y in range(208, 224):
    line = "".join(" .#oO+*%$&@0123456789"[pixel_idx(x, y)] if pixel_idx(x, y) < 16 else "?"
                   for x in range(32, 48))
    print(f"  {y:3d} |{line}|")
