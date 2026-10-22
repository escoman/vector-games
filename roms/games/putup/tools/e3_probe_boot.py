#!/usr/bin/env python3
"""Мини-проба: что делает ROM после load/SPACE (отладка e3_cls_test).
PC сэмплируется, чтобы отличить «игнор клавиши» от «залип в цикле»."""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.abspath(os.path.join(PROJECT, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

ROM = os.environ.get('PUTUP_ROM') or os.path.join(PROJECT, 'putup_new.rom')
LAYOUT = os.environ.get('PUTUP_LAYOUT') or os.path.join(
    PROJECT, 'tools', 'layout.json')
SYMS = json.load(open(LAYOUT))
SYMS = SYMS.get('symbols', SYMS)
MAIN_LOOP = SYMS['lbl_main_game_loop']
s = McpSession(cwd=ROOT)


def owner(addr):
    best = None
    for n, a in SYMS.items():
        if isinstance(a, int) and a <= addr and (best is None or a > best[1]):
            best = (n, a)
    return best[0] if best else '?'


s.start()
try:
    print("ROM:", ROM, os.path.getsize(ROM), "байт")
    s.load_rom(ROM, org=0x0100)
    s.call("debug_set_breakpoint", {"address": MAIN_LOOP})
    s.call("debug_run")
    time.sleep(0.5)
    print("до клавиши: running =", s.call("debug_is_running").get("running"),
          " PC =", s.call("debug_get_registers").get('PC'))
    s.call("debug_press_key", {"key": "SPACE"})
    seen = []
    t0 = time.time()
    while time.time() - t0 < 20:
        if not s.call("debug_is_running").get("running"):
            r = s.call("debug_get_registers")
            print(f"ПАУЗА через {time.time()-t0:.1f} с: PC={r.get('PC')} "
                  f"({owner(to_addr(r['PC']))})")
            break
        r = s.call("debug_get_registers")
        seen.append(to_addr(r['PC']))
        time.sleep(0.7)
    else:
        print("за 20 с не остановилось; сэмплы PC:",
              " ".join(f"{x:04X}" for x in seen))
        uniq = set(seen[-8:])
        print("последние уникальные:", [f"{x:04X} {owner(x)}" for x in sorted(uniq)])
        d = s.call("debug_disassemble", {"address": hex(seen[-1]), "count": 8})
        print("дизасм вокруг последнего PC:", d.get('instructions') or d)
    print("beam:", {k: s.call("debug_get_beam_state")[k]
                    for k in ('frame', 'raster_line', 'visible')})
finally:
    s.close()
