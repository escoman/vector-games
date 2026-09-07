#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_samples.py — генерация 16 синтетических шумовых инструментов
для библиотеки nes_drums (Вектор-06Ц, AY-3-8910).

Модель: детерминированный 15-битный LFSR задаёт характер шума
каждого инструмента через частоту продвижения (NES noise clock).
Частота преобразуется в регистр R6 AY-3-8910 по формуле делителя
шума из smp2wav.py:

    F = AY_CLK / (32 * (R6 + 1)),  AY_CLK = 1750000 Гц

Обратное преобразование:

    R6 = round(AY_CLK / (32 * F) - 1),  ограничение 0..31.

Выход .smp — кадровая последовательность пар (R6, R10) по одному
кадру на тик 50 Гц.  Формат .smp: байт N (число кадров), затем
N пар байт (R6, R10) — раздельно, как читает drums.asm и mus2inc.py.

Огибающая громкости у каждого инструмента своя.

Индексы соответствуют шумам NES $0..$F:
  $0  hihat_closed       $8  tom_low
  $1  hihat_open          $9  tom_rumble
  $2  snare_attack        $A  kick_heavy
  $3  snare_body          $B  kick_tight
  $4  snare_standard      $C  rumble_sub
  $5  cymbal_crash        $D  roar_ultra_low
  $6  snare_low           $E  subbass_drop
  $7  explosion_distant   $F  crackle

Использование:
    python3 gen_samples.py
