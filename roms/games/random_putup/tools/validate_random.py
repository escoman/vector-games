#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_random.py — гейты решаемости уровней RANDOM PUTUP (Stage 4).

Идея: func_gen_level строит уровни 2..15 «решаемыми по построению», а сид
func_prng не сбрасывается (энтропия = число вызовов), поэтому карты 2..15
невоспроизводимы между запусками. Валидатор не доверяет построению вслепую:
он независимо решает каждую карту поиском пути (BFS по состояниям героя) и
проверяет инварианты §10 GAMEPLAY.MD.

Модель героя — на ТИЛОВОЙ сетке 16x11 (тайл = 2x2 знака; герой в кураторском
уровне выровнен по тайлам, что совпадает с чётными знаковыми координатами для
депозита). Физика: гравитация вниз, горизонтальный ход, прыжок вверх на
JUMP_T тайлов, подбор яйца, депозит в замок (нужен 1..2 яйца), открытие двери
при seq==B и победа на клетке двери.

Используемый ГПСЧ — ЗЕРКАЛО func_prng (ROM 0x1123):
    state = (state * 899) & 0x7FFF ;  байт = ((state>>8) + (state&0xFF)) & 0xFF
Тем же func_prng func_spawn_egg выбирает фрукт в «?»-коробке.

