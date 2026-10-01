#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
midi2mus.py — конвертер Standard MIDI File в партитуру .mus для
компиллятора Вектора-06Ц (mus2inc.py).

Цепочка: *.mid -> midi2mus.py -> *.mus -> mus2inc.py -> *.inc.

В проекте нет MIDI-библиотек, поэтому файл разбирается собственным
лёгким парсером (формат 0/1, running status, карта темпа). Вся
дальнейшая работа (квантование в сетку PPQ=32, сворачивание пауз,
разложение длинных нот, поиск повторов) переиспользуется из
txt2mus.convert() и find_repeats — тот же проверенный код, что и для
NSF-экспорта.

Что делает конвертер:
  * темп НОРМАЛИЗУЕТСЯ: времена пересчитываются от постоянного темпа
    (--tempo, по умолчанию T118), рубато исходника игнорируется, доли
    равномерные — .mus хранит один глобальный темп;
  * все НЕ-ударные каналы сводятся в общий пул нот и РАЗБИВАЮТСЯ НА
    ГОЛОСА (voice separation): в каждой группе нот одного onset'а
    высшая нота уходит в score0 (мелодия), следующая — в score1,
    низшая — в score2; 4-я одновременная нота отбрасывается (у
    Вектора три тональных канала);
  * ударные: если в MIDI есть percussion-канал (9), его ноты
    отображаются в индексы nes-барабанов по таблице GM; иначе
    генерируется стандартный монофонический бэкбит (kick на 1 и 3,
    snare на 2 и 4, closed hi-hat на оффбитах) на всю длину пьесы.

Индексы ударных — это позиции в массиве nes_drums_samples[16]
(см. roms/musics/nes_drums): 0=Closed Hi-Hat, 1=Open Hi-Hat,
4=Standard Noise, 5=Cymbal Crash, 8=Low Tom, 9=Kick Drum и т.д.
Собирается .inc через `mus2inc.py --use-shared nes_drums`.

Использование:
    python3 utils/midi2mus.py theme.mid -o theme.mus
                             [--tempo 118] [--voices 3] [--no-drums]
