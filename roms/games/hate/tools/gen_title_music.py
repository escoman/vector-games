#!/usr/bin/env python3
"""gen_title_music.py — ВСЯ мелодия заставки H.A.T.E. для Вектора-06Ц.

Источник — `assets/title_music.txt`, лог ВСЕХ переключений динамика ZX
(`t_zx frame pc value`), снятый прогоном настоящего плеера $8000-$85C5
в SkoolKit (см. zx-disasm/games/hate/SOUND.MD). Формулы периода в
оригинале нет: полупериод задаёт длина пути диспетчера Z80, поэтому
партитура здесь — ИЗМЕРЕННЫЕ интервалы, а не пересчёт байтов периода.

ЧТО ИГРАЕТ ОРИГИНАЛ (разобрано по логу, 38.5 с, 22138 переключений):

  * голос A ($82D1/$82D9) и голос B ($8333/$833B) — ДВА генератора
    «узкого импульса»: высокий уровень ~300 тактов ZX, низкий — период
    минус эти 300. Периоды у обоих плавно-ступенчато меняются по партитуре
    (94 Гц → 113 → 76 → 85 …), то есть это и есть мелодия;
  * клик ($836A/$8375) — импульс 2 мс каждые 0.2976 с (метроном/ритм);
  * шум ($8389) — 44 вспышки по 77 переключений, ровно через 0.7988 с,
    два пропуска (через 19 и через 42 вспышки — там пауза в 3 периода);
  * тональные семейства $83A6/$83B9/$83D1 — свипы аттракт-демо; их
    наложение на голоса не воспроизводится (в партитуру не входят).

ПОЧЕМУ НЕ ЦЕПОЧКА ФРОНТОВ. Прежний экспорт был цепочкой (задержка,
уровень) на каждый фронт: 3 байта на фронт, 22 тыс. фронтов — 65 КБ,
то есть физически не влезало в ROM, и в него попал только первый цикл
(3.2 с). Здесь наоборот: интервалы не перечислены, а ВЫЧИСЛЯЮТСЯ
плеером из партитуры (период + сколько импульсов этим периодом), как
в оригинале. Периоды отфильтрованы от дрожания кадровой синхронизации
(медиана по 5 импульсам) и сжаты RLE с допуском 1.5 %: примерно 1 %
по высоте — это 17 центов, на слух неразличимо, а данных в 20 раз
меньше. Цена решения — «пропущенные проходы» оригинала (каждый 10-16-й
интервал растянут в 1.6 раза) в модель не входят: они артефакт
кадрового планировщика Z80, а не партитура.

ФОРМАТ ДАННЫХ (include/title_music.asm), СОГЛАСОВАН С include/beep.asm:

    mus_a/mus_b/mus_c — по 3 байта на запись: счётчик импульсов,
        период (мл. байт, ст. байт) в единицах UNIT_T; 0 — конец
        скрипта (плеер переходит к его началу);
    mus_np — период слотов шума в единицах UNIT_T (16 бит);
    mus_n  — по 2 байта на запись: сколько слотов и признак
        «играть вспышку» (1) или «пропустить» (0); 0 — конец;
    mus_nz — рисунок вспышки: число шагов, далее интервалы в тиках
        по BURST_TICK тактов (плеер в каждом шаге тратит BURST_STEP).

Использование:
    python3 tools/gen_title_music.py            # -> include/title_music.asm
    python3 tools/gen_title_music.py --stats    # + разбор в stdout
"""

import argparse
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ZX_HZ = 3_500_000
CPU_HZ = 3_000_000

# ВРЕМЯ НА ВЕКТОРЕ. Такты КР580ВМ80А здесь не номинальные, а РЕАЛЬНО
# ЗАНИМАЕМЫЕ: контроллер видео придерживает процессор, поэтому короткая
# команда занимает целое число 4-тактовых окон (v06c-emu, i8080.cpp:
# cpu_cycles -> v_cycles): 4->4, 5->8, 7->8, 10->12, 13->16, 16->20,
# 17->24. Поэтому цикл задержки beep.asm (dcx d / mov a,e / ora d / jnz)
# = 8+8+4+12 = 32 такта, а не 24. Проверено на эмуляторе по лучу:
# 1 такт = 4 v_cycle.
UNIT_T = 128            # единица счётчиков плеера, тактов Вектора (42.7 мкс)
BEAT_T = 32             # шаг цикла beat_delay: он же шаг скважности
BURST_STEP = 60         # накладные расходы одного шага вспышки шума, такты
BURST_TICK = 20         # шаг цикла dcr b / jnz внутри вспышки, такты
FIRE_BASE = 8           # цена импульса сверх скважности, биты по BEAT_T
                        # (beep.asm: ПИА + вызов задержки + spent ~260 такта)

