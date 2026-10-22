#!/usr/bin/env python3
"""Шаг E3 (фикс «следы врагов в пустых клетках») — инвариант чистоты VRAM после
загрузки/рестарта уровня.

БАГ (замети пользователь): после смерти/рестарта и на переходе к следующему
уровню в пустых клетках (код 0x20) оставались пиксели врагов.

МЕХАНИКА (проверено по коду, не догадка): func_put_char (0x0800) начинается с
`CMP M / RZ` — если код в текстовом буфере уже равен записываемому, функция
возвращается, НЕ трогая VRAM. Пути входа в уровень (func_level_loader /
loc_19A0 — смерть, следующий уровень, старт из заставки) сначала затирают ВЕСЬ
текстовый буфер пробелами (func_clear_textbuf), и только потом рисуют карту.
Для каждой пустой клетки карты 0x20 == 0x20 -> RZ -> VRAM не перетирается.
Значит пиксели, оставленные в пустой клетке любым рисовальщиком, переживают
рестарт. Карта покрывает только 16x11 тайлов, поэтому нижние строки поля и
траектория яйца не перерисовываются вообще никем.

ФИКС: вызов func_clear_vram (тот же CLS, что на загрузке в func_main_init) на
входе уровня в func_level_loader / loc_19A0, перед func_clear_textbuf.

ПРОВЕРКИ:
  A) ИНВАРИАНТ ЧИСТОТЫ: после рестарта для каждой глиф-клетки поля (24 строки x
     32 колонки) с кодом 0x20 в буфере все 8 байт во всех 4 плоскостях VRAM == 0.
     Идёт на живой игре: враг перед рестартом гарантированно стоит в пустой
     клетке, т.е. его пиксели реально лежат в VRAM до перезагрузки.
  B) ДЕТЕРМИНИЗМ РЕСТАРТА: рестарт с VRAM, целиком заполненной 0xFF (худший
     случай «мусора любого происхождения»), даёт ПОБайТОВО тот же VRAM, что и
     рестарт A. Если хотя бы один байт отличается — из старого кадра что-то
     просочилось в новый уровень.
  C) УРОВЕНЬ НАРИСОВАН: CLS не «съел» отрисовку — число ненулевых байт в VRAM
     после рестарта больше порога и одинаково в A и B.
  D) ЦЕНА: сколько hw-кадров занимает загрузчик с CLS (по beam-состоянию).

Запуск:  python3 roms/games/putup/tools/e3_cls_test.py
         PUTUP_ROM=/path/to/rom.py PUTUP_LAYOUT=/path/to/layout.json — для A/B
         на другой сборке (напр. HEAD-baseline): там ожидается FAIL по A/B.
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

ROM = os.environ.get('PUTUP_ROM') or os.path.join(PROJECT, 'putup_new.rom')
LAYOUT = os.environ.get('PUTUP_LAYOUT') or os.path.join(
    os.path.dirname(os.path.abspath(ROM)), 'tools', 'layout.json')
SYMS = json.load(open(LAYOUT))
SYMS = SYMS.get('symbols', SYMS)
ROM_BASE = 0x0100

TEXTBUF = SYMS['data_text_buffer']
COL_TABLE = SYMS['data_vram_col_table']
MODE_ADDR = SYMS['data_ram_init_image_08C3'] + 0x0D   # var_screen_mode
MAIN_LOOP = SYMS['lbl_main_game_loop']
RESTART = SYMS['loc_19A0']             # точка перезагрузки уровня (без ++level)
DISP_RC = 0x6A37                       # var_enemy_disp_rc: slot0 = 0, slot1 = 2
VRAM_LO, VRAM_HI = 0x8000, 0x10000
ROWS, COLS = 24, 32                    # видимое поле в глиф-клетках
MIN_INK = 2000                         # минимум ненулевых байт в нарисованном кадре

s = None
COLPAGE = []


def regs():
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def wait_pause(limit=60.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.02)
    return False


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def write(addr, data):
    s.call("debug_write_memory", {"address": addr, "data": list(data)})


def beam():
    b = s.call("debug_get_beam_state")
    return int(b.get('frame', 0) or 0), float(b.get('v_cycle_in_frame', 0) or 0)


def recv(row, col, mode):
    """Адрес приёмника 1-го байта глифа — копия арифметики func_render_glyph."""
    hl = (row * 32 + col) & 0xFFFF
    h, l = hl >> 8, hl & 0xFF
    rowbits = ((h & 3) << 6) | ((l & 0xE0) >> 2)
    return (COLPAGE[hl & 0x1F] << 8) | ((mode - rowbits) & 0xFF)


def dump_vram():
    """Весь VRAM 0x8000..0xFFFF одним массивом (чанками по 4 КБ)."""
    out = []
    for a in range(VRAM_LO, VRAM_HI, 0x1000):
        out.extend(bytes_of(s.call("debug_get_vram_bytes",
                                   {"address": a, "length": 0x1000})))
    return bytes(out)


def fill_vram(byte):
    for a in range(VRAM_LO, VRAM_HI, 0x1000):
        write(a, [byte] * 0x1000)


def glyph_block(v, row, col, mode):
    """8 байт глифа (row,col) во всех 4 плоскостях из дампа v."""
    base = recv(row, col, mode) & 0xFFFF
    out = []
    for p in range(4):
        a = (base + p * 0x2000) & 0xFFFF
        if not (VRAM_LO <= a < VRAM_HI):
            return None
        out.append(v[a - VRAM_LO: a - VRAM_LO + 8])
    return out


def restart_to_loop(tag):
    """Форсируем перезагрузку уровня (PC = loc_19A0) и ждём возврата в главный
    цикл. Локальная метка сама делает LXI SP,0100h, поэтому jmp безопасен."""
    f0, _ = beam()
    s.call("debug_set_register", {"name": "PC", "value": RESTART})
    s.call("debug_run")                  # смена PC не возобновляет исполнение
    assert wait_pause(), f"{tag}: загрузчик не вернулся в главный цикл за 60 с"
    pc = regs()['pc']
    f1, _ = beam()
    print(f"  {tag}: рестарт -> PC={pc:04X} (ожидался {MAIN_LOOP:04X}), "
          f"загрузчик занял {f1 - f0} hw-кадров")
    if pc != MAIN_LOOP:
        return None
    return dump_vram()


def check_clean(v, mode, tag, fails):
    """Инвариант A: код 0x20 в буфере => все 4 плоскости клетки = 0."""
    bad = []
    buf = read(TEXTBUF, ROWS * 32 + 32)
    for r in range(ROWS):
        for c in range(COLS):
            for rr in (0, 1):
                for cc in (0, 1):
                    gr, gc = r + rr, c + cc
                    if gr >= ROWS:
                        continue
                    if buf[gr * 32 + gc] != 0x20:
                        continue
                    blk = glyph_block(v, gr, gc, mode)
                    if blk is None:
                        continue
                    if any(any(b) for b in blk):
                        bad.append((gr, gc, tuple(x for x in blk[0] if x)[:4]))
    # считаем по клеткам 2x2, поэтому дубли возможны: уникальные позиции
    uniq = sorted(set(bad))
    ink = sum(1 for x in v if x)
    print(f"  {tag}: ненулевых байт в VRAM {ink}, грязных пустых глифов: "
          f"{len(uniq)}")
    for gr, gc, sample in uniq[:8]:
        print(f"     строка {gr} кол {gc}: плоскость0 = {sample}")
    if uniq:
        fails.append(f"{tag}: {len(uniq)} пустых клеток (0x20) с чужими пикселями")
    return uniq, ink


def main():
    global s
    fails = []
    if 'func_clear_vram' in SYMS:
        print("проверка: рестарт уровня обязан затирать VRAM целиком "
              "(func_clear_vram в загрузчике)")
    else:
        print("ВНИМАНИЕ: в сборке нет func_clear_vram — тест всё равно показателен")
    print(f"ROM: {ROM} ({os.path.getsize(ROM)} байт)")
    s = McpSession(cwd=ROOT)
    s.start()
    try:
        s.load_rom(ROM, org=ROM_BASE)
        s.call("debug_set_breakpoint", {"address": MAIN_LOOP})
        s.call("debug_run")
        time.sleep(0.3)
        s.call("debug_press_key", {"key": "SPACE"})
        assert wait_pause(), "игра не стартовала"
        mode = read(MODE_ADDR, 1)[0]
        COLPAGE.extend(read(COL_TABLE, 32))

        # немного живой игры, чтобы враги реально leaving-пиксели в пустых клетках
        for _ in range(30):
            s.call("debug_run")
            assert wait_pause(), "нет кадров"
        r0 = read(DISP_RC, 1)[0]
        c0 = read(DISP_RC + 1, 1)[0]
        r1 = read(DISP_RC + 2, 1)[0]
        c1 = read(DISP_RC + 3, 1)[0]
        print(f"враги до рестарта: slot0=({r0},{c0}) slot1=({r1},{c1}), "
              f"тек. VRAM заполнен на {sum(1 for x in dump_vram() if x)} байт")

        # ---- A) естественный рестарт ----------------------------------------
        vA = restart_to_loop("A")
        if vA is None:
            fails.append("A: загрузчик не дошёл до главного цикла")
        else:
            uniqA, inkA = check_clean(vA, mode, "A", fails)
            if inkA < MIN_INK:
                fails.append(f"A: уровень не нарисован (ненулевых байт {inkA})")

            # ---- C/B) тот же рестарт поверх полностью грязного экрана -------
            fill_vram(0xFF)
            assert all(b == 0xFF for b in dump_vram()[0x2000:0x2100]), \
                "не удалось загрязнить VRAM (debug_write_memory до него не пишет?)"
            vB = restart_to_loop("B")
            if vB is None:
                fails.append("B: загрузчик не дошёл до главного цикла")
            else:
                uniqB, inkB = check_clean(vB, mode, "B", fails)
                if vB != vA:
                    nd = sum(1 for x, y in zip(vB, vA) if x != y)
                    first = next(i for i in range(len(vB)) if vB[i] != vA[i])
                    fails.append(f"B: рестарт не детерминирован — {nd} байт "
                                 f"отличаются от A, первый в 0x{VRAM_LO + first:04X}")
                    print(f"  B: отличается от A в {nd} байтах, первый @ "
                          f"0x{VRAM_LO + first:04X}")
                else:
                    print("  B: VRAM после рестарта побайтово совпал с A "
                          "(наследие старого кадра отсутствует)")
                if inkB < MIN_INK:
                    fails.append(f"B: уровень не нарисован (ненулевых байт {inkB})")
    finally:
        s.close()

    print("\nRESULT:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("  -", f)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
