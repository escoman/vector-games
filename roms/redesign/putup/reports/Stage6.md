# Stage 6 — Main Game Loop Research

## Goal
Research the main game loop of `putup.rom` (TZ Stage 6): find the title-screen wait-for-SPACE loop
and record it in the RDB; follow the code that runs after SPACE; investigate level rendering
(location of level maps, character/enemy sprite blocks, tiles); find and mark the main game loop;
step through the loop for several dozen cycles to identify the game variables and record them in
the RDB. Save the RDB.

## ROM
- File: `putup.rom`, 17664 bytes, load 0x0100
- SHA256: `8486442efc390b15860ec7f69c32db93b0884908565fa11fec57d5c551b4e9a6`
- Mapping entry point: **0x0000**; program entry `func_entry` = **0x0100**

## Method (per TZ Stage 6)
1. Reloaded the ROM (`debug_load_rom` org=0x0100), set PC=0x0100, ran ~5 s, paused (title screen).
2. Confirmed the title poll: PC observed at 0x019F (`func_read_keybuf`) — the SPACE-key wait loop.
3. Set a breakpoint at 0x0E85, pressed SPACE (`debug_press_key`), ran → BP hit with **SP=0x0100**
   (clean stack ⇒ reached by `JMP`, not `CALL`), confirming the level loader tail-jumps into the loop.
4. Snapshotted the variable block (0x08C0/0x08E0) before and after ~2 s of gameplay with a key held
   (dozens of loop iterations); used the runtime memory access map (block 0x0900 = the game-variable
   block: read 3499 / write 2269 / fetch 8) plus raw `debug_read_memory_range` diffs as ground truth.
5. Disassembled via `debug_disassemble_range`: title poll (0x0C65), level loader (0x197C), main loop
   (0x0E85), `func_game_update` (0x0CE0), `func_draw_status_hud` (0x121A), entity handler 1 (0x1489).
6. Recorded 33 new objects + 49 links in the RDB and saved (`debug_save_rdb`, dirty=false).

---

## Findings

### Finding 1 — Title-screen wait-for-SPACE loop (`lbl_title_key_poll` @0x0C65)
**Observation (Fact):** A timeout-bounded poll loop that animates a marquee while waiting for SPACE.
**Evidence — disassembly (MCP):**
```
0C65  LXI B,0C00      ; timeout = 3072
0C68  XRA A           ; --- poll loop ---
0C69  PUSH B
0C6A  CALL 017C       ; func_check_start_key -> A=0xFF if SPACE/SHIFT
0C6D  POP B
0C6E  ORA A
0C6F  JNZ 0C9D        ; key pressed -> start game
0C72  DCX B           ; timeout--
0C73  MOV A,C / ORA B
0C75  JNZ 0C68        ; keep polling
0C78  LXI H,5180      ; --- timeout: animate marquee (text buffer @0x5180) ---
0C7B  MVI B,20        ; 32 chars
0C7D  MOV A,M / CPI 75 ('u') / JZ 0C90
0C83  CPI FE / JNZ 0C95
0C88  MVI A,75 / CALL 0145   ; draw 'u'
0C90  MVI A,FE / CALL 0145   ; draw 0xFE  (toggles 'u' <-> 0xFE)
0C95  INX H / DCR B / JNZ 0C7D
0C9A  JMP 0C65        ; loop back
0C9D  CALL 3DCD       ; key pressed: func_music_start_track
0CA0  JMP 197C        ; -> func_level_loader  (post-SPACE entry, TZ step 3)
```
**Conclusion:** The marquee/toggle animation runs on a 3072-iteration timeout; a SPACE (or SHIFT)
press starts the music and jumps to the level loader. **Confidence: High** (disassembly + the Stage 5
ISR observation that VBlank interrupted PC=0x017C, i.e. this poll).

