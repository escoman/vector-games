#!/usr/bin/env python3
"""Step E2 (горизонтальный easing врагов) — автоматическая проверка.

Своя сессия v06c-mcp: грузит ROM, запускает игру и на КАЖДОМ кадре сверяет с
независимой Python-моделью:

  A) func_ed_blit3 (midpoint-кадр): окно предсчитано на старте и лежит в
     data_enemy_shift_pre (E3-6a; до этого — окно слота, пересобиравшееся в кадре)
     и 24 блока VRAM по 8 байт (6 фрагментов x 4 плоскости), которые блит обязан
     нарисовать по адресу func_ed_blit3+size-1 (RET);
  B) метка главного цикла (следующий кадр): «ведомая» колонка midpoint-окна
     (base для hoff=1 / base+2 для hoff=2) НЕ должна оставаться побайтово равной
     фрагментам этого окна — иначе остаток пикселей старого сдвинутого вида. Сверка
     по сигнатуре окна, а не по снимку «до blit3»: с E3-6b в midpoint-кадре erase
     может не происходить вовсе (новая отрисовка перекрывает старый footprint), а
     после restore колонку перекрашивают другие рисовальщики (огонь, герой);
  C) засеивание отображения при init: disp_rc == координаты спауна,hoff/voff=0.

Модель глифов — из ROM-файла по data_glyph_ptr_table (тег compactness = бит0
младшего байта слова, снимается как в func_ed_resolve_glyph). Адресная арифметика
приёмника — копия func_ed_blit_frag: дробление строки сделано ПОВОРОТАМИ RRC,
поэтому вклад старшего байта = ((H & 3) << 6), а не (H >> 2) & 0xC0.

Запуск:  python3 roms/games/putup/tools/e2_test.py [КАДРОВ]
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, '..'))           # roms/games/putup
ROOT = os.path.abspath(os.path.join(PROJECT, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 120
ROM = os.path.join(PROJECT, 'putup_new.rom')
SYMS = json.load(open(os.path.join(PROJECT, 'tools', 'layout.json')))
SYMS = SYMS.get('symbols', SYMS)
ROM_BASE = 0x0100
rom = open(ROM, 'rb').read()

TEXTBUF = SYMS['data_text_buffer']
COL_TABLE = SYMS['data_vram_col_table']
PTR_TABLE = SYMS['data_glyph_ptr_table']
PRE = SYMS['data_enemy_shift_pre']          # E3-6a: таблица предсчитанных окон
PRE_KEYS = SYMS['var_enemy_pre_keys']       #   ключи записей [годно][4 кода], шаг 8
PRE_N = SYMS['var_enemy_pre_n']             #   число записей (ставит func_enemy_prebuild)
DISP_RC = 0x6A37
SCRATCH = 0x6A50                     # var_ed_slot .. var_ed_erase_rc (+ho/newh)
MODE_ADDR = SYMS['data_ram_init_image_08C3'] + 0x0D    # var_screen_mode
MAIN_LOOP = SYMS['lbl_main_game_loop']
BLIT3 = SYMS['func_ed_blit3']
BLIT3_RET = SYMS['func_ed_blit_frag'] - 1     # RET — последний байт func_ed_blit3


def peek(addr, n):
    return list(rom[addr - ROM_BASE: addr - ROM_BASE + n])


def regs(session):
    r = session.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def wait_pause(session, limit=20.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not session.call("debug_is_running").get("running"):
            return True
        time.sleep(0.02)
    return False


def read(session, addr, n):
    return list(bytes_of(session.call("debug_read_memory", {"address": addr, "size": n})))


def read_vram(session, addr, n):
    return list(bytes_of(session.call("debug_get_vram_bytes", {"address": addr, "length": n})))


def record(code):
    """Запись глифа как её читает func_render_glyph: compact (тег бит0=1) = 8-байтная
    маска плоскости 0 + нули плоскостей 1..3; код 0x20 = 32 нуля; raw = 32 подряд."""
    if code == 0x20:
        return [0] * 32
    w = peek(PTR_TABLE + 2 * code, 2)
    ptr = w[0] | (w[1] << 8)
    if ptr & 1:
        return peek(ptr & 0xFFFE, 8) + [0] * 24
    return peek(ptr & 0xFFFE, 32)


def recv(cell, mode):
    hl = (cell + (0 - TEXTBUF)) & 0xFFFF
    col = hl & 0x1F
    h, l = hl >> 8, hl & 0xFF
    rowbits = ((h & 3) << 6) | ((l & 0xE0) >> 2)
    page = peek(COL_TABLE + col, 1)[0]
    return (page << 8) | ((mode - rowbits) & 0xFF)


def pre_index(session, gcodes, _cache={}):
    """E3-6a: индекс готового окна из var_enemy_pre_keys с кодами gcodes, либо None.
    Таблица ключей пишется один раз func_enemy_prebuild, поэтому читаем её один раз."""
    if 'keys' not in _cache:
        n = read(session, PRE_N, 1)[0]
        _cache['keys'] = [read(session, PRE_KEYS + i * 8, 5) for i in range(n)]
    for i, rec in enumerate(_cache['keys']):
        if rec[0] and rec[1:5] == list(gcodes):
            return i
    return None


def composite(codes):
    """6 фрагментов (row*3+colpos) x 32 байта: сдвиг на 4 px, вакуум = 0 везде."""
    win = []
    for r in range(2):
        L, R = record(codes[r * 2]), record(codes[r * 2 + 1])
        for cpos in range(3):
            frag = []
            for p in range(4):
                for i in range(8):
                    a, b = L[p * 8 + i], R[p * 8 + i]
                    frag.append([(a >> 4) & 0x0F,
                                 (((a & 0x0F) << 4) | (b >> 4)) & 0xFF,
                                 (b & 0x0F) << 4][cpos])
            win.append(frag)
    return win


def blocks(session, cell, mode):
    """8 плоскостных блоков (4 плоскости x 2 строки) одной колонки."""
    out = []
    for rr in range(2):
        base = recv(cell + rr * 32, mode)
        for p in range(4):
            out.append(((base + p * 0x2000) & 0xFFFF,
                        read_vram(session, (base + p * 0x2000) & 0xFFFF, 8)))
    return out


def bg_blocks(session, row, col, mode):
    """Ожидание для restore-фона колонки: тайл 2x2, который func_render_glyph
    нарисовал бы по кодам текстового буфера в (row,col) и (row+1,col). Тот же
    порядок плоскостей и та же адресная арифметика, что в blocks()."""
    out = []
    for rr in range(2):
        base = recv(TEXTBUF + (row + rr) * 32 + col, mode)
        rec = record(read(session, TEXTBUF + (row + rr) * 32 + col, 1)[0])
        for p in range(4):
            out.append(((base + p * 0x2000) & 0xFFFF, rec[p * 8:p * 8 + 8]))
    return out


def main():
    s = McpSession(cwd=ROOT)
    s.start()
    stats = {'midpoint': 0, 'frames': 0, 'dir1': 0, 'dir2': 0,
             'cache_bad': 0, 'vram_bad': 0, 'stale_bad': 0}
    pending = []            # [(slot, hoff, ведущая колонка, строка, pre-блоки, возраст)]
    try:
        s.load_rom(ROM, org=ROM_BASE)
        s.call("debug_set_breakpoint", {"address": MAIN_LOOP})
        s.call("debug_run")
        time.sleep(0.3)
        s.call("debug_press_key", {"key": "SPACE"})
        assert wait_pause(s), "нет попадания на метку главного цикла"
        disp = read(s, DISP_RC, 24)
        print(f"C) init-засев: rc={disp[0:6]} hoff={disp[6:9]} voff={disp[9:12]} "
              f"codes={disp[13:25]}")
        assert disp[2:6] == [6, 10, 12, 10], "disp_rc не засеян координатами спауна"

        s.call("debug_set_breakpoint", {"address": BLIT3})
        s.call("debug_set_breakpoint", {"address": BLIT3_RET})
        mode = read(s, MODE_ADDR, 1)[0]
        deadline = time.time() + 240
        while stats['frames'] < FRAMES and time.time() < deadline:
            s.call("debug_run")
            if not wait_pause(s):
                print("нет событий 20 с — игра, похоже, закончилась")
                break
            pc = regs(s)['pc']
            if pc == BLIT3:
                r = regs(s)
                base_col, row = r['d'], r['e']
                sc = read(s, SCRATCH, 20)
                slot, gcodes, newh = sc[0], sc[10:14], sc[17]
                win = composite(gcodes)
                # E3-6a: окно больше не привязано к слоту — ищем запись ключа,
                # совпадающего с кодами цели. В blit3 попадаем только при хите
                # поиска, так что отсутствие записи = баг.
                idx = pre_index(s, gcodes)
                assert idx is not None, f"blit3 без окна в таблице: codes={gcodes}"
                actual = read(s, PRE + idx * 192, 192)
                exp_flat = [b for f in win for b in f]
                bad = sum(1 for i in range(192) if actual[i] != exp_flat[i])
                stats['cache_bad'] += bad > 0
                # VRAM «ведомая» колонка до рисования (E3-6b: в midpoint-кадре erase
                # мог не восстанавливать её вовсе — снимок больше не эталон)
                lead = base_col if newh == 1 else base_col + 2
                pre = blocks(s, TEXTBUF + row * 32 + lead, mode)
                # чем именно midpoint-окно забило ведомую колонку: 8 блоков (2 строки
                # x 4 плоскости). Именно их обязан убрать erase следующего кадра.
                cpos = 0 if newh == 1 else 2
                win_lead = []
                for rr in range(2):
                    frag = win[rr * 3 + cpos]
                    base = recv(TEXTBUF + (row + rr) * 32 + lead, mode)
                    for p in range(4):
                        win_lead.append(((base + p * 0x2000) & 0xFFFF,
                                         frag[p * 8:p * 8 + 8]))
                s.call("debug_run")
                assert wait_pause(s) and regs(s)['pc'] == BLIT3_RET, "не на RET blit3"
                vbad = []
                for idx, frag in enumerate(win):
                    rr, cc = idx // 3, idx % 3
                    base = recv(TEXTBUF + (row + rr) * 32 + base_col + cc, mode)
                    for p in range(4):
                        a = (base + p * 0x2000) & 0xFFFF
                        got = read_vram(s, a, 8)
                        if got != frag[p * 8:p * 8 + 8]:
                            vbad.append((rr, cc, p, a, got, frag[p * 8:p * 8 + 8]))
                stats['midpoint'] += 1
                stats['dir1'] += newh == 1
                stats['dir2'] += newh == 2
                stats['vram_bad'] += bool(vbad)
                tag = 'кэш ' + ('OK' if not bad else f'MISMATCH {bad}')
                tag += ' | VRAM ' + ('OK' if not vbad else f'MISMATCH {len(vbad)}')
                print(f"A) midpoint slot={slot} base=({row},{base_col}) hoff={newh} "
                      f"codes={gcodes} -> {tag}")
                if bad:
                    for i in [j for j in range(192) if actual[j] != exp_flat[j]][:6]:
                        print(f"    кэш +0x{i:03X}: факт {actual[i]:02X} != "
                              f"модель {exp_flat[i]:02X}")
                for rr, cc, p, a, got, exp in vbad[:6]:
                    print(f"    row+{rr} frag{cc} pl{p} 0x{a:04X}: факт "
                          f"{bytes(got).hex(' ')} != модель {bytes(exp).hex(' ')}")
                if vbad:
                    full = bytes(read_vram(s, 0x8000, 32768))
                    rr, cc, p, a, got, exp = vbad[0]
                    hits = [hex(0x8000 + m.start()) for m in
                            re.finditer(re.escape(bytes(exp)), full)][:4]
                    print(f"    (модель этого блока встречается в {hits})")
                pending.append((slot, newh, lead, row, pre, win_lead, 0))
            elif pc == BLIT3_RET:
                s.call("debug_run")            # случай, если вход не поймали
            else:                              # кадр главного цикла: проверка B
                stats['frames'] += 1
                # midpoint нарисован в кадре F; erase+выровненный draw происходят в
                # кадре F+1, поэтому сверять можно только на метке кадра F+2.
                still = []
                for (slot, newh, lead, row, pre, win_lead, *age_) in pending:
                    age = (age_[0] if age_ else 0) + 1
                    if age < 2:
                        still.append((slot, newh, lead, row, pre, win_lead, age))
                        continue
                    post = blocks(s, TEXTBUF + row * 32 + lead, mode)
                    exp = bg_blocks(s, row, lead, mode)
                    # остаток сдвинутого вида = колонка всё ещё равна фрагментам окна;
                    # фон = post == модель буфера; иначе колонку перекрасил кто-то ещё
                    # (огонь/герой пишут поверх restore) — это не остаток врага.
                    hit_win = sum(1 for ((_, got), (_, w)) in zip(post, win_lead)
                                  if got == w)
                    hit_bg = sum(1 for ((_, got), (_, e)) in zip(post, exp)
                                 if got == e)
                    if hit_win * 2 > len(post):
                        stats['stale_bad'] += 1
                        print(f"B) stale! slot={slot} hoff={newh} кол.{lead} стр.{row}: "
                              f"{hit_win}/{len(post)} блоков = пиксели midpoint-окна "
                              f"(erase их не вернул)")
                        for (a, got), (_, w) in list(zip(post, win_lead))[:4]:
                            print(f"    0x{a:04X}: факт {bytes(got).hex(' ')} == окно "
                                  f"{bytes(w).hex(' ')}")
                    else:
                        kind = ('фон' if hit_bg == len(post)
                                else f'фон {hit_bg}/{len(post)}, остальное — чужой блит')
                        print(f"B) slot={slot} hoff={newh} кол.{lead} -> чисто ({kind})")
                pending = still
        print(f"\nИТОГО: кадров={stats['frames']} midpoint={stats['midpoint']} "
              f"(hoff1={stats['dir1']} hoff2={stats['dir2']}) "
              f"кэш_сбоев={stats['cache_bad']} vram_сбоев={stats['vram_bad']} "
              f"stale_сбоев={stats['stale_bad']}")
        ok = (stats['midpoint'] > 0 and stats['dir2'] > 0
              and not (stats['cache_bad'] or stats['vram_bad'] or stats['stale_bad']))
        print("PASS" if ok else "FAIL/NEEDS-COVERAGE")
        return 0 if ok else 1
    finally:
        s.close()


if __name__ == '__main__':
    sys.exit(main())
