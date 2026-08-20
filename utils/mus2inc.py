#!/usr/bin/env python3
#
# mus2inc.py — компилятор партитур Вектора-06Ц: .mus + .smp -> .inc.
#
# Формат .mus (текст, комментарии от ';' до конца строки):
#   Tempo: T<n>                — общий темп композиции (ударных в
#             минуту): один на все партитуры, можно указать вместо
#             T<n> в каждой партитуре; T<n> внутри партитуры обязан
#             ему соответствовать;
#   sample N: путь/к/файлу.smp   — объявление семпла ударных (N = 0..9);
#   score N: ...                 — партитура тонального канала (N = 0..2);
#   drums: ...                   — партитура ударных.
#
# Команды в партитурах (как в BASIC PLAY Вектора):
#   T<n>      темп, ударных в минуту (параметр композиции; один на все
#             партитуры, только до первого события; при заявленном
#             Tempo: может отсутствовать); по умолчанию T120;
#   O<n>      октава 1..7 (по умолчанию O4);
#   L<n>      длительность: 1,2,4,8,16,32,64,128 (по умолчанию L4);
#   P         пауза на текущую длительность;
#   C..B      ноты; '#' или '+' — диез, '-' — бемоль; цифра после ноты
#             или паузы — явная длительность этой ноты (C8, P16).
# Партитура ударных: цифры 0..9 — атака семпла с объявленным номером,
# P — пауза (звучащий семпл не обрывает), L/T как выше.
# '!' в любом месте файла — явно разрешить разную длину партитур.
#
# Время компилируется заранее (ТЗ §26): единая целочисленная сетка
# PPQ = 32 — четверть всегда 32 тика, L_n = 128/n (целое для всех
# L = 1..128, никаких округлений и дрейфа, ТЗ §27). Темп: T =
# четвертей в минуту, тиков за кадр 50 Гц = 32*T/60/50 = 4T/375
# (несократимая дробь, в runtime — аккумулятор Брешихэма).
# Ноты — в абсолютный хроматический номер. Никакого ASCII в байткоде.
#
# Байткод потока (константы MUS_* в lib/v06.h):
#   0x00        конец потока;
#   0x01..0x5F  нота, абсолютный номер = байт - 1 (октава*12 + полутон);
#   0x60        пауза на текущую длительность;
#   0xE1, len   текущая длительность в тиках сетки (четверть = 32).
#
# Формат .smp (бинарный): байт N — число кадров, затем N пар
# (R6, R10) — период шума и громкость канала C AY-3-8910, по одному
# кадру в тик 50 Гц.
#
# Использование:
#   python3 utils/mus2inc.py music/song.mus -o rom_data/song.inc --name song

import argparse
import math
import os
import re
import sys

MUS_END = 0x00
MUS_REST = 0x60
MUS_CMD_LEN = 0xE1

NOTE_BASE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
VALID_L = (1, 2, 4, 8, 16, 32, 64, 128)


class MusError(Exception):
    pass


def len_ticks(l_val):
    """Длительность L_n в тиках сетки PPQ = 32: четверть = 32 тика.
    128/n — целое для всех n = 1..128, округления не нужны."""
    return 128 // l_val


class Stream:
    def __init__(self, name, drums=False):
        self.name = name
        self.drums = drums
        self.oct = 4
        self.l_val = 4
        self.tempo = None       # T заявлен в этой партитуре
        self.len_locked = False # длительности уже считаются
        self.bytes = [MUS_CMD_LEN, 32]  # начальная длительность: L4 = 32
        self.ticks = 0
        self.events = 0

    def cur_len(self):
        return len_ticks(self.l_val)

    def set_len(self, l_val):
        self.l_val = l_val
        self.bytes += [MUS_CMD_LEN, self.cur_len()]

    def emit_event(self, code, l_override=None):
        """Событие (нота/пауза/атака) с текущей или явной длительностью."""
        if l_override is not None and l_override != self.l_val:
            saved = self.l_val
            self.set_len(l_override)
            self.bytes.append(code)
            self.ticks += self.cur_len()
            self.set_len(saved)
        else:
            self.bytes.append(code)
            self.ticks += self.cur_len()
        self.events += 1


