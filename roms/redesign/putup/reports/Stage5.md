# Stage 5 — Interrupt Research (special focus: hardware RST 7)

## Goal
Research the interrupt architecture of `putup.rom` using facts from `docs/VECTOR_VERIFIED.md`,
inspect the interrupt vector addresses for the subroutines installed there, record/update the
interrupt information in the RDB, and pay special attention to the hardware interrupt **RST 7**.
Save the RDB.

## ROM
- File: `putup.rom`, 17664 bytes, load 0x0100
- SHA256: `8486442efc390b15860ec7f69c32db93b0884908565fa11fec57d5c551b4e9a6`
- Mapping entry point: **0x0000**; program entry `func_entry` = **0x0100**

## Method (per TZ Stage 5)
1. Reloaded the ROM (`debug_load_rom` org=0x0100), set PC=0x0100, ran ~5 s, paused.
2. Read the runtime contents of the interrupt-vector page 0x0000–0x00FF.
3. Disassembled `func_hw_init` (0x0383) and `func_vblank_isr` (0x03A4) via `debug_disassemble_range`.
4. Set a breakpoint at 0x03A4 and ran to confirm the ISR is entered by the hardware RST 7;
   captured the interrupted return address and the frame-counter increment across two hits.
5. Recorded vectors/comments/properties/links in the RDB and saved.

## Reference facts (docs/VECTOR_VERIFIED.md)
| Fact | Value | Status |
|------|-------|--------|
| 0000h–00FFh = interrupt/RST vector area (RAM after boot ROM disabled) | §6.1, §6.2 | VERIFIED_BY_CODE |
| 0000h = RESET vector | §6.1 | VERIFIED_BY_CODE |
| 0038h = RST 7 (VBlank) vector | §6.1 | VERIFIED_BY_CODE |
| Frame rate ≈ 50.08 Hz (312 lines, 22 VSync lines) | §7.4.2 | VERIFIED_BY_CODE |
| Palette colour written via `OUT 0Ch` | §7.3 | VERIFIED_BY_CODE |
| Scrolling is on Port A (`OUT 03h`), not Port C | §7.4.1 | VERIFIED (CONFLICT with VECTOR.MD) |

---

## Findings

### Finding 1 — The ROM installs exactly two interrupt vectors
**Location:** 0x0000 (RESET), 0x0038 (RST 7); installer `func_hw_init` @0x0383
**Observation (Fact):** After the 5 s run, the runtime bytes of the vector page are:
- `0x0000 = C3 57 0B` → `JMP 0x0B57` (`func_main_init`)
- `0x0038 = C3 A4 03` → `JMP 0x03A4` (`func_vblank_isr`)
- `0x0008/0x0010/0x0018/0x0020/0x0028/0x0030 = 00` → **unused** (RST 1..RST 6 not wired)
- The rest of 0x003B–0x00E7 is zero; 0x00E8–0x00FF holds live **stack** residue (SP top = 0x0100).

**Evidence — `func_hw_init` disassembly (MCP):**
```
0383  XRA A          ; A = 0
0384  OUT 10         ; system/bank control port 10h <- 0
0386  STA 08CF       ; scroll / Port A shadow = 0
0389  MVI A,E0
038B  STA 08D0       ; Port B / mode shadow = E0h
038E  MVI A,C3       ; JMP opcode
0390  STA 0038       ; [0x0038] = C3h      (RST7 vector opcode)
0393  STA 0000       ; [0x0000] = C3h      (RESET vector opcode)
0396  LXI H,03A4     ; HL = func_vblank_isr
0399  SHLD 0039      ; [0x0039..0x003A] = A4 03  -> RST7 = JMP 0x03A4
039C  LXI H,0B57     ; HL = func_main_init
039F  SHLD 0001      ; [0x0001..0x0002] = 57 0B  -> RESET = JMP 0x0B57
03A2  EI             ; enable interrupts
03A3  RET
```
**Conclusion:** `func_hw_init` patches the RESET vector to re-enter `func_main_init` (warm-reset
re-init) and the RST 7 vector to `func_vblank_isr`, then enables interrupts. **Confidence: High.**

