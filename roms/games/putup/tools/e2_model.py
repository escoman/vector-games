#!/usr/bin/env python3
# E2 verification: reconstruct the expected 3-column composite (VRAM runs) for the
# enemy slot window that func_enemy_build_cache + func_ed_blit3 must have written.
# Usage: e2_model.py <rom> <codes:TL,TR,BL,BR> <base_col> <row> <mode>
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))      # roms/games/putup/tools

rom_path, codes_s, base_col_s, row_s, mode_s = sys.argv[1:6]
codes = [int(x) for x in codes_s.split(',')]
base_col = int(base_col_s); row = int(row_s); mode = int(mode_s)

ROM_BASE = 0x0100
rom = open(rom_path, 'rb').read()
def peek(addr, n):
    off = addr - ROM_BASE
    return list(rom[off:off+n])

layout = json.load(open(os.path.join(HERE, 'layout.json')))
layout = layout.get('symbols', layout)
PTR_TABLE = layout['data_glyph_ptr_table']
COL_TABLE = layout['data_vram_col_table']
TEXTBUF   = layout['data_text_buffer']

def record(code):
    """Как читает запись сам func_render_glyph (Tier 2): bit0 слова указателя = тег
    compact -> только 8-байтная маска плоскости 0, плоскости 1..3 = нули; код 0x20
    имеет own fast-path (32 нуля). raw (тег=0) — 32 байта подряд."""
    if code == 0x20:
        return 0, [0] * 32
    w = peek(PTR_TABLE + 2*code, 2)
    ptr = w[0] | (w[1] << 8)
    addr = ptr & 0xFFFE
    if ptr & 1:
        return addr, peek(addr, 8) + [0] * 24
    return addr, peek(addr, 32)

def recv_addr(cell_addr):
    """One-for-one copy of func_ed_blit_frag / func_render_glyph address math."""
    hl = (cell_addr + (0 - TEXTBUF)) & 0xFFFF
    col = hl & 0x1F
    h, l = hl >> 8, hl & 0xFF
    # RRC,RRC,ANI 0C0h над H и RRC,RRC,ANI 38h над L = ((H&3)<<6)|((L&0E0h)>>2),
    # т.е. 8*row (а НЕ (H>>2)&0C0h, как ошибочно написано в шапке func_render_glyph)
    rowbits = (((h & 3) << 6) | ((l & 0xE0) >> 2)) & 0xFF
    page = peek(COL_TABLE + col, 1)[0]
    l2 = (mode - rowbits) & 0xFF
    return (page << 8) | l2, col, rowbits

# --- composite: 3 columns x 2 rows, nibble spill, vacuum = 0 in all planes ----
def shift_pair(L, R):
    frags = []
    for p in range(4):
        f = []
        for i in range(8):
            a, b = L[p*8+i], R[p*8+i]
            f.append((a >> 4) & 0x0F)
        frags.append(f)
    return frags

def composite_row(L, R):
    """returns list of 3 fragments (each 4 planes x 8 bytes) = frag0,frag1,frag2"""
    out = [[0]*32 for _ in range(3)]
    for p in range(4):
        for i in range(8):
            a, b = L[p*8+i], R[p*8+i]
            out[0][p*8+i] = (a >> 4) & 0x0F
            out[1][p*8+i] = (((a & 0x0F) << 4) | (b >> 4)) & 0xFF
            out[2][p*8+i] = (b & 0x0F) << 4
    return out

recs = {c: record(c)[1] for c in codes}
addrs = {c: record(c)[0] for c in codes}
rows = []
for r in range(2):
    rows.append(composite_row(recs[codes[r*2]], recs[codes[r*2+1]]))

print("glyph addrs:", {c: hex(a) for c, a in addrs.items()})
print("glyph records:", {c: ' '.join(f'{b:02X}' for b in recs[c]) for c in codes})
print("\nexpected cache window (6 frags x 32B):")
for r in range(2):
    for cpos in range(3):
        print(f"  row{r} col+{cpos}: " + ' '.join(f'{b:02X}' for b in rows[r][cpos]))

print("\nexpected VRAM runs (plane order 0..3, addr = receiver of each fragment):")
runs = []
for r in range(2):
    cell = TEXTBUF + (row + r) * 32 + base_col
    for cpos in range(3):
        addr, col, rb = recv_addr(cell + cpos)
        frag = rows[r][cpos]
        for p in range(4):
            a = (addr + p * 0x2000) & 0xFFFF
            runs.append((a, frag[p*8:p*8+8]))
        print(f"  row{r} frag{cpos} cell=0x{cell+cpos:04X} col={col} rowbits=0x{rb:02X} base=0x{addr:04X}")
for a, b in runs:
    print(f"READ 0x{a:04X} " + ' '.join(f'{x:02X}' for x in b))
json.dump([[a, b] for a, b in runs],
          open(os.path.join(HERE, 'e2_expected.json'), 'w'))
