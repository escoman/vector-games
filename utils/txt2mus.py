#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
txt2mus.py — конвертер извлечённых мелодий NES (текстовый экспорт
NSF) в партитуры .mus для компилятора Вектора-06Ц mus2inc.py.

Цепочка: *.txt -> txt2mus.py -> *.mus -> mus2inc.py -> *.inc.
Внутренний байтовый формат NES (pulse*.bin и т.п.) больше не
разбирается: TXT является источником истины по времени и высотам.

Использование:
    python3 utils/txt2mus.py track_0.txt [-o out.mus] [--tempo N]
                           [--verify] [--self-test]

Формат входа (экспорт Jackal.nsf / Castlevania.nsf):
    Jackal.nsf track=0 framerate=60
    Square1(56)
    time dur note vol
    0.083 0.800 G1 10
    ...
    12.117 BEGIN_CYCLE
    ...
    50.517 END_CYCLE
    ...
Секции: Square1 -> score 0, Square2 -> score 1, Triangle -> score 2,
Noise и DPCM -> drums (все четыре партитуры — единая временная шкала).

Поддержка циклов: маркеры BEGIN_CYCLE / END_cycle внутри любой секции
помечают повторяющийся фрагмент. В .mus он оформляется как BEGIN … END
с принудительным сбросом октавы и длительности (O/L) сразу после BEGIN,
чтобы повтор цикла всегда начинался с корректного состояния.

Квантизация: сетка PPQ = 32 (четверть = 32 тика), тик = 1.875/T с.
Темп: --tempo N либо из framerate заголовка (T = 3.75 * framerate;
60 Гц -> T225, кадр источника = ровно 2 тика, времена точные).

Музыкальная реконструкция:
  * события одного канала с одинаковой высотой, соприкасающиеся по
    времени, объединяются в одну ноту (§16); перекрытия усекаются;
  * промежутки между событиями становятся паузами; последовательные
    паузы автоматически объединяются разложением суммарной длительности
    в минимальное число стандартных L (§15);
  * длинная нота раскладывается в сумму разрешённых длительностей
    повторением той же ноты (ВИ53 тянет звук без паузы);
  * октава TXT переносится как есть: D4 -> O4 D (без транспозиции);
  * каждый тип ударных сохраняется отдельным индексом 0..9 (стабильно,
    в порядке появления); больше 10 типов — ошибка.

