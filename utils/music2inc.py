# -*- coding: utf-8 -*-
"""
music2inc.py — конвертер извлечённых дорожек Konami NES-движка в .inc
для ROM Вектора-06Ц (плеер на КР580ВИ53).

Использование:
    python3 music2inc.py <папка_с_bin> [-o выход.inc] [--tick-hz Гц]
                         [--dump-notes] [--dump-dmc] [--dump-timeline]
                         [--dump-frames ФАЙЛ] [--self-test]

  папка_с_bin — папка с каналами pulse1.bin, pulse2.bin, triangle.bin,
                dmc.bin (результат работы extract_music.py);
  -o          — выходной .inc (по умолчанию <папка>_music.inc в текущем
                каталоге); имя массива = имя файла без расширения
                (intro_music.inc -> intro_music[], intro_music_len);
  --tick-hz   — частота тика движка исходной игры (по умолчанию 60;
                Intro Jackal — 53.333). Источник ретайминга: шкала
                пересчитывается под 50 Гц плеера Вектора, в .inc
                попадают целочисленные длительности, плеер — темп 1/1;
  --dump-notes— печать списка нот для визуальной проверки;
  --dump-dmc  — печать событий DMC-канала с абсолютными кадрами
                (в кадрах источника, до ретайминга);
  --dump-timeline — единая шкала границ событий всех каналов;
  --dump-frames ФАЙЛ — CSV итоговой покадровой шкалы (после ретайминга,
                как в .inc);
  --self-test — внутренние проверки парсера и границ событий, без конвертации.

Модель звукового движка Konami (по дизассемблеру Jackal, Bank0.ASM):
  * Движок покадровый; темп игры задаётся пропуском кадров снаружи
    (например, Intro Jackal: 1 из 9 кадров пропускается -> 53.33 Гц).
    Конвертер выполняет ретайминг шкалы источника под 50 Гц плеера
    Вектора: в .inc — целые тики цели, реальная скорость — темп 1/1
    (ровно один тик плеера на кадровое прерывание, без дробных темпов,
    дающих дрожание ритма).
  * Поток канала состоит из байтов-команд/нот (режим команд, т.к. 1-й байт $FB):
      $FB/$FC      - маркер начала петли (для $FE)
      $FD <dw>     - переход по абсолютному адресу (не поддерживается)
      $FE n        - повтор секции от $FB n раз, затем пропуск n байт.
                     ВАЖНО: извлечённые .bin уже содержат повторный участок
                     «в строке», поэтому при транскрипции $FE не выполняется
                     как прыжок, а просто пропускается (иначе музыка играла
                     бы участок дважды).
      $FE $FF      - конец клипа
      $FF          - конец клипа
      $E0-$E7      - октава: period >>= (4 - n)
      $E8          - переключатель (игнорируем)
      $F0-$FA      - глубина вибрато (игнорируем)
      $Dn <операнды> - база длительности = n;
                     pulse: 3 операнда; triangle: 1 операнд; dmc: без операндов
      $Cn          - пауза, длительность n*base (n=0 -> base). ПАУЗА ДЛЯ ВСЕХ
                     КАНАЛОВ, ВКЛЮЧАЯ DMC: удар не генерируется.
      остальные байты < $C0: нота с индексом = hi nibble,
                     длительность = lo nibble * base (0 -> base)
  * Высота ноты: period16 = table3[idx] >> (4 - octave);
    для triangle стартовое значение октавного регистра принимается равным 1
    (движок инициализирует его для басового диапазона).
  * table3 - хроматическая таблица от C2 (периоды NES pulse-таймера):
    C2 C#2 D2 D#2 E2 F2 F#2 G2 G#2 A2 A#2 B2
  * NES pulse:  f = 1789773 / (16*(period+1))
    NES triangle: f = 1789773 / (32*(period+1))  (тот же период -> на октаву
    ниже пульса, что даёт басовую партию)
  * DMC-канал - триггеры ударных: байт $Dn задаёт базу, байты нот -
    удар (hi nibble = тип: 3 = бочка/короткий, $B = том/длинный),
    длительность = lo nibble * base (0 -> base). Начальная база = 0.
    В плеере удар рендерится только в первые 2 кадра события:
    бочка = короткий низкий «стук» (шумовой код 2), том/снейр =
    шумовой всплеск (код 1); остаток длительности события звучит
    обычный бас triangle-канала.
"""