Пока валидируется уровень 1 (кураторский, детерминированный). Уровни 2..15
будут подключены через зеркало генератора + прогон по многим сидам.
"""

import argparse
import os
import re
import sys
from collections import deque

# --- карта тайлов: TL-код по индексу (GAMEPLAY.MD §2) -----------------------
TILE_TL = {
    0: 0x00, 1: 0x20, 2: 0x77, 3: 0x60, 4: 0x7E, 5: 0x7D, 6: 0x75, 7: 0x20,
    8: 0x79, 9: 0x60, 10: 0x20, 11: 0x63, 12: 0x66, 13: 0x20, 14: 0x61,
}
TILE_COLS = 16
TILE_ROWS = 11
EGG, LOCK, FIRE = 7, 8, 6
JUMP_T = 2          # высота прыжка в тайлах (~4 знака, var_scr_0906 до 4)
START_TR, START_TC = 0, 1   # PLAYER_START_ROW=1,COL=2 (знаковые) -> тайл (0,1)


def solid(idx):
    """Твёрдая клетка: TL-глиф >= 0x77 (стена/замок/кубик). Огонь (0x75) — проходим."""
    return TILE_TL.get(idx, 0x20) >= 0x77


class Prng:
    """Зеркало func_prng (16-битный Lehmer, mod 2^15)."""

    def __init__(self, state):
        self.state = state & 0x7FFF

    def next(self):
        self.state = (self.state * 899) & 0x7FFF
        return ((self.state >> 8) + (self.state & 0xFF)) & 0xFF


# --- ПОРТ func_gen_level: уровни 2..15 (решаемость по построению) -----------
# Точное зеркало ассемблерного генератора: тот же порядок вызовов func_prng и
# те же таблицы. После rgl_rndpick флаг переноса всегда 0 (DAD без переполнения),
# поэтому RLC даёт ровно 2*row/2*col, а RLCx4 в rgl_setcell — ровно row*16.
RGL_COL8  = [0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x05, 0x09]  # колонки предметов/выхода
RGL_ECOL8 = [0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B]  # колонки огня/врагов
RGL_EROW8 = [0x03, 0x04, 0x05, 0x06, 0x07, 0x05, 0x03, 0x06]  # air-ряды огня/врагов
RGL_FRT8  = [0x0A, 0x0B, 0x0C, 0x0D, 0x0B, 0x0C, 0x0D, 0x0A]  # тайлы фруктов
RGL_PCOL8 = [0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x04, 0x06]  # стартовые колонки платформ (<=8)
RGL_PROW8 = [0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x06]  # #3: ряд платформ (row8 = запрыг. с земли)


def framework_map():
    """Шаг 1: memset 0x01, периметр 0x02 (row0/row10/col0/col15)."""
    mp = [0x01] * 176
    for tc in range(TILE_COLS):
        mp[tc] = 0x02
        mp[(TILE_ROWS - 1) * TILE_COLS + tc] = 0x02
    for tr in range(1, TILE_ROWS - 1):
        mp[tr * TILE_COLS] = 0x02
        mp[tr * TILE_COLS + TILE_COLS - 1] = 0x02
    return mp


def _rndpick(prng, table):
    return table[prng.next() & 7]


def _setcell(mp, row, col, tile):
    mp[row * TILE_COLS + col] = tile


def gen_random_level(prng, level):
    """Один уровень 2..15 поверх каркаса; прнг — общий сквозной поток."""
    mp = framework_map()
    B = 1 if level < 10 else 2
    # ОГОНЬ (#4) перенесён ПОСЛЕ мебели (см. rgl_fire_draw ниже): низ-стилю нужен
    # routeRight — правая колонка обязательного маршрута, чтобы класть огонь в
    # row10 ПРАВЕЕ неё (герой туда не доходит, опора под путём цела).
    # ПЛАТФОРМЫ (Stage 5 / #3): 1..2 уступа (tile 0x02). Порядок consume как в asm:
    # count=next(); на платформу: row(rgl_prow8),col(rgl_pcol8),length.
    # #3: row8 = единственная высота, запрыгиваемая с пола row9 за 1 прыжок
    # (герой ногами на row7, опираясь на solid row8); row6 — верхняя полка.
    for _ in range((prng.next() & 0x01) + 1):
        r = _rndpick(prng, RGL_PROW8)
        c = _rndpick(prng, RGL_PCOL8)
        length = (prng.next() & 0x03) + 3
        for i in range(length):
            _setcell(mp, r, c + i, 0x02)
    # ФРУКТЫ: 3 клетки на row9
    for _ in range(3):
        c = _rndpick(prng, RGL_COL8); t = _rndpick(prng, RGL_FRT8)
        _setcell(mp, 9, c, t)
    # КЛЮЧИ (яйцо 0x07) на row9, ровно B РАЗНЫХ колонок (nudge 4<->6 при коллизии)
    for _ in range(B):
        c = _rndpick(prng, RGL_COL8)
        if mp[9 * TILE_COLS + c] == 0x07:      # клетка уже с яйцом -> увести
            c = 0x06 if c == 0x04 else 0x04
        _setcell(mp, 9, c, 0x07)
    # МЕБЕЛЬ (Stage 5-fix): выход + коробка + B замков на РАЗНЫХ колонках.
    # Замок одноразовый (loc_106B меняет 0x79->0x7B) => для B=2 нужно 2 замка;
    # выход не над замком (base != lock-индексы). Индексы rgl_col8 различны.
    base = prng.next() & 7
    loff = (prng.next() & 3) + 1                        # 1..4
    ex = (RGL_COL8[base] * 2) & 0xFF                   # char-X выхода
    door_col = RGL_COL8[base]                          # колонка двери (#4)
    _setcell(mp, 10, RGL_COL8[(base + 6) & 7], 0x05)   # скрытая коробка
    _setcell(mp, 10, RGL_COL8[(base + loff) & 7], 0x08)        # замок-1
    if B == 2:
        _setcell(mp, 10, RGL_COL8[(base + loff + 1) & 7], 0x08)  # замок-2
    # ---- ОГОНЬ (#4): два стиля, разбор бита4 func_prng. Зеркало rgl_fire_draw.
    #  решаемость по построению цела: стиль P — огонь на кирпичной полке (rows7/8,
    #  row9/row10 не трогает); стиль B — огонь в row10 правее routeRight (герой не
    #  доходит). Нет места (routeRight>=13) -> откат к стилю P.
    b = prng.next()
    fcount = (b & 0x03) + 2                            # 2..5 клеток
    fstyle = (b >> 4) & 1                              # 0=platform, 1=bottom
    if fstyle == 1:
        rmax = door_col                                # правосторонняя нужная колонка
        for fc in range(14, 1, -1):                    # 14..2, первый справа egg/lock
            if mp[9 * TILE_COLS + fc] in (0x07, 0x08) or \
               mp[10 * TILE_COLS + fc] in (0x07, 0x08):
                if fc > rmax:
                    rmax = fc
                break
        if rmax >= 13:
            fstyle = 0                                 # нет места справа -> платформа
    if fstyle == 1:
        fc = rmax + 2                                  # буфер 1 колонка (rmax+1)
        while fc < 15 and fcount > 0:                  # col15 = правая стена
            if mp[10 * TILE_COLS + fc] == 0x02:         # только свободный пол-стена
                mp[10 * TILE_COLS + fc] = 0x06
                fcount -= 1
            fc += 1
    else:
        for _ in range(fcount):
            c = _rndpick(prng, RGL_ECOL8)              # 4..11
            _setcell(mp, 8, c, 0x02)                   # опора-кирпич
            _setcell(mp, 7, c - 1, 0x02)               # левый кирпич
            _setcell(mp, 7, c, 0x06)                   # огонь
            _setcell(mp, 7, c + 1, 0x02)               # правый кирпич
    # ВРАГИ: тип из тех же 3 вызовов func_prng на слот (поток не смещается).
    def _est(b):
        typ = b & 0x03
        sub = (b >> 2) & 0x03
        if typ in (0, 1):          return typ, 1 + (sub & 1)   # ходок 1/2
        if typ == 2:               return typ, 3 + (sub & 1)   # ворона 3/4
        return typ, 5 + (sub & 3)                              # вертолёт 5..8

    def _cage(typ, r, c):
        if typ in (0, 1):                       # ходок: боковые отражатели
            _setcell(mp, r, 2, 0x03); _setcell(mp, r, 13, 0x03)
        elif typ == 2:                          # ворона: вверх/вниз по колонке
            _setcell(mp, 2, c, 0x03); _setcell(mp, 8, c, 0x03)

    frame = False
    # ВРАГ-1
    typ1, s1 = _est(prng.next())
    r1 = _rndpick(prng, RGL_EROW8); y1 = (r1 * 2) & 0xFF
    c1 = _rndpick(prng, RGL_ECOL8); x1 = (c1 * 2) & 0xFF
    _cage(typ1, r1, c1)
    if typ1 == 3:
        frame = True
    # ВРАГ-2
    typ2, s2 = _est(prng.next())
    r2 = _rndpick(prng, RGL_EROW8); y2 = (r2 * 2) & 0xFF
    if y2 == y1:                                 # #1: не в одном air-ряду (3<->5)
        r2 = 0x03 if r1 != 0x03 else 0x05
        y2 = (r2 * 2) & 0xFF
    c2 = _rndpick(prng, RGL_ECOL8); x2 = (c2 * 2) & 0xFF
    _cage(typ2, r2, c2)
    if typ2 == 3:
        frame = True
    # РАМКА-АРЕНА (если есть вертолёт): row2/row8 (cols2..13) + col2/col13
    # (rows2..8) — замкнутый контур держит хоминг в rows3..7/cols3..12.
    # #3: НЕ перекрашиваем уже твёрдую стену-платформу (0x02) — она сама служит
    # полом арены (solid блокирует вертолёт) и остаётся запрыгиваемой для героя.
    def _paint_reflect(mp, row, col):
        if mp[row * TILE_COLS + col] != 0x02:      # стену платформы не трогаем
            _setcell(mp, row, col, 0x03)
    if frame:
        for tc in range(2, 14):
            _paint_reflect(mp, 2, tc); _paint_reflect(mp, 8, tc)
        for tr in range(2, 9):
            _paint_reflect(mp, tr, 2); _paint_reflect(mp, tr, 13)
    # ВЫХОД уже вычислен в МЕБЕЛИ (ex = 2*col8[base]); desc[1]=Y=row9=18.
    desc = [ex, 0x12, s1, x1, y1, s2, x2, y2]
    return mp, desc


def gen_levels(seed):
    """Уровни 2..15 из одного сквозного потока func_prng, засеянного seed."""
    p = Prng(seed)
    return {lvl: gen_random_level(p, lvl) for lvl in range(2, 16)}


# --- загрузка кураторского уровня 1 из asm ----------------------------------
def _grab_defb(txt, label):
    m = re.search(r'^' + re.escape(label) + r':\s*$', txt, re.M)
    if not m:
        raise SystemExit('метка %s не найдена' % label)
    tail = txt[m.end():]
    vals = []
    for line in tail.splitlines():
        s = line.strip()
        if not s or s.startswith(';'):
            continue
        if not s.startswith('DEFB') and not s.startswith('DEFB'.lower()):
            if ':' in s:      # следующая метка — стоп
                break
        for tok in re.findall(r'([0-9A-Fa-f]+)h', s):
            vals.append(int(tok, 16))
        if s.startswith('DEFB') and len(vals) >= 8 and label == 'rgl_desc1':
            break
        if len(vals) >= 176:
            break
    return vals


def load_curated_level1(asm_path):
    txt = open(asm_path, encoding='utf-8', errors='replace').read()
    mp = _grab_defb(txt, 'rgl_map1')
    de = _grab_defb(txt, 'rgl_desc1')
    if len(mp) < 176:
        raise SystemExit('rgl_map1: ожидал 176 байт, получил %d' % len(mp))
    if len(de) < 8:
        raise SystemExit('rgl_desc1: ожидал 8 байт, получил %d' % len(de))
    return mp[:176], de[:8]


# --- pathfinder: решает карту поиском пути ----------------------------------
def solve(mp, desc, level=1, verbose=False):
    """BFS по состояниям (tr,tc,carried,coll,used). seq = len(used) — число
    сданных яиц; каждый замок используется РОВНО один раз (после депозита
    loc_106B меняет глиф 0x79->0x7B, повторный депозит невозможен). Победа:
    seq>=B и герой на клетке двери."""
    door_tc = desc[0] // 2
    door_tr = desc[1] // 2
    B = 1 if level < 10 else 2

    def tile(tr, tc):
        if 0 <= tr < TILE_ROWS and 0 <= tc < TILE_COLS:
            return mp[tr * TILE_COLS + tc]
        return 2  # вне карты = стена

    locks = {(i // TILE_COLS, i % TILE_COLS)
             for i, v in enumerate(mp) if v == LOCK}

    def passable(tr, tc, seq):
        if tr == door_tr and tc == door_tc and seq >= B:
            return True  # открытая дверь проходима
        return not solid(tile(tr, tc))

    def fall(tr, tc, seq):
        while tr + 1 < TILE_ROWS and passable(tr + 1, tc, seq):
            tr += 1
        return tr

    eggs = {(i // TILE_COLS, i % TILE_COLS)
            for i, v in enumerate(mp) if v == EGG}

    start = (fall(START_TR, START_TC, 0), START_TC)
    # состояние: tr, tc, carried, coll(яйца), used(замки)
    init = (start[0], start[1], 0, frozenset(), frozenset())
    seen = {init}
    q = deque([(init, [init])])

    def win(st):
        return len(st[4]) >= B and (st[0], st[1]) == (door_tr, door_tc)

    while q:
        (tr, tc, carried, coll, used), path = q.popleft()
        if win((tr, tc, carried, coll, used)):
            return True, path
        seq = len(used)

        # подбор яйца под ногами (принудительно при стоянии на тайле 7)
        st0 = (tr, tc, carried, coll, used)
        if tile(tr, tc) == EGG and (tr, tc) not in coll:
            st0 = (tr, tc, carried + 1, coll | {(tr, tc)}, used)
            if st0 not in seen:
                seen.add(st0)
                q.append((st0, path + [st0]))
        tr, tc, carried, coll, used = st0
        seq = len(used)

        # депозит: стою НА НЕИСПОЛЬЗОВАННОМ замке (клетка под ногами), несу 1..2
        below = (tr + 1, tc)
        if below in locks and below not in used and 1 <= carried <= 2:
            ns = (tr, tc, carried - 1, coll, used | {below})
            if ns not in seen:
                seen.add(ns)
                q.append((ns, path + [ns]))

        # ходы: влево/вправо с гравитацией
        moves = []
        for dtc in (-1, 1):
            ntc = tc + dtc
            if passable(tr, ntc, seq):
                moves.append((fall(tr, ntc, seq), ntc))
        # прыжок: вверх по чистой колонке, затем боковой сход с падением
        for h in range(1, JUMP_T + 1):
            atr = tr - h
            if atr < 0 or not all(passable(tr - k, tc, seq) for k in range(1, h + 1)):
                break
            moves.append((fall(atr, tc, seq), tc))
            for dtc in (-1, 1):
                ntc = tc + dtc
                if passable(atr, ntc, seq):
                    moves.append((fall(atr, ntc, seq), ntc))
        for ntr, ntc in moves:
            ns = (ntr, ntc, carried, coll, used)
            if tile(ntr, ntc) == EGG and (ntr, ntc) not in coll:
                ns = (ntr, ntc, carried + 1, coll | {(ntr, ntc)}, used)
            if ns not in seen:
                seen.add(ns)
                q.append((ns, path + [ns]))

    return False, 'путь старт->яйцо->замок->дверь не найден (BFS исчерпан)'


# --- инварианты §10 ----------------------------------------------------------
def check_invariants(mp, desc, level=1):
    errs = []
    B = 1 if level < 10 else 2
    eggs = [i for i, v in enumerate(mp) if v == EGG]
    locks = [i for i, v in enumerate(mp) if v == LOCK]
    lock_cols = {i % TILE_COLS for i in locks}
    if not eggs:
        errs.append('нет ключа (тайл 7)')
    if len(eggs) < B:
        errs.append('ключей %d < требуется %d' % (len(eggs), B))
    if not locks:
        errs.append('нет замка (тайл 8)')
    # замок одноразовый => нужно минимум B замков на РАЗНЫХ колонках
    if len(locks) < B:
        errs.append('замков %d < требуется %d (замок одноразовый)' % (len(locks), B))
    if len(lock_cols) < len(locks):
        errs.append('замки на одинаковых колонках')
    dtr, dtc = desc[1] // 2, desc[0] // 2
    if (dtr, dtc) in {(0, 0), (0, 15), (10, 0), (10, 15)}:
        errs.append('выход в углу (%d,%d)' % (dtr, dtc))
    if dtc in lock_cols:
        errs.append('выход прямо над замком (col %d) -> мгновенная победа' % dtc)
    # ровно 2 врага, клетка containment, не на клетке старта/коридоре
    # frame_present: замкнутая рамка-арена (держит 2D-преследователя в air-области).
    # #3: границей арены считает ЛЮБУЮ блокирующую врага клетку — отражатель 0x03
    # ИЛИ стену-платформу 0x02 (обе TL!=0x20 => враг отскакивает). Ряд row8 может
    # содержать платформы, поэтому чисто ==0x03 уже неверно.
    _blk = (0x02, 0x03)
    frame_present = (all(mp[2 * TILE_COLS + tc] in _blk for tc in range(2, 14))
                     and all(mp[8 * TILE_COLS + tc] in _blk for tc in range(2, 14))
                     and all(mp[tr * TILE_COLS + 2] in _blk for tr in range(2, 9))
                     and all(mp[tr * TILE_COLS + 13] in _blk for tr in range(2, 9)))
    epos = []
    for base, name in ((2, 'ent1'), (5, 'ent2')):
        st, ex, ey = desc[base], desc[base + 1] // 2, desc[base + 2] // 2
        # states 9/10 = динамический погонщик Hurry-Up, в параметрах быть не должен
        if not (1 <= st <= 8):
            errs.append('%s: состояние %d вне 1..8' % (name, st))
        if (ey, ex) == (START_TR, START_TC):
            errs.append('%s: стартует на клетке героя' % name)
        # враг не должен стоять на выигрышном коридоре row9 или на col1/col0/col15
        if ey == 9:
            errs.append('%s: на коридоре row9 (перекрыт выигрышный путь)' % name)
        if ex <= 1 or ex >= 15:
            errs.append('%s: вне safe-колонок (col %d)' % (name, ex))
        # клетка containment актуальна только для random-уровней (2..15);
        # кураторский L1 — эталон с открытой ареной, проверок клетки не требует.
        if level >= 2:
            # 2D-преследователь (5..8) обязан быть заперт рамкой-ареной
            if 5 <= st <= 8 and not (frame_present and 3 <= ey <= 7 and 3 <= ex <= 12):
                errs.append('%s: вертолёт без замкнутой рамки (state %d @ %d,%d)' % (name, st, ey, ex))
            # ворона (3/4): клетки сверху/снизу своей колонки (или рамка)
            if 3 <= st <= 4 and not (frame_present or (mp[2 * TILE_COLS + ex] == 0x03
                                   and mp[8 * TILE_COLS + ex] == 0x03)):
                errs.append('%s: ворона без вертикальной клетки (col %d)' % (name, ex))
            # ходок (1/2): боковые клетки своего ряда (или рамка)
            if 1 <= st <= 2 and not (frame_present or (mp[ey * TILE_COLS + 2] == 0x03
                                  and mp[ey * TILE_COLS + 13] == 0x03)):
                errs.append('%s: ходок без боковой клетки (row %d)' % (name, ey))
        epos.append((ey, ex))
    # #1: два врага не должны сливаться в одного (разные air-ряды)
    if epos and epos[0] == epos[1]:
        errs.append('оба врага в одной точке %s -> видно одного' % (epos[0],))
    if len({r for (r, _c) in epos}) < len(epos):
        errs.append('враги в одном air-ряду (могут визуально сливаться)')
    # периметр solid (стена 2; в полу допустим замок 8 — он тоже solid).
    # #4: в НИЖНЕМ ряду row10 разрешён ОГОНЬ 0x06 как граница (пользователь
    # авторизовал «вместо стены огонь»); потолок row0 обязателен solid.
    for tc in range(TILE_COLS):
        top = mp[0 * TILE_COLS + tc]
        bot = mp[(TILE_ROWS - 1) * TILE_COLS + tc]
        if not solid(top) or not (solid(bot) or bot == 0x06):
            errs.append('нарушен периметр по горизонтали')
            break
    for tr in range(TILE_ROWS):
        if not solid(mp[tr * TILE_COLS]) or not solid(mp[tr * TILE_COLS + TILE_COLS - 1]):
            errs.append('нарушен периметр по вертикали')
            break
    return errs


def render(mp, path=None):
    gl = {1: '.', 2: '#', 3: ' ', 6: '~', 7: 'K', 8: 'L',
          10: 'o', 11: 'o', 12: 'o', 13: 'o', 14: 's'}
    grid = [[gl.get(v, '?') for v in row] for row in
            (mp[r * TILE_COLS:(r + 1) * TILE_COLS] for r in range(TILE_ROWS))]
    if path:
        for (tr, tc, *_ ) in path:
            if grid[tr][tc] in '.~ ':
                grid[tr][tc] = '*'
    return '\n'.join(''.join(row) for row in grid)


def run_negative_tests(mp0, desc0):
    """Проверка строгости pathfinder'а: интактный уровень решается, а
    заведомо сломанные мутации — НЕ решаются. Ловит «слишком всеядную» модель
    (например, если забыт лимит высоты прыжка или не проверяется депозит).
    Мутации намеренно НЕ трогают инварианты §10 (ключ/замок есть, периметр
    цел) — падать должен именно поиск пути."""
    cases = []
    # позитивный контроль: уровень 1 как есть — решаем
    cases.append(('позитив: уровень 1 без изменений', list(mp0), list(desc0), True))
    # негатив 1: ключ уведён высоко (3,3) — без платформ недостижим -> нечего сдавать
    m = list(mp0); m[9 * 16 + 3] = 0x01; m[3 * 16 + 3] = 0x07
    cases.append(('негатив: ключ перенесён высоко (3,3)', m, list(desc0), False))
    # негатив 2: замок уведён высоко (2,6) — встать на него нельзя -> нет депозита
    m = list(mp0); m[10 * 16 + 6] = 0x02; m[2 * 16 + 6] = 0x08
    cases.append(('негатив: замок перенесён высоко (2,6)', m, list(desc0), False))
    # негатив 3: выход уведён высоко (2,1) — после открытия не добраться
    d = list(desc0); d[0] = 0x02; d[1] = 0x04
    cases.append(('негатив: выход перенесён высоко (2,1)', list(mp0), d, False))
    # негатив 4: глухая стена-колонка col8 (ряды 1..9) отсекает дверь (col10)
    m = list(mp0)
    for tr in range(1, 10):
        m[tr * 16 + 8] = 0x02
    cases.append(('негатив: стена-барьер col8 — дверь отрезана', m, list(desc0), False))

    all_ok = True
    for name, m, d, want in cases:
        got, _ = solve(m, d)
        good = (got == want)
        all_ok = all_ok and good
        tag = 'OK  ' if good else 'FAIL'
        kind = 'ожидался решаем' if want else 'ожидался нерешаем'
        print('  [%s] %-42s pathfinder=%-8s (%s)' % (
            tag, name, 'РЕШАЕТ' if got else 'НЕ решает', kind))
    return all_ok


def do_gen_seed(seed):
    """Печатает карты уровней 2..15 для заданного сида — для побайтовой
    сверки с дампом памяти эмулятора (кросс-чек порта func_gen_level)."""
    print('# seed=0x%04X' % (seed & 0x7FFF))
    for lvl, (mp, desc) in sorted(gen_levels(seed).items()):
        print('LVL %d desc=%s' % (lvl, ' '.join('%02X' % b for b in desc)))
        for tr in range(TILE_ROWS):
            row = mp[tr * TILE_COLS:(tr + 1) * TILE_COLS]
            print('  ' + ' '.join('%02X' % v for v in row))


def do_sweep(n):
    """Прогон решаемости уровней 2..15 на сидах 1..n: каждая карта обязана
    пройти и гейты §10, и pathfinder."""
    total = 0
    fails = []
    for seed in range(1, n + 1):
        for lvl, (mp, desc) in sorted(gen_levels(seed).items()):
            total += 1
            errs = check_invariants(mp, desc, lvl)
            ok, info = solve(mp, desc, lvl)
            if errs or not ok:
                why = '; '.join(errs) if errs else info
                fails.append((seed, lvl, why))
    print('Прогон: %d уровней (seed 1..%d), отказов: %d' % (total, n, len(fails)))
    for seed, lvl, why in fails[:40]:
        print('  FAIL seed=%d lv=%d: %s' % (seed, lvl, why))
    if len(fails) > 40:
        print('  ... ещё %d' % (len(fails) - 40))
    return not fails


def main():
    ap = argparse.ArgumentParser(description='Гейты решаемости RANDOM PUTUP')
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--asm', default=os.path.join(
        here, '..', 'overlay', 'funcs', 'func_gen_level.asm'))
    ap.add_argument('--level', type=int, default=1,
                    help='пока поддержан только 1 (кураторский)')
    ap.add_argument('--selftest', action='store_true',
                    help='негатив-тест строгости поиска пути на мутациях уровня 1')
    ap.add_argument('--gen-seed', type=lambda s: int(s, 0), metavar='N',
                    help='напечатать карты уровней 2..15 для сида N (кросс-чек, dec/hex)')
    ap.add_argument('--sweep', type=int, metavar='N', default=0,
                    help='прогнать решаемость уровней 2..15 на сидах 1..N')
    args = ap.parse_args()

    if args.gen_seed is not None:
        do_gen_seed(args.gen_seed)
        return
    if args.sweep:
        sys.exit(0 if do_sweep(args.sweep) else 1)

    if args.level != 1:
        sys.exit('Stage 4 v1: реализован уровень 1; уровни 2..15 '
                 'подключаются следующим шагом (зеркало генератора + прогон по сидам)')

    mp, desc = load_curated_level1(args.asm)

    if args.selftest:
        print('Негатив-тест pathfinder (мутации уровня 1):')
        ok = run_negative_tests(mp, desc)
        print('ИТОГ:', 'ВСЁ В ПОРЯДКЕ' if ok else 'ЕСТЬ РАСХОЖДЕНИЯ')
        sys.exit(0 if ok else 1)
    print('Уровень 1 (кураторский). Описатель:',
          ' '.join('%02X' % b for b in desc))
    print(render(mp))
    print()

    errs = check_invariants(mp, desc, args.level)
    for e in errs:
        print('  [инвариант] ПРОБЛЕМА:', e)
    if not errs:
        print('  [инвариант] OK (§10: ключ/замок/выход-не-угол/2 врага/периметр)')

    ok, info = solve(mp, desc)
    if ok:
        print('  [путь] РЕШАЕМ — найден маршрут (%d состояний):' % len(info))
        print('  маршрут (тайл tr,tc):',
              ' -> '.join('(%d,%d)' % (s[0], s[1]) for s in info))
        print(render(mp, info))
    else:
        print('  [путь] НЕ РЕШАЕМ:', info)

    rc = 0 if (ok and not errs) else 1
    sys.exit(rc)


if __name__ == '__main__':
    main()
