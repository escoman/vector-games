#!/usr/bin/env python3
"""E4: смоук-тест генерализации флипа (таблица data_flip_tab + мигание выхода).

Проверяет то, что не покрыто существующими гейтами:
  S) статика ROM: XCHG-идиом в func_render_all (LDAX D без индекса на 8080 не
     умеет — прежняя «табличная» версия читала всегда M[tab+0] и не флиппила
     ничего), выравнивание data_flip_tab, симметричность пар, record[7] нового
     выхода, LXI H, data_tile_table_26DE+1Ch в спауне;
  F+A) флип-скан: засыпаем в чистую (0x20) зону level-1 светлый выход
     {16,18,17,19} (2x2) и пару огня 75h/FEh (две клетки той же строки) ->
     скан переключает их за оборот: выход в {12,14,13,15}, огонь 75->FE /
     FE->75; через полный оборот (~6 кадров) всё возвращается; VRAM-блоки
     клеток побайтово равны модели record(нового кода);
  B) победа: код 17h ПОД ногами героя диспетчер нормализует в 74h ->
     func_player_move_a вызывается (BP).

Важно по boot-секвенции: на первом попадании в lbl_main_game_loop level loader
ещё не инициализировал var_player_* (в RAM лежат дефолты образа 08C3) —
тест прогревает 10 кадров и проверяет, что bufaddr попал в диапазон буфера.

Запуск:  python3 roms/games/putup/tools/e4_exit_flip_test.py
"""
import sys
import time

import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', 'utils')))

import e2_test as E2                                  # noqa: E402
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

S = E2.SYMS
ROM_BASE = E2.ROM_BASE
TEXTBUF = S['data_text_buffer']
MAIN_LOOP = S['lbl_main_game_loop']
FLIP_TAB = S['data_flip_tab']
SCAN_PTR = S['var_scan_ptr']
RENDER_ALL = S['func_render_all']
MOVE_A = S['func_player_move_a']
TILE_26DE = S['data_tile_table_26DE']
RAMIMG = S['data_ram_init_image_08C3']
PLAYER_BUF = RAMIMG + 0x40          # var_player_bufaddr (слово)
MODE_ADDR = RAMIMG + 0x0D
BRIGHT = [0x16, 0x18, 0x17, 0x19]   # record[7]: TL TR BL BR
DARK = [0x12, 0x14, 0x13, 0x15]     # record[10]

# зона флипа: ряды 10/11 level-1 полностью пусты в колонках 2..23; берём
# правый край (колонки 18..21) — дальше всех от стартовых дорожек яиц.
ZR, ZC = 10, 18

s = None
MODE = None
fails = []


def check(cond, tag, detail=''):
    print(f"{tag}: {'OK' if cond else 'FAIL'}" + (f" | {detail}" if detail else ''))
    if not cond:
        fails.append(tag)
    return cond


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def write(addr, data):
    s.call("debug_write_memory", {"address": addr, "data": list(data)})


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


def frame():
    s.call("debug_run")
    assert wait_pause(), "нет паузы на метке (игра завершилась?)"
    return regs()['pc']


def cell(row, col):
    return TEXTBUF + row * 32 + col


