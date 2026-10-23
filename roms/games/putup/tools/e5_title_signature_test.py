#!/usr/bin/env python3
"""E5: смоук-тест подписей заставки (сдвиг на 4 px вверх от сетки).

Покрывает фичу "REMASTERED BY SARMIN ALEXEY 2026" и раздельные сдвиги:
  S) статика ROM: строка в образе; паттерны LDA/ADI 4/STA (окна накапливаются:
     +4 и ещё +4; третье — возврат подписи) и LDA/SUI 8/STA, LDA/SUI 4/STA
     (окно подписи −4) var_screen_mode; LXI H на ряды 25 (+0320h) и 26 (+0340h);
  1) буфер: 32 клетки ряда 26 == коды строки; ряд 24 пуст (0FFh @idx 63
     терминует первую печать кредитсов);
  2) var_screen_mode восстановлен (0xE0) — окна сдвига короткие;
  3) VRAM plane0 == record(символ): ряд 23 при mode+4 (строка 1, +4 px вверх),
     ряд 25 при mode+8 («Центр…», +8 px), ряд 26 (подпись) при mode−4 (−4 px,
     y=212..219); для всех рядов проверяются непустые клетки;
  4) регресс окна: блок подписи при natural mode != record (печать обязана
     идти в окне mode−4; ловит no-op/переворот), и при mode−4 == record
     (уже проверено в 3) — нижняя полоса y=216..223 НЕ обязана быть пустой:
     блоки ряда 25 (mode+8) и 26 (mode−4) упакованы вплотную, нижний байт
     масок credits залезает в неё штатно (на экране не виден: record[0]=0).

Заставка рисуется синхронно в func_main_init до lbl_title_key_poll; тест
просто гоняет ROM ~2 сек и встаёт на паузу (BP не нужен — метку главного
цикла заставка не достигает).

Запуск:  python3 roms/games/putup/tools/e5_title_signature_test.py
"""
import sys
import time

import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', 'utils')))

import e2_test as E2                                  # noqa: E402
from analyze.mcp_session import McpSession, bytes_of   # noqa: E402

S = E2.SYMS
ROM_BASE = E2.ROM_BASE
TEXTBUF = S['data_text_buffer']
MODE_ADDR = S['data_ram_init_image_08C3'] + 0x0D      # var_screen_mode
SIG = "REMASTERED BY SARMIN ALEXEY 2026"
SIG_ROW = 26                       # ряд подписи (data_text_buffer+0340h)
# ряд -> сдвиг вверх в окне печати (px над сеткой; 0 = натурально)
LAYOUT = {23: 4, 24: 4, 25: 8, 26: -4}

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


def wait_pause(limit=10.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.02)
    return False


def cell(row, col):
    return TEXTBUF + row * 32 + col


def static_checks():
    pat = SIG.encode('ascii') + b'\xff'
    i = E2.rom.find(pat)
    check(i >= 0, "S) строка 'REMASTERED ...' + 0FFh в ROM",
          f"@0x{0x100 + i:04X}" if i >= 0 else "не найдена")
    ml, mh = MODE_ADDR & 0xFF, MODE_ADDR >> 8
    up4 = bytes([0x3A, ml, mh, 0xC6, 0x04, 0x32, ml, mh])     # LDA/ADI 4/STA
    dn8 = bytes([0x3A, ml, mh, 0xD6, 0x08, 0x32, ml, mh])     # LDA/SUI 8/STA
    dn4 = bytes([0x3A, ml, mh, 0xD6, 0x04, 0x32, ml, mh])     # LDA/SUI 4/STA
    check(E2.rom.find(up4) >= 0, "S) окна строк 1/2: LDA mode; ADI 4; STA mode")
    check(E2.rom.count(up4) == 3, "S) ADI 4 ровно 3 окна (строка 2 +8 и возврат "
          "подписи; накопленно 4+4, возвраты 8 и 4)",
          f"встречается {E2.rom.count(up4)} раз(а)")
    check(E2.rom.find(dn8) >= 0, "S) возврат credits: LDA mode; SUI 8; STA mode")
    check(E2.rom.find(dn4) >= 0, "S) окно подписи: LDA mode; SUI 4; STA mode")
    lxi25 = bytes([0x21, (TEXTBUF + 0x320) & 0xFF, (TEXTBUF + 0x320) >> 8])
    check(E2.rom.find(lxi25) >= 0, "S) LXI H, data_text_buffer+0320h (ряд 25)")
    lxi24 = bytes([0x21, (TEXTBUF + 0x340) & 0xFF, (TEXTBUF + 0x340) >> 8])
    check(E2.rom.find(lxi24) >= 0, "S) LXI H, data_text_buffer+0340h (ряд 26)")


