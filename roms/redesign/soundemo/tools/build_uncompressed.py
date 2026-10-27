#!/usr/bin/env python3
"""
Build uncompressed SOUNDEMO ROM from pristine RAM image.
Output: soundemo_uncompressed.rom — loads at 0x0100, runs directly without unpacker.

Pristine image captured at breakpoint 0x37A8 (after unpacker, before func_main_entry runs).
func_main_entry installs RST7 vector and EI/HLT — works correctly on real HW.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DUMP = ROOT / "dump"
OUT  = ROOT / "src"

raw = (DUMP / "pristine_ram.bin").read_bytes()
assert len(raw) == 0x4000, f"Expected 16384 bytes, got {len(raw)}"

# ROM starts at RAM 0x0100, so we take bytes 0x0100..0x3FFF
rom = bytearray(raw[0x0100:])  # 16128 bytes

# Verify entry at 0x0100 is JMP func_main_entry (0x37A8)
assert rom[0] == 0xC3 and rom[1] == 0xA8 and rom[2] == 0x37, \
    f"Expected C3 A8 37 at entry, got {rom[0]:02X} {rom[1]:02X} {rom[2]:02X}"

# Verify func_main_entry starts with DI
assert raw[0x37A8] == 0xF3, f"Expected DI at 0x37A8, got {raw[0x37A8]:02X}"

# --- Patch 1: Bake melody-active flag [0x3C17] = 1 ---
# In pristine image, [0x3C17]=0 because melody requires CALL 3B07 (keyboard) to activate.
# For direct-play ROM we set it to 1 so main loop enters VI53 path immediately.
ROM_BASE = 0x0100
MELODY_FLAG_ADDR = 0x3C17
rom[MELODY_FLAG_ADDR - ROM_BASE] = 0x01
print(f"  Patched [0x3C17] = 1 (melody active)")

# --- Patch 2: NOP the STA 3C17 at 0x3830 ---
# func_main_entry at 0x3829 does: CALL 0x382F → XRA A; STA 3C17 (zeros melody flag)
# Replace STA 3C17 (32 17 3C) at 0x3830 with NOPs so melody flag stays baked
STA_ADDR = 0x3830  # STA 3C17: 3 bytes (32 17 3C)
assert raw[STA_ADDR] == 0x32 and raw[STA_ADDR+1] == 0x17 and raw[STA_ADDR+2] == 0x3C, \
    f"Expected STA 3C17 at 0x3830, got {raw[STA_ADDR]:02X} {raw[STA_ADDR+1]:02X} {raw[STA_ADDR+2]:02X}"
rom[STA_ADDR - ROM_BASE : STA_ADDR - ROM_BASE + 3] = b'\x00\x00\x00'  # NOP NOP NOP
print(f"  Patched [0x3830] = NOP (skip STA 3C17 zero)")
out_path = OUT / "soundemo_uncompressed.rom"
out_path.write_bytes(rom)
print(f"\nWrote {out_path} ({len(rom)} bytes = 0x{len(rom):X})")
print(f"  Entry: JMP 0x37A8 (func_main_entry)")
print(f"  func_main_entry: DI → OUT 10h → VI53 mode → RST7 vec → EI/HLT → active melody")
print(f"  Covers RAM 0x0100..0x3FFF")