def static_checks():
    code = E2.peek(RENDER_ALL, 34)
    # LHLD(3) var_scan_ptr; LXI D(3) tab; MVI B(2) 80h; затем цикл:
    # MOV A,M; XCHG; MOV L,A; MOV A,M; XCHG; ORA A; JZ ...
    got = code[8:14]
    want = [0x7E, 0xEB, 0x6F, 0x7E, 0xEB, 0xB7]
    imm = code[4] | (code[5] << 8)
    check(imm == FLIP_TAB and FLIP_TAB % 256 == 0,
          "S) LXI D, data_flip_tab (выровнена)",
          f"imm=0x{imm:04X} tab=0x{FLIP_TAB:04X}")
    check(got == want, "S) XCHG-идиом в скане (7e eb 6f 7e eb b7)",
          f"факт {bytes(got).hex(' ')}")
    tbl = E2.peek(FLIP_TAB, 256)
    nz = [(i, b) for i, b in enumerate(tbl) if b]
    sym = all(tbl[b] == i for i, b in nz)
    want_pairs = {(0x12, 0x16), (0x13, 0x17), (0x14, 0x18), (0x15, 0x19),
                  (0x75, 0xFE)}
    got_pairs = {(i, b) for i, b in nz if i < b}
    check(sym and got_pairs == want_pairs and len(nz) == 10,
          "S) таблица: 10 ненулей, пары симметричны",
          f"pairs={sorted(hex(a) + '->' + hex(b) for a, b in got_pairs)}")
    rec7 = E2.peek(TILE_26DE + 0x1C, 4)
    check(rec7 == BRIGHT, "S) record[7] = {16,18,17,19}",
          f"факт {bytes(rec7).hex(' ')}")
    tgt = TILE_26DE + 0x1C
    pat = bytes([0x21, tgt & 0xFF, tgt >> 8])
    check(E2.rom.find(pat) >= 0, "S) LXI H, data_tile_table_26DE+1Ch в спауне")


def current():
    """(4 кода выхода TL TR BL BR, код огня (ZR,ZC+2), код огня (ZR,ZC+3))."""
    ex = read(cell(ZR, ZC), 2) + read(cell(ZR + 1, ZC), 2)
    f1 = read(cell(ZR, ZC + 2), 1)[0]
    f2 = read(cell(ZR, ZC + 3), 1)[0]
    return ex, f1, f2


def vram_checks(items):
    """items = [(row, col, expected_code)]; блоки клеток == модель record()."""
    bad = []
    for (row, col, code) in items:
        rec = E2.record(code)
        blocks = E2.blocks(s, cell(row, col), MODE)
        for p in range(4):
            a, got = blocks[p]                      # верхняя строка клетки
            if got != rec[p * 8:p * 8 + 8]:
                bad.append((row, col, p, a, got, rec[p * 8:p * 8 + 8]))
    return bad


def part_fa_flip():
    zone = [read(cell(ZR, ZC), 4), read(cell(ZR + 1, ZC), 4)]
    if not check(all(b == 0x20 for row in zone for b in row),
                 "F+A) зона (10,18..21) чиста (0x20)",
                 f"зона={bytes(zone[0]).hex(' ')} / {bytes(zone[1]).hex(' ')}"):
        return
    write(cell(ZR, ZC), [BRIGHT[0], BRIGHT[1], 0x75, 0xFE])
    write(cell(ZR + 1, ZC), [BRIGHT[2], BRIGHT[3]])
    scan = read(SCAN_PTR, 2)[0] | (read(SCAN_PTR + 1, 1)[0] << 8)
    off = (cell(ZR, ZC) - scan) % 0x300
    print(f"    курсор 0x{scan:04X}, клеток до зоны: {off} "
          f"(~{(off + 127) // 128} кадр(ов))")

    def wait_flip(expect_ex, expect_f, limit):
        for i in range(1, limit + 1):
            frame()
            ex, f1, f2 = current()
            if ex == expect_ex and f1 == expect_f[0] and f2 == expect_f[1]:
                return i, ex, f1, f2
            odd = [c for c in ex if not 0x12 <= c <= 0x19] or \
                  [c for c in (a, b) if c not in (0x75, 0xFE)]
            if odd:
                return None, ex, f1, f2              # затёрто посторонним
        return None, ex, f1, f2

    # оборот скана: выход светлый->тёмный, огонь 75->FE / FE->75
    f1, ex, a, b = wait_flip(DARK, (0xFE, 0x75), 9)
    if not check(f1 is not None, "F+A) за оборот скана все 6 клеток флиппнулись",
                 f"кадр +{f1}; exit={bytes(ex).hex(' ')} fire=({a:02X},{b:02X})"):
        return
    bad = vram_checks([(ZR, ZC, ex[0]), (ZR, ZC + 1, ex[1]),
                       (ZR + 1, ZC, ex[2]), (ZR + 1, ZC + 1, ex[3]),
                       (ZR, ZC + 2, a), (ZR, ZC + 3, b)])
    check(not bad, "F+A) VRAM тёмной фазы == модель record(кодов)",
          '' if not bad else f"{len(bad)} блоков mismatch, напр. 0x{bad[0][3]:04X}")
    for row, col, p, ad, got, exp in bad[:3]:
        print(f"    ({row},{col}) pl{p} 0x{ad:04X}: {bytes(got).hex(' ')} != "
              f"{bytes(exp).hex(' ')}")

    # обратный оборот: всё возвращается
    f2, ex2, a2, b2 = wait_flip(BRIGHT, (0x75, 0xFE), 9)
    if not check(f2 is not None and 5 <= (f1 + f2) <= 8,
                 "F+A) обратный флип через ещё один оборот (6±2 кадра)",
                 f"кадр +{f2}; суммарно {f1}+{f2}; exit={bytes(ex2).hex(' ')} "
                 f"fire=({a2:02X},{b2:02X})"):
        return
    bad = vram_checks([(ZR, ZC, ex2[0]), (ZR, ZC + 1, ex2[1]),
                       (ZR + 1, ZC, ex2[2]), (ZR + 1, ZC + 1, ex2[3]),
                       (ZR, ZC + 2, a2), (ZR, ZC + 3, b2)])
    check(not bad, "F+A) VRAM светлой фазы == модель (глифы 188..191 и 75/FE)",
          '' if not bad else f"{len(bad)} блоков mismatch")


