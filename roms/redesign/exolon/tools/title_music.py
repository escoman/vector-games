#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 9a: PARTITURA ЗАСТАВКИ exolon → нормализованные потоки кодов + спека MIDI.

ROM-специфичный разбор (правило проекта: ROM-специфичное живёт в tools/). Здесь
понимается ЭКЗОЛОНОВСКИЙ формат, а байт→MIDI-математику делает универсальный
`utils/analyze/music2midi.py` по схеме `v06c-music-spec/1` (encoding=period_table).

Что доказано анализом (см. reports/Stage9a.md):
  * Мелодия заставки играется ОДИН раз из `func_play_blink_sequence @0x73BE`
    (LXI H,70B4h), это НЕ ВИ53 и НЕ прерывание: звук — 1-битный бипер ВВ55
    (порт C бит0), который `func_blink_toggle @0x7335` переключает командами
    `OUT 00h` (BSR 00h/01h) в tight-цикле.
  * Нота = 3 байта {A=длительность, hi-idx, lo-idx}. hi/lo — индексы в таблице
    периодов @0x7300 (53 монотонных значения 01h..F4h):
        D = table[hi-idx], E = table[lo-idx]
  * Два одновременных тона-огибающие (измерено прогоном реального кода в
    v06_emu, автокорреляция фронта бипера):
        нижний тон: период = 2*(256 - D) итераций быстрого цикла  (задаётся hi-idx)
        верхний тон: период = 2*(256 - E) итераций                (задаётся lo-idx)
    быстрый путь = 77 T-состояний/итерацию; эффективный CPU ≈ 3 МГц (docs VERIFIED).
    f = 3_000_000 / (77 * период) → ноты прилично ложатся на западную шкалу.
  * Длительность A ∈ {18,36,54,72,90} = 1..5 музыкальных шагов (шаг A=18 →
    256*18 итераций = 4608 → ~118.3 мс). Терминатор списка — 00h @0x72FD.
  * Пауз (hi=0 & lo=0) в заставке НЕТ — все ноты двухголосые.