import argparse
import os
import sys

CHANNEL_FILES = [("pulse1.bin", "pulse"),
                 ("pulse2.bin", "pulse"),
                 ("triangle.bin", "triangle"),
                 ("dmc.bin", "dmc")]

BURST_FRAMES = 2      # кадров всплеска удара (короче — отрывистее)
NOISE_SNARE = 1       # код всплеска: том/снейр (шум)
NOISE_KICK = 2        # код всплеска: бочка (низкий стук)

TABLE3 = [0x06AE, 0x064E, 0x05F4, 0x059E, 0x054E, 0x0501,
          0x04B9, 0x0476, 0x0436, 0x03F9, 0x03C0, 0x038A]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

CPU_CLK = 1789773.0
MAX_FRAMES = 6000
TARGET_HZ = 50.0      # кадровая частота плеера Вектора-06Ц


def hit_type_of(hi):
    """Тип удара по старшей тетраде DMC-ноты (3 = бочка, B = том/снейр)."""
    return NOISE_KICK if hi < 0x08 else NOISE_SNARE


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
        self.rep_cnt = 0
        self.finished = False
        self.last_hit = 0           # hi-тетрада последнего удара (dmc)
        self.last_event = None      # словарь последнего события (для dump)
        self.fe_skips = []          # диагностика $FE: (pc, n, след. байт)
        # текущее звучащее состояние
        self.period = None          # NES-период
        self.dur_left = 0           # кадров до следующей команды

    def parse_one(self):
        """Разбирает одно событие; возвращает длительность в кадрах.
        Заполняет self.last_event: kind ('note'|'rest'), byte, dur."""
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
                    nxt = d[self.pc + 2 + n] if self.pc + 2 + n < len(d) else None
                    self.fe_skips.append((self.pc, n, nxt))
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

            # $C0-$CF — пауза ДЛЯ ВСЕХ КАНАЛОВ, проверяется до
            # специальной обработки DMC-ноты: пауза DMC не создаёт
            # last_hit и не генерирует noise.
            if hi == 0x0C:
                self.period = None
                self.last_hit = 0
                self.last_event = {"kind": "rest", "byte": b, "dur": dur}
                return dur

            if self.kind == "dmc":
                self.last_hit = hi
                self.period = None
                self.last_event = {"kind": "hit", "byte": b, "dur": dur,
                                   "hit": hit_type_of(hi)}
                return dur

            idx = hi
            self.period = TABLE3[idx] >> (4 - self.octave)
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


