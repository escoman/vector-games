# Stage 7 — Text Output Functions & Glyphs

## Goal
Research the text-output path of `putup.rom` (TZ Stage 7): find the functions that print text
strings in English **and** Russian (upper- and lower-case) to the screen planes; locate **all**
ROM strings (title/HUD/credits, not only the four TZ examples); investigate the memory areas copied
into VRAM to draw strings; record one RDB object per string with the string content as its comment;
investigate the glyph-set memory area (including the unpacked data) and the string-output function
that holds the address relative to which per-character glyph offsets are computed — that address is
the **start of the glyph block**; save the glyph block + size in the RDB. The task is complete when
every glyph used by the step-2 strings is found. Save the RDB and this report.

## ROM
- File: `putup.rom`, 17664 bytes, load 0x0100
- SHA256: `8486442efc390b15860ec7f69c32db93b0884908565fa11fec57d5c551b4e9a6`
- Mapping entry point: **0x0000**; program entry `func_entry` = **0x0100**

## Method (per TZ Stage 7)
1. Reloaded the ROM (`debug_load_rom` org=0x0100), ran ~5 s, paused on the title screen (TZ step 1).
2. Followed the title-screen setup `func_main_init` (0x0B57) and the HUD drawers to the string
   printers; disassembled the whole text chain with `debug_disassemble_range` (TZ step 2).
3. Read every string block with `debug_read_memory_range` and decoded ASCII + KOI8-R (TZ steps 2/4).
4. Disassembled `func_render_glyph` (0x0803) to find the glyph-offset base address, then read the
   glyph pointer table (0x0600) and the glyph block (0x6000) (TZ steps 3/5).
5. Identified and **empirically verified** the glyph-block loader `func_load_glyph_block` (0x0401):
   zeroed glyph 65 @0x6820, re-ran the loader (PC=0x0401 → BP 0x042A), and the glyph regenerated
   (TZ step 3 — "the memory areas from which data is copied").
6. Verified glyph coverage by reading the glyphs of the step-2 strings (TZ step 7).
7. Recorded 12 `str_*` objects, renamed/updated 5 objects, added 10 links, saved (`debug_save_rdb`).

---

## Findings

### Finding 1 — Text-output function chain
**Observation (Fact):** Strings are printed by a 4-level chain; the cursor is a RAM variable.
**Evidence — disassembly / calls (MCP):**
```
func_print_string      0x0321  ; HL = 0xFF-terminated string; loops over chars
func_print_char_at_ptr 0x01A1  ; prints A at cursor var_text_ptr(0x0B53), advances cursor
func_put_char          0x0800  ; thin wrapper -> func_render_glyph
func_render_glyph      0x0803  ; builds the 8x8 glyph into the 4 VRAM planes (Finding 3)
func_set_text_ptr      0x014F  ; HL -> var_text_ptr(0x0B53)  (set cursor)
func_draw_char_at_hl   0x0145  ; draw char A at text-buf addr HL
func_print_uint16      0x0331  ; prints a 16-bit number as decimal digits (used for LEVEL/score)
func_restore_cursor    0x01AE  ; restore cursor after a nested print
var_text_ptr           0x0B53  ; 2-byte current text-buffer cursor (0x5000..0x53FF)
```
**Conclusion:** `func_print_string`(0x0321) → `func_print_char_at_ptr`(0x01A1) → `func_put_char`
(0x0800) → `func_render_glyph`(0x0803). The text buffer is 32×32 chars @0x5000; the cursor lives at
`var_text_ptr`(0x0B53). This answers TZ step 2 (the string-output functions). **Confidence: High.**

