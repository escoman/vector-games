#!/usr/bin/env python3
"""gen_title_music.py — цикличная мелодия заставки H.A.T.E. (7 голосов).

Источник — `assets/title_music_ay.txt`, лог всех переключений динамика ZX,
снятый прогоном настоящего плеера из AY-архива `assets/HATE_title_theme.ay`
в SkoolKit (tools/ay_beeper.py, разбор — SOUND_FIX.MD). Цикл оригинала —
ровно 2800 кадров (56.00 с), и партитура здесь циклична: каждый скрипт
длится ровно LOOP_UNITS единиц и кончается терминатором, который отматывает
указатель СВОЕГО голоса — все голоса смыкаются на одном шаге, это и есть
цикл.

СЕМЬ ГОЛОСОВ:
  * A ($82D1/$82D9) и B ($8333/$833B) — генераторы узкого импульса
    (мелодия), период плавно-ступенчато меняется по партитуре;
  * C ($836A/$8375) — клик, сетка 15 кадров с пропусками 20 и 95;
  * N ($8389) — вспышки шума, сетка 40 кадров, фаза 20, три пропуска по 120;
  * S1 ($83A6), S2 ($83B9), S3 ($83D1) — свипы «пиу» (очередь 5+5+4 пуска
    на кадрах 800..875, группы на 1760 и 2720) — третий инструмент мелодии,
    а не аттракт-демо.

ФОРМАТ ЗАПИСИ (один на все семь голосов, 3 байта, include/beep.asm):

        defw    delay           ; единиц по 128 такта; 0 = терминатор скрипта
        defb    n               ; A/B/C: сколько импульсов; N/S: 1 = пуск

Семантика: запись потребляет n*delay единиц, импульсы на +delay, +2*delay,
... +n*delay; следующий интервал задаёт СЛЕДУЮЩАЯ запись. n = 0 — пауза
длиной delay (ею закрывается хвост до границы цикла). Терминатор отматывает
указатель своего голоса на начало скрипта.

ПРЕДЕЛ ЗАДЕРЖКИ — MAX_DELAY = 16 383 ед. (0.70 с). Плеер держит счётчики
16 битами, а перед выжиданием умножает их на 4 (dad h ×2), поэтому задержка
сверх 16 383 даёт не то время (переполнение), а сверх 65 535 не влезает и в
сам счётчик. Длинные паузы (пропуски клика 95 кадров, ударных 120, группы
свипов) режутся на цепочку записей-пауз не длиннее MAX_DELAY (chunk_long):
сумма выдерживается точно, подхват записи компенсирован (PICKUP_B).

АБСОЛЮТНАЯ ПРИВЯЗКА. Генератор не «идёт по периодам»: для каждой записи
p = round((момент последнего импульса записи - момент последнего импульса
предыдущей) / n) по измеренным моментам оригинала. Остаток округления не
накапливается — каждая записка кончается ровно там, где надо. Первая запись
каждого скрипта — одиночный импульс на измеренной фазе, поэтому фаза
стартового клика/удара (кадр 0 / кадр 20) сохраняется.

СВИПЫ — таблицы полупериодов битами по BEAT_T = 32 такта:
beats_i = round((hp_i * 3/3.5 - CHIRP_STEP) / 32), минимум 1. Нижние шаги
$83A6 упираются в минимум и усекаются (на слух неслышно). Цена пуска
(длительность свипа целиком) — в spent, как MUS_BURST_B у шума, иначе 42
пускания за цикл утаскивают мелодию.

Использование:
    python3 tools/gen_title_music.py            # -> include/title_music.asm
    python3 tools/gen_title_music.py --stats    # + разбор в stdout
"""

import argparse
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ZX_HZ = 3_500_000
CPU_HZ = 3_000_000

