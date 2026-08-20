#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
music2mus.py — конвертер извлечённых дорожек Konami NES-движка (Jackal)
в партитуры .mus для компилятора Вектора-06Ц mus2inc.py.

Использование:
    python3 utils/music2mus.py <папка music из extract_music.py> <вых. папка>
                               [--self-test]

Для каждой мелодии (01_intro..09_ending с каналами pulse1/pulse2/
triangle/dmc.bin) создаёт <имя>.mus:
    pulse1   -> score 0;
    pulse2   -> score 1;
    triangle -> score 2;
    dmc      -> drums (sample 0 = бочка, sample 1 = снейр/том).

Время переносится на целочисленную сетку PPQ = 32 (как в mus2inc.py)
БЕЗ округлений:
    1 кадр движка = TICKS_PER_FRAME = 2 тика сетки;
    темп T = 1.875 * f_движка * 2  (целое):
        60 Гц        -> T225  (1 тик = 1/120 с, кадр 60 Гц = ровно 2 тика);
        53.333 Гц    -> T200  (Intro Jackal, пропуск 1 из 9 кадров);
    за кадр 50 Гц плеер потребляет 4T/375 тика (аккумулятор Брешихэма
    в music.c) — длительность кадра источника воспроизводится точно.

Длительность события в тиках раскладывается в сумму разрешённых
длительностей {128,64,32,16,8,4,2} (L_n = 128/n):
    тон  — повторение той же ноты (ВИ53 перезагружает тот же делитель,
           звук тянется без паузы);
    пауза/удар — паузы P (звучащий семпл не обрывается).

Модель звукового движка Konami и байтовый парсер перенесены из
удалённого music2inc.py (см. его историю): байты $FB/$FC/$FE/$FF —
петли/конец, $E0-$E7 — октава, $Dn — база длительности, $Cn — пауза,
остальные < $C0 — ноты (hi-тетрада = индекс в TABLE3, lo * base =
длительность; .bin уже содержат повторные участки «в строке», поэтому
$FE просто пропускается).