MEDIAN_WIN = 5          # медианный фильтр по импульсам
TOL = 0.015             # допуск RLE по периоду (1.5 % = 26 центов)
HYST = 3                # сколько подряд «выбросов» считать новой нотой
OUTLIER = 1.25          # интервал длиннее медианы на 25 % — отдельная запись

# Семьи PC, по которым лог разложен на голоса (см. SOUND.MD §2.1).
VOICES = (
    ('a', '$82D1', '$82D9'),
    ('b', '$8333', '$833B'),
    ('c', '$836A', '$8375'),
)
NOISE_PC = '$8389'
NOISE_MIN_GAP_ZX = 30_000   # пауза между вспышками, такты ZX
# Свипы аттракт-демо — в партитуру не входят.
IGNORED_PC = ('$83A6', '$83B9', '$83D1')


def load_log(path):
    events = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        t, _frame, pc, value = line.split()
        events.append((int(t), pc, int(value, 16)))
    if not events:
        raise SystemExit('%s: пустой лог' % path)
    return events


def to_cpu(t_zx):
    """Такты ZX (3.5 МГц) -> такты КР580ВМ80А (3.0 МГц)."""
    return t_zx * CPU_HZ / ZX_HZ


def pulses(events, t0, pc_hi, pc_lo):
    """Фронты голоса -> (момент высокого фронта, длительность) в тактах ZX.

    Пары hi->lo не всегда идут с чётного индекса: голос B в логе местами
    начинает с низкого фронта, поэтому пара ищется по имени кода, а не по
    чётности.
    """
    e = [(t - t0, pc) for t, pc, _ in events if pc in (pc_hi, pc_lo)]
    out = []
    i = 0
    while i + 1 < len(e):
        if e[i][1] == pc_hi and e[i + 1][1] == pc_lo:
            out.append((e[i][0], e[i + 1][0] - e[i][0]))
            i += 2
        else:
            i += 1
    return out


def median_filter(series, win):
    h = win // 2
    return [statistics.median(series[max(0, i - h):i + h + 1])
            for i in range(len(series))]


def rle_periods(periods, tol, hyst):
    """Периоды импульсов -> [(сколько импульсов, период)]."""
    segs = []
    cur = periods[0]
    n = 1
    bad = 0
    for p in periods[1:]:
        if abs(p - cur) > tol * cur:
            bad += 1
            if bad >= hyst:
                segs.append((n, cur))
                cur = p
                n = 0
                bad = 0
        else:
            bad = 0
        n += 1
    segs.append((n, cur))
    return segs


def segments(periods, filt, tol, hyst, outlier):
    """Периоды -> записи скрипта: RLE по сглаженным + одиночные выбросы.

    «Пропущенные проходы» оригинала (интервал в 1.6 раза длиннее медианы)
    медианный фильтр вытравливает, и модель начинает спешить — за 38 с
    набегало 2-5 с, голоса расходились между собой. Поэтому такие
    интервалы сохраняются КАК ЕСТЬ, отдельной записью на один импульс:
    стоит 3 байта, зато темп и ритм (клик!) остаются оригинальными.
    """
    segs = []
    n = len(periods)
    i = 0
    while i < n:
        if abs(periods[i] - filt[i]) > (outlier - 1) * filt[i]:
            segs.append((1, periods[i]))
            i += 1
            continue
        j = i
        while j < n and abs(periods[j] - filt[j]) <= (outlier - 1) * filt[j]:
            j += 1
        segs += rle_periods(filt[i:j], tol, hyst)
        i = j
    return segs