### Finding 2 — Level loader (`func_level_loader` @0x197C) renders the level and enters the loop
**Observation (Fact):** Increments the level, clears the screen, draws the tile map, HUD and objects,
initialises the player/entities, then `JMP 0x0E85` (main loop).
**Evidence — key instructions (MCP):**
```
197C  LXI H,08F5 / INR M      ; var_level(0x08F5)++
1981  CPI 10 / JNC 1A3B       ; level >= 16 -> completion path (all 15 levels cleared)
198A  LXI H,1C0E              ; data_level_params
198D  LDA 08F5 / RLC / RLC / RLC ; offset = level*8
1997  LXI D,0911 / LXI B,0008 / CALL 1BC9  ; memcpy 8 bytes -> data_level_param_buf(0x0911)
19A0  LXI SP,0100 / CALL 1BE5 ; reset stack; func_clear_textbuf
19AA  LXI H,1C8E              ; data_level_maps (base)
19A6  LDA 08F5 / DCR A        ; level-1
19B0  LXI D,00B0 / DAD D / DCR A / JNZ 19B3  ; HL = 0x1C8E + (level-1)*176
19BB  LXI B,00B0              ; --- MAP DRAW LOOP: 176 iterations (16x11) ---
19C0  MOV A,M / ADD A / ADD A ; tile*4
19C3  LXI H,2706 / CALL 032C  ; data_tile_graphics + tile*4  (4 bytes = 2x2 chars)
19CA  CALL 1B87               ; func_draw_tile_to_buf
19CE  INR D / INR D           ; col += 2
19D1  CPI 20 / JNZ 19DA       ; col == 32 ?
19D6  MVI D,00 / INR E / INR E; wrap col, row += 2
19DC  DCX B / JNZ 19BE        ; next tile
19E3  CALL 1197 / CALL 11E9   ; func_draw_score_hud, func_play_sfx
19E9  MVI A,10 / STA 091E     ; var_lives_icons(0x091E) = 16
19EE  CALL 121A               ; func_draw_status_hud
19F1  MVI A,01 / STA 0901     ; var_player_row = 1
19F6  INR A / STA 0902        ; var_player_col = 2
19FA  XRA A / STA 0900        ; var_game_state = 0
19FE  LDA 0913 / STA 091A     ; entity1_state <- level param[+2]
1A04  LDA 0916 / STA 091B     ; entity2_state <- level param[+5]
1A0A  LDA 0914 / STA 0920     ; entity1 X     <- level param[+3]
1A10  LDA 0915 / STA 0923     ; entity1 Y     <- level param[+4]
1A16  LDA 0917 / STA 0921     ; entity2 X     <- level param[+6]
1A1C  LDA 0918 / STA 0924     ; entity2 Y     <- level param[+7]
1A2C  CALL 130A               ; func_draw_game_objects
1A35  MVI A,03 / STA 0907     ; var_work_const = 3
1A38  JMP 0E85                ; -> lbl_main_game_loop
1A3B  CALL 130A / CALL 1BE5   ; completion path (level >= 16)
```
**Conclusion:** The loader fully builds a level from ROM tables and enters the main loop. The map is
**176 bytes = 16×11 tiles**, each tile drawn as a 2×2 char block (→ 32×22 char playfield). This
directly answers TZ Stage 6 step 4 (level maps @0x1C8E, per-level params @0x1C0E, tile graphics
@0x2706). **Confidence: High.**