def plane0(row, col, mode):
    """(адрес, 8 байт plane0 приёмника клетки при заданном режиме)."""
    a = E2.recv(cell(row, col), mode)
    return a, read(a, 8)


def part_buffer():
    got = read(cell(SIG_ROW, 0), 32)
    want = [ord(ch) for ch in SIG]
    check(got == want, "1) буфер: ряд 26 == 32 кода подписи",
          f"факт {bytes(got).hex(' ')}")
    row24 = read(cell(24, 0), 32)
    check(set(row24) == {0x20}, "1) буфер: ряд 24 пуст (0FFh @idx 63 терминует)",
          f"факт {bytes(row24).hex(' ')}")
    MODE_now = read(MODE_ADDR, 1)[0]
    check(MODE_now == 0xE0, "2) var_screen_mode восстановлен (0E0h)",
          f"факт 0x{MODE_now:02X}")


def part_vram():
    bad = []
    for c, ch in enumerate(SIG):
        if ch == ' ':
            continue                      # space CMP M/RZ не перерисовывает
        a, got = plane0(SIG_ROW, c, MODE + LAYOUT[SIG_ROW])
        rec = E2.record(ord(ch))[:8]
        if got != rec:
            bad.append((c, ch, a, got, rec))
    check(not bad, "3) VRAM: plane0 ряда 26 (подпись) при mode−4 == record",
          f"расхождений: {len(bad)}" + (f", первое {bad[0][:3]}" if bad else ''))
    if bad:
        c, ch, a, got, rec = bad[0]
        print(f"    col {c} '{ch}' @0x{a:04X}: got {bytes(got).hex(' ')} "
              f"want {bytes(rec).hex(' ')}")

    # credits: непустые клетки ряда 23 при mode+4 и ряда 25 при mode+8
    badc = []
    for row in (23, 25):
        codes = read(cell(row, 0), 32)
        for c, code in enumerate(codes):
            if code == 0x20:
                continue
            a, got = plane0(row, c, MODE + LAYOUT[row])
            rec = E2.record(code)[:8]
            if got != rec:
                badc.append((row, c, code, a))
    check(not badc, "3) VRAM: plane0 credits (ряд 23 +4, ряд 25 +8) == record",
          f"расхождений: {len(badc)}"
          + (f", первое row={badc[0][0]} col={badc[0][1]}" if badc else ''))

    # 4) регресс окна подписи: при natural mode блок != record (иначе печать
    # шла бы без сдвига, а −4 даёт видимость только в окне). Полосу «ниже»
    # пустой не проверяем: блоки row25(+8) и row26(−4) упакованы вплотную,
    # нижний байт маски credits — штатный гость в ней (не виден: record[7]=0).
    worst = 0
    mismatch = 0
    for c, ch in enumerate(SIG):
        if ch == ' ':
            continue
        rec = E2.record(ord(ch))[:8]
        a, got = plane0(SIG_ROW, c, MODE)
        if got != rec:
            mismatch += 1
        worst = max(worst, sum(1 for g, r in zip(got, rec) if g != r))
    check(mismatch and worst >= 2, "4) natural mode: блок подписи != record (окно −4 живое)",
          f"клеток с расхождением: {mismatch}, max байт/клетка: {worst}")


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
        s.call("debug_run")
        time.sleep(2.0)                   # заставка рисуется синхронно на init
        s.call("debug_pause")
        assert wait_pause(), "ROM не встал на паузу"
        MODE = read(MODE_ADDR, 1)[0]
        print(f"    boot ok: режим 0x{MODE:02X}")
        part_buffer()
        part_vram()
    finally:
        s.close()
    print("\nИТОГО: " + ("PASS" if not fails else f"FAIL {fails}"))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