"""

import argparse
import os
import struct
import sys

UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, UTILS_DIR)

import txt2mus          # noqa: E402  (квантование/эмиссия .mus)
import find_repeats     # noqa: E402  (сжатие повторов)

EPS = 1e-6

# Индексы nes-барабанов (массив nes_drums_samples[16]).
NES_HIHAT_CLOSED = 0
NES_HIHAT_OPEN = 1
NES_SNARE = 4
NES_CYMBAL = 5
NES_TOM = 8
NES_KICK = 9

# Ноты percussion-канала GM (по MIDI-спеке, барабаны 35..81) → nes-индекс.
GM_DRUM_MAP = {
    35: NES_KICK, 36: NES_KICK,
    38: NES_SNARE, 40: NES_SNARE, 37: NES_SNARE, 39: NES_SNARE,
    42: NES_HIHAT_CLOSED, 44: NES_HIHAT_CLOSED,
    46: NES_HIHAT_OPEN, 26: NES_HIHAT_OPEN,
    49: NES_CYMBAL, 51: NES_CYMBAL, 57: NES_CYMBAL, 52: NES_CYMBAL,
    41: NES_TOM, 43: NES_TOM, 45: NES_TOM, 47: NES_TOM,
    48: NES_TOM, 50: NES_TOM,
}


class MidiError(Exception):
    pass


# ------------------------------ парсер MIDI ------------------------------

def _read(data, pos, n):
    if pos + n > len(data):
        raise MidiError('MIDI: неожиданный конец файла')
    return data[pos:pos + n], pos + n


def _vlq(data, pos):
    value = 0
    while True:
        byte, pos = _read(data, pos, 1)
        b = byte[0]
        value = (value << 7) | (b & 0x7F)
        if not b & 0x80:
            return value, pos


def parse_midi(data):
    """SMF -> (ppq, notes, perc).

    notes — список (onset_tick, dur_tick, pitch) по всем НЕ-ударным
    каналам (единый пул для разбиения на голоса); perc — то же для
    percussion-канала 9. Темп-карта игнорируется (времена нормализуются
    от постоянного темпа), поэтому в тиках PPQ источника."""
    chunk, pos = _read(data, 0, 4)
    if chunk != b'MThd':
        raise MidiError('MIDI: нет заголовка MThd')
    hlen, pos = _read(data, pos, 4)
    hlen = struct.unpack('>I', hlen)[0]
    hdr, pos = _read(data, pos, hlen)
    fmt, ntrk, ppq = struct.unpack('>HHH', hdr[:6])
    if ppq & 0x8000:
        raise MidiError('MIDI: SMPTE-тайминг не поддерживается (нужен PPQ)')

    notes, perc = [], []
    for _ in range(ntrk):
        chunk, pos = _read(data, pos, 4)
        if chunk != b'MTrk':
            raise MidiError('MIDI: ожидался MTrk')
        tlen, pos = _read(data, pos, 4)
        tlen = struct.unpack('>I', tlen)[0]
        end = pos + tlen
        tick = 0
        running = None
        active = {}                       # (chan, pitch) -> onset_tick
        while pos < end:
            delta, pos = _vlq(data, pos)
            tick += delta
            status, pos = _read(data, pos, 1)
            sb = status[0]
            if sb < 0x80:                 # running status
                if running is None:
                    raise MidiError('MIDI: running status без префикса')
                msg = running
                pos -= 1                  # байт уже прочитан как данный
            else:
                msg = sb
                running = sb
            hi = msg & 0xF0
            chan = msg & 0x0F
            if msg == 0xFF:               # meta
                mtype, pos = _read(data, pos, 1)
                mlen, pos = _vlq(data, pos)
                _, pos = _read(data, pos, mlen)
                continue
            if msg in (0xF0, 0xF7):       # sysex
                slen, pos = _vlq(data, pos)
                _, pos = _read(data, pos, slen)
                continue
            if hi in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                b1b, pos = _read(data, pos, 1)
                b2b, pos = _read(data, pos, 1)
                pitch, vel = b1b[0], b2b[0]
                if hi == 0x90 and vel > 0:
                    active[(chan, pitch)] = tick
                elif hi in (0x80, 0x90):  # note off (или on с vel 0)
                    key = (chan, pitch)
                    onset = active.pop(key, None)
                    if onset is not None:
                        dur = max(tick - onset, 1)
                        (perc if chan == 9 else notes).append(
                            (onset, dur, pitch))
            elif hi in (0xC0, 0xD0):
                _, pos = _read(data, pos, 1)
            else:
                raise MidiError('MIDI: неизвестный статус 0x%02X' % msg)
        pos = end
    if not notes and not perc:
        raise MidiError('MIDI: не найдено ни одной ноты')
    notes.sort(key=lambda e: (e[0], -e[2]))
    perc.sort(key=lambda e: e[0])
    return ppq, notes, perc


# --------------------------- квантование по сетке -----------------------

def quantize_notes(notes, ppq, grid):
    """(onset_tick, dur_tick, pitch) -> (onset_beat, dur_beat, pitch),
    onset и конец прижимаются к ближайшей доле сетки 4/grid (16 =
    шестнадцатые). Минимальная длительность — один шаг сетки. Это
    убирает «живой» разброс тайминга MIDI и даёт чистые L-длительности."""
    step = 4.0 / grid       # N-я нота = 4/N доли (16 -> 0.25 = шестнадцатая)
    out = []
    for onset, dur, pitch in notes:
        ob = onset / ppq
        eb = (onset + dur) / ppq
        oq = round(ob / step) * step
        eq = round(eb / step) * step
        dq = max(eq - oq, step)
        out.append((oq, dq, pitch))
    out.sort(key=lambda e: (e[0], -e[2]))
    return out


# ------------------------- разбиение на голоса ---------------------------

def separate_voices(notes, nvoices=3):
    """Монофонические голоса из пула нот: [(onset_beat, dur_beat, pitch)]
    -> list. В каждой группе одного onset'а ноты сортируются по высоте
    вниз и раскладываются по свободным голосам от младшего индекса:
    высшая -> голос 0 (мелодия), средняя -> 1, низшая -> 2. Нота сверх
    числа свободных голосов отбрасывается (полифония > nvoices)."""
    voices = [[] for _ in range(nvoices)]
    free_at = [-1e9] * nvoices
    evs = sorted(notes, key=lambda e: (e[0], -e[2]))
    i, n = 0, len(evs)
    dropped = 0
    while i < n:
        onset = evs[i][0]
        group = []
        while i < n and abs(evs[i][0] - onset) < EPS:
            group.append(evs[i])
            i += 1
        group.sort(key=lambda e: -e[2])   # высота по убыванию
        for o, d, p in group:
            free = [v for v in range(nvoices) if free_at[v] <= o + EPS]
            if not free:
                dropped += 1
                continue
            pick = free[0]                # младший свободный -> мелодия
            voices[pick].append((o, d, p))
            free_at[pick] = o + d
    return voices, dropped


# --------------------------- генерация ударных --------------------------

def backbeat_events(total_beats):
    """Стандартный монофонический бэкбит 4/4 восьмыми:
    kick на 1 и 3, snare на 2 и 4, closed hi-hat на оффбитах.
    Возвращает [(beat, nes_index)]."""
    bars = int((total_beats + EPS) // 4)
    if (total_beats - bars * 4) > EPS:
        bars += 1
    out = []
    for bar in range(bars):
        base = bar * 4.0
        # 8 восьмых на такт; позиция в долях = base + k*0.5
        pattern = [NES_KICK, NES_HIHAT_CLOSED, NES_SNARE, NES_HIHAT_CLOSED,
                   NES_KICK, NES_HIHAT_CLOSED, NES_SNARE, NES_HIHAT_CLOSED]
        for k, idx in enumerate(pattern):
            out.append((base + k * 0.5, idx))
    return out


def perc_to_events(perc, ppq):
    """Ноты percussion-канала -> [(beat, nes_index)] (GM-карта)."""
    out = []
    for onset, _dur, pitch in perc:
        idx = GM_DRUM_MAP.get(pitch)
        if idx is None:
            continue                      # неизвестный барабан — пропускаем
        out.append((onset / ppq, idx))
    out.sort(key=lambda e: e[0])
    return out


# ----------------------------- сборка .mus ------------------------------

def build_mus(ppq, notes, perc, tempo, nvoices, use_drums, grid=16):
    """Словарь каналов для txt2mus.convert + текст .mus (с повторами)."""
    spb = 60.0 / tempo                  # секунд на долю (четверть)

    qnotes = quantize_notes(notes, ppq, grid)
    voices, dropped = separate_voices(qnotes, nvoices)

    chans = {'score0': [], 'score1': [], 'score2': [], 'drums': []}
    keys = ('score0', 'score1', 'score2')
    for vi, voice in enumerate(voices):
        if vi >= len(keys):
            break
        for onset, dur, pitch in voice:
            chans[keys[vi]].append({
                'start': onset * spb,
                'dur': dur * spb,
                'note': pitch,           # абсолютный номер (MIDI pitch)
            })

    total_beats = max((o + d) for o, d, _ in qnotes) if qnotes else 0.0
    if use_drums:
        if perc:
            drum_beats = perc_to_events(perc, ppq)
        else:
            drum_beats = backbeat_events(total_beats)
        for beat, idx in drum_beats:
            chans['drums'].append({
                'start': beat * spb,
                'dur': 0.5 * spb,
                'name': 'nes%d' % idx,
                'noise_idx': idx,
            })

    txt = {'framerate': tempo / 3.75, 'channels': chans}
    mus_text, _names = txt2mus.convert(txt, 'theme.mid', tempo,
                                       label='theme')

    # Сжатие повторов (как в txt2inc.py).
    header, sections = find_repeats.parse_mus(mus_text)
    out_lines = list(header)
    for name, tokens in sections:
        new_tokens = find_repeats.find_repeats(tokens)
        if name.startswith('score'):
            out_lines.append('score %s:' % name[5])
        else:
            out_lines.append('%s:' % name)
        out_lines.append(find_repeats.format_tokens(new_tokens))
    rep_text = '\n'.join(out_lines) + '\n'

    stats = {
        'voices': [len(v) for v in voices],
        'dropped': dropped,
        'drums': len(chans['drums']),
        'bars': int((total_beats + EPS) // 4) + (
            1 if (total_beats % 4) > EPS else 0),
        'beats': round(total_beats, 2),
        'tempo': tempo,
    }
    return rep_text, stats


def main():
    ap = argparse.ArgumentParser(
        description='Standard MIDI File -> партитура .mus Вектора-06Ц')
    ap.add_argument('midi', help='входной .mid')
    ap.add_argument('-o', '--output', help='выходной .mus (по умолчанию —'
                    ' имя .mid с расширением .mus)')
    ap.add_argument('--tempo', type=int, default=118,
                    help='нормализованный темп T (32..255), по умолчанию 118')
    ap.add_argument('--voices', type=int, default=3,
                    help='число тональных голосов 1..3 (по умолчанию 3)')
    ap.add_argument('--grid', type=int, default=16,
                    choices=(4, 8, 16, 32),
                    help='сетка квантования: 8=восьмые, 16=шестнадцатые'
                         ' (по умолчанию), 32=тридцать вторые')
    ap.add_argument('--no-drums', action='store_true',
                    help='не генерировать партию ударных')
    args = ap.parse_args()

    if not 32 <= args.tempo <= 255:
        ap.error('--tempo вне диапазона 32..255')
    if not 1 <= args.voices <= 3:
        ap.error('--voices должно быть 1..3')

    try:
        with open(args.midi, 'rb') as f:
            data = f.read()
        ppq, notes, perc = parse_midi(data)
    except (MidiError, OSError, struct.error) as e:
        print('midi2mus: %s' % e, file=sys.stderr)
        return 1

    mus_text, st = build_mus(ppq, notes, perc, args.tempo, args.voices,
                             not args.no_drums, args.grid)

    out = args.output or os.path.splitext(args.midi)[0] + '.mus'
    parent = os.path.dirname(os.path.abspath(out))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(mus_text)

    print('midi2mus: %s -> %s' % (args.midi, out))
    print('  PPQ источника %d, темп T%d, %.2f долей (~%d тактов)'
          % (ppq, st['tempo'], st['beats'], st['bars']))
    print('  голоса: score0=%d score1=%d score2=%d (отброшено %d)'
          % (st['voices'][0],
             st['voices'][1] if len(st['voices']) > 1 else 0,
             st['voices'][2] if len(st['voices']) > 2 else 0,
             st['dropped']))
    print('  ударных событий: %d' % st['drums'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
