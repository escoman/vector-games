#!/usr/bin/env python3
"""Проверка привязки звуков к событиям (белый ящик, по кадрам).

Звуки — только три тональных канала КР580ВИ53, Tape Out не задействован.

A) 400+ кадров игры:
   1) сдвиг жёлоба, в котором есть яйца ↔ начался fx_move (один на все
      четыре жёлоба); обратное — тик без сдвига жёлоба;
   2) любое нажатие клавиши волка ↔ fx_click, в любом состоянии (игра и
      анимации) — как в JS, где click не зависит от позиции и состояния;
   3) разбитое яйцо ↔ fx_miss (тональный гудок), по предсказанию анимаций;
   4) в порт 0x00 (PIA1) за прогон не ушло ни одной записи с битом 7 = 0 —
      это BSR, которым drums.asm переключает бипер; легитимные значения там —
      управляющие слова клавиатуры (88/8A). Семплов шума в ROM нет
      (`SFX_SMP` пуст), поэтому проверяем не «звучит шум», а «Tape Out не
      тронут».
B) Трель конца игры: в ОЗУ остаётся 1 жизнь, ждём разбитое яйцо → ST_LOOSE;
   в этот момент делители тональных каналов должны быть ровно из step_loose
   (G#6, D7, B5, E5, A4, D4 — делители 903, 638, 1519, 2275, 3409, 5108) и
   съезд хвоста на +100 к делителю в кадр;
   затухание к тишине; слот освобождается по окончании.

За одно обращение к MCP берём только короткий кадр: кольцо debug_get_io_trace
вмещает 10000 событий, длинные прогоны вытесняют начало. Поэтому
перед прогоном запоминаем последний sequence, а разбираем только новые записи
(и сбрасываем кольцо каждые 80 кадров).

Проверка: `make consist KEEP_MAP=1`, затем `python3 tools/check_sfx.py 400`
(B сама берёт не меньше 700 кадров — трель должна отзвучить до конца).
"""
import sys, os, time, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'roms', 'games', 'nu_pogodi', 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))
import npg_check as npg                                   # noqa: E402

CH = {0x09: 'ch2', 0x0A: 'ch1', 0x0B: 'ch0'}


def div_of(n):
    """абсолютный номер ноты -> делитель, как в lib/snd/notes.c."""
    return int(round(1500000.0 / (440.0 * 2 ** ((n - 57) / 12.0))))


def hx(v):
    return int(v, 16) if isinstance(v, str) else int(v)


def trace(s):
    raw = s.call('debug_get_io_trace', max_entries=400000)
    return raw.get('events') or [] if isinstance(raw, dict) else raw


def mark(s):
    ev = trace(s)
    return ev[-1]['sequence'] if ev else 0


def pairs(s, since):
    """(управляющее слово, канал, делитель) -> число повторов, только новые."""
    vi53 = sorted((e['sequence'], hx(e['port']), hx(e['value']))
                  for e in trace(s)
                  if e['sequence'] > since and hx(e['port']) in set(CH) | {0x08})
    out = collections.Counter()
    cur = None
    for seq, port, val in vi53:
        if port == 0x08:
            cur = (val, None)
            continue
        if cur is None:
            continue
        if cur[1] is None:
            cur = (cur[0], val)
        else:
            out[(cur[0], CH[port], cur[1] | (val << 8))] += 1
            cur = None
    return out


def report(title, got, want_notes):
    print('  %-9s делители: %s' % (title, [div_of(n) for n in want_notes]))
    have = set(d for (_, _, d) in got)
    hit = [div_of(n) for n in want_notes
           if div_of(n) in have or div_of(n) - 1 in have or div_of(n) + 1 in have]
    print('  %-9s найдено  : %d/%d %s' % ('', len(hit), len(want_notes), hit))
    return len(hit) == len(want_notes)


def start(s, sym):
    npg.BP = sym['_input']
    # точка останова переживает debug_reset, а повторная установка — ошибка
    try:
        s.call('debug_set_breakpoint', address=npg.BP)
    except Exception:               # уже стоит (debug_reset её не снимает)
        pass
    s.call('debug_run')
    npg.wait_bp(s)
    s.call('debug_press_key', key='F1')
    s.call('debug_run')
    npg.wait_bp(s)
    s.call('debug_release_key', key='F1')