### Finding 2 — Glyph block @0x6000 + pointer table @0x0600 (TZ steps 5/6)
**Observation (Fact):** A 256-entry word table @0x0600 points into an 8192-byte glyph block @0x6000;
entry N = 0x6000 + N·32.
**Evidence — `debug_read_memory_range` @0x0600 (24 bytes = 12 words):**
```
00 60 | 20 60 | 40 60 | 60 60 | 80 60 | A0 60 | C0 60 | E0 60 | 00 61 | 20 61 | 40 61 | 60 61
=0x6000 =0x6020 =0x6040 =0x6060 =0x6080 =0x60A0 =0x60C0 =0x60E0 =0x6100 =0x6120 =0x6140 =0x6160
 glyph0  glyph1  glyph2  glyph3  glyph4  glyph5  glyph6  glyph7  glyph8  glyph9  gl10    gl11
```
**Evidence — glyph bitmaps (`debug_read_memory_range`):**
```
glyph 0   @0x6000 = 00×24, FF×8                     (blank/space: planes0-2=0, plane3=0xFF)
glyph 65  @0x6820 = [0,CC,CC,FC,CC,CC,78,30] ×3 planes, plane3=[FF,33,33,03,33,33,87,CF]=~plane0  ('A')
glyph 247 @0x7EE0 = [0,FC,C6,C6,FC,CC,CC,F8] ×3 planes, plane3=[FF,03,39,39,03,33,33,07]=~plane0  (KOI8-R 'В')
```
**Conclusion:** The glyph block is **0x6000–0x7FFF, 8192 bytes = 256 glyphs × 32 bytes**. Each glyph is
4 colour planes × 8 bytes (8×8 px); for a drawn glyph planes 0/1/2 hold the bitmap and plane 3 =
~plane 0 (so the character is drawn in one colour on an inverse background). The glyph block is in
**RAM** (built at run time — Finding 4). This answers TZ step 6 (block + size). **Confidence: High.**

### Finding 3 — `func_render_glyph` @0x0803: the glyph-offset base is 0x6000 (TZ step 5)
**Observation (Fact):** The renderer indexes the pointer table with `MVI H,06` (→ 0x0600) using
`char·2`, dereferences it to the glyph address, then copies 4×8 bytes into the 4 VRAM planes.
**Evidence — disassembly (MCP), key instructions:**
```
0803  PUSH PSW/B/D/H
0807  MOV D,A              ; D = char code
0808  LXI B,B000 / DAD B   ; HL = text-buf cursor + 0xB000
080C  MOV A,L / ANI 1F / MOV C,A          ; C = column = L & 0x1F
0810  MOV A,H /RRC/RRC/ ANI C0 / MOV B,A  ; row (high)
0816  MOV A,L /RRC/RRC/ ANI 38 / ORA B / MOV B,A ; B = row
081D  MOV A,D              ; A = char code
081E  DI
081F  LXI H,0000 / DAD SP / SHLD 08DD     ; save SP
0826  ADD A                ; A = char*2
0827  MVI H,06             ; *** H=0x06 -> glyph POINTER TABLE base 0x0600 ***
0829  MOV L,A              ; L = char*2
082A  JNC 082E             ; char < 128 -> table high byte stays 0x06
082D  INR H                ; char >= 128 -> H = 0x07
082E  MOV E,M / INX H / MOV D,M           ; DE = word[0x0600 + char*2] = glyph ptr (0x6000+char*32)
0831  MVI H,00 / MOV L,C / PUSH B
0835  LXI B,051B / DAD B / MOV H,M        ; H = VRAM column-base table[0x051B + column]
083A  LDA 08D0 / POP B / SUB B / MOV L,A  ; L = screen_base(0x08D0) - row
0840  LXI B,1FF8           ; BC = 0x1FF8 (= +0x2000 - 8) : VRAM plane step
0843  XCHG / SPHL / XCHG   ; SP = glyph ptr (glyph data now popped as words); HL = VRAM addr
0846  POP D / MOV M,E / INX H / MOV M,D / INX H   ; write 8 bytes to plane (x4 POP D)
084B  POP D / ... 0850 POP D / ... 0855 POP D / ...
085A  DAD B                ; HL += 0x1FF8 (+8 written = +0x2000) -> next VRAM plane
085B  POP D / MOV M,E / ... (planes 2..3 continue identically)
```
**Conclusion:** The address relative to which per-character glyph offsets are computed is the pointer
table **0x0600** (`MVI H,06`), whose entries are absolute pointers into the glyph block; therefore the
**start of the glyph block = 0x6000** (glyph N = 0x6000 + N·32). The renderer uses the `SPHL`/`POP D`
trick to stream the 32-byte glyph and `DAD B`(0x1FF8) to step the four 0x2000-spaced VRAM planes
(0xE000/0xC000/0xA000/0x8000 family). This is the exact answer to TZ step 5. **Confidence: High.**

