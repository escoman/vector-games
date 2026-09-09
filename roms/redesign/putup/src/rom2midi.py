#!/usr/bin/env python3
"""
ROM music → MIDI converter for putup.rom (v4 — based on frequency table analysis)

Music data (3 voices × 96 notes) from ROM:
  Voice 1 (melody):  ROM 0x3E29, notes 36-57
  Voice 2 (harmony): ROM 0x3F29, notes 31-48
  Voice 3 (bass):    ROM 0x4029, notes 12-36

Frequency table at ROM 0x421A: 64 entries, chromatic scale from G4.
  Entry i → divisor = table[i*2] | (table[i*2+1] << 8)
  freq = 1500000 / divisor
  Entry 0 = G4 ≈ 392 Hz, entry 12 = G3, etc.

Note mapping: note_value → table_entry = note_value - 36
  → MIDI = note_value + 31  (36 → MIDI 67 = G4)
"""
import struct
import math

# ── Frequency table from ROM 0x421A (64 entries, 16-bit LE) ──────────
FREQ_TABLE_RAW = [
    0x0EEE, 0x0E18, 0x0D4D, 0x0C8E, 0x0BDA, 0x0B2F, 0x0A8F, 0x09F7,
    0x0968, 0x08E1, 0x0861, 0x07E9, 0x0777, 0x070C, 0x06A7, 0x0647,
    0x05ED, 0x0598, 0x0548, 0x04FC, 0x04B4, 0x0471, 0x0431, 0x03F5,
    0x03BC, 0x0386, 0x0353, 0x0323, 0x02F4, 0x02C7, 0x029C, 0x0274,
    0x024E, 0x022A, 0x0208, 0x01E7, 0x01C8, 0x01AB, 0x018F, 0x0175,
    0x015C, 0x0145, 0x012F, 0x011B, 0x0108, 0x00F6, 0x00E5, 0x00D5,
    0x00C6, 0x00B8, 0x00AB, 0x009F, 0x0093, 0x0088, 0x007E, 0x0075,
    0x006D, 0x0065, 0x005E, 0x0058, 0x0052, 0x004D, 0x0048, 0x0043,
]

def divisor_to_midi_note(divisor):
    """Convert VI53 divisor to nearest MIDI note number."""
    if divisor <= 0:
        return -1
    freq = 1_500_000.0 / divisor
    if freq <= 0:
        return -1
    midi = 69 + 12 * math.log2(freq / 440.0)
    return max(0, min(127, round(midi)))

# Build mapping: ROM note value → MIDI note
NOTE_OFFSET = 31  # ROM 36 → MIDI 67 (G4)

# ── Read note data from extracted binary ──────────────────────────────
with open("assets/music_data.bin", "rb") as f:
    raw = f.read()

# The 1008 bytes span ROM 0x3E29..0x4218 but with page gaps.
# We need to reconstruct the actual note data from the pages.
# Page layout in music_data.bin (extracted from ROM 0x3E29-0x4218):
#   ROM 0x3E29-0x3EFF → raw[0x000:0x0D7] (215 bytes, rest of page 0x3E00)
#   ROM 0x3F00-0x3FFF → raw[0x0D7:0x1D7] (256 bytes, page 0x3F00)
#   ROM 0x4000-0x40FF → raw[0x1D7:0x2D7] (256 bytes, page 0x4000)
#   ROM 0x4100-0x4218 → raw[0x2D7:0x3F7] (305 bytes, page 0x4100)

# Voice 1 notes at ROM 0x3E29 = raw[0x000], 96 bytes
voice1 = raw[0x000:0x060]

# Voice 2 notes at ROM 0x3F29.
# ROM 0x3F00 = raw[0x0D7] (since page 0x3E00 has 0xD7 bytes from 0x3E29 to 0x3EFF)
# ROM 0x3F29 = raw[0x0D7 + 0x29] = raw[0x100]
voice2 = raw[0x100:0x160]

# Voice 3 notes at ROM 0x4029.
# ROM 0x4000 = raw[0x1D7]
# ROM 0x4029 = raw[0x1D7 + 0x29] = raw[0x200]
voice3 = raw[0x200:0x260]

# Verify data matches what we read from emulator
print("Voice data verification:")
for name, data in [("Voice1", voice1), ("Voice2", voice2), ("Voice3", voice3)]:
    nz = sum(1 for b in data if b > 0)
    vals = [b for b in data if b > 0]
    lo, hi = (min(vals), max(vals)) if vals else (0, 0)
    print(f"  {name}: {len(data)} steps, {nz} notes, range {lo}-{hi}")

# ── Compute MIDI notes using frequency table ─────────────────────────
print("\nFrequency table verification (first 12 entries):")
for i in range(12):
    d = FREQ_TABLE_RAW[i]
    freq = 1_500_000 / d
    midi = divisor_to_midi_note(d)
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    name = note_names[midi % 12]
    octave = midi // 12 - 1
    print(f"  Entry {i:2d}: divisor={d:5d}, freq={freq:8.1f} Hz, "
          f"MIDI {midi} ({name}{octave})")

