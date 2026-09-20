# Stage 4 — Function Parameter Determination

## Goal
For every function in the RDB, determine its calling convention (input registers, output
registers, side effects) and store the result in the function object's `params` property.
Save the RDB.

## ROM
- File: `putup.rom`, 17664 bytes, load 0x0100
- SHA256: `8486442efc390b15860ec7f69c32db93b0884908565fa11fec57d5c551b4e9a6`
- Mapping entry point: **0x0000**; program entry `func_entry` = **0x0100**

## Method
1. Ran the ROM for ~5 s (`debug_run` + wait + `debug_pause`) per TZ.
2. Set a runtime breakpoint at the hottest API function `func_sound_op` (0x01BC) and captured
   register state at two separate hits to **dynamically confirm** the calling convention.
3. For all other functions, parameters were derived from the Stage 3 MCP disassembly
   (register reads at entry, `LDA`/`STA`/`LHLD`/`SHLD` operands, `RET`-path register writes).
4. Recorded each result via `debug_set_rdb_property(address, "params", ...)` and saved with
   `debug_save_rdb`.

## Runtime evidence (Fact, MCP-observed)
Breakpoint at `func_sound_op` (0x01BC), registers at entry:

| Hit | A (op index) | E (value) | Conclusion |
|-----|--------------|-----------|------------|
| 1 | 0x00 | 0x98 | A = op index, E = value |
| 2 | 0x09 | 0x0F | A = op index (9 = enable ch1), E = value |

Confirms the sound API convention `A = op_index(0..15)`, `E = value` used throughout the
sound and music subsystems.

## Result summary
```
Mapping entry point: 0x0000  (program entry func_entry = 0x0100)
Objects: 106   (69 functions)
Functions with params property: 69 / 69  (100%)
Links:   76
RDB:     /home/alexey/Projects/vector-games/roms/redesign/putup/src/putup.rdb
RDB save: success (dirty = false)
```

---

## Parameter conventions by subsystem

### Sound engine (VI53)
| Function | Addr | Params |
|----------|------|--------|
| func_sound_op | 0x01BC | in: A=op_index(0..15), E=value; out: none. **Runtime-confirmed** |
| func_sound_init | 0x0121 | in: B=delay outer count; out: none (startup beep ch2) |
| func_snd_calc_period | 0x020E | in: HL=addr of note word; out: HL=12×value |
| func_snd_out_ch0/1/2 | 0x0201/0x022D/0x024E | in: none (period vars @0x031A/C/E); out: ports 0Bh/0Ah/09h |
| func_snd_enable_ch0/1/2 | 0x0290/0x029E/0x02AC | in: E=enable mask; out: none (control 0x36/0x76/0xB6 → port 08h) |
| func_snd_enable_ch01/02/12/012 | 0x02BA/0x02C0/0x02C6/0x02CC | in: E=mask; out: none (channel combos) |
| func_snd_toggle | 0x026E | in: E=channel bits; out: none (XOR var_snd_state @0x0320) |
| func_snd_gate_ch0/1/2 | 0x02D2/0x02EA/0x0302 | in: E=note/gate value (bit4=sustain, low nibble=note); out: none |

### Text / glyph
| Function | Addr | Params |
|----------|------|--------|
| func_coords_to_textbuf | 0x1BD4 | in: D=col x, E=row y; out: HL=0x5000+E*32+D |
| func_clear_textbuf | 0x1BE5 | in/out: none (fills 0x5000 with spaces) |
| func_set_text_ptr | 0x014F | in: HL=cursor addr; out: none (→0x0B53) |
| func_put_char | 0x0800 | in: A=char, HL=buffer addr; out: none (store + render) |
| func_render_glyph | 0x0803 | in: A=char, HL=buffer addr; out: none (VRAM; clobbers DE/BC; SP saved @0x08DD) |
| func_draw_char_at_hl | 0x0145 | in: A=char, HL=buffer addr; out: none (advances cursor) |
| func_print_char_at_ptr | 0x01A1 | in: A=char; out: none (draws at cursor 0x0B53, advances) |
| func_restore_cursor | 0x01AE | in: none (coords @0x08FE/FF); out: none |
| func_print_string | 0x0321 | in: HL=string (0xFF-terminated); out: none |
| func_print_uint16 | 0x0331 | in: HL=addr of u16; out: none (5-digit decimal) |
| func_divmod_u16 | 0x0355 | in: HL=dividend, DE=divisor; out: A=quotient, DE=remainder |
| func_hl_add_a | 0x032C | in: HL=base, A=offset; out: HL=HL+A |
| func_draw_tile_to_buf | 0x1B87 | in: D=col, E=row, HL=4 source chars; out: none (2×2 tile → buffer) |
| func_render_tile_vram | 0x1BA8 | in: D=col, E=row, HL=4 source chars; out: none (2×2 tile → VRAM) |
| func_draw_tile_at_ptr | 0x0104 | in: HL=addr of coord word; out: none (2×2 tile at coords) |
| func_memcpy | 0x1BC9 | in: HL=src, DE=dst, BC=count; out: none |