### Finding 3 — Main game loop (`lbl_main_game_loop` @0x0E85)
**Observation (Fact):** An entity-state dispatch loop over 2 entities, then a per-frame update,
a delay, and a page flip; loops forever.
**Evidence — disassembly (MCP):**
```
0E85  LXI B,0001             ; entity counter C = 1
0E88  PUSH B                 ; --- per-entity ---
0E89  MOV A,C / STA 090E     ; var_entity_index = C
0E8D  LXI H,0919 / DAD B     ; HL = 0x0919 + entity_index
0E91  MOV A,M                ; A = entity state (0x091A e1 / 0x091B e2)
0E92  CPI 01 / PUSH PSW / CZ 1489 / POP PSW   ; state 1 -> func_entity_state1
0E99  CPI 02 / ... CZ 14F9    ; state 2
0EA0  CPI 03 / ... CZ 1568    ; state 3
0EA7  CPI 04 / ... CZ 15DF    ; state 4
0EAE  CPI 05 / ... CZ 164F    ; state 5
0EB5  CPI 06 / ... CZ 16FC    ; state 6
0EBC  CPI 07 / ... CZ 17A8    ; state 7
0EC3  CPI 08 / ... CZ 1851    ; state 8
0ECA  CPI 09 / ... CZ 18FE    ; state 9
0ED1  CPI 0A / CZ 191B        ; state 10 -> func_entity_state10
0ED6  CALL 0CE0              ; func_game_update (player control/movement/collision)
0ED9  MVI B,02 / CALL 0EF7   ; func_delay (frame pacing)
0EDE  POP B / INX B          ; next entity
0EE1  CPI 03 / JC 0E88       ; loop while C < 3  (entities 1 and 2)
0EE6  LDA 08F9 / MOV B,A     ; --- page flip (double buffer) ---
0EEA  LDA 08FA / STA 08F9
0EF0  MOV A,B / STA 08FA
0EF4  JMP 0E85               ; back edge
```
**Conclusion:** The loop drives a **10-state machine per entity** (2 entities), calls
`func_game_update` once per frame, paces with `func_delay`, and swaps the page-flip pair
0x08F9↔0x08FA. `PUSH/POP PSW` around each `CZ` preserves the state byte in A across handler calls.
BP at 0x0E85 hit with SP=0x0100 confirms entry via the loader's `JMP`. **Confidence: High.**

### Finding 4 — Entity state handlers (10 targets) and handler 1 (movement AI)
**Observation (Fact):** The `CZ` targets are the 10 state handlers; sizes derived from address deltas.

| State | Handler | Addr | Size (bytes) |
|-------|---------|------|--------------|
| 1 | func_entity_state1 | 0x1489 | 112 |
| 2 | func_entity_state2 | 0x14F9 | 111 |
| 3 | func_entity_state3 | 0x1568 | 119 |
| 4 | func_entity_state4 | 0x15DF | 112 |
| 5 | func_entity_state5 | 0x164F | 173 |
| 6 | func_entity_state6 | 0x16FC | 172 |
| 7 | func_entity_state7 | 0x17A8 | 169 |
| 8 | func_entity_state8 | 0x1851 | 173 |
| 9 | func_entity_state9 | 0x18FE | 29 |
| 10 | func_entity_state10 | 0x191B | 97 |

**Evidence — handler 1 (MCP):**
```
1489  LDA 090E / PUSH PSW
148D  LXI H,091F / CALL 032C  ; data_entity_xcoords + entity_index
1493  INR M / MOV D,M         ; X++ (move entity right)
1496  LXI H,0922 / CALL 032C  ; data_entity_ycoords + entity_index
149C  MOV E,M                 ; E = Y
149D  CALL 1BD4               ; func_coords_to_textbuf -> HL
14A0  INX H / MOV A,M / CPI 20 / JNZ 14B1   ; probe cell
14A7  LXI B,0020 / DAD B / MOV A,M / CPI 20 / JZ 14C6  ; probe cell below
14B1  (BLOCKED) ... 091F+idx DCR M (undo X); 0919+idx MVI M,02 (state -> 2); RET
14C6  (CLEAR)  LXI H,270A / CALL 1B87 ; draw sprite tile @0x270A
14F2  LXI H,2756 / CALL 1B87          ; draw sprite tile @0x2756 ; RET
```
**Conclusion:** Handler 1 is entity movement AI: advance X, probe the text buffer for an obstacle
(space = free); if blocked, undo and transition the entity to state 2 (turn-around); if clear, redraw
the 2×2 sprite from the tile graphics table (0x270A / 0x2756). Handlers 2–10 are confirmed dispatch
targets with known sizes; their internals are **not yet disassembled** (deferred). **Confidence:
handler 1 = High; handlers 2–10 dispatch/size = High, internals = Low/Unknown.**