def tokenize(body, fname, drums):
    """Разобрать тело партитуры на события. Возвращает список кортежей
    (kind, value): ('T', n), ('O', n), ('L', n), ('P', l|None),
    ('N', abs_note, l|None), ('D', sample_id), ('!',)."""
    toks = []
    pos = 0
    body = body.strip()
    while pos < len(body):
        m = re.match(r'\s+', body[pos:])
        if m:
            pos += m.end()
            continue
        c = body[pos]
        if c == '!':
            toks.append(('!',))
            pos += 1
            continue
        if drums and c.isdigit():
            toks.append(('D', int(c)))
            pos += 1
            continue
        m = re.match(r'T(\d+)', body[pos:], re.I)
        if m:
            toks.append(('T', int(m.group(1))))
            pos += m.end()
            continue
        m = re.match(r'O(\d+)', body[pos:], re.I)
        if m:
            toks.append(('O', int(m.group(1))))
            pos += m.end()
            continue
        m = re.match(r'L(\d+)', body[pos:], re.I)
        if m:
            toks.append(('L', int(m.group(1))))
            pos += m.end()
            continue
        m = re.match(r'P(\d+)?', body[pos:], re.I)
        if m:
            toks.append(('P', int(m.group(1)) if m.group(1) else None))
            pos += m.end()
            continue
        m = re.match(r'([A-G])([#\+\-])?(\d+)?', body[pos:], re.I)
        if m and not drums:
            semi = NOTE_BASE[m.group(1).upper()]
            acc = m.group(2)
            if acc in ('#', '+'):
                semi += 1
            elif acc == '-':
                semi -= 1
            toks.append(('N', semi,
                         int(m.group(3)) if m.group(3) else None))
            pos += m.end()
            continue
        ctx = body[pos:pos + 12].replace('\n', ' ')
        raise MusError(f'{fname}: непонятный токен «{ctx}»'
                       f' в секции {("drums" if drums else "score")}')
    return toks


def compile_stream(st, toks, fname, song_tempo_ref, allow_flag):
    """Скомпилировать токены в байткод. song_tempo_ref — одноэлементный
    список [T композиции]; T внутри партитуры обязан ему соответствовать
    и встречаться только до первого события. Длительности от темпа не
    зависят: сетка PPQ = 32, темп применяется в runtime."""
    for tok in toks:
        kind = tok[0]
        if kind == '!':
            allow_flag.append(1)
            continue
        if kind == 'T':
            t = tok[1]
            if not 32 <= t <= 255:
                raise MusError(f'{fname}: T{t} вне диапазона 32..255')
            if st.events or st.len_locked:
                raise MusError(f'{fname}: T{t} после событий/длительностей в'
                               f' «{st.name}» — темп задаётся до начала')
            st.tempo = t
            if song_tempo_ref[0] is None:
                song_tempo_ref[0] = t
            elif song_tempo_ref[0] != t:
                raise MusError(f'{fname}: темп T{t} в «{st.name}» не'
                               f' совпадает с T{song_tempo_ref[0]}')
            continue
        if kind == 'O':
            if not 1 <= tok[1] <= 7:
                raise MusError(f'{fname}: O{tok[1]} вне диапазона 1..7')
            st.oct = tok[1]
            continue
        if kind == 'L':
            if tok[1] not in VALID_L:
                raise MusError(f'{fname}: L{tok[1]} — допустимы'
                               ' 1,2,4,8,16,32,64,128')
            st.len_locked = True
            st.set_len(tok[1])
            continue
        if kind == 'P':
            st.len_locked = True
            l_ov = tok[1]
            if l_ov is not None and l_ov not in VALID_L:
                raise MusError(f'{fname}: P{l_ov} — недопустимая длительность')
            st.emit_event(MUS_REST, l_ov)
            continue
        if kind == 'N':
            st.len_locked = True
            semi, l_ov = tok[1], tok[2]
            if l_ov is not None and l_ov not in VALID_L:
                raise MusError(f'{fname}: нота с L{l_ov} — недопустимая'
                               ' длительность')
            abs_note = st.oct * 12 + semi
            if abs_note < 12:
                raise MusError(f'{fname}: нота в «{st.name}» ниже рабочей'
                               f' зоны ВИ53 (октава {st.oct})')
            if abs_note > 94:
                raise MusError(f'{fname}: нота в «{st.name}» выше байткода'
                               ' (максимум — октава 7, ре)')
            st.emit_event(abs_note + 1, l_ov)
            continue
        if kind == 'D':
            st.len_locked = True
            st.emit_event(tok[1] + 1)
            continue
    st.bytes.append(MUS_END)