### Finding 2 — RST 7 is the VBlank ISR and fires every frame
**Location:** `func_vblank_isr` @0x03A4 (vector 0x0038)
**Observation (Fact):** A breakpoint at 0x03A4 is hit repeatedly while the ROM runs;
`debug_get_state` reports `current_function = func_vblank_isr`, first instruction `PUSH H`,
`IFF = true`. The 1-byte frame counter `var_frame_counter`@0x08DF read **130 → 131** between two
consecutive hits (increment of exactly 1 per interrupt = one 50 Hz frame).
The hardware-pushed return address on the stack (`[SP]` = `[0x00FA]`) was **0x017C**
(`func_check_start_key`) — i.e. VBlank interrupted the **title-screen SPACE-key poll**.
**Conclusion:** The video controller raises **RST 7** at each vertical blank; the CPU vectors to
0x0038 → `func_vblank_isr`. This is the only hardware interrupt used by the program.
**Confidence: High** (runtime-confirmed).

### Finding 3 — What the RST 7 ISR does (full breakdown)
**Location:** `func_vblank_isr` 0x03A4–0x0400
**Evidence — disassembly (MCP):**
```
03A4  PUSH H / PUSH D / PUSH B / PUSH PSW   ; save H,D,B,PSW
03A8  LXI H,08DF
03AB  INR M            ; (1) frame_counter++ (@0x08DF)
03AC  LXI H,08C3
03AF  XRA A
03B0  CMP M            ; (2) palette_timer (@0x08C3) == 0 ?
03B1  JZ 03D1          ;     if 0 -> skip palette effect, go to keyboard scan
03B4  DCR M            ;     palette_timer--
03B5  LXI D,100F
03B8  LHLD 08DB        ;     HL = palette_ptr (@0x08DB)
03BB  MOV A,E          ;     --- timed palette loop ---
03BC  OUT 02           ;     Port B <- E (palette index/address)
03BE  MOV A,M          ;     A = [HL] colour byte
03BF  OUT 0C           ;     write colour to palette (port 0Ch)
03C1  DCR C
03C2  OUT 0C
03C3  INR C
03C4  NOP / NOP / NOP
03C7  DCX H
03C8  OUT 0C
03CA  DCR E
03CB  DCR D
03CC  OUT 0C
03CE  JNZ 03BB         ;     loop while D != 0
03D1  MVI A,8A         ; (3) keyboard scan setup
03D3  OUT 00           ;     VV55 control = 8Ah (Port A out, Port B in)
03D5  LXI H,08D3       ;     HL = kbd matrix buffer (0x08D3..0x08DA)
03D8  MVI A,FE         ;     row-select mask = FEh
03DA  PUSH PSW         ;     --- 8-row scan loop ---
03DB  OUT 03           ;     Port A <- mask (select keyboard row)
03DD  IN 02            ;     A = Port B (read keyboard columns)
03DF  MOV M,A          ;     store row byte into matrix buffer
03E0  POP PSW
03E1  INX H            ;     next row
03E2  RLC              ;     rotate mask
03E3  JC 03DA          ;     repeat 8 times (carry set after 8 rotates)
03E6  MVI A,88         ; (4) restore VV55
03E8  OUT 00           ;     control = 88h (all ports output)
03EA  MVI A,02
03EC  OUT 01           ;     Port C <- 02h
03EE  LDA 08CF
03F1  OUT 03           ;     Port A <- scroll shadow (@0x08CF)
03F3  LDA 08C4
03F6  OUT 02           ;     Port B <- portb_mode shadow (@0x08C4)
03F8  CALL 3858        ; (5) func_music_tick — advance music sequencer by one frame
03FB  POP PSW / POP B / POP D / POP H   ; restore registers
03FF  EI               ; re-enable interrupts
0400  RET
```
**Conclusion:** The RST 7 ISR is a classic VBlank handler that, in order:
1. increments the free-running **frame counter** (0x08DF);
2. runs an optional **timed palette effect** (only when `palette_timer`@0x08C3 ≠ 0) driven by
   `palette_ptr`@0x08DB, writing colours to the palette port `0Ch`;