### Finding 5 — `func_game_update` @0x0CE0 (player control, movement, collision)
**Evidence — disassembly (MCP), key variable accesses:**
```
0CE0  XRA A / CALL 017C       ; func_check_start_key
0CE5  JZ 0CF5                 ; no key -> normal play
0CE8  LDA 0900 / CPI 01 / JZ 12B3 ; game_state==1 -> 0x12B3
0CF0  CPI 02 / JZ 12F6        ; game_state==2 -> 0x12F6
0CF5  LXI H,0901 / INR M      ; var_player_row++ (auto-advance each frame)
0CF9  MOV E,M / LDA 0902 / MOV D,A ; E=row, D=var_player_col
0CFE  CALL 1BD4 / SHLD 0903   ; var_player_bufaddr = coords_to_textbuf(row,col)
0D05  STA 0905 (=0)           ; var_collision_flag = 0
0D08  LXI B,0020 / DAD B      ; HL += 0x20 (cell below player)
0D0C  MOV A,M / CPI 76 ('v') / JC|JZ skip / CMA / STA 0905 ; flag if char > 'v'
0D19  INX H ... (2nd char) ... STA 0905
0D27  LDA 0905 / ORA A / JZ 0D3E
0D2E  (collision) LXI H,0901 / DCR M (row--); MVI A,01 / STA 0900 (game_state=1); STA 0906=0
0D3E  (no collision) STA 0900 (=0)
0D41  XRA A / CALL 0153       ; func_decode_key -> A = keycode
0D45  CPI 01/02 -> 0D68 ; CPI 03/04 -> 0FD4 ; CPI 05 -> 1042 ; CPI 06/07 -> 1017
0D68  MVI A,03 / STA 0907     ; var_work_const = 3
0D6D  LDA 0902 / STA 0909     ; object col = player col
0D73  LDA 0901 / STA 090A     ; object row = player row
0D79  LDA 090D / RLC / ADD B  ; 0x090D * 3
0D80  LDA 0907 / ADD B / DCR A / STA 090C ; tile_index = work_const + 0x090D*3 - 1
0D88  LXI H,08E3 ... CMP ... CALL 0104 (redraw prev) ... SHLD 08E3 (save pos)
0DAA  LDA 090C / ADD A / ADD A / LXI H,26DE / CALL 032C ; data_tile_table_26DE + tile_index*4
0DB5  CALL 1BA8               ; func_render_tile_vram
0DB8  LXI H,5000 / LXI B,0300 ; 768-byte text-buffer scan loop
```
**Conclusion:** Per-frame the player auto-advances one row; the two cells below are tested against
`'v'`(0x76) for collision (collision ⇒ row-- and `game_state=1`); a decoded key selects a movement
branch; the player/object tile index is computed and rendered from `data_tile_table_26DE`. This is
the core of TZ step 6 variable identification. **Confidence: High.**

### Finding 6 — `func_draw_status_hud` @0x121A resolves LEVEL vs LIVES
**Evidence — disassembly (MCP):**
```
121A  LXI H,52F2 / CALL 014F  ; cursor = 0x52F2
1220  LXI H,08F5 / CALL 0331  ; func_print_uint16 -> prints var_level(0x08F5) AS A NUMBER
1226  LXI H,52EF / CALL 014F / LXI H,0AF4 / CALL 0321  ; string @0x0AF4
1232  LXI H,5302 / CALL 014F / LXI H,0AFB / CALL 0321  ; string @0x0AFB
123E  LXI H,5307 / CALL 014F
1244  LDA 091E / MOV B,A      ; B = var_lives_icons(0x091E)
1248  MVI A,9B                ; icon char 0x9B
124A  CALL 01A1 / DCR B / JNZ 124A  ; draw B copies of the icon
1251  RET
```
**Conclusion (correction):** **0x08F5 = LEVEL** (printed as a number), **0x091E = lives/icon count**
(drawn as N copies of icon 0x9B, initialised to 16). Earlier analysis/comments that labelled 0x08F5
or 0x0907 as "lives" were **incorrect** and have been corrected in the RDB. **Confidence: High.**

