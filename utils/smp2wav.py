#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smp2wav.py — синтез WAV-превью семплов .smp (шумовой канал AY-3-8910).

Формат .smp: байт N — число кадров 50 Гц, затем N пар (R6, R10) —
период шума и громкость канала C AY-3-8910.

Скрипт моделирует генератор шума AY-3-8910 (12-битный LFSR с
обратной связью биты 0 и 3) и записывает результат в WAV.

Частота шума: F = AY_CLK / (32 * (R6 + 1)), AY_CLK = 1750000 Гц.

Использование:
    python3 utils/smp2wav.py music-roms/jackal/music/samples
    python3 utils/smp2wav.py music-roms/jackal/music/samples/kick.smp
    python3 utils/smp2wav.py music-roms/jackal/music/samples -o /tmp/wav
"""

import argparse
import math
import os
import struct
import sys
import wave

AY_CLK = 1750000.0

# Логарифмическая кривая громкости AY-3-8910 (16 шагов, 0 = тишина).
# Приближение реального поведения чипа: ~2 дБ на шаг.
def ay_volume(v):
    """Громкость AY (0..15) -> амплитуда (0.0..1.0)."""
    if v == 0:
        return 0.0
    return (math.pow(2.0, v / 4.0) - 1.0) / 15.0


def synthesize(smp_data, sample_rate):
    """Моделирование шума AY-3-8910 по кадрам .smp -> список sample [-1, 1]."""
    n_frames = smp_data[0]
    frames = []
    for i in range(n_frames):
        r6 = smp_data[1 + i * 2]
        r10 = smp_data[2 + i * 2]
        frames.append((r6 & 0x1F, r10 & 0x0F))

    samples_per_frame = sample_rate // 50
    period_max = 2 * (n_frames * samples_per_frame + 64)
    buf = [0.0] * period_max
    total = 0

    lfsr = 1                          # 12-битный сдвиговый регистр
    noise_counter = 0
    cur_r6 = 255                      # force reload on first frame
    cur_vol = 0.0
    out_level = 0                     # текущий выходnoise (0 или 1)

    for frame_idx, (r6, vol_idx) in enumerate(frames):
        vol = ay_volume(vol_idx)
        frame_start = frame_idx * samples_per_frame

        for s in range(samples_per_frame):
            # Плавная смена громкости между кадрами (линейная интерполяция)
            if frame_idx < n_frames - 1:
                next_vol = ay_volume(frames[frame_idx + 1][1])
                t = s / samples_per_frame
                eff_vol = cur_vol + (next_vol - cur_vol) * t
            else:
                # Затухание в последнем кадре до тишины
                t = s / samples_per_frame
                eff_vol = cur_vol * (1.0 - t)

            # Смена периода шума — только на границе кадра (как в реальности)
            if s == 0 and r6 != cur_r6:
                cur_r6 = r6
                noise_counter = 0

            # Генератор шума: обратный отсчёт, при 0 — сдвиг LFSR
            if noise_counter >= cur_r6:
                noise_counter = 0
                feedback = (lfsr ^ (lfsr >> 3)) & 1
                lfsr = (lfsr >> 1) | (feedback << 11)
                out_level = lfsr & 1
            noise_counter += 1

            sample = (2.0 * out_level - 1.0) * eff_vol
            buf[total] = sample
            total += 1

    return buf[:total]


def write_wav(path, samples, sample_rate):
    """Запись 16-бит mono WAV."""
    with wave.open(path, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            w.writeframes(struct.pack('<h', int(clamped * 32767)))


def process_one(smp_path, wav_path, sample_rate):
    with open(smp_path, 'rb') as f:
        data = f.read()
    if len(data) < 1:
        print(f"  пропущен {smp_path}: пустой файл")
        return False
    n_frames = data[0]
    expected = 1 + n_frames * 2
    if len(data) < expected:
        print(f"  пропущен {smp_path}: ожидалось {expected} байт, есть {len(data)}")
        return False

    samples = synthesize(data, sample_rate)
    write_wav(wav_path, samples, sample_rate)
    dur_ms = len(samples) / sample_rate * 1000
    pairs = ' '.join(f'(R6={data[1+i*2]},R10={data[2+i*2]})'
                     for i in range(n_frames))
    print(f"  {os.path.basename(smp_path):30s} -> {os.path.basename(wav_path):34s}"
          f" {n_frames} кадр(ов), {dur_ms:.0f} мс: {pairs}")
    return True


def main():
    ap = argparse.ArgumentParser(
        description='.smp -> WAV (симуляция шума AY-3-8910)')
    ap.add_argument('input',
                    help='файл .smp или папка с .smp')
    ap.add_argument('-o', '--output', default=None,
                    help='папка для WAV (по умолчанию — рядом с .smp)')
    ap.add_argument('--rate', type=int, default=44100,
                    help='частота дискретизации (по умолчанию 44100)')
    args = ap.parse_args()

    if os.path.isfile(args.input):
        files = [args.input]
        out_dir = args.output or os.path.dirname(args.input)
    elif os.path.isdir(args.input):
        files = sorted(os.path.join(args.input, f)
                       for f in os.listdir(args.input)
                       if f.endswith('.smp'))
        out_dir = args.output or args.input
    else:
        sys.exit(f'{args.input}: нет такого файла или папки')

    if not files:
        sys.exit('.smp файлы не найдены')

    os.makedirs(out_dir, exist_ok=True)
    print(f'AY_CLK = {AY_CLK:.0f} Гц, sample rate = {args.rate} Гц\n')

    ok = 0
    for smp_path in files:
        base = os.path.splitext(os.path.basename(smp_path))[0]
        wav_path = os.path.join(out_dir, base + '.wav')
        if process_one(smp_path, wav_path, args.rate):
            ok += 1

    print(f'\nЗаписано {ok} WAV файл(ов) в {out_dir}')


if __name__ == '__main__':
    main()
