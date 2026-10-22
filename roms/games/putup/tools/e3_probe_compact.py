#!/usr/bin/env python3
"""Проб: бывают ли КОМПАКТНЫЕ глифы (тег бит0=1) в 4 кодах цели при сборке
композита E2 (func_enemy_build_cache)?

Зачем: func_ed_resolve_glyph снимает тег (ANI 0FEh), а билдер идёт по 32
последовательным байтам. Для compact-записи после 8 байт маски идут байты СОСЕДНЕЙ
записи => в композит попадает мусор плоскостей 1..3. Если такой код достижим на
натуральной игре — это живой баг ROM, если нет — latent (guard всё равно нужен).

Запуск: python3 roms/games/putup/tools/e3_probe_compact.py [КАДРОВ]
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.abspath(os.path.join(PROJECT, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))
from analyze.mcp_session import McpSession, to_addr  # noqa: E402

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 120
ROM = os.path.join(PROJECT, 'putup_new.rom')
SYMS = json.load(open(os.path.join(PROJECT, 'tools', 'layout.json')))
SYMS = SYMS.get('symbols', SYMS)
BUILD = SYMS['func_enemy_build_cache']
MAIN_LOOP = SYMS['lbl_main_game_loop']
GCODES = 0x6A5A                 # var_ed_gcodes (SCRATCH+10)
SCRATCH = 0x6A50
PTR_TABLE = SYMS['data_glyph_ptr_table']
ISLAND = SYMS['data_ram_init_image_08C3']
STATE1 = ISLAND + 0x57
STATE2 = ISLAND + 0x58


def regs(s):
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def wait_pause(s, limit=30.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.02)
    return False


def read(s, addr, n):
    from analyze.mcp_session import bytes_of
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def main():
    s = McpSession(cwd=ROOT)
    s.start()
    tags = {}
    try:
        s.load_rom(ROM, org=0x100)
        # теги компактности из живой RAM (таблица указателей в ROM, org 0x100)
        pt = read(s, PTR_TABLE, 512)
        for c in range(256):
            tags[c] = pt[2 * c] & 1
        s.call("debug_set_breakpoint", {"address": MAIN_LOOP})
        s.call("debug_run")
        time.sleep(0.3)
        s.call("debug_press_key", {"key": "SPACE"})
        assert wait_pause(s), "игра не стартовала"
        s.call("debug_set_breakpoint", {"address": BUILD})
        frames = calls = compact_calls = 0
        seen = {}
        while frames < FRAMES:
            s.call("debug_run")
            if not wait_pause(s):
                print("нет событий — игра, похоже, закончилась")
                break
            pc = regs(s)['pc']
            if pc == MAIN_LOOP:
                frames += 1
                continue
            if pc == BUILD:
                calls += 1
                g = read(s, GCODES, 4)
                slot = read(s, SCRATCH, 1)[0]
                bad = [c for c in g if tags[c]]
                for c in g:
                    seen.setdefault(c, 0)
                    seen[c] += 1
                if bad:
                    compact_calls += 1
                    print(f"  compact в compozite: slot={slot} codes={g} "
                          f"state=({read(s, STATE1, 1)[0]},{read(s, STATE2, 1)[0]})")
        print(f"кадров={frames} вызовов build_cache={calls} с compact-кодом="
              f"{compact_calls}")
        print("уникальные коды:", sorted(seen))
        print("compact среди них:", sorted(c for c in seen if tags[c]))
    finally:
        s.close()


if __name__ == '__main__':
    main()