### Graphics
| Function | Addr | Params |
|----------|------|--------|
| func_draw_image | 0x0401 | in: none (src 0x3041, dst 0x6000); out: none |
| func_blit_plane_mask80/40/20/10 | 0x0439/0x045E/0x0483/0x04A8 | in: HL=dst plane, DE=src; out: none |
| func_load_gfx_2761 | 0x04CD | in: none (src 0x2761 → 0x6000); out: none |

### Input
| Function | Addr | Params |
|----------|------|--------|
| func_read_keybuf | 0x0197 | in: A=row index; out: A=matrix byte @0x08D3+A |
| func_decode_key | 0x0153 | in: A=0 to trigger (guard); out: A=keycode (table @0x016C) |
| func_check_start_key | 0x017C | in: A=0 to trigger (guard); out: A=0xFF if SPACE/SHIFT else 0x00 |

### Music sequencer
| Function | Addr | Params |
|----------|------|--------|
| func_music_tick | 0x3858 | in/out: none (per-frame, from ISR) |
| func_music_init | 0x3D4E | in/out: none (resets vars, loads track base @0x3856) |
| func_music_start_track | 0x3DCD | in/out: none (setup @0x3DE8; VI53 control 0x36/0x76/0xB6) |
| func_music_set_note_params | 0x3B0F | in: HL=note selector; out: none (fills buf @0x3845) |
| func_music_load_voice_params | 0x3902 | in: none (buf @0x3845); out: none (14 params → engine) |
| func_music_play_note_ch0 | 0x3BCA | in: none (track ptr @0x3854); out: none (table @0x445D) |
| func_music_play_note_ch1 | 0x3C7D | in: none (track ptr, flag @0x3BC8); out: none (table @0x42F9) |
| func_music_process_voice | 0x3946 | in/out: none |
| func_snd_op_keep_a / _a2 / _a3 | 0x3940 / 0x3C77 / 0x3D48 | in: A=op, E=value; out: A preserved (PSW saved) |
| func_memcpy_keep_psw | 0x3DB8 | in: HL=src, DE=dst, BC=count; out: PSW preserved |

### Game logic
| Function | Addr | Params |
|----------|------|--------|
| func_entry | 0x0100 | in/out: none (DI; JMP main_init) |
| func_main_init | 0x0B57 | in/out: none (SP=0x0100; full init) |
| func_hw_init | 0x0383 | in/out: none (vectors + EI) |
| func_vblank_isr | 0x03A4 | in/out: none (ISR; preserves H/D/B/PSW) |
| func_game_update | 0x0CE0 | in/out: none (reads state @0x0900, pos @0x0901/2) |
| func_draw_game_objects | 0x130A | in/out: none (coords @0x0909/A, tile idx @0x090C) |
| func_score_and_redraw | 0x0F09 | in/out: none (score += 10×val @0x08F3) |
| func_erase_char_08E9 | 0x0CA3 | in/out: none (reads packed pos @0x08E9) |
| func_draw_score_hud | 0x1197 | in/out: none (score @0x08F3) |
| func_draw_status_hud | 0x121A | in/out: none (lives @0x08F5, icons @0x091E) |
| func_draw_level_hud | 0x11EE | in/out: none (level @0x08FB → @0x091D) |
| func_play_sfx | 0x11E9 | in: none (B=2 internal); out: none |
| func_prng | 0x1123 | in: none (state @0x1155); out: A=random byte |
| func_delay | 0x0EF7 | in: B=outer count; out: none (~B×4096 cyc) |
| func_delay_long | 0x1477 | in: B=outer count; out: none (~B×65536 cyc) |

---

## Verified Facts
- `func_sound_op` convention (A=op, E=value) confirmed at runtime via 2 breakpoint hits.
- All 69 functions carry a `params` property (100% coverage), stored in RDB and saved.

## Inferences (Medium)
- Register-based (not stack-based) calling convention throughout — typical hand-written 8080.
- Coordinate helpers consistently use D=column, E=row; buffer/VRAM addresses returned in HL.
- Sound and music share the `A=op, E=value` API via three identical PSW-preserving wrappers.

## Unknowns
- Exact set of `op_index` values used by the music sequencer per note (only op 0x00 and 0x09
  observed live this stage); full enumeration deferred to Stage 5 (interrupt/music research).
- Whether any function relies on flags passed in from the caller (not observed).

## Limitations
- Only `func_sound_op` was confirmed by live breakpoint; the remaining conventions come from
  static disassembly analysis (High confidence for entry-register reads, Medium for
  less-frequently-called helpers).

## Recommended Next Steps (Stage 5)
- Research the interrupt vectors (0x0000 reset, 0x0038 RST7) and `func_vblank_isr` in detail;
  enumerate the music `op_index` values by tracing the sequencer across several frames.
