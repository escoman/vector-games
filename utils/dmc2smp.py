#!/usr/bin/env python3
#
# dmc2smp.py — генерация шумовых семплов .smp для drums.asm из WAV.
#
# Исторически — озвучка DPCM-образцов, извлечённых из NES-рома; теперь
# читает любой PCM WAV (8/16 бит, mono/stereo, любая частота), поэтому годится
# и для снятия конвертов с записей оригинала (nu_pogodi: catch/miss/gameover).
#
# Формат .smp (lib/snd/drums.asm, drum_sample_play): байт N — число кадров
# 50 Гц (N <= 255 => максимум 5.1 с), затем N пар (R6, R10) — период шума
# и громкость канала C AY.
#
# Обработка: WAV -> mono, окно по 20 мс (50 Гц = частота drum_tick); в каждом
# кадре (с удалением постоянной составляющей) считается:
#   - RMS      -> громкость R10 (максимум по файлу = 15);
#   - центроид -> период шума R6 = round(K / центроид), шум AY тем «ниже»,
#     чем больше R6; K калибруется на слух (по умолчанию 24000 Гц*ед.:
#     центроид ~1300 Гц -> R6 18, ~2800 Гц -> R6 9).
#
# Число кадров: --frames N (N равных окон на всю длительность, как раньше)
# или auto/не указано — ровно 50 кадров в секунду (длительность как в оригинале).
# --gate доли от пика: кадры тишины получают R10=0 и обрезаются по краям
# (по умолчанию 0 — как в прежнем поведении, минимальная громкость 1).
#
# Использование:
#   python3 utils/dmc2smp.py <in.wav> <out.smp> [--frames N] [--k 24000]
#   python3 utils/dmc2smp.py <in.wav> --fixed-r6 12 -v
#   python3 utils/dmc2smp.py src/sounds/ -o src/sounds/smp/ -g 0.03
#   python3 utils/dmc2smp.py --self-test
#
import argparse
import array
import math
import os
import struct
import sys
import wave

FRAME_HZ = 50.0
MAX_FRAMES = 255            # число кадров в формате .smp — один байт


def read_wav(path):
    """WAV -> (список отсчётов float, частота). PCM 8/16 бит, mono/stereo."""
    with wave.open(path) as w:
        ch, sw, sr, n = (w.getnchannels(), w.getsampwidth(),
                         w.getframerate(), w.getnframes())
        raw = w.readframes(n)
    if sw == 2:
        a = array.array('h')
        a.frombytes(raw[:len(raw) & ~1])
        if sys.byteorder == 'big':
            a.byteswap()
        data = [x / 32768.0 for x in a]
    elif sw == 1:
        data = [(b - 128) / 128.0 for b in raw]
    else:
        sys.exit('%s: битность %d не поддерживается' % (path, sw * 8))
    if ch == 2:
        data = [(data[i] + data[i + 1]) * 0.5 for i in range(0, len(data) - 1, 2)]
    elif ch > 2:
        sys.exit('%s: %d канала(ов), нужен mono или stereo' % (path, ch))
    return data, sr


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


def auto_frames(n, sr):
    """Число кадров 50 Гц на длительность сигнала (1..MAX_FRAMES)."""
    return max(1, min(MAX_FRAMES, int(round(n / float(sr) * FRAME_HZ))))


def build_smp(stats, gate=0.0, fixed_r6=None, k=24000.0):
    """(rms, центроид) по кадрам -> список пар (R6, R10).

    gate > 0: кадры тишины (rms/пик < gate) получают R10=0, ведущие и
    замыкающие такие кадры обрезаются. gate == 0 — прежнее поведение:
    минимальная громкость 1, ничего не обрезается."""
    if not stats:
        return []
    peak = max(r for r, _ in stats)
    if peak <= 0:
        return []
    pairs = []
    for rms, centroid in stats:
        r6 = (fixed_r6 if fixed_r6 is not None
              else max(1, min(31, round(k / centroid))))
        if gate > 0.0:
            pairs.append((r6, 0 if rms / peak < gate else max(1, round(rms / peak * 15))))
        else:
            pairs.append((r6, max(1, round(rms / peak * 15))))
    if gate > 0.0:
        while pairs and pairs[0][1] == 0:
            pairs.pop(0)
        while pairs and pairs[-1][1] == 0:
            pairs.pop()
    return pairs[:MAX_FRAMES]


def convert(path, frames=None, gate=0.0, fixed_r6=None, k=24000.0, verbose=False):
    """WAV -> байты .smp. Возвращает (blob, число_кадров, обложено_ли)."""
    data, sr = read_wav(path)
    if not data:
        sys.exit('%s: пустой файл' % path)
    n_frames = auto_frames(len(data), sr) if not frames else frames
    stats = frame_stats(data, sr, n_frames)
    if not stats:
        sys.exit('%s: пустой сигнал' % path)
    pairs = build_smp(stats, gate, fixed_r6, k)
    trimmed = len(pairs) < len(stats)
    if verbose:
        print('  кадр  R6  R10')
        for i, (r6, vol) in enumerate(pairs):
            print('  %-4d  %-3d %-3d' % (i, r6, vol))
    return bytes([len(pairs)] + [b for p in pairs for b in p]), len(pairs), trimmed


