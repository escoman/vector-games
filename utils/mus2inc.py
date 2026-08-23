#!/usr/bin/env python3
#
# mus2inc.py — компилятор партитур Вектора-06Ц: .mus + .smp -> .inc.
#
# Формат .mus (текст, комментарии от ';' до конца строки):
#   Tempo: T<n>                — общий темп композиции (ударных в
#             минуту): один на все партитуры, можно указать вместо
#             T<n> в каждой партитуре; T<n> внутри партитуры обязан
#             ему соответствовать;
#   Enabled: 0 1 2 D           — необязательный: какие каналы играть
#             (0..2 — тоновые партитуры, D — ударные); не указанные
#             каналы в .inc не попадают (указатель 0 в music_song_t,
#             рантайм поток пропускает). По умолчанию все включены;
#   sample N: путь/к/файлу.smp   — объявление семпла ударных (N = 0..9);
#   score N: ...                 — партитура тонального канала (N = 0..2);
#   drums: ...                   — партитура ударных.
#
# Команды в партитурах (как в BASIC PLAY Вектора):
#   T<n>      темп, ударных в минуту (параметр композиции; один на все
#             партитуры, только до первого события; при заявленном
#             Tempo: может отсутствовать); по умолчанию T120;
#   O<n>      октава 0..7 (по умолчанию O4);
#   L<n>      длительность: 1,2,4,8,16,32,64,128 (по умолчанию L4);
#   P         пауза на текущую длительность;
#   C..B      ноты; '#' или '+' — диез, '-' — бемоль; цифра после ноты
#             или паузы — явная длительность этой ноты (C8, P16);
#   [ ... ]n  повтор секции: содержимое между '[' и ']n' звучит ровно
#             n раз (аналог $FB/$FE n движка Konami; секция хранится
#             в байткоде один раз, рантайм прыгает назад). Вложенные
#             маркеры: внутренний '[' перекрывает базу внешнего.
#             ']n' без '[' повторяет поток от начала.
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
#   0xE0..0xE7  длительность L1..L128: L = 1 << (байт - 0xE0), в тиках
#               сетки 128/L (четверть = 32). Команда состояния время не
#               продвигает; начальная длительность потока без команд —
#               L4. Октава O — только compile-time состояние: нота сразу
#               уходит в байткод абсолютным номером, команды октавы в
#               потоке нет (диапазон 0xD0..0xD7 свободен).
#   0xE8        '[' — начало повторяемой секции: запоминает адрес
#               возврата (следующий байт), счётчик повторов = 0;
#   0xE9 n      ']n' — конец секции: счётчик + 1; пока счётчик < n,
#               исполнение возвращается к адресу возврата (секция
#               звучит ровно n раз). Время не продвигает.
#
# Формат .smp (бинарный): байт N — число кадров, затем N пар
# (R6, R10) — период шума и громкость канала C AY-3-8910, по одному
# кадру в тик 50 Гц.
#
# Использование:
#   python3 utils/mus2inc.py music/song.mus -o rom_data/song.inc --name song
#   python3 utils/mus2inc.py --self-test   # проверка кодирования L/O

import argparse
import math
import os
import re
import sys