"""

import glob
import math
import os
import sys

# Путь к папке с семплами (src/samples/ рядом со скриптом)
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'src', 'samples')

# Тактовая частота AY-3-8910 (как в smp2wav.py)
AY_CLK = 1750000.0


# =====================================================================
#   LFSR и преобразование частоты
# =====================================================================

def lfsr_step(state):
    """15-битный LFSR: биты 0 и 1, сдвиг вправо (спецификация ТЗ §2)."""
    feedback = ((state >> 0) ^ (state >> 1)) & 1
    return ((state >> 1) | (feedback << 14)) & 0x7FFF


def freq_to_r6(freq):
    """Частота шума LFSR → R6 AY-3-8910.

    Формула делителя шума (smp2wav.py):
        F = AY_CLK / (32 * (R6 + 1))
    Обратное:
        R6 = round(AY_CLK / (32 * F) - 1)
    Результат ограничивается диапазоном 0..31.
    """
    r6 = AY_CLK / (32.0 * freq) - 1.0
    return max(0, min(31, round(r6)))


# =====================================================================
#   Формат .smp
# =====================================================================

def write_smp(path, frames):
    """Записать .smp: байт N, затем N пар (R6, R10) раздельно."""
    n = len(frames)
    if n > 255:
        print(f'  ВНИМАНИЕ: {n} кадров > 255, обрезка',
              file=sys.stderr)
        n = 255
        frames = frames[:n]
    for r6, r10 in frames:
        if not (0 <= r6 <= 31 and 0 <= r10 <= 15):
            raise ValueError(
                f'{path}: R6={r6} R10={r10} вне диапазона')
    data = bytes([n] + [b for r6, r10 in frames for b in (r6, r10)])
    with open(path, 'wb') as f:
        f.write(data)


# =====================================================================
#   Конструкторы огибающих
# =====================================================================

def build_const(r6, vols):
    """Постоянный R6, список громкостей."""
    return [(r6, v) for v in vols]


def build_sweep(r6_seq, vols):
    """R6 меняется по кадрам (свип), громкости задаются списком."""
    if len(r6_seq) != len(vols):
        raise ValueError('r6_seq и vols разной длины')
    return [(r6, v) for r6, v in zip(r6_seq, vols)]


def env_lin(start, n):
    """Линейное затухание start → 1 за n кадров."""
    if n <= 0:
        return []
    if n == 1:
        return [max(1, start)]
    return [max(1, round(start * (n - 1 - i) / (n - 1)))
            for i in range(n)]


def env_exp(start, n):
    """Квадратичное затухание start → 1 за n кадров."""
    if n <= 0:
        return []
    if n == 1:
        return [max(1, start)]
    return [max(1, round(start * ((n - 1 - i) / (n - 1)) ** 2))
            for i in range(n)]


def env_steps(start, steps):
    """Ступенчатое затухание: список (уровень, длительность)."""
    vols = []
    for level, dur in steps:
        vols.extend([level] * dur)
    return vols


# =====================================================================
#   16 инструментов
# =====================================================================

# Частоты LFSR из ТЗ §3 (Гц)
LFSR_FREQS = [
    447400, 223700, 111860,  55900,  28000,  18600,  14000,  11200,
      8900,   7000,   4700,   3500,   2300,   1700,    880,    440,
]

NAMES = [
    'hihat_closed',    'hihat_open',      'snare_attack',
    'snare_body',      'snare_standard',  'cymbal_crash',
    'snare_low',       'explosion_distant',
    'tom_low',         'tom_rumble',      'kick_heavy',
    'kick_tight',      'rumble_sub',      'roar_ultra_low',
    'subbass_drop',    'crackle',
]


def gen_00_hihat_closed(r6):
    """$0 Closed Hi-Hat — очень короткий, 1-2 кадра.
    15 → 10 → 5 → 2 → 0."""
    return build_const(r6, [15, 10, 5, 2, 0])


def gen_01_hihat_open(r6):
    """$1 Open Hi-Hat — длиннее, ~100-150 мс.
    15 → 14 → 12 → 10 → 8 → 6 → 4 → 2 → 0."""
    return build_const(r6, [15, 14, 12, 10, 8, 6, 4, 2, 0])


def gen_02_snare_attack(r6):
    """$2 Snare Attack — очень короткий яркий транзиент."""
    return build_const(r6, [15, 12, 8, 3, 0])


def gen_03_snare_body(r6):
    """$3 Snare Body — короткий шумовой хвост после атаки."""
    return build_const(r6, env_exp(12, 6))


def gen_04_snare_standard(r6):
    """$4 Standard Noise — комбинация атаки и тела."""
    attack = [15, 12, 8]
    body = env_exp(10, 5)
    return build_const(r6, attack + body)


def gen_05_cymbal_crash(r6):
    """$5 Cymbal Crash — длинный decay, 500-800 мс."""
    return build_const(r6, env_exp(15, 40))


def gen_06_snare_low(r6):
    """$6 Snare Low — средняя длительность."""
    return build_const(r6, env_exp(11, 8))


def gen_07_explosion_distant(r6):
    """$7 Explosion Distant — длинный глухой шум, медленный decay.
    За 20 кадров R6 слегка сдвигается (шум темнеет)."""
    vols = env_exp(12, 20)
    r6_seq = [r6 + round(2 * i / 19) for i in range(20)]
    return build_sweep(r6_seq, vols)


def gen_08_tom_low(r6):
    """$8 Tom Low — коротко/средне, низкочастотный удар."""
    return build_const(r6, env_exp(14, 8))


def gen_09_tom_rumble(r6):
    """$9 Tom Rumble — более длинный низкочастотный удар.
    R6 плавно растёт на 2 шага (лёгкое падение высоты)."""
    vols = env_exp(13, 14)
    r6_seq = [r6 + round(2 * i / 13) for i in range(14)]
    return build_sweep(r6_seq, vols)


def gen_0A_kick_heavy(r6):
    """$A Heavy Kick — мощный короткий низкочастотный удар."""
    return build_const(r6, env_exp(15, 10))


def gen_0B_kick_tight(r6):
    """$B Tight Kick — короткий сухой удар, ~40-60 мс."""
    return build_const(r6, [15, 12, 8, 4, 0])


def gen_0C_rumble_sub(r6):
    """$C Rumble Sub — длинный низкочастотный rumble."""
    return build_const(r6, env_exp(12, 30))


def gen_0D_roar_ultra_low(r6):
    """$D Ultra Low Roar — очень длинный низкочастотный звук."""
    return build_const(r6, env_exp(13, 40))


def gen_0E_subbass_drop(r6):
    """$E Subbass Drop — R6 меняется во времени,
    создавая ощущение падения/изменения высоты.
    R6 растёт от 18 до максимума (частота падает)."""
    n = 20
    vols = env_exp(14, n)
    r6_seq = [18 + round((r6 - 18) * i / (n - 1)) for i in range(n)]
    return build_sweep(r6_seq, vols)


def gen_0F_crackle(r6):
    """$F Crackle — прерывистая последовательность
    коротких шумовых импульсов, не плавный decay."""
    # (длительность шума, громкость, длительность паузы)
    bursts = [
        (2, 13, 1), (2, 12, 1), (3, 11, 1),
        (2, 10, 1), (2,  8, 1), (1,  6, 1),
        (2,  5, 1), (1,  3, 1), (1,  2, 1),
        (1,  1, 0),
    ]
    frames = []
    for noise_dur, vol, gap in bursts:
        frames.extend([(r6, vol)] * noise_dur)
        if gap > 0:
            frames.extend([(r6, 0)] * gap)
    return frames


GENERATORS = [
    gen_00_hihat_closed,  gen_01_hihat_open,
    gen_02_snare_attack,  gen_03_snare_body,
    gen_04_snare_standard, gen_05_cymbal_crash,
    gen_06_snare_low,     gen_07_explosion_distant,
    gen_08_tom_low,       gen_09_tom_rumble,
    gen_0A_kick_heavy,    gen_0B_kick_tight,
    gen_0C_rumble_sub,    gen_0D_roar_ultra_low,
    gen_0E_subbass_drop,  gen_0F_crackle,
]


# =====================================================================
#   Главная
# =====================================================================

def main():
    os.makedirs(DIR, exist_ok=True)

    # Удалить старые .smp (любой формат имени)
    old_files = glob.glob(os.path.join(DIR, '*.smp'))
    for f in old_files:
        os.remove(f)

    # Рассчитать R6 для каждого инструмента
    r6_values = [freq_to_r6(f) for f in LFSR_FREQS]

    print('Генерация 16 шумовых семплов (LFSR-модель)')
    print(f'AY_CLK = {AY_CLK:.0f} Гц')
    print(f'Формула: F = {AY_CLK:.0f} / (32 * (R6 + 1))')
    print(f'Папка: {DIR}/\n')

    all_data = []

    for idx, (gen, name, freq) in enumerate(
            zip(GENERATORS, NAMES, LFSR_FREQS)):
        r6 = r6_values[idx]
        frames = gen(r6)
        fname = f'{idx:02X}_{name}.smp'
        path = os.path.join(DIR, fname)
        write_smp(path, frames)
        all_data.append((idx, name, r6, frames, path))

    # Таблица результатов
    print(f'{"INDEX":<7s}{"NAME":<22s}{"R6":<7s}{"FRAMES":<9s}{"MS"}')
    for idx, name, r6, frames, path in all_data:
        ms = len(frames) * 20       # 1 кадр = 20 мс (50 Гц)
        print(f'${idx:X}      {name:<22s}{r6:<7d}{len(frames):<9d}{ms}')

    # Проверки
    print()
    ok = True

    # 1. Все 16 файлов на месте
    expected = len(GENERATORS)
    actual = len(glob.glob(os.path.join(DIR, '*.smp')))
    if actual != expected:
        print(f'ОШИБКА: ожидалось {expected} файлов, получено {actual}')
        ok = False
    else:
        print(f'Файлов: {actual} (OK)')

    # 2. Корректный формат .smp
    for idx, name, r6, frames, path in all_data:
        with open(path, 'rb') as f:
            data = f.read()
        n = data[0]
        if len(data) != 1 + 2 * n:
            print(f'ОШИБКА формата: {os.path.basename(path)}:'
                  f' N={n}, байт {len(data)} (ождалось {1 + 2 * n})')
            ok = False
        for i in range(n):
            r6v = data[1 + 2 * i]
            r10v = data[2 + 2 * i]
            if r6v > 31 or r10v > 15:
                print(f'ОШИБКА данных: {os.path.basename(path)}'
                      f' кадр {i}: R6={r6v} R10={r10v}')
                ok = False

    if ok:
        print('Формат .smp: OK')

    # 3. Нет идентичных семплов
    raw = []
    for idx, name, r6, frames, path in all_data:
        with open(path, 'rb') as f:
            raw.append(f.read())
    dupes = 0
    for i in range(len(raw)):
        for j in range(i + 1, len(raw)):
            if raw[i] == raw[j]:
                print(f'ОШИБКА: ${i:X} и ${j:X} идентичны!')
                dupes += 1
                ok = False
    if dupes == 0:
        print('Все 16 семплов уникальны (OK)')

    print(f'\nГотово: {expected} семплов'
          f'{" — все проверки пройдены" if ok else " — ЕСТЬ ОШИБКИ"}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