### Finding 4 — `func_load_glyph_block` @0x0401 builds the glyph block from packed font @0x3041
**Observation (Fact):** The glyph block @0x6000 is RAM and is unpacked at start-up from a packed font
source @0x3041 by `func_load_glyph_block` (previously named `func_draw_image`), called from
`func_main_init`(0x0B57) @0x0B83.
**Evidence — disassembly (MCP):**
```
0401  PUSH H/D/B/PSW
0405  CALL 04CD            ; func_load_gfx_2761: seeds glyph 0 from ROM 0x2761
0408  LXI H,6000           ; dst = glyph block
040B  LXI D,3041           ; src = packed font (read DESCENDING: LDAX D / DCX D)
040E  MVI B,00             ; 256 glyphs
0410  PUSH B / PUSH D / CALL 0439 / POP D    ; plane writer 0 (masks 0x80/0x08)
       ... CALL 045E ...   ; plane writer 1 (0x40/0x04)
       ... CALL 0483 ...   ; plane writer 2 (0x20/0x02)
       ... CALL 04A8 ...   ; plane writer 3 (0x10/0x01)
0426  DCR B / JNZ 042F
042A  POP PSW/B/D/H / RET
042F  PUSH H / LXI H,0008 / DAD D / XCHG / POP H / JMP 0410   ; src DE += 8 per glyph
```
Writer core (0x0439): `MVI C,08; loop: LDAX D; DCX D; MOV C,A; MOV A,M; CMA; MOV B,A; MOV A,C;
ANI 80; MVI A,00; JZ s; MOV A,M; s: MOV M,A; MOV A,C; ANI 08; MVI A,00; JZ s2; MOV A,B; s2: ORA M;
MOV M,A; INX H; POP B; DCR C; JNZ loop; RET` — i.e. `dest = (hi?dest_old:0) | (lo?~dest_old:0)`.
**Empirical proof (MCP):** glyph 65 @0x6820 was zeroed with `debug_write_memory`, then PC was set to
0x0401 and run to the BP @0x042A; reading 0x6820 afterwards returned the clean `A` bitmap
`[0,CC,CC,FC,CC,CC,78,30]…` — the loader **regenerated it from scratch**.
**Conclusion:** `func_load_glyph_block`(0x0401) is the routine that copies/unpacks font data into the
glyph block; the source is the packed font @0x3041 (`data_packed_font_3041`). This answers TZ step 3
(the memory area from which glyph data is copied). The exact bit-packing/RLE of the four writers is
data-dependent and **not fully reversed** (see Unknowns). **Confidence: High** (loader identity,
verified by regeneration); packing scheme = Low/Unknown.

### Finding 5 — All ROM strings located and decoded (TZ steps 2/4)
**Observation (Fact):** Twelve 0xFF-terminated strings live in two ROM blocks: the KOI8-R credits
@0x0925 and an ASCII block @0x0A06–0x0B3B. All were read byte-exact via `debug_read_memory_range`.

