# Vector-06C Library (`lib/`)

Hardware interaction for the Vector-06C (KR580VM80A / i8080), without z88dk clib.

Architecture:
- `sys/v06io.asm` — port write/read (self-modifying operand);
- `sys/startup.asm` — ROM entry, frame interrupt 50 Hz, `frame_count`, `frame_handler`, `irq_active`;
- `sys/v06pal.asm` — palette register write during vertical blank;
- `gfx/` — video memory, modes, clearing, text rendering;
- `snd/` — KR580VI53 timer, AY-3-8910 PSG, step sequencer (`sound.c`), bytecode synthesizer (`music.c`), noise drum engine (`drums.asm`), precomputed note tables (`notes.c`);
- `kbd/` — matrix keyboard polling via PIA ports (no interrupts);
- `unpack/` — RLE and LZ bitmap decompression into VRAM;
- `comps/` — UI components (controller, edit, textarea) — own header `comps/comps.h`.

All public prototypes are declared centrally in `v06.h`.

---

## COMMON — Hardware Port Map

| Port | Name | Purpose |
|------|------|---------|
| 0x00 | `V06_PIA_CW` | PIA control word |
| 0x01 | `V06_PIA_PC` | Port C: keyboard modifiers, Tape Out (bit 0) |
| 0x02 | `V06_PIA_PB` | Port B: border bits 0-3, mode bit 4 |
| 0x03 | `V06_PIA_PA` | Port A: row register (scroll) / keyboard row |
| 0x08 | `V06_VI53_CTRL` | VI53 control word |
| 0x09 | `V06_VI53_CH2` | VI53 channel 2 |
| 0x0A | `V06_VI53_CH1` | VI53 channel 1 |
| 0x0B | `V06_VI53_CH0` | VI53 channel 0 |
| 0x0C | `V06_PALETTE` | Palette byte write |
| 0x15 | `V06_AY_SEL` | AY-3-8910 register select (odd port) |
| 0x14 | `V06_AY_DAT` | AY-3-8910 data (even port) |

**Palette byte format:** `RRRGGGBB` (D0-D2 red, D3-D5 green, D6-D7 blue).
Use `V06_RGB(r, g, b)` macro.

**PIA control words:**
- `V06_CW_NORMAL` (0x88) — PA input, PB output (normal operation);
- `V06_CW_KEYSCAN` (0x8A) — keyboard read through port B.

**VRAM** at `0x8000`: 32 KB, 4 bit-planes at 8 KB each:
- 0x8000 — weight 8, 0xA000 — weight 4, 0xC000 — weight 2, 0xE000 — weight 1.

---

## GFX — Video Modes and Drawing

### Modes

| Constant | Resolution | Colors | Active planes |
|----------|-----------|--------|---------------|
| `GFX_MODE_256_16` (0) | 256x256 | 16 | All (0x0F) |
| `GFX_MODE_256_2` (1) | 256x256 | 2 | 0xE000 (mask 0x01) |
| `GFX_MODE_512_4` (2) | 512x256 | 4 | All (0x0F) |
| `GFX_MODE_512_2` (3) | 512x256 | 2 | 0xE000+0xA000 (mask 0x05) |

`gfx_set_mode()`: 256x256 modes are hardware default (no PIA touch); 512x256 modes configure PIA and scroll.

`gfx_clear(color)`: fills only active planes of current mode (via `gfx_fill_planes`).

`gfx_set_palette(colors)`: loads `num_colors` entries, auto-extends to 16 slots, masking unused planes.

### Palette Loading

`gfx_set_bmp_palette(pal)` — loads all 16 colors (format: `0bRRRGGGBB`).
The Vector palette is addressed "color under beam", so writes go through the border register during vertical blank interval (implemented in `v06pal.asm`).

`gfx_set_black_palette()` — all 16 colors black (hide screen / drawing process).

### Scroll

`gfx_set_scroll(row)` writes ONLY the variable `gfx_scroll_row` (deferred, safe from ISR). The keyboard poll outputs the value to port 0x03 at the next VSync (beam in blanking). Immediate `v06_out(V06_PIA_PA, ...)` from ISR is **forbidden**: `v06_out` contains `ei`.

### Text

**8x8 font** (standard 256x256): `gfx_put_char`, `gfx_print`.
Glyph set: `" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:()."` Cell is opaque: glyph pixels = color (0-15), background is cleared. `x` must be multiple of 8, `y` = top row of cell.

**16x8 font** (512x256 mode): `gfx_put_char_512`, `gfx_print_512` (pr512.asm).

**4x8 thin font** (512x256 mode): `gfx_print_512t` (pr512t.asm).

### Fill Functions

`gfx_fill_planes(mask, fill)` — fills VRAM planes with color 0-15. `mask` = which planes; `fill` = 0x00 or 0xFF.

