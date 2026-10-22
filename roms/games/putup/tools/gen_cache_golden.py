#!/usr/bin/env python3
# Reimplement func_build_hero_shift_cache against the built ROM to produce a
# golden expected cache image, for byte-for-byte comparison vs emulator RAM.
import sys

ROM = "putup_new.rom"
data = open(ROM, "rb").read()
BASE_HDR = 0x100  # putup_new.rom = full image minus 256-byte header; runtime A -> offset A-0x100

def rd(addr, n=1):
    o = addr - BASE_HDR
    return data[o] if n == 1 else data[o:o+n]

PTR_TABLE = 0x0434      # runtime (layout.json)

def resolve(code):
    lo = rd(PTR_TABLE + 2*code)
    hi = rd(PTR_TABLE + 2*code + 1)
    word = (hi << 8) | lo
    return word & 0xFFFE   # strip compactness tag (bit0)

HERO = [
    [0xA0,0xA2,0xA1,0xA3],
    [0xA4,0xA6,0xA5,0xA7],
    [0xA8,0xAA,0xA9,0xAB],
    [0xAC,0xAE,0xAD,0xAF],
    [0xB0,0xB2,0xB1,0xB3],
    [0xB4,0xB6,0xB5,0xB7],
    [0xB8,0xBA,0xB9,0xBB],
    [0xBC,0xBE,0xBD,0xBF],
]

cache = bytearray(1536)  # data_hero_shift_cache @ 0x6C00, 8*6*32
for tile in range(8):
    TL,TR,BL,BR = HERO[tile]
    for row,(lc,rc) in enumerate([(TL,TR),(BL,BR)]):
        Lrec = resolve(lc); Rrec = resolve(rc)
        base = tile*192 + row*96
        for p in range(4):
            fill0 = 0xF0 if p==3 else 0
            fill2 = 0x0F if p==3 else 0
            for j in range(8):
                lp = rd(Lrec + p*8 + j)
                rp = rd(Rrec + p*8 + j)
                cache[base + 0*32 + p*8 + j] = (lp >> 4) | fill0
                cache[base + 1*32 + p*8 + j] = ((lp & 0x0F) << 4) | (rp >> 4)
                cache[base + 2*32 + p*8 + j] = ((rp & 0x0F) << 4) | fill2

out = sys.argv[1] if len(sys.argv) > 1 else "export/hero_cache_expected.bin"
import os
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out,"wb").write(bytes(cache))
print("expected cache:", len(cache), "bytes ->", out)
print("nonzero bytes:", sum(1 for b in cache if b))
# sample tile0 top row
print("tile0 row0 frag0 (32B):", " ".join("%02X"%b for b in cache[0:32]))
print("tile0 row0 frag1 (32B):", " ".join("%02X"%b for b in cache[32:64]))
