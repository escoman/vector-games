#!/usr/bin/env python3
"""
PUTUP title-screen melody -> Standard MIDI File converter.

Source of truth: roms/redesign/putup/reports/Stage11_music_spec.md
(all facts MCP-verified in Stage 11; no emulator needed).

Rules (spec sections in parentheses):
  - 3 voices, 96 steps each; streams at 0x3E29 + N*0x100 (spec §2)
  - track byte = note code; 0x00 = REST, else NOTE (spec §4)
  - MIDI note = code + 30                     (spec §5)
  - step = DURATION 6 VBlank ticks; tick = 1 frame ~19.97 ms (spec §6)
  - MIDI mapping: 1 step = 1/16 note, PPQ=192 => step = 48 ticks,
    quarter = 479200 us (BPM ~125.2)          (spec §6)
  - voice -> MIDI channel / GM program        (spec §9, artistic choice)

The three streams are read from src/putup.rom (org 0x0100) and cross-checked
against the decimal dumps embedded below from spec §10 — any mismatch aborts.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../putup/tools
ROM = HERE.parent / "src" / "putup.rom"
OUT = HERE.parent / "putup_title.mid"

ROM_ORG = 0x0100
TRACK_ADDR = [0x3E29, 0x3F29, 0x4029]           # spec §2
TRACK_LEN = 96                                  # spec §2 (LOOP=96)
MIDI_OFFSET = 30                                # spec §5: MIDI = code + 30

PPQ = 192
STEP_TICKS = PPQ // 4                           # 1 step = 1/16 note (spec §6)
US_PER_QUARTER = 479200                         # 6 * 19.97 ms * 4 (spec §6)
VELOCITY = 100                                  # uniform, no dynamics in ROM (spec §8)

VOICES = [
    # (name,           midi_channel, gm_program)         spec §9
    ("PUTUP ch0 lead", 0, 0),    # Acoustic Grand (rect. wave lead)
    ("PUTUP ch1 harm", 1, 4),    # Electric Piano
    ("PUTUP ch2 bass", 2, 38),   # Synth Bass 1
]

# Expected note-code dumps (decimal) — Stage11_music_spec.md §10, MCP-verified.
SPEC_TRACKS = [
    [48, 0, 43, 0, 0, 48, 47, 48, 50, 0, 43, 0, 0, 50, 48, 50, 52, 50, 52, 53,
     55, 0, 53, 52, 50, 0, 43, 0, 0, 50, 52, 55, 57, 57, 57, 57, 50, 50, 52, 53,
     55, 55, 55, 55, 48, 48, 50, 52, 53, 53, 53, 53, 47, 47, 48, 50, 52, 50, 52,
     53, 55, 55, 55, 55, 57, 57, 57, 57, 50, 50, 52, 53, 55, 55, 55, 55, 48, 48,
     50, 52, 53, 52, 50, 48, 48, 45, 47, 47, 48, 43, 40, 43, 36, 36, 0, 0],
    [36, 40, 43, 41, 40, 38, 36, 0, 31, 35, 38, 36, 35, 33, 31, 0, 36, 35, 36,
     38, 40, 41, 43, 40, 38, 0, 31, 0, 43, 42, 43, 0, 41, 43, 45, 48, 47, 45,
     43, 41, 40, 41, 43, 47, 45, 43, 41, 40, 38, 40, 41, 45, 43, 41, 40, 38, 40,
     36, 40, 43, 48, 47, 48, 0, 41, 43, 45, 48, 47, 45, 43, 41, 40, 41, 43, 47,
     45, 43, 41, 40, 38, 40, 41, 45, 43, 45, 47, 43, 48, 0, 43, 0, 36, 0, 48,
     47, 0, 0],
    [12, 0, 19, 0, 24, 0, 0, 0, 19, 0, 26, 0, 31, 0, 0, 0, 24, 0, 19, 0, 28, 0,
     24, 0, 23, 21, 19, 0, 0, 0, 31, 0, 17, 0, 21, 0, 19, 0, 31, 0, 19, 0, 16,
     0, 21, 0, 33, 0, 17, 0, 14, 0, 19, 0, 31, 0, 36, 0, 24, 0, 28, 31, 24, 0,
     17, 0, 21, 0, 19, 0, 31, 0, 16, 0, 19, 0, 17, 0, 33, 0, 17, 0, 21, 0, 19,
     0, 23, 0, 24, 0, 19, 0, 12, 0, 12, 0],
]


def read_tracks_from_rom():
    data = ROM.read_bytes()
    tracks = []
    for addr in TRACK_ADDR:
        off = addr - ROM_ORG
        stream = data[off:off + TRACK_LEN]
        if len(stream) != TRACK_LEN:
            sys.exit(f"ROM too short for stream @0x{addr:04X}")
        tracks.append(list(stream))
    return tracks


def validate(tracks):
    for i, (got, exp) in enumerate(zip(tracks, SPEC_TRACKS)):
        if got != exp:
            for j, (g, e) in enumerate(zip(got, exp)):
                if g != e:
                    sys.exit(f"track_0{i+1}[{j}] = {g}, spec says {e} — aborting")
        if any(b & 0x80 for b in got):
            sys.exit(f"track_0{i+1}: code with bit7 set — extended branch "
                     f"not exercised by title melody per spec §4, aborting")


# --- minimal SMF writer (format 1) ---

def vlq(value):
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def meta(dt, payload):
    return vlq(0) + bytes([0xFF, dt, len(payload)]) + payload


def chunk(kind, body):
    return kind + len(body).to_bytes(4, "big") + body


def track_text(name):
    return meta(0x03, name.encode("ascii"))


def voice_track(steps, name, channel, program):
    # events: (absolute tick, order, bytes) — order 0=note_off before note_on
    events = [(0, -1, bytes([0xC0 | channel, program]))]   # program change
    for step, code in enumerate(steps):
        if code:
            note = code + MIDI_OFFSET
            on, off = step * STEP_TICKS, (step + 1) * STEP_TICKS
            events.append((on, 1, bytes([0x90 | channel, note, VELOCITY])))
            events.append((off, 0, bytes([0x80 | channel, note, 0])))
    events.sort(key=lambda e: (e[0], e[1]))

    body, pos = b"", 0
    for tick, _, msg in events:
        body += vlq(tick - pos) + msg
        pos = tick
    body += vlq(0) + bytes([0xFF, 0x2F, 0x00])              # end of track
    return chunk(b"MTrk", track_text(name) + body)


def main():
    tracks = read_tracks_from_rom()
    validate(tracks)

    header_body = b"\x00\x01" + b"\x00\x04" + (PPQ).to_bytes(2, "big")
    tempo = US_PER_QUARTER.to_bytes(3, "big")
    header_track = (track_text("PUTUP Vector-06C title")
                    + meta(0x51, tempo)
                    + meta(0x58, bytes([4, 2, 24, 8]))      # time sig 4/4
                    + vlq(0) + bytes([0xFF, 0x2F, 0x00]))

    smf = chunk(b"MThd", header_body)
    smf += chunk(b"MTrk", header_track)
    for steps, (name, ch, prog) in zip(tracks, VOICES):
        smf += voice_track(steps, name, ch, prog)

    OUT.write_bytes(smf)
    total_steps = len(tracks[0])
    dur_s = total_steps * 6 * 0.01997
    print(f"OK: {OUT} ({len(smf)} bytes)")
    print(f"    3 tracks x {total_steps} steps, {STEP_TICKS} tick/step @ {PPQ} PPQ")
    print(f"    tempo {US_PER_QUARTER} us/quarter (~{6e7/US_PER_QUARTER:.1f} BPM), "
          f"loop ~{dur_s:.2f} s, MIDI = code + {MIDI_OFFSET}")


if __name__ == "__main__":
    main()