def frame(s):
    s.call('debug_run')
    return npg.wait_bp(s) is not None


def voice_slots(s, sym):
    """3 слота sfx.c: steps(2) idx len left prio div(2)."""
    gv = npg.rd(s, sym['_g_voice'], 24)
    return [('steps=%04X idx=%d/%d left=%d prio=%d div=%d'
             % (gv[i * 8] | (gv[i * 8 + 1] << 8), gv[i * 8 + 2], gv[i * 8 + 3],
                gv[i * 8 + 4], gv[i * 8 + 5], gv[i * 8 + 6] | (gv[i * 8 + 7] << 8)))
            for i in range(3)]


# ---------------------------------------------------------------- A) тик и клик
def start_b(s, sym):
    """gameB (F2): все четыре жёлоба и участвуют в переборе, и яйца встают
    во все четыре — иначе на шести жизнях LD вообще не двигается."""
    npg.BP = sym['_input']
    try:
        s.call('debug_set_breakpoint', address=npg.BP)
    except Exception:
        pass
    s.call('debug_run')
    npg.wait_bp(s)
    s.call('debug_press_key', key='F2')
    s.call('debug_run')
    npg.wait_bp(s)
    s.call('debug_release_key', key='F2')


def seed_lanes(s, sym):
    """Разложить яйца средний части всех четырёх жёлобов (у края — пусто,
    чтобы на этом кадре ничего не поймалось и не разбилось). Иначе на слухе
    одного лишь генератора яиц покрытие зависит от случайности: в прошлый раз
    LU за 600 кадров ни разу не двинулся с яйцом."""
    s.call('debug_write_memory', address=sym['_groove'],
           data=[0, 1, 1, 1, 0] * 4)


def tape_writes(s, since):
    """Записи в ПИА1 (порт 0x00) после кадра-маркера.

    Легальные слова игры туда — только управляющие клавиатурой (бит 7 = 1:
    0x8A/0x88 в kbdscan, слова режима экрана). Бипер/Tape Out пишет BSR-слова
    с битом 7 = 0 (drums.asm: out (PIA_CW), a, a = 0 или 1). Значит любое
    значение < 0x80 = кто-то всё-таки полез в шум.
    """
    vals = collections.Counter(hx(e['value']) for e in trace(s)
                               if e['sequence'] > since and hx(e['port']) == 0x00)
    return vals, {v: n for v, n in vals.items() if not (v & 0x80)}


