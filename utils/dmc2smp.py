#!/usr/bin/env python3
#
# dmc2smp.py — генерация семплов ударных .smp для drums.asm из wav,
# полученных озвучкой DPCM-образцов, извлечённых из NES-рома.
#
# Формат .smp (lib/drums.asm, drum_sample_play): байт N — число кадров
# 50 Гц, затем N пар (R6, R10) — период шума и громкость канала C AY.
#
# wav делится на N кадров по 20 мс; в каждом кадре (с удалением
# постоянной составляющей) считается:
#   - RMS        -> громкость R10 (максимум по файлу = 15);
#   - центроид   -> период шума R6 = round(K / центроид), шум AY
#     тем «ниже», чем больше R6; K калибруется на слух (по умолчанию
#     24000 Гц*ед.: центроид ~1300 Гц -> R6 18, ~2800 Гц -> R6 9).
#
# Использование:
#   python3 utils/dmc2smp.py <in.wav> <out.smp> --frames N [--k 24000]
#
import argparse
import math
import sys
import wave


def frame_stats(data, sr, frames):
    """RMS и спектральный центроид каждого из frames окон."""
    win = math.ceil(len(data) / frames)
    stats = []
    for f in range(frames):
        seg = data[f * win:(f + 1) * win]
        if not seg:
            break
        mean = sum(seg) / len(seg)
        seg = [s - mean for s in seg]
        rms = math.sqrt(sum(s * s for s in seg) / len(seg))
        length = len(seg)
        total, centroid = 0.0, 0.0
        for k in range(1, length // 2):
            re = sum(s * math.cos(2 * math.pi * k * i / length)
                     for i, s in enumerate(seg))
            im = sum(s * math.sin(2 * math.pi * k * i / length)
                     for i, s in enumerate(seg))
            amp = math.hypot(re, im)
            total += amp
            centroid += amp * k * sr / length
        centroid = centroid / total if total > 0 else 1.0
        stats.append((rms, centroid))
    return stats


def main():
    ap = argparse.ArgumentParser(description="wav -> .smp (шум AY)")
    ap.add_argument("wav")
    ap.add_argument("smp")
    ap.add_argument("--frames", type=int, required=True,
                    help="число кадров 50 Гц в семпле")
    ap.add_argument("--k", type=float, default=24000.0,
                    help="калибровка R6 = K / центроид (по умолчанию 24000)")
    args = ap.parse_args()

    with wave.open(args.wav) as w:
        sr, n = w.getframerate(), w.getnframes()
        data = [b - 128 for b in w.readframes(n)]
    stats = frame_stats(data, sr, args.frames)
    if not stats:
        sys.exit(f"{args.wav}: пустой файл")
    peak = max(r for r, _ in stats)
    if peak <= 0:
        sys.exit(f"{args.wav}: тишина")

    pairs = []
    for rms, centroid in stats:
        vol = max(1, round(rms / peak * 15))
        r6 = max(1, min(31, round(args.k / centroid)))
        pairs.append((r6, vol))

    body = bytes([len(pairs)] + [b for p in pairs for b in p])
    with open(args.smp, "wb") as out:
        out.write(body)
    print(f"{args.wav} ({n / sr * 1000:.0f} мс, {len(pairs)} кадра) -> "
          f"{args.smp}: " +
          " ".join(f"(R6={r6},R10={vol})" for r6, vol in pairs))


if __name__ == "__main__":
    main()