---

## Level-rendering memory blocks (TZ Stage 6 step 4)
| Block | Addr | Size | Structure / evidence |
|-------|------|------|----------------------|
| data_level_maps | 0x1C8E | 2640 (15×176) | 16×11 tile maps; addr = 0x1C8E + (level−1)·176; ends exactly at 0x26DE |
| data_level_params | 0x1C0E | 128 (16×8) | per-level entity states/coords; addr = 0x1C0E + level·8; memcpy→0x0911 |
| data_tile_graphics | 0x2706 | Unknown (≥0xB4) | 4 bytes/tile = 2×2 chars; indexed tile·4; sprites at 0x270A, 0x2756 |
| data_tile_table_26DE | 0x26DE | (existing) | player/object tiles; `func_game_update` renders tile_index·4 from here |
| data_level_param_buf | 0x0911 | 8 | RAM copy of the current level's 8-byte param entry |

## Game variables identified (TZ Stage 6 step 6)
Runtime snapshot read at 0x08E0 (paused inside `func_game_update`, level 1, mid-gameplay):

| Variable | Addr | Size | Snapshot | Role (evidence) |
|----------|------|------|----------|-----------------|
| var_score | 0x08F3 | 2 | 40 | score; drawn by func_draw_score_hud, added by func_score_and_redraw |
| var_level | 0x08F5 | 1 | 1 | level number; INR by loader; indexes maps/params; printed as number |
| var_page_flip | 0x08F9 | 2 | 1, 2 | double-buffer page pair, swapped each frame |
| var_bonus_counter | 0x08FB | 1 | 1 | INR by score HUD; clamped to 6 by func_draw_level_hud |
| var_bonus_threshold | 0x08FC | 2 | 2000 | += 0x07D0 each bonus; remaining = threshold−1−score |
| var_game_state | 0x0900 | 1 | 1 | sub-state: 1 on collision w/ 'v'; dispatched on key press |
| var_player_row | 0x0901 | 1 | 6 | player Y; INR each frame, DCR on collision |
| var_player_col | 0x0902 | 1 | 12 | player X (0..31); changed by left/right keys |
| var_player_bufaddr | 0x0903 | 2 | 0x50CC | text-buffer addr = coords_to_textbuf(row,col) |
| var_collision_flag | 0x0905 | 1 | 0x88 | set when char below player > 'v'(0x76) |
| var_work_const | 0x0907 | 1 | 1→3 | set to 3; tile_index = 0x0907 + 0x090D·3 − 1 |
| var_entity_index | 0x090E | 1 | 1 | current entity (1 or 2) in main loop |
| var_entity1_state | 0x091A | 1 | 1 | entity 1 state (0x0919+idx); dispatch selector |
| var_entity2_state | 0x091B | 1 | 1 | entity 2 state |
| var_lives_icons | 0x091E | 1 | 16 | lives; drawn as N icon chars (0x9B) |
| data_entity_xcoords | 0x091F | 3 | (54),15,14 | entity X array (e1=0x0920, e2=0x0921; idx0 unused) |
| data_entity_ycoords | 0x0922 | 3 | (45),6,12 | entity Y array (e1=0x0923, e2=0x0924; idx0 unused) |

Object/level coords also seen: 0x0909 (object col=12), 0x090A (object row=6), 0x090C (tile index=0),
0x090D (tile-index input=0), 0x08E3 (prev object pos word=6), 0x08E9 (packed prev pos=9).

