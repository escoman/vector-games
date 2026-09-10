Now let me check the current RDB state and the asm directory to understand the full picture:


Now I have a complete picture. Here's my analysis:

---

## Analysis: What's Missing for Full Automation

After reviewing all 9 stages (TZ.md + Stage1.md–Stage9.md), the current RDB state (154 objects, 101 functions, 101 .asm files), and the actual coverage gaps, here's what prevents full automation of disassembly → analysis → ROM rebuild:

### 1. **63 Unnamed Functions (sub_XXXX)** — Critical

Out of 101 functions, **63 still have temporary `sub_XXXX` names**. Their purpose is unknown. You can't rebuild meaningful, modifiable code when 62% of functions are anonymous. Each needs:
- Disassembly analysis to determine purpose
- A meaningful `func_` name
- A comment describing behavior
- Parameter documentation (input/output registers)

This is the largest remaining effort — roughly equivalent to Stages 3–4 repeated 63 times.

### 2. **~400 Unresolved Memory References** — Critical

The exported .asm files contain **414 hex address references** (STA, LDA, SHLD, LHLD, CALL, JMP). Most are RAM variable accesses to locations like `0x08E2`, `0x0900`, `0x0B41`, etc. that aren't in RDB. Only **17 variables** are named, but the code references dozens more. For automation, every memory location needs either:
- A named RDB variable (`var_game_state`, `var_score`, etc.)
- Or being part of a known data structure

### 3. **7,262 Bytes of Unexplored ROM (0x1BFA–0x3857)** — Critical

The largest gap is a **7.1 KB block** between `func_level_init` and `func_isr_game_state`. Given the total unpacked ROM is ~17 KB (0x0100–0x45FF), this is **~40% of the entire code** that has no functions defined. Other gaps:

| Gap | Size | Likely content |
|-----|------|----------------|
| 0x1BFA–0x3857 | 7,262 B | Major game functions (rendering, collision, scoring?) |
| 0x051B–0x07FF | 741 B | VRAM offset tables, glyph data in ROM |
| 0x08A3–0x0B56 | 692 B | Packed data stream, string tables |
| 0x1A59–0x1B86 | 302 B | Level-related functions |
| 0x396E–0x3BC9 | 604 B | Sound/music engine |
| 0x0219–0x0320 | 264 B | Jump table dispatch handlers |

### 4. **No Data Block Inventory** — Major

There's no complete byte-level map of what every ROM byte is. For rebuild, you need to know:
- Which bytes are **code** (and which function)
- Which bytes are **data** (tables, strings, maps, sprites)
- Which bytes are **padding/alignment**
- Which bytes are **compressed data** (the decompression pipeline 0x0401–0x04CD)

The 18 gaps above contain both undiscovered functions AND data blocks, but we don't know which is which.

### 5. **Compression Format Not Fully Documented** — Major

`func_decompress` unpacks ROM data (0x2761 → 0x6000, 8192 bytes of glyphs). But the compression format isn't documented as a reusable encoder/decoder. For ROM rebuild:
- Need to understand the exact compression algorithm
- Need a tool to re-compress modified data back into the same format
- The glyph block (0x6000, 8192 bytes) is entirely decompressed data — modifying it requires re-compression

### 6. **No Build System / Assembler Pipeline** — Major

There's no:
- Master `.asm` file that includes all function files in correct order
- Linker script defining memory layout (where code goes, where data goes)
- Makefile to assemble all 101 .asm files into a single binary
- Tool to validate the assembled binary matches the original ROM byte-for-byte

### 7. **VRAM Address Translation Logic** — Moderate

`func_copy_to_vram` uses a complex SP-swap trick with address translation (logical screen → physical bitplane). The VRAM layout (4 planes × 8KB, interleaved) isn't captured as a reusable data structure. Rebuilding requires understanding how logical tile/sprite data maps to physical VRAM addresses.

### 8. **ISR Timing Dependencies** — Moderate

The ISR writes palette colors with NOP-delays between port writes. This timing-sensitive code means you can't freely rearrange ISR instructions. For rebuild, timing constraints must be preserved.

### 9. **Self-Modifying Code / RAM-Resident Code** — Moderate

A large portion of the game runs from RAM (0x0800+), unpacked at startup. The ROM's `func_decompress` + data loader writes code into RAM that then executes. For rebuild:
- Need to separate "ROM code" from "RAM code" (unpacked)
- The RAM code origin, size, and load address must be precisely defined
- Modifications to RAM code change the compressed ROM data

### 10. **Variable Naming Corrections** — Minor but Needed

Per your earlier corrections:
- `var_lives` @ 0x08EF is NOT lives (set at startup, before space press)
- `var_lives_level` @ 0x0907 IS the actual lives count (set in `func_level_init` after space)
- These need renaming to reflect actual purpose

---

### Summary: What Stages Are Needed

| What's needed | Estimated effort | Priority |
|---|---|---|
| **Stage 10**: Analyze & name all 63 `sub_` functions | Very large (63 functions) | Critical |
| **Stage 11**: Map ALL RAM variables (eliminate 400+ hex refs) | Large (~50 variables) | Critical |
| **Stage 12**: Fill ROM coverage gaps (7.3 KB unexplored) | Large (dozens of new functions/data) | Critical |
| **Stage 13**: Document all data blocks byte-by-byte | Medium | Major |
| **Stage 14**: Document compression format + build re-compressor | Medium | Major |
| **Stage 15**: Create assembler build pipeline (Makefile, linker script) | Medium | Major |
| **Stage 16**: VRAM layout documentation | Small–Medium | Moderate |
| **Fix**: Rename var_lives / var_lives_level | Trivial | Minor |

**Bottom line:** The current state covers roughly **30–35%** of what's needed for full automation. The biggest gaps are the 63 unnamed functions, the 7 KB unexplored ROM region, and the absence of a build pipeline that can reassemble modified sources back into a working ROM.