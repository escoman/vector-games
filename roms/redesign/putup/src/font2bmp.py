#!/usr/bin/env python3
"""
Extract font glyphs from putup.rom and render to BMP.
Font region: ROM 0x2E00 - 0x37FF (2560 bytes).
Each glyph: 8 bytes (8 rows x 8 pixels, 1 bit per pixel).
Rendering code reads bytes in REVERSE order (LDAX D + DCX D loop).
"""

from PIL import Image

ROM_PATH = "/home/alexey/Projects/vector-games/roms/redesign/putup/src/putup.rom"
OUT_BMP = "/home/alexey/Projects/vector-games/roms/redesign/putup/dest/font_table.bmp"
OUT_BIN = "/home/alexey/Projects/vector-games/roms/redesign/putup/assets/font_table.bin"

FONT_START = 0x2E00
FONT_END   = 0x3800  # exclusive
GLYPH_SIZE = 8       # 8 bytes per glyph slot

# Load ROM
with open(ROM_PATH, "rb") as f:
    rom = f.read()

font_data = rom[FONT_START:FONT_END]
print(f"Font region: 0x{FONT_START:04X}-0x{FONT_END-1:04X} ({len(font_data)} bytes)")

# Save raw binary
with open(OUT_BIN, "wb") as f:
    f.write(font_data)
print(f"Saved raw binary: {OUT_BIN} ({len(font_data)} bytes)")

# Detect glyph boundaries: find runs of non-zero data
# Each glyph is 8 bytes; blank glyphs (all zeros) are separators
num_glyphs = len(font_data) // GLYPH_SIZE
print(f"Total possible glyphs: {num_glyphs}")

# Scan for actual glyphs (non-blank 8-byte blocks)
glyphs = []
for i in range(num_glyphs):
    block = font_data[i*GLYPH_SIZE:(i+1)*GLYPH_SIZE]
    if any(b != 0 for b in block):
        # Reverse byte order: code reads from DE down to DE-7
        # So display order is byte[7], byte[6], ..., byte[0]
        reversed_block = bytes(reversed(block))
        glyphs.append((i, reversed_block))

print(f"Non-blank glyphs: {len(glyphs)}")

# Render to BMP: arrange glyphs in a grid
COLS = 16
rows = (len(glyphs) + COLS - 1) // COLS
img_w = COLS * 8
img_h = rows * 8

img = Image.new("1", (img_w, img_h), 0)  # 1-bit image, black background

for idx, (glyph_num, data) in enumerate(glyphs):
    col = idx % COLS
    row = idx // COLS
    x0 = col * 8
    y0 = row * 8
    
    for byte_idx, byte_val in enumerate(data):
        y = y0 + byte_idx
        for bit in range(8):
            if byte_val & (0x80 >> bit):
                img.putpixel((x0 + bit, y), 1)

# Scale up 4x for visibility
img_big = img.resize((img_w * 4, img_h * 4), Image.NEAREST)

img_big.save(OUT_BMP)
print(f"Saved BMP: {OUT_BMP} ({img_big.width}x{img_big.height} px, {len(glyphs)} glyphs in {rows} rows)")

# Print first few glyphs as ASCII art for quick check
print("\nFirst 8 glyphs (ASCII preview):")
for i, (glyph_num, data) in enumerate(glyphs[:8]):
    print(f"  Glyph #{glyph_num} (ROM 0x{FONT_START + glyph_num*GLYPH_SIZE:04X}):")
    for byte_val in data:
        row_str = ""
        for bit in range(8):
            row_str += "#" if byte_val & (0x80 >> bit) else "."
        print(f"    {row_str}")
