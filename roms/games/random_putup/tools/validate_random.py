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
def solve(mp, desc, verbose=False):
    """BFS по состояниям (tr,tc,carried,seq,frozenset(collected)).
    Возвращает (True, путь) если уровень проходим, иначе (False, причина)."""
    door_tc = desc[0] // 2
    door_tr = desc[1] // 2
    level = 1  # уровень 1 -> B=1
    B = 1 if level < 10 else 2

    def tile(tr, tc):
        if 0 <= tr < TILE_ROWS and 0 <= tc < TILE_COLS:
            return mp[tr * TILE_COLS + tc]
        return 2  # вне карты = стена

    def passable(tr, tc, seq):
        idx = tile(tr, tc)
        if tr == door_tr and tc == door_tc and seq >= B:
            return True  # открытая дверь проходима
        return not solid(idx)

    def fall(tr, tc, seq):
        while tr + 1 < TILE_ROWS and passable(tr + 1, tc, seq):
            tr += 1
        return tr

    eggs = {(i // TILE_COLS, i % TILE_COLS)
            for i, v in enumerate(mp) if v == EGG}

    start = (fall(START_TR, START_TC, 0), START_TC)
    # состояние: tr, tc, carried, seq, collected(frozenset)
    init = (start[0], start[1], 0, 0, frozenset())
    seen = {init}
    q = deque([(init, [init])])

    def win(st):
        return st[3] >= B and (st[0], st[1]) == (door_tr, door_tc)

    while q:
        (tr, tc, carried, seq, coll), path = q.popleft()
        if win((tr, tc, carried, seq, coll)):
            return True, path

        # подбор яйца под ногами (принудительно при стоянии на тайле 7)
        st0 = (tr, tc, carried, seq, coll)
        if tile(tr, tc) == EGG and (tr, tc) not in coll:
            st0 = (tr, tc, carried + 1, seq, coll | {(tr, tc)})
            if st0 not in seen:
                seen.add(st0)
                q.append((st0, path + [st0]))
        tr, tc, carried, seq, coll = st0

        # депозит: стою НА замке (тайл под ногами == LOCK), несу 1..2 яйца
        if tile(tr + 1, tc) == LOCK and 1 <= carried <= 2:
            ns = (tr, tc, carried - 1, seq + 1, coll)
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
            ns = (ntr, ntc, carried, seq, coll)
            # пересбор яйца в новой точке
            if tile(ntr, ntc) == EGG and (ntr, ntc) not in coll:
                ns = (ntr, ntc, carried + 1, seq, coll | {(ntr, ntc)})
            if ns not in seen:
                seen.add(ns)
                q.append((ns, path + [ns]))

    return False, 'путь старт->яйцо->замок->дверь не найден (BFS исчерпан)'


# --- инварианты §10 ----------------------------------------------------------
def check_invariants(mp, desc):
    errs = []
    eggs = [i for i, v in enumerate(mp) if v == EGG]
    locks = [i for i, v in enumerate(mp) if v == LOCK]
    if not eggs:
        errs.append('нет ключа (тайл 7)')
    if not locks:
        errs.append('нет замка (тайл 8)')
    dtr, dtc = desc[1] // 2, desc[0] // 2
    if (dtr, dtc) in {(0, 0), (0, 15), (10, 0), (10, 15)}:
        errs.append('выход в углу (%d,%d)' % (dtr, dtc))
    # ровно 2 врага, состояния 1..8, не на клетке старта
    for base, name in ((2, 'ent1'), (5, 'ent2')):
        st, ex, ey = desc[base], desc[base + 1] // 2, desc[base + 2] // 2
        if not (1 <= st <= 8):
            errs.append('%s: состояние %d вне 1..8' % (name, st))
        if (ey, ex) == (START_TR, START_TC):
            errs.append('%s: стартует на клетке героя' % name)
    # периметр solid (стена 2; в полу допустим замок 8 — он тоже solid)
    for tc in range(TILE_COLS):
        if not solid(mp[0 * TILE_COLS + tc]) or not solid(mp[(TILE_ROWS - 1) * TILE_COLS + tc]):
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


def main():
    ap = argparse.ArgumentParser(description='Гейты решаемости RANDOM PUTUP')
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--asm', default=os.path.join(
        here, '..', 'overlay', 'funcs', 'func_gen_level.asm'))
    ap.add_argument('--level', type=int, default=1,
                    help='пока поддержан только 1 (кураторский)')
    ap.add_argument('--selftest', action='store_true',
                    help='негатив-тест строгости поиска пути на мутациях уровня 1')
    args = ap.parse_args()

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

    errs = check_invariants(mp, desc)
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
