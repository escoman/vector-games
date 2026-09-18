#!/usr/bin/env python3
"""TESTAY.ROM -> MIDI extractor (approach A: emulate + capture AY register writes).

Runs src/TESTAY.ROM inside the repo's own 8080 emulator (utils/emulator/v06_emu.py),
intercepts the AY-3-8910 register writes on ports 0x15 (register select) and 0x14
(data), reconstructs per-frame register snapshots, detects the musical loop and
emits a Standard MIDI File (Format 1) with one track per AY tone channel plus a
percussion track for the noise channel.

No AY audio synthesis is performed -- we only need the register timeline, which is
exactly what the player writes each frame.

Usage:
    python3 testay2midi.py                       # capture + write testay.mid
    python3 testay2midi.py --steps 4000000       # longer capture
    python3 testay2midi.py --fps 50 --bpm 150    # timing overrides
    python3 testay2midi.py --stats               # only print capture statistics
"""
from __future__ import annotations

import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# repo root is <root>/roms/redesign/testay/tools
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
EMU_DIR = os.path.join(ROOT, "utils", "emulator")
sys.path.insert(0, EMU_DIR)

import v06_emu  # noqa: E402

ROM_PATH = os.path.join(ROOT, "roms", "redesign", "testay", "src", "TESTAY.ROM")

ORIGIN = 0x0100
SP0 = 0xC300            # Vector monitor sets SP here before entering the ROM
AY_CLOCK = 1_773_400    # Hz; matches z88dk psgT(hz)=110837.5/hz  => clock/16=110837.5
AY_T16 = AY_CLOCK / 16.0

PORT_AY_DATA = 0x14
PORT_AY_REG = 0x15
PORT_KBD = 0x01         # observed IN 0x01 always returns 0xEF
KBD_VALUE = 0xEF


class Capture:
    """Holds AY register state as written by the ROM."""

    def __init__(self):
        self.reg_select = 0
        self.regs = [0] * 16
        self.frames = []          # list of (steps, tuple(regs[0..10]))
        self.last_frame_steps = 0
        self._pending = {}        # reg -> value within the current batch
        self._dirty = False

    def io_write(self, port, value, steps):
        port &= 0xFF
        value &= 0xFF
        if port == PORT_AY_REG:
            self.reg_select = value & 0x1F
        elif port == PORT_AY_DATA:
            r = self.reg_select
            if r < 16:
                self.regs[r] = value
            # Registers 0x0A..0x00 are written as one batch, ending with R0.
            # Snapshot the frame when R0 (last) lands.
            if r == 0x00:
                self.frames.append((steps, tuple(self.regs[:11])))
                self.last_frame_steps = steps

    def io_read(self, port):
        return KBD_VALUE if (port & 0xFF) == PORT_KBD else 0xFF


def build_cpu():
    cap = Capture()
    cpu = v06_emu.CPU8080()
    cpu.io_write = lambda port, value: cap.io_write(port, value, cpu.steps)
    cpu.io_read = lambda port: cap.io_read(port)
    with open(ROM_PATH, "rb") as fh:
        data = fh.read()
    for i, b in enumerate(data):
        cpu.wb(ORIGIN + i, b)
    cpu.pc = ORIGIN
    cpu.sp = SP0
    cpu.steps = 0
    cpu.halted = False
    return cpu, cap, len(data)


def run_capture(max_steps):
    cpu, cap, rom_len = build_cpu()
    for _ in range(max_steps):
        if cpu.halted:
            break
        cpu.step()
    return cpu, cap, rom_len


def per_channel_series(frames):
    """Return for each AY channel a list of (frame_idx, period12, volume)."""
    # 12-bit tone periods: A=R1<<8|R0, B=R3<<8|R2, C=R5<<8|R4. Vols: R8,R9,R10.
    pairs = {0: ((1, 0), 8), 1: ((3, 2), 9), 2: ((5, 4), 10)}
    series = {0: [], 1: [], 2: []}
    for idx, (_steps, r) in enumerate(frames):
        for ch, ((hi, lo), volreg) in pairs.items():
            period = ((r[hi] & 0x0F) << 8) | r[lo]
            series[ch].append((idx, period, r[volreg] & 0x0F))
    return series


def mixer_series(frames):
    """Per-frame noise period (R6), mixer (R7) and per-channel volume."""
    out = []
    for idx, (_s, r) in enumerate(frames):
        out.append({
            "idx": idx,
            "noise_per": r[6] & 0x1F,
            "mixer": r[7],
            "vol": (r[8] & 0x0F, r[9] & 0x0F, r[10] & 0x0F),
        })
    return out


