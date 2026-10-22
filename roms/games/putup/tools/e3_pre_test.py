#!/usr/bin/env python3
"""
Шаг E3-6a: все предсдвинутые окна врагов собираются ОДИН РАЗ на старте
(func_enemy_prebuild), в кадровом пути остаётся только поиск (func_ed_find_pre).

Проверяет:
  A) Таблица на старте: var_enemy_pre_n = длина data_enemy_pre_tiles; ключ записи =
     4 кода тайла из data_tile_graphics; окно записи побайтово равно независимой
     Python-модели композита (сдвиг 4px, вакуум 0). Отдельно: запись с compact-глифом
     обязана быть помечена НЕгодной (окно не используется) — это перенесённая на старт
     проверка E3. Реальный пример: тайл 1 = data_tile_empty (коды 0x20, он compact).
  B) В игре: на каждом попадании поиска HL указывает внутрь таблицы (выровненно по
     192), ключ найденной записи = var_ed_gcodes кадра, а само окно = модель этих
     кодов. Промахи считаются отдельно: они легальны (тайл вне списка), но должны быть
     редкостью — иначе horizontal easing теряется.
  C) В игровых кадрах func_enemy_build_cache НЕ вызывается ни разу (bp молчит).

Запуск:  python3 roms/games/putup/tools/e3_pre_test.py [КАДРОВ]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', 'utils')))

import e2_test as E2                                  # noqa: E402
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 80
S = E2.SYMS
ROM_BASE = E2.ROM_BASE
PRE = S['data_enemy_shift_pre']
KEYS = S['var_enemy_pre_keys']
PRE_N = S['var_enemy_pre_n']
TILES = S['data_enemy_pre_tiles']
TILE_GRAPHICS = S['data_tile_graphics']
PREBUILD = S['func_enemy_prebuild']
FIND = S['func_ed_find_pre']
FP_OK = S['loc_fp_ok']
FP_MISS = S['loc_fp_miss']
BUILD = S['func_enemy_build_cache']
MAIN_LOOP = S['lbl_main_game_loop']
GCODES = 0x6A5A                     # var_ed_gcodes
RECORD_LEN = 192                    # размер окна (6 фрагментов x 32 байта)
KEY_STRIDE = 8                      # [годно][код0..код3][pad x3]

s = None


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def regs():
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}


def wait_pause(limit=25.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.02)
    return False


def resume():
    s.call("debug_run")
    assert wait_pause(), "нет паузы после debug_run"


def tile_codes(idx):
    return E2.peek(TILE_GRAPHICS + idx * 4, 4)


def pre_list():
    """ROM-список индексов тайлов (он же RAM-копия, image грузится на 0x0100)."""
    out = []
    for b in E2.peek(TILES, 16):
        if b == 0xFF:
            break
        out.append(b)
    return out


def flat(win):
    return [b for f in win for b in f]


def compact_codes(codes):
    pt = E2.peek(S['data_glyph_ptr_table'], 512)
    return [c for c in codes if pt[2 * c] & 1]


def check_table(fails, tiles):
    """A) таблица, построенная func_enemy_prebuild, = модель."""
    n = read(PRE_N, 1)[0]
    print(f"A) записей построено: {n} (список тайлов: {tiles})")
    if n != len(tiles):
        fails.append(f"A) var_enemy_pre_n={n}, в data_enemy_pre_tiles {len(tiles)} записей")
    # Ёмкость размечена ВРУЧНУЮ (OPTIMIZATION.MD §4.4): data_enemy_shift_pre =
    # 0x7200..0x77FF — ровно 8 окон по 192 Б; var_enemy_pre_keys = 0x7E00, шаг 8 —
    # 8 записей = 64 Б внутри одной страницы (у func_ed_find_pre старший байт
    # курсора постояннен). Добавление 9-го тайла в data_enemy_pre_tiles молча
    # ломает обе инвариантности — проверяем здесь.
    if n > 8:
        fails.append(f"A) записей {n} > 8: окна выйдут за 0x7200..0x77FF, а ключи — "
                     "за страницу 0x7Eh (func_ed_find_pre держит H постоянным)")
    if (KEYS % 0x100) + KEY_STRIDE * min(n, 8) > 0x100:
        fails.append(f"A) разметка ключей: {KEYS:#04X} + {min(n, 8)}*{KEY_STRIDE} "
                     "выходит за страницу")
    for i, t in enumerate(tiles):
        codes = tile_codes(t)
        rec = read(KEYS + i * KEY_STRIDE, 5)
        ctag = compact_codes(codes)
        if rec[1:5] != codes:
            fails.append(f"A) запись #{i}: ключ {rec[1:5]} != коды тайла {t} {codes}")
        if ctag:
            if rec[0]:
                fails.append(f"A) запись #{i} (тайл {t}, коды {codes}) годна, хотя "
                             f"компактные глифы {ctag} — фильтр prebuild не работает")
            print(f"   #{i} тайл {t:2d} коды={codes} -> НЕ годна (compact {ctag})")
            continue
        if not rec[0]:
            fails.append(f"A) запись #{i} (тайл {t}, коды {codes}) помечена негодной "
                         f"без compact-глифов")
            continue
        actual = read(PRE + i * RECORD_LEN, RECORD_LEN)
        exp = flat(E2.composite(codes))
        bad = sum(1 for j in range(RECORD_LEN) if actual[j] != exp[j])
        print(f"   #{i} тайл {t:2d} коды={codes} окно {'OK' if not bad else f'MISMATCH {bad}'}")
        if bad:
            fails.append(f"A) окно #{i} (тайл {t}) расходится с моделью в {bad} байтах")


def check_frames(fails, want):
    """B) и C) в игровых кадрах:_hits/misses окна, билдер не вызывается."""
    stats = {'frames': 0, 'hit': 0, 'miss': 0, 'win_bad': 0, 'build': 0,
             'miss_codes': set()}
    for bp in (FP_OK, FP_MISS, MAIN_LOOP, BUILD):
        s.call("debug_set_breakpoint", {"address": bp})
    deadline = time.time() + 300
    while stats['frames'] < want and time.time() < deadline:
        s.call("debug_run")
        if not wait_pause():
            print("   нет событий 25 с — игра, похоже, закончилась")
            break
        pc = regs()['pc']
        if pc == BUILD:
            stats['build'] += 1
            fails.append("C) func_enemy_build_cache вызвался в игровом кадре — "
                         "пересборка окна вернулась в кадровый путь")
        elif pc == FP_MISS:
            stats['miss'] += 1
            stats['miss_codes'].add(tuple(read(GCODES, 4)))
        elif pc == FP_OK:
            stats['hit'] += 1
            hl = regs()['hl']
            if not (PRE <= hl < PRE + 16 * RECORD_LEN) or (hl - PRE) % RECORD_LEN:
                fails.append(f"B) попадание поиска вне таблицы окон: HL={hl:04X}")
                resume()
                continue
            i = (hl - PRE) // RECORD_LEN
            codes = read(GCODES, 4)
            rec = read(KEYS + i * KEY_STRIDE, 5)
            if not rec[0] or rec[1:5] != codes:
                fails.append(f"B) окно #{i} для кодов {codes}, ключ записи {rec}")
            actual = read(hl, RECORD_LEN)
            if actual != flat(E2.composite(codes)):
                stats['win_bad'] += 1
                fails.append(f"B) окно #{i} (коды {codes}) не равно модели кадра")
        elif pc == MAIN_LOOP:
            stats['frames'] += 1
        resume()
    for bp in (FP_OK, FP_MISS, MAIN_LOOP, BUILD):
        s.call("debug_remove_breakpoint", {"address": bp})
    print(f"B) кадров пройдено {stats['frames']}: попаданий поиска {stats['hit']}, "
          f"промахов {stats['miss']}")
    if stats['miss_codes']:
        print(f"   промахнулись коды: {sorted(stats['miss_codes'])}")
    if not stats['hit']:
        fails.append("B) за кадры не было ни одного попадания поиска — предсчитанные "
                     "окна вообще не применяются (horiz. easing не работает?)")
    if stats['miss'] > stats['hit']:
        fails.append(f"B) промахов ({stats['miss']}) больше, чем попаданий "
                     f"({stats['hit']}) — список тайлов не покрывает игру")
    if stats['build']:
        print(f"C) вызовов билдера в кадре: {stats['build']}")
    return stats


def main():
    global s
    fails = []
    tiles = pre_list()
    s = McpSession(cwd=E2.ROOT)
    s.start()
    try:
        s.load_rom(E2.ROM, org=ROM_BASE)
        # стартуем с паузой на входе в prebuild: до него таблицы нет
        s.call("debug_set_breakpoint", {"address": PREBUILD})
        s.call("debug_run")
        assert wait_pause(), "func_enemy_prebuild не вызвался при старте"
        assert regs()['pc'] == PREBUILD, "первая пауза не на входе в prebuild"
        s.call("debug_remove_breakpoint", {"address": PREBUILD})
        print(f"стоп на входе в func_enemy_prebuild ({PREBUILD:04X}) — ок")
        check_table_not_yet(fails)

        # игра стартует, таблица к этому моменту построена
        s.call("debug_run")                      # prebuild + остальной init + заставка
        s.call("debug_set_breakpoint", {"address": MAIN_LOOP})
        time.sleep(0.3)
        s.call("debug_press_key", {"key": "SPACE"})
        assert wait_pause(), "главный цикл не достигнут после SPACE"
        s.call("debug_remove_breakpoint", {"address": MAIN_LOOP})

        check_table(fails, tiles)
        check_frames(fails, FRAMES)
    finally:
        s.close()
    print("\n" + ("RESULT: PASS" if not fails else "RESULT: FAIL"))
    for f in fails:
        print(" -", f)
    return 0 if not fails else 1


def check_table_not_yet(fails):
    """До prebuild таблицы нет: var_enemy_pre_n ещё не проставлен (счётчик нулевой),
    а ключи не заполнены. Это и есть доказательство, что строится именно здесь."""
    n = read(PRE_N, 1)[0]
    print(f"до prebuild: var_enemy_pre_n={n} (ожидаем 0 — таблица ещё не строилась)")
    if n:
        fails.append(f"var_enemy_pre_n={n} ДО func_enemy_prebuild — таблица строится "
                     "не только на старте")
    return []


if __name__ == '__main__':
    sys.exit(main())