def burst_schedule(bursts, t0, cpu_period):
    """Интервалы между вспышками -> [(сколько вспышек, играть 0/1)]."""
    starts = [b[0] - t0 for b in bursts]
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    plan = []
    for g in gaps:
        slots = max(1, int(round(to_cpu(g) / cpu_period)))
        for k in range(slots):
            plan.append(1 if k == 0 else 0)
    # RLE по признаку «играть»
    out = []
    for v in plan:
        if out and out[-1][1] == v:
            out[-1][0] += 1
        else:
            out.append([1, v])
    return [(n, v) for n, v in out]


def noise_pattern(bursts):
    """Вспышка -> интервалы в тиках по BURST_TICK (все вспышки совпадают).

    Плеер тратит на шаг BURST_STEP + BURST_TICK*тик тактов, поэтому из
    измеренного интервала накладные расходы вычитаются: так 76 шагов
    занимают столько же времени, сколько в оригинале (~13 мс).
    """
    def ticks(b):
        out = [max(1, int(round((to_cpu(y - x) - BURST_STEP) / BURST_TICK)))
               for x, y in zip(b, b[1:])]
        if max(out) > 255:
            raise SystemExit('шаг вспышки не влезает в байт: %d' % max(out))
        return out
    first = ticks(bursts[0])
    for b in bursts[1:]:
        if ticks(b) != first:
            raise SystemExit('вспышки шума различаются — модель неверна')
    return first


def units(t_zx, unit):
    """Такты ZX -> единицы плеера (округление, минимум 1)."""
    return max(1, int(round(to_cpu(t_zx) / unit)))


def build_voice(segs, t_end_cpu):
    """Сегменты -> записи скрипта (счётчик <= 255) до момента t_end.

    Записи обрываются на ПЕРВОМ импульсе за t_end, а не на границе
    RLE-сегмента: сегмент — это до 255 импульсов (у голоса A это 2.7 с), и
    обрыв по границе оттянул бы конец партитуры на секунды.
    """
    out = []
    t = 0.0
    for cnt, per in segs:
        p = units(per, UNIT_T)
        step = p * UNIT_T
        while cnt > 0:
            if t >= t_end_cpu:
                return out
            if out and out[-1][1] == p and out[-1][0] < 255:
                out[-1] = (out[-1][0] + 1, p)
            else:
                out.append((1, p))
            t += step
            cnt -= 1
    # Сегменты кончаются на предпоследнем импульсе (периоды считаны между
    # импульсами) — последний такт голоса доигрываем тем же периодом.
    while out and t < t_end_cpu:
        p = out[-1][1]
        if out[-1][0] >= 255:
            out.append((0, p))
        out[-1] = (out[-1][0] + 1, p)
        t += p * UNIT_T
    return out


def plan_seconds(plan, gap_units):
    """Длительность плана шума: слоты по gap_units единиц."""
    return sum(n for n, _ in plan) * gap_units * UNIT_T / CPU_HZ


def simulate(entries, n):
    """Проиграть скрипт моделью плеера: моменты импульсов в единицах.

    Правило (см. include/beep.asm): на каждом импульсе счётчик записи
    уменьшается, и при нуле загружается следующая запись — её период и
    задаёт СЛЕДУЮЩИЙ интервал.
    """
    t = 0
    times = []
    c = 0
    j = 0
    for _ in range(n):
        if c == 0:
            c, p = entries[j]
            j += 1
        times.append(t)
        t += p
        c -= 1
    return times