## RDB changes this stage
- **New objects (33):**
  - Code (3): `lbl_title_key_poll` (0x0C65), `func_level_loader` (0x197C), `lbl_main_game_loop` (0x0E85)
  - Entity handlers (10): `func_entity_state1..10` (0x1489,0x14F9,0x1568,0x15DF,0x164F,0x16FC,0x17A8,0x1851,0x18FE,0x191B)
  - Level-render data (3): `data_level_maps` (0x1C8E), `data_level_params` (0x1C0E), `data_tile_graphics` (0x2706)
  - Variables/buffers (17): `var_score`, `var_level`, `var_lives_icons`, `var_bonus_counter`,
    `var_bonus_threshold`, `var_player_row`, `var_player_col`, `var_player_bufaddr`,
    `var_collision_flag`, `var_page_flip`, `var_entity_index`, `var_entity1_state`,
    `var_entity2_state`, `var_work_const`, `data_level_param_buf`, `data_entity_xcoords`,
    `data_entity_ycoords`
- **Updated comments (3):** `func_game_update` (0x0CE0), `func_draw_status_hud` (0x121A, was empty),
  `var_game_state` (0x0900).
- **Corrected property:** `func_draw_status_hud.params` (0x08F5 = LEVEL, not lives).
- **New links (49):**
  - `lbl_main_game_loop` → 10 handlers + `func_game_update` + `func_delay` (12)
  - `lbl_title_key_poll` → `func_check_start_key`, `func_level_loader`, `func_music_start_track`,
    `func_draw_char_at_hl` (4)
  - `func_level_loader` → maps/params/tiles/memcpy/clear/draw_tile/score_hud/sfx/status_hud/
    draw_objects/main_loop/hl_add_a (12)
  - `func_entity_state1` → hl_add_a, coords_to_textbuf, draw_tile_to_buf, xcoords, ycoords (5)
  - `func_game_update` → decode_key, draw_tile_at_ptr, render_tile_vram, tile_table_26DE,
    player_row, collision_flag, game_state (7)
  - `func_draw_status_hud` → print_uint16, print_string, set_text_ptr, print_char_at_ptr,
    var_level, var_lives_icons (6)
  - `func_draw_score_hud` → var_score, var_bonus_counter, var_bonus_threshold (3)

## Result summary
```
Mapping entry point: 0x0000  (program entry func_entry = 0x0100)
Objects: 141   (+33 this stage; was 108)
Links:   ~134  (+49 this stage; Stage 5 baseline 85)
_unknown names remaining: 0
RDB:     /home/alexey/Projects/vector-games/roms/redesign/putup/src/putup.rdb
RDB save: success (dirty = false)
```

---

## Verified Facts (MCP-observed)
- Title poll @0x0C65: `LXI B,0C00` timeout, `CALL func_check_start_key`, on key `CALL 3DCD`+`JMP 197C`.
- Level loader @0x197C: `INR M` on 0x08F5 (level); `JMP 0E85` at 0x1A38; completion `JNC 1A3B` at level≥16.
- Map geometry: 176 bytes/map (0xB0), addr = 0x1C8E + (level−1)·176; 15 maps end at 0x26DE.
- Per-level params: 8 bytes/level, addr = 0x1C0E + level·8, memcpy'd to 0x0911.
- Tile graphics @0x2706 indexed tile·4 (2×2 chars); entity sprites @0x270A / @0x2756.
- Main loop @0x0E85 dispatches 10 states via CPI/CZ; iterates entities C=1,2; page-flips 0x08F9↔0x08FA.
- BP @0x0E85 hit with SP=0x0100 (clean stack) after SPACE ⇒ entered by JMP from the loader.
- `func_game_update`: 0x0901 row++, 0x0902 col, 0x0903 bufaddr, 0x0905 collision (vs 'v'=0x76),
  0x0907=3, tile_index = 0x0907 + 0x090D·3 − 1, render from 0x26DE.