def transcribe_full(chans):
    """Покадровая симуляция всех каналов.

    Возвращает dict:
      frames      — [(f1, f2, f3, noise)] по одному на кадр движка;
      events      — {канал: [(start, dur, ev)]} границы событий;
      chan_frames — {канал: число кадров активности канала};
      fe_skips    — {канал: [(pc, n, следующий байт)]}.

    Модель времени: событие с длительностью d, разобранное после кадра N,
    занимает кадры N+1..N+d; следующее событие начинается ровно на N+d+1
    (без лишних и пропущенных кадров). Всплеск удара — первые
    BURST_FRAMES кадров самого события удара.
    """
    frames = []
    events = {ch: [] for ch in chans}
    chan_frames = {ch: 0 for ch in chans}
    noise_left = 0
    noise_kind = 0
    next_frame = 0

    ev = {}
    for ch in chans:
        dur = ch.parse_one()
        ev[ch] = dur
        if ch.last_event is not None:
            events[ch].append((next_frame, dur, ch.last_event))
        if ch.kind == "dmc" and ch.last_event is not None \
                and ch.last_event["kind"] == "hit" and dur > 0:
            noise_left = min(BURST_FRAMES, dur)
            noise_kind = hit_type_of(ch.last_hit)

    while next_frame < MAX_FRAMES:
        if all(c.finished for c in chans) and all(ev[c] == 0 for c in ev):
            break

        noise = noise_kind if noise_left > 0 else 0
        frames.append((round(chans[0].freq()), round(chans[1].freq()),
                       round(chans[2].freq()), noise))
        if noise_left > 0:
            noise_left -= 1
        for ch in chans:
            if not ch.finished or ev[ch] > 0:
                chan_frames[ch] += 1
        next_frame += 1

        for ch in chans:
            if ev[ch] > 0:
                ev[ch] -= 1
            if ev[ch] == 0 and not ch.finished:
                dur = ch.parse_one()
                ev[ch] = dur
                if ch.last_event is not None:
                    events[ch].append((next_frame, dur, ch.last_event))
                if ch.kind == "dmc" and ch.last_event is not None \
                        and ch.last_event["kind"] == "hit" and dur > 0:
                    noise_left = min(BURST_FRAMES, dur)
                    noise_kind = hit_type_of(ch.last_hit)

    fe = {}
    for ch in chans:
        if ch.fe_skips:
            fe[ch.name or ch.kind] = ch.fe_skips
    return {"frames": frames, "events": events,
            "chan_frames": chan_frames, "fe_skips": fe, "chans": chans}


def transcribe(song_dir):
    """Совместимая обёртка: только покадровая шкала."""
    chans = [read_channel(song_dir, f, k, os.path.splitext(f)[0])
             for f, k in CHANNEL_FILES]
    return transcribe_full(chans)["frames"]


def retime(frames, src_hz, dst_hz):
    """Ретайминг шкалы: src_hz -> dst_hz методом ближайшего кадра.

    Результат — целочисленные кадры цели, суммарная длина точно
    round(N * dst / src); ошибка округления каждого события не
    превышает одного кадра и не накапливается (позиция берётся из
    точного соотношения, а не инкрементом).
    """
    n = len(frames)
    m = int(round(n * dst_hz / src_hz))
    if m <= 0:
        return []
    out = []
    for j in range(m):
        i = (2 * j + 1) * n // (2 * m)      # ближайший кадр источника
        out.append(frames[min(i, n - 1)])
    return out


