#!/usr/bin/env python3
"""beam_scan.py — поштучные записи скана огня/выхода (func_render_all ->
func_draw_char_at_hl) против луча.

func_render_all пишет НЕ весь чанк, а только «флипаемые» клетки (огонь 75h<->FEh,
выход 16h..19h<->12h..15h) через func_draw_char_at_hl. Каждая такая запись —
глиф 8x8 в полосе луча [48+8*row .. 48+8*row+7]. Ловим вход в func_draw_char_at_hl
(стоп), берёт HL=клетка (row=(HL-TB)/32, col=%32), возвращающий адрес (стека) и
положение луча. Если на момент записи луч внутри полосы клетки — это tearing.

Фильтр по caller: loc_ra_next в func_render_all (адрес из tools/layout.json,
только скан; hand-константа устаревала при каждом сдвиге компоновки).

Запуск: python3 tools/beam_scan.py [КАДРОВ]
"""
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

S = json.load(open(os.path.join(PROJECT, 'tools', 'layout.json')))
S = S.get('symbols', S)
FRAME_LINES = 312
FIELD_TOP = 48
TB = S['data_text_buffer']
COLS = 32
DRAW = S['func_draw_char_at_hl']
SCAN_RET = S['loc_ra_next']       # возврат CALL func_draw_char_at_hl в func_render_all
MAIN = S['lbl_main_game_loop']

s = McpSession(cwd=ROOT)


def rd(a, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": a, "size": n})))


def regs():
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def beam():
    b = s.call("debug_get_beam_state")
    return b['frame'] * FRAME_LINES + b['raster_line'] + \
        b['v_cycle_in_line'] / 768.0, b


def wait(lim=25.0):
    t0 = time.time()
    while time.time() - t0 < lim:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.01)
    return False


def start_game():
    s.call("debug_set_breakpoint", {"address": MAIN})
    wait(5.0)
    for i in range(4):
        s.call("debug_run"); time.sleep(0.2)
        s.call("debug_press_key", {"key": "SPACE"}); time.sleep(0.6)
        s.call("debug_release_key", {"key": "SPACE"})
        s.call("debug_run"); time.sleep(1.2)
        s.call("debug_pause"); time.sleep(0.2)
        if rd(S['var_frame_sub'], 1)[0]:
            print(f"    геймплей с {i + 1}-й попытки")
            return True
    return False


FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 20
recs = []
CALLERS = {}
frames = 0
s.start()
try:
    s.load_rom(os.path.join(PROJECT, 'putup_new.rom'), org=0x0100)
    if not start_game():
        print("!! не стартовала"); sys.exit(2)
    s.call("debug_set_breakpoint", {"address": DRAW})   # MAIN уже стоит
    t_end = time.time() + 1500
    while frames < FRAMES and time.time() < t_end:
        s.call("debug_run")
        if not wait():
            print("!! нет паузы"); break
        r = regs()
        t, b = beam()
        if r['pc'] == MAIN:
            frames += 1
            continue
        lo, hi = rd(r['sp'], 2)
        ret = lo | hi << 8
        CALLERS[ret] = CALLERS.get(ret, 0) + 1
        if ret != SCAN_RET:
            continue
        row = (r['hl'] - TB) // COLS
        col = (r['hl'] - TB) % COLS
        code = rd(r['hl'], 1)[0]
        top = FIELD_TOP + 8 * row
        recs.append({'frame': frames, 't': t, 'row': row, 'col': col, 'code': code,
                     'line': b['raster_line'], 'vis_y': b.get('visible_y'),
                     'inband': top <= (t % FRAME_LINES) <= top + 7})
finally:
    s.close()

print(f"записей скана поймано: {len(recs)} за {frames} кадров")
print("возвращающие адреса func_draw_char_at_hl:",
      {hex(k): v for k, v in sorted(CALLERS.items(), key=lambda kv: -kv[1])[:10]})
if recs:
    per_row = defaultdict(list)
    for x in recs:
        per_row[x['row']].append(x)
    print("\nrow    n  полосы луча   линии записи (min..max)   в полосе своего ряда")
    for row in sorted(per_row):
        vs = per_row[row]
        top = FIELD_TOP + 8 * row
        lines = [v['line'] for v in vs]
        n_in = sum(1 for v in vs if v['inband'])
        print(f"{row:4d} {len(vs):4d}  {top:3d}..{top + 7:3d}   "
              f"{min(lines):3d}..{max(lines):3d}   {n_in:4d}  ({100.0 * n_in / len(vs):5.1f}%)")
    c = Counter(x['code'] for x in recs)
    print("\nкоды клеток:", dict(sorted(c.items())))
    print("всего записей в полосе своего ряда:", sum(1 for x in recs if x['inband']))
    js = os.path.join(PROJECT, '.scratch', 'beam_scan_recs.json')
    json.dump(recs, open(js, 'w'))
    print("записи:", js)