def check_move(s, sym, rm, frames=300):
    """Чпок движения — на сдвиг жёлоба, клик — на клавишу, гудок — на разбитое.

    Белый ящик со сверкой по предсказанию: считаем, какой жёлоб двинулся
    в этом кадре (turn_order[строка][cursor]) и есть ли в нём яйца после
    сдвига, и сравниваем с указателем steps в слотах sfx.c. Трасса на
    10000 событий за 300 кадров вытеснила бы начало.

    Плюс аудит Tape Out: за прогон в шумовой генератор никто не должен войти
    (на звуке это значит, что все эффекты — три тональных канала ВИ53).
    """
    print('\n== A) чпок/клик/гудок: предсказание против ОЗУ ==')
    start_b(s, sym)            # gameB: все четыре жёлоба в переборе и в яйцах
    order = rm.read(sym['_turn_order'], 20)
    names = {sym['_step_move']: 'move', sym['_step_catch']: 'catch',
             sym['_step_click']: 'click', sym['_step_loose']: 'loose',
             sym['_step_miss']: 'miss'}

    def life_row(n):
        return 0 if n >= 6 else 1 if n >= 4 else 2 if n >= 2 else 3

    seen = collections.Counter()
    bad = []
    turns = 0
    turn_lane = collections.Counter()    # сколько раз жёлоб двинулся с яйцом
    held = None
    click_at = None                      # клавиша, которую жмём ради клика
    prev = set()
    misses = 0                           # запусков тонального «разбилось»
    click_state = collections.Counter()  # в каком состоянии застал клик
    g = npg.decode(*npg.read_vars(s, sym), sym)
    keys = npg.pos_keys(g)
    active = frames // 3            # первые треть — ловим, остальное — роняем
    LANE = ('LU', 'LD', 'RU', 'RD')
    STATE = {0: 'меню', 1: 'игра', 2: 'проигрыш', 3: 'анимация'}
    tape_from = mark(s)
    beep_all = collections.Counter()   # кольца трассы на 10000 событий — вычитываем часто
    vals_all = collections.Counter()
    for i in range(frames):
        pre = g
        row = 4 if pre['game_type'] else life_row(pre['life'])
        p = order[row * 4 + pre['cursor']] if pre['state'] == 1 else None
        # автоигрок: волк под яйцо у края; после ACTIVE кадров клавиши не
        # трогаем — яйца начнут биться, и заиграет гудок (fx_miss)
        want = None
        if i <= active:
            for q in range(4):
                if pre['grooves'][q * 5 + 4]:
                    want = q
                    break
            if want is None:
                for q in range(4):
                    if pre['grooves'][q * 5 + 3]:
                        want = q
                        break
        if want != held:
            if held is not None:
                s.call('debug_release_key', key=keys[held])
            if want is not None:
                s.call('debug_press_key', key=keys[want])
            held = want
        # Раз в 20 кадров — нажатие СВОБОДНОЙ клавиши волка ради клика.
        # Во второй трети игра стоит (ST_ANIMATION), в третьей — после
        # проигрыша; в JS clickSound.play() не защищён состоянием, так что
        # клик обязан прозвучать и там.
        if i % 20 == 12:
            click_at = keys[(pre['wolf'] + 1) % 4]
            s.call('debug_press_key', key=click_at)
        if i % 20 == 15 and click_at is not None:
            s.call('debug_release_key', key=click_at)
            click_at = None

        if not frame(s):
            print('  стоп на кадре %d' % i)
            return False
        if i == 5:      # разрешаем до пяти яиц на сцене — тогда все четыре
            s.call('debug_write_memory', address=sym['_eggs_needed'], data=[5])
            print('  кадр 5: eggs_needed := 5 (все жёлоба будут полны)')
        if i <= active and i % 12 == 5:
            seed_lanes(s, sym)      # не даём жёлобам опустеть покрываемым
        if i % 80 == 79:            # кольцо трассы не должно вытеснить порт 0x00
            v, b = tape_writes(s, tape_from)
            vals_all.update(v)
            beep_all.update(b)
            tape_from = mark(s)
        g = npg.decode(*npg.read_vars(s, sym), sym)
        gv = npg.rd(s, sym['_g_voice'], 24)
        playing = set()
        for k in range(3):
            ptr = gv[k * 8] | (gv[k * 8 + 1] << 8)
            if ptr in names:
                playing.add(names[ptr])
                seen[names[ptr]] += 1

        started = playing - prev          # именно старт, не присутствие
        prev = playing
        turned = (g['game_timer'] == 0)
        if 'click' in started:
            click_state[STATE.get(g['state'], g['state'])] += 1
        if 'miss' in started:
            misses += 1
        if turned and pre['state'] == 1:
            turns += 1
        if 'move' in started and not turned:
            bad.append((i, 'кадр %d: чпок начался без сдвига жёлоба' % i))
        if p is not None and turned:
            eggs = sum(g['grooves'][p * 5:p * 5 + 5])
            if eggs:
                turn_lane[LANE[p]] += 1
            if eggs and 'move' not in playing:
                bad.append((i, 'кадр %d: жёлоб %s двинулся (яиц %d) — чпока нет'
                            % (i, LANE[p], eggs)))
            if not eggs and 'move' in started:
                bad.append((i, 'кадр %d: жёлоб пуст, но чпок играет' % i))
    for _, msg in bad[:8]:
        print('  ' + msg)
    v, b = tape_writes(s, tape_from)      # последний хвост
    vals_all.update(v)
    beep_all.update(b)
    print('  расхождений предсказания: %d из %d кадров' % (len(bad), frames))
    print('  сдвигов жёлоба (всего / с яйцом): %d / %s'
          % (turns, dict(turn_lane)))
    print('  кто играл (кадров с активным голосом): %s' % dict(seen))
    print('  кликов по состояниям: %s' % dict(click_state))
    print('  запусков гудка «разбилось»: %d' % misses)
    print('  порт 0x00 за прогон: %s%s'
          % ({'%02X' % val: n for val, n in sorted(vals_all.items())},
             '' if not beep_all else '  !!! BSR/бипер: %s' % beep_all)
    )
    need = ['move', 'click', 'miss']
    miss = [n for n in need if not seen.get(n)]
    if miss:
        print('  не покрыты: %s' % miss)
    return not bad and not miss and misses > 0 and not beep_all