def dump_notes(frames):
    """Печать списка нот для визуальной проверки."""
    def hz2name(f):
        if f == 0:
            return "-"
        import math
        n = round(12 * math.log2(f / 440.0)) + 69
        return NOTE_NAMES[n % 12] + str(n // 12 - 1)

    prev = None
    run = 0
    out = []
    for fr in frames + [None]:
        key = fr if fr is None else (fr[0], fr[1], fr[2], fr[3])
        if key == prev:
            run += 1
            continue
        if prev is not None:
            out.append("%-4s %-4s %-4s %s x%-3d" % (
                hz2name(prev[0]), hz2name(prev[1]), hz2name(prev[2]),
                "K" if prev[3] == 2 else ("N" if prev[3] else "."), run))
        prev = key
        run = 1
    print("p1    p2    tri   noise длит")
    print("\n".join(out))


def dump_dmc(result):
    """События DMC-канала с абсолютными кадрами (паузы — тоже, как rest)."""
    chans = result["chans"]
    dm = chans[3]
    print("DMC-события (%s):" % (dm.name or "dmc"))
    print("frame  byte  hit_type  duration")
    for start, dur, ev in result["events"][dm]:
        if ev["kind"] == "hit":
            ht = "kick" if ev["hit"] == NOISE_KICK else "snare"
            print("%-6d $%02X   %-8s  %d" % (start, ev["byte"], ht, dur))
        else:
            print("%-6d $%02X   %-8s  %d" % (start, ev["byte"], "rest", dur))


def dump_timeline(result):
    """Единая шкала границ событий всех каналов (по кадрам)."""
    events = result["events"]
    chans = result["chans"]
    n = len(result["frames"])
    ptr = [0] * 4

    def label(ch, ev):
        if ch.kind == "dmc":
            if ev["kind"] == "rest":
                return "REST(%d)" % ev["dur"]
            return ("KICK" if ev["hit"] == NOISE_KICK else "SNARE") \
                + "(%d)" % ev["dur"]
        if ev["kind"] == "rest":
            return "rest(%d)" % ev["dur"]
        return "note(%d)" % ev["dur"]

    print("frame  %-14s %-14s %-14s %s" % ("pulse1", "pulse2", "triangle", "dmc"))
    for f in range(n):
        cols = []
        for i, ch in enumerate(chans):
            evs = events[ch]
            txt = "-"
            if ptr[i] < len(evs) and evs[ptr[i]][0] == f:
                txt = label(ch, evs[ptr[i]][2])
                ptr[i] += 1
            cols.append(txt)
        if any(c != "-" for c in cols):
            print("%-6d %-14s %-14s %-14s %s" % (f, *cols))


def dump_frames_csv(result, path):
    """CSV итоговой покадровой шкалы (после ретайминга — как в .inc)."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("frame,pulse1,pulse2,triangle,noise\n")
        for i, fr in enumerate(result["frames"]):
            f.write("%d,%d,%d,%d,%d\n" % (i, fr[0], fr[1], fr[2], fr[3]))
    print("Покадровая шкала записана: %s (%d кадров)" %
          (path, len(result["frames"])))


def report_fe(result):
    """Диагностика пропусков $FE: участок не должен пересекать границу
    музыкального события — проверяем, что байт сразу после пропуска
    выглядит как начало нового события/команды."""
    if not result["fe_skips"]:
        print("Пропуски $FE: нет")
        return
    for name, skips in result["fe_skips"].items():
        for pc, n, nxt in skips:
            note = ""
            if nxt is None:
                note = "ПРОПУСК В КОНЕЦ ПОТОКА"
            elif nxt >= 0xC0:
                note = "за пропуском — пауза/нота $%02X (граница события)" % nxt
            else:
                note = "за пропуском — байт $%02X" % nxt
            print("$FE в %s: pc=$%04X, пропущено %d байт; %s" %
                  (name, pc, n, note))


def to_steps(frames):
    """Сжатие покадровой последовательности в шаги (divisor-формат ВИ53)."""
    VI = 1500000.0

    def div(f):
        if f <= 0:
            return 0
        d = int(VI / f + 0.5)
        return max(2, min(65535, d))

    steps = []
    prev = None
    run = 0
    for fr in frames + [None]:
        key = fr if fr is None else (div(fr[0]), div(fr[1]), div(fr[2]),
                                     fr[3])
        if key == prev:
            run += 1
            continue
        if prev is not None:
            while run > 255:
                steps.append((255,) + prev)
                run -= 255
            steps.append((run,) + prev)
        prev = key
        run = 1

    # сохранение временной шкалы: сумма длительностей шагов обязана
    # совпадать с числом кадров движка
    total = sum(s[0] for s in steps)
    assert total == len(frames), \
        "to_steps: сумма длительностей %d != кадров %d" % (total, len(frames))
    return steps


def validate_transcription(result):
    """Автоматическая проверка DMC-событий (п.11 ТЗ). Возвращает список
    проблем (пустой — всё в порядке)."""
    problems = []
    chans = result["chans"]
    frames = result["frames"]
    dm = chans[3]
    dmc_events = result["events"][dm]
    n = len(frames)

    # 1) паузы $Cn не генерируют удар
    for start, dur, ev in dmc_events:
        if ev["kind"] == "rest" and (ev["byte"] >> 4) == 0x0C:
            for f in range(start, min(start + dur, n)):
                if frames[f][3] != 0:
                    problems.append("пауза $%02X@%d даёт noise на кадре %d" %
                                    (ev["byte"], start, f))
                    break

    # 2,6) каждый удар присутствует в frames ровно BURST_FRAMES кадрами
    #      (или dur, если событие короче) — и ничто другое noise не даёт.
    #      Проверка в обе стороны покрывает и склейку соседних событий.
    hits = [(start, dur, ev) for start, dur, ev in dmc_events
            if ev["kind"] == "hit"]
    expect = {}
    for start, dur, ev in hits:
        for f in range(start, min(start + min(BURST_FRAMES, dur), n)):
            expect[f] = ev["hit"]
    for f in range(n):
        noise = frames[f][3]
        if f in expect:
            if noise != expect[f]:
                problems.append("кадр %d: ждали noise=%d, получили %d" %
                                (f, expect[f], noise))
        elif noise != 0:
            problems.append("кадр %d: noise=%d без события DMC" % (f, noise))

    # 4) соседние события не склеиваются: старт каждого следующего события
    #    = старт предыдущего + его длительность
    for (s1, d1, _), (s2, _, _) in zip(dmc_events, dmc_events[1:]):
        if s2 != s1 + d1:
            problems.append("DMC: после события @%d (dur %d) следующее @%d" %
                            (s1, d1, s2))

    # 6) сумма длительностей DMC-событий = кадровой шкале канала
    if dmc_events:
        last = dmc_events[-1]
        extent = last[0] + last[1]
        if extent != result["chan_frames"][dm]:
            problems.append("DMC: шкала событий %d != кадров активности %d" %
                            (extent, result["chan_frames"][dm]))

    return problems


def self_test():
    """Внутренние проверки: паузы DMC, границы dur=0/1/2, event/pause
    последовательности, сохранение шкалы в to_steps."""
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    def pulse_freq(hi, octave):
        return round(CPU_CLK / (16.0 * ((TABLE3[hi] >> (4 - octave)) + 1)))

    def sim(ch):
        """Событийная симуляция одного канала: [(start, dur, ev)]."""
        events = []
        t = 0
        while True:
            dur = ch.parse_one()
            if ch.last_event is None:
                break
            events.append((t, dur, ch.last_event))
            t += dur
            if ch.finished:
                break
        return events

    # 1) DMC: dur=1/2, пауза $C2 не даёт удара
    ch = Channel(bytes([0xFB, 0xD3, 0x31, 0x32, 0xC2, 0x31, 0xFF]), "dmc")
    evs = sim(ch)
    check([e["kind"] for _, _, e in evs] == ["hit", "hit", "rest", "hit"],
          "DMC: порядок событий %s" % [e["kind"] for _, _, e in evs])
    check([d for _, d, _ in evs] == [3, 6, 6, 3],
          "DMC: длительности %s" % [d for _, d, _ in evs])
    check([s for s, _, _ in evs] == [0, 3, 9, 15],
          "DMC: старты %s" % [s for s, _, _ in evs])

    # 2) DMC: dur=0 -> base; два удара подряд без склейки
    ch = Channel(bytes([0xFB, 0xD2, 0x30, 0xB0, 0xFF]), "dmc")
    evs = sim(ch)
    check([d for _, d, _ in evs] == [2, 2], "DMC dur=0: %s" % evs)
    check([s for s, _, _ in evs] == [0, 2], "DMC dur=0 старты: %s" % evs)

    # 3) pulse: нота -> нота, dur=1; затем пауза
    ch = Channel(bytes([0xFB, 0x31, 0x41, 0xC1, 0xFF]), "pulse")
    evs = sim(ch)
    check([e["kind"] for _, _, e in evs] == ["note", "note", "rest"],
          "pulse порядок: %s" % [e["kind"] for _, _, e in evs])
    check([s for s, _, _ in evs] == [0, 1, 2], "pulse старты: %s" % evs)

    # 4) пауза -> событие, dur=2
    ch = Channel(bytes([0xFB, 0xC2, 0x32, 0xFF]), "pulse")
    evs = sim(ch)
    check([e["kind"] for _, _, e in evs] == ["rest", "note"],
          "pause->event: %s" % evs)
    check([d for _, d, _ in evs] == [2, 2], "pause->event dur: %s" % evs)

    # 5) полная транскрипция: четыре канала, инварианты шкалы
    dmc = bytes([0xFB, 0xD3, 0x31, 0xC1, 0xB1, 0xFF])
    p1 = bytes([0xFB, 0x32, 0x42, 0x32, 0xFF])     # 6 кадров
    p2 = bytes([0xFB, 0xC2, 0x52, 0xFF])           # пауза + нота
    tr = bytes([0xFB, 0xE1, 0x33, 0xFF])           # 3 кадра
    chans = [Channel(p1, "pulse", "pulse1"), Channel(p2, "pulse", "pulse2"),
             Channel(tr, "triangle", "triangle"), Channel(dmc, "dmc", "dmc")]
    res = transcribe_full(chans)
    frames = res["frames"]
    # dmc: удар(3) + пауза(3) + удар(3) = 9 кадров — шкала до конца dmc
    check(len(frames) == 9, "тестовая шкала: %d кадров" % len(frames))
    # kick на кадрах 0-1, пауза (кадры 3-5), snare на 6-7, кадр 8 чистый
    check(frames[0][3] == NOISE_KICK and frames[1][3] == NOISE_KICK,
          "всплеск kick: %s" % [f[3] for f in frames])
    check(frames[2][3] == 0, "хвост kick длиннее BURST: %s" % frames[2][3])
    check(all(frames[f][3] == 0 for f in (3, 4, 5)),
          "$C1 даёт noise: %s" % [frames[f][3] for f in (3, 4, 5)])
    check(frames[6][3] == NOISE_SNARE and frames[7][3] == NOISE_SNARE,
          "всплеск snare: %s" % [f[3] for f in frames])
    check(frames[8][3] == 0, "хвост шумит: %s" % frames[8][3])
    # burst начинается точно с кадра удара (без сдвига на кадр)
    check(frames[0][3] != 0 and frames[6][3] != 0,
          "сдвиг фазы всплеска")
    problems = validate_transcription(res)
    check(not problems, "validate тестовой шкалы: %s" % problems)
    steps = to_steps(frames)      # внутри assert суммы длительностей
    check(sum(s[0] for s in steps) == len(frames), "to_steps шкала")

    # 6) ретайминг: 6 кадров @60 Гц -> 5 кадров @50 Гц, содержимое —
    #    ближайшие кадры источника, длина точная
    rf = retime([1, 2, 3, 4, 5, 6], 60.0, 50.0)
    check(rf == [1, 2, 4, 5, 6], "retime 60->50: %s" % rf)
    rf9 = retime(list(range(9)), 160.0 / 3.0, 50.0)   # 53.333 -> 50
    check(len(rf9) == 8, "retime 53.33->50 длина: %d" % len(rf9))
    check(retime([7], 60.0, 60.0) == [7], "retime 1/1 не идемпотентен")

    if fails:
        print("SELF-TEST: %d ошибок" % len(fails))
        for m in fails:
            print("  - " + m)
        return 1
    print("SELF-TEST: все проверки пройдены")
    return 0


def emit_c(steps, fname, name, source):
    lines = []
    lines.append(f"/* Автоматически сгенерировано music2inc.py из {source} */")
    lines.append(f"const music_step_t {name}[] = {{")
    for i in range(0, len(steps), 4):
        chunk = steps[i:i + 4]
        lines.append("    " + ", ".join(
            "{%3d,%5d,%5d,%5d,%d}" % s for s in chunk) + ",")
    lines.append("};")
    lines.append(f"const unsigned int {name}_len = {len(steps)};")
    text = "\n".join(lines) + "\n"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(text)
    print("Записано %s: %d шагов" % (fname, len(steps)))


def main():
    ap = argparse.ArgumentParser(
        description="Конвертер дорожек Konami NES-движка (pulse1/pulse2/"
                    "triangle/dmc .bin) в .inc для плеера ВИ53 Вектора-06Ц")
    ap.add_argument("song_dir", nargs="?", default=None,
                    help="папка с pulse1.bin, pulse2.bin, "
                         "triangle.bin, dmc.bin")
    ap.add_argument("-o", "--output", default=None,
                    help="выходной .inc (по умолчанию <имя папки>_music.inc "
                         "в текущем каталоге)")
    ap.add_argument("--tick-hz", type=float, default=60.0,
                    help="частота тика движка игры — источник ретайминга "
                         "(по умолчанию 60; Intro Jackal — 53.333); шкала "
                         "пересчитывается под 50 Гц плеера Вектора")
    ap.add_argument("--dump-notes", action="store_true",
                    help="напечатать список нот")
    ap.add_argument("--dump-dmc", action="store_true",
                    help="события DMC-канала с абсолютными кадрами")
    ap.add_argument("--dump-timeline", action="store_true",
                    help="единая шкала границ событий всех каналов")
    ap.add_argument("--dump-frames", metavar="ФАЙЛ", default=None,
                    help="записать покадровую шкалу (CSV) до to_steps")
    ap.add_argument("--self-test", action="store_true",
                    help="внутренние проверки парсера и границ событий")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.song_dir:
        ap.error("не указана папка с дорожками")
    if not os.path.isdir(args.song_dir):
        sys.exit(f"music2inc: папка не найдена: {args.song_dir}")

    stem = os.path.basename(os.path.normpath(args.song_dir))
    out_path = args.output or f"{stem}_music.inc"
    name = os.path.splitext(os.path.basename(out_path))[0]

    chans = [read_channel(args.song_dir, f, k, os.path.splitext(f)[0])
             for f, k in CHANNEL_FILES]
    result = transcribe_full(chans)
    frames = result["frames"]

    # --- отчёт по каналам и темпу ---
    print("Кадры источника (%g Гц) по каналам:" % args.tick_hz)
    for ch in chans:
        print("  %-8s %5d" % (ch.name, result["chan_frames"][ch]))
    print("  %-8s %5d" % ("total:", len(frames)))
    print("Source duration: %.3f s @ %g Hz" %
          (len(frames) / args.tick_hz, args.tick_hz))

    report_fe(result)

    if args.dump_dmc:
        dump_dmc(result)
    if args.dump_timeline:
        dump_timeline(result)
    if args.dump_notes:
        dump_notes(frames)

    problems = validate_transcription(result)
    if problems:
        print("=== ПРОБЛЕМЫ ВАЛИДАЦИИ DMC ===")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("Валидация DMC: %d событий, нарушений нет" %
          len(result["events"][chans[3]]))

    # --- ретайминг под 50 Гц плеера ---
    frames = retime(frames, args.tick_hz, TARGET_HZ)
    result["frames"] = frames       # итоговая шкала — для --dump-frames
    print("Ретайминг %g Гц -> %g Гц: %d кадров (%.3f с), плеер темп 1/1" %
          (args.tick_hz, TARGET_HZ, len(frames), len(frames) / TARGET_HZ))
    if args.dump_frames:
        dump_frames_csv(result, args.dump_frames)

    steps = to_steps(frames)
    print("Временная шкала сохранена: %d кадров == %d в %d шагах" %
          (len(frames), sum(s[0] for s in steps), len(steps)))
    emit_c(steps, out_path, name, args.song_dir)


if __name__ == "__main__":
    main()