`gfx_fill_stride(addr, val, step, count)` — writes `val` at `addr`, `addr+step`, `addr+2*step`, etc., `count` bytes total (fstride.asm).

### Frame Sync

`gfx_next_frame()` — waits for the next 50 Hz VBlank (HLT until interrupt, then checks `frame_count`).

---

## UNPACK — Bitmap Decompression

### RLE (256x256)

`gfx_rle_expand(src, x, y)` — unpacks RLE stream from `bmp2inc.py` into VRAM at (x, y).

Stream format: header = width in 8-pixel blocks + height (0 = 256), then pairs (count, byte), terminator = count 0. The rectangle contains planes ordered weight 8,4,2,1; within a plane, blocks left-to-right; within a block, rows top-to-bottom. An RLE run may cross block and plane boundaries.

Constraints: `x` must be multiple of 8; image must fit in 256x256. Area outside the image is unchanged (use `gfx_clear` for clean background).

### RLE (512x256)

`gfx_rle_expand_512(src)` — two-color 512x256 mode. Stream contains data for both planes: first 32 blocks → plane 1 (A000h), next 32 blocks → plane 0 (E000h). Header: (64, height).

### LZ (tile-based)

`gfx_lz_expand(src)` — LZ tile unpacker. Header: tpp(16), ntiles(16), h_div8(8); dictionary: ntiles * 8 bytes; four LZ streams; literal token = 9-bit dictionary index (2 bytes); reference token = 12-bit offset + 4-bit length. Tile #0 at xxxx:00FF, descending.

---

## SND — Audio Subsystem

### Notes (`notes.c`)

Precomputed pitch tables, indexed by absolute note number = `octave*12 + semitone`, range 0..94. Same indexing as `music.c` bytecode (`0x01..0x5F` → 0..94). Indices 0..11 are silence (VI53 divider would exceed 16 bit).

| Symbol | Meaning |
|--------|---------|
| `v06_div_tab[95]`        | VI53 dividers: `f = 1500000 / div` |
| `v06_ay_period_tab[95]`  | AY-3-8910 periods (12-bit), precomputed via `(div*887+6000)/12000` clamped to 1..4095 |

Mnemonic index macros (use inside `DIV_OF()` / `AY_PER()`):

```c
N_C(n), N_Cs(n), N_D(n), N_Ds(n), N_E(n), N_F(n), N_Fs(n),
N_G(n), N_Gs(n), N_A(n), N_As(n), N_B(n)
/* aliases: N_Db=N_Cs, N_Eb=N_Ds, N_Gb=N_Fs, N_Ab=N_Gs, N_Bb=N_As */

#define DIV_OF(note)   v06_div_tab[(note)]        /* for vi53_set_channel */
#define AY_PER(note)   v06_ay_period_tab[(note)]  /* for ay_set_tone_period */
```

Example — A4 (440 Hz concert pitch, index 57):

```c
vi53_set_channel(0,        DIV_OF(N_A(4)));   /* 3409 */
ay_set_tone_period(0,      AY_PER(N_A(4)));   /* 252  */
```

No 32-bit multiply/divide on either path. The old `ay_set_tone(ch, div_VI53)` helper (which did the conversion at runtime via `vi53_to_ay_period`) is removed — callers use `ay_set_tone_period()` with `AY_PER(N_x(oct))` directly.

Caveat: `DIV_OF(x)`/`AY_PER(x)` are runtime array lookups, so they cannot appear in `static const` struct initializers (SDCC requires a compile-time constant). Test ROMs that build a static `melody[]` keep the raw divider literal (e.g. `3409u` — the same value the table contains at that index).

Table variants are selected by the same guards as `music.c`:
- `MUSIC_AY_DRUMS_AY` — omit `v06_div_tab` (VI53 tone path unused in AY-only ROM);
- `MUSIC_VI53_DRUMS_TAPE` — omit `v06_ay_period_tab` (AY tone path unused in VI53-only ROM).

Linking: any ROM that references `v06_div_tab`/`v06_ay_period_tab` (i.e. uses `music.c` or `DIV_OF`/`AY_PER`) must also link `lib/snd/notes.c`.

---

### KR580VI53 (vi53.c)

Sole owner of VI53 port writes. Channel: 0/1/2 (ports 0x0B/0x0A/0x09).
Frequency = 1500000 / divisor (mode 3); divisor 0 = silence.

- `vi53_set_channel()` — 0 = writes only mode-3 control word, counter NOT loaded (music.c method);
- `vi53_set_channel_m0()` — 0 = mode 0 (OUT=0) + two zero bytes (sound.c method).

### AY-3-8910 (ay.c)

