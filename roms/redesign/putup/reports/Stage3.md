# Stage 3 — Detailed Function Research (rename + comment + links)

## Goal
For every function/data object discovered in Stage 2, research its code in detail via the
MCP `vector-debugger`, rename it to a meaningful symbolic name, add a purpose comment, and
establish confirmed function↔data / function↔function links. Save the RDB.

## ROM
- File: `putup.rom`
- Size: 17664 bytes, load address 0x0100, spans 0x0100–0x45FF
- SHA256: `8486442efc390b15860ec7f69c32db93b0884908565fa11fec57d5c551b4e9a6`
- Mapping entry point: **0x0000** (ROM reset/RST vectors); program entry `func_entry` = **0x0100** (`DI; JMP func_main_init`)

## Method
All disassembly and memory reads were obtained through MCP tools
(`debug_disassemble_range`, `debug_read_memory_range`). No self-disassembly, no external
post-processing scripts. RDB was updated exclusively through the RDB API
(`debug_update_rdb_object`, `debug_add_rdb_object`, `debug_set_rdb_comment`,
`debug_add_rdb_link`, `debug_save_rdb`).

## Result summary
```
Mapping entry point: 0x0000  (program entry func_entry = 0x0100)
Objects: 106   (69 functions, remainder data/variables/tables)
Links:   76
RDB:     /home/alexey/Projects/vector-games/roms/redesign/putup/src/putup.rdb
RDB save: success (dirty = false, exists_on_disk = true)
Remaining *_unknown names: 0
```

---

## Key corrections to Stage 2 provisional names

Stage 2 provisionally named 0x01BC `func_set_color` and 0x0121 `func_palette_init`.
Detailed research **rejected** both: these are the **KR580VI53 (8253) sound engine**, not
palette code. Evidence: writes to ports 0Bh/0Ah/09h (VI53 counter0/1/2) and control words
0x36/0x76/0xB6 (counter mode-3 square wave), plus per-channel period words at 0x031A–0x031F
and a state byte at 0x0320.

| Addr | Stage 2 (provisional) | Stage 3 (confirmed) |
|------|-----------------------|---------------------|
| 0x01BC | func_set_color | **func_sound_op** (16-way PCHL dispatcher) |
| 0x0121 | func_palette_init | **func_sound_init** (startup beep on ch2) |

---

## Subsystem 1 — Sound engine (KR580VI53, 3-channel square wave)

`func_sound_op` (0x01BC) is the public API: a 16-way `PCHL` jump-table dispatcher.
Params: **A = op index (0..15)**, **E = value**. Jump table `data_snd_dispatch_table` @0x01CD
(16 words); secondary toggle table `data_snd_toggle_table` @0x0280 (8 words).

| Function | Addr | Purpose |
|----------|------|---------|
| func_sound_op | 0x01BC | 16-way sound-op dispatcher (A=op, E=value) |
| func_sound_init | 0x0121 | Startup config + beep on channel 2 |
| func_snd_calc_period | 0x020E | HL = 12 × note value (counter reload) |
| func_snd_out_ch0/ch1/ch2 | 0x0201 / 0x022D / 0x024E | Write period to port 0Bh/0Ah/09h |
| func_snd_enable_ch0/ch1/ch2 | 0x0290 / 0x029E / 0x02AC | Gate channel via control word 0x36/0x76/0xB6 to port 08h |
| func_snd_enable_ch01/ch02/ch12/ch012 | 0x02BA / 0x02C0 / 0x02C6 / 0x02CC | Enable channel combinations |
| func_snd_toggle | 0x026E | Re-enter dispatcher via toggle table (state XOR) |
| func_snd_gate_ch0/ch1/ch2 | 0x02D2 / 0x02EA / 0x0302 | Envelope/gate per channel |

State: `var_snd_state` @0x0320; period words `var_snd_period_ch0/1/2` @0x031A/0x031C/0x031E.

---

## Subsystem 2 — Text / glyph rendering pipeline

Screen text is a 32×32 character buffer at **0x5000** (`data_ram_buffer_5000`, 1024 bytes).
Glyph bitmaps are reached through `data_glyph_ptr_table` @0x0600 (256 words, char×2) and
VRAM column bases through `data_vram_col_table` @0x051B.