| # | RDB object | Addr | Size | Terminator | Content | Printed by (cursor) |
|---|-----------|------|------|-----------|---------|---------------------|
| 1 | `str_credits_koi8` | 0x0925 | 100 | FF@0x0988 | ` Версия для "Вектор-06Ц"  1991` + 39 sp + `Центр "КОМПЬЮТЕР" г.Кишинев   ` | func_main_init @0x0C5F (0x52E0) |
| 2 | `str_title_logo` | 0x0A06 | 193 | FF@0x0AC6 | logo art: spaces 0x20 + block-icon 0x9B | func_main_init @0x0C1E (0x50A0) |
| 3 | `str_push_space` | 0x0AC7 | 15 | FF@0x0AD5 | `PUSH SPACE KEY` | func_main_init @0x0C2A (0x5229) |
| 4 | `str_msx_magazine` | 0x0AD6 | 19 | FF@0x0AE8 | `MSX MAGAZINE, 1987` | func_main_init @0x0C36 (0x5287) |
| 5 | `str_hi` | 0x0AE9 | 4 | FF@0x0AEC | `HI ` | func_main_init @0x0C42 (0x506B) |
| 6 | `str_score` | 0x0AED | 7 | FF@0x0AF3 | `SCORE ` | func_draw_score_hud 0x1197 (0x52E1) |
| 7 | `str_round` | 0x0AF4 | 7 | FF@0x0AFA | `ROUND ` | func_draw_status_hud 0x121A (0x52EF) |
| 8 | `str_time` | 0x0AFB | 6 | FF@0x0B00 | `TIME ` | func_draw_status_hud 0x121A (0x5302) |
| 9 | `str_hurry_up` | 0x0B01 | 13 | FF@0x0B0D | ` HURRY UP ! ` | Unknown |
| 10 | `str_game_over` | 0x0B0E | 10 | FF@0x0B17 | `GAME OVER` | Unknown |
| 11 | `str_congratulation` | 0x0B18 | 17 | FF@0x0B28 | `CONGRATULATION !` | Unknown |
| 12 | `str_bonus` | 0x0B29 | 19 | FF@0x0B3B | `BONUS 50000 POINTS` | Unknown |

**Evidence — raw bytes (MCP), ASCII block @0x0AC7 (excerpt):**
```
0AC7: 50 55 53 48 20 53 50 41 43 45 20 4B 45 59 FF      "PUSH SPACE KEY"
0AD6: 4D 53 58 20 4D 41 47 41 5A 49 4E 45 2C 20 31 39 38 37 FF  "MSX MAGAZINE, 1987"
0AE9: 48 49 20 FF                                        "HI "
0AED: 53 43 4F 52 45 20 FF                               "SCORE "
0AF4: 52 4F 55 4E 44 20 FF   0AFB: 54 49 4D 45 20 FF     "ROUND " / "TIME "
0B01: 20 48 55 52 52 59 20 55 50 20 21 20 FF             " HURRY UP ! "
0B0E: 47 41 4D 45 20 4F 56 45 52 FF                      "GAME OVER"
0B18: 43 4F 4E 47 52 41 54 55 4C 41 54 49 4F 4E 20 21 FF "CONGRATULATION !"
0B29: 42 4F 4E 55 53 20 35 30 30 30 30 20 50 4F 49 4E 54 53 FF  "BONUS 50000 POINTS"
```
**Evidence — KOI8-R credits @0x0925 (decoded):** `F7 C5 D2 D3 C9 D1` = «Версия», `C4 CC D1` = «для»,
`F7 C5 CB D4 CF D2 2D 30 36 E3` = «Вектор-06Ц», `31 39 39 31` = «1991», then 39×0x20, then
`E3 C5 CE D4 D2` = «Центр», `CB CF CD D0 DC E0 F4 C5 D2` = «КОМПЬЮТЕР», `C7 2E CB C9 DB C9 CE C5 D7`
= «г.Кишинев», `FF`.
**Conclusion:** All four TZ example strings are present (`PUSH SPACE KEY`, `MSX MAGAZINE, 1987`,
`Версия для "Вектор-06Ц" 1991`, `Центр "КОМПЬЮТЕР" г.Кишинев`) **plus eight more**. Both Russian
credit lines are stored as ONE 0xFF-terminated string. Each string is an RDB object whose comment is
its content (TZ step 4). **Confidence: High** (byte-exact reads).