HEADER_RE = re.compile(
    r'^\s*(?:score\s+([0-2])|drums|sample\s+([0-9])|(tempo))\s*:(.*)$',
    re.I)


def split_sections(text, fname):
    """Разбить .mus на секции. Возвращает (sections, samples, tempo):
    sections — список ('score0'|'drums', текст), samples — {N: путь},
    tempo — общий темп из строки «Tempo: T<n>» или None."""
    text = re.sub(r';[^\n]*', '', text)
    sections = []
    samples = {}
    tempo = None
    cur = None
    for line in text.split('\n'):
        m = HEADER_RE.match(line)
        if m:
            if m.group(3) is not None:      # Tempo: T<n> — общий темп
                tm = re.match(r'\s*T?(\d+)\s*$', m.group(4))
                if not tm:
                    raise MusError(f'{fname}: Tempo: не распознано:'
                                   f' «{m.group(4).strip()}»')
                t = int(tm.group(1))
                if not 32 <= t <= 255:
                    raise MusError(f'{fname}: Tempo: T{t} вне диапазона'
                                   ' 32..255')
                if tempo is not None and tempo != t:
                    raise MusError(f'{fname}: Tempo: объявлен дважды'
                                   f' с разными значениями ({tempo}, {t})')
                tempo = t
                continue
            if m.group(1) is not None:
                cur = ('score' + m.group(1), [])
                sections.append(cur)
                rest = m.group(4)
            elif m.group(2) is not None:
                idx = int(m.group(2))
                path = m.group(4).strip()
                if not path:
                    raise MusError(f'{fname}: sample {idx}: не указан файл')
                if idx in samples:
                    raise MusError(f'{fname}: sample {idx} объявлен дважды')
                samples[idx] = path
                cur = None
                rest = ''
            else:
                cur = ('drums', [])
                sections.append(cur)
                rest = m.group(4)
            if rest.strip():
                cur[1].append(rest)
        elif cur is not None:
            cur[1].append(line)
        elif line.strip():
            raise MusError(f'{fname}: данные вне секции: «{line.strip()}»')
    return sections, samples, tempo