def detect_loop(frames):
    """Find the repeating span of frames. Returns (start, period) or None."""
    if len(frames) < 40:
        return None
    # Build a compact key per frame of the musically meaningful state.
    keys = [f[1] for f in frames]
    n = len(keys)
    # search loop start in the early region, period up to half the data
    best = None
    for start in range(0, min(120, n // 3)):
        for period in range(20, (n - start) // 2 + 1):
            ok = True
            # require the candidate to repeat contiguously for one full period
            # (i.e. compare [start,start+period) against [start+period,start+2*period);
            # needs only 2 periods of captured data).
            for i in range(start, start + period):
                if i + period >= n:
                    ok = False
                    break
                if keys[i] != keys[i + period]:
                    ok = False
                    break
            if ok:
                best = (start, period)
                return best
    return best


# ------------------------- MIDI writer -------------------------

def period_to_midi(period):
    if period <= 0:
        return None
    freq = AY_T16 / period
    if freq <= 0:
        return None
    midi = 69 + 12 * math.log2(freq / 440.0)
    note = int(round(midi))
    if 0 <= note <= 127:
        return note
    return None


class MIDITrack:
    def __init__(self):
        self.events = []  # (abs_tick, bytes)

    def add(self, tick, data):
        self.events.append((tick, data))

    def to_bytes(self):
        self.events.sort(key=lambda e: e[0])
        out = bytearray()
        last = 0
        for tick, data in self.events:
            delta = tick - last
            last = tick
            out += _vlq(delta)
            out += data
        out += _vlq(0) + b"\xff\x2f\x00"  # end of track
        return bytes(out)


def _vlq(value):
    value &= 0x7FFFFFFF
    buf = [value & 0x7F]
    value >>= 7
    while value:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(buf))


def _byte(v):
    """Clamp to a valid 7-bit MIDI data byte (0..127)."""
    return max(0, min(127, int(v)))


def _vel(v):
    """Velocity 1..127 (a note-on must never be 0, that means note-off)."""
    return max(1, min(127, int(v)))


def channel_events_to_midi(series, ppq, tpf, prog, ch, transpose=0):
    """Turn a per-frame (period, vol) series into note on/off MIDI events.

    The player drives a fixed per-note volume envelope (attack at 15, decaying
    to 8 over ~8 frames). A new note therefore starts on a *volume attack*
    (vol rises above the previous frame) or a pitch change while sounding, and
    is released when volume drops to 0 or the next attack arrives. Keying on the
    attack (not just pitch) keeps repeated same-pitch notes articulated instead
    of merging them into one long tie. An explicit open/closed flag guarantees
    every note-off is preceded by exactly one note-on.
    """
    tr = MIDITrack()
    tr.add(0, bytes([0xC0 | (ch & 0x0F), _byte(prog)]))
    open_note = None            # currently sounding MIDI note, or None
    prev_vol = 0
    st = ch & 0x0F
    for (fidx, period, vol) in series:
        tick = fidx * tpf
        note = period_to_midi(period)
        if note is not None:
            note = _byte(note + transpose)
        sounding = vol > 0 and note is not None
        attack = sounding and (note != open_note or vol > prev_vol)
        if attack:
            if open_note is not None:                       # close previous
                tr.add(tick, bytes([0x80 | st, _byte(open_note), 0]))
            tr.add(tick, bytes([0x90 | st, _byte(note), _vel(20 + vol * 90 / 15)]))
            open_note = note
        elif not sounding and open_note is not None:        # release
            tr.add(tick, bytes([0x80 | st, _byte(open_note), 0]))
            open_note = None
        prev_vol = vol
    if open_note is not None:                               # tail close
        tr.add(len(series) * tpf, bytes([0x80 | st, _byte(open_note), 0]))
    return tr


def noise_events_to_midi(mix, ppq, tpf, ch=9):
    """Route the AY noise generator (tone-off + noise-on channels) to a drum track.

    Drum chosen per channel: A->closed hat(42), B->snare(38), C->kick(36).
    """
    tr = MIDITrack()
    drums = [42, 38, 36]           # ch A, B, C default noise drums
    # mixer bits: 0 toneA, 1 noiseA, 2 toneB, 3 noiseB, 4 toneC, 5 noiseC
    tone_bits = [0, 2, 4]
    noise_bits = [1, 3, 5]
    active = [False, False, False]
    st = ch & 0x0F
    for row in mix:
        tick = row["idx"] * tpf
        mixer = row["mixer"]
        for c in range(3):
            noise_on = (mixer >> noise_bits[c]) & 1
            tone_on = (mixer >> tone_bits[c]) & 1
            vol = row["vol"][c]
            hit = noise_on and (not tone_on) and vol > 0
            if hit and not active[c]:
                tr.add(tick, bytes([0x90 | st, _byte(drums[c]), _vel(20 + vol * 7)]))
                active[c] = True
            elif (not hit) and active[c]:
                tr.add(tick, bytes([0x80 | st, _byte(drums[c]), 0]))
                active[c] = False
    for c in range(3):
        if active[c]:
            tr.add(len(mix) * tpf, bytes([0x80 | st, _byte(drums[c]), 0]))
    return tr


def write_midi(path, ppq, bpm, tracks):
    def track_chunk(b):
        return b"MTrk" + len(b).to_bytes(4, "big") + b

    # conductor track: tempo + time signature
    cond = bytearray()
    us_per_q = int(round(60_000_000 / bpm))
    cond += _vlq(0) + bytes([0xFF, 0x51, 0x03]) + us_per_q.to_bytes(3, "big")
    cond += _vlq(0) + bytes([0xFF, 0x58, 0x04, 4, 2, 24, 8])
    cond += _vlq(0) + b"\xff\x2f\x00"  # end of track

    out = bytearray()
    ntracks = 1 + len(tracks)
    out += b"MThd" + (6).to_bytes(4, "big") + (1).to_bytes(2, "big") \
        + ntracks.to_bytes(2, "big") + ppq.to_bytes(2, "big")
    out += track_chunk(bytes(cond))
    for tr in tracks:
        out += track_chunk(tr.to_bytes())
    with open(path, "wb") as fh:
        fh.write(out)
    return len(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", type=int, default=72_000_000, help="max 8080 instructions to run (>=2 loop periods)")
    ap.add_argument("--fps", type=float, default=50.0, help="real AY playback frame rate (50 Hz video refresh; drives MIDI tempo)")
    ap.add_argument("--bpm", type=float, default=0.0, help="override MIDI tempo; 0 = derive from --fps and --frames-per-beat")
    ap.add_argument("--ppq", type=int, default=480, help="MIDI ticks per quarter")
    ap.add_argument("--frames-per-beat", type=int, default=8, help="AY frames per quarter note (base note length)")
    ap.add_argument("--no-loop-trim", action="store_true", help="emit whole capture, no loop detect")
    ap.add_argument("--out", default=os.path.join(ROOT, "roms", "redesign", "testay", "testay.mid"))
    ap.add_argument("--stats", action="store_true", help="print capture stats only")
    args = ap.parse_args()

    cpu, cap, rom_len = run_capture(args.steps)
    frames = cap.frames
    print(f"ROM bytes loaded : {rom_len} @0x{ORIGIN:04X}")
    print(f"instructions run : {cpu.steps}")
    print(f"AY data writes   : {sum(1 for _ in frames)} frames (R0-terminated)")
    if frames:
        span = frames[-1][0] - frames[0][0]
        print(f"steps/frame      : {span/max(1,len(frames)-1):.0f}")

    loop = None if args.no_loop_trim else detect_loop(frames)
    print(f"detected loop    : {loop}")

    if args.stats:
        return

    if not frames:
        print("No AY frames captured -- aborting.", file=sys.stderr)
        sys.exit(1)

    use_frames = frames
    if loop:
        start, period = loop
        # keep one clean cycle starting at the loop point
        use_frames = frames[start:start + period]
    # reindex frames to 0..N-1 for the series builders (frame index -> tick)
    reindexed = list(enumerate(f[1] for f in use_frames))

    series = per_channel_series(reindexed)
    mix = mixer_series(reindexed)

    # ticks per frame: ppq / frames_per_beat
    tpf = max(1, round(args.ppq / args.frames_per_beat))
    # programs: A=lead, B=harmony, C=bass; noise -> drums (MIDI ch 10)
    tracks = [
        channel_events_to_midi(series[0], args.ppq, tpf, prog=80, ch=0),   # lead
        channel_events_to_midi(series[1], args.ppq, tpf, prog=81, ch=1),   # harmony
        channel_events_to_midi(series[2], args.ppq, tpf, prog=38, ch=2),   # bass
        noise_events_to_midi(mix, args.ppq, tpf),                          # drums
    ]

    bpm = args.bpm
    if not bpm:
        beat_sec = args.frames_per_beat / args.fps
        bpm = 60.0 / beat_sec if beat_sec > 0 else 120.0
    total_frames = len(use_frames)
    dur_sec = total_frames / args.fps

    size = write_midi(args.out, args.ppq, bpm, tracks)
    print(f"tpf (ticks/frame): {tpf}")
    print(f"frames emitted   : {total_frames}  (~{dur_sec:.1f}s @ {args.fps:g} fps)")
    print(f"tempo            : {bpm:.1f} BPM")
    print(f"wrote            : {args.out} ({size} bytes)")


if __name__ == "__main__":
    main()