3. **scans the 8×8 keyboard matrix** into 0x08D3..0x08DA (temporarily reconfiguring the KR580VV55:
   Port A = row select via `OUT 03h`, Port B = column read via `IN 02h`);
4. **restores the VV55** (control `88h`, Port C = `02h`, Port A/B from shadow vars 0x08CF/0x08C4);
5. calls **`func_music_tick` (0x3858)** so music advances in sync with the 50 Hz frame;
6. restores registers, `EI`, `RET`.
**Confidence: High** (disassembly + runtime confirmation).

### Finding 4 — No subroutines are copied into the low vector page
**Location:** 0x0000–0x00FF
**Observation (Fact):** The only non-zero bytes in this page after the run are the two 3-byte
vectors (0x0000, 0x0038) and the transient CPU **stack** (SP=0x0100 growing down; residue seen
from ~0x00E8). No code (music channels or otherwise) is relocated into 0x0000–0x00FF by this ROM.
**Conclusion / clarification:** Unlike the general Vector-06C note that the low page may hold
interrupt vectors *and* small subroutines, **this** ROM keeps all handler code in the ROM image
(0x0100+); the ISR reaches the music engine by `CALL 0x3858`, not by copied low-page stubs.
The low page is used solely for the two vectors plus the interrupt/return stack.
**Confidence: High.**

---

## Interrupt-related I/O used by the ISR
| Port | Direction | Purpose in ISR | Note |
|------|-----------|----------------|------|
| 00h | OUT | KR580VV55 control word (`8Ah` before scan, `88h` after) | reconfigures Port A/B direction |
| 01h | OUT | VV55 Port C (`02h`) | restored after scan |
| 02h | IN/OUT | VV55 Port B — keyboard **columns** (IN), palette index (OUT) | |
| 03h | OUT | VV55 Port A — keyboard **row select**; also scroll restore | scroll on Port A (VERIFIED §7.4.1) |
| 0Ch | OUT | Palette colour write | VERIFIED §7.3 |
| 10h | OUT | System/bank control (written 0 in `func_hw_init`) | init only |

## Interrupt-related variables (RDB)
| Var | Addr | Size | Role in RST 7 ISR |
|-----|------|------|-------------------|
| var_frame_counter | 0x08DF | 1 | INR every VBlank (50 Hz tick; wraps at 256) |
| var_palette_timer | 0x08C3 | 1 | countdown; ≠0 ⇒ run timed palette loop |
| var_palette_ptr | 0x08DB | 2 | palette data pointer (runtime value 0x08B2) |
| var_scroll | 0x08CF | 1 | VV55 Port A / scroll shadow, restored after scan |
| var_portb_mode | 0x08C4 | 1 | VV55 Port B shadow, restored after scan |
| (shadow) | 0x08D0 | 1 | init 0xE0 in func_hw_init (Port-B/mode shadow) |
| data_kbd_matrix | 0x08D3 | 8 | 8×8 keyboard matrix written by the scan (all 0xFF = no key) |