MUS_END = 0x00
MUS_REST = 0x60
MUS_LEN_BASE = 0xE0   # E0..E7 = L1..L128 (однобайтовая команда состояния)
MUS_LPSTART = 0xE8    # '[' — начало повторяемой секции
MUS_LPEND = 0xE9      # ']n' + байт n: секция звучит n раз
MUS_JMP = 0xEA        # END -> JMP: 0xEA <lo> <hi> — возврат назад
L_INDEX = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5, 64: 6, 128: 7}

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
        # Байткод пуст: длительность по умолчанию (L4) совпадает
        # с начальным состоянием рантайма — команда не нужна.
        self.bytes = []
        self.mark_ticks = []    # время на входе в открытые секции '['
        self.loop_pos = None    # позиция байткода после BEGIN (для END)
        self.ticks = 0
        self.events = 0

    def cur_len(self):
        return len_ticks(self.l_val)

    def set_len(self, l_val):
        """Однобайтовая команда E0..E7 (E0 = L1, E7 = L128)."""
        self.l_val = l_val
        self.bytes.append(MUS_LEN_BASE + L_INDEX[l_val])

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
    ('N', abs_note, l|None), ('D', sample_id), ('[',), (']', n), ('!',)."""
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
        m = re.match(r'BEGIN\b', body[pos:], re.I)
        if m:
            toks.append(('BEGIN',))
            pos += m.end()
            continue
        m = re.match(r'END\b', body[pos:], re.I)
        if m:
            toks.append(('END',))
            pos += m.end()
            continue
        if c == '[':
            toks.append(('[',))
            pos += 1
            continue
        m = re.match(r'\](\d+)', body[pos:])
        if m:
            toks.append((']', int(m.group(1))))
            pos += m.end()
            continue
        if drums and c.isdigit():
            m = re.match(r'\d+', body[pos:])
            toks.append(('D', int(m.group())))
            pos += m.end()
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
        # BEGIN — маркер начала бесконечного цикла (intro + loop)
        if kind == 'BEGIN':
            if st.loop_pos is not None:
                raise MusError(f'{fname}: вложенный BEGIN в «{st.name}»')
            st.loop_pos = len(st.bytes)
            continue
        # END — безусловный JMP на байткод сразу после BEGIN
        if kind == 'END':
            if st.loop_pos is None:
                raise MusError(f'{fname}: END без BEGIN в «{st.name}»')
            target = st.loop_pos
            current = len(st.bytes) + 3  # позиция после 0xEA + 2 байт
            back = current - target
            st.bytes.append(MUS_JMP)
            st.bytes.append(back & 0xFF)
            st.bytes.append((back >> 8) & 0xFF)
            st.loop_pos = None
            continue
        if kind == '[':
            st.bytes.append(MUS_LPSTART)
            st.mark_ticks.append(st.ticks)
            continue
        if kind == ']':
            n = tok[1]
            if not 2 <= n <= 255:
                raise MusError(f'{fname}: ]{n} — повторов должно быть 2..255')
            if st.mark_ticks:
                section = st.ticks - st.mark_ticks.pop()
            else:
                # ']n' без '[' — повтор от начала потока (база повтора
                # рантайма по умолчанию = начало потока)
                section = st.ticks
            st.ticks += section * (n - 1)   # рантайм играет n проходов
            st.bytes.append(MUS_LPEND)
            st.bytes.append(n)
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
            if not 0 <= tok[1] <= 7:
                raise MusError(f'{fname}: O{tok[1]} вне диапазона 0..7')
            # Октава — compile-time состояние: команды в байткоде нет,
            # нота уйдёт абсолютным номером (октава*12 + полутон).
            st.len_locked = True
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
            if abs_note > 94:
                raise MusError(f'{fname}: нота в «{st.name}» выше байткода'
                               ' (максимум — октава 7, ре)')
            if abs_note < 12:
                print(f'ВНИМАНИЕ: {fname}: нота в «{st.name}» ниже рабочей'
                      f' зоны ВИ53 (октава {st.oct}) — тишина',
                      file=sys.stderr)
            st.emit_event(abs_note + 1, l_ov)
            continue
        if kind == 'D':
            st.len_locked = True
            st.emit_event(tok[1] + 1)
            continue
    st.bytes.append(MUS_END)
    if st.mark_ticks:
        raise MusError(f'{fname}: незакрытая секция «[» в «{st.name}»')
    if st.loop_pos is not None:
        raise MusError(f'{fname}: незакрытый BEGIN в «{st.name}»')


HEADER_RE = re.compile(
    r'^\s*(?:score\s+([0-2])|drums|sample\s+([0-9]|1[0-5])|(tempo)|(enabled))\s*:'
    r'(.*)$',
    re.I)


def split_sections(text, fname):
    """Разбить .mus на секции. Возвращает (sections, samples, tempo,
    enabled): sections — список ('score0'|'drums', текст), samples —
    {N: путь}, tempo — общий темп из строки «Tempo: T<n>» или None,
    enabled — множество включённых каналов ('score0'..'drums') из
    «Enabled: ...» или None (параметр не заявлен — все включены)."""
    text = re.sub(r';[^\n]*', '', text)
    sections = []
    samples = {}
    tempo = None
    enabled = None
    cur = None
    for line in text.split('\n'):
        m = HEADER_RE.match(line)
        if m:
            if m.group(3) is not None:      # Tempo: T<n> — общий темп
                tm = re.match(r'\s*T?(\d+)\s*$', m.group(5))
                if not tm:
                    raise MusError(f'{fname}: Tempo: не распознано:'
                                   f' «{m.group(5).strip()}»')
                t = int(tm.group(1))
                if not 32 <= t <= 255:
                    raise MusError(f'{fname}: Tempo: T{t} вне диапазона'
                                   ' 32..255')
                if tempo is not None and tempo != t:
                    raise MusError(f'{fname}: Tempo: объявлен дважды'
                                   f' с разными значениями ({tempo}, {t})')
                tempo = t
                continue
            if m.group(4) is not None:      # Enabled: 0 1 2 D
                if enabled is not None:
                    raise MusError(f'{fname}: Enabled: объявлен дважды')
                en = set()
                for tok in m.group(5).split():
                    u = tok.upper()
                    if u == 'D':
                        key = 'drums'
                    elif u in ('0', '1', '2'):
                        key = 'score' + u
                    else:
                        raise MusError(f'{fname}: Enabled: непонятный канал'
                                       f' «{tok}» (допустимы 0, 1, 2, D)')
                    if key in en:
                        raise MusError(f'{fname}: Enabled: канал'
                                       f' «{tok}» указан дважды')
                    en.add(key)
                if not en:
                    raise MusError(f'{fname}: Enabled: не указан ни один'
                                   ' канал')
                enabled = en
                continue
            if m.group(1) is not None:
                cur = ('score' + m.group(1), [])
                sections.append(cur)
                rest = m.group(5)
            elif m.group(2) is not None:
                idx = int(m.group(2))
                path = m.group(5).strip()
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
                rest = m.group(5)
            if rest.strip():
                cur[1].append(rest)
        elif cur is not None:
            cur[1].append(line)
        elif line.strip():
            raise MusError(f'{fname}: данные вне секции: «{line.strip()}»')
    return sections, samples, tempo, enabled


def self_test():
    """Проверка однобайтового кодирования L (E0..E7), compile-time
    октавы O и повторов секций (E8/E9 n) — случаи из ТЗ. Нота C в O4 =
    абсолютный номер 48, байт 0x31; команды октавы в байткоде нет."""
    def comp(text, drums=False):
        st = Stream('selftest', drums=drums)
        toks = tokenize(text, '<selftest>', drums)
        compile_stream(st, toks, '<selftest>', [None], [])
        return bytes(st.bytes)

    def hx(bs):
        return ' '.join(f'{b:02X}' for b in bs)

    cases = [
        # Тест 1 — все длительности: L1..L128 -> E0..E7
        ('все L',
         'L1 C L2 C L4 C L8 C L16 C L32 C L64 C L128 C', False,
         'E0 31 E1 31 E2 31 E3 31 E4 31 E5 31 E6 31 E7 31 00'),
        # Тест 2 — все октавы: команды O в байткоде нет, октава видна
        # в абсолютном номере ноты (C = октава*12 + 1)
        ('все O',
         'O0 C O1 C O2 C O3 C O4 C O5 C O6 C O7 C', False,
         '01 0D 19 25 31 3D 49 55 00'),
        # Тест 3 — частая смена длительности: каждая L — один байт
        ('смена L',
         'L64 C L32 C L64 C L32 C L64 C L32 C', False,
         'E6 31 E5 31 E6 31 E5 31 E6 31 E5 31 00'),
        # Тест 4 — смена октавы во время воспроизведения
        # (C = 0, D = 2, E = 4 полутона: O4 C = 48 -> 0x31 и т.д.)
        ('смена O',
         'O4 C D E O5 C D E O6 C D E O4 C', False,
         '31 33 35 3D 3F 41 49 4B 4D 31 00'),
        # Тест 5 — повтор секции: [ ... ]3 -> E8 ... E9 03
        ('повтор',
         '[ C C ]3', False,
         'E8 31 31 E9 03 00'),
        # Тест 6 — вложенные маркеры: внутренний '[' переопределяет базу
        ('вложенный повтор',
         '[ C [ D ]2 E ]2', False,
         'E8 31 E8 33 E9 02 35 E9 02 00'),
        # Тест 7 — BEGIN/END: бесконечный цикл (intro + loop)
        ('BEGIN/END',
         'BEGIN C D END', False,
         '31 33 EA 05 00 00'),
        # Тест 8 — BEGIN/END с O/L: JMP указывает на первый байт после BEGIN
        ('BEGIN/END с O/L',
         'O4 C BEGIN D E END', False,
         '31 33 35 EA 05 00 00'),
    ]
    failed = 0
    for name, text, drums, want in cases:
        exp = bytes(int(x, 16) for x in want.split())
        got = comp(text, drums)
        if got != exp:
            failed += 1
            print(f'САМОТЕСТ [{name}]: ОШИБКА')
            print(f'  ожидалось: {want}')
            print(f'  получено:  {hx(got)}')
        else:
            print(f'САМОТЕСТ [{name}]: OK ({len(got)} байт)')
    # Время секции умножается на n: '[ C8 C ]3' = 3 * (16+32) = 144 тика
    st = Stream('selftest')
    compile_stream(st, tokenize('[ C8 C ]3', '<selftest>', False),
                   '<selftest>', [None], [])
    if st.ticks != 144:
        failed += 1
        print(f'САМОТЕСТ [время повтора]: ОШИБКА, {st.ticks} тиков != 144')
    else:
        print('САМОТЕСТ [время повтора]: OK (144 тика)')
    # «Enabled:» — список каналов (0..2, D); регистр не важен
    _secs, _smp, _tmp, en = split_sections(
        'Enabled: 0 2 d\nscore 0:\nC\n', '<selftest>')
    if en != {'score0', 'score2', 'drums'}:
        failed += 1
        print(f'САМОТЕСТ [Enabled]: ОШИБКА, каналы {en}')
    else:
        print('САМОТЕСТ [Enabled]: OK (0 2 d -> score0 score2 drums)')
    _secs, _smp, _tmp, en = split_sections('score 0:\nC\n', '<selftest>')
    if en is not None:
        failed += 1
        print(f'САМОТЕСТ [Enabled по умолчанию]: ОШИБКА, {en}')
    else:
        print('САМОТЕСТ [Enabled по умолчанию]: OK (не заявлен -> None)')
    # END без BEGIN — ошибка
    try:
        comp('C END', False)
        failed += 1
        print('САМОТЕСТ [END без BEGIN]: не выдал ошибку')
    except MusError:
        print('САМОТЕСТ [END без BEGIN]: OK (ошибка)')
    # Незакрытый BEGIN — ошибка
    try:
        comp('BEGIN C', False)
        failed += 1
        print('САМОТЕСТ [незакрытый BEGIN]: не выдал ошибку')
    except MusError:
        print('САМОТЕСТ [незакрытый BEGIN]: OK (ошибка)')
    if failed:
        sys.exit(f'mus2inc --self-test: провалено {failed} из'
                 f' {len(cases) + 5}')
    print(f'mus2inc --self-test: все {len(cases) + 5} тестов пройдены')


def main():
    ap = argparse.ArgumentParser(description='.mus/.smp -> .inc для music.c')
    ap.add_argument('mus', nargs='?', help='файл партитуры .mus')
    ap.add_argument('-o', '--output', help='выходной .inc (по умолчанию'
                    ' имя .mus с расширением .inc)')
    ap.add_argument('--name', help='префикс символов C (по умолчанию —'
                    ' имя файла без расширения)')
    ap.add_argument('--allow-len-mismatch', action='store_true',
                    help='предупреждение вместо ошибки при разной длине'
                    ' партитур (то же, что «!» в .mus)')
    ap.add_argument('--shared-lib', action='store_true',
                    help='генерировать общую библиотеку: .h (extern) +'
                    ' .c (определения) вместо .inc')
    ap.add_argument('--use-shared', metavar='NAME',
                    help='использовать семплы из внешней библиотеки NAME'
                    ' (включает NAME.h, без локальных семплов)')
    ap.add_argument('--self-test', action='store_true',
                    help='проверить однобайтовое кодирование L и октавы,'
                    ' выйти')
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return
    if args.mus is None:
        ap.error('не указан файл партитуры .mus')
    if args.shared_lib and args.use_shared:
        ap.error('--shared-lib и --use-shared несовместимы')

    fname = args.mus
    out = args.output or os.path.splitext(fname)[0] + '.inc'
    name = args.name or os.path.splitext(os.path.basename(fname))[0]
    base_dir = os.path.dirname(os.path.abspath(fname))

    try:
        with open(fname, encoding='utf-8') as f:
            text = f.read()
        sections, sample_paths, global_tempo, enabled = \
            split_sections(text, fname)
        all_ch = ('score0', 'score1', 'score2', 'drums')
        if enabled is None:
            enabled = set(all_ch)     # параметр не заявлен — все включены

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

        lengths = {k: st.ticks for k, st in streams.items()
                   if st.events and k in enabled}
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

        if args.use_shared and sample_paths:
            print(f'ВНИМАНИЕ: {fname}: --use-shared {args.use_shared}:'
                  f' локальные sample объявления игнорируются',
                  file=sys.stderr)

        # семплы (обрабатываются всегда, если есть объявления)
        sample_arrays = {}
        samples_field = '0'
        if sample_paths and not args.use_shared:
            for idx, path in sorted(sample_paths.items()):
                smp_path = path if os.path.isabs(path) \
                    else os.path.join(base_dir, path)
                try:
                    with open(smp_path, 'rb') as f:
                        data = f.read()
                except FileNotFoundError:
                    print(f'ВНИМАНИЕ: {fname}: файл {path} не найден'
                          f' — семпл {idx} заменён паузами',
                          file=sys.stderr)
                    continue
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

            # номера семплов в партитуре ударных: без данных (файл
            # не найден или не объявлен) — предупреждение и замена
            # на паузы (время сохраняется)
            used = set()
            for tok in getattr(streams['drums'], '_toks', []):
                if tok[0] == 'D':
                    used.add(tok[1])
            missing = sorted(idx for idx in used
                             if idx not in sample_arrays)
            for idx in missing:
                print(f'ВНИМАНИЕ: {fname}: семпл {idx} используется,'
                      f' но данных нет — заменяю паузами',
                      file=sys.stderr)
            if missing:
                dr_bytes = streams['drums'].bytes
                for i in range(len(dr_bytes)):
                    sid = dr_bytes[i] - 1
                    if 0 <= sid <= 15 and sid in missing:
                        dr_bytes[i] = MUS_REST

    except MusError as e:
        print(f'mus2inc: {e}', file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f'mus2inc: {e}', file=sys.stderr)
        sys.exit(1)

    g = math.gcd(4 * tempo, 375)
    tempo_num, tempo_den = 4 * tempo // g, 375 // g

    def cbytes(prefix, data, st=True):
        kw = 'static const' if st else 'const'
        lines = [f'{kw} unsigned char {prefix}[] = {{']
        for i in range(0, len(data), 12):
            chunk = ', '.join(f'0x{b:02X}' for b in data[i:i + 12])
            lines.append('    ' + chunk + ',')
        lines.append('};')
        return '\n'.join(lines)

    is_shared_lib = args.shared_lib
    is_use_shared = bool(args.use_shared)
    parts = [f'/* {os.path.basename(out)} — сгенерирован mus2inc.py из'
             f' {os.path.basename(fname)}; не редактировать. */\n']
    if is_use_shared:
        parts.insert(0, f'#include "{args.use_shared}.h"\n')
    for idx in sorted(sample_arrays):
        parts.append(cbytes(f'{name}_smp{idx}', sample_arrays[idx],
                            st=not is_shared_lib))
    ch_names = (('score0', 's0'), ('score1', 's1'),
                ('score2', 's2'), ('drums', 'dr'))
    for key, suffix in ch_names:
        if key in enabled and not is_shared_lib:
            parts.append(cbytes(f'{name}_{suffix}', streams[key].bytes,
                                st=not is_shared_lib))
    if sample_arrays:
        table = ', '.join(f'{name}_smp{i}' if i in sample_arrays else '0'
                          for i in range(16))
        stbl_kw = 'const' if is_shared_lib else 'static const'
        parts.append(f'{stbl_kw} unsigned char * const'
                     f' {name}_samples[16] = {{\n    {table}\n}};')
        samples_field = f'{name}_samples'
    elif is_use_shared:
        samples_field = f'{args.use_shared}_samples'
    else:
        samples_field = '0'
    if is_shared_lib:
        ch_vals = '0, 0, 0, 0'
    else:
        ch_vals = ', '.join(f'{name}_{sfx}' if key in enabled
                            else '0' for key, sfx in ch_names)
    song_kw = 'const' if is_shared_lib else 'static const'
    parts.append(f'{song_kw} music_song_t {name}_song = {{')
    parts.append(f'    {tempo_num}u, {tempo_den}u, {song_len}u,')
    parts.append(f'    {ch_vals},')
    parts.append(f'    {samples_field}')
    parts.append('};')

    if is_shared_lib:
        guard = re.sub(r'[^A-Z0-9]', '_',
                       os.path.basename(out).upper().replace('.INC', '.H'))
        h_path = re.sub(r'\.inc$', '.h', out, flags=re.I)
        c_path = re.sub(r'\.inc$', '.c', out, flags=re.I)
        h_parts = [f'/* {os.path.basename(h_path)} — extern declarations'
                   f' для {name}; не редактировать. */\n',
                   f'#ifndef {guard}\n',
                   f'#define {guard}\n',
                   '#include "v06.h"\n']
        for idx in sorted(sample_arrays):
            h_parts.append(
                f'extern const unsigned char {name}_smp{idx}[];')
        if sample_arrays:
            h_parts.append(
                f'extern const unsigned char * const'
                f' {name}_samples[16];')
        h_parts.append(f'extern const music_song_t {name}_song;')
        h_parts.append('#endif')
        c_parts = [f'/* {os.path.basename(c_path)} — определения данных'
                   f' для {name}; не редактировать. */\n',
                   f'#include "{os.path.basename(h_path)}"\n']
        c_parts.extend(parts)
        with open(h_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(h_parts) + '\n')
        with open(c_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(c_parts) + '\n')
        print(f'  -> {h_path} + {c_path}')
    else:
        with open(out, 'w', encoding='utf-8') as f:
            f.write('\n'.join(parts) + '\n')
        print(f'  -> {out}')

    print(f'{os.path.basename(fname)}: темп T{tempo}'
          f' ({tempo_num}/{tempo_den} тика/кадр), длина {song_len} тиков')
    for key in ('score0', 'score1', 'score2', 'drums'):
        st = streams[key]
        off = '' if key in enabled else '  (выключен)'
        print(f'  {key:7s}: событий {st.events:3d}, байткод'
              f' {len(st.bytes):4d} байт{off}')
    print(f'  семплы: {", ".join(str(i) for i in sorted(sample_arrays)) or "нет"}')


if __name__ == '__main__':
    main()