Sole owner of AY register writes from C. Ports: select = ODD 0x15, data = 0x14. ROM linking `ay.c` must also link `drums.asm` (contains mixer mirror `g_ay_r7`).

Three tone channels A/B/C: periods R0/R1, R2/R3, R4/R5; volumes R8/R9/R10. Envelope is ONE shared across all channels (R11/R12/R13).

#### Envelope Shapes (R13)

R13 bits interpretation in AY-3-8910:
- bit 3 = "first cycle down/up" AND "allow continuation"
- bit 2 = select start direction
- bit 1 = alternate cycle
- bit 0 = hold result after FIRST cycle

Due to this encoding, pairs (8,9), (10,11), (12,13), (14,15) give DIFFERENT observed behavior: odd (no continuation) = single pass with hold; even (continuation) = periodic shape.

| Code | Shape | Description |
|------|-------|-------------|
| 0-3 | `\_____` | Decay → hold 0 |
| 4-7 | `/^^^^^` | Linear rise → hold max |
| 8 | `\\\\` | Repeating saw-down |
| 9 | `\_____` | Single decay → hold 0 |
| 10 | `\/\/\/` | Repeating triangle (start down) |
| 11 | `\_____` | Single decay → hold 0 |
| 12 | `//////` | Repeating saw-up |
| 13 | `/^^^^^` | Rise → hold 15 (single) |
| 14 | `/\/\/\` | Repeating triangle (start up) |
| 15 | `/^^^^^` | Rise → hold 15 (single) |

Practical aliases: `AY_ENV_DECAY`, `AY_ENV_ATTACK`, `AY_ENV_TRIANGLE`, `AY_ENV_TRIANGLE_DOWN`.

#### ay_set_tone_period(ch, period)

Sets tone channel `ch` (0=A, 1=B, 2=C) from a ready AY period (12 bit, 0 = silence, volume to 0). Hardware level: period → R0..R5 + volume/envelope. Callers take the period from `v06_ay_period_tab[]` via `AY_PER(N_x(oct))` (`notes.c`), so no 32-bit math is involved. Applies envelope on attack if `ay_env_mode` is set for the channel.

> The old `ay_set_tone(ch, div_VI53)` wrapper (which did `div → period` via `vi53_to_ay_period()` and pulled in `l_long_mult`/`l_long_div_u` from the SDCC runtime) is removed. Use `ay_set_tone_period(ch, AY_PER(N_x(oct)))` instead.

#### ay_set_envelope(chan_mask, shape, period)

Define hardware envelope and attach channels: stores global shape/period and sets `ay_env_mode = chan_mask`. Applies on NEXT note attack (`ay_set_tone` programs R11/R12 period, R13 shape with generator restart, sets bit 4 in R8/R9/R10 of attached channels). Does NOT write registers immediately — otherwise envelope would attach to a currently sounding tone and produce a continuous signal.

`chan_mask`: bits `AY_CH_A/B/C` (0x07 = all three). Ignored if `chan_mask == 0` (after masking with 0x07).

**WARNING:** R11/R12/R13 are shared registers across all three AY channels: shape/period is one for the entire mask. Independent per-channel envelopes do not exist in AY-3-8910.

#### ay_set_fixed_volume(chan_mask, volume)

Return channels to fixed volume: clear envelope flag for channels in `chan_mask`, store `volume` (clamped 0..15). Applies on NEXT note attack. Does NOT write R8/R9/R10 immediately (would produce background tone). Volume = 0 → channel off. Ignored if `chan_mask == 0`.

### Melody Players

Two mutually exclusive players (both write to the same VI53 channels — use only one per ROM):

- **sound.c** — step sequencer (`sound_step_t` array); simple, no bytecode.
- **music.c** (`-DMUSIC_ONLY`) — bytecode synthesizer; 3 tone + drums from `.smp` samples.

#### sound.c

`sound_step_t`: duration (50 Hz ticks), ch1/ch2/ch3 (VI53 dividers, 0 = silence), noise (drum event: 0=none, 1=snare/tom, 2=kick).

`sound_set_tempo(num, den)`: steps per frame interrupt. 1/1 = nominal; num < den = slower; num > den = faster. Example: `sound_set_tempo(4, 5)` = 80% tempo.

`sound_set_loop(loop)`: 0 (default) = stop at end; 1 = repeat.

#### music.c — Bytecode Format

Data: `music_song_t` — four bytecode streams (3 tone + drums) and sample table. All durations pre-computed in 50 Hz frames; no time division in interrupt.

Bytecode (constants shared with `mus2inc.py`):

| Byte | Meaning |
|------|---------|
| 0x00 | End of stream |
| 0x01..0x5F | Note (abs number = byte-1; octave*12 + semitone; A4 = 57, div 3409) |
| 0x60 | Rest (current duration) |
| 0xE0..0xE7 | Duration L1..L128, grid PPQ=32; ticks = 128/L |
| 0xE8 | Loop start `[` |
| 0xE9 n | Loop end `]n`: repeat section n times total |
| 0xEA lo hi | JMP back (lo | hi<<8) bytes: infinite loop |

State commands (0xE0-0xE9) do not advance time. Default duration without commands = L4. Octave is compile-time state in mus2inc.py, no bytecode command (range 0xD0..0xD7 is free).

Tempo at runtime: `tempo_num/tempo_den` ticks per frame.

#### music_start_vi53 / music_start_ay

Explicit output device binding (no global "sound mode" selector). Start = reset transport + bind output. `music_use_vi53/ay` = rebind WITHOUT resetting position (during playback). Three melodic channels: 0→VI53 CH0/AY A, 1→CH1/AY B, 2→CH2/AY C. Drums follow the selected device: VI53 → Tape Out PC0 (LFSR), AY → noise channel C. The route is set internally via `drum_route_tape()/ay()`.

#### Diagnostics (music.c)

Counter variables for detecting desynchronization between tone channels and drums. Observation only, do not affect sound output.

---

## SND — Drums (drums.asm)

### Architecture: Three Independent Layers

1. **Drum Engine** — Galois LFSR (mask 0xB400, seed 0xACE1) + batch core. One LFSR step + one OUT to PIA port 0x00 (PC0) per iteration. This is the only Tape Out hardware path.

2. **Output Route** (`drum_route` byte):
   - 0 = Tape Out (`drum_route_tape`): software 1-bit LFSR noise on PIA1 Port C bit 0; R6 = shifts per tick, R10 = duty window for PC0 toggles;
   - 1 = AY Noise C (`drum_route_ay`): channel C in "tone off, noise on"; R6 = period, R10 = volume, mixer R7.
   
   Switching route mutes the currently sounding hit. Tone registers: R0-R5 never written, R8/R9 never written, R7 only noise/tone-C bits changed (via mirror `g_ay_r7`).

3. **Scheduler** (`tape_sched` byte) — how Tape Out generation relates to the frame interrupt:
   - **FRAME (0, default):** `drum_tick` performs `tape_shifts[R6]` steps per frame (or fixed threshold via `drum_tape_set_steps_per_tick(n)` when non-zero). Small n = minimal CPU load.
   - **MANUAL (1):** `drum_tick` does NOT touch PC0 or envelope. Tape Out changes only via explicit `drum_tape_step()` / `drum_tape_generate()` from main loop.
   - **MANUAL+ENV (2):** `drum_tick` walks sample envelope and duty-window timing but does NOT toggle PC0. Density set by main loop via `drum_tape_generate()`. `drum_tape_running()` reports per-frame gate. Enables max-frequency noise without losing envelope.

**Note on LFSR vs perceived sound:** LFSR steps/sec ≠ PC0 toggle count/sec ≠ perceived noise frequency. Each step writes PC0, but a toggle occurs only when the LFSR bit changes. Step rate ≠ noise frequency.

The AY noise path (route == 1) does NOT use any `drum_tape_*` function.

### Noise in sound_step_t

`noise` field is a momentary event: each `drum_*()` always restarts the sounding hit. No priority blocking. Instrument parameters = table at start of `drums.asm`.

### drum_sample_play(smp)

Plays a `.smp` sample (generated by `mus2inc.py`). Format: byte N = number of frames, then N pairs (R6, R10) — one frame per 50 Hz tick; first frame immediately. Null pointer or N=0 = silence. A sounding sample replaces a table-driven hit and vice versa; `drum_tick()` advances it.

---

## KBD — Keyboard

`kbd_scan()` — single matrix poll. Returns ASCII code of first pressed key (27=ESC, 13=ENTER) or 0 if nothing pressed.

`kbd_scan_now()` — matrix poll without waiting for a frame. Designed for calling at the very start of the frame interrupt: beam is at VSync blanking, row masks (port 03h = scroll) do not affect visible area. Paired with `kbd_read()`.

`kbd_read()` — decode the last matrix snapshot without re-polling ports.

`kbd_wait_key(key)` — blocking wait for a specific key press. 50 Hz sync, edge detector (reacts only to press transition).

---

## SYS — Interrupt and Frame Handling

`startup.asm` sets ROM entry at 0x0100, installs the frame interrupt vector (0x0038).

- `frame_count` — increments every 50 Hz from hardware interrupt;
- `frame_handler` — function pointer called each frame from ISR (0 = none). Assign: `frame_handler = music_tick;`;
- `irq_active` — 1 while hardware interrupt is executing, 0 outside. Main loop can detect ISR overlap.