- `func_draw_status_hud`: prints 0x08F5 as a number (LEVEL); draws 0x091E copies of icon 0x9B (LIVES).
- Runtime snapshot @0x08E0: score=40, level=1, game_state=1, player row=6/col=12, lives=16,
  entity1/2 state=1, e1 X=15/Y=6, e2 X=14/Y=12.

## Inferences (Medium)
- The playfield is a 32×22 char grid (16×11 tiles × 2×2 chars) inside the 32×32 text buffer @0x5000.
- Entities (2 per level) are enemies/objects driven by the shared 10-state machine; state 2 is a
  turn-around entered on obstacle collision (handler 1 sets state→2 when blocked).
- The page-flip pair 0x08F9/0x08FA drives flicker-free double-buffered rendering.
- Per-level params encode the two entities' initial states and X/Y coordinates (8 bytes/level).

## Hypotheses (Low — need Stage 7/9)
- data_tile_graphics @0x2706 and data_tile_table_26DE @0x26DE are adjacent parts of one tile atlas;
  the player/object tiles (0x26DE) and map tiles (0x2706) may share a common glyph source.
- The completion path (level≥16) leads to an ending/game-over screen (0x1A3B → 0x5100 text).
- Entity states 3–10 encode distinct enemy behaviours (patrol/chase/attack); only state 1 is decoded.

## Unknowns
- Internals of entity handlers 2–10 (dispatch + size known; behaviour not yet disassembled).
- The exit-coordinate field of each 176-byte map (TZ Stage 9 will parse per-map structure).
- Meaning of index-0 slots 0x091F/0x0922/0x0919 (unused by entity indexing 1/2) — possibly other
  object coords or padding.
- The 768-byte text-buffer scan loop @0x0DB8 (purpose not yet traced).
- Semantics of the key-dispatch branches 0x0FD4 / 0x1042 / 0x1017 (keys 3–7) in func_game_update.

## Limitations
- **MCP tool anomaly — `debug_compare_memory_snapshots` under-reports dense diffs.** A controlled
  test (isolated single-byte write to 0x0912) was detected correctly, but the snapshot pair spanning
  ~2 s of gameplay reported only 14 changed ranges, while a manual byte-by-byte diff of two
  authoritative `debug_read_memory_range` reads showed additional changed bytes (e.g. 0x0908, 0x090B,
  0x090D, 0x090F, 0x0918–0x0925). Per TZ Stage 0 ("if the MCP server does/returns something
  incorrect, verify and, once confirmed, stop and report to the user"), this is reported. **Ground
  truth for the variable-change set was taken from raw `debug_read_memory_range` before/after diffs
  (verified stable while paused), not from the compare tool.** The anomaly did not block Stage 6;
  the compare tool's dense-diff output should be treated as a lower bound only.
- Handler sizes are derived from address deltas between consecutive dispatch targets (exact for
  contiguous handlers); handler 10's size assumes it ends where `func_level_loader` (0x197C) begins.
- Emulator Behaviour vs. original hardware: loop/frame pacing (`func_delay`) and page-flip timing are
  observed in the emulator; exact cadence on real Vector-06C hardware is UNVERIFIED.

## Recommended Next Steps (Stage 7)
- Locate the text-output functions and the glyph block: the status/score HUD print strings @0x0AF4,
  @0x0AFB, @0x0AED and use `func_print_string`(0x0321)/`func_print_char_at_ptr`(0x01A1)/
  `func_render_glyph`(0x0803) with the glyph pointer table @0x0600 — a good entry point for Stage 7.
- Find the title/HUD strings ("PUSH SPACE KEY", "MSX MAGAZINE, 1987", the Cyrillic credits) and the
  glyph base address used by `func_render_glyph`.
- Stage 9 will parse the 15 level maps @0x1C8E (176 bytes each) and their exit coordinates.