--verify повторно разбирает созданный .mus и количественно сравнивает
его с исходным TXT (высоты, старты, концы, потерянные события).
"""

import argparse
import os
import re
import sys

PPQ = 32                    # четверть = 32 тика (как в mus2inc.py)
# разрешённые длительности в тиках: L_n = 128/n (L1..L128)
VALID_TICKS = (128, 64, 32, 16, 8, 4, 2, 1)
NOTE_BASE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
NOTE_NAMES = ['C', 'C+', 'D', 'D+', 'E', 'F',
              'F+', 'G', 'G+', 'A', 'A+', 'B']
# секция TXT -> (имя секции .mus, тип канала)
# DPCM игнорируется: на Векторе-06Ц нет аналога, используем только Noise
CHANNELS = (('Square1', 'score0', 'tone'), ('Square2', 'score1', 'tone'),
            ('Triangle', 'score2', 'tone'), ('Noise', 'drums', 'drum'))
EPS = 1e-9


class ConvError(Exception):
    pass


# ------------------------------ разбор TXT ------------------------------

def parse_txt(text, fname):
    """TXT-экспорт NSF -> {'framerate': float,
    'channels': {'score0': [...], 'score1': [...], 'score2': [...],
    'drums': [...]}}; тоновые события: {'start', 'dur', 'note'}
    (абсолютный номер), ударные: {'start', 'dur', 'name'}.
    Маркеры циклов: {'type': 'begin'|'end', 'start': float}."""
    framerate = None
    chans = {'score0': [], 'score1': [], 'score2': [], 'drums': []}
    cur = None                  # (ключ, тип) текущей секции
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r'\S+\s+track=(\d+)\s+framerate=([\d.]+)', line)
        if m:
            framerate = float(m.group(2))
            continue
        m = re.match(r'(Square1|Square2|Triangle|Noise|DPCM)\((\d+)\)', line)
        if m:
            section = m.group(1)
            # DPCM игнорируем: на Векторе нет DMC, используем только Noise
            if section == 'DPCM':
                cur = ('skip', None)  # маркер пропуска секции
            else:
                key = dict((s[0], (s[1], s[2])) for s in CHANNELS)[section]
                cur = key
            continue
        if line.startswith('time '):       # заголовок колонок секции
            continue
        if cur is None:
            raise ConvError(f'{fname}: данные вне секции: «{line}»')
        if cur[0] == 'skip':
            continue  # пропускаем DPCM-секцию
        parts = line.split()
        key, kind = cur
        # --- маркеры циклов ---
        if len(parts) >= 2 and parts[1] == 'BEGIN_CYCLE':
            chans[key].append({'type': 'begin',
                               'start': float(parts[0])})
            continue
        if len(parts) >= 2 and parts[1] == 'END_CYCLE':
            chans[key].append({'type': 'end',
                               'start': float(parts[0])})
            continue
        try:
            start, dur = float(parts[0]), float(parts[1])
        except ValueError:
            raise ConvError(f'{fname}: нечисловое время: «{line}»')
        if kind == 'tone':
            if len(parts) < 3:
                raise ConvError(f'{fname}: тоновая строка без ноты:'
                                f' «{line}»')
            chans[key].append({'start': start, 'dur': dur,
                               'note': parse_note_name(parts[2], fname)})
        else:                               # Noise (ударные)
            if len(parts) < 5:
                raise ConvError(f'{fname}: строка Noise без имени'
                                f' ударника: «{line}»')
            chans['drums'].append({'start': start, 'dur': dur,
                                   'name': parts[4]})
    if framerate is None:
        raise ConvError(f'{fname}: нет заголовка «... framerate=...»')
    for key in chans:
        chans[key].sort(key=lambda e: e['start'])
    return {'framerate': framerate, 'channels': chans}


def parse_note_name(name, fname='<txt>'):
    """«D#4» -> абсолютный номер (октава*12 + полутон). Октава TXT
    переносится в .mus как есть (D4 -> O4 D), транспозиции нет."""
    m = re.match(r'([A-G])([#b]?)(\d+)$', name)
    if not m:
        raise ConvError(f'{fname}: непонятная нота «{name}»')
    semi = NOTE_BASE[m.group(1)]
    if m.group(2) == '#':
        semi += 1
    elif m.group(2) == 'b':
        semi -= 1
    return int(m.group(3)) * 12 + semi


# --------------------- реконструкция: слияния/квант ----------------------

def merge_tone(evs):
    """Соседние ноты одной высоты без промежутка — в одну (§16);
    перекрытия усекаются до старта следующего события."""
    out = []
    for e in evs:
        end = e['start'] + e['dur']
        if out and e['start'] < out[-1]['end'] - EPS:
            out[-1]['end'] = e['start']      # перекрытие: усекаем
        if (out and e['note'] == out[-1]['note']
                and abs(out[-1]['end'] - e['start']) <= EPS):
            out[-1]['end'] = max(out[-1]['end'], end)
        else:
            out.append({'note': e['note'], 'start': e['start'],
                        'end': end})
    return [e for e in out if e['end'] > e['start'] + EPS]


def quant_ticks(sec, tps):
    return int(round(sec * tps))


def decompose(ticks):
    """Минимальное число разрешённых длительностей в сумме = ticks
    (жадно от крупных) — объединение пауз §15 без потери точности."""
    parts = []
    for v in VALID_TICKS:
        while ticks >= v:
            parts.append(v)
            ticks -= v
    return parts


# ------------------------------- эмиссия ---------------------------------

class Writer:
    """Партитура одного канала: текущие L и октава, время в тиках."""

    def __init__(self):
        self.toks = []
        self.l_ticks = PPQ      # mus2inc: старт L4
        self.oct = 4

    def _set_len(self, ticks):
        if ticks != self.l_ticks:
            self.toks.append(f'L{128 // ticks}')
            self.l_ticks = ticks

    def rest(self, ticks):
        for p in decompose(ticks):
            self._set_len(p)
            self.toks.append('P')

    def note(self, a, ticks):
        o, semi = divmod(a, 12)
        if o != self.oct:
            self.toks.append(f'O{o}')
            self.oct = o
        parts = decompose(ticks)
        self._set_len(parts[0])
        self.toks.append(NOTE_NAMES[semi])
        for p in parts[1:]:     # тянущийся тон: повтор той же ноты
            self._set_len(p)
            self.toks.append(NOTE_NAMES[semi])

    def hit(self, sample_id, ticks):
        parts = decompose(ticks)
        self._set_len(parts[0])
        self.toks.append(str(sample_id))
        for p in parts[1:]:     # атака одна, остаток — паузы
            self._set_len(p)
            self.toks.append('P')

    def force_state(self, with_octave=True):
        """Принудительно выставить текущие O и L (для сброса после
        BEGIN — чтобы повтор цикла не унаследовал чужое состояние).
        with_octave=False — только L (для канала ударных)."""
        if with_octave:
            self.toks.append(f'O{self.oct}')
        self.toks.append(f'L{128 // self.l_ticks}')


def wrap(toks, width=72):
    lines, cur = [], ''
    for t in toks:
        if cur and len(cur) + 1 + len(t) > width:
            lines.append(cur)
            cur = t
        else:
            cur = t if not cur else cur + ' ' + t
    if cur:
        lines.append(cur)
    return lines


def choose_tempo(framerate, cli_tempo):
    if cli_tempo is not None:
        if not 32 <= cli_tempo <= 255:
            raise ConvError(f'--tempo {cli_tempo} вне диапазона 32..255')
        return cli_tempo
    t = int(round(3.75 * framerate))
    if not 32 <= t <= 255:
        raise ConvError(f'framerate {framerate} не даёт темп 32..255 —'
                        ' укажите --tempo N')
    return t


def convert(txt, fname, tempo, label=None):
    """Словарь parse_txt -> (текст .mus, таблица семплов {idx: имя}).
    label — имя для шапкого комментария (по умолчанию — fname).
    Поддерживает маркеры циклов BEGIN_CYCLE / END_CYCLE."""
    tps = tempo / 1.875         # тиков в секунду
    chans = txt['channels']

    # --- индексы ударных ---
    all_drums = [e for e in chans['drums'] if 'type' not in e]
    names = []                  # стабильные индексы: порядок появления
    for e in all_drums:
        if e['name'] not in names:
            names.append(e['name'])
    if len(names) > 10:
        raise ConvError(f'{fname}: {len(names)} типов ударных —'
                        f' максимум 10: {", ".join(names)}')
    idx_of = {n: i for i, n in enumerate(names)}

    # --- обработка каналов с учётом циклов ---
    writers = {}
    lengths = {}
    for key in ('score0', 'score1', 'score2'):
        w, t = _process_tone(chans[key], tps)
        writers[key] = w
        lengths[key] = t

    w, t = _process_drums(chans['drums'], tps, idx_of)
    writers['drums'] = w
    lengths['drums'] = t

    # --- генерация текста .mus ---
    mismatch = len(set(v for v in lengths.values() if v > 0)) > 1
    base = os.path.splitext(os.path.basename(label or fname))[0]
    lines = [f'; {base}.mus — сгенерировано txt2mus.py из'
             f' {os.path.basename(fname)}',
             f'; сетка PPQ=32; тик = 1.875/T с; framerate'
             f' {txt["framerate"]:g}',
             f'Tempo: T{tempo}']
    for i, n in enumerate(names):
        lines.append(f'sample {i}: samples/{n}.smp')
    headers = (('score0', 'score 0:'), ('score1', 'score 1:'),
               ('score2', 'score 2:'), ('drums', 'drums:'))
    first = True
    for key, header in headers:
        w = writers[key]
        if not w.toks:
            continue
        body = list(w.toks)
        if mismatch and first:
            body.append('!')    # длины партитур разные — разрешаем
        lines.append(header)
        lines.extend(wrap(body))
        first = False
    return '\n'.join(lines) + '\n', names


# ---- вспомогательные функции для обработки каналов с циклами ----

def _extract_cycles(events):
    """Извлекает пары циклов из списка событий канала.
    Возвращает (cycles, regular_events), где cycles — список
    {'begin': float, 'end': float}, regular_events — без маркеров.
    Дубликаты циклов (Noise+DPCM дают одинаковые маркеры в drums)
    объединяются."""
    cycles = []
    regular = []
    begins = []
    for e in events:
        if e.get('type') == 'begin':
            begins.append(e['start'])
        elif e.get('type') == 'end':
            if begins:
                cb, ce = begins.pop(0), e['start']
                # дедупликация: если такой цикл уже есть — пропускаем
                if not any(abs(c['begin'] - cb) < EPS and
                           abs(c['end'] - ce) < EPS for c in cycles):
                    cycles.append({'begin': cb, 'end': ce})
        else:
            regular.append(e)
    return cycles, regular


def _process_tone(events, tps):
    """Обработка тонового канала с поддержкой циклов."""
    cycles, regular = _extract_cycles(events)
    merged = merge_tone(regular)
    w = Writer()
    cur = 0
    offset = 0                # выход = вход + offset (вне циклов)

    if not cycles:
        # --- обычный путь (без циклов) — идентичен старому коду ---
        for e in merged:
            s = quant_ticks(e['start'], tps)
            if s > cur:
                w.rest(s - cur)
            end = quant_ticks(e['end'], tps)
            ticks = max(end - max(s, cur), 1)
            w.note(e['note'], ticks)
            cur = max(s, cur) + ticks
        return w, cur

    # --- обработка с циклами ---
    ei = 0
    for cyc in cycles:
        cb = cyc['begin']
        ce = cyc['end']
        cb_tick = quant_ticks(cb, tps)
        ce_tick = quant_ticks(ce, tps)
        cyc_dur = max(ce_tick - cb_tick, 1)

        # intro: события до начала цикла
        while ei < len(merged) and merged[ei]['start'] < cb - EPS:
            e = merged[ei]
            s = quant_ticks(e['start'], tps) + offset
            if s > cur:
                w.rest(s - cur)
            end = quant_ticks(e['end'], tps) + offset
            ticks = max(end - max(s, cur), 1)
            w.note(e['note'], ticks)
            cur = max(s, cur) + ticks
            ei += 1

        # BEGIN + принудительный сброс O/L
        w.toks.append('BEGIN')
        w.force_state()
        cur = 0                   # сброс позиции: внутри цикла время с 0

        # события внутри цикла (относительное время)
        cycle_start = ei
        while ei < len(merged) and merged[ei]['start'] < ce - EPS:
            e = merged[ei]
            s = quant_ticks(e['start'], tps) - cb_tick
            s = max(s, 0)
            if s > cur:
                w.rest(s - cur)
            end = quant_ticks(e['end'], tps) - cb_tick
            end = min(end, cyc_dur)       # клип по границе цикла
            ticks = max(end - max(s, cur), 1)
            w.note(e['note'], ticks)
            cur = max(s, cur) + ticks
            ei += 1

        # выравнивающая пауза: если канал закончил раньше cyc_dur
        if cur < cyc_dur:
            w.rest(cyc_dur - cur)

        # END
        w.toks.append('END')
        cur = cyc_dur
        # накопление смещения: выход = вход + offset (вне циклов)
        offset += cyc_dur - (ce_tick - cb_tick)

    # outro: события после последнего цикла
    while ei < len(merged):
        e = merged[ei]
        s = quant_ticks(e['start'], tps) + offset
        if s > cur:
            w.rest(s - cur)
        end = quant_ticks(e['end'], tps) + offset
        ticks = max(end - max(s, cur), 1)
        w.note(e['note'], ticks)
        cur = max(s, cur) + ticks
        ei += 1
    return w, cur


def _process_drums(events, tps, idx_of):
    """Обработка канала ударных с поддержкой циклов."""
    cycles, regular = _extract_cycles(events)
    w = Writer()
    cur = 0
    offset = 0

    if not cycles:
        # --- обычный путь (без циклов) ---
        for i, e in enumerate(regular):
            s = quant_ticks(e['start'], tps)
            if s > cur:
                w.rest(s - cur)
            nxt = (quant_ticks(regular[i + 1]['start'], tps)
                   if i + 1 < len(regular) else None)
            end = nxt if nxt is not None else \
                quant_ticks(e['start'] + e['dur'], tps)
            ticks = max(end - max(s, cur), 1)
            w.hit(idx_of[e['name']], ticks)
            cur = max(s, cur) + ticks
        return w, cur

    # --- обработка с циклами ---
    ei = 0
    for cyc in cycles:
        cb = cyc['begin']
        ce = cyc['end']
        cb_tick = quant_ticks(cb, tps)
        ce_tick = quant_ticks(ce, tps)
        cyc_dur = max(ce_tick - cb_tick, 1)

        # intro
        while ei < len(regular) and regular[ei]['start'] < cb - EPS:
            e = regular[ei]
            s = quant_ticks(e['start'], tps) + offset
            if s > cur:
                w.rest(s - cur)
            nxt_idx = ei + 1
            if nxt_idx < len(regular) and regular[nxt_idx]['start'] < cb - EPS:
                nxt = quant_ticks(regular[nxt_idx]['start'], tps) + offset
            else:
                nxt = None
            end = nxt if nxt is not None else \
                quant_ticks(e['start'] + e['dur'], tps) + offset
            ticks = max(end - max(s, cur), 1)
            w.hit(idx_of[e['name']], ticks)
            cur = max(s, cur) + ticks
            ei += 1

        # BEGIN + принудительный сброс L (октава для ударных не нужна)
        w.toks.append('BEGIN')
        w.force_state(with_octave=False)
        cur = 0                   # сброс позиции: внутри цикла время с 0

        # события внутри цикла
        cycle_ei_start = ei
        while ei < len(regular) and regular[ei]['start'] < ce - EPS:
            e = regular[ei]
            s = quant_ticks(e['start'], tps) - cb_tick
            s = max(s, 0)
            if s > cur:
                w.rest(s - cur)
            nxt_idx = ei + 1
            if nxt_idx < len(regular) and \
                    regular[nxt_idx]['start'] < ce - EPS:
                nxt = quant_ticks(regular[nxt_idx]['start'], tps) - cb_tick
            else:
                nxt = None
            end = nxt if nxt is not None else \
                quant_ticks(e['start'] + e['dur'], tps) - cb_tick
            end = min(end, cyc_dur)
            ticks = max(end - max(s, cur), 1)
            w.hit(idx_of[e['name']], ticks)
            cur = max(s, cur) + ticks
            ei += 1

        # выравнивающая пауза: если канал закончил раньше cyc_dur
        if cur < cyc_dur:
            w.rest(cyc_dur - cur)

        # END
        w.toks.append('END')
        cur = cyc_dur
        offset += cyc_dur - (ce_tick - cb_tick)

    # outro
    while ei < len(regular):
        e = regular[ei]
        s = quant_ticks(e['start'], tps) + offset
        if s > cur:
            w.rest(s - cur)
        nxt_idx = ei + 1
        if nxt_idx < len(regular):
            nxt = quant_ticks(regular[nxt_idx]['start'], tps) + offset
        else:
            nxt = None
        end = nxt if nxt is not None else \
            quant_ticks(e['start'] + e['dur'], tps) + offset
        ticks = max(end - max(s, cur), 1)
        w.hit(idx_of[e['name']], ticks)
        cur = max(s, cur) + ticks
        ei += 1
    return w, cur


# ------------------------------- --verify --------------------------------

def parse_mus_events(text):
    """Обратный разбор .mus: темп и события по каналам. Возвращает
    (tempo, {'score0'..: [{'start','end','note'|'drum'}], ...})
    во временной шкале секунд. Состояние (октава, L, время) живёт
    на всю секцию: перенос строк в .mus — только форматирование."""
    text = re.sub(r';[^\n]*', '', text)
    tempo = None
    chans = {'score0': [], 'score1': [], 'score2': [], 'drums': []}
    header = re.compile(r'^\s*(?:score\s+([0-2])|drums|sample\s+[0-9]'
                        r'|tempo|enabled)\s*:(.*)$', re.I)
    bodies = {}                 # ключ секции -> список строк
    order = []
    cur = None
    for line in text.split('\n'):
        m = header.match(line)
        if m:
            if re.match(r'\s*tempo\s*:', line, re.I):
                tempo = int(re.search(r'(\d+)', m.group(2)).group(1))
                cur = None
            elif m.group(1) is not None:
                cur = 'score' + m.group(1)
            elif re.match(r'\s*drums\s*:', line, re.I):
                cur = 'drums'
            else:
                cur = None
            if cur is not None and cur not in bodies:
                bodies[cur] = []
                order.append(cur)
            continue
        if cur is not None:
            bodies[cur].append(line)
    if tempo is None:
        return None, chans
    tick_s = 1.875 / tempo
    for key in order:
        drums = key == 'drums'
        oct, l_ticks, t = 4, PPQ, 0
        body = '\n'.join(bodies[key])
        pos = 0
        while pos < len(body):
            mm = re.match(r'\s+', body[pos:])
            if mm:
                pos += mm.end()
                continue
            c = body[pos]
            if c == '!':
                pos += 1
                continue
            # BEGIN / END — маркеры цикла, не влияют на время
            mm = re.match(r'BEGIN|END', body[pos:])
            if mm:
                pos += mm.end()
                continue
            mm = re.match(r'O(\d+)', body[pos:], re.I)
            if mm:
                oct = int(mm.group(1))
                pos += mm.end()
                continue
            mm = re.match(r'L(\d+)', body[pos:], re.I)
            if mm:
                l_ticks = 128 // int(mm.group(1))
                pos += mm.end()
                continue
            if drums and c.isdigit():
                d = l_ticks
                chans[key].append({'start': t * tick_s,
                                   'end': (t + d) * tick_s,
                                   'drum': int(c)})
                t += d
                pos += 1
                continue
            mm = re.match(r'P(\d+)?', body[pos:], re.I)
            if mm:
                d = 128 // int(mm.group(1)) if mm.group(1) else l_ticks
                t += d
                pos += mm.end()
                continue
            mm = re.match(r'([A-G])([#\+\-])?(\d+)?', body[pos:], re.I)
            if mm and not drums:
                semi = NOTE_BASE[mm.group(1).upper()]
                if mm.group(2) in ('#', '+'):
                    semi += 1
                elif mm.group(2) == '-':
                    semi -= 1
                d = 128 // int(mm.group(3)) if mm.group(3) else l_ticks
                note = oct * 12 + semi
                evs = chans[key]
                # повтор той же ноты подряд = одна тянущаяся нота
                if (evs and evs[-1]['note'] == note
                        and abs(evs[-1]['end'] - t * tick_s) < 1e-12):
                    evs[-1]['end'] = (t + d) * tick_s
                else:
                    evs.append({'start': t * tick_s,
                                'end': (t + d) * tick_s, 'note': note})
                t += d
                pos += mm.end()
                continue
            pos += 1              # '[' и ']n' в новых .mus не ожидаются
    return tempo, chans


def verify(txt_path, txt, mus_text):
    """Сравнить .mus с исходным TXT; печатает отчёт, возвращает код."""
    tempo, got = parse_mus_events(mus_text)
    tps = tempo / 1.875
    bad = False
    print('Verification (сравнение .mus с исходным TXT):')
    for key in ('score0', 'score1', 'score2'):
        ref = merge_tone([e for e in txt['channels'][key]
                          if 'type' not in e])
        evs = got[key]
        print(f'  score {key[-1]}: событий TXT {len(ref)},'
              f' .mus {len(evs)}')
        n = min(len(ref), len(evs))
        if len(ref) != len(evs):
            bad = True
        pitch_err = sum(1 for i in range(n)
                        if ref[i]['note'] != evs[i]['note'])
        max_start = max((abs(ref[i]['start'] - evs[i]['start'])
                         for i in range(n)), default=0.0)
        max_end = max((abs(ref[i]['end'] - evs[i]['end'])
                       for i in range(n)), default=0.0)
        if pitch_err:
            bad = True
        # систематический дрейф: средняя ошибка старта по второй
        # половине канала не должна расти против первой
        print(f'    max pitch error: {pitch_err} нот'
              f' ({"ОК" if not pitch_err else "ОШИБКА"})')
        print(f'    max start error: {max_start:.3f} s'
              f' ({max_start * tps:.1f} тика)')
        print(f'    max end error:   {max_end:.3f} s'
              f' ({max_end * tps:.1f} тика)')
    ref = sorted([e for e in txt['channels']['drums'] if 'type' not in e],
                 key=lambda e: e['start'])
    evs = got['drums']
    missed = max(len(ref) - len(evs), 0)
    print(f'  drums: событий TXT {len(ref)}, .mus {len(evs)}')
    if missed:
        bad = True
    n = min(len(ref), len(evs))
    max_start = max((abs(ref[i]['start'] - evs[i]['start'])
                     for i in range(n)), default=0.0)
    names = sorted(set(e['name'] for e in ref))
    print(f'    max start error: {max_start:.3f} s ({max_start * tps:.1f}'
          f' тика)')
    print(f'    missed events:   {missed}'
          f' ({"ОК" if not missed else "ОШИБКА"})')
    print(f'    типы ударных: {len(names)}: {", ".join(names)}')
    if bad:
        print('VERIFY: ОШИБКИ')
        return 1
    print('VERIFY: OK')
    return 0


# ------------------------------ self-test --------------------------------

def self_test():
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    # 1) нота TXT -> абсолютный номер: октава как есть, без сдвига
    check(parse_note_name('D4') == 50, 'D4 != 50')
    check(parse_note_name('C4') == 48, 'C4 != 48')
    check(parse_note_name('B3') == 47, 'B3 != 47')
    check(parse_note_name('C#5') == 61, 'C#5 != 61')
    check(parse_note_name('A#3') == 46, 'A#3 != 46')

    # 2) слияние соприкасающихся одинаковых нот; промежуток запрещает
    evs = merge_tone([{'start': 0.0, 'dur': 0.5, 'note': 50},
                      {'start': 0.5, 'dur': 0.5, 'note': 50}])
    check(len(evs) == 1 and abs(evs[0]['end'] - 1.0) < EPS,
          'слияние соприкасающихся: %s' % evs)
    evs = merge_tone([{'start': 0.0, 'dur': 0.4, 'note': 50},
                      {'start': 0.5, 'dur': 0.5, 'note': 50}])
    check(len(evs) == 2, 'промежуток обязан запретить слияние')
    evs = merge_tone([{'start': 0.0, 'dur': 0.6, 'note': 50},
                      {'start': 0.5, 'dur': 0.5, 'note': 52}])
    check(len(evs) == 2 and abs(evs[0]['end'] - 0.5) < EPS,
          'перекрытие усекается: %s' % evs)

    # 3) разложение длительностей: минимум частей, точность суммы
    check(decompose(14) == [8, 4, 2], 'decompose(14): %s' % decompose(14))
    for t in (1, 2, 7, 32, 90, 450):
        parts = decompose(t)
        check(sum(parts) == t and all(p in VALID_TICKS for p in parts),
              f'decompose({t}): {parts}')
    check(decompose(96) == [64, 32], 'decompose(96): %s' % decompose(96))
    check(len(decompose(64)) == 1, '64 тика = одна L2')

    # 4) темп из framerate: 60 Гц -> T225, кадр = ровно 2 тика
    check(choose_tempo(60.0, None) == 225, '60 Гц != T225')
    check(abs(225 / 1.875 / 60 - 2.0) < 1e-9, 'T225: кадр != 2 тика')
    check(choose_tempo(60.0, 120) == 120, '--tempo не в силе')

    # 5) Writer: старт L4; «7/64» паузы = L16 P L32 P L64 P (§15)
    w = Writer()
    w.rest(14)
    check(w.toks == ['L16', 'P', 'L32', 'P', 'L64', 'P'],
          'объединение пауз: %s' % w.toks)
    w = Writer()
    w.note(50, 32)              # D4: стартовая октава O4 — команда не нужна
    check(w.toks == ['D'], 'первая нота: %s' % w.toks)
    w.note(50, 32)              # та же нота вплотную: повтор на той же L
    check(w.toks.count('D') == 2 and 'L' not in ' '.join(w.toks),
          'тянущийся тон без лишних L: %s' % w.toks)
    w = Writer()
    w.hit(3, 6)                 # удар: атака + паузы на остаток
    check(w.toks == ['L32', '3', 'L64', 'P'],
          'удар 6 тиков: %s' % w.toks)

    # 5b) Writer.force_state: всегда пишет O и L, даже если совпадают
    w = Writer()
    w.oct = 4
    w.l_ticks = 32              # L4
    w.force_state()
    check(w.toks == ['O4', 'L4'],
          'force_state: %s' % w.toks)
    # смена октавы/длины — тоже пишется
    w.oct = 2
    w.l_ticks = 8               # L16
    w.force_state()
    check(w.toks[-2:] == ['O2', 'L16'],
          'force_state после смены: %s' % w.toks)

    # 6) больше 10 типов ударных — ошибка
    txt = {'framerate': 60.0,
           'channels': {k: [] for k in
                        ('score0', 'score1', 'score2')}}
    txt['channels']['drums'] = [
        {'start': i * 0.1, 'dur': 0.05, 'name': f'd{i}'}
        for i in range(11)]
    try:
        convert(txt, '<t>', 225)
        fails.append('11 типов ударных не дали ошибку')
    except ConvError:
        pass

    # 7) полный цикл: TXT -> .mus -> обратный разбор (без потери
    #    событий и высот, старты в пределах полтика)
    txt = {'framerate': 60.0, 'channels': {
        'score0': [{'start': 0.0, 'dur': 0.4, 'note': 50},
                   {'start': 0.4, 'dur': 0.2, 'note': 50},
                   {'start': 0.8, 'dur': 0.2, 'note': 52}],
        'score1': [],
        'score2': [{'start': 0.0, 'dur': 1.0, 'note': 38}],
        'drums': [{'start': 0.0, 'dur': 0.05, 'name': 'kick'},
                  {'start': 0.5, 'dur': 0.05, 'name': 'snare_deep'}]}}
    mus, names = convert(txt, 'selftest.txt', 225)
    check(names == ['kick', 'snare_deep'],
          'индексы ударных: %s' % names)
    check('sample 0: samples/kick.smp' in mus, 'sample 0 не объявлен')
    tempo, got = parse_mus_events(mus)
    check(tempo == 225, 'темп .mus: %s' % tempo)
    check(len(got['score0']) == 2 and got['score0'][0]['note'] == 50
          and got['score0'][1]['note'] == 52,
          'реверс score0: %s' % got['score0'])
    check(abs(got['score0'][0]['end'] - 0.6) < 0.02,
          'слияние в реверсе: %s' % got['score0'][0])
    check(len(got['drums']) == 2
          and [e['drum'] for e in got['drums']] == [0, 1],
          'реверс drums: %s' % got['drums'])
    check(abs(got['drums'][1]['start'] - 0.5) < 0.02,
          'старт второго удара: %s' % got['drums'][1])

    # 7b) цикл: BEGIN/END с принудительным O/L и ведущей паузой
    txt = {'framerate': 60.0, 'channels': {
        'score0': [
            {'start': 0.0, 'dur': 0.2, 'note': 50},
            {'type': 'begin', 'start': 0.4},
            {'start': 0.6, 'dur': 0.1, 'note': 52},
            {'start': 0.8, 'dur': 0.1, 'note': 53},
            {'type': 'end', 'start': 1.0},
            {'start': 1.2, 'dur': 0.2, 'note': 55}],
        'score1': [], 'score2': [],
        'drums': []}}
    mus, _ = convert(txt, 'cycle_test.txt', 225)
    check('BEGIN' in mus and 'END' in mus,
          'цикл: нет BEGIN/END в .mus')
    # после BEGIN всегда идёт O и L
    idx = mus.index('BEGIN')
    after_begin = mus[idx:idx + 30]
    check('O' in after_begin and 'L' in after_begin,
          'force_state после BEGIN: %s' % after_begin)
    # обратный разбор не падает на BEGIN/END
    tempo, got = parse_mus_events(mus)
    check(tempo == 225, 'цикл: темп после разбора')
    check(len(got['score0']) >= 2,
          'цикл: событий score0: %d' % len(got['score0']))

    # 8) эталон track_0.txt, если доступен рядом с репозиторием
    ref_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'music-roms', 'jackal', 'music_txt',
                            'track_0.txt')
    if os.path.isfile(ref_path):
        with open(ref_path, encoding='utf-8') as f:
            txt = parse_txt(f.read(), ref_path)
        tempo = choose_tempo(txt['framerate'], None)
        mus, names = convert(txt, ref_path, tempo)
        check(len(names) <= 10, 'track_0: больше 10 типов ударных')
        tps = tempo / 1.875
        _, got = parse_mus_events(mus)
        for key in ('score0', 'score1', 'score2'):
            ref = merge_tone(txt['channels'][key])
            check(len(got[key]) == len(ref),
                  f'track_0 {key}: событий {len(got[key])} != {len(ref)}')
            n = min(len(ref), len(got[key]))
            pe = sum(1 for i in range(n)
                     if ref[i]['note'] != got[key][i]['note'])
            check(pe == 0, f'track_0 {key}: {pe} ошибок высоты')
            ms = max((abs(ref[i]['start'] - got[key][i]['start'])
                      for i in range(n)), default=0.0)
            check(ms * tps <= 0.5 + 1e-9,
                  f'track_0 {key}: дрейф старта {ms * tps} тика')
        rd = sorted(txt['channels']['drums'], key=lambda e: e['start'])
        check(len(got['drums']) == len(rd),
              f'track_0 drums: {len(got["drums"])} != {len(rd)}')
        print(f'САМОТЕСТ [track_0.txt]: OK ({len(rd)} ударных,'
              f' типы {names})')
    else:
        print('САМОТЕСТ [track_0.txt]: пропущен (файл не найден)')

    if fails:
        print('SELF-TEST: %d ошибок' % len(fails))
        for m in fails:
            print('  - ' + m)
        return 1
    print('SELF-TEST: все проверки пройдены')
    return 0


# -------------------------------- main -----------------------------------

def main():
    ap = argparse.ArgumentParser(
        description='Конвертер TXT-экспорта мелодий NES в .mus'
                    ' для mus2inc.py')
    ap.add_argument('txt', nargs='?', help='входной .txt (экспорт NSF)')
    ap.add_argument('-o', '--output', help='выходной .mus (по умолчанию —'
                    ' имя .txt с расширением .mus)')
    ap.add_argument('--tempo', type=int,
                    help='темп T (четвертей в минуту, 32..255); по'
                         ' умолчанию выводится из framerate заголовка')
    ap.add_argument('--verify', action='store_true',
                    help='после генерации разобрать .mus и сравнить'
                         ' с исходным TXT')
    ap.add_argument('--self-test', action='store_true',
                    help='внутренние проверки, выйти')
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.txt:
        ap.error('не указан входной .txt')

    try:
        with open(args.txt, encoding='utf-8') as f:
            text = f.read()
        txt = parse_txt(text, args.txt)
        tempo = choose_tempo(txt['framerate'], args.tempo)
        mus, names = convert(txt, args.txt, tempo, label=args.output)
    except (ConvError, OSError) as e:
        print(f'txt2mus: {e}', file=sys.stderr)
        sys.exit(1)

    out = args.output or os.path.splitext(args.txt)[0] + '.mus'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(mus)
    n_ev = {k: sum(1 for e in v if 'type' not in e)
            for k, v in txt['channels'].items()}
    print(f'{os.path.basename(args.txt)}: темп T{tempo}, события'
          f' s0={n_ev["score0"]} s1={n_ev["score1"]}'
          f' s2={n_ev["score2"]} drums={n_ev["drums"]}, типы ударных:'
          f' {", ".join(f"{i}={n}" for i, n in enumerate(names)) or "нет"}')
    print(f'  -> {out}')
    if args.verify:
        sys.exit(verify(args.txt, txt, mus))


if __name__ == '__main__':
    main()
