#!/usr/bin/env python3
"""beam_pickup.py — КАК УДАЛЯЮТСЯ предметы (фрукт / кольцо-жизнь / яйцо-ключ) и
ГДЕ при этом луч.

Два вопроса, на которые инструмент отвечает одним прогоном:

(A) МЕХАНИКА УДАЛЕНИЯ. Каждый кадр снимается снапшот всего текстового буфера
    (768 клеток) и полный журнал поштучных блитов глифов в VRAM
    (BP на func_render_glyph = единственный писатель пикселей в буфер; на него
    приходят и func_put_char (запись кода клетки + глиф), и func_draw_tile_at_ptr,
    и func_render_tile_vram). Сопоставление «BUF-изменились» против «VRAM-записали»
    по клеткам даёт точный ответ: стирание предмета = запись 0x20 в клетку +
    обязательный блит пустого глифа, или достаточно только записи в клетку?

(B) ПОЛОЖЕНИЕ ЛУЧА. Для каждого блита известна его точная линия луча и его
    клетка (row,col) => полоса луча клетки = [48+8*row .. 48+8*row+7]
    (калибровка — см. tools/beam_hero.py, .scratch/vram_geom2.py). Отсюда:
      * tearing — луч сканировал клетку во время её записи;
      * ДВОЙНАЯ запись одной клетки в одном кадре РАЗНЫМИ кодами — был ли луч
        на полосе клетки МЕЖДУ записями (тогда промежуточное состояние реально
        попало на экран = мерцание).

Отбор кадров: сбор предмета определяется по изменению var_score /
var_bonus_counter (жизни) / var_egg_counter, тип — по var_collision_flag в момент
эпилога. Предметы подводятся герою режимом HUNT (героя переставляет на клетку
НАД ближайшим предметом; гравитация +1 ряд на update-кадре сама «надевает» его
на предмет) — иначе собирается то, что встречается само.

Запуск:
    python3 tools/beam_pickup.py [КАДРОВ] [файл.json]
    PUTUP_CODES=6E,72   ограничить коды для HUNT
    PUTUP_QUIET=1       не печатать поштучные таймлайны
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

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 60
DUMP = sys.argv[2] if len(sys.argv) > 2 else os.path.join(PROJECT, '.scratch',
                                                          'beam_pickup.json')
ROM = os.environ.get('PUTUP_ROM') or os.path.join(PROJECT, 'putup_new.rom')
S = json.load(open(os.environ.get('PUTUP_LAYOUT') or
                   os.path.join(PROJECT, 'tools', 'layout.json')))
S = S.get('symbols', S)
QUIET = bool(os.environ.get('PUTUP_QUIET'))
CODES = [int(x, 16) for x in os.environ.get('PUTUP_CODES', '6E,6F,70,71,72,73').split(',') if x]
# PUTUP_INJECT=6E,72 — принудительно подсаживать предмет ПРЯМО ПОД ГЕРОЯ (в
# текстовый буфер), чтобы собрать статистику по каждому типу, а не по тому, что
# повстречается. Код кладётся в клетки (player_row+2, col..col+1): game_update
# сначала прибавляет ряд, потом читает клетку под героем.
INJECT = [int(x, 16) for x in os.environ.get('PUTUP_INJECT', '').split(',') if x]
# PUTUP_WARP=24 — каждые 15 кадров принудительно возвращать героя на row=WARP,
# чтобы собрать статистику сборов на глубоких рядах (24..26). Без INJECT
# предмет всё равно подсаживается штатной логикой (или hunt'ом).
WARP = int(os.environ.get('PUTUP_WARP', '0'), 0) or 0

ROM_BASE = 0x0100
LINE = 96                 # отсчётов секундомера на строку растра
FRAME_LINES = 312         # строк луча в кадре
VC_LINE = 768
FIELD_TOP = 48            # линия луча начала level row 0 (калибровано)
GLYPH_LINES = 8
COLS = 32
ROWS = 24
BUFFER_CELLS = COLS * ROWS

MAIN = S['lbl_main_game_loop']
GLYPH = S['func_render_glyph']          # 0x0651 — единый блит 8x8 в VRAM
# окна-менеджеры: чтобы каждый блит был приписан к смыслу (сбор/рисунок/скан)
WINDOWED = {
    'game_update': S['func_game_update'],
    'hero_render': S['func_hero_render'],
    'enemy_render': S['func_enemy_render'],
    'render_all': S['func_render_all'],
    'guard_hero': S['func_raster_guard_hero'],
    'tile_at_ptr': S['func_draw_tile_at_ptr'],
    'tile_vram': S['func_render_tile_vram'],
    'or2(hero)': S['func_render_tile_vram_or'],
    'or3(hero)': S['func_render_tile_vram_or3'],
    'repaint': S['func_hero_repaint_over'],
    'EPILOG score_and_redraw': S['func_score_and_redraw'],
    'draw_tile_to_buf': S['func_draw_tile_to_buf'],
    'draw_score_hud': S['func_draw_score_hud'],
    'draw_status_hud': S['func_draw_status_hud'],
    'bonus_collect': S['func_item_bonus_collect'],
    'bonus_timer': S['func_item_bonus_timer'],
    'egg_caught': S['func_egg_caught'],
    'spawn_egg': S['func_spawn_egg'],
    'erase_char_08E9': S['func_erase_char_08E9'],
    'player_move_a': S['func_player_move_a'],
}
# посредники в цепочке вызовов: их не показываем как «кого»
PASS_THROUGH = ('func_draw_char_at_hl', 'func_put_char', 'func_print_char_at_ptr',
                'func_render_glyph')

ISLAND = S['data_ram_init_image_08C3']
A_SCORE = ISLAND + 0x30           # слово
A_BLINK_CELL = ISLAND + 0x26      # слово: курсор скана мигания/стирания
A_BLINK_TYPE = ISLAND + 0x27
A_LIVES = ISLAND + 0x38           # var_bonus_counter = жизни
A_PLAYER_RC = ISLAND + 0x3E       # (row, col) — цель easing'а
A_COLL = ISLAND + 0x42            # var_collision_flag (код собранной клетки)
A_EGGS = ISLAND + 0x4C            # var_egg_counter
A_ENEMY_RC = ISLAND + 0x20        # lo=строка, hi=колонка отображаемого героя
A_GSTATE = ISLAND + 0x3D          # var_game_state (0 игра, 1 ловушка, 2 уклонение)
A_SCR909 = ISLAND + 0x46          # var_scr_0909/090A = (col,row) цели для guard'а
TB = S['data_text_buffer']
A_VOFF = S['var_glyph_voff']
A_HOFF = S['var_glyph_hoff']
A_SUB = S['var_frame_sub']
A_HERO_EROW = S['var_hero_erow']
A_RASTER_CAP = S['var_raster_cap']

ITEM_NAMES = {0x6E: 'фрукт1', 0x6F: 'фрукт2', 0x70: 'фрукт3', 0x71: 'фрукт4',
              0x72: 'ЯЙЦО-КЛЮЧ (бонус)', 0x73: 'КОЛЬЦО (+жизнь)',
              0x74: "'т' (выход)", 0x75: 'огонь A', 0x76: "'v' (твёрдое)",
              0xFE: 'огонь B', 0x20: 'пусто (0x20)'}

SYMS_SORTED = sorted((a, n) for n, a in S.items() if isinstance(a, int))


def owner(addr):
    i = bisect.bisect_right(SYMS_SORTED, (addr, '\uffff')) - 1
    return SYMS_SORTED[i][1] if i >= 0 and SYMS_SORTED[i][0] <= addr else '?'


s = McpSession(cwd=ROOT)


def regs():
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def write(addr, data):
    s.call("debug_write_memory", {"address": addr, "data": list(data)})


def beam_t():
    b = s.call("debug_get_beam_state")
    return b['frame'] * FRAME_LINES + b['raster_line'] + b['v_cycle_in_line'] / float(VC_LINE)


def wait_pause(limit=25.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.01)
    return False


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else 0.0


class Probe:
    def __init__(self):
        self.names = {}
        self.open = {}
        self.ret_of = defaultdict(set)
        self.bps = set()
        self.glyphs = []        # поштучные блиты
        self.windows = []       # окна менеджеров/гардов/рисовальщиков
        self.frames = []        # (t_main, ctx)
        self.stops = 0

    def bp(self, addr):
        if addr not in self.bps:
            s.call("debug_set_breakpoint", {"address": addr})
            self.bps.add(addr)

    def arm(self):
        for name, addr in WINDOWED.items():
            self.names[addr] = name
            self.open.setdefault(name, [])
            self.bp(addr)
        self.names[MAIN] = '_frame'
        self.bp(MAIN)
        self.names[GLYPH] = '_glyph'
        self.bp(GLYPH)

    def frame_ctx(self):
        sc = read(A_SCORE, 2)
        return {
            'sub': read(A_SUB, 1)[0],
            'score': sc[0] | sc[1] << 8,
            'lives': read(A_LIVES, 1)[0],
            'eggs': read(A_EGGS, 1)[0],
            'coll': read(A_COLL, 1)[0],
            'gstate': read(A_GSTATE, 1)[0],
            'prow': read(A_PLAYER_RC, 2)[0], 'pcol': read(A_PLAYER_RC, 2)[1],
            'erow': read(A_ENEMY_RC, 2)[0], 'ecol': read(A_ENEMY_RC, 2)[1],
            'buf': read(TB, BUFFER_CELLS),
        }

    def chain(self, t):
        """имена окон, открытых в момент t (внешний→внутренний)"""
        out = []
        for name, stack in self.open.items():
            for e in stack:
                if e['t0'] <= t:
                    out.append(e['short'])
        return '/'.join(sorted(set(out)))

    def handle(self, t, r):
        self.stops += 1
        pc = r['pc']
        if pc == MAIN:
            self.frames.append({'t': t, 'ctx': self.frame_ctx()})
            for k in self.open:
                self.open[k] = []
            return
        if pc == GLYPH:
            st = read(r['sp'], 4)
            ret1 = st[0] | st[1] << 8
            ret2 = st[2] | st[3] << 8
            caller = owner(ret1)
            via = caller
            if caller in PASS_THROUGH:
                caller = owner(ret2)
            cell = r['hl'] - TB
            self.glyphs.append({
                't': t, 'frame': int(t // FRAME_LINES), 'line': t % FRAME_LINES,
                'row': cell // COLS if 0 <= cell < BUFFER_CELLS else None,
                'col': cell % COLS if 0 <= cell < BUFFER_CELLS else None,
                'code': r['a'] & 0xFF, 'caller': caller, 'via': via,
                'hl': r['hl'],
                'win': self.chain(t), 'sub': read(A_SUB, 1)[0],
            })
            return
        name = self.names.get(pc)
        if name is None:
            return
        if pc in self.ret_of[name]:
            if not self.open[name]:
                return
            ent = self.open[name].pop()
            ent['t1'] = t
            ent['closed'] = True
            if name.startswith('guard'):
                ent['cap'] = read(A_RASTER_CAP, 1)[0]
            self.windows.append(ent)
            return
        st = read(r['sp'], 2)
        ret = st[0] | st[1] << 8
        ent = {'name': name, 'short': name, 't0': t, 'line': t % FRAME_LINES,
               'frame': int(t // FRAME_LINES), 'caller': owner(ret),
               'closed': False, 'sub': read(A_SUB, 1)[0],
               'coll': read(A_COLL, 1)[0], 'score': (lambda x: x[0] | x[1] << 8)(read(A_SCORE, 2))}
        if name in ('or2(hero)', 'or3(hero)', 'tile_vram', 'repaint'):
            if name == 'repaint':
                rc = read(A_ENEMY_RC, 2)
                ent['row'], ent['col'] = rc[0], rc[1]
            else:
                ent['row'], ent['col'] = r['e'] & 0xFF, r['d'] & 0xFF
            ent['voff'], ent['hoff'] = read(A_VOFF, 1)[0], read(A_HOFF, 1)[0]
        if name == 'tile_at_ptr':
            rc = read(r['hl'], 2)
            ent['row'], ent['col'] = rc[0], rc[1]
        if name == 'EPILOG score_and_redraw' or name.startswith('bonus') or \
           name in ('egg_caught', 'erase_char_08E9', 'spawn_egg'):
            ent['blink'] = (lambda x: x[0] | x[1] << 8)(read(A_BLINK_CELL, 2))
            ent['blink_type'] = read(A_BLINK_TYPE, 1)[0]
        self.open[name].append(ent)
        if ret not in self.bps:
            self.bp(ret)
            self.names[ret] = name
            self.ret_of[name].add(ret)


def hunt_item(buf, prow, pcol):
    """ближайшая клетка-предмет, на которую можно «надеть» героя (герой ставится
    на row-2: update-кадр прибавит ряд, и предмет окажется ровно под ним)"""
    best = None
    for r in range(ROWS):
        for c in range(COLS):
            code = buf[r * COLS + c]
            if code in CODES:
                d = abs(r - 2 - prow) + abs(c - pcol)
                if r >= 2 and c + 1 < COLS:
                    if best is None or d < best[0]:
                        best = (d, r, c, code)
    return best


def inject(code_list, idx):
    """подсадить предмет в клетки (prow+2, pcol..pcol+1) — ровно туда, куда
    посмотрит func_game_update после INR var_player_row"""
    prow, pcol = read(A_PLAYER_RC, 2)
    code = code_list[idx % len(code_list)]
    done = []
    for c in (pcol, pcol + 1):
        if 0 <= prow + 2 < ROWS and 0 <= c < COLS:
            write(TB + (prow + 2) * COLS + c, [code])
            done.append((prow + 2, c, code))
    return done


def warp(hero_row, hero_col):
    write(A_PLAYER_RC, [hero_row, hero_col])
    write(A_ENEMY_RC, [hero_row, hero_col])
    write(A_HERO_EROW, [hero_row, hero_col])
    write(A_SCR909, [hero_col, hero_row])
    write(S['var_hero_newr'], [hero_row])
    write(S['var_hero_newc'], [hero_col])


ZIG = [('DOWN', 10), ('RIGHT', 6), ('DOWN', 10), ('LEFT', 6)]


def key_at(f):
    i = 0
    fr = f
    while fr >= ZIG[i % len(ZIG)][1]:
        fr -= ZIG[i % len(ZIG)][1]
        i += 1
    return ZIG[i % len(ZIG)][0]


def start_game(probe):
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


def band_of(row, n_rows=1):
    """линии луча, которые сканирует полоса клеток row..row+n_rows-1"""
    return FIELD_TOP + GLYPH_LINES * row, FIELD_TOP + GLYPH_LINES * (row + n_rows) - 1


def beam_crosses(ta, tb, row, n_rows=1):
    """прошёл ли луч по полосе клетки между моментами ta и tb (tb >= ta, в
    абсолютных линиях); возвращает линию прохода или None"""
    lo, hi = band_of(row, n_rows)
    fa = int(ta // FRAME_LINES)
    for f in range(fa, int(tb // FRAME_LINES) + 1):
        a, b = max(ta, lo + f * FRAME_LINES), min(tb, hi + f * FRAME_LINES)
        if a < b:
            return (lo + f * FRAME_LINES + hi + f * FRAME_LINES) / 2.0
    return None


def main():
    if os.environ.get('REPORT_ONLY'):
        report(json.load(open(DUMP)))
        return 0
    probe = Probe()
    hunts, pickups, inj_idx = 0, 0, 0
    cur_key = None
    last_inj_frame = -99
    try:
        s.start()
        s.load_rom(ROM, org=ROM_BASE)
        probe.bp(MAIN)
        wait_pause(5.0)
        if not start_game(probe):
            print("!! игра не стартовала (заставка): замеры невозможны")
            return 2
        probe.arm()
        if WARP:
            warp(WARP, read(A_PLAYER_RC, 2)[1])
        t_deadline = time.time() + 2400
        while len(probe.frames) < FRAMES and time.time() < t_deadline:
            fr = len(probe.frames)
            if WARP and fr and (fr % 15 == 0):
                # штатный гравитационный сдвиг уводит героя вниз; возврат на
                # WARP держит выборку на глубоких рядах долго
                write(A_PLAYER_RC, [WARP, read(A_PLAYER_RC, 2)[1]])
                write(A_ENEMY_RC, [WARP, read(A_ENEMY_RC, 2)[1]])
                write(A_SCR909, [read(A_SCR909, 1)[0], WARP])
            if fr:
                ctx = probe.frames[-1]['ctx']
                if ctx['gstate'] == 0 and (fr - last_inj_frame) >= 4:
                    if INJECT:
                        prow, pcol = read(A_PLAYER_RC, 2)
                        below = ctx['buf'][(prow + 2) * COLS + pcol] if prow + 2 < ROWS else 0
                        if below not in CODES and inject(INJECT, inj_idx):
                            inj_idx += 1
                            last_inj_frame = fr
                    elif fr % 12 == 0:
                        it = hunt_item(ctx['buf'], ctx['prow'], ctx['pcol'])
                        if it:
                            _, r, c, code = it
                            warp(r - 2, c)
                            hunts += 1
            k = key_at(fr)
            if k != cur_key:
                if cur_key:
                    s.call("debug_release_key", {"key": cur_key})
                s.call("debug_press_key", {"key": k})
                cur_key = k
            s.call("debug_run")
            if not wait_pause(25.0):
                print("!! нет паузы за 25 c")
                break
            probe.handle(beam_t(), regs())
        if cur_key:
            s.call("debug_release_key", {"key": cur_key})
    finally:
        s.close()

    print(f"стопов {probe.stops}, кадров {len(probe.frames)}, подводок к предметам "
          f"{hunts}, блитов глифов {len(probe.glyphs)}, окон {len(probe.windows)}")
    ev = {'frames': probe.frames, 'glyphs': probe.glyphs, 'windows': probe.windows}
    try:
        os.makedirs(os.path.dirname(DUMP), exist_ok=True)
        json.dump(ev, open(DUMP, 'w'))
        print("сырые данные:", DUMP)
    except OSError as exc:
        print("(дамп не записан:", exc, ")")
    report(ev)
    return 0


def report(ev):
    frames, glyphs, wins = ev['frames'], ev['glyphs'], ev['windows']
    n = len(frames)
    if n < 3:
        print("!! кадров меньше трёх — выводов не будет")
        return
    # ---- [1] детекция сборов ------------------------------------------------
    picks = []
    pickup_frames = set()
    for i in range(1, n):
        a, b = frames[i - 1]['ctx'], frames[i]['ctx']
        d_score = b['score'] - a['score']
        d_lives = b['lives'] - a['lives']
        d_eggs = b['eggs'] - a['eggs']
        if d_score or d_lives or d_eggs:
            picks.append((i, d_score, d_lives, d_eggs, b['coll']))
            pickup_frames.update((i - 1, i))
    print(f"\n[1] кадры с изменением счёта/жизней/яиц: {len(picks)} из {n}")
    if not picks:
        print("    !! сборов не случилось — увеличить КАДРЫ или задать PUTUP_CODES")
    for (i, ds, dl, de, coll) in picks[:20]:
        print(f"    кадр {i:4d} Δсчёт={ds:+5d} Δжизни={dl:+2d} Δяйца={de:+2d} "
              f"код клетки={coll:02X} ({ITEM_NAMES.get(coll, '?')}) "
              f"герой(row={frames[i]['ctx']['erow']},col={frames[i]['ctx']['ecol']}) "
              f"цель(row={frames[i]['ctx']['prow']},col={frames[i]['ctx']['pcol']})")
    # ---- [2] что пишут блиты: код × вызывающий ------------------------------
    print("\n[2] поштучные блиты глифов (func_render_glyph): код × цепочка вызова")
    by = Counter((g['code'], g['win'] or g['caller']) for g in glyphs)
    for (code, win), c in by.most_common(28):
        nm = ITEM_NAMES.get(code, '')
        print(f"    code {code:02X} {nm:18s} n={c:5d}  {win}")
    # ---- [3] дифф буфера против блитов по клеткам ---------------------------
    print("\n[3] изменение ТЕКСТОВОГО БУФЕРА (клетка) vs запись пикселей в VRAM")
    cellbuf = defaultdict(list)      # (row,col) -> [(frame, old, new)]
    for i in range(1, n):
        a, b = frames[i - 1]['ctx']['buf'], frames[i]['ctx']['buf']
        for k in range(BUFFER_CELLS):
            if a[k] != b[k]:
                cellbuf[(k // COLS, k % COLS)].append((i, a[k], b[k]))
    cellvram = defaultdict(list)     # (row,col) -> [(frame, t, code)]
    for g in glyphs:
        if g['row'] is not None:
            cellvram[(g['row'], g['col'])].append((g['frame'], g['t'], g['code']))
    to_items = [x for x in cellbuf if any(o in CODES for _, o, _ in cellbuf[x])]
    print(f"    клеток с изменением кода: {len(cellbuf)}, из них когда-либо "
          f"содержали предмет (6E..73): {len(to_items)}")
    only_buf = [x for x in cellbuf if x not in cellvram]
    print(f"    клеток, где КОД поменялся, но пиксели НЕ перезаписывались ни разу: "
          f"{len(only_buf)}  {sorted(only_buf)[:12]}")
    # ---- [4] кадры сбора: таймлайн -----------------------------------------
    print("\n[4] таймлайн кадров сбора (линия луча, клетка, код, кем)")
    pickset = {i for (i, _, _, _, _) in picks}
    pf = sorted(pickset)
    show = pf if not QUIET else pf[:8]
    for i in show[:14]:
        lo = frames[i - 1]['t']
        hi = frames[i + 1]['t'] if i + 1 < n else frames[i]['t'] + FRAME_LINES
        gs = [g for g in glyphs if lo <= g['t'] < hi]
        ws = [w for w in wins if lo <= w['t0'] < hi and w['closed']]
        ctx = frames[i]['ctx']
        print(f"\n  --- кадр {i}: код клетки {ctx['coll']:02X} "
              f"({ITEM_NAMES.get(ctx['coll'], '?')}), герой (r={ctx['erow']},c={ctx['ecol']}) "
              f"цель (r={ctx['prow']},c={ctx['pcol']}), блитов {len(gs)}")
        for w in sorted(ws, key=lambda x: x['t0']):
            print(f"      окно {w['short']:22s} line {w['t0'] % FRAME_LINES:6.1f}.."
                  f"{w['t1'] % FRAME_LINES:6.1f} (cap={w.get('cap', '-')}) "
                  f"<-{w['caller']}" + (f" row={w.get('row')} col={w.get('col')}"
                                        if w.get('row') is not None else ''))
        for g in sorted(gs, key=lambda x: x['t']):
            band = band_of(g['row']) if g['row'] is not None else (None, None)
            inband = ''
            if g['row'] is not None:
                f0 = int(g['t'] // FRAME_LINES) * FRAME_LINES
                inband = 'ЛУЧ В ПОЛОСЕ' if band[0] + f0 <= g['t'] <= band[1] + f0 else 'вне полосы'
            rc = (f"r{g['row']:2d} c{g['col']:2d}" if g['row'] is not None
                  else f"вне буфера (HL={g.get('hl', 0):04X})")
            print(f"      глиф  line {g['line']:6.1f} клетка {rc} "
                  f"код {g['code']:02X} полоса={band[0]}..{band[1]} [{inband:11s}] "
                  f"{g['win'] or g['via']}")
    # ---- [5] двойные записи клетки в одном кадре ----------------------------
    print("\n[5] двойная запись ОДНОЙ клетки в одном кадре и луч между записями")
    doubles, seen_between = 0, 0
    pairs = defaultdict(list)
    for g in glyphs:
        if g['row'] is None:
            continue
        pairs[(g['frame'], g['row'], g['col'])].append(g)
    example = []
    for key in sorted(pairs):
        seq = sorted(pairs[key], key=lambda x: x['t'])
        if len(seq) < 2:
            continue
        codes = {x['code'] for x in seq}
        if len(codes) < 2:
            continue
        doubles += 1
        crossed = None
        for a, b in zip(seq, seq[1:]):
            if a['code'] != b['code']:
                cr = beam_crosses(a['t'], b['t'], key[1])
                if cr is not None:
                    crossed = (a, b, cr)
        if crossed:
            seen_between += 1
            if len(example) < 12:
                a, b, cr = crossed
                example.append((key, a, b, cr))
    print(f"    клеток с записью РАЗНЫМИ кодами в одном кадре: {doubles}, из них луч "
          f"успел просканировать клетку между записями (промежуточное состояние "
          f"видели): {seen_between}")
    for (key, a, b, cr) in example:
        fr, row, col = key
        print(f"      кадр {fr} клетка r{row} c{col}: {a['code']:02X} (line {a['line']:5.1f},"
              f" {a['win']}) -> {b['code']:02X} (line {b['line']:5.1f}, {b['win']}), "
              f"луч на {cr % FRAME_LINES:5.1f}")
    # ---- [6] tearing точечных записей --------------------------------------
    print("\n[6] записи, попавшие под луч (tearing отдельного блита)")
    tear = []
    for g in glyphs:
        if g['row'] is None:
            continue
        f0 = int(g['t'] // FRAME_LINES) * FRAME_LINES
        lo_, hi_ = band_of(g['row'])
        if lo_ + f0 <= g['t'] <= hi_ + f0:
            tear.append(g)
    print(f"    всего {len(tear)} из {len([x for x in glyphs if x['row'] is not None])}")
    for g in Counter((g['win'] or g['via']) for g in tear).most_common(12):
        print(f"      {g[1]:5d}  {g[0]}")
    # ---- [7] итоги по типам сборов -----------------------------------------
    print("\n[7] сводка по механике")
    kinds = Counter()
    for (i, ds, dl, de, coll) in picks:
        kinds[ITEM_NAMES.get(coll, f'код {coll:02X}')] += 1
    print(f"    собрано за прогон: {dict(kinds)}")
    ep = [w for w in wins if w['name'] == 'EPILOG score_and_redraw']
    dtb = [w for w in wins if w['name'] == 'draw_tile_to_buf']
    sh = [w for w in wins if w['name'] == 'draw_score_hud']
    sth = [w for w in wins if w['name'] == 'draw_status_hud']
    ec = [w for w in wins if w['name'] == 'erase_char_08E9']
    egg = [w for w in wins if w['name'] == 'egg_caught']
    sp = [w for w in wins if w['name'] == 'spawn_egg']
    bc = [w for w in wins if w['name'] == 'bonus_collect']
    bt = [w for w in wins if w['name'] == 'bonus_timer']
    for nm, lst in (('score_and_redraw (эпилог)', ep), ('draw_tile_to_buf', dtb),
                    ('draw_score_hud', sh), ('draw_status_hud', sth),
                    ('erase_char_08E9', ec), ('egg_caught', egg), ('spawn_egg', sp),
                    ('bonus_collect', bc), ('bonus_timer', bt)):
        if lst:
            d = [x['t1'] - x['t0'] for x in lst]
            print(f"    {nm:24s} n={len(lst):4d} длительность строк мед={pct(d, .5):5.1f} "
                  f"max={max(d):5.1f}")
        else:
            print(f"    {nm:24s} не вызывался")
    guard = [w for w in wins if w['name'] == 'guard_hero']
    if guard:
        caps = Counter('не ждал' if w.get('cap') == 0xFF else 'ЖДАЛ' for w in guard)
        d = [w['t1'] - w['t0'] for w in guard]
        print(f"    guard_hero n={len(guard)} вейт строк мед={pct(d, .5):5.1f} "
              f"max={max(d):5.1f} cap: {dict(caps)} (защита есть ТОЛЬКО у рисовальщиков "
              f"героя/погонщика)")
    mechanics(ev)


def mechanics(ev):
    """[8] МЕХАНИКА УДАЛЕНИЯ: какие клетки стирает эпilog сбора, кто ЕЩЁ пишет те
    же клетки в том же кадре, и был бы виден «призрак», если бы эпilog писал
    только в текстовый буфер (без блита в VRAM) — т.е. когда клетку перекрасил
    бы штатный проход восстановления фона."""
    n = len(ev['frames'])
    ts = [f['t'] for f in ev['frames']]

    def mi(t):
        return max(i for i in range(n) if ts[i] <= t) if t >= ts[0] else 0

    writes = defaultdict(list)          # (iter, row, col) -> [(code, writer)]
    for g in ev['glyphs']:
        if g['row'] is None:
            continue
        writes[(mi(g['t']), g['row'], g['col'])].append((g['code'], g['win'] or g['via']))
    for w in ev['windows']:             # OR-рисовальщики идут мимо render_glyph
        if w.get('row') is None or w['row'] >= ROWS or not w['closed']:
            continue
        r, c = w['row'], w['col']
        tag = w['name'] + '<-' + w['caller']
        for rr in (r, r + 1):
            if rr >= ROWS:
                continue
            cols = (c, c + 1, c + 2) if w['name'] == 'or3(hero)' else (c, c + 1)
            for cc in cols:
                if 0 <= cc < COLS:
                    writes[(mi(w['t0']), rr, cc)].append(('HERO', tag))
    picks = []
    for i in range(1, n):
        a, b = ev['frames'][i - 1]['ctx'], ev['frames'][i]['ctx']
        if b['score'] != a['score'] or b['lives'] != a['lives'] or b['eggs'] != a['eggs']:
            picks.append((i, b['coll']))
    print("\n[8] механика удаления предмета (эпилог vs штатное восстановление фона)")
    if not picks:
        print("    сборов за прогон не было")
        return 0
    per_pick = []
    for (i, code) in picks:
        it = i - 1                                  # сбор случился в итерации it
        cleared = [(k[1], k[2], w) for k, v in writes.items()
                   if k[0] == it for (cd, w) in v
                   if 'EPILOG' in w or 'erase_char' in w or 'draw_tile_to_buf' in w]
        cells = sorted({(r, c) for r, c, _ in cleared})
        buf_before = ev['frames'][max(0, it - 1)]['ctx']['buf']
        rows = []
        for (r, c) in cells:
            who = [w for (cd, w) in writes[(it, r, c)]]
            nxt = None
            for j in range(it + 1, min(n, it + 7)):
                if (j, r, c) in writes and any('EPILOG' not in w for cd, w in writes[(j, r, c)]):
                    nxt = j - it
                    break
            rows.append((r, c, buf_before[r * COLS + c], sorted(set(who)), nxt))
        per_pick.append((i, code, rows))
    kinds = defaultdict(list)
    for (i, code, rows) in per_pick:
        kinds[ITEM_NAMES.get(code, f'код {code:02X}')].append(rows)
    for kind in sorted(kinds, key=lambda k: -len(kinds[k])):
        lst = kinds[kind]
        print(f"  {kind}: сборов {len(lst)}")
        wcount = Counter()
        delays = []
        for rows in lst:
            for (r, c, oldcode, who, nxt) in rows:
                wcount[len(who)] += 1
                if oldcode not in (0x20,):
                    delays.append(nxt if nxt is not None else 99)
        print(f"    стиралось клеток на сбор: "
              f"{sorted(Counter(len(rows) for rows in lst).items())}")
        print(f"    записей в ОДНУ клетку в кадре сбора: "
              f"{dict(sorted(wcount.items()))} (1 = только эпilog, 2+ = эпilog + ещё)")
        if delays:
            print(f"    когда ЭТУ клетку перекрасил бы штатный писатель (кадров "
              f"спустя, 99 = за 6 кадров ни одного): мед={pct(delays, .5)} "
              f"p95={pct(delays, .95)} max={max(delays)} "
              f"распределение={dict(sorted(Counter(delays).items()))}")
    if not QUIET:
        for (i, code, rows) in per_pick[:10]:
            print(f"\n    --- сбор на итерации {i} (код {code:02X} "
                  f"{ITEM_NAMES.get(code, '')})")
            for (r, c, oldcode, who, nxt) in rows:
                print(f"        клетка r{r:2d} c{c:2d}: в буфере было {oldcode:02X}, "
                      f"писателей в кадре {len(who)}: {who}; "
                      f"следующий перекрас через {nxt if nxt is not None else '>6'} кадр(ов)")
    return len(per_pick)


if __name__ == '__main__':
    sys.exit(main())
