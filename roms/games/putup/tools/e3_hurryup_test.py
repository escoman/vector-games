#!/usr/bin/env python3
"""Step E3 — HURRY-UP/off-screen инвариант рендерера врагов.

Баг (замечен пользователем): в начале HURRY-UP, когда погонщик ещё за экраном
внизу, вверху экрана появляется мусор. Причина: func_egg_caught спаунит погонщика
на ycoords = 023h (35), а клетка строки r — это 06600h + r*32, т.е. hl = r*32+col
и приёмник L = 0E0h - 8*r по модулю 100h. Строки >= 32 АЛИАСЯТСЯ на r mod 32
(35 -> строка 3!), а «коды фона» для erase читаются уже за концом буфера — из
scratch самого рендерера (06A60h = var_ed_ho/newh/pL/pR). Пассивная ветка
loc_ed_p_erase звала func_ed_erase_old без проверки строки.

Проверки:
  1) ИНВАРИАНТ: на входе в func_ed_erase_old var_ed_dr < 18h — на натуральной игре;
  2) A) спавн погонщика (disp=35, цель=34..): за подъём 35->26 ни один байт VRAM в
     зоне алиаса (строки 0..5, колонки 24..29, 4 плоскости) не меняется;
  3) B) легитимный erase НЕ сломан: disp=(12,col) на экране -> старый footprint
     обязан быть стёрт;
  4) инвариант ещё раз на синтетическом подъёме (bp на erase_old: учёт отклонённых
     вызовов + bp на erase_old+6, куда доходит только легитимный erase);
  5) снапы лестницы (правая стена, «телепорт» |dcol|>1, подъём, |drow|>1) и midpoint
     у левого края: решение (disp/hoff/voff) и побайтовый VRAM против модели
     func_render_glyph (raw/compact/space — см. record());
  6) compact-глиф в окне композита: инъекция var_ed_gcodes на входе в билдер ->
     флаг var_ed_bc_compact=1, решение не изменилось (hoff=1), а нарисован ВЫРОВНЕННЫЙ
     2x2, третья колонка окна не тронута.

Запуск:  python3 roms/games/putup/tools/e3_hurryup_test.py [КАДРОВ]
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

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 40
ROM = os.path.join(PROJECT, 'putup_new.rom')
SYMS = json.load(open(os.path.join(PROJECT, 'tools', 'layout.json')))
SYMS = SYMS.get('symbols', SYMS)
ROM_BASE = 0x0100
rom = open(ROM, 'rb').read()

TEXTBUF = SYMS['data_text_buffer']
PTR_TABLE = SYMS['data_glyph_ptr_table']
ISLAND = SYMS['data_ram_init_image_08C3']
STATE1 = ISLAND + 0x57              # var_entity1_state
STATE2 = ISLAND + 0x58              # var_entity2_state
XC = ISLAND + 0x5C                  # data_entity_xcoords[0]
YC = ISLAND + 0x5F                  # data_entity_ycoords[0]
PLAYER_RC = ISLAND + 0x3E           # var_player_row, +1 = var_player_col
LIVES = ISLAND + 0x5B               # var_lives_icons (байт-паттерн значков HUD)
BONUS = ISLAND + 0x38               # var_bonus_counter: счётчик жизней (DCR в death)
DISP_RC = 0x6A37
DISP_HOFF = 0x6A3D
DISP_VOFF = 0x6A40
DISP_CODES = 0x6A44
SCRATCH = 0x6A50                    # var_ed_slot..; var_ed_dr = SCRATCH+3
GCODES = 0x6A5A                     # var_ed_gcodes: 4 кода цели (и compact, и raw)
BC_COMPACT = 0x6A6D                 # var_ed_bc_compact: ставится билдером на старте
BUILD = SYMS['func_enemy_build_cache']
FIND = SYMS['func_ed_find_pre']      # E3-6a: поиск готового окна (промах = A=0FFh)
INIT = SYMS['func_enemy_render_init']
PRE = SYMS['data_enemy_shift_pre']          # E3-6a: таблица предсчитанных окон
PRE_KEYS = SYMS['var_enemy_pre_keys']       #   ключи [годно][4 кода], шаг 8
PRE_N = SYMS['var_enemy_pre_n']             #   число записей
COL_TABLE = SYMS['data_vram_col_table']
MODE_ADDR = ISLAND + 0x0D           # var_screen_mode
MAIN_LOOP = SYMS['lbl_main_game_loop']
ERASE_OLD = SYMS['func_ed_erase_old']
# guard в func_ed_erase_old = LDA abs(3) + CPI(2) + RNC(1) => следующая инструкция:
ERASE_GOES = ERASE_OLD + 6          # сюда доходит только легитимный erase
ROW_LIMIT = 0x18                    # инвариант: строки >= 18h (вне поля) не трогаем
CH_COL = 26                         # колонка синтетического погонщика

s = None                            # сессия для хелперов
COLPAGE = []                        # col_table целиком (читается один раз)


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


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def write(addr, data):
    s.call("debug_write_memory", {"address": addr, "data": list(data)})


def read_vram(addr, n):
    return list(bytes_of(s.call("debug_get_vram_bytes", {"address": addr, "length": n})))


def recv(row, col, mode):
    """Адрес приёмника 1-го байта глифа — копия арифметики func_render_glyph."""
    hl = (row * 32 + col) & 0xFFFF
    h, l = hl >> 8, hl & 0xFF
    rowbits = ((h & 3) << 6) | ((l & 0xE0) >> 2)
    return (COLPAGE[hl & 0x1F] << 8) | ((mode - rowbits) & 0xFF)


def segments(rows, cols, mode):
    """Сегменты VRAM: строки одного столбца лежат подряд (8 байт на строку)."""
    lo, hi = min(rows), max(rows)
    n = (hi - lo + 1) * 8
    out = []
    for c in cols:
        base = recv(hi, c, mode)          # старшая строка = младший адрес
        for p in range(4):
            out.append((base + p * 0x2000) & 0xFFFF)
    return [(a, n) for a in out]


def snap(segs):
    return {a: read_vram(a, n) for a, n in segs}


def diff(before, after):
    return [(a, e, after[a]) for a, e in before.items() if after[a] != e]


def one_frame():
    s.call("debug_run")
    assert wait_pause(), "нет попадания на метку главного цикла"


def force_chaser(disp_row, target_row, col=CH_COL):
    """Синтетический HURRY-UP: слот 1 = погонщик (state 9) с заданным отображением."""
    write(STATE1, [9])
    write(XC + 1, [col])
    write(YC + 1, [target_row])
    write(DISP_RC + 2, [disp_row, col])
    write(DISP_HOFF + 1, [0])
    write(DISP_VOFF + 1, [0])


def peek(addr, n):
    return list(rom[addr - ROM_BASE: addr - ROM_BASE + n])


def record(code):
    """Запись глифа так, как её читает func_render_glyph (Tier 2):
    код 0x20 — own fast-path, 32 нуля; compact (тег бит0 указателя = 1) —
    только 8-байтная маска плоскости 0, плоскости 1..3 пишутся нулями;
    raw (тег=0) — 32 байта подряд."""
    if code == 0x20:
        return [0] * 32
    w = peek(PTR_TABLE + 2 * code, 2)
    ptr = w[0] | (w[1] << 8)
    if ptr & 1:
        return peek(ptr & 0xFFFE, 8) + [0] * 24
    return peek(ptr & 0xFFFE, 32)


def bufcell(row, col):
    """4 кода клетки текстового буфера ЖИВОЙ RAM (его логика и правит в этом кадре)."""
    a = TEXTBUF + row * 32 + col
    return [read(a, 1)[0], read(a + 1, 1)[0], read(a + 32, 1)[0], read(a + 33, 1)[0]]


def expect_tile(row, col, codes, mode):
    """Ожидание выровненного рендера 2x2: {адрес блока: 32 байта}."""
    out = {}
    for rr in range(2):
        for cc in range(2):
            base = recv(row + rr, col + cc, mode)
            glyph = record(codes[rr * 2 + cc])
            for p in range(4):
                a = (base + p * 0x2000) & 0xFFFF
                out[a] = glyph[p * 8: p * 8 + 8]
    return out


def vram_of(blocks):
    return {a: read_vram(a, 8) for a in blocks}


def pre_index(codes, _cache={}):
    """E3-6a: индекс окна в var_enemy_pre_keys с кодами codes, либо None.
    Ключи пишются один раз func_enemy_prebuild, поэтому таблицу читаем один раз."""
    if 'keys' not in _cache:
        n = read(PRE_N, 1)[0]
        _cache['keys'] = [read(PRE_KEYS + i * 8, 5) for i in range(n)]
    for i, rec in enumerate(_cache['keys']):
        if rec[0] and rec[1:5] == list(codes):
            return i
    return None


def composite(codes):
    """6 фрагментов (row*3+colpos) x 32 байта — копия арифметики
    func_enemy_build_cache: сдвиг на 4 px, вакуум = 0 во всех плоскостях."""
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


def check_seed(tag, fails):
    """Сев после func_enemy_render_init: disp := цель, суб-сдвиги := 0, кэш кодов :=
    буфер по цели. E3-6a: композит больше не строится на init — окна готовы со
    старта; проверяем, что годным кодам спауна соответствует запись таблицы, а
    компактные коды годного окна не имеют (draw уйдёт выровненно)."""
    pt = read(PTR_TABLE, 512)
    for slot in (1, 2):
        t = (read(YC + slot, 1)[0], read(XC + slot, 1)[0])
        d = read(DISP_RC + slot * 2, 2)
        h, v = read(DISP_HOFF + slot, 1)[0], read(DISP_VOFF + slot, 1)[0]
        if list(d) != list(t) or h or v:
            fails.append(f"{tag} slot{slot}: disp={list(d)} hoff={h} voff={v}, "
                         f"цель {list(t)}")
        codes = bufcell(*t)
        if read(DISP_CODES + slot * 4, 4) != codes:
            fails.append(f"{tag} slot{slot}: кэш кодов "
                         f"{read(DISP_CODES + slot * 4, 4)} != буфер по цели {codes}")
        compact = [c for c in codes if pt[2 * c] & 1]
        idx = pre_index(codes)
        if compact and idx is not None:
            fails.append(f"{tag} slot{slot}: компактные коды {codes} получили "
                         f"годное окно #{idx} — фильтр prebuild не работает")
        if idx is not None:
            win = composite(codes)
            cache = read(PRE + idx * 192, 192)
            bad = [i for i in range(6) if win[i] != cache[i * 32:i * 32 + 32]]
            if bad:
                fails.append(f"{tag} slot{slot}: окно #{idx} не совпало с моделью во "
                             f"{len(bad)} фрагментах {bad} коды={codes}")


def force_ladder(state, disp, target):
    """Синтетический кадр рендерера: состояние + отображение + цель слота 1."""
    write(STATE1, [state])
    write(DISP_RC + 2, list(disp))
    write(DISP_HOFF + 1, [0])
    write(DISP_VOFF + 1, [0])
    write(XC + 1, [target[1]])
    write(YC + 1, [target[0]])


def check_snap(name, disp, target, fails, mode, want=None, want_h=0, want_v=0):
    """Один форсированный кадр: ждём разрешённый лестницей исход (snap или midpoint)."""
    want = list(target) if want is None else list(want)
    for _ in range(4):
        force_ladder(1, disp, target)
        before_target = read(YC + 1, 1)[0], read(XC + 1, 1)[0]
        one_frame()
        if (read(YC + 1, 1)[0], read(XC + 1, 1)[0]) == before_target:
            break
    d = read(DISP_RC + 2, 2)
    hoff, voff = read(DISP_HOFF + 1, 1)[0], read(DISP_VOFF + 1, 1)[0]
    ok = True
    if list(d) != want or hoff != want_h or voff != want_v:
        ok = False
        fails.append(f"{name}: disp={list(d)} hoff={hoff} voff={voff}, ждали "
                     f"{want} {want_h} {want_v}")
    # модель кадра для SNAP: erase старого 2x2 -> коды буфера, затем draw нового
    # 2x2; пересечение окон перекрывается новым видом (update по адресам блоков).
    # Midpoint-окно ( hoff/voff != 0 ) здесь не сверяется — его поштучно проверяет
    # e2_test.py на живых midpoint-кадрах.
    nblk = 0
    if want_h == 0 and want_v == 0:
        exp = expect_tile(disp[0], disp[1], bufcell(*disp), mode)
        exp.update(expect_tile(d[0], d[1], bufcell(d[0], d[1]), mode))
        got = vram_of(exp)
        nblk = len(exp)
        bad = [a for a in exp if exp[a] != got[a]]
        if bad:
            ok = False
            sc = read(SCRATCH, 20)
            fails.append(
                f"{name}: VRAM не совпал с моделью в {len(bad)} блоках "
                + " ".join('%04X %s!=%s' % (a, bytes(exp[a]).hex(),
                                            bytes(got[a]).hex()) for a in bad[:3])
                + f" | после кадра: цель=({read(YC + 1, 1)[0]},{read(XC + 1, 1)[0]}) "
                  f"scratch tr={sc[1]} tc={sc[2]} dr={sc[3]} dc={sc[4]} gcodes={sc[10:14]} "
                  f"buf(disp)={bufcell(*disp)} buf(цель)={bufcell(d[0], d[1])} "
                  f"disp_codes={read(DISP_CODES + 4, 4)}")
    print(f"{'OK ' if ok else 'BAD'} {name}: disp {list(disp)}->{list(d)} "
          f"hoff={hoff} voff={voff} блоков сверено {nblk}")


def main():
    global s
    fails = []
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

        # ---- 1) инвариант на натуральной игре -------------------------------
        s.call("debug_set_breakpoint", {"address": ERASE_OLD})
        s.call("debug_set_breakpoint", {"address": ERASE_GOES})
        hits = frames = worst = skipped = 0
        while frames < FRAMES:
            s.call("debug_run")
            if not wait_pause():
                print("нет событий 20 с — игра, похоже, закончилась")
                break
            pc = regs()['pc']
            if pc == ERASE_OLD:
                hits += 1
                dr = read(SCRATCH + 3, 1)[0]
                worst = max(worst, dr)
                if dr >= ROW_LIMIT:
                    skipped += 1        # guard обязан вернуть, проверим на +6
            elif pc == ERASE_GOES:
                dr = read(SCRATCH + 3, 1)[0]
                if dr >= ROW_LIMIT:
                    fails.append(f"erase_old ПРОДОЛЖИЛ с dr={dr} "
                                 f"слот={read(SCRATCH, 1)[0]}")
            elif pc == MAIN_LOOP:
                frames += 1
        s.call("debug_remove_breakpoint", {"address": ERASE_OLD})
        s.call("debug_remove_breakpoint", {"address": ERASE_GOES})
        print(f"1) натуральная игра: кадров={frames} вызовов erase_old={hits} "
              f"(отклонено guard'ом {skipped}) max dr={worst} (предел {ROW_LIMIT})")

        # ---- 2A) спавн погонщика: алиас строк >= 32 -------------------------
        segs = segments(range(0, 6), range(CH_COL - 2, CH_COL + 4), mode)
        total = sum(n for _, n in segs)
        force_chaser(35, 34)
        for a, n in segs:
            write(a, [0xAA] * n)
        alias = 0
        for f in range(12):
            before = snap(segs)
            one_frame()
            bad = diff(before, snap(segs))
            if bad:
                alias += 1
                fails.append(f"A) кадр {f}: dr={read(DISP_RC + 2, 1)[0]} "
                             f"цель={read(YC + 1, 1)[0]} -> запись в алиас "
                             + " ".join("%04X %s->%s" % (a, bytes(e).hex(), bytes(g).hex())
                                        for a, e, g in bad[:3]))
            if read(YC + 1, 1)[0] <= 26:
                break
        print(f"2A) подъём погонщика 35->26: кадров={f + 1} байт в зоне алиаса="
              f"{total} попаданий={alias}")

        # ---- 3B) легитимный erase на экране обязан остаться -----------------
        force_chaser(12, 35)
        segs_b = segments([12, 13], [CH_COL, CH_COL + 1], mode)
        for a, n in segs_b:
            write(a, [0xAA] * n)
        before = snap(segs_b)
        one_frame()
        bad = diff(before, snap(segs_b))
        print(f"3B) erase footprint (12,{CH_COL}): изменённых сегментов "
              f"{len(bad)} из {len(segs_b)}")
        if not bad:
            fails.append("B) старый footprint не стёрся — регресс пассивной ветки")

        # ---- 4) инвариант на синтетическом подъёме --------------------------
        s.call("debug_set_breakpoint", {"address": ERASE_OLD})
        s.call("debug_set_breakpoint", {"address": ERASE_GOES})
        force_chaser(35, 35)
        bad_inv = rejected = 0
        rows_seen = []
        for _ in range(80):
            s.call("debug_run")
            if not wait_pause():
                break
            pc = regs()['pc']
            if pc == ERASE_OLD:
                dr = read(SCRATCH + 3, 1)[0]
                if dr >= ROW_LIMIT:
                    rejected += 1
                    rows_seen.append(dr)
            elif pc == ERASE_GOES:
                dr = read(SCRATCH + 3, 1)[0]
                if dr >= ROW_LIMIT:
                    bad_inv += 1
                    fails.append(f"erase_old ПРОДОЛЖИЛ с dr={dr} на HURRY-UP-подъёме")
            elif pc == MAIN_LOOP and read(YC + 1, 1)[0] <= 26:
                break
        s.call("debug_remove_breakpoint", {"address": ERASE_OLD})
        s.call("debug_remove_breakpoint", {"address": ERASE_GOES})
        print(f"4) HURRY-UP-подъём: guard отклонил вызовов = {rejected} "
              f"(строки {rows_seen}) нарушений = {bad_inv}")

        # ---- 5) снапы: правая стена, «телепорт», подъём ---------------------
        # state 1 (активный) + форсированные disp/цель: лестница обязана выдать
        # мгновенный snap (hoff=voff=0, disp=цель) и чистый выровненный VRAM.
        check_snap("5a) правая стена (30->31) snap", (6, 30), (6, 31), fails, mode)
        check_snap("5b) левый край (1->0) midpoint", (6, 1), (6, 0), fails, mode,
                   want=(6, 1), want_h=2)
        check_snap("5c) телепорт |dcol|>1 snap", (6, 10), (6, 14), fails, mode)
        check_snap("5d) подъём на клетку snap", (6, 10), (5, 10), fails, mode)
        check_snap("5e) прыжок |drow|>1 snap", (6, 10), (10, 10), fails, mode)
        check_snap("5f) шаг вправо midpoint", (6, 10), (6, 11), fails, mode,
                   want=(6, 10), want_h=1)

        # ---- 6) compact-глиф в окне: отказ от композита (E3) -------------------
        # Инъекция НА ВХОДЕ func_enemy_build_cache: var_ed_gcodes := compact-коды
        # (тег бит0=1). Решение (midpoint hoff=1) менять нельзя, поэтому ждём, что
        # диспетчер draw на этот кадр возьмёт ВЫРОВНЕННЫЙ путь: 2x2 = модель
        # func_render_glyph для compact (маска + нули), а третья колонка окна
        # (base+2) обязана остаться нетронутой (маркер). Без guard'а туда лёг бы
        # композит, собранный из байт СОСЕДНЕЙ записи (мусор).
        INJ = [44, 44, 44, 44]
        pt = read(PTR_TABLE, 512)
        if not pt[2 * INJ[0]] & 1:
            fails.append(f"6) код {INJ[0]} не compact — тест потерял смысл")
        # гарантируем вызов поиска окна слотом 1 в этом кадре (hoff=1) и подменяем
        # коды цели на компактные: для них в таблице нет годной записи, поиск обязан
        # промахнуться, и кадр рисуется выровненно (2 колонки), не трогая третью.
        force_ladder(1, (6, 10), (6, 11))
        write(DISP_CODES + 4, [0, 0, 0, 0])
        third = [recv(6, 12, mode), recv(7, 12, mode)]
        third += [a + p * 0x2000 for a in third for p in range(4)]
        third = sorted(set(third))
        for a in third:
            write(a, [0xAA] * 8)
        s.call("debug_set_breakpoint", {"address": FIND})
        injected = False
        for _ in range(40):
            s.call("debug_run")
            if not wait_pause():
                break
            pc = regs()['pc']
            if pc == FIND and not injected and read(SCRATCH, 1)[0] == 1:
                write(GCODES, INJ)
                injected = True
            elif pc == MAIN_LOOP:
                break
        s.call("debug_remove_breakpoint", {"address": FIND})
        if not injected:
            fails.append("6) func_ed_find_pre слотом 1 не вызвался — нечего проверять")
        else:
            hoff = read(DISP_HOFF + 1, 1)[0]
            d = read(DISP_RC + 2, 2)
            if hoff != 1 or list(d) != [6, 10]:
                fails.append(f"6) решение изменилось: disp={list(d)} hoff={hoff}")
            exp = expect_tile(6, 10, INJ, mode)      # выровненный draw 2x2
            got = vram_of(exp)
            bad = [a for a in exp if exp[a] != got[a]]
            kept = [a for a in third if read_vram(a, 8) != [0xAA] * 8]
            print(f"{'OK ' if not bad and not kept else 'BAD'} 6) compact-инъекция "
                  f"{INJ}: hoff={hoff} блоков сверено {len(exp)}, "
                  f"расхождений {len(bad)}, маркер 3-й колонки тронут в {len(kept)}")
            if bad:
                fails.append("6) VRAM не совпал с моделью выровненного render "
                             + " ".join('%04X %s!=%s' % (a, bytes(exp[a]).hex(),
                                                        bytes(got[a]).hex())
                                        for a in bad[:3]))
            if kept:
                fails.append(f"6) третья колонка окна перезаписана ({len(kept)} "
                             f"блоков) — композит применён, несмотря на промах поиска")

        # ---- 7) РЕАЛЬНАЯ гибель и перезагрузка уровня -------------------------
        # 9/0A — пара «мозг+тело» погонщика: func_entity_state9 ведёт координаты
        # слота 1 к игроку, func_entity_state10 рисует тело и при |dx|,|dy| < 2
        # уходит в func_collision_death -> JMP loc_19A0 (перезагрузка уровня) ->
        # func_enemy_render_init. Проверяем: за всю погоню ни одного erase за
        # инвариантом строк, а сев после init годен (disp=цель, суб-сдвиги 0, кэш
        # кодов = буфер по цели, композит = модель этих кодов).
        lives0 = read(BONUS, 1)[0]
        write(STATE1, [9])
        write(STATE2, [10])
        write(XC + 1, [read(PLAYER_RC + 1, 1)[0]])
        write(YC + 1, [35])
        s.call("debug_set_breakpoint", {"address": ERASE_GOES})
        s.call("debug_set_breakpoint", {"address": INIT})
        seeded = viol = 0
        for _ in range(900):
            s.call("debug_run")
            if not wait_pause():
                break
            pc = regs()['pc']
            if pc == ERASE_GOES:
                if read(SCRATCH + 3, 1)[0] >= ROW_LIMIT:
                    viol += 1
                    fails.append("7) erase_old ПРОДОЛЖИЛ вне поля на пути к гибели")
            elif pc == INIT:
                seeded += 1
                s.call("debug_remove_breakpoint", {"address": INIT})
                break
        # init ещё не выполнился (bp на входе) — доходим до первого MAIN_LOOP, где
        # загрузчик уже всё нарисовал и засевал отображение
        for _ in range(4):
            s.call("debug_run")
            if not wait_pause():
                break
            if regs()['pc'] == MAIN_LOOP:
                break
        print(f"7) гибель: дошло до func_enemy_render_init={bool(seeded)} "
              f"жизни {lives0}->{read(BONUS, 1)[0]} y=({read(YC + 1, 1)[0]},"
              f"{read(YC + 2, 1)[0]}) нарушений инварианта={viol}")
        if seeded and read(BONUS, 1)[0] >= lives0:
            fails.append(f"7) init случился, но жизни не ubyло ({lives0}->"
                         f"{read(BONUS, 1)[0]}) — это не гибель, coverage не получен")
        if not seeded:
            fails.append("7) погонщик не догнал игрока / перезагрузка не случилась")
        else:
            check_seed("7) после перезагрузки", fails)
        # ещё 20 кадров обычным ходом: инвариант строк не должен ломаться и дальше
        bad20 = frames20 = 0
        while frames20 < 20:
            s.call("debug_run")
            if not wait_pause():
                break
            pc = regs()['pc']
            if pc == ERASE_GOES and read(SCRATCH + 3, 1)[0] >= ROW_LIMIT:
                bad20 += 1
            elif pc == MAIN_LOOP:
                frames20 += 1
        s.call("debug_remove_breakpoint", {"address": ERASE_GOES})
        if bad20:
            fails.append(f"7b) после перезагрузки erase_old продолжался вне поля "
                         f"{bad20} раз")
        print(f"7b) {frames20} кадров после перезагрузки: нарушений инварианта={bad20}")
    finally:
        s.close()

    print()
    for f in fails:
        print("FAIL:", f)
    print("RESULT:", "FAIL" if fails else "PASS")
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
