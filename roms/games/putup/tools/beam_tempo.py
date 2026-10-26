#!/usr/bin/env python3
"""beam_tempo.py — ТЕМП игрового цикла vs позиция героя (проверка гипотезы
«герой внизу => проходы цикла переползают за границу VBlank»).

Гипотеза: все растер-гарды (герой render+repaint, ряд-атомарный огонь Этапа 1)
ждут прохода луча ВНУТРИ прохода главного цикла (между EI;HLT). Когда цель
гарда в НИЖНИХ рядах поля, ожидание тянет проход за 312-ю линию кадра ->
следующее VBlank-прерывание приходит при IE=0 и теряется -> HLT просыпается
только на следующем: период прохода = 2 кадра вместо 1 => логика (шаг героя
раз в 6 sub-кадров) идёт вдвое медленнее. Вверху гарды не ждут -> период 1.

Метод (одинарные trap-замеры; BP-потоки морозят луч — см. BLINK.MD):
  BP одна на lbl_main_game_loop (сразу после EI;HLT). На каждом стопе читаем
  var_frame_counter (INR в ISR каждый VBlank) => delta между соседними стопами
  = длительность прохода в hw-кадрах. Героя принудительно держим в двух
  band'ах (ВВЕРХ: row 3, ВНИЗ: row 22) через warp каждые 5 итераций; удерживаем RIGHT,
  герой бежит и остаётся в band (гравитация кидает вниз, но warp корректирует).

Запуск:
    python3 tools/beam_tempo.py [ИТЕРАЦИЙ_НА_BAND]   (default 40)
    PUTUP_TOP=3 PUTUP_BOT=22  — ряды band'ов
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, '..'))           # roms/games/putup
ROOT = os.path.abspath(os.path.join(PROJECT, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
TOP = int(os.environ.get('PUTUP_TOP', '3'))
BOT = int(os.environ.get('PUTUP_BOT', '22'))
ROM = os.environ.get('PUTUP_ROM') or os.path.join(PROJECT, 'putup_new.rom')
S = json.load(open(os.environ.get('PUTUP_LAYOUT') or
                   os.path.join(PROJECT, 'tools', 'layout.json')))
S = S.get('symbols', S)

ROM_BASE = 0x0100
COLS, ROWS = 32, 24
MAIN = S['lbl_main_game_loop']
ISLAND = S['data_ram_init_image_08C3']
A_FRAMEC = ISLAND + 0x1C          # var_frame_counter (EQU image+1Ch, INR в ISR)
A_PLAYER_RC = ISLAND + 0x3E       # (row, col) цель easing'а
A_ENEMY_RC = ISLAND + 0x20        # (lo=row, hi=col) отображаемый герой
A_SCR909 = ISLAND + 0x46
TB = S['data_text_buffer']
A_SUB = S['var_frame_sub']
A_SCAN = S['var_scan_ptr']


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def word(addr):
    b = read(addr, 2)
    return b[0] | b[1] << 8


def write(addr, data):
    s.call("debug_write_memory", {"address": addr, "data": list(data)})


def regs():
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def wait_pause(limit=25.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.01)
    return False


def warp(hero_row, hero_col):
    write(A_PLAYER_RC, [hero_row, hero_col])
    write(A_ENEMY_RC, [hero_row, hero_col])
    write(S['var_hero_erow'], [hero_row, hero_col])
    write(A_SCR909, [hero_col, hero_row])
    write(S['var_hero_newr'], [hero_row])
    write(S['var_hero_newc'], [hero_col])


def start_game():
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


def sample_band(row_band, label):
    """N trap-стопов на MAIN с героем, удерживаемым в band; возвращает список
    записей {delta, prow, fire_chunk}"""
    out = []
    prev = None
    col = read(A_PLAYER_RC, 2)[1]
    s.call("debug_press_key", {"key": "RIGHT"})
    try:
        for it in range(N):
            if it % 5 == 0:
                warp(row_band, read(A_PLAYER_RC, 2)[1])
            s.call("debug_run")
            if not wait_pause():
                print("!! нет стопа за 25 c"); break
            fc = read(A_FRAMEC, 1)[0]
            prow = read(A_PLAYER_RC, 2)[0]
            scan = word(A_SCAN)
            fire_row = None
            if TB <= scan < TB + COLS * ROWS:
                r = (scan - TB) // COLS
                chunk = read(TB + r * COLS, COLS)
                fire_row = r if any(c in (0x75, 0xFE) for c in chunk) else None
            if prev is not None and it >= 3:    # прогрем после первого warp
                d = (fc - prev) & 0xFF          # счётчик байтовый, wrap-ok
                out.append({'delta': d, 'prow': prow, 'fire_chunk': fire_row})
            prev = fc
    finally:
        s.call("debug_release_key", {"key": "RIGHT"})
    return out


def report(samples):
    ds = [x['delta'] for x in samples]
    if not ds:
        return "нет данных"
    med = sorted(ds)[len(ds) // 2]
    over2 = sum(1 for d in ds if d >= 2)
    fc_ov = sum(1 for x in samples if x['delta'] >= 2 and x['fire_chunk'] is not None)
    rows_ov = sorted({x['prow'] for x in samples if x['delta'] >= 2})
    return (f"n={len(ds)} медиана={med} период>=2: {over2} "
            f"({100.0 * over2 / len(ds):.0f}%), из них на fire-чанк кадре: {fc_ov}; "
            f"prow при period>=2: {rows_ov[:8]}")


def main():
    try:
        s.start()
        s.load_rom(ROM, org=ROM_BASE)
        s.call("debug_set_breakpoint", {"address": MAIN})
        wait_pause(5.0)
        if not start_game():
            print("!! игра не стартовала"); return 2
        top = sample_band(TOP, 'top')
        bot = sample_band(BOT, 'bot')
        print(f"ВВЕРХ (row {TOP}):  {report(top)}")
        print(f"ВНИЗ  (row {BOT}): {report(bot)}")
        d = os.path.join(PROJECT, '.scratch', 'beam_tempo.json')
        json.dump({'top': top, 'bot': bot}, open(d, 'w'))
        print("сырые данные:", d)
    finally:
        s.close()
    return 0


if __name__ == '__main__':
    s = McpSession(cwd=ROOT)
    sys.exit(main())
