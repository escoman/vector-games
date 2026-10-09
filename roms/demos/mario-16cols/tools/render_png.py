#!/usr/bin/env python3
"""Кадр из реального ROM: 4 плоскости VRAM -> индексное поле -> PNG.

Гоняем горячий путь mario.rom в ядре v06_emu (тот же 8080, что и в эмуляторе),
снимаем VRAM и красим пиксели палитрой level_palette. Нужен чтобы ГЛАЗАМИ
проверить, что небо = индекс 0 = цвет фона и тайлы на месте.

Адреса берутся из mario.map — пересборка ROM инструмент не ломает.

    make all && python3 tools/render_png.py [cam]
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "..", "utils", "emulator"))
from v06_emu import Emulator8080                                # noqa: E402
from PIL import Image                                           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = os.path.join(HERE, "..", "mario.rom")
MAP = os.path.join(HERE, "..", "mario.map")

SP = 0x7FF0
CAM_NO_REF = 0xFFFF
VIEW_BLOCKS = 32
PLANES = [(0x8000, 8), (0xA000, 4), (0xC000, 2), (0xE000, 1)]

S = {}
for line in open(MAP):
    m = re.match(r"^([A-Za-z_]\w*)\s*=\s*\$([0-9A-Fa-f]+)\s*;", line)
    if m:
        S[m.group(1)] = int(m.group(2), 16)
for need in ("_render_window", "_mario_draw", "_level_palette"):
    if need not in S:
        sys.exit(f"в mario.map нет {need} — пересоберите ROM (make all)")

cam = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0

rom = open(ROM, "rb").read()
emu = Emulator8080()
emu.load_bytes(rom, 0x0100)
c = emu.cpu

# sccz80 раскладывает аргументы слева направо, поэтому в стеке они задом на
# перед: sp+2 = nblk, sp+4 = blk0, sp+6 = old_cam, sp+8 = cam -> передаём
# перевёрнутым кортежем.
emu.call(S["_render_window"], args=(VIEW_BLOCKS, 0, CAM_NO_REF, cam),
         sp=SP, max_steps=4_000_000)
assert c.pc == 0xFF00, f"render_window не вернулась: pc={c.pc:04X}"

# марио в разных позах, чтобы проверить и спрайтовый путь
for name, x, y in [("stand", 4, 208), ("walk0", 8, 208),
                   ("jump", 12, 150), ("duck", 16, 216)]:
    spr = S[f"_mario_{name}_r"]
    emu.call(S["_mario_draw"], args=(spr, y, x * 8), sp=SP, max_steps=2_000_000)
    assert c.pc == 0xFF00, f"mario_draw {name}: pc={c.pc:04X}"


def pixel_idx(x, y):
    """Индекс палитры пиксела (x, y) из 4 плоскостей VRAM."""
    bx, col = x // 8, x % 8
    bitpos = 7 - col                # bit7 = левый пиксел блока
    i = 255 - y                     # байт i хранит строку y = 255 - i
    idx = 0
    for base, w in PLANES:
        idx |= ((c.mem[base + bx * 256 + i] >> bitpos) & 1) * w
    return idx


def pal_rgb(byte):
    r = (byte & 7) * 255 // 7
    g = ((byte >> 3) & 7) * 255 // 7
    bl = ((byte >> 6) & 3) * 255 // 3
    return (r, g, bl)


palette = [c.mem[S["_level_palette"] + j] for j in range(16)]
print("палитра:", " ".join(f"{p:02X}" for p in palette))
print("небо (индекс 0) ->", pal_rgb(palette[0]))

img = Image.new("RGB", (256, 256))
px = img.load()
for y in range(256):
    for x in range(256):
        px[x, y] = pal_rgb(palette[pixel_idx(x, y)])

out = os.path.join(HERE, f"render_dump_{cam}.png")
img.save(out)
print(f"{out} ({os.path.getsize(out)} байт)")

# Пустого индекса 0 в окне должно быть ровно столько, сколько неба.
hist = {}
for y in range(256):
    for x in range(256):
        k = pixel_idx(x, y)
        hist[k] = hist.get(k, 0) + 1
print("гистограмма индексов:",
      " ".join(f"{k}:{hist[k]}" for k in sorted(hist)))

print(f"\nфрагмент верха экрана (строки 0..15), экранные колонки 24..31 "
      f"(мировые {cam + 24}..{cam + 31}):")
for y in range(0, 16):
    line = "".join(" .#oO+*%$&@0123456789"[pixel_idx(x, y)]
                   for x in range(192, 256))
    print(f"  {y:3d} |{line}|")