| Function | Addr | Purpose |
|----------|------|---------|
| func_coords_to_textbuf | 0x1BD4 | HL = 0x5000 + E*32 + D (D=col, E=row) |
| func_clear_textbuf | 0x1BE5 | Fill 1024 bytes @0x5000 with spaces |
| func_set_text_ptr | 0x014F | SHLD 0x0B53 (set text cursor) |
| func_put_char | 0x0800 | Store char A to (HL) if changed; falls through to render |
| func_render_glyph | 0x0803 | Render glyph A at HL to VRAM (SPHL pop trick; saves SP→0x08DD) |
| func_draw_char_at_hl | 0x0145 | Draw char A at HL, advance cursor 0x0B53 |
| func_print_char_at_ptr | 0x01A1 | Print A at cursor 0x0B53, advance |
| func_restore_cursor | 0x01AE | Cursor ← saved coords @0x08FE/0x08FF |
| func_print_string | 0x0321 | Print NUL/0xFF-terminated string at HL |
| func_print_uint16 | 0x0331 | Print word at (HL) as 5-digit decimal (leading-zero blanking via 0x08E2) |
| func_divmod_u16 | 0x0355 | Unsigned 16-bit div/mod by repeated addition |
| func_hl_add_a | 0x032C | HL += A (ubiquitous address helper) |
| func_draw_tile_to_buf | 0x1B87 | Draw 2×2 char tile from DE into text buffer (stride +31) |
| func_render_tile_vram | 0x1BA8 | Render 2×2 glyph tile from DE straight to VRAM |
| func_draw_tile_at_ptr | 0x0104 | Draw 2×2 tile at coords read from (HL) |
| func_memcpy | 0x1BC9 | Copy BC bytes HL→DE |

---

## Subsystem 3 — Graphics / bit-plane blit

`func_draw_image` (0x0401) composes a full 256×256 image into back-buffer `data_backbuffer_6000`
from bitmap source `data_bitmap_3041` (0x3041), using 4 bit-plane expand writers.
`func_load_gfx_2761` (0x04CD) preloads ROM gfx `data_gfx_2761` (0x2761) into 0x6000.

| Function | Addr | Masks |
|----------|------|-------|
| func_blit_plane_mask80 | 0x0439 | 0x80 / 0x08 |
| func_blit_plane_mask40 | 0x045E | 0x40 / 0x04 |
| func_blit_plane_mask20 | 0x0483 | 0x20 / 0x02 |
| func_blit_plane_mask10 | 0x04A8 | 0x10 / 0x01 |

VRAM plane map (verified): 0x8000=plane3(MSB), 0xA000=plane2, 0xC000=plane1, 0xE000=plane0(LSB).

---

## Subsystem 4 — Input / keyboard

ISR scans the 8×8 keyboard matrix into `data_kbd_matrix` @0x08D3 (8 bytes).

| Function | Addr | Purpose |
|----------|------|---------|
| func_read_keybuf | 0x0197 | Return matrix row byte (index A) from 0x08D3 |
| func_decode_key | 0x0153 | Decode row→keycode via `data_keycode_table` @0x016C |
| func_check_start_key | 0x017C | Return 0xFF if SPACE (row7 bit7) or SHIFT (port 01h bit5) pressed |

`func_check_start_key` is the title/key-poll primitive required by Stage 6.

---

## Subsystem 5 — Music sequencer (VI53 tracker, driven from VBlank)

`func_music_tick` (0x3858) is called from `func_vblank_isr` (0x03A4) every frame and drives a
3-channel note sequencer. Track state: `var_music_track_ptr` @0x3854,
`var_music_track_base` @0x3856, `var_music_tick` @0x383A, working ptr `var_music_work_ptr` @0x0B41,
14-byte `data_voice_param_buf` @0x3845, `var_music_voice2_flag` @0x3BC8.

| Function | Addr | Purpose |
|----------|------|---------|
| func_music_tick | 0x3858 | Per-frame sequencer tick (from ISR) |
| func_music_init | 0x3D4E | Clear music vars, load track pointer (called from main_init) |
| func_music_start_track | 0x3DCD | Copy track setup @0x3DE8→0x03F8; program VI53 (0x36/0x76/0xB6) |
| func_music_set_note_params | 0x3B0F | Copy note's 14-byte param block from `data_note_param_table_43F9` @0x43F9 |
| func_music_load_voice_params | 0x3902 | Push 14 voice params to sound engine |
| func_music_play_note_ch0 | 0x3BCA | Sound voice-1 note (table `data_note_freq_table_ch0` @0x445D, stride 20) |
| func_music_play_note_ch1 | 0x3C7D | Sound voice-2 note (table `data_note_table_ch1` @0x42F9, stride 10) |
| func_music_process_voice | 0x3946 | Per-voice note parameter processing |
| func_snd_op_keep_a / _a2 / _a3 | 0x3940 / 0x3C77 / 0x3D48 | Identical wrappers: `PUSH PSW; CALL func_sound_op; POP PSW; RET` |
| func_memcpy_keep_psw | 0x3DB8 | memcpy BC bytes HL→DE, preserving PSW |