## RDB changes this stage
- **New objects (2):** `data_int_vector_reset` (0x0000, Data, 3 b), `data_int_vector_rst7` (0x0038, Data, 3 b) — with comments and `runtime_bytes` properties.
- **Updated comments (7):** `func_hw_init`, `func_vblank_isr`, `var_frame_counter`, `var_palette_timer`, `var_palette_ptr`, `var_scroll`, `var_portb_mode`.
- **New properties:** `func_vblank_isr.interrupt`, `func_hw_init.role`, both vectors' `runtime_bytes`.
- **New links (9):**
  - `data_int_vector_reset` → `func_main_init` (0x0B57)
  - `data_int_vector_rst7` → `func_vblank_isr` (0x03A4)
  - `func_hw_init` → 0x0000, `func_hw_init` → 0x0038
  - `func_vblank_isr` → 0x08DF, 0x08C3, 0x08DB, 0x08CF, 0x08C4
  - (links `func_vblank_isr`→0x3858/0x08D3 and `func_hw_init`→0x03A4 already existed from Stage 3)

## Result summary
```
Mapping entry point: 0x0000  (program entry func_entry = 0x0100)
Objects: 108   (69 functions, +2 interrupt-vector objects)
Links:   85    (+9 this stage)
_unknown names remaining: 0
RDB:     /home/alexey/Projects/vector-games/roms/redesign/putup/src/putup.rdb
RDB save: success (dirty = false)
```

---

## Verified Facts (MCP-observed)
- Runtime vector page: 0x0000 = `C3 57 0B` (JMP func_main_init); 0x0038 = `C3 A4 03` (JMP func_vblank_isr).
- RST 1..RST 6 vectors (0x08,0x10,0x18,0x20,0x28,0x30) are zero — unused.
- Breakpoint at 0x03A4 is hit while running; `current_function = func_vblank_isr`; `IFF = true`.
- `var_frame_counter`@0x08DF incremented 130 → 131 across two consecutive ISR entries (1 per frame).
- Interrupted return address on the stack = 0x017C (`func_check_start_key`) — title-screen key poll.
- `func_hw_init` writes the JMP opcode to 0x0000/0x0038 and the targets via `SHLD 0x0001`/`SHLD 0x0039`, then `EI`.
- Keyboard matrix 0x08D3..0x08DA all 0xFF at the observed instant (no key pressed).

## Inferences (Medium)
- RST 7 is generated by the video controller at vertical blank (~50.08 Hz); the frame counter and
  music tick are therefore frame-locked to the display.
- The palette loop is a timed effect (fade/flash) armed by setting `palette_timer`/`palette_ptr`
  elsewhere in the game code (not observed being armed during this title-screen window).
- The VV55 is time-shared: reconfigured for keyboard scan inside the ISR, then restored from
  shadow vars so main-loop Port A/B state (incl. scroll) is preserved.

## Hypotheses (Low — need Stage 6+)
- `palette_timer`/`palette_ptr` are armed by level-transition or death/flash effects.
- The music sequencer (`func_music_tick`) is the sole consumer of the per-frame tick; tempo is
  fixed to the 50 Hz frame.

## Unknowns
- Exact meaning of `OUT 10h` (system/bank control) beyond “written 0 at init” — not required for
  interrupt behaviour.
- The full set of palette-effect data pointed to by `palette_ptr` (0x08B2 region) — deferred.
- Complete enumeration of music `op_index` values (Stage 4 carry-over): the tick calls into the
  sound API but the op set was not exhaustively traced this stage.

## Limitations
- Interrupt timing/frequency (50.08 Hz) is taken from `docs/VECTOR_VERIFIED.md` (VERIFIED_BY_CODE
  for the emulators). Emulator Behaviour vs. original hardware: the *existence* and *vectoring* of
  RST 7 are hardware facts; exact per-frame cadence here is **Emulator Behavior**.
- The palette effect branch was not exercised at runtime (timer was 0 during the observed frames);
  its behaviour is from static disassembly (High confidence for the code path, effect data unknown).

## Recommended Next Steps (Stage 6)
- The interrupted PC (0x017C, `func_check_start_key`) confirms the title-screen SPACE-key poll is
  the entry to Stage 6: locate `lbl_title_key_poll` in `func_main_init`, then follow the post-SPACE
  path into level rendering and the main game loop.
- Trace `var_palette_timer`/`var_palette_ptr` writes to identify where timed palette effects are armed.
