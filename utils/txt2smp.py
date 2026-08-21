#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
txt2smp.py — синтез стартовых конвертов ударных .smp из параметров
шумового канала NES-экспорта (track_*.txt).

Формат .smp (drums.asm, drum_sample_play): байт N — число кадров 50 Гц,
затем N пар (R6, R10) — период шума и громкость канала C AY-3-8910.

Алгоритм: для каждого типа ударных собираются все события Noise-секции
во всех треках, вычисляются медианные параметры (индекс шума NES,
громкость, длительность), и из них детерминированно строится AY-конверт:
  * R6 — из периода шума NES (таблица NES_PERIOD) пропорционально
    периоду AY; малый индекс = высокий шум = малый R6;
  * R10 — громкость NES как есть (0..15), с линейным затуханием;
  * число кадров — из длительности: ceil(dur*50) + 1 (атака + хвост).

DPCM-события (dmc0_kick / dmc1_snare) уже представлены существующими
samples/kick.smp и samples/snare.smp — скрипт их НЕ перезаписывает,
шумовой тип 'kick' тоже использует существующий kick.smp (реальный
DMC-сэмпл — более аутентичен, чем синтез).

Использование:
    python3 utils/txt2smp.py music-roms/jackal/music_txt \\
            -o music-roms/jackal/music/samples [--force]

После запуска файлы .smp можно править вручную (формат простой:
байты R6/R10 по кадрам 50 Гц).
"""

import argparse
import os
import re
import statistics
import sys

# Таблица периодов шума NES (NTSC), индекс 0..14
NES_PERIOD = [4, 8, 16, 32, 64, 96, 128, 160, 202, 254,
              380, 508, 762, 1016, 2034]
CPU_CLK = 1789773.0           # NES NTSC
AY_CLK = 1750000.0            # AY-3-8910 Вектора-06Ц


def scan(txt_path):
    """Собрать параметры Noise-событий по типам ударных."""
    stats = {}
    sec = None
    for ln in open(txt_path, encoding='utf-8').read().splitlines():
        if re.match(r'^(Square|Triangle|Noise|DPCM)', ln):
            sec = ln.split('(')[0]
            continue
        if sec == 'Noise' and ln[:1].isdigit():
            p = ln.split()
            if len(p) < 5:
                continue
            t = p[4]
            stats.setdefault(t, []).append((int(p[2]), int(p[3]),
                                            float(p[1])))
    return stats


def synthesize(params):
    """Из параметров (noise_idx, vol, dur) -> список (R6, R10)."""
    idx = params[0][0]                    # индекс шума NES (у типа один)
    vols = [v for _, v, _ in params]
    durs = [d for _, _, d in params]
    vol = statistics.median(vols)
    dur = statistics.median(durs)
    # R6: период шума NES -> AY R6 пропорционально периоду
    p = NES_PERIOD[idx]
    r6 = max(0, min(31, round(AY_CLK * p / (16 * CPU_CLK)) - 1))
    # число кадров: атака по длительности + 1 кадр затухания
    n = max(2, round(dur * 50) + 1)
    frames = []
    for i in range(n):
        decay = (n - i) / n                 # 1.0 -> ~1/n
        v = max(1, round(vol * decay))
        frames.append((r6, v))
    return frames


def write_smp(path, frames):
    body = bytes([len(frames)] + [b for r6, v in frames for b in (r6, v)])
    with open(path, 'wb') as f:
        f.write(body)


def main():
    ap = argparse.ArgumentParser(description='TXT -> .smp ударных')
    ap.add_argument('txt_dir', help='папка с track_*.txt')
    ap.add_argument('-o', '--output', required=True,
                    help='папка для samples/')
    ap.add_argument('--force', action='store_true',
                    help='перезаписать существующие .smp')
    args = ap.parse_args()

    if not os.path.isdir(args.txt_dir):
        sys.exit(f'{args.txt_dir}: не папка')
    os.makedirs(args.output, exist_ok=True)

    # собираем параметры по всем трекам
    merged = {}
    for fn in sorted(os.listdir(args.txt_dir)):
        if fn.startswith('track_') and fn.endswith('.txt'):
            for k, v in scan(os.path.join(args.txt_dir, fn)).items():
                merged.setdefault(k, []).extend(v)

    # шумовой 'kick' и 'snare' — реальные DMC-сэмплы, не синтезируем
    skip = {'kick', 'snare'}
    wrote, skipped = [], []
    for name, params in sorted(merged.items()):
        if name in skip:
            skipped.append(name)
            continue
        out = os.path.join(args.output, name + '.smp')
        if os.path.isfile(out) and not args.force:
            skipped.append(name)
            continue
        frames = synthesize(params)
        write_smp(out, frames)
        wrote.append((name, frames))

    print(f'Записано {len(wrote)} новых .smp:')
    for name, frames in wrote:
        pairs = ' '.join(f'({r6},{v})' for r6, v in frames)
        print(f'  {name:22s} {len(frames)} кадр(ов): {pairs}')
    if skipped:
        print(f'Пропущено (существуют): {", ".join(skipped)}')


if __name__ == '__main__':
    main()