# ВРЕМЯ НА ВЕКТОРЕ. Такты КР580ВМ80А здесь не номинальные, а РЕАЛЬНО
# ЗАНИМАЕМЫЕ (4-тактовые окна видео-контроллера, см. шапку include/beep.asm).
UNIT_T = 128            # единица счётчиков плеера, тактов Вектора (42.7 мкс)
BEAT_T = 32             # шаг цикла beat_delay: он же шаг скважности
GRID = 468              # единиц на кадр (59 904 / 128) — кадровая сетка
LOOP_FRAMES = 2800      # цикл оригинала, кадров
LOOP_UNITS = LOOP_FRAMES * GRID      # 1 310 400 ед. = 56.00 с
MAX_DELAY = 16383       # предел задержки одной записи, ед.: счётчики плеера
                        # 16-битные, а перед выжиданием умножаются на 4
                        # (dad h ×2), 4*16383 = 65 532 < 65 536

BURST_STEP = 56         # накладные одного шага вспышки шума, такты (cma/ani/
                        # out 24 + mov b,m/inx h 16 + dcr c 8 + jnz 12)
BURST_TICK = 20         # шаг цикла dcr b / jnz внутри вспышки, такты
BURST_EDGE = 108        # вход и хвост вспышки (lxi h, call, последний фронт,
                        # тишина), такты
CHIRP_STEP = 128        # накладные одного шага свипа, такты (cma/ani/out 24 +
                        # mov b,a 8 + mov e,m/inx h 16 + call 24 + вход и
                        # выход beat_delay 40 + dcr c/jnz 20)
CHIRP_EDGE = 128        # вход и хвост свипа (lxi h, call, инициализация,
                        # последний фронт, тишина), такты
FIRE_BASE = 9           # цена импульса сверх скважности, биты по BEAT_T
                        # (beep.asm: корпус fire_x ~292 такта = 9.1 бита)

MEDIAN_WIN = 5          # медианный фильтр по интервалам
TOL = 0.015             # допуск RLE по периоду (1.5 % = 26 центов)
OUTLIER = 1.25          # интервал длиннее медианы на 25 % — отдельная запись
GLIDE = 0.08            # размах периода внутри записи, при котором группа
                        # рвётся: дрожание ZX (до ~6 %) держится одной
                        # записью, глиссандо/смену ноты режет
MIN_GAP_ZX = 30_000     # пауза между пусками событий, такты ZX

# Голоса мелодии и события (см. SOUND_FIX.MD §3).
VOICES = (
    ('a', '$82D1', '$82D9'),
    ('b', '$8333', '$833B'),
    ('c', '$836A', '$8375'),
)
EVENT_PC = (
    ('n', '$8389'),
    ('s1', '$83A6'),
    ('s2', '$83B9'),
    ('s3', '$83D1'),
)


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


def units(t_zx, unit=UNIT_T):
    """Такты ZX -> единицы плеера (округление, минимум 1)."""
    return max(1, int(round(to_cpu(t_zx) / unit)))


