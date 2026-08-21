#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
music2mus.py — конвертер извлечённых мелодий NES (текстовый экспорт
NSF) в партитуры .mus для компилятора Вектора-06Ц mus2inc.py.

Цепочка: *.txt -> music2mus.py -> *.mus -> mus2inc.py -> *.inc.
Внутренний байтовый формат NES (pulse*.bin и т.п.) больше не
разбирается: TXT является источником истины по времени и высотам.

Использование:
    python3 utils/music2mus.py track_0.txt [-o out.mus] [--tempo N]
                             [--verify] [--self-test]

Формат входа (экспорт Jackal.nsf, track_0.txt — эталон):
    Jackal.nsf track=0 framerate=60
    Square1(56)
    time dur note vol
    0.083 0.800 G1 10
    ...
    Noise(551)
    time dur noise vol drum
    0.000 0.017 0 12 hihat_closed_bright
    ...
Секции: Square1 -> score 0, Square2 -> score 1, Triangle -> score 2,
Noise и DPCM -> drums (все четыре партитуры — единая временная шкала).

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
CHANNELS = (('Square1', 'score0', 'tone'), ('Square2', 'score1', 'tone'),
            ('Triangle', 'score2', 'tone'), ('Noise', 'drums', 'drum'),
            ('DPCM', 'drums', 'dpcm'))
EPS = 1e-9


class ConvError(Exception):
    pass


# ------------------------------ разбор TXT ------------------------------

def parse_txt(text, fname):
    """TXT-экспорт NSF -> {'framerate': float,
    'channels': {'score0': [...], 'score1': [...], 'score2': [...],
    'drums': [...]}}; тоновые события: {'start', 'dur', 'note'}
    (абсолютный номер), ударные: {'start', 'dur', 'name'}."""
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
            key = dict((s[0], (s[1], s[2])) for s in CHANNELS)[m.group(1)]
            cur = key
            continue
        if line.startswith('time '):       # заголовок колонок секции
            continue
        if cur is None:
            raise ConvError(f'{fname}: данные вне секции: «{line}»')
        parts = line.split()
        key, kind = cur
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
        else:                               # Noise / DPCM
            if kind == 'drum':
                if len(parts) < 5:
                    raise ConvError(f'{fname}: строка Noise без имени'
                                    f' ударника: «{line}»')
                name = parts[4]
            else:                           # DPCM: реальные DMC-сэмлы NES:
                # C4 = dmc0_kick, C#4 = dmc1_snare (Bank7.ASM, DMC 0/1)
                a = (parse_note_name(parts[2], fname)
                     if len(parts) >= 3 else 48)
                name = {48: 'kick', 49: 'snare'}.get(a,
                       'dpcm_' + parts[2].lower())
            chans['drums'].append({'start': start, 'dur': dur,
                                   'name': name})
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
    label — имя для шапкого комментария (по умолчанию — fname)."""
    tps = tempo / 1.875         # тиков в секунду
    chans = txt['channels']

    drums = sorted(chans['drums'], key=lambda e: e['start'])
    names = []                  # стабильные индексы: порядок появления
    for e in drums:
        if e['name'] not in names:
            names.append(e['name'])
    if len(names) > 10:
        raise ConvError(f'{fname}: {len(names)} типов ударных —'
                        f' максимум 10: {", ".join(names)}')
    idx_of = {n: i for i, n in enumerate(names)}

    writers = {}
    lengths = {}
    for key in ('score0', 'score1', 'score2'):
        w = Writer()
        cur = 0
        for e in merge_tone(chans[key]):
            s = quant_ticks(e['start'], tps)
            if s > cur:
                w.rest(s - cur)
            end = quant_ticks(e['end'], tps)
            ticks = max(end - max(s, cur), 1)
            w.note(e['note'], ticks)
            cur = max(s, cur) + ticks
        writers[key] = w
        lengths[key] = cur

    w = Writer()
    cur = 0
    for i, e in enumerate(drums):
        s = quant_ticks(e['start'], tps)
        if s > cur:
            w.rest(s - cur)
        nxt = (quant_ticks(drums[i + 1]['start'], tps)
               if i + 1 < len(drums) else None)
        # для ударных ритм определяется интервалом до следующего
        # события, а не длительностью самого события (атака мгновенна)
        end = nxt if nxt is not None else quant_ticks(e['start'] + e['dur'], tps)
        ticks = max(end - max(s, cur), 1)
        w.hit(idx_of[e['name']], ticks)
        cur = max(s, cur) + ticks
    writers['drums'] = w
    lengths['drums'] = cur

    mismatch = len(set(v for v in lengths.values() if v > 0)) > 1
    base = os.path.splitext(os.path.basename(label or fname))[0]
    lines = [f'; {base}.mus — сгенерировано music2mus.py из'
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
        ref = merge_tone(txt['channels'][key])
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
    ref = sorted(txt['channels']['drums'], key=lambda e: e['start'])
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
        print(f'music2mus: {e}', file=sys.stderr)
        sys.exit(1)

    out = args.output or os.path.splitext(args.txt)[0] + '.mus'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(mus)
    n_ev = {k: len(v) for k, v in txt['channels'].items()}
    print(f'{os.path.basename(args.txt)}: темп T{tempo}, события'
          f' s0={n_ev["score0"]} s1={n_ev["score1"]}'
          f' s2={n_ev["score2"]} drums={n_ev["drums"]}, типы ударных:'
          f' {", ".join(f"{i}={n}" for i, n in enumerate(names)) or "нет"}')
    print(f'  -> {out}')
    if args.verify:
        sys.exit(verify(args.txt, txt, mus))


if __name__ == '__main__':
    main()
