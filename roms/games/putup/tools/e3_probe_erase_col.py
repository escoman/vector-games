#!/usr/bin/env python3
"""Проб: что реально рисует func_ed_erase_col за один вызов func_ed_erase_old.

Ловим вход в erase, затем на каждом входе func_render_glyph пишем (A=код, HL=клетка
буфера) до RET erase'а. Плюс расшифровка приёмникаGlyph: HL -> (row,col) и адреса
плоскостей. Ответ на вопрос «ROM отрисовал обе строки колонки или одну».
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', 'utils')))

import e2_test as E2                                  # noqa: E402
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

S = E2.SYMS
ERASE = S['func_ed_erase_old']
GLYPH = S['func_render_glyph']
MAIN_LOOP = S['lbl_main_game_loop']
SCRATCH = 0x6A50
TEXTBUF = S['data_text_buffer']
MODE_ADDR = S['data_ram_init_image_08C3'] + 0x0D

s = McpSession(cwd=E2.ROOT)
s.start()


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def regs():
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def wait_pause(limit=20.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.02)
    return False


try:
    s.load_rom(E2.ROM, org=E2.ROM_BASE)
    s.call("debug_set_breakpoint", {"address": MAIN_LOOP})
    s.call("debug_run")
    time.sleep(0.3)
    s.call("debug_press_key", {"key": "SPACE"})
    assert wait_pause()
    mode = read(MODE_ADDR, 1)[0]
    s.call("debug_set_breakpoint", {"address": ERASE})
    hits = 0
    s.call("debug_set_breakpoint", {"address": GLYPH})
    inside = False
    calls = []
    while hits < 6:
        s.call("debug_run")
        if not wait_pause():
            print("стоп: нет событий")
            break
        pc = regs()['pc']
        if pc == MAIN_LOOP:
            continue
        if pc == ERASE:
            sc = read(SCRATCH, 18)
            inside = True
            calls = []
            sp = regs()['sp']
            ret = read(sp, 2)[0] | (read(sp + 1, 1)[0] << 8)
            print(f"\nerase #{hits}: slot={sc[0]} disp=({sc[3]},{sc[4]}) ho={sc[16]} "
                  f"vo={sc[5]} new=({sc[6]},{sc[7]}) h/v={sc[17]},{sc[8]} ret=0x{ret:04X}")
            try:
                s.call("debug_set_breakpoint", {"address": ret})
            except Exception:
                pass                       # ret уже стоит с прошлого вызова
            continue
        if inside and pc == GLYPH:
            r = regs()
            hl, a = r['hl'], r['a'] & 0xFF
            cell = hl - TEXTBUF
            row, col = divmod(cell, 32)
            base = E2.recv(hl, mode)
            calls.append((a, hl, row, col, [ (base + p * 0x2000) & 0xFFFF for p in range(4)]))
            continue
        if inside and pc != GLYPH:
            inside = False
            hits += 1
            if not calls:
                print("   (ни одного func_render_glyph — erase ничего не восстановил)")
            for a, hl, row, col, addrs in calls:
                print(f"   glyph код 0x{a:02X} клетка (row={row},col={col}) HL=0x{hl:04X} "
                      f"плоскости {[hex(x) for x in addrs]}")
                vals = [bytes_of(s.call("debug_get_vram_bytes", {"address": ad, "length": 8}))
                        for ad in addrs]
                print("     сейчас:", [' '.join(f'{b:02X}' for b in v) for v in vals])
    print("\nпроб завершён")
finally:
    s.close()
