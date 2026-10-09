#!/usr/bin/env python3
"""Сколько v-cycle стоит кадр: редрав, шаг скролла, спрайт.

Такты берутся из таблицы i8080.cpp эмулятора vector-psp (см.
utils/analyze/extract_vcycles.py), поэтому это реальные циклы процессора,
а не число инструкций.

Горячие точки сопоставляются со строками mario.asm через метки из mario.map.

    make all && python3 tools/frame_cost.py
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "utils", "emulator"))
from v06_emu import Emulator8080                                # noqa: E402

ROM = os.path.join(HERE, "..", "mario.rom")
MAP = os.path.join(HERE, "..", "mario.map")
EXTRACT = os.path.join(ROOT, "utils", "analyze", "extract_vcycles.py")
SP = 0x7FF0
CAM_NO_REF = 0xFFFF
VIEW_BLOCKS = 32


def cycles_table():
    """{opcode: v_cycles} из исходников эмулятора."""
    out = subprocess.run([sys.executable, EXTRACT], capture_output=True,
                         text=True, check=True).stdout
    return {int(k, 16): v for k, v in json.loads(out).items()}


CYC = cycles_table()

LABELS = []          # [(адрес, имя, строка mario.asm)]
for line in open(MAP):
    m = re.match(r"^([A-Za-z_]\w*)\s*=\s*\$([0-9A-Fa-f]+)\s*;.*?"
                 r"mario\.asm:(\d+)", line)
    if m:
        LABELS.append((int(m.group(2), 16), m.group(1), int(m.group(3))))
LABELS.sort()
ADDR = {n: a for a, n, _ in LABELS}
for line in open(MAP):
    m = re.match(r"^([A-Za-z_]\w*)\s*=\s*\$([0-9A-Fa-f]+)\s*;", line)
    if m and m.group(1) not in ADDR:
        ADDR[m.group(1)] = int(m.group(2), 16)
LABELS.sort()


def label_of(pc):
    """Ближайшая метка <= pc -> (имя, строка)."""
    best = None
    for a, name, ln in LABELS:
        if a <= pc:
            best = (name, ln)
        else:
            break
    return best or ("?", 0)


emu = Emulator8080()
emu.load_bytes(open(ROM, "rb").read(), 0x0100)
c = emu.cpu


def run(fn, args, want_vram=False):
    emu.setup_call(fn, args=args, sp=SP)
    c.trace_enabled = True
    c.reset_trace()
    c.run_until(max_steps=60_000_000, stop_pc=0xFF00)
    assert c.pc == 0xFF00, f"{fn:04X} не вернулась: pc={c.pc:04X}"
    total = 0
    unk = 0
    per_line = {}
    for t in c.trace:
        cyc = CYC.get(t["opcode"])
        if cyc is None:
            unk += 1
            cyc = 4
        total += cyc
        name, ln = label_of(t["pc"])
        per_line[(name, ln)] = per_line.get((name, ln), 0) + cyc
    return total, unk, sorted(per_line.items(), key=lambda kv: -kv[1])[:8]


def render(cam, old, blk0=0, nblk=VIEW_BLOCKS):
    return run(ADDR["_render_window"], (nblk, blk0, old, cam))


print(f"таблица тактов: {len(CYC)} опкодов")

total, unk, hot = render(0, CAM_NO_REF)
print(f"\nпервый экран (полный редрав, cam=0): {total:,} T"
      f"{'  (неизвестных опкодов: %d)' % unk if unk else ''}")
for (name, ln), t in hot:
    print(f"    {t:8,d} T  {name}:{ln}")

print("\nшаг скролла (разность, cam-1 -> cam):")
tot = 0
for cam in range(1, 25):
    t, _u, _h = render(cam, cam - 1)
    tot += t
print(f"    среднее {tot / 24:,.0f} T за шаг")
total, unk, hot = render(24, 23)
for (name, ln), t in hot:
    print(f"    {t:8,d} T  {name}:{ln}")

total, unk, hot = render(24, CAM_NO_REF)
print(f"\nполный редрав без дорисовки (cam=24): {total:,} T")

spr = ADDR["_mario_walk0_r"]
total, unk, hot = run(ADDR["_mario_draw"], (spr, 208, 4 * 8))
print(f"\nmario_draw: {total:,} T")
for (nme, ln), t in hot[:4]:
    print(f"    {t:8,d} T  {nme}:{ln}")
total, unk, hot = run(ADDR["_mario_undraw"], ())
print(f"mario_undraw: {total:,} T")