Высоты: NES-период -> частота -> ближайший полутон (абсолютный номер
октава*12 + полутон, ля 4-й октавы = 57). Частоты triangle считаются
по формуле треугольного канала NES (на октаву ниже пульса при том же
периоде). Выход за рабочий диапазон 12..94 транспонируется октавой
с предупреждением.
"""

import argparse
import math
import os
import sys

TICKS_PER_FRAME = 2     # тиков сетки PPQ=32 на кадр движка NES
VALID_TICKS = (128, 64, 32, 16, 8, 4, 2, 1)   # L_n = 128/n

# Мелодии Jackal: папка extract_music.py -> (имя .mus, частота тика
# движка). Intro идёт на 53.333 Гц (пропуск 1 из 9 кадров), остальные —
# на кадровых 60 Гц NES.
SONGS = [
    ("01_intro",       "intro",        160.0 / 3.0),
    ("02_level1",      "level1",       60.0),
    ("03_level2",      "level2",       60.0),
    ("04_level3",      "level3",       60.0),
    ("05_boss",        "boss",         60.0),
    ("06_final_boss",  "final_boss",   60.0),
    ("07_stage_clear", "stage_clear",  60.0),
    ("08_game_over",   "game_over",    60.0),
    ("09_ending",      "ending",       60.0),
]

CHANNEL_FILES = [("pulse1.bin", "pulse"),
                 ("pulse2.bin", "pulse"),
                 ("triangle.bin", "triangle"),
                 ("dmc.bin", "dmc")]

# table3 движка Konami — хроматическая таблица периодов NES pulse от C2
TABLE3 = [0x06AE, 0x064E, 0x05F4, 0x059E, 0x054E, 0x0501,
          0x04B9, 0x0476, 0x0436, 0x03F9, 0x03C0, 0x038A]
NOTE_NAMES = ["C", "C+", "D", "D+", "E", "F",
              "F+", "G", "G+", "A", "A+", "B"]

CPU_CLK = 1789773.0
NOTE_MIN, NOTE_MAX = 12, 94     # рабочая зона байткода (октавы 1..7)


# ------------------------- парсер движка Konami -------------------------

class Channel:
    def __init__(self, data, kind, name=""):
        self.d = data
        self.kind = kind            # 'pulse' | 'triangle' | 'dmc'
        self.name = name
        self.pc = 0
        # движок инициализирует базу длительности и октаву нулём; для
        # triangle-канала октавный сдвиг по умолчанию = 1 (басовый диапазон)
        self.dur_base = 0 if kind == "dmc" else 1
        self.octave = 1 if kind == "triangle" else 0
        self.loop_base = 0          # позиция после $FB
        self.finished = False
        self.last_hit = 0           # hi-тетрада последнего удара (dmc)
        self.last_event = None      # словарь последнего события

    def parse_one(self):
        """Разбирает одно событие; возвращает длительность в кадрах
        движка. Заполняет self.last_event: kind ('note'|'rest'|'hit'),
        byte, dur."""
        d = self.d
        while self.pc < len(d) and not self.finished:
            b = d[self.pc]
            hi, lo = b >> 4, b & 0x0F

            if b >= 0xFB:
                if b in (0xFB, 0xFC):
                    self.pc += 1
                    self.loop_base = self.pc
                    continue
                if b == 0xFD:
                    raise RuntimeError("$FD не поддерживается")
                if b == 0xFE:
                    n = d[self.pc + 1]
                    if n == 0xFF:
                        self.finished = True
                        self.last_event = None
                        return 0
                    # .bin уже содержит повторный участок внутри блока,
                    # поэтому просто пропускаем $FE n
                    self.pc += 2 + n
                    continue
                if b == 0xFF:
                    self.finished = True
                    self.last_event = None
                    return 0

            if 0xE0 <= b <= 0xE7:
                self.octave = lo
                self.pc += 1
                continue
            if b == 0xE8:
                self.pc += 1
                continue
            if 0xF0 <= b <= 0xFA:
                self.pc += 1              # вибрато - не моделируем
                continue

            if 0xD0 <= b <= 0xDF:
                self.dur_base = lo
                if self.kind == "pulse":
                    self.pc += 4
                elif self.kind == "triangle":
                    self.pc += 2
                else:                     # dmc: операндов нет
                    self.pc += 1
                continue

            # --- нота / пауза ($00-$CF) ---
            dur = self.dur_base if lo == 0 else lo * self.dur_base
            self.pc += 1

            if hi == 0x0C:                # пауза ДЛЯ ВСЕХ КАНАЛОВ
                self.period = None
                self.last_hit = 0
                self.last_event = {"kind": "rest", "byte": b, "dur": dur}
                return dur

            if self.kind == "dmc":
                self.last_hit = hi
                self.period = None
                self.last_event = {"kind": "hit", "byte": b, "dur": dur,
                                   "hit": 0 if hi < 0x08 else 1}
                return dur

            self.period = TABLE3[hi] >> (4 - self.octave)
            self.last_event = {"kind": "note", "byte": b, "dur": dur}
            return dur

        self.finished = True
        self.last_event = None
        return 0

    def freq(self):
        """Частота в Гц для текущего периода."""
        if self.period is None:
            return 0.0
        p = int(self.period)
        if self.kind == "triangle":
            return CPU_CLK / (32.0 * (p + 1))
        return CPU_CLK / (16.0 * (p + 1))


def read_channel(song_dir, fname, kind, name=""):
    path = os.path.join(song_dir, fname)
    if not os.path.isfile(path):
        print(f"  {fname}: отсутствует — канал пустой", file=sys.stderr)
        return Channel(b"\xFF", kind, name)
    return Channel(open(path, "rb").read(), kind, name)


def chan_events(ch):
    """Событийная шкала одного канала: [(start, dur, ev)], start/dur —
    в кадрах движка. Повторяет модель времени music2inc.py."""
    out = []
    t = 0
    while True:
        dur = ch.parse_one()
        if ch.last_event is None:
            break
        ev = dict(ch.last_event)
        if ev["kind"] == "note":
            ev["freq"] = ch.freq()
        out.append((t, dur, ev))
        t += dur
        if ch.finished:
            break
    return out


# ---------------------------- эмиссия .mus ------------------------------

def tempo_of(src_hz):
    """Темп .mus, при котором кадр источника = ровно TICKS_PER_FRAME
    тиков сетки: 1 тик = 1.875/T с; кадр источника = 1/hz с."""
    t = 1.875 * src_hz * TICKS_PER_FRAME
    ti = int(round(t))
    if abs(t - ti) > 1e-6 or not 32 <= ti <= 255:
        raise RuntimeError(f"частота {src_hz} Гц не даёт целый темп: {t}")
    return ti


def decompose(ticks):
    """Разложить длительность в тиках в сумму разрешённых (жадно,
    от крупных к мелким)."""
    parts = []
    for v in VALID_TICKS:
        while ticks >= v:
            parts.append(v)
            ticks -= v
    return parts


def freq_to_abs(freq, warnings, where):
    """Частота -> абсолютный номер ноты (октава*12 + полутон)."""
    n = round(12 * math.log2(freq / 440.0)) + 69     # MIDI-номер
    a = n - 12                                        # наш номер (A4=57)
    while a < NOTE_MIN:
        warnings.append(f"{where}: {freq:.1f} Гц ниже рабочей зоны —"
                        " транспонировано октавой вверх")
        a += 12
    while a > NOTE_MAX:
        warnings.append(f"{where}: {freq:.1f} Гц выше рабочей зоны —"
                        " транспонировано октавой вниз")
        a -= 12
    return a


class Writer:
    """Партитура одного канала: следит за текущими L и октавой."""

    def __init__(self):
        self.toks = []
        self.l_ticks = 32         # как в mus2inc.py: старт L4
        self.oct = 4

    def _set_len(self, ticks):
        lval = 128 // ticks
        if ticks != self.l_ticks:
            self.toks.append(f"L{lval}")
            self.l_ticks = ticks

    def _note(self, a):
        o, semi = divmod(a, 12)
        if o != self.oct:
            self.toks.append(f"O{o}")
            self.oct = o
        self.toks.append(NOTE_NAMES[semi])

    def note(self, a, ticks):
        parts = decompose(ticks)
        self._set_len(parts[0])
        self._note(a)
        for p in parts[1:]:       # тянущийся тон: повтор той же ноты
            self._set_len(p)
            self._note(a)

    def rest(self, ticks):
        for p in decompose(ticks):
            self._set_len(p)
            self.toks.append("P")

    def hit(self, sample_id, ticks):
        parts = decompose(ticks)
        self._set_len(parts[0])
        self.toks.append(str(sample_id))
        for p in parts[1:]:       # атака одна, остаток — паузы
            self._set_len(p)
            self.toks.append("P")


def wrap(toks, width=72):
    """Разбить список токенов на строки не шире width."""
    lines, cur = [], ""
    for t in toks:
        if cur and len(cur) + 1 + len(t) > width:
            lines.append(cur)
            cur = t
        else:
            cur = t if not cur else cur + " " + t
    if cur:
        lines.append(cur)
    return lines


def convert_song(song_dir, tick_hz, name):
    """Одна мелодия -> (текст .mus, сводка, предупреждения)."""
    warnings = []
    tempo = tempo_of(tick_hz)
    writers = [Writer(), Writer(), Writer(), Writer()]
    totals = []

    for i, (fname, kind) in enumerate(CHANNEL_FILES):
        ch = read_channel(song_dir, fname, kind, os.path.splitext(fname)[0])
        evs = chan_events(ch)
        totals.append(sum(d for _, d, _ in evs))
        w = writers[i]
        for _start, dur, ev in evs:
            ticks = dur * TICKS_PER_FRAME
            if ticks == 0:
                warnings.append(f"{name}/{ch.name}: событие"
                                f" ${ev['byte']:02X} нулевой длительности"
                                " пропущено")
                continue
            if kind == "dmc":
                if ev["kind"] == "rest":
                    w.rest(ticks)
                else:
                    w.hit(ev["hit"], ticks)
            elif ev["kind"] == "rest":
                w.rest(ticks)
            else:
                a = freq_to_abs(ev["freq"], warnings,
                                f"{name}/{ch.name}")
                w.note(a, ticks)

    # выравнивание длин: партитуры обязаны совпадать по тактам, иначе '!'
    lengths = {n: t * TICKS_PER_FRAME
               for n, t in zip(("score0", "score1", "score2", "drums"),
                               totals) if t > 0}
    mismatch = len(set(lengths.values())) > 1

    lines = [f"; {name}.mus — автоматически сгенерировано music2mus.py",
             f"; источник: {os.path.basename(song_dir)} (движок Konami,"
             f" {tick_hz:g} Гц); сетка PPQ=32, 1 кадр = {TICKS_PER_FRAME}"
             f" тика — длительности точные",
             "; sample 0 — бочка (DMC hi<8), sample 1 — снейр/том (hi>=8)",
             "sample 0: samples/kick.smp",
             "sample 1: samples/snare.smp"]
    sections = [("score 0:", writers[0]), ("score 1:", writers[1]),
                ("score 2:", writers[2]), ("drums:", writers[3])]
    first_emitted = False
    for header, w in sections:
        if not w.toks:
            continue
        body = [f"T{tempo}"] + w.toks
        if mismatch and not first_emitted:
            body.append("!")     # разная длина партитур разрешена
        lines.append(header)
        lines.extend(wrap(body))
        first_emitted = True

    summary = (f"{name}: темп T{tempo}, кадры источника"
               f" p1={totals[0]} p2={totals[1]} tri={totals[2]}"
               f" dmc={totals[3]}"
               + ("; ДЛИНЫ ПАРТИТУР РАЗНЫЕ — добавлен '!'" if mismatch
                  else ""))
    return "\n".join(lines) + "\n", summary, warnings


# ------------------------------ self-test --------------------------------

def self_test():
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    def sim(ch):
        evs = chan_events(ch)
        return evs

    # 1) DMC: порядок и длительности событий, пауза не даёт удара
    #    (dur = lo * base, lo = 0 -> base; база задаётся $Dn)
    ch = Channel(bytes([0xFB, 0xD3, 0x31, 0x32, 0xC2, 0xB1, 0xFF]), "dmc")
    evs = sim(ch)
    check([e["kind"] for _, _, e in evs] == ["hit", "hit", "rest", "hit"],
          "DMC порядок: %s" % [e["kind"] for _, _, e in evs])
    check([d for _, d, _ in evs] == [3, 6, 6, 3],
          "DMC длительности: %s" % [d for _, d, _ in evs])
    check([s for s, _, _ in evs] == [0, 3, 9, 15],
          "DMC старты: %s" % [s for s, _, _ in evs])
    check(evs[0][2]["hit"] == 0 and evs[3][2]["hit"] == 1,
          "DMC типы ударов")

    # 2) pulse: $D3 берёт 3 операнда; нота -> нота -> пауза, dur = base
    ch = Channel(bytes([0xFB, 0xD3, 0, 0, 0, 0x30, 0x40, 0xC0, 0xFF]),
                 "pulse")
    evs = sim(ch)
    check([e["kind"] for _, _, e in evs] == ["note", "note", "rest"],
          "pulse порядок: %s" % [e["kind"] for _, _, e in evs])
    check([d for _, d, _ in evs] == [3, 3, 3],
          "pulse длительности: %s" % [d for _, d, _ in evs])

    # 3) расклад длительностей: точность сумм
    for t in (2, 6, 32, 90, 450):
        parts = decompose(t)
        check(sum(parts) == t, f"decompose({t}) сумма: {parts}")
        check(all(p in VALID_TICKS for p in parts),
              f"decompose({t}) недопустимая часть: {parts}")

    # 4) темп: кадр источника воспроизводится точно
    for hz in (60.0, 160.0 / 3.0):
        t = tempo_of(hz)
        tick_s = 1.875 / t
        check(abs(tick_s * TICKS_PER_FRAME - 1.0 / hz) < 1e-9,
              f"темп T{t} неточен для {hz} Гц")

    # 5) частота -> нота: ля 440 Гц = A4 (абс. 57)
    w = []
    check(freq_to_abs(440.0, w, "t") == 57, "A4 != 57")
    check(freq_to_abs(CPU_CLK / (32.0 * (0x06AE + 1)), w, "t") >= NOTE_MIN,
          "triangle C-ниже рабочей зоны без транспозиции")

    # 6) Writer: старт с L4; первая нота на текущую длину, разлад
    #    длительности даёт L + повтор ноты
    w = Writer()
    w.note(57, 32)
    check(w.toks == ["A"], "Writer первая нота на L4: %s" % w.toks)
    w.note(59, 48)              # 48 = 32 + 16 -> L8 + повтор
    check(w.toks == ["A", "B", "L8", "B"],
          "Writer повтор: %s" % w.toks)

    if fails:
        print("SELF-TEST: %d ошибок" % len(fails))
        for m in fails:
            print("  - " + m)
        return 1
    print("SELF-TEST: все проверки пройдены")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Конвертер дорожек Konami NES-движка (Jackal) в .mus"
                    " для mus2inc.py")
    ap.add_argument("music_root", nargs="?",
                    help="папка с 01_intro..09_ending (результат"
                         " extract_music.py)")
    ap.add_argument("out_dir", nargs="?",
                    help="папка для выходных .mus")
    ap.add_argument("--self-test", action="store_true",
                    help="внутренние проверки парсера и эмиссии")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.music_root or not args.out_dir:
        ap.error("нужны папка с мелодиями NES и выходная папка")

    os.makedirs(args.out_dir, exist_ok=True)
    all_warnings = []
    for folder, name, hz in SONGS:
        song_dir = os.path.join(args.music_root, folder)
        if not os.path.isdir(song_dir):
            print(f"ПРОПУСК: {song_dir} не найдена", file=sys.stderr)
            continue
        text, summary, warns = convert_song(song_dir, hz, name)
        out = os.path.join(args.out_dir, name + ".mus")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(summary + f" -> {out}")
        all_warnings.extend(warns)
    if all_warnings:
        print("\n=== ПРЕДУПРЕЖДЕНИЯ ===")
        for wmsg in all_warnings:
            print("  - " + wmsg)


if __name__ == "__main__":
    main()