def pulses(events, t0, pc_hi, pc_lo):
    """Фронты голоса -> (момент высокого фронта, длительность) в тактах ZX.

    Пары hi->lo не всегда идут с чётного индекса (голос B местами начинает с
    низкого фронта), поэтому пара ищется по имени кода, а не по чётности.
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


def group_by_gap(stamps, min_gap):
    """Моменты -> группы: новая группа при зазоре > min_gap."""
    groups = [[stamps[0]]]
    for t in stamps[1:]:
        if t - groups[-1][-1] > min_gap:
            groups.append([t])
        else:
            groups[-1].append(t)
    return groups


def median_filter(series, win):
    h = win // 2
    return [statistics.median(series[max(0, i - h):i + h + 1])
            for i in range(len(series))]


def segments(periods, filt, tol, outlier):
    """Периоды -> сегменты скрипта: выбросы отдельно, ровные участки группами.

    «Пропущенные проходы» оригинала (интервал заметно длиннее медианы)
    сохраняются КАК ЕСТЬ, отдельной записью на один импульс: стоит 3 байта,
    зато темп и ритм (клик!) остаются оригинальными. При абсолютной привязке
    дрейфа от них нет: каждая запись кончается на измеренном моменте.

    Группа рвётся, когда размах СЫРЫХ периодов внутри неё превышает
    GLIDE: так дрожание плеера ZX (до ~6 %) остаётся одной записью, а
    реальное движение периода (глиссандо, хвост ноты) — нет. Медианный
    фильтр для этого не годится: он сглаживает последние шаги хвоста, и
    сегмент с глиссандо игрался бы одной плоской нотой с ошибкой до сотен
    единиц.
    """
    limit = GLIDE
    segs = []
    n = len(periods)
    i = 0
    while i < n:
        if abs(periods[i] - filt[i]) > (outlier - 1) * filt[i]:
            segs.append((1, periods[i]))
            i += 1
            continue
        j = i + 1
        lo = hi = periods[i]
        while j < n:
            p = periods[j]
            if abs(p - filt[j]) > (outlier - 1) * filt[j]:
                break
            if max(hi, p) - min(lo, p) > limit * filt[i]:
                break
            lo = min(lo, p)
            hi = max(hi, p)
            j += 1
        segs.append((j - i, int(round(statistics.median(periods[i:j])))))
        i = j
    return segs


def chunk_long(recs, max_delay=MAX_DELAY):
    """Разбить задержки длиннее max_delay на цепочку записей.

    Плеер умножает счётчик на 4 в 16 битах (см. ПРЕДЕЛ ЗАДЕРЖКИ в шапке),
    поэтому длинная задержка игралась бы короче — именно так уезжали ударные
    и клик. Пауза (n = 0) режется на подряд идущие паузы; у записи с
    импульсами паузы ставятся ПЕРЕД каждым импульсом, чтобы период
    сохранился: событие подхватывает следующую запись сразу (beep.asm).
    Терминатор (delay = 0) проходит как есть.
    """
    out = []
    for delay, n in recs:
        if delay <= max_delay:
            out.append((delay, n))
            continue
        k, rem = divmod(delay, max_delay)
        if rem == 0:
            k, rem = k - 1, max_delay
        if n == 0:
            out.extend([(max_delay, 0)] * k)
            out.append((rem, 0))
        else:
            for _ in range(n):
                out.extend([(max_delay, 0)] * k)
                out.append((rem, 1))
    return out


def build_pulse_voice(moments, segs, loop_units):
    """Моменты импульсов + сегменты -> записи (delay, n) до границы цикла.

    Первая запись — одиночный импульс на измеренной фазе (фаза цикла!).
    Дальше сегменты по АБСОЛЮТНОЙ привязке с обратной связью: период записи
    считается не от измеренного конца предыдущей, а от её СЫГРАННОГО конца
    (sim_prev). Иначе погрешность округления периода (до 0.5*cnt на запись)
    накапливается по цепочке записей и к середине цикла достигает сотен
    единиц — бас слышно уплывает от кликов. При обратной связи ошибка
    ограничена последней записью и дальше не передаётся.
    """
    out = []
    if moments[0] > 0:
        out.append((moments[0], 1))
        sim_prev = moments[0]
    else:
        sim_prev = 0
    i = 1
    for cnt, _per in segs:
        cnt = min(cnt, len(moments) - i)
        if cnt <= 0:
            break
        while cnt > 255:
            t_end = moments[i + 254]
            p = max(1, int(round((t_end - sim_prev) / 255)))
            out.append((p, 255))
            sim_prev += p * 255
            i += 255
            cnt -= 255
        t_end = moments[i + cnt - 1]
        p = max(1, int(round((t_end - sim_prev) / cnt)))
        out.append((p, cnt))
        sim_prev += p * cnt
        i += cnt
    # Скрипт обязан кончаться РОВНО на границе цикла (терминатор
    # отматывает указатель, все голоса смыкаются на одном шаге). Сумма
    # записей отличается от границы на погрешность округления периодов:
    # перелёт гасим укорачиванием последней записи, недолёт — паузой.
    total = sum(d * max(1, n) for d, n in out)
    if total > loop_units and out:
        d, n = out[-1]
        k = -(-(total - loop_units) // n)       # ceil(перелёт / n)
        out[-1] = (max(1, d - k), n)
        total -= (d - max(1, d - k)) * n
    while total > loop_units and out and out[-1][1] > 0:
        d, n = out[-1]
        if n > 1:
            out[-1] = (d, n - 1)
            total -= d
        else:
            out.pop()
            total -= d
    tail = loop_units - total
    if tail > 0:
        out.append((tail, 0))
    out.append((0, 0))
    return chunk_long(out)


def build_event_voice(moments, loop_units):
    """Моменты пусков события -> записи (delay, 1) и паузы (delay, 0).

    Сетка событий — кадровая (N: 40 кадров, свипы: 5 кадров), поэтому
    моменты привязаны к GRID: фаза — ближайшая кадровая граница, интервалы
    — ближайшие кратные GRID. Первая запись — пуск на фазе.
    """
    phase = int(round(moments[0] / GRID)) * GRID
    snapped = [phase + int(round((u - phase) / GRID)) * GRID for u in moments]
    out = [(snapped[0], 1)]
    for a, b in zip(snapped, snapped[1:]):
        out.append((b - a, 1))
    tail = loop_units - snapped[-1]
    if tail > 0:
        out.append((tail, 0))
    out.append((0, 0))
    return chunk_long(out), snapped


def simulate(entries, n):
    """Проиграть скрипт моделью плеера: моменты импульсов в единицах.

    Правило (include/beep.asm): счётчик заряжается delay записи; при нуле —
    импульс (если n > 0) и счётчик записи уменьшается; при нуле записи
    подхватывается следующая; n = 0 — пауза без импульса.
    """
    times = []
    t = 0
    j = 0
    c = 0
    p = 0
    for _ in range(n):
        if c == 0:
            d, c = entries[j]
            j += 1
            p = d
        t += p
        if c > 0:
            times.append(t)
            c -= 1
        else:
            c = 0
    return times


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


def chirp_pattern(launches, pc):
    """Полупериоды свипа -> биты по BEAT_T (все пуски совпадают).

    Полупериод измерен в тактах ZX; в тактах Вектора это hp*3/3.5. Плеер на
    шаг тратит CHIRP_STEP + BEAT_T*бит, поэтому CHIRP_STEP вычитается.
    Нижние шаги упираются в минимум 1 бит и усекаются — на слух неслышно
    (SOUND_FIX.MD §5.3).
    """
    def beats(g):
        return [max(1, int(round((hp * CPU_HZ / ZX_HZ - CHIRP_STEP) / BEAT_T)))
                for hp in (b - a for a, b in zip(g, g[1:]))]
    first = beats(launches[0])
    for g in launches[1:]:
        if beats(g) != first:
            raise SystemExit('%s: пуски свипа различаются — модель неверна'
                             % pc)
    if max(first) > 255:
        raise SystemExit('%s: шаг свипа не влезает в байт' % pc)
    return first


def burst_cost(ticks):
    """Длительность вспышки в тактах — по коду mus_burst (beep.asm).

    На шаг: cma/ani/out (24), mov b,m/inx h (16), dcr c (8), jnz (12) =
    BURST_STEP, плюс ожидание BURST_TICK*тик; последний jnz — непереход (-4).
    """
    return BURST_EDGE + BURST_STEP * len(ticks) + BURST_TICK * sum(ticks) - 4


def chirp_cost(beats):
    """Длительность пуска свипа в тактах — по коду mus_chirp (beep.asm).

    На шаг: CHIRP_STEP (вместе с call и входом/выходом beat_delay) плюс
    полупериод BEAT_T*бит; последний jnz шага — непереход (-4).
    """
    return CHIRP_EDGE + CHIRP_STEP * len(beats) + BEAT_T * sum(beats) - 4


def emit(path, data, stats):
    lines = [
        ';',
        '; title_music.asm — мелодия заставки H.A.T.E. целиком (TapeOut, PC0).',
        ';',
        '; СГЕНЕРИРОВАНО tools/gen_title_music.py из assets/title_music_ay.txt —',
        '; править здесь бессмысленно: правь исходник и пересобери.',
        ';',
        '; Семь голосов (SOUND_FIX.MD): A/B — мелодия, C — клик, N — ударные,',
        '; S1/S2/S3 — свипы. Запись — 3 байта: delay (ед. по %d такта, 0 =' % UNIT_T,
        '; терминатор) и n (число импульсов; 1 = пуск; 0 = пауза). Плеер',
        '; (include/beep.asm) сам считает интервалы: голос выдаёт узкий',
        '; импульс и ждёт период. Каждый скрипт длится ровно LOOP_UNITS =',
        '; %d ед. и кончается терминатором-перемоткой: все голоса смыкаются' % LOOP_UNITS,
        '; на одном шаге, это и есть цикл (%.2f с).' % stats['loop_s'],
        ';',
        '; Рисунки вспышки/свипов: первый байт — число шагов, далее интервалы',
        '; в тиках по %d такта (шум) или битах по %d такта (свипы).' % (BURST_TICK, BEAT_T),
        ';',
        '; Задержка записи не длиннее %d ед. (0.70 с): плеер умножает счётчик' % MAX_DELAY,
        '; на 4 в 16 битах, поэтому длинные паузы разбиты на цепочку записей.',
        ';',
        '; Данных %d байт, записей %d.' % (stats['bytes'], stats['records']),
        '; Накладные расходы и скважность импульса считает сам плеер;',
        '; MUS_DUTY_x — скважность в шагах beat_delay по %d такта.' % BEAT_T,
        ';',
        '        SECTION code_clib',
        '        PUBLIC  mus_a',
        '        PUBLIC  mus_b',
        '        PUBLIC  mus_c',
        '        PUBLIC  mus_n',
        '        PUBLIC  mus_s1',
        '        PUBLIC  mus_s2',
        '        PUBLIC  mus_s3',
        '        PUBLIC  mus_nz',
        '        PUBLIC  mus_cz1',
        '        PUBLIC  mus_cz2',
        '        PUBLIC  mus_cz3',
        '        PUBLIC  MUS_DUTY_A',
        '        PUBLIC  MUS_DUTY_B',
        '        PUBLIC  MUS_DUTY_C',
        '        PUBLIC  MUS_FIRE_A',
        '        PUBLIC  MUS_FIRE_B',
        '        PUBLIC  MUS_FIRE_C',
        '        PUBLIC  MUS_BURST_B',
        '        PUBLIC  MUS_CHIRP_B1',
        '        PUBLIC  MUS_CHIRP_B2',
        '        PUBLIC  MUS_CHIRP_B3',
        '',
    ]
    for v in stats['voices']:
        lines += [
            '; --- голос %s: %d записей, %d импульсов, импульс %d тактов ZX' %
            (v['name'].upper(), v['records'], v['pulses'], v['width']),
            ';     длина скрипта %d ед. (уход к границе цикла %d), фаза %d ед.' %
            (v['length'], v['drift'], v['phase']),
            'MUS_DUTY_%s equ %d' % (v['name'].upper(), v['duty']),
            'MUS_FIRE_%s equ MUS_DUTY_%s+%d' %
            (v['name'].upper(), v['name'].upper(), FIRE_BASE),
            'mus_%s:' % v['name'],
        ]
        for delay, n in data['voices'][v['name']]:
            lines.append('        defw    %d' % delay)
            lines.append('        defb    %d' % n)
        lines.append('')

    lines += [
        '; --- шум: %d вспышек, период %.4f с, %d пропусков' %
        (stats['bursts'], stats['noise_s'], stats['skips']),
        ';     скрипт %d записей, фаза %d ед., хвост %d ед.' %
        (len(data['noise']) - 1, data['noise'][0][0], data['noise'][-2][0]),
        'mus_n:',
    ]
    for delay, n in data['noise']:
        lines.append('        defw    %d' % delay)
        lines.append('        defb    %d' % n)
    lines += [
        '',
        'mus_nz:',
    ]
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

    for v in stats['events']:
        name = v['name'].upper()
        recs = data['voices'][v['name']]
        lines += [
            '; --- свип %s: %d пусков, %d шагов, %.2f мс' %
            (name, v['launches'], v['steps'], v['seconds'] * 1e3),
            ';     скрипт %d записей, фаза %d ед., хвост %d ед.' %
            (len(recs) - 1, recs[0][0], recs[-2][0]),
            'mus_s%d:' % v['idx'],
        ]
        for delay, n in recs:
            lines.append('        defw    %d' % delay)
            lines.append('        defb    %d' % n)
        lines += [
            '',
            'mus_cz%d:' % v['idx'],
        ]
        rows = [v['steps']] + list(data['chirps'][name])
        for i in range(0, len(rows), 12):
            lines.append('        defb    '
                         + ', '.join('0x%02X' % b for b in rows[i:i + 12]))
        lines += [
            '',
            '; Цена пуска свипа в битах (длительность + вход/выход): добавляется',
            '; в spent, как MUS_BURST_B (beep.asm, fire_s%d).' % v['idx'],
            'MUS_CHIRP_B%d equ %d' % (v['idx'], v['chirp_beats']),
            '',
        ]
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--src', default=str(ROOT / 'assets' / 'title_music_ay.txt'))
    parser.add_argument('--out', default=str(ROOT / 'include' / 'title_music.asm'))
    parser.add_argument('--stats', action='store_true')
    args = parser.parse_args()

    events = load_log(args.src)
    t0 = events[0][0]
    t_end_zx = events[-1][0] - t0
    loop_s = LOOP_UNITS * UNIT_T / CPU_HZ

    # --- голоса A/B/C -----------------------------------------------------
    data = {'voices': {}, 'noise': None, 'nz': [], 'chirps': {}}
    vstats = []
    per_voice = {}
    for name, hi, lo in VOICES:
        pl = pulses(events, t0, hi, lo)
        widths = [w for _, w in pl]
        us = [units(t) for t, _ in pl if units(t) < LOOP_UNITS]
        u0 = us[0]
        if name == 'c':
            # клик: сетка кадровая — интервалы к ближайшему кратному GRID
            gaps = [int(round(g / GRID)) * GRID
                    for g in (b - a for a, b in zip(us, us[1:]))]
            us = [u0] + [u0 + sum(gaps[:k + 1]) for k in range(len(gaps))]
            segs = segments(gaps, median_filter(gaps, MEDIAN_WIN),
                            TOL, OUTLIER)
        else:
            gaps = [b - a for a, b in zip(us, us[1:])]
            segs = segments(gaps, median_filter(gaps, MEDIAN_WIN),
                            TOL, OUTLIER)
        recs = build_pulse_voice(us, segs, LOOP_UNITS)
        length = sum(d * max(1, n) for d, n in recs)
        sim = simulate(recs, len(us))
        err = [a - b for a, b in zip(sim, us)]
        per_voice[name] = (us, statistics.median(widths))
        data['voices'][name] = recs
        vstats.append(dict(
            name=name,
            records=len(recs) - 1,
            pulses=len(us),
            width=statistics.median(widths),
            duty=units(statistics.median(widths), BEAT_T),
            length=length,
            drift=length - LOOP_UNITS,
            phase=u0,
            max_err=max(abs(x) for x in err) if err else 0,
        ))

    # --- шум N ------------------------------------------------------------
    stamps = [t - t0 for t, pc, _ in events if pc == '$8389']
    bursts = group_by_gap(stamps, MIN_GAP_ZX)
    nz = noise_pattern(bursts)
    n_us = [units(b[0]) for b in bursts if units(b[0]) < LOOP_UNITS]
    recs, snapped = build_event_voice(n_us, LOOP_UNITS)
    length = sum(d * max(1, n) for d, n in recs)
    data['noise'] = recs
    data['nz'] = nz
    noise_s = (snapped[1] - snapped[0]) * UNIT_T / CPU_HZ
    skips = sum(b - a - GRID * 40 for a, b in zip(snapped, snapped[1:])) // GRID

    # --- свипы ------------------------------------------------------------
    estats = []
    for idx, (name, pc) in enumerate(EVENT_PC[1:], start=1):
        st = [t - t0 for t, p, _ in events if p == pc]
        launches = group_by_gap(st, MIN_GAP_ZX)
        beats = chirp_pattern(launches, pc)
        s_us = [units(g[0]) for g in launches if units(g[0]) < LOOP_UNITS]
        recs, snapped = build_event_voice(s_us, LOOP_UNITS)
        length = sum(d * max(1, n) for d, n in recs)
        data['chirps'][name.upper()] = beats
        data['voices'][name] = recs
        dur = chirp_cost(beats)
        estats.append(dict(
            name=name, idx=idx, launches=len(s_us), steps=len(beats),
            seconds=dur / CPU_HZ,
            chirp_beats=int(round(dur / float(BEAT_T))),
            length=length, drift=length - LOOP_UNITS,
            phase=snapped[0],
        ))

    records = sum(len(v) for v in data['voices'].values()) \
        + len(data['noise'])
    splits = sum(1 for recs in list(data['voices'].values()) + [data['noise']]
                 for d, n in recs if d == MAX_DELAY and n == 0)
    bytes_ = records * 3 + len(nz) + 1 + sum(len(data['chirps'][c]) + 1
                                             for c in data['chirps'])

    stats = dict(
        loop_s=loop_s,
        records=records - 7,        # без терминаторов семи скриптов
        splits=splits,
        bytes=bytes_,
        bursts=len(bursts),
        noise_s=noise_s,
        skips=skips,
        burst_beats=int(round(burst_cost(nz) / float(BEAT_T))),
        voices=vstats,
        events=estats,
    )

    emit(args.out, data, stats)

    print('%s -> %s' % (args.src, args.out))
    print('  цикл %.2f с = %d ед. по %d такта, лог %.2f с, %d фронтов'
          % (loop_s, LOOP_UNITS, UNIT_T, t_end_zx / ZX_HZ, len(events)))
    for v in vstats:
        print('  голос %s: %d записей, %d импульсов, фаза %d ед., '
              'скрипт %d ед. (уход %d), макс ошибка %d ед.'
              % (v['name'].upper(), v['records'], v['pulses'], v['phase'],
                 v['length'], v['drift'], v['max_err']))
    nrec = len(data['noise']) - 1
    print('  шум: %d вспышек, %d записей, период %.4f с, пропусков %d, '
          'рисунок %d шагов, вспышка %d бит'
          % (stats['bursts'], nrec, stats['noise_s'], stats['skips'],
             len(nz), stats['burst_beats']))
    for e in estats:
        print('  свип %s: %d пусков, %d шагов, %.2f мс, пуск %d бит, '
              'скрипт %d ед. (уход %d)'
              % (e['name'].upper(), e['launches'], e['steps'],
                 e['seconds'] * 1e3, e['chirp_beats'], e['length'], e['drift']))
    print('  записей %d, данных %d байт, из них %d пауз по %d ед. (предел '
          'задержки)' % (stats['records'], stats['bytes'], stats['splits'],
                         MAX_DELAY))
    if args.stats:
        for v in vstats:
            name = v['name']
            recs = data['voices'][name]
            ds = [d for d, _ in recs if d]
            print('  %s: delay %d..%d ед., счётчики 1..%d, период %s'
                  % (name.upper(), min(ds), max(ds),
                     max(n for _, n in recs),
                     'кадровая сетка' if name == 'c' else 'свободный'))
            cnt = Counter(d for d, _ in recs if d)
            print('    частые delay:', cnt.most_common(6))
        print('  шум: фаза %d ед., хвост %d ед.' %
              (data['noise'][0][0], data['noise'][-2][0]))
        for e in estats:
            print('  свип %s: фаза %d ед., хвост %d ед.'
                  % (e['name'].upper(), data['voices'][e['name']][0][0],
                     data['voices'][e['name']][-2][0]))


if __name__ == '__main__':
    main()