def self_test():
    """Формат, декодирование 8/16 бит и стерео, авто-кадры, порог/обрезка."""
    import tempfile
    sr = 8000
    tmp = tempfile.mkdtemp(prefix='dmc2smp_')

    def write(name, samples, width=2, ch=1):
        p = os.path.join(tmp, name)
        with wave.open(p, 'wb') as w:
            w.setnchannels(ch)
            w.setsampwidth(width)
            w.setframerate(sr)
            if width == 2:
                w.writeframes(b''.join(struct.pack('<h', int(s)) for s in samples))
            else:
                w.writeframes(bytes(int(s) + 128 for s in samples))
        return p

    # 16-битная 2 кГц синусоида на 0.2 с = 10 кадров авто; амплитуда растёт
    n = sr // 5
    amp = [6000.0 * (i + 1) / n for i in range(n)]
    sine16 = [math.sin(2 * math.pi * 2000 * i / sr) * a for i, a in enumerate(amp)]
    p16 = write('sine16.wav', sine16)
    data, got_sr = read_wav(p16)
    assert got_sr == sr and len(data) == n, (got_sr, len(data))
    blob, nf, _ = convert(p16)
    assert nf == 10 and blob[0] == 10, nf
    assert len(blob) == 1 + 2 * nf, len(blob)
    vols = [blob[2 + 2 * i] for i in range(nf)]
    assert vols == sorted(vols) and vols[-1] == 15, vols
    # центроид ~2000 Гц -> R6 ~ k/2000 = 12
    assert abs(blob[1] - 12) <= 2, blob[1]

    # стерео: каналы в противофазе -> mono почти тишина, кадров 0 после gate
    stereo = [v for s in sine16 for v in (s, -s)]
    p_st = write('anti.wav', stereo, ch=2)
    d_st, _ = read_wav(p_st)
    assert len(d_st) == n and abs(sum(d_st) / len(d_st)) < 1e-6, 'mono из стерео'
    _, nf_g, trimmed = convert(p_st, gate=0.03)
    assert nf_g == 0 and trimmed, (nf_g, trimmed)

    # 8-бит mono + явное число окон (прежнее поведение)
    p8 = write('lo8.wav', [x / 300.0 for x in sine16], width=1)
    blob8, nf8, _ = convert(p8, frames=4)
    assert nf8 == 4 and len(blob8) == 9, (nf8, len(blob8))

    # fixed-r6 применяется ко всем кадрам
    blobf, nff, _ = convert(p16, fixed_r6=7)
    assert all(blobf[1 + 2 * i] == 7 for i in range(nff)), blobf

    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    print('self-test OK')
    return 0


def main():
    ap = argparse.ArgumentParser(description="wav -> .smp (шум AY)")
    ap.add_argument("wav", nargs='?', help="файл .wav или каталог с .wav")
    ap.add_argument("smp", nargs='?', help="выходной .smp (для одного файла)")
    ap.add_argument("--frames", type=int, default=None,
                    help="число кадров 50 Гц; по умолчанию — по длительности")
    ap.add_argument("--k", type=float, default=24000.0,
                    help="калибровка R6 = K / центроид (по умолчанию 24000)")
    ap.add_argument("-g", "--gate", type=float, default=0.0,
                    help="порог тишины как доля от пика (0 — не обрезать)")
    ap.add_argument("--fixed-r6", type=int, default=None,
                    help="зафиксировать период шума 1..31 на всех кадрах")
    ap.add_argument("-o", "--out", help="каталог для пакетного режима")
    ap.add_argument("-v", "--verbose", action='store_true',
                    help="таблица кадров в отчёт")
    ap.add_argument("--self-test", action='store_true',
                    help="проверка декодирования, кадров и формата")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.wav:
        ap.error('нужен .wav (или каталог) либо --self-test')
    if args.fixed_r6 is not None and not 1 <= args.fixed_r6 <= 31:
        ap.error('--fixed-r6 вне диапазона 1..31')
    if args.frames is not None and not 1 <= args.frames <= MAX_FRAMES:
        ap.error('--frames вне диапазона 1..%d' % MAX_FRAMES)

    is_dir = os.path.isdir(args.wav)
    sources = (sorted(os.path.join(args.wav, f) for f in os.listdir(args.wav)
                      if f.lower().endswith('.wav')) if is_dir
               else [args.wav])
    if not sources:
        sys.exit('%s: нет .wav' % args.wav)
    if is_dir and args.smp:
        sys.exit('для каталога выход задавать через -o, не позиционно')

    total = 0
    for src in sources:
        blob, nf, trimmed = convert(src, args.frames, args.gate,
                                    args.fixed_r6, args.k, args.verbose)
        if is_dir:
            outdir = args.out or (args.smp if args.smp else '.')
            os.makedirs(outdir, exist_ok=True)
            out = os.path.join(
                outdir, os.path.splitext(os.path.basename(src))[0] + '.smp')
        else:
            out = args.smp or args.out or \
                os.path.splitext(src)[0] + '.smp'
        if not nf:
            print('%s: после обрезки тишины не осталось кадров — семпл пуст'
                  % os.path.basename(src))
        with open(out, 'wb') as f:
            f.write(blob)
        total += len(blob)
        print('%s (%.0f мс, %d кадр(ов), %d Б%s) -> %s: %s' % (
            src, nf * 1000.0 / FRAME_HZ, nf, len(blob),
            ', подрезано' if trimmed else '', out,
            ' '.join('(R6=%d,R10=%d)' % (blob[1 + 2 * i], blob[2 + 2 * i])
                     for i in range(min(nf, 8))) +
            (' …' if nf > 8 else '')))
    if is_dir:
        print('всего байт в .smp: %d' % total)


if __name__ == "__main__":
    main()
