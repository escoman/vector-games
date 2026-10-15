#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 9b: PARTITURA GAME OVER exolon → потоки кодов + спека MIDI.

Формат нот идентичен заставке (тройка {A, hi-idx, lo-idx}, период-таблица @0x7300),
но базовая длительность A=15 (не 18) => шаг ~98.6 мс, темп быстрее.

Выход: tools/gameover_streams.bin + tools/music_spec_gameover.json.
"""
from __future__ import annotations
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROM_DIR = os.path.dirname(HERE)
SRC = os.path.join(ROM_DIR, "src")
ORG = 0x0100

SEQ_ADDR = 0x7079       # LXI H в func_render_and_blink → GAME OVER melody
TABLE_ADDR = 0x7300
TABLE_LEN = 53
DUR_BASE = 15           # A=15 -> 1 musical step (GAME OVER specific)
CYC_PER_ITER = 77
CPU_HZ = 3_000_000
ITER_PER_STEP = 256 * DUR_BASE
PPQ = 192
STEP_TICKS = 48

rom = open(os.path.join(SRC, "exolon.rom"), "rb").read()
def rb(a, n): return rom[a - ORG:a - ORG + n]


def parse_notes():
    notes = []
    a = SEQ_ADDR
    while True:
        A = rb(a, 1)[0]
        if A == 0x00:
            return a, notes
        hi = rb(a + 1, 1)[0]
        lo = rb(a + 2, 1)[0]
        notes.append((A, hi, lo))
        a += 3


TABLE = rb(TABLE_ADDR, TABLE_LEN)
PERIOD_WORDS = [2 * (256 - v) for v in TABLE]


def emit_stream(notes, idx_pos):
    out = []
    for A, hi, lo in notes:
        code = (hi if idx_pos == 1 else lo)
        k = A // DUR_BASE
        out.append(code)
        if k > 1:
            out.append(0x80 | (k - 1))
    return out


def build_spec(lo_stream, hi_stream):
    len_lo = len(lo_stream)
    return {
        "schema": "v06c-music-spec/1",
        "title": "EXOLON Game Over (beeper bit-bang)",
        "rom": "gameover_streams.bin",
        "org": "0x0000",
        "output": "../exolon_gameover.mid",
        "format": 1,
        "ppq": PPQ,
        "tempo_us_per_quarter": int(round(CYC_PER_ITER * ITER_PER_STEP / CPU_HZ * 4 * 1e6)),
        "time_signature": [4, 2, 24, 8],
        "encoding": "period_table",
        "rest_code": 0,
        "code_mask": "0xFF",
        "velocity": 96,
        "loop_code": 0,
        "slot_steps": 1,
        "hold_steps_per_nibble": 1,
        "gate_steps": 0,
        "rest_rule": "table_word_zero",
        "pitch_table": {
            "timer_hz": CPU_HZ,
            "prescale": CYC_PER_ITER,
            "a4_hz": 440,
            "unit": "func_blink_toggle loop-iteration (77 T @ ~3 MHz); period=2*(256-table[i])",
            "words": PERIOD_WORDS,
        },
        "provenance": {
            "facts_from": "reports/Stage9b.md",
            "notes": [
                "GAME OVER melody = 19 двухголосых нот из func_play_blink_sequence @0x73BE (LXI H,0x7079)",
                "формат тройки {A, hi-idx, lo-idx} идентичен title, но DUR_BASE=15 (не 18)",
                "таблица периодов @0x7300 (53 знач.); тон_низ=2*(256-tab[hi]), тон_верх=2*(256-tab[lo])",
                "pitch_table.words[i]=2*(256-tab[i]); prescale=77, timer=3 MHz",
                "дорожки — НОРМАЛИЗОВАННЫЕ потоки из tools/gameover_music.py (exolon.rom 0x7079..0x70B1)",
            ],
            "verified_by": "tools/gameover_music.py (парсинг) + expect-дампы music2midi",
        },
        "tracks": [
            {
                "name": "EXOLON GO low (hi-idx tone)",
                "address": "0x0000",
                "length": len_lo,
                "source": "image",
                "midi_channel": 0,
                "gm_program": 80,
                "expect": lo_stream,
            },
            {
                "name": "EXOLON GO high (lo-idx tone)",
                "address": hex(len_lo),
                "length": len(hi_stream),
                "source": "image",
                "midi_channel": 1,
                "gm_program": 81,
                "expect": hi_stream,
            },
        ],
    }


def main():
    term, notes = parse_notes()
    seq_len = term - SEQ_ADDR
    lo_stream = emit_stream(notes, 1)
    hi_stream = emit_stream(notes, 2)
    spec = build_spec(lo_stream, hi_stream)

    binp = os.path.join(HERE, "gameover_streams.bin")
    with open(binp, "wb") as f:
        f.write(bytes(lo_stream) + bytes(hi_stream))
    sp = os.path.join(HERE, "music_spec_gameover.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    total_steps = sum(A // DUR_BASE for A, _, _ in notes)
    step_ms = round(CYC_PER_ITER * ITER_PER_STEP / CPU_HZ * 1000, 1)
    print(f"GAME OVER: {len(notes)} нот, {seq_len}B, терминатор 00h @0x{term:04X}")
    print(f"шаг = {step_ms} мс (DUR_BASE={DUR_BASE}); {total_steps} шагов ≈ {total_steps*step_ms/1000:.2f} с")
    print(f" streams: lo={len(lo_stream)} hi={len(hi_stream)} (hold codes at k>1)")
    print(f"выпущено: {binp}, {sp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