Выход: tools/title_streams.bin (поток кодов нижн.голоса || поток кодов верхн.) и
tools/music_spec_title.json для music2midi. `--validate` прогоняет v06_emu и
сверяет измеренную огибающую с формулой 2*(256-value).
"""
from __future__ import annotations
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROM_DIR = os.path.dirname(HERE)
SRC = os.path.join(ROM_DIR, "src")
ORG = 0x0100

SEQ_ADDR = 0x70B4      # LXI H в lbl_title_init (CALL func_play_blink_sequence)
TABLE_ADDR = 0x7300    # таблица периодов (53 значения)
TABLE_LEN = 53
DUR_BASE = 18          # A=18 -> 1 музыкальный шаг
CYC_PER_ITER = 77      # T-состояния быстрого пути func_blink_toggle (ручной подсчёт)
CPU_HZ = 3_000_000     # docs/VECTOR_VERIFIED.md: эффективная частота CPU ≈ 3 МГц
ITER_PER_STEP = 256 * DUR_BASE  # итераций в одном базовом шаге (C=A, B=256)
PPQ = 192
STEP_TICKS = 48                  # базовый шаг = восьмая (quarter=192, 4 шага/такт)

rom = open(os.path.join(SRC, "exolon.rom"), "rb").read()
def rb(a, n): return rom[a - ORG:a - ORG + n]


def parse_notes():
    """Тройки {A, hi, lo} от SEQ_ADDR до терминатора 00h."""
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
PERIOD_WORDS = [2 * (256 - v) for v in TABLE]   # итерации (prescale-единицы)


def note_freq(period_iters):
    return CPU_HZ / (CYC_PER_ITER * period_iters)


def midi_note(period_iters):
    import math
    rel = 12.0 * math.log2(note_freq(period_iters) / 440.0)
    return 69 + int(round(rel))


def emit_stream(notes, idx_pos):
    """Поток кодов для одного голоса: pitch-code + (hold-code если k>1).

    idx_pos=1 -> hi-idx (нижний тон), =2 -> lo-idx (верхний тон).
    """
    out = []
    for A, hi, lo in notes:
        code = (hi if idx_pos == 1 else lo)
        k = A // DUR_BASE
        out.append(code)
        if k > 1:
            out.append(0x80 | (k - 1))   # холд: (code&0x0F)*hold_unit шагов
    return out


def build_spec(lo_stream, hi_stream):
    len_lo = len(lo_stream)
    return {
        "schema": "v06c-music-spec/1",
        "title": "EXOLON Vector-06C title (beeper bit-bang)",
        "rom": "title_streams.bin",
        "org": "0x0000",
        "output": "../exolon_title.mid",
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
            "unit": "func_blink_toggle loop-iteration (77 T-states @ ~3 MHz); period=2*(256-table[i])",
            "words": PERIOD_WORDS,
        },
        "provenance": {
            "facts_from": "reports/Stage9a_music_spec.md",
            "notes": [
                "мелодия заставки = 195 двухголосых нот из func_play_blink_sequence @0x73BE (LXI H,0x70B4)",
                "источник звука: 1-битный бипер ВВ55 (OUT 00h = BSR порта C бит0), НЕ КР580ВИ53",
                "нота 3 байта {A=18/36/54/72/90 (1..5 шагов), hi-idx (низ), lo-idx (верх)}",
                "таблица периодов @0x7300 (53 знач.); тон_низ=2*(256-tab[hi]), тон_верх=2*(256-tab[lo])",
                "pitch_table.words[i]=2*(256-tab[i]) — период в итерациях; prescale=77, timer=3 МГц (docs VERIFIED)",
                "дорожки ниже — НОРМАЛИЗОВанные потоки кодов, построенные tools/title_music.py из exolon.rom "
                "@0x70B4 (терминатор 00h @0x72FD); source=image читает tools/title_streams.bin",
                "побайтовая подложка: 585 байт @0x70B4..0x72FD + 53 байта @0x7300 в exolon.rom (sha см. отчёт)",
            ],
            "verified_by": "tools/title_music.py --validate (прогон func_blink_toggle в v06_emu, "
                           "автокорреляция огибающей бипера == 2*(256-value)) + expect-дампы потоков",
        },
        "tracks": [
            {
                "name": "EXOLON title low (hi-idx tone)",
                "address": "0x0000",
                "length": len_lo,
                "source": "image",
                "midi_channel": 0,
                "gm_program": 80,
                "expect": lo_stream,
            },
            {
                "name": "EXOLON title high (lo-idx tone)",
                "address": hex(len_lo),
                "length": len(hi_stream),
                "source": "image",
                "midi_channel": 1,
                "gm_program": 81,
                "expect": hi_stream,
            },
        ],
    }


def write_outputs(lo_stream, hi_stream, spec):
    binp = os.path.join(HERE, "title_streams.bin")
    with open(binp, "wb") as f:
        f.write(bytes(lo_stream) + bytes(hi_stream))
    sp = os.path.join(HERE, "music_spec_title.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    return binp, sp


def validate_measured(limit_pairs=12):
    """Прогон реального func_blink_toggle в v06_emu: фундаментал огибающей == 2*(256-value)."""
    sys.path.insert(0, os.path.join(ROM_DIR, "..", "..", "..", "utils", "emulator"))
    try:
        from v06_emu import CPU8080, SENTINEL
    except Exception as e:
        print("v06_emu недоступен, пропускаю измерение:", e)
        return True
    TOGGLE = 0x7335
    def measured_Lperiod(D, E):
        ev = []
        def hook(p, v):
            if p == 0x00:
                ev.append(v & 1)
        c = CPU8080(io_write=hook); c.mem[ORG:ORG + len(rom)] = rom
        c.sp = 0xF000; c.push(SENTINEL); c.a = DUR_BASE; c.d = D; c.e = E; c.pc = TOGGLE
        try:
            c.run_until(max_steps=8_000_000, stop_pc=SENTINEL)
        except TimeoutError:
            return None
        L = [ev[2 * k + 1] for k in range(len(ev) // 2)]
        for lag in range(2, len(L) // 2):
            if all(L[i] == L[i + lag] for i in range(0, len(L) - lag)):
                return lag
        return None
    uniq_hi = sorted(set(h for _, h, _ in parse_notes()[1]))[:limit_pairs]
    ok = True
    for hi in uniq_hi:
        D = TABLE[hi]; want = 2 * (256 - D)
        got = measured_Lperiod(D, 0xEA)
        flag = "OK" if got == want else "!!"
        if got != want:
            ok = False
        print(f"  hi={hi:2d} D=0x{D:02X} период_низ: измер={got} формула={want} [{flag}]")
    return ok


def main(argv=None):
    term, notes = parse_notes()
    seq_bytes = rb(SEQ_ADDR, term - SEQ_ADDR)
    lo_stream = emit_stream(notes, 1)
    hi_stream = emit_stream(notes, 2)
    spec = build_spec(lo_stream, hi_stream)
    binp, sp = write_outputs(lo_stream, hi_stream, spec)

    print(f"notes={len(notes)} терминатор 00h @0x{term:04X} (длина списка {term-SEQ_ADDR}B)")
    print(f"таблица периодов @0x{TABLE_ADDR:04X}: {TABLE_LEN} значений "
          f"(0x{TABLE[0]:02X}..0x{TABLE[-1]:02X})")
    print(f"поток кодов: низ={len(lo_stream)} верх={len(hi_stream)} "
          f"(всего шагов={sum(A//DUR_BASE for A,_,_ in notes)})")
    lo = min(midi_note(PERIOD_WORDS[h]) for _, h, _ in notes)
    hi = max(midi_note(PERIOD_WORDS[h]) for _, h, _ in notes)
    print(f"нижний голос MIDI-диапазон: {lo}..{hi} "
          f"(A{lo-12*4}..) ; базовый шаг ~{round(CYC_PER_ITER*ITER_PER_STEP/CPU_HZ*1000,1)} мс")
    print("выпущено:", binp, sp)

    if argv and "--validate" in argv:
        print("== проверка измерением (v06_emu автокорреляция огибающей) ==")
        if not validate_measured():
            print("ВНИМАНИЕ: расхождение формулы и измерения")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