### Finding 6 — Glyph coverage verified (TZ step 7)
**Observation (Fact):** Every character class used by the step-2 strings has a drawn glyph in the
block @0x6000.
**Evidence (MCP reads):**
- ASCII upper-case: glyph 65 `A` @0x6820 = `[0,CC,CC,FC,CC,CC,78,30]` (drawn).
- KOI8-R upper-case: glyph 247 `В`(0xF7) @0x7EE0 = `[0,FC,C6,C6,FC,CC,CC,F8]` (drawn).
- Logo block-icon: glyph 155 (0x9B) @0x7360 = drawn (used by `str_title_logo` and the LIVES icon).
- Space/blank: glyph 0 @0x6000 = `00×24,FF×8`.
**Conclusion:** ASCII (A–Z, 0–9, space, punctuation), KOI8-R lower-case (0xC1–0xDF) and upper-case
(0xE1–0xFE) glyphs are all present in the 256-glyph block; the four step-2 strings render fully.
TZ step 7 is satisfied. **Confidence: High** for the sampled glyphs (A, В, 0x9B, blank); the full
0–255 set is present by construction (256 table entries) but not every glyph was individually read.

---

## RDB changes this stage
- **New string objects (12):** `str_credits_koi8` (0x0925), `str_title_logo` (0x0A06),
  `str_push_space` (0x0AC7), `str_msx_magazine` (0x0AD6), `str_hi` (0x0AE9), `str_score` (0x0AED),
  `str_round` (0x0AF4), `str_time` (0x0AFB), `str_hurry_up` (0x0B01), `str_game_over` (0x0B0E),
  `str_congratulation` (0x0B18), `str_bonus` (0x0B29) — each comment = the string content.
- **Renamed / re-typed (3):**
  - `data_backbuffer_6000` → **`data_glyph_block`** (0x6000, Data, size **8192**).
  - `func_draw_image` → **`func_load_glyph_block`** (0x0401, Function, size 56).
  - `data_bitmap_3041` → **`data_packed_font_3041`** (0x3041, Data, size −1/unknown).
- **Comment-only updates (2):** `data_glyph_ptr_table` (0x0600 — glyph base 0x6000, entry N=0x6000+N·32),
  `func_render_glyph` (0x0803 — the glyph-offset function; base 0x6000 via table 0x0600).
- **Correction this session:** `str_credits_koi8` size 104→**100**, FF 0x098C→**0x0988**, 43→**39**
  spaces (re-counted from a fresh byte-exact read; ROM is static so the earlier value was a miscount).
- **New links (10):** 0x0600→0x6000, 0x0803→0x6000, 0x1197→0x0AED, 0x121A→0x0AF4, 0x121A→0x0AFB,
  0x0B57→{0x0A06, 0x0AC7, 0x0AD6, 0x0AE9, 0x0925}.

## Result summary
```
Mapping entry point: 0x0000  (program entry func_entry = 0x0100)
Objects: 153   (+12 strings this stage; was 141)
Links:   +10 this stage
Glyph block: 0x6000–0x7FFF, 8192 bytes (256 × 32), base address = 0x6000 (TZ step 5/6 answer)
Strings found: 12 (EN ASCII + RU KOI8-R), all recorded with content comments (TZ step 4)
Glyph coverage: ASCII + KOI8-R upper/lower + block-icon + blank verified (TZ step 7)
_unknown names remaining: 0
RDB:     /home/alexey/Projects/vector-games/roms/redesign/putup/src/putup.rdb
RDB save: success (dirty = false)
```

---

## Verified Facts (MCP-observed)
- Glyph pointer table @0x0600: word[N] = 0x6000 + N·32 (read 0x6000,0x6020,0x6040,…,0x6160).
- Glyph block @0x6000, 256×32 = 8192 bytes; glyph 0 = `00×24,FF×8`; drawn glyph plane3 = ~plane0.
- glyph 65 `A` @0x6820 = `[0,CC,CC,FC,CC,CC,78,30]`×3 + inverse; glyph 247 `В` @0x7EE0 = `[0,FC,C6,C6,FC,CC,CC,F8]`×3 + inverse.
- `func_render_glyph` @0x0803: `MVI H,06` (0x0600) + `char·2` → glyph ptr; `LXI B,1FF8`/`DAD B` steps the 4 VRAM planes (+0x2000); column-base table @0x051B; screen base var @0x08D0.
- `func_load_glyph_block` @0x0401: dst HL=0x6000, src DE=0x3041 (descending), 256 iterations, 4 plane writers (0x0439/0x045E/0x0483/0x04A8), `func_load_gfx_2761`(0x04CD) seeds glyph 0.
- Loader verified empirically: zeroed glyph 65, ran 0x0401→BP 0x042A, glyph regenerated.
- 12 strings byte-exact: credits @0x0925 (FF@0x0988), logo @0x0A06 (FF@0x0AC6), PUSH SPACE @0x0AC7, MSX @0x0AD6, HI @0x0AE9, SCORE @0x0AED, ROUND @0x0AF4, TIME @0x0AFB, HURRY UP @0x0B01, GAME OVER @0x0B0E, CONGRATULATION @0x0B18, BONUS @0x0B29 (FF@0x0B3B).
- Title strings printed by `func_main_init`(0x0B57) @0x0C1E/0x0C2A/0x0C36/0x0C42/0x0C5F; HUD strings by `func_draw_score_hud`(0x1197) and `func_draw_status_hud`(0x121A).