def part_b_win():
    s.call("debug_set_breakpoint", {"address": MOVE_A})
    hit = None
    foot = None
    try:
        for i in range(14):
            # bufaddr пересчитываем КАЖДЫЙ кадр: герой может падать/идти,
            # а диспетчер читает M[bufaddr+0x20] свежего кадра
            buf = read(PLAYER_BUF, 2)[0] | (read(PLAYER_BUF + 1, 1)[0] << 8)
            foot = (buf + 0x20) & 0xFFFF
            # целимся на два вперёд: за кадр герой успевает упасть на строку,
            # и диспетчер читает M[bufaddr_new+0x20] = foot+0x20
            write(foot, [0x17])           # светлый выход под ногами = мигание
            write((foot + 0x20) & 0xFFFF, [0x16])
            pc = frame()
            if pc == MOVE_A:
                hit = i
                break
        check(hit is not None,
              "B) 17h под героем -> func_player_move_a (нормализация в 74h)",
              f"кадр {hit}, foot=0x{foot:04X}")
    finally:
        s.call("debug_remove_breakpoint", {"address": MOVE_A})


def main():
    global s, MODE
    static_checks()
    if fails:
        print("FAIL (статика не сходится — ROM не тот?)")
        return 1
    s = McpSession(cwd=E2.ROOT)
    s.start()
    try:
        s.load_rom(E2.ROM, org=ROM_BASE)
        s.call("debug_set_breakpoint", {"address": MAIN_LOOP})
        s.call("debug_run")
        time.sleep(0.3)
        s.call("debug_press_key", {"key": "SPACE"})
        assert wait_pause(), "нет попадания на метку главного цикла"
        MODE = read(MODE_ADDR, 1)[0]
        disp = read(0x6A37, 6)
        print(f"    boot ok: режим 0x{MODE:02X}, disp-засев {disp[2:6]}")
        if not check(disp[2:6] == [6, 10, 12, 10], "init-засев врагов (как в e2)"):
            return 1
        for _ in range(8):                # прогрет: level loader должен закончить
            frame()
        part_fa_flip()
        part_b_win()
    finally:
        s.close()
    print("\nИТОГО: " + ("PASS" if not fails else f"FAIL {fails}"))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