---

## Subsystem 6 — Game logic

| Function | Addr | Purpose |
|----------|------|---------|
| func_entry | 0x0100 | ROM program entry: `DI; JMP func_main_init` |
| func_main_init | 0x0B57 | SP=0x0100; clear VRAM; hw_init; clear text buffer; draw image; load sprites 0x2F61→0x7418; init game vars; CALL music_init |
| func_hw_init | 0x0383 | Bank 0 (port 10h); scroll/mode vars; install RST7 vector 0x0038→0x03A4; reset vector→0x0B57; EI |
| func_vblank_isr | 0x03A4 | RST7/VBlank ISR: frame counter, palette update, kbd matrix scan, CALL func_music_tick |
| func_game_update | 0x0CE0 | Main per-frame update: check start key; dispatch on `var_game_state` @0x0900 (1→0x12B3, 2→0x12F6); advance position, collision scan vs 'v'(0x76) into var_0905 |
| func_draw_game_objects | 0x130A | Draw ball/paddle/items using tile table @0x26DE (index var_090C×4) via func_render_tile_vram |
| func_score_and_redraw | 0x0F09 | Add 10×value to score var_08F3; redraw HUD; draw tile @0x270A; JMP game_update |
| func_erase_char_08E9 | 0x0CA3 | Erase object cell at previous position (from var_08E9) |
| func_draw_score_hud | 0x1197 | Print label @0x0AED + score var_08F3 as decimal |
| func_draw_status_hud | 0x121A | Print var_08F5 + strings @0x0AF4/@0x0AFB + N icon chars (0x9B) |
| func_draw_level_hud | 0x11EE | Draw level indicator from var_08FB (clamped to 6) |
| func_play_sfx | 0x11E9 | Short SFX: B=2; CALL func_sound_init |
| func_prng | 0x1123 | LCG PRNG: var_1155 = (var_1155 × 899) & 0x7FFF; returns byte in A |
| func_delay | 0x0EF7 | Delay ≈ B×4096 cycles |
| func_delay_long | 0x1477 | Delay ≈ B×65536 cycles |

Key game variables: `var_game_state` @0x0900, score @0x08F3, level @0x08FB,
lives/status @0x08F5, position vars @0x0901/0x0902, collision flag @0x0905,
object coords @0x0909/0x090A, tile index @0x090C, PRNG state @0x1155.

---

## Verified Facts (High confidence, MCP-observed)
- 0x01BC is a 16-way `PCHL` jump-table dispatcher; table @0x01CD confirmed by `debug_read_memory_range`.
- Sound output targets ports 0Bh/0Ah/09h with VI53 control words 0x36/0x76/0xB6 → 3-channel square-wave tone generator.
- Text buffer is 32×32 @0x5000; glyph pointers @0x0600; VRAM column bases @0x051B.
- `func_music_tick` (0x3858) is invoked from the VBlank ISR (0x03A4) — music is interrupt-driven.
- `func_prng` multiplies state by 0x0383 (899) and masks to 15 bits.
- All 69 functions now carry meaningful names; 0 `_unknown` names remain.

## Inferences (Medium)
- The 0x38xx–0x3Dxx cluster is a note-based music tracker (per-note param blocks, frequency
  tables with fixed strides, tick counter, two melodic voices) built on the same VI53
  `func_sound_op` API used for SFX.
- `func_game_update` implements a small state machine (states 1/2 branch to attract/gameplay
  sub-modes) with collision detection against tile char 'v' (0x76).

## Hypotheses (Low — to verify in later stages)
- Note tables @0x445D/@0x42F9/@0x43F9 hold frequency+timbre records; exact record layout to be
  confirmed in Stage 5.
- `var_game_state` values map to title/attract (1) and play (2); full semantics in Stage 6.

## Unknowns
- Exact byte layout of music note records and the song/track data beginning @0x3DE8.
- Precise meaning of icon char 0x9B and HUD strings @0x0AED/0x0AF4/0x0AFB (Stage 7 covers text/glyphs).
- Level map location (Stage 9).

## Limitations
- Static analysis via MCP disassembly + memory reads; no live execution trace was captured this
  stage (emulator paused at 0x032C). Runtime confirmation of branch semantics deferred to
  Stage 5/6 where breakpoints + trace will be used.
- Bytes beyond 0x3DE7 that decode as instructions were treated as **data** (track tables), not
  code, per the "no conclusions from adjacent bytes" rule.

## Recommended Next Steps (Stage 4)
- Determine and record function parameters/return conventions into RDB properties
  (`debug_set_rdb_property`), starting with the sound API (A=op, E=value), text API
  (HL=coord/char), and music note routines.