def main():
    ap = argparse.ArgumentParser(description='.mus/.smp -> .inc для music.c')
    ap.add_argument('mus', help='файл партитуры .mus')
    ap.add_argument('-o', '--output', help='выходной .inc (по умолчанию'
                    ' имя .mus с расширением .inc)')
    ap.add_argument('--name', help='префикс символов C (по умолчанию —'
                    ' имя файла без расширения)')
    ap.add_argument('--allow-len-mismatch', action='store_true',
                    help='предупреждение вместо ошибки при разной длине'
                    ' партитур (то же, что «!» в .mus)')
    args = ap.parse_args()

    fname = args.mus
    out = args.output or os.path.splitext(fname)[0] + '.inc'
    name = args.name or os.path.splitext(os.path.basename(fname))[0]
    base_dir = os.path.dirname(os.path.abspath(fname))

    try:
        with open(fname, encoding='utf-8') as f:
            text = f.read()
        sections, sample_paths, global_tempo = split_sections(text, fname)

        streams = {'score0': Stream('score 0'),
                   'score1': Stream('score 1'),
                   'score2': Stream('score 2'),
                   'drums': Stream('drums', drums=True)}
        for sec_name, lines in sections:
            if sec_name in ('score0', 'score1', 'score2'):
                st = streams[sec_name]
            else:
                st = streams['drums']
            toks = tokenize('\n'.join(lines), fname, st.drums)
            st._toks = getattr(st, '_toks', []) + toks
        # темп — параметр композиции: общий Tempo: либо T в партитурах
        tempo_ref = [global_tempo]
        allow_flag = []
        for sec_name in ('score0', 'score1', 'score2', 'drums'):
            st = streams[sec_name]
            compile_stream(st, getattr(st, '_toks', []), fname,
                           tempo_ref, allow_flag)
        tempo = tempo_ref[0] or 120

        lengths = {k: st.ticks for k, st in streams.items() if st.events}
        if len(set(lengths.values())) > 1:
            msg = ('; '.join(f'{k}: {v} тиков'
                             for k, v in sorted(lengths.items())))
            if allow_flag or args.allow_len_mismatch:
                print(f'ВНИМАНИЕ: разная длина партитур ({msg})',
                      file=sys.stderr)
            else:
                raise MusError('разная длина партитур: ' + msg +
                               '; выровняйте длительности или поставьте «!»')
        song_len = max(lengths.values()) if lengths else 0

        # семплы
        sample_arrays = {}
        for idx, path in sorted(sample_paths.items()):
            smp_path = path if os.path.isabs(path) \
                else os.path.join(base_dir, path)
            with open(smp_path, 'rb') as f:
                data = f.read()
            if len(data) < 1:
                raise MusError(f'{fname}: {path}: пустой .smp')
            n = data[0]
            if len(data) != 1 + 2 * n:
                raise MusError(f'{fname}: {path}: заявлено кадров {n},'
                               f' байт {len(data)} (нужно {1 + 2 * n})')
            for i in range(n):
                r6, r10 = data[1 + 2 * i], data[2 + 2 * i]
                if r6 > 31 or r10 > 15:
                    raise MusError(f'{fname}: {path}: кадр {i}:'
                                   ' R6 должно быть 0..31, R10 0..15')
            sample_arrays[idx] = data

        # номера семплов в партитуре ударных обязаны быть объявлены
        used = set()
        for tok in getattr(streams['drums'], '_toks', []):
            if tok[0] == 'D':
                used.add(tok[1])
        for idx in sorted(used):
            if idx not in sample_paths:
                raise MusError(f'{fname}: семпл {idx} используется,'
                               ' но не объявлен (sample ' + str(idx) + ':)')

    except MusError as e:
        print(f'mus2inc: {e}', file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f'mus2inc: {e}', file=sys.stderr)
        sys.exit(1)

    g = math.gcd(4 * tempo, 375)
    tempo_num, tempo_den = 4 * tempo // g, 375 // g

    def cbytes(prefix, data):
        lines = [f'static const unsigned char {prefix}[] = {{']
        for i in range(0, len(data), 12):
            chunk = ', '.join(f'0x{b:02X}' for b in data[i:i + 12])
            lines.append('    ' + chunk + ',')
        lines.append('};')
        return '\n'.join(lines)

    parts = [f'/* {os.path.basename(out)} — сгенерирован mus2inc.py из'
             f' {os.path.basename(fname)}; не редактировать. */\n']
    for idx in sorted(sample_arrays):
        parts.append(cbytes(f'{name}_smp{idx}', sample_arrays[idx]))
    for key, suffix in (('score0', 's0'), ('score1', 's1'),
                        ('score2', 's2'), ('drums', 'dr')):
        parts.append(cbytes(f'{name}_{suffix}', streams[key].bytes))
    table = ', '.join(f'{name}_smp{i}' if i in sample_arrays else '0'
                      for i in range(10))
    parts.append(f'static const unsigned char * const {name}_samples[10]'
                 f' = {{\n    {table}\n}};')
    parts.append(f'static const music_song_t {name}_song = {{')
    parts.append(f'    {tempo_num}u, {tempo_den}u, {song_len}u,')
    parts.append(f'    {name}_s0, {name}_s1, {name}_s2, {name}_dr,')
    parts.append(f'    {name}_samples')
    parts.append('};')

    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts) + '\n')

    print(f'{os.path.basename(fname)}: темп T{tempo}'
          f' ({tempo_num}/{tempo_den} тика/кадр), длина {song_len} тиков')
    for key in ('score0', 'score1', 'score2', 'drums'):
        st = streams[key]
        print(f'  {key:7s}: событий {st.events:3d}, байткод'
              f' {len(st.bytes):4d} байт')
    print(f'  семплы: {", ".join(str(i) for i in sorted(sample_arrays)) or "нет"}')
    print(f'  -> {out}')


if __name__ == '__main__':
    main()
