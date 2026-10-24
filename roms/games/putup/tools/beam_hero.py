#!/usr/bin/env python3
"""beam_hero.py — ЗАМЕР ПОЛОЖЕНИЯ ЛУЧА в моменты восстановления фона (erase) и
рисования героя в putup.

Вопрос: каждый ли всплеск записи тайла в живую VRAM лежит ПОЛНОСТЬЮ вне полосы
строк этого тайла, или луч успевает просканировать часть полосы посреди всплеска
(тогда тайл в этом кадре половина старый / половина новый = видимое помигивание).

Два независимых часа (оба снимаются на каждом останове):
  * ЛУЧ эмулятора: debug_get_beam_state -> T = frame*312 + raster_line +
    v_cycle_in_line/768 (в строках развёртки).
  * СЕКУНДОМЕР ROM (КР580ВИ53 ch1, читается ровно как func_beam_count):
    elapsed = 0x7500 - count — в нём живёт решение func_raster_guard_hero.

КАЛИБРОВКА (измерено этим инструментом и .scratch/vram_geom2.py):
  * фаза часов beam_line - elapsed/96 = L0 ~ +5 строк (постоянна по всему кадру)
    => секундомер и луч в одном такте; нуль секундомера смещён на L0.
  * соответствие ROM-строки экранной (по диффу реально изменённых байт VRAM):
        Y_top(экранная строка) = 24 + 8*row,  линия ЛУЧА = Y + 24 = 48 + 8*row
    => модель guard'а VISIBLE_TOP=48 верна в СТРОКАХ ЛУЧА; сравнение же с
       elapsed даёт ей систематический запас/недостаток в L0 ~ 5 строк.
  * видимое поле: raster_line - visible_y = 24 (top), строки 24..280.

Вердикт окна: записываемая полоса [48+8*row+voff .. +15+voff] против отрезка
времени всплеска [t0..t1] в строках луча:
  «до луча»   — всплеск закончился до прихода луча (безопасно);
  «после луча»— луч уже ушёл (безопасно);
  «РАЗРЫВ»    — луч сканировал полосу во время записи (tearing на overlap строк).

Запуск: python3 tools/beam_hero.py [КАДРОВ] [файл.json для сырых событий]
Герой гоняется удержанием клавиш (смена направления по расписанию), чтобы он
проехал и верхние, и нижние строки поля.
"""
import bisect
import json
import os
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.abspath(os.path.join(PROJECT, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 30
DUMP = sys.argv[2] if len(sys.argv) > 2 else os.path.join(PROJECT, '.scratch',
                                                          'beam_hero_events.json')
ROM = os.environ.get('PUTUP_ROM') or os.path.join(PROJECT, 'putup_new.rom')
SYMS = json.load(open(os.environ.get('PUTUP_LAYOUT') or
                      os.path.join(PROJECT, 'tools', 'layout.json')))
SYMS = SYMS.get('symbols', SYMS)
ROM_BASE = 0x0100

LINE = 96                 # отсчётов секундомера на строку растра
FRAME_LEN = 0x7500        # 29952 отсчёта = 312 строк кадра
VC_LINE = 768             # v_cycle'ов на строку луча (debug_get_screen_info)
FRAME_LINES = 312
FIELD_TOP = 48            # строка ЛУЧА, где начинается level row 0 (калибровано)
GLYPH_LINES = 8           # строк луча в одном level row
TILE_LINES = 16           # тайл 2x2
MARGIN_ROM_LINES = 112    # MARGIN guard'а в строках

S = SYMS
MAIN = S['lbl_main_game_loop']
WINDOWED = {
    'guard_hero': S['func_raster_guard_hero'],
    'guard_enemy': S['func_raster_guard_enemy'],
    'tile_at_ptr': S['func_draw_tile_at_ptr'],
    'tile_vram': S['func_render_tile_vram'],
    'or2(hero)': S['func_render_tile_vram_or'],
    'or3(hero)': S['func_render_tile_vram_or3'],
    'repaint': S['func_hero_repaint_over'],
    'render_all': S['func_render_all'],
}
BEAMCNT = S['func_beam_count']
DRAW = S['func_draw_char_at_hl']          # писатель скана огня/выхода (поштучно)
SCAN_RET = 0x38A0                          # loc_ra_next = возврат CALL в func_render_all

ISLAND = S['data_ram_init_image_08C3']
A_PLAYER_RC = ISLAND + 0x3E       # var_player_row, var_player_col (цель easing'а)
A_ENEMY_RC = ISLAND + 0x20          # var_enemy_rc: prev-кэш врага И отображение героя
A_BONUS_RC = ISLAND + 0x22          # var_bonus_rc
A_DISP_RC1 = S['var_enemy_disp_rc'] + 2
A_HERO_EROW = S['var_hero_erow']    # пара (row,col) erase героя
A_ED_ERASE_RC = 0x6A5E              # var_ed_erase_rc: erase врага
A_RASTER_TOP = S['var_raster_top']
A_RASTER_BOT = S['var_raster_bot']
A_RASTER_CAP = S['var_raster_cap']
A_VOFF = S['var_glyph_voff']
A_HOFF = S['var_glyph_hoff']
A_SUB = S['var_frame_sub']
A_SCAN_PTR = S['var_scan_ptr']
TB = S['data_text_buffer']
CHUNK_CELLS = 0x80          # func_render_all: 128 клеток за проход = 4 строки
COLS = 32                   # data_text_buffer: cell = TB + row*32 + col

ERASE_WHO = {A_HERO_EROW: 'hero-erase', A_ED_ERASE_RC: 'enemy-erase',
             A_ENEMY_RC: 'egg-erase', A_BONUS_RC: 'bonus-erase',
             A_DISP_RC1: 'chaser-erase'}

SYMS_SORTED = sorted((a, n) for n, a in SYMS.items() if isinstance(a, int))


def owner(addr):
    i = bisect.bisect_right(SYMS_SORTED, (addr, '\uffff')) - 1
    return SYMS_SORTED[i][1] if i >= 0 and SYMS_SORTED[i][0] <= addr else '?'


s = McpSession(cwd=ROOT)


def regs():
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def elapsed():
    s.call("debug_write_io", {"port": 0x08, "value": 0x40})
    lo = to_addr(s.call("debug_read_io", {"port": 0x0A})['value'])
    hi = to_addr(s.call("debug_read_io", {"port": 0x0A})['value'])
    return (FRAME_LEN - ((hi << 8) | lo)) & 0xFFFF


def beam_state():
    b = s.call("debug_get_beam_state")
    return b['frame'] * FRAME_LINES + b['raster_line'] + \
        b['v_cycle_in_line'] / float(VC_LINE), b['raster_line'], b


class Probe:
    def __init__(self):
        self.names = {}
        self.open = {}
        self.ret_of = defaultdict(set)
        self.bps = set()
        self.events = []
        self.beams = 0
        self.frames = []

    def bp(self, addr):
        if addr not in self.bps:
            s.call("debug_set_breakpoint", {"address": addr})
            self.bps.add(addr)

    def arm(self, full=True):
        self.bp(MAIN)
        if not full:
            return
        for name, addr in WINDOWED.items():
            self.names[addr] = name
            self.open.setdefault(name, [])
            self.bp(addr)
        self.names[BEAMCNT] = '_beam'
        self.bp(BEAMCNT)
        self.names[DRAW] = '_charwrite'
        self.bp(DRAW)

    def geometry(self, name, r):
        if name == 'tile_at_ptr':
            hl = r['hl']
            row, col = read(hl, 2)
            who = ERASE_WHO.get(hl, 'erase@' + owner(r['ret']))
            return row, col, read(A_VOFF, 1)[0], read(A_HOFF, 1)[0], who
        if name in ('or2(hero)', 'or3(hero)', 'tile_vram'):
            row, col = r['e'] & 0xFF, r['d'] & 0xFF
            voff, hoff = read(A_VOFF, 1)[0], read(A_HOFF, 1)[0]
            if name == 'tile_vram':
                # func_render_tile_vram зовётся и врагом (loc_ed_drawa_flat), и
                # погрузчиком уровня/HUD: различаем по вызывающему
                caller = owner(r['ret'])
                who = ('enemy-draw' if caller.startswith('func_enemy_render')
                       else 'draw@' + caller)
            else:
                who = name
            return row, col, voff, hoff, who
        if name == 'repaint':
            row, col = read(A_ENEMY_RC, 2)     # отображаемая позиция героя
            return row, col, read(A_VOFF, 1)[0], read(A_HOFF, 1)[0], name
        if name == 'render_all':
            ptr = read(A_SCAN_PTR, 2)
            base = (ptr[0] | ptr[1] << 8) - TB
            row = base // COLS
            return row, None, 0, 0, 'fire-scan'
        return None, None, read(A_VOFF, 1)[0], read(A_HOFF, 1)[0], name

    def handle(self, t, e, r):
        pc = r['pc']
        if pc == BEAMCNT:
            self.beams += 1
            return None
        if pc == DRAW:
            # поштучная запись скана: считаем только клетки из func_render_all
            lo, hi = read(r['sp'], 2)
            if (lo | hi << 8) != SCAN_RET:
                return None
            cell = r['hl'] - TB
            ent = {'name': 'scan-write', 't0': t, 't1': t, 'e0': e, 'e1': e,
                   'row': cell // COLS, 'col': cell % COLS, 'voff': 0, 'hoff': 0,
                   'who': 'fire/exit-write', 'caller': 'func_render_all',
                   'beams_in': 0, 'beams_wait': 0, 'sub': read(A_SUB, 1)[0],
                   'closed': True}
            self.events.append(ent)
            return 'scan-write'
        if pc == MAIN:
            self.frames.append(t)
            for k in self.open:
                self.open[k] = []
            return 'frame'
        name = self.names.get(pc)
        if name is None:
            return None
        if pc in self.ret_of[name]:
            if not self.open[name]:
                return name
            ent = self.open[name].pop()
            ent.update(t1=t, e1=e, closed=True, beams_wait=self.beams)
            if name.startswith('guard'):
                top = read(A_RASTER_TOP, 2)
                bot = read(A_RASTER_BOT, 2)
                ent['top'] = top[0] | top[1] << 8
                ent['bot'] = bot[0] | bot[1] << 8
                ent['cap'] = read(A_RASTER_CAP, 1)[0]
            self.events.append(ent)
            return name
        lo, hi = read(r['sp'], 2)
        r['ret'] = lo | hi << 8
        row, col, voff, hoff, who = self.geometry(name, r)
        ent = {'name': name, 't0': t, 'e0': e, 'row': row, 'col': col,
               'voff': voff, 'hoff': hoff, 'who': who, 'caller': owner(r['ret']),
               'beams_in': self.beams, 'sub': read(A_SUB, 1)[0], 'closed': False}
        self.open[name].append(ent)
        if r['ret'] not in self.bps:
            self.bp(r['ret'])
            self.names[r['ret']] = name
            self.ret_of[name].add(r['ret'])
        self.beams = 0
        return name


def band(ev):
    """полоса строк ЛУЧА, которую занимает запись:
    Y_top = 24 + 8*row, линия луча = Y + 24 = 48 + 8*row (калибровано по диффу
    реально изменённых байт VRAM); voff уносит запись вниз до +4 строк.
    Одиночный глиф 8x8 (scan-write) — 8 строк; скан-чанк (render_all) — 4 строки
    клеток, но это ГРУБАЯ оценка (фактически пишутся только флипаемые клетки,
    они мерятся окном scan-write)."""
    if ev['row'] is None or ev['row'] >= 0x20:
        return None, None
    if ev['name'] == 'scan-write':
        top = FIELD_TOP + GLYPH_LINES * ev['row']
        return top, top + GLYPH_LINES - 1
    if ev['who'] == 'fire-scan':
        top = FIELD_TOP + GLYPH_LINES * ev['row']
        return top, top + GLYPH_LINES * CHUNK_CELLS // COLS - 1
    top = FIELD_TOP + GLYPH_LINES * ev['row'] + (ev['voff'] or 0)
    return top, top + TILE_LINES - 1


def verdict(ev):
    bt, bb = band(ev)
    ev['band'] = [bt, bb] if bt is not None else None
    if bt is None:
        ev['verdict'] = 'нет геометрии'
        return ev
    f = int(ev['t0'] // FRAME_LINES) * FRAME_LINES
    lo, hi = bt + f, bb + f
    t0 = ev.get('t0w', ev['t0'])        # реальное начало ЗАПИСИ (после in-window guard)
    ev['t0w'] = t0
    ev['wrapped'] = ev['t1'] // FRAME_LINES > ev['t0'] // FRAME_LINES
    if ev['t1'] <= lo:
        ev['verdict'] = 'до луча'
        ev['gap'] = lo - ev['t1']                 # запас до прихода луча
    elif t0 >= hi:
        ev['verdict'] = 'после луча'
        ev['gap'] = t0 - hi                       # насколько луч уже ушёл
    else:
        ev['verdict'] = 'РАЗРЫВ'
        ev['overlap'] = min(ev['t1'], hi) - max(t0, lo)
    if ev['who'] == 'fire-scan':                  # грубая полоса чанка: не считаем
        ev['verdict'] = 'чанк (инфо)'
        ev.pop('overlap', None)
        ev.pop('gap', None)
    return ev


def nest_guards(ev):
    """func_hero_repaint_over = guard + запись одним окном. Начало записи — конец
    вложенного окна guard'а в том же кадре; иначе вейт стража ошибочно считается
    записью и даёт ложный РАЗРЫВ."""
    by_frame = defaultdict(list)
    for x in ev:
        if x['name'].startswith('guard'):
            by_frame[int(x['t0'] // FRAME_LINES)].append(x)
    n = 0
    for x in ev:
        if x['name'] == 'repaint':
            gs = [g for g in by_frame[int(x['t0'] // FRAME_LINES)]
                  if x['t0'] <= g['t0'] and g['t1'] <= x['t1']]
            if gs:
                x['t0w'] = max(g['t1'] for g in gs)
                n += 1
    return n


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else 0.0


def wait_pause(limit=25.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.01)
    return False


def write(addr, data):
    s.call("debug_write_memory", {"address": addr, "data": list(data)})


def warp_hero(row):
    """Переставить героя на глубокий ряд, чтобы поймать опасную ветку guard'а
    «луч далеко СВЕРХУ» (полоса внизу, всплеск начинается сразу). Колонку берём
    текущую. Физика игры потом может вернуть героя на пол — нам важно несколько
    кадров с глубокой полосой."""
    col = read(A_PLAYER_RC, 2)[1]
    cells = read(TB + row * COLS + col - 1, 3)
    write(A_PLAYER_RC, [row, col])
    write(A_ENEMY_RC, [row, col])
    write(S['var_hero_erow'], [row, col])
    write(ISLAND + 0x46, [col, row])         # var_scr_0909/090A (цель для guard'а)
    write(S['var_hero_newr'], [row])
    write(S['var_hero_newc'], [col])
    print(f"    герой переставлен на row={row} col={col} "
          f"(клетки {['%02x' % c for c in cells]})")
    return True


def start_game():
    """Довести ROM до геймплея: SPACE с проверкой var_frame_sub (на заставке
    lbl_main_game_loop не выполняется)."""
    for attempt in range(4):
        s.call("debug_run")
        time.sleep(0.2)
        s.call("debug_press_key", {"key": "SPACE"})
        time.sleep(0.6)
        s.call("debug_release_key", {"key": "SPACE"})
        s.call("debug_run")
        time.sleep(1.2)
        s.call("debug_pause")
        time.sleep(0.2)
        if read(A_SUB, 1)[0]:
            print(f"    геймплей с {attempt + 1}-й попытки SPACE")
            return True
    return False


# сценарий: зигзагом спуститься в самый низ (ряды 20+), потом подняться
ZIG = [('DOWN', 12), ('RIGHT', 8), ('DOWN', 12), ('LEFT', 8)]


def key_at(frame):
    if os.environ.get('PUTUP_WARP'):
        return 'LEFT' if (frame // 6) % 2 == 0 else 'RIGHT'
    if frame < 200:
        i = 0
        f = frame
        while f >= ZIG[i % len(ZIG)][1]:
            f -= ZIG[i % len(ZIG)][1]
            i += 1
        return ZIG[i % len(ZIG)][0]
    return 'UP'


def main():
    probe = Probe()
    phase, vis = [], []
    stops = 0
    cur_key = None
    try:
        s.start()
        s.load_rom(ROM, org=ROM_BASE)
        probe.arm(full=False)
        wait_pause(5.0)
        if not start_game():
            print("!! игра не стартовала (заставка): замеры невозможны")
            return 2
        probe.arm()
        WARP = os.environ.get('PUTUP_WARP')
        if WARP:
            WARP = int(WARP, 0)
            warp_hero(WARP)
        t_end = time.time() + 3000
        while len(probe.frames) < FRAMES and time.time() < t_end:
            if WARP and len(probe.frames) % 15 == 0:
                write(A_PLAYER_RC, [WARP, read(A_PLAYER_RC, 2)[1]])
                write(ISLAND + 0x46, [read(ISLAND + 0x46, 1)[0], WARP])
            k = key_at(len(probe.frames))
            if k != cur_key:
                if cur_key:
                    s.call("debug_release_key", {"key": cur_key})
                s.call("debug_press_key", {"key": k})
                cur_key = k
            s.call("debug_run")
            if not wait_pause(25.0):
                print("!! нет паузы за 25 c (брейкпоинт не достигнут?)")
                break
            r = regs()
            t, line, b = beam_state()
            e = elapsed()
            ph = line - e / float(LINE)
            if ph < -FRAME_LINES / 2:
                ph += FRAME_LINES
            phase.append(ph)
            if b['visible']:
                vis.append((b['raster_line'], b['visible_y']))
            stops += 1
            probe.handle(t, e, r)
        if cur_key:
            s.call("debug_release_key", {"key": cur_key})
    finally:
        s.close()

    ev = [verdict(x) for x in probe.events if x['closed']]
    nested = nest_guards(ev)
    ev = [verdict(x) for x in ev]
    print(f"стопов {stops}, кадров {len(probe.frames)}, закрытых окон {len(ev)}, "
          f"окон repaint с вычтенным вейтом guard'а: {nested}")
    try:
        os.makedirs(os.path.dirname(DUMP), exist_ok=True)
        json.dump({'phase': phase, 'events': ev,
                   'frames': probe.frames}, open(DUMP, 'w'))
        print("сырые события:", DUMP)
    except OSError as exc:
        print("(дамп событий не записан:", exc, ")")

    # [0] калибровка часов и поля -------------------------------------------
    ph = sorted(phase)
    if ph:
        print("\n[0] фаза часов: beam_line - elapsed/96 (в строках)")
        print(f"    медиана={pct(ph, .5):6.2f}  p5={pct(ph, .05):6.2f} "
              f"p95={pct(ph, .95):6.2f}  min={ph[0]:6.2f} max={ph[-1]:6.2f}")
    if vis:
        ft = sorted(a - b for a, b in vis)
        print(f"    видимое поле: raster_line - visible_y = медиана "
              f"{pct(ft, .5)}, разброс {ft[0]}..{ft[-1]} (модель ROM: поле "
              f"начинается на линии луча {FIELD_TOP})")

    # [1] окна записи -------------------------------------------------------
    print("\n[1] окна записи VRAM против полосы луча тайла")
    by_who = defaultdict(list)
    for x in ev:
        if not x['name'].startswith('guard'):
            by_who[x['who']].append(x)
    tears = 0
    for who in sorted(by_who, key=lambda k: -len(by_who[k])):
        vs = by_who[who]
        c = Counter(v['verdict'] for v in vs)
        d = [v['t1'] - v['t0'] for v in vs]
        ov = [v.get('overlap', 0) for v in vs if v['verdict'] == 'РАЗРЫВ']
        gaps = [v['gap'] for v in vs if 'gap' in v]
        tears += c['РАЗРЫВ']
        wrapped = sum(1 for v in vs if v.get('wrapped'))
        print(f"  {who:16s} n={len(vs):4d} дл.строк мед={pct(d, .5):5.1f} "
              f"p95={pct(d, .95):5.1f} max={max(d) if d else 0:5.1f} | "
              + (f"зазор мед={pct(gaps, .5):6.1f} p5={pct(gaps, .05):6.1f} | "
                 if gaps else "")
              + f"до={c['до луча']:4d} после={c['после луча']:4d} "
              f"РАЗРЫВ={c['РАЗРЫВ']:4d} через_кадр={wrapped:3d}"
              + (f"  перекрытие мед={pct(ov, .5):.1f} max={max(ov):.1f} строк"
                 if ov else ""))

    # [2] guard'ы ------------------------------------------------------------
    print("\n[2] raster-guard'ы: ожидание и порог var_raster_cap (0FFh = не ждал)")
    for g in ('guard_hero', 'guard_enemy'):
        gs = [x for x in ev if x['name'] == g]
        if not gs:
            print(f"  {g}: не вызывался")
            continue
        dur = [x['t1'] - x['t0'] for x in gs]
        spins = Counter(min(x['beams_wait'], 4) for x in gs)
        caps = Counter('не ждал' if x['cap'] == 0xFF else 'ЖДАЛ' for x in gs)
        early = [x for x in gs if x['beams_wait'] == 0]
        print(f"  {g}: n={len(gs)} длительность строк мед={pct(dur, .5):5.1f} "
              f"p95={pct(dur, .95):5.1f} max={max(dur):5.1f} | сразу (без вейта)"
              f"={len(early)} | циклов beam_count (4=>=4): {dict(sorted(spins.items()))} | "
              f"cap: {dict(caps)}")

    # [3] разрыв по строкам поля --------------------------------------------
    print("\n[3] окна по level row: где именно луч догоняет запись")
    print("    row   n   длительность      луч на входе   вердикты")
    per_row = defaultdict(list)
    for x in ev:
        if x['row'] is not None and x['row'] < 0x20:
            per_row[x['row']].append(x)
    for row in sorted(per_row):
        vs = per_row[row]
        c = Counter(v['verdict'] for v in vs)
        bt = FIELD_TOP + GLYPH_LINES * row
        print(f"    {row:3d} {len(vs):4d}  мед={pct([v['t1'] - v['t0'] for v in vs], .5):5.1f} "
              f"  line {pct([v['t0'] % FRAME_LINES for v in vs], .5):6.1f}      "
              f"до={c['до луча']:3d} после={c['после луча']:3d} "
              f"РАЗРЫВ={c['РАЗРЫВ']:3d}  полоса={bt}..{bt + TILE_LINES - 1}")

    # [4] всплеск целиком (erase->draw) за кадр ------------------------------
    print("\n[4] кадры: суммарный span записей героя и его конец относительно луча")
    per_frame = defaultdict(list)
    for x in ev:
        per_frame[int(x['t0'] // FRAME_LINES)].append(x)
    spans = []
    for fr in sorted(per_frame):
        w = [x for x in per_frame[fr] if x['who'] in
             ('hero-erase', 'or2(hero)', 'or3(hero)', 'repaint', 'tile_vram')]
        if len(w) >= 2:
            spans.append(max(x['t1'] for x in w) - min(x['t0'] for x in w))
    if spans:
        print(f"    n={len(spans)} span строк мед={pct(spans, .5):.1f} "
              f"p95={pct(spans, .95):.1f} max={max(spans):.1f} "
              f"(MARGIN guard'а = {MARGIN_ROM_LINES} строк)")

    # [5] разрывы ------------------------------------------------------------
    tl = [x for x in ev if x['verdict'] == 'РАЗРЫВ']
    print(f"\n[5] РАЗРЫВЫ луч/запись: {len(tl)}")
    for x in sorted(tl, key=lambda v: -v['overlap'])[:25]:
        bt, bb = x['band']
        print(f"    кадр {int(x['t0'] // FRAME_LINES)} line "
              f"{x['t0'] % FRAME_LINES:6.1f}..{x['t1'] % FRAME_LINES:6.1f} "
              f"перекрытие={x['overlap']:5.1f} полоса={bt:.0f}..{bb:.0f} "
              f"row={x['row']} col={x['col']} voff={x['voff']} hoff={x['hoff']} "
              f"{x['name']}<-{x['caller']}")

    print(f"\n[6] ИТОГО окон с перекрытием луча: {tears}")
    return 1 if tears else 0


if __name__ == '__main__':
    sys.exit(main())
