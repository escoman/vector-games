#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сравнительный анализ shot.wav vs explosion.wav чистым stdlib (без numpy).

Скрипт читает mono PCM16 WAV, считает огибающую по блокам, метрики энергии
(RMS по кадрам), распрежение ширин импульсов PC0 (по нулявым переходам) и
рисует ASCII-осциллограмму огибающей. Используется для отчёта Stage9c.
"""
from __future__ import annotations
import sys, wave, struct, math


def read_wav(path):
    with wave.open(path, "rb") as w:
        rate = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    width = w.getsampwidth()
    if width != 2:
        raise SystemExit(f"{path}: ожидался 16-bit PCM, получен {width*8}-bit")
    s = struct.unpack("<%dh" % (len(raw) // 2), raw)
    return rate, list(s)


def edges(samples):
    """Индексы смен знака (фронты меандра PC0), включая границу с нулём."""
    idx = []
    prev = 1 if samples[0] >= 0 else -1
    for i, v in enumerate(samples):
        cur = 1 if v >= 0 else -1
        if cur != prev:
            idx.append(i)
            prev = cur
    return idx


def pulse_widths_us(edge_idx, rate):
    if len(edge_idx) < 2:
        return []
    return [(edge_idx[i + 1] - edge_idx[i]) / rate * 1e6 for i in range(len(edge_idx) - 1)]


def rms_block(samples, block):
    out = []
    for k in range(0, len(samples), block):
        seg = samples[k:k + block]
        if not seg:
            break
        m = math.sqrt(sum(v * v for v in seg) / len(seg))
        out.append(m)
    return out


def histogram(vals, bins=24):
    if not vals:
        return None, None, None
    lo, hi = min(vals), max(vals)
    hist = [0] * bins
    for v in vals:
        if hi > lo:
            k = int((v - lo) / (hi - lo) * (bins - 1))
        else:
            k = 0
        hist[k] += 1
    return lo, hi, hist


def ascii_pulse_timeline(pw, rate, width=100, height=17, label=""):
    """Осциллограмма тембра: высота столбца = ширина импульса PC0 ( duty ).

    Для 1-битного меандра постоянного амплитуды RMS-огибающая вырождена
    (везде константа), поэтому показываем, как меняются длительности
    импульсов во времени: ровный частый треск (выстрел) против редких
    длинных импульсов-гула (хвост взрыва).
    """
    if not pw:
        return ""
    hi = max(pw) or 1.0
    cols = [int(round(v / hi * (height - 1))) for v in pw]
    n = len(cols)
    if n > width:
        step = n / width
        thin = []
        for c in range(width):
            a = int(c * step); b = max(a + 1, int((c + 1) * step))
            thin.append(max(cols[a:b]))
        cols = thin
    lines = ["", f"  {label}  осциллограмма ширин импульсов "
                 f"({n} имп. -> {len(cols)} ст.; max={hi:.0f} мкс)"]
    for row in range(height - 1, -1, -1):
        line = "".join("\u2588" if c >= row + 1 else " " for c in cols)
        lines.append("  |" + line)
    lines.append("  +" + "-" * len(cols))
    return "\n".join(lines)


def report(path):
    rate, samples = read_wav(path)
    dur_ms = len(samples) / rate * 1000.0
    ei = edges(samples)
    pw = pulse_widths_us(ei, rate)
    block = max(1, int(rate * 0.0005))  # 0.5 мс блок
    env = rms_block(samples, block)
    peak = max(env) or 1
    active_blocks = sum(1 for e in env if e > 0.05 * peak)
    overall_rms = math.sqrt(sum(v * v for v in samples) / len(samples))
    print(f"\n=== {path} ===")
    print(f"  длительность : {dur_ms:.1f} мс   сэмплов {len(samples)} @ {rate} Гц")
    print(f"  фронтов (смена знака): {len(ei)}")
    if pw:
        pw_sorted = sorted(pw)
        print(f"  ширина импульса: median={pw_sorted[len(pw)//2]:.1f} мкс  "
              f"min={pw_sorted[0]:.1f}  max={pw_sorted[-1]:.1f}  "
              f"mean={sum(pw)/len(pw):.1f}")
    print(f"  overall RMS  : {overall_rms:.0f} FS   "
          f"активных блоков (0.5 мс): {active_blocks}/{len(env)}")
    print(ascii_pulse_timeline(pw, rate, label=path.split('/')[-1]))
    return dur_ms, len(ei), (sorted(pw)[len(pw)//2] if pw else 0), overall_rms


def main():
    a = report(sys.argv[1] if len(sys.argv) > 1 else "shot.wav")
    b = report(sys.argv[2] if len(sys.argv) > 2 else "explosion.wav")
    print("\n=== СРАВНЕНИЕ ===")
    print(f"  {'метрика':22s} {'shot':>12s} {'explosion':>12s}")
    print(f"  {'длительность, мс':22s} {a[0]:12.1f} {b[0]:12.1f}")
    print(f"  {'фронтов':22s} {a[1]:12d} {b[1]:12d}")
    print(f"  {'median импульса, мкс':22s} {a[2]:12.1f} {b[2]:12.1f}")
    print(f"  {'RMS (FS)':22s} {a[3]:12.0f} {b[3]:12.0f}")


if __name__ == "__main__":
    main()