# ── MIDI helpers ─────────────────────────────────────────────────────

def var_len(value):
    buf = []
    buf.append(value & 0x7F)
    value >>= 7
    while value:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    buf.reverse()
    return bytes(buf)


def build_track(voice_data, channel, program, note_offset, velocity, label):
    """Build MIDI track for one voice using frequency table mapping."""
    track = bytearray()
    # Program change
    track += var_len(0)
    track += bytes([0xC0 | channel, program])

    current_note = -1
    current_tick = 0
    note_count = 0

    for tick, byte_val in enumerate(voice_data):
        abs_tick = tick * TICKS_PER_STEP
        if byte_val > 0:
            # Map ROM note to MIDI using offset
            midi_note = max(0, min(127, byte_val + note_offset))

            # Also compute from frequency table for verification
            table_idx = byte_val - 36
            if 0 <= table_idx < len(FREQ_TABLE_RAW):
                divisor = FREQ_TABLE_RAW[table_idx]
                freq_midi = divisor_to_midi_note(divisor)
                # Use the frequency-table-based MIDI note
                midi_note = max(0, min(127, freq_midi))

            if midi_note != current_note:
                if current_note != -1:
                    delta = abs_tick - current_tick
                    track += var_len(delta)
                    track += bytes([0x80 | channel, current_note, 0x40])
                    current_tick = abs_tick
                delta = abs_tick - current_tick
                track += var_len(delta)
                track += bytes([0x90 | channel, midi_note, velocity])
                current_note = midi_note
                current_tick = abs_tick
                note_count += 1
        else:
            if current_note != -1:
                delta = abs_tick - current_tick
                track += var_len(delta)
                track += bytes([0x80 | channel, current_note, 0x40])
                current_note = -1
                current_tick = abs_tick

    if current_note != -1:
        delta = len(voice_data) * TICKS_PER_STEP - current_tick
        track += var_len(delta)
        track += bytes([0x80 | channel, current_note, 0x40])

    track += var_len(0)
    track += bytes([0xFF, 0x2F, 0x00])
    print(f"  Track '{label}': {len(voice_data)} bytes, {note_count} notes")
    return track


# ── Settings ─────────────────────────────────────────────────────────
PPQN = 480
TICKS_PER_STEP = 150    # each step ≈ eighth note
TEMPO_BPM = 120         # BPM
VELOCITY = 100

# ── Build tracks ─────────────────────────────────────────────────────

# Tempo track
tempo_track = bytearray()
us_per_beat = int(60_000_000 / TEMPO_BPM)
tempo_track += var_len(0)
tempo_track += bytes([0xFF, 0x51, 0x03,
                      (us_per_beat >> 16) & 0xFF,
                      (us_per_beat >> 8) & 0xFF,
                      us_per_beat & 0xFF])
tempo_track += var_len(0)
tempo_track += bytes([0xFF, 0x58, 0x04, 0x04, 0x02, 0x18, 0x08])
tempo_track += var_len(0)
tempo_track += bytes([0xFF, 0x2F, 0x00])

# Voice tracks
track1 = build_track(voice1, channel=0, program=80,  # Square Lead (melody)
                     note_offset=NOTE_OFFSET, velocity=VELOCITY, label="Melody")
track2 = build_track(voice2, channel=1, program=80,  # Square Lead (harmony)
                     note_offset=NOTE_OFFSET, velocity=VELOCITY - 10, label="Harmony")
track3 = build_track(voice3, channel=2, program=80,  # Square Lead (bass)
                     note_offset=NOTE_OFFSET, velocity=VELOCITY, label="Bass")

# ── Assemble MIDI file ───────────────────────────────────────────────
midi = bytearray()
midi += b'MThd'
midi += struct.pack('>I', 6)
midi += struct.pack('>HHH', 1, 4, PPQN)  # format 1, 4 tracks

tracks = [("Tempo", tempo_track), ("Melody", track1),
          ("Harmony", track2), ("Bass", track3)]

for name, data in tracks:
    midi += b'MTrk'
    midi += struct.pack('>I', len(data))
    midi += data

# ── Write ────────────────────────────────────────────────────────────
output_path = "../dest/music.mid"
with open(output_path, "wb") as f:
    f.write(midi)

max_steps = max(len(voice1), len(voice2), len(voice3))
duration_sec = max_steps * TICKS_PER_STEP * 60.0 / (TEMPO_BPM * PPQN)
print(f"\nMIDI file: {output_path} ({len(midi)} bytes)")
print(f"  Format 1, PPQN {PPQN}, {TEMPO_BPM} BPM")
print(f"  Note mapping: freq_table[note-36] → MIDI")
print(f"  Max steps: {max_steps}, ticks/step: {TICKS_PER_STEP}")
print(f"  Estimated duration: {duration_sec:.1f} seconds")
