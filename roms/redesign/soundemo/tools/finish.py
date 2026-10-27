#!/usr/bin/env python3
"""Lightweight: copy binaries, write main.asm stub, export.json. Code+data already generated."""
import json, shutil, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, DATA, ASM, DUMP = ROOT/"src", ROOT/"data", ROOT/"asm", ROOT/"dump"
DATA.mkdir(exist_ok=True)

# Copy binaries
shutil.copy2(SRC/"soundemo.rom", DATA/"soundemo_packed.rom")
shutil.copy2(DUMP/"decompressed_ram.bin", DATA/"decompressed_0x0000_0x3FFF.bin")

sha = hashlib.sha256((SRC/"soundemo.rom").read_bytes()).hexdigest()
size = (SRC/"soundemo.rom").stat().st_size

# asm/main.asm
(ASM/"main.asm").write_text(f"""; SOUNDEMO.ROM main include
; ROM: SOUNDEMO.ROM  Size: {size}  SHA-256: {sha}
; Self-extracting shilin-LZ; decompressed image at 0x0000..0x3FFF

        org     0000h

        include "boot/boot.asm"
        include "boot/unpacker.asm"
        include "code/main.asm"
        include "data/data.asm"
""")

# export.json
export = {
    "rom": "SOUNDEMO.ROM", "rom_size": size, "rom_sha256": sha,
    "origin": "0x0100", "decompressed_size": 0x4000,
    "unpacker": "shilin LZ (c) Шилин Д.В. 1994, 160 bytes at 0xFF50",
    "code_ranges": 4, "data_ranges": 5, "entries": 7,
}
(ASM/"export.json").write_text(json.dumps(export, indent=2)+"\n")
print("OK: data/, main.asm, export.json")
