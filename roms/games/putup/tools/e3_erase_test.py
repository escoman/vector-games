#!/usr/bin/env python3
"""
Шаг E3-6b: ЧАСТИЧНЫЙ erase фона врага.

Инвариант, который проверяет тест (для каждого вызова func_ed_erase_old):
  * множество восстанавливаемых клеток задаёт ГЕОМЕТРИЯ, а не «весь footprint наугад»:
      old-окно = [ob, ob+ow) x rows, где ob = dc - (ho==2), ow = 3 при ho != 0 иначе 2;
      rows = {dr, dr+1}, а при vo != 0 ещё dr+1, dr+2 (спил 4 px вниз);
      при vo==0, newv==0, dr==newr (горизонтальный easing) восстанавливаются только
      колонки old-окна ВНЕ гарантированно перерисованных [newc, newc+1];
      иначе — все колонки old-окна;
  * каждая клетка из множества после erase побайтово равна ФОНУ из текстового буфера
     (модель func_render_glyph по коду клетки);
  * каждая клетка old-окна, НЕ входящая в множество, побайтово НЕ изменилась.

Отдельно считается экономия: сколько колонок реально восстановлено против «полного»
варианта (для midpoint-кадра должно быть 0).

Запуск:  python3 roms/games/putup/tools/e3_erase_test.py [КАДРОВ]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', 'utils')))

import e2_test as E2                                  # noqa: E402
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 60
S = E2.SYMS
ROM_BASE = E2.ROM_BASE
TEXTBUF = S['data_text_buffer']
MAIN_LOOP = S['lbl_main_game_loop']
ERASE = S['func_ed_erase_old']
SCRATCH = 0x6A50            # var_ed_slot .. var_ed_erase_rc (+ho при 0x6A60)
MODE_ADDR = S['data_ram_init_image_08C3'] + 0x0D

s = None


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def regs():
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def ret_addr():
    sp = regs()['sp']
    return read(sp, 2)[0] | (read(sp + 1, 1)[0] << 8)


def wait_pause(limit=20.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.02)
    return False


def cell_vram(row, col, mode):
    """Адреса 4 плоскостей клетки (row,col) — та же арифметика, что у render_glyph."""
    base = E2.recv(TEXTBUF + row * 32 + col, mode)
    return [(base + p * 0x2000) & 0xFFFF for p in range(4)]


def snap_cell(row, col, mode):
    out = []
    for a in cell_vram(row, col, mode):
        out.append((a, list(bytes_of(s.call("debug_get_vram_bytes",
                                            {"address": a, "length": 8})))))
    return out


def model_row(row, col):
    """Что обязан содержать фон КЛЕТКИ (row,col): запись глифа по коду буфера."""
    code = read(TEXTBUF + row * 32 + col, 1)[0]
    rec = E2.record(code)
    return code, [rec[p * 8:p * 8 + 8] for p in range(4)]


def expected_set(sc):
    """Клетки, которые erase обязан восстановить, и клетки, которые трогать нельзя.
    Индексы scratch: 0=slot 3=dr 4=dc 5=vo 6=newr 7=newc 8=newv 16=ho 17=newh."""
    dr, dc, vo = sc[3], sc[4], sc[5]
    newr, newc, newv = sc[6], sc[7], sc[8]
    ho = sc[16]
    if dr >= 0x18:
        return [], []                    # guard: вне поля рендерер не рисовал
    ob = dc - 1 if ho == 2 else dc
    ow = 3 if ho else 2
    cols = [ob + i for i in range(ow)]
    rows = [dr, dr + 1] + ([dr + 2] if vo else [])
    fast = (vo == 0 and newv == 0 and dr == newr)
    covered = {newc & 0xFF, (newc + 1) & 0xFF}
    restore = [(r, c) for c in cols for r in rows
               if not fast or c not in covered]
    keep = [(r, c) for c in cols for r in rows if (r, c) not in restore]
    return restore, keep


def main():
    global s
    stats = {'erase_calls': 0, 'frames': 0, 'bad_restore': 0, 'bad_keep': 0,
             'cols_restored': {}, 'full_path': 0, 'partial_zero': 0}
    s = McpSession(cwd=E2.ROOT)
    s.start()
    try:
        s.load_rom(E2.ROM, org=ROM_BASE)
        s.call("debug_set_breakpoint", {"address": MAIN_LOOP})
        s.call("debug_run")
        time.sleep(0.3)
        s.call("debug_press_key", {"key": "SPACE"})
        assert wait_pause(), "нет попадания на метку главного цикла"
        mode = read(MODE_ADDR, 1)[0]
        s.call("debug_set_breakpoint", {"address": ERASE})
        deadline = time.time() + 240
        while stats['frames'] < FRAMES and time.time() < deadline:
            s.call("debug_run")
            if not wait_pause():
                print("нет событий 20 с — игра, похоже, закончилась")
                break
            pc = regs()['pc']
            if pc == MAIN_LOOP:
                stats['frames'] += 1
                continue
            if pc != ERASE:
                continue                   # иная остановка (не наш bp) — просто жмём дальше
            sc = read(SCRATCH, 18)
            restore, keep = expected_set(sc)
            pre_keep = {(r, c): snap_cell(r, c, mode) for (r, c) in keep}
            # снимок И восстанавливаемых клеток: нужен для диагностики « ROM вообще
            # не писал по этому адресу» vs «писал не то»
            pre_restore = {}
            for (r, c) in restore:
                for rr in (0, 1):
                    for p, a in enumerate(cell_vram(r + rr, c, mode)):
                        pre_restore[(r + rr, c, p)] = list(bytes_of(s.call(
                            "debug_get_vram_bytes", {"address": a, "length": 8})))
            ret = ret_addr()
            s.call("debug_set_breakpoint", {"address": ret})
            s.call("debug_run")
            assert wait_pause() and regs()['pc'] == ret, "не на RET func_ed_erase_old"
            s.call("debug_remove_breakpoint", {"address": ret})
            stats['erase_calls'] += 1
            stats['cols_restored'][len(restore)] = \
                stats['cols_restored'].get(len(restore), 0) + 1
            if not restore:
                stats['partial_zero'] += 1
            if sc[5] or sc[8]:                       # vo != 0 или newv != 0 -> полный
                stats['full_path'] += 1
            bad = []
            for (r, c) in restore:
                code, planes = model_row(r, c)
                addrs = cell_vram(r, c, mode)
                for p in range(4):
                    got = list(bytes_of(s.call("debug_get_vram_bytes",
                                               {"address": addrs[p], "length": 8})))
                    if got != planes[p]:
                        bad.append((r, c, p, addrs[p], code, planes[p], got,
                                    pre_restore.get((r, c, p))))
            if bad:
                stats['bad_restore'] += 1
                print(f"  !! erase не восстановил фон: slot={sc[0]} disp=({sc[3]},{sc[4]}) "
                      f"ho={sc[16]} vo={sc[5]} -> new=({sc[6]},{sc[7]}) hv={sc[17]},{sc[8]}")
                for r, c, p, a, code, expb, got, preb in bad[:4]:
                    print(f"     ({r},{c}) pl{p} 0x{a:04X} код 0x{code:02X}: ждём "
                          f"{' '.join(f'{b:02X}' for b in expb)} = "
                          f"{' '.join(f'{b:02X}' for b in got)} (до erase было "
                          f"{' '.join(f'{b:02X}' for b in (preb or []))})")
            badk = []
            for (r, c), pre in pre_keep.items():
                post = snap_cell(r, c, mode)
                if post != pre:
                    badk.append((r, c, pre, post))
            if badk:
                stats['bad_keep'] += 1
                print(f"  !! erase тронул не-восстанавливаемую клетку: slot={sc[0]} "
                      f"disp=({sc[3]},{sc[4]}) ho={sc[16]} vo={sc[5]} "
                      f"new=({sc[6]},{sc[7]})")
                for r, c, pre, post in badk[:3]:
                    print(f"     ({r},{c}) было {pre[0][1]} -> стало {post[0][1]}")
        print(f"\nвызовов erase: {stats['erase_calls']} (полный путь "
              f"{stats['full_path']}, с нулём колонок {stats['partial_zero']})")
        print("распределение восстановленных клеток:",
              dict(sorted(stats['cols_restored'].items())))
        print(f"сбоев фон-restore: {stats['bad_restore']}, сбоев «не трогать»: "
              f"{stats['bad_keep']}")
        ok = (stats['erase_calls'] >= 6 and stats['partial_zero'] >= 1
              and not stats['bad_restore'] and not stats['bad_keep'])
        print(f"\nRESULT: {'PASS' if ok else 'FAIL/NEEDS-COVERAGE'}")
        return 0 if ok else 1
    finally:
        s.close()


if __name__ == '__main__':
    sys.exit(main())