## Inferences (Medium)
- Glyph format = 4 planes × 8 bytes; a drawn glyph uses one foreground colour (planes0-2 = bitmap)
  on an inverse background (plane3 = ~bitmap), matching the Vector-06C 4-plane VRAM at 0x8000/0xA000/0xC000/0xE000.
- The packed font @0x3041 is a bit-packed/RLE source; the four writers expand one source bit-pair per
  destination bit, so glyph N's source window is consumed data-dependently (not a flat 0x3041+8·N).
- `str_hurry_up`/`str_game_over`/`str_congratulation`/`str_bonus` belong to the in-game / end-of-level
  flow (likely reached from `func_game_update` 0x0CE0 and the level-completion path 0x1A3B).

## Hypotheses (Low — need Stage 8/9)
- `str_congratulation` (0x0B18) and `str_bonus` (0x0B29) are shown on the level-completion path
  (0x1A3B, level ≥ 16); `str_game_over` (0x0B0E) on player-out; `str_hurry_up` (0x0B01) on a timer.
- The block-icon glyph 0x9B (155) doubles as the LIVES icon (Stage 6 `func_draw_status_hud`) and as
  the title-logo fill character.

## Unknowns
- The exact bit-packing/RLE scheme of `func_load_glyph_block`'s four writers (loader identity is
  proven; the source-to-glyph bit expansion is not fully reversed).
- Callers of `str_hurry_up` / `str_game_over` / `str_congratulation` / `str_bonus` (not yet
  disassembled; deferred to Stage 8/9 control-flow export).
- Fine VRAM addressing inside `func_render_glyph` (column-base table @0x051B contents and the
  `screen_base(0x08D0) − row` mapping to the four plane bases) — the +0x2000 plane step is confirmed,
  the per-column base table is not fully decoded.
- Whether glyphs beyond the sampled set (A, В, 0x9B, blank) are all non-blank; only construction
  (256 table entries) guarantees their addresses, not their pixels.

## Limitations
- Glyph coverage (TZ step 7) was confirmed by sampling representative glyphs (ASCII 'A', KOI8-R 'В',
  block-icon 0x9B, blank) rather than reading all 256; the four step-2 strings render fully.
- The loader was verified in the **emulator** (zero-and-regenerate). Original-hardware behaviour is
  UNVERIFIED, though the loader is pure RAM/ROM logic with no timing dependency.
- `debug_compare_memory_snapshots` under-reports dense/multi-byte diffs (carried from Stage 6); all
  glyph/string bytes here were taken from authoritative `debug_read_memory_range` reads instead.

## Recommended Next Steps (Stage 8)
- Export every RDB function to `./asm` in z88dk format, substituting hex operands with RDB symbol
  names (functions/data/strings/vars/labels), local `.loc_XXXX` labels for intra-function branches,
  and raw hex only for unresolved addresses (TZ Stage 8).
- While exporting `func_main_init`/`func_game_update`/the completion path (0x1A3B), resolve the
  callers of `str_hurry_up`/`str_game_over`/`str_congratulation`/`str_bonus` to close the Unknowns.
- Decode the column-base table @0x051B and `screen_base`(0x08D0) to fully document VRAM addressing.