def emit(path, data, stats):
    lines = [
        ';',
        '; title_music.asm — мелодия заставки H.A.T.E. целиком (TapeOut, PC0).',
        ';',
        '; СГЕНЕРИРОВАНО tools/gen_title_music.py из assets/title_music.txt —',
        '; править здесь бессмысленно: правь исходник и пересобери.',
        ';',
        '; Скрипты голосов — записи по 3 байта: счётчик импульсов, период',
        '; (мл. байт, ст. байт) в единицах %d такта Вектора; 0 — конец.' %
        UNIT_T,
        '; Плеер (include/beep.asm) сам считает интервалы: голос выдаёт узкий',
        '; импульс и ждёт период, поэтому данных нужно ~%d записей вместо' %
        sum(s['segments'] for s in stats['voices']),
        '; %d фронтов PC0.' % stats['edges'],
        ';',
        '; Скрипт шума — записи по 2 байта: сколько интервалов по mus_np и',
        '; признак 1 = вспышка, 0 = пропуск; 0 — конец. Рисунок вспышки',
        '; (mus_nz): первый байт — число шагов, далее интервалы в тиках.',
        ';',
        '; Длительность партитуры %.2f с, записей %d (%d байт данных).' %
        (stats['loop_s'], stats['records'], stats['bytes']),
        '; Накладные расходы и скважность импульса считает сам плеер;',
        '; MUS_DUTY_x — скважность в шагах beat_delay по %d такта.' % BEAT_T,
        ';',
        '        SECTION code_clib',
        '        PUBLIC  mus_a',
        '        PUBLIC  mus_b',
        '        PUBLIC  mus_c',
        '        PUBLIC  mus_n',
        '        PUBLIC  mus_np',
        '        PUBLIC  mus_nz',
        '        PUBLIC  MUS_DUTY_A',
        '        PUBLIC  MUS_DUTY_B',
        '        PUBLIC  MUS_DUTY_C',
        '        PUBLIC  MUS_FIRE_A',
        '        PUBLIC  MUS_FIRE_B',
        '        PUBLIC  MUS_FIRE_C',
        '        PUBLIC  MUS_BURST_B',
        '',
    ]
    for v in stats['voices']:
        lines += [
            '; --- голос %s: %d записей, %.2f с, импульс %d тактов ZX' %
            (v['name'].upper(), v['segments'], v['seconds'], v['width']),
            'MUS_DUTY_%s equ %d' % (v['name'].upper(), v['duty']),
            'MUS_FIRE_%s equ MUS_DUTY_%s+%d' %
            (v['name'].upper(), v['name'].upper(), FIRE_BASE),
            'mus_%s:' % v['name'],
        ]
        for cnt, per in data['voices'][v['name']]:
            lines.append('        defb    %d, 0x%02X, 0x%02X'
                         % (cnt, per & 0xFF, per >> 8))
        lines += ['        defb    0', '']

    lines += [
        '; --- шум: %d вспышек, период %.4f с, %d пропусков' %
        (stats['bursts'], stats['noise_s'], stats['skips']),
        'mus_np: defw    0x%04X' % stats['noise_period'],
        'mus_n:',
    ]
    for cnt, fire in data['noise']:
        lines.append('        defb    %d, %d' % (cnt, fire))
    lines += ['        defb    0', '', '; --- рисунок вспышки: %d шагов' %
              len(data['nz'])]
    lines.append('mus_nz:')
    rows = [len(data['nz'])] + list(data['nz'])
    for i in range(0, len(rows), 12):
        lines.append('        defb    '
                     + ', '.join('0x%02X' % b for b in rows[i:i + 12]))
    lines += [
        '',
        '; Цена вспышки в битах по %d такта: плеер добавляет её в spent,' % BEAT_T,
        '; поэтому шум не сдвигает партитуру (beep.asm, fire_n).',
        'MUS_BURST_B equ %d' % stats['burst_beats'],
        '',
    ]
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--src', default=str(ROOT / 'assets' / 'title_music.txt'))
    parser.add_argument('--out', default=str(ROOT / 'include' / 'title_music.asm'))
    parser.add_argument('--stats', action='store_true')
    args = parser.parse_args()

    events = load_log(args.src)
    t0 = events[0][0]
    t_end_zx = events[-1][0] - t0

    # --- голоса -----------------------------------------------------------
    data = {'voices': {}, 'noise': [], 'nz': []}
    vstats = []
    per_voice = {}
    for name, hi, lo in VOICES:
        pl = pulses(events, t0, hi, lo)
        widths = [w for _, w in pl]
        periods = [pl[i + 1][0] - pl[i][0] for i in range(len(pl) - 1)]
        segs = segments(periods, median_filter(periods, MEDIAN_WIN),
                        TOL, HYST, OUTLIER)
        per_voice[name] = (pl, segs, statistics.median(widths))
        vstats.append(dict(name=name, segments=len(segs),
                           seconds=to_cpu(pl[-1][0]) / CPU_HZ,
                           width=statistics.median(widths),
                           duty=units(statistics.median(widths), BEAT_T)))

    # --- конец партитуры --------------------------------------------------
    # Это конец ЗАПИСИ (38.5 с), а не последний импульс одного голоса: голоса
    # кончаются по-разному (A 38.44, C 38.35), а кольцо общее. Каждый скрипт
    # продлевается до t_end своим последним периодом. Раньше конец задавал
    # план шума — он кончался на 37.5 с, и хвост мелодии не играл никогда.
    t_end_cpu = to_cpu(t_end_zx)

    # --- шум --------------------------------------------------------------
    stamps = [t - t0 for t, pc, _ in events if pc == NOISE_PC]
    bursts = [[stamps[0]]]
    for t in stamps[1:]:
        if t - bursts[-1][-1] > NOISE_MIN_GAP_ZX:
            bursts.append([t])
        else:
            bursts[-1].append(t)
    nz = noise_pattern(bursts)
    noise_period_units = units(bursts[1][0] - bursts[0][0], UNIT_T)
    noise_gap_cpu = noise_period_units * UNIT_T
    plan = burst_schedule(bursts, t0, noise_gap_cpu)
    # Хвост плана — тишина: после последней вспышки партитура ещё играет.
    tail = int(round(t_end_cpu / noise_gap_cpu)) + 2 - sum(n for n, _ in plan)
    if tail > 0:
        plan.append((tail, 0))
    data['nz'] = nz
    data['noise'] = plan

    # --- сборка скриптов --------------------------------------------------
    for name, _, _ in VOICES:
        data['voices'][name] = build_voice(per_voice[name][1], t_end_cpu)
    script_s = {n: sum(c * p for c, p in data['voices'][n]) * UNIT_T / CPU_HZ
                for n, _, _ in VOICES}

    records = sum(len(v) for v in data['voices'].values())
    bytes_ = records * 3 + len(plan) * 2 + 2 + len(nz) + 1

    stats = dict(
        edges=len(events),
        loop_s=t_end_cpu / CPU_HZ,
        records=records,
        bytes=bytes_,
        bursts=len(bursts),
        noise_s=noise_period_units * UNIT_T / CPU_HZ,
        noise_period=noise_period_units,
        skips=sum(n for n, f in plan if not f),
        # Цена вспышки в битах задержки: шаги плюс вход/выход mus_burst.
        burst_beats=int(round((len(nz) * BURST_STEP + BURST_TICK * sum(nz)
                               + 108) / float(BEAT_T))),
        voices=vstats,
    )

    emit(args.out, data, stats)

    print('%s -> %s' % (args.src, args.out))
    print('  партитура %.2f с (лог %.2f с), %d фронтов'
          % (stats['loop_s'], t_end_zx / ZX_HZ, stats['edges']))
    for v in vstats:
        print('  голос %s: %d записей, импульс %d такта ZX (duty %d ед.), '
              'лог до %.2f с, скрипт до %.2f с'
              % (v['name'].upper(), v['segments'], v['width'], v['duty'],
                 v['seconds'], script_s[v['name']]))
    print('  план шума %.2f с — должен быть длиннее партитуры'
          % plan_seconds(plan, noise_period_units))
    print('  шум: %d вспышек по %.4f с, пропусков %d, рисунок %d шагов, '
          'вспышка %d бит'
          % (stats['bursts'], stats['noise_s'], stats['skips'], len(nz),
             stats['burst_beats']))
    print('  записей %d, данных %d байт' % (stats['records'], stats['bytes']))
    if args.stats:
        for name, _, _ in VOICES:
            segs = data['voices'][name]
            ps = [p for _, p in segs]
            real = [to_cpu(t) / UNIT_T for t, _ in per_voice[name][0]]
            # Скрипт короче лога на несколько импульсов (RLE меняет счётчики),
            # поэтому сверяем общий префикс, а не «по числу фронтов».
            sim = simulate(segs, min(len(real), sum(c for c, _ in segs)))
            err = [a - b for a, b in zip(sim, real)]
            print('  %s: период %d..%d ед., записей %d, счётчики 1..%d, '
                  'уход к концу %+.0f ед. (%.1f мс), макс %.0f ед.'
                  % (name.upper(), min(ps), max(ps), len(segs),
                     max(c for c, _ in segs), err[-1],
                     err[-1] * UNIT_T / CPU_HZ * 1e3,
                     max(abs(x) for x in err)))
        print('  шум: период %d ед. по %d такта' % (noise_period_units, UNIT_T))
        print('  план шума', plan)


if __name__ == '__main__':
    main()