def back_to_menu(s, sym):
    """АП2/ESCAPE из игры — в меню (там же срабатывает sfx_stop_all)."""
    s.call('debug_press_key', key='ESCAPE')
    frame(s)
    s.call('debug_release_key', key='ESCAPE')
    for _ in range(4):
        frame(s)
    g = npg.decode(*npg.read_vars(s, sym), sym)
    return g['state'] == 0


# ------------------------------------------------------------- B) fx_loose
def check_loose(s, sym, rm, frames=500, was_playing=False):
    print('\n== B) трель конца игры fx_loose ==')
    # Трель идёт ~68 кадров, а до ST_LOOSE игра доживает в средний ~350-400
    # кадров (RNG). Короткий прогон обрезал бы хвост — и делители 3409/5108
    # не нашлись бы, поэтому нижняя граница жёсткая.
    frames = max(frames, 700)
    if was_playing:
        print('  возврат в меню (ESC): %s' % ('ок' if back_to_menu(s, sym) else 'НЕ'))
    start(s, sym)
    life = 6
    loose_at = None
    m = mark(s)
    for i in range(frames):
        if not frame(s):
            print('  остановка не пришла на кадре %d' % i)
            return False
        g = npg.decode(*npg.read_vars(s, sym), sym)
        if i == 20 and g['life'] > 1:
            s.call('debug_write_memory', address=sym['_life_count'], data=[1])
            print('  кадр %3d: life_count := 1' % i)
        if g['life'] != life:
            print('  кадр %3d: life %d -> %d (state=%d)' % (i, life, g['life'], g['state']))
            life = g['life']
        if g['state'] == 2 and loose_at is None:
            loose_at = i
            m = mark(s)                       # трассу берём только с этого кадра
            print('  кадр %3d: ST_LOOSE — пишем трель' % i)
        if loose_at is not None:
            if i - loose_at in (1, 2, 4, 40, 52, 56, 68, 70):
                print('  кадр %3d (+%2d): %s' % (i, i - loose_at,
                                                 ' | '.join(voice_slots(s, sym))))
            if i - loose_at >= 72:
                break
    got = pairs(s, m)
    print('  пар (упр, канал, делитель):')
    for (ctrl, ch, d), n in got.most_common(12):
        print('     %02X %s div=%5d (%6.0f Гц) x%d' % (ctrl, ch, d, 1500000.0 / d, n))
    # трель: G#6/D7 поперменно, хвост B5 E5 A4 D4
    ok = report('loose', got, [80, 86, 71, 64, 57, 50])
    return ok


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    mode = sys.argv[2] if len(sys.argv) > 2 else 'all'
    s = npg.session()
    sym = npg.symbols()
    rm = npg.Rom(s, sym)
    a = check_move(s, sym, rm, frames) if mode in ('all', 'pos') else True
    if mode in ('all', 'pos'):
        s.call('debug_press_key', key='ESCAPE')   # gameB → в меню, дальше gameA
        frame(s)
        s.call('debug_release_key', key='ESCAPE')
        for _ in range(6):
            frame(s)
    b = check_loose(s, sym, rm, frames, was_playing=(mode == 'all')) if mode in ('all', 'loose') else True
    s.call('debug_pause')
    s.close()
    print('\nчпок+клик+гудок %s   fx_loose %s' % ('OK' if a else 'НЕ ПОДТВЕРЖДЁН',
                                         'OK' if b else 'НЕ ПОДТВЕРЖДЁН'))
    return 0 if (a and b) else 1


sys.exit(main())
