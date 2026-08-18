# -*- coding: utf-8 -*-
"""
music2inc.py — конвертер извлечённых дорожек Konami NES-движка в .inc
для ROM Вектора-06Ц (плеер на КР580ВИ53).

Использование:
    python3 music2inc.py <папка_с_bin> [-o выход.inc] [--tick-hz Гц]
                         [--dump-notes]

  папка_с_bin — папка с каналами pulse1.bin, pulse2.bin, triangle.bin,
                dmc.bin (результат работы extract_music.py);
  -o          — выходной .inc (по умолчанию <папка>_music.inc в текущем
                каталоге); имя массива = имя файла без расширения
                (intro_music.inc -> intro_music[], intro_music_len);
  --tick-hz   — частота тика движка исходной игры, только для оценки
                длительности в секундах в отчёте (по умолчанию 60);
  --dump-notes— печать списка нот для визуальной проверки.

Модель звукового движка Konami (по дизассемблеру Jackal, Bank0.ASM):
  * Движок покадровый; темп игры задаётся пропуском кадров снаружи
    (например, Intro Jackal: 1 из 9 кадров пропускается -> 53.33 Гц).
    Конвертер выдаёт один шаг на тик движка; реальная скорость —
    за плеером ROM (music_tick в кадровом прерывании 50 Гц).
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
      $Cn          - пауза, длительность n*base (n=0 -> base)
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


class Channel:
    def __init__(self, data, kind):
        self.d = data
        self.kind = kind            # 'pulse' | 'triangle' | 'dmc'
        self.pc = 0
        # движок инициализирует базу длительности и октаву нулём; для
        # triangle-канала октавный сдвиг по умолчанию = 1 (басовый диапазон)
        self.dur_base = 0 if kind == "dmc" else 1
        self.octave = 1 if kind == "triangle" else 0
        self.loop_base = 0          # позиция после $FB
        self.rep_cnt = 0
        self.finished = False
        self.last_hit = 0
        # текущее звучащее состояние
        self.period = None          # NES-период
        self.dur_left = 0           # кадров до следующей команды

    def parse_one(self):
        """Разбирает одно событие; возвращает длительность в кадрах."""
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
                        return 0
                    # .bin уже содержит повторный участок внутри блока,
                    # поэтому просто пропускаем $FE n
                    self.pc += 2 + n
                    continue
                if b == 0xFF:
                    self.finished = True
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
            if self.kind == "dmc":
                self.last_hit = hi
                self.period = None
                return dur

            if hi == 0x0C:
                # пауза
                self.period = None
                return dur

            idx = hi
            self.period = TABLE3[idx] >> (4 - self.octave)
            return dur

        self.finished = True
        return 0

    def freq(self):
        """Частота в Гц для текущего периода."""
        if self.period is None:
            return 0.0
        p = int(self.period)
        if self.kind == "triangle":
            return CPU_CLK / (32.0 * (p + 1))
        return CPU_CLK / (16.0 * (p + 1))


def read_channel(song_dir, fname, kind):
    path = os.path.join(song_dir, fname)
    if not os.path.isfile(path):
        print(f"  {fname}: отсутствует — канал пустой", file=sys.stderr)
        return Channel(b"\xFF", kind)
    return Channel(open(path, "rb").read(), kind)


def transcribe(song_dir):
    p1 = read_channel(song_dir, "pulse1.bin", "pulse")
    p2 = read_channel(song_dir, "pulse2.bin", "pulse")
    tr = read_channel(song_dir, "triangle.bin", "triangle")
    dm = read_channel(song_dir, "dmc.bin", "dmc")

    # Покадровая симуляция до конца самого длинного канала:
    # на каждый кадр — (f1, f2, f3, noise)
    frames = []
    noise_left = 0
    noise_kind = 0
    frame = 0

    ev = {}               # канал -> оставшиеся кадры события
    for ch in (p1, p2, tr, dm):
        dur = ch.parse_one()
        ev[ch] = dur
        if ch is dm and dur > 0:
            noise_left = min(BURST_FRAMES, dur)
            noise_kind = NOISE_KICK if dm.last_hit < 0x08 else NOISE_SNARE

    while frame < MAX_FRAMES:
        if all(c.finished for c in (p1, p2, tr, dm)) and \
           all(ev[c] == 0 for c in ev):
            break

        frames.append((round(p1.freq()), round(p2.freq()),
                       round(tr.freq()), noise_kind if noise_left > 0 else 0))
        frame += 1

        for ch in (p1, p2, tr, dm):
            if ev[ch] > 0:
                ev[ch] -= 1
            if ev[ch] == 0 and not ch.finished:
                dur = ch.parse_one()
                ev[ch] = dur
                if ch is dm and dur > 0:
                    noise_left = min(BURST_FRAMES, dur)
                    noise_kind = NOISE_KICK if dm.last_hit < 0x08 else NOISE_SNARE
        if noise_left > 0:
            noise_left -= 1

    return frames


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
    return steps


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
    ap.add_argument("song_dir", help="папка с pulse1.bin, pulse2.bin, "
                                     "triangle.bin, dmc.bin")
    ap.add_argument("-o", "--output", default=None,
                    help="выходной .inc (по умолчанию <имя папки>_music.inc "
                         "в текущем каталоге)")
    ap.add_argument("--tick-hz", type=float, default=60.0,
                    help="частота тика движка игры для оценки длительности "
                         "(по умолчанию 60; Intro Jackal — 53.33)")
    ap.add_argument("--dump-notes", action="store_true",
                    help="напечатать список нот")
    args = ap.parse_args()

    if not os.path.isdir(args.song_dir):
        sys.exit(f"music2inc: папка не найдена: {args.song_dir}")

    stem = os.path.basename(os.path.normpath(args.song_dir))
    out_path = args.output or f"{stem}_music.inc"
    name = os.path.splitext(os.path.basename(out_path))[0]

    frames = transcribe(args.song_dir)
    print("Кадров движка: %d (%.2f с при %g Гц тике)" %
          (len(frames), len(frames) / args.tick_hz, args.tick_hz))
    if args.dump_notes:
        dump_notes(frames)
    steps = to_steps(frames)
    emit_c(steps, out_path, name, args.song_dir)


if __name__ == "__main__":
    main()
