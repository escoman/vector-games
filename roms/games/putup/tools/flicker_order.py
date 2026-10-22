#!/usr/bin/env python3
"""Проверка ПОРЯДКА: перерисовка изменённых тайлов из тени относительно OR-героя.

Гипотеза (тезис пользователя): если стирание/перерисовка тайла теневого экрана
(сбор фрукта -> func_score_and_redraw -> draw_tile_to_buf -> draw_char_at_hl;
объекты -> func_draw_game_objects EI;HLT; erase -> draw_tile_at_ptr) происходит
ПОЗЖЕ, чем func_hero_render наложил героя (OR-блит), то герой в этой клетке
затирается (его нет в тени), а вернётся его только OR-блит СЛЕДУЮЩЕГО кадра,
который guarded и идёт после прохода луча -> скан видит пустую клетку -> мерцание.

Ловим по порядку (хронологически, через паузы на brealpoint) внутри кадра:
  FRAME(граница)  hero_render  OR/OR3(герой наложен)  enemy_render
  SCORE(сбор->erase)  DGO(объекты)  tile_at_ptr/tile_vram(факт. запись в VRAM)
Вердикт по кадру: есть ли запись в VRAM (erase/redraw) ПОЗЖЕ OR-блита героя.

Запуск: python3 roms/games/putup/tools/flicker_order.py [КАДРОВ_СО_СБОРОМ] (молч. 3)
"""
import json
import os
import sys
import time
import bisect

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.abspath(os.path.join(PROJECT, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

NEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
ROM = os.path.join(PROJECT, 'putup_new.rom')
SYMS = json.load(open(os.path.join(PROJECT, 'tools', 'layout.json')))
SYMS = SYMS.get('symbols', SYMS)
SYMS_SORTED = sorted((a, n) for n, a in SYMS.items() if isinstance(a, int))
ROM_BASE = 0x0100

MAIN = SYMS['lbl_main_game_loop']
HERO_RENDER = SYMS['func_hero_render']
ENEMY_RENDER = SYMS['func_enemy_render']
OR = SYMS['func_render_tile_vram_or']
OR3 = SYMS['func_render_tile_vram_or3']
SCORE = SYMS['func_score_and_redraw']
DGO = SYMS['func_draw_game_objects']
GAME_UPDATE = SYMS['func_game_update']
TILE_AT_PTR = SYMS['func_draw_tile_at_ptr']
TILE_VRAM = SYMS['func_render_tile_vram']
DRAW_TO_BUF = SYMS['func_draw_tile_to_buf']
DRAW_CHAR = SYMS['func_draw_char_at_hl']

# фактические записи тайла в VRAM (erase/redraw из тени или объектов)
# draw_tile_to_buf/draw_char_at_hl = путь стирания собранного фрукта из тени
VRAM_WRITERS = {TILE_AT_PTR: 'tile_at_ptr', TILE_VRAM: 'tile_vram',
                DRAW_TO_BUF: 'draw_to_buf', DRAW_CHAR: 'draw_char'}
# маркерыhigh-level
MARKS = {MAIN: 'FRAME', HERO_RENDER: 'hero_render', ENEMY_RENDER: 'enemy_render',
         OR: 'OR(hero)', OR3: 'OR3(hero)', SCORE: 'SCORE(collect)', DGO: 'draw_objects',
         GAME_UPDATE: 'game_update'}
ALL_BP = [MAIN, HERO_RENDER, ENEMY_RENDER, OR, OR3, SCORE, DGO, GAME_UPDATE,
          TILE_AT_PTR, TILE_VRAM, DRAW_TO_BUF]  # draw_char вне BP: flood 128/кадр


def sym_before(addr):
    i = bisect.bisect_right(SYMS_SORTED, (addr, '\uffff')) - 1
    return SYMS_SORTED[i][1] if i >= 0 and SYMS_SORTED[i][0] <= addr else '?'


def main():
    s = McpSession(cwd=ROOT)
    s.start()
    try:
        s.load_rom(ROM, org=ROM_BASE)

        def regs():
            r = s.call("debug_get_registers")
            return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}

        def beam():
            b = s.call("debug_get_beam_state")
            return int(b['raster_line']), int(b['frame'])

        def pause(limit=8.0):
            t0 = time.time()
            while time.time() - t0 < limit:
                if not s.call("debug_is_running").get("running"):
                    return True
                time.sleep(0.015)
            return False

        for a in ALL_BP:
            s.call("debug_set_breakpoint", {"address": a})

        s.call("debug_run")
        time.sleep(0.5)
        # старт уровня: ОДНО SPACE (лишние нажатия возвращают на заставку)
        s.call("debug_press_key", {"key": "SPACE"})
        time.sleep(0.25)
        s.call("debug_release_key", {"key": "SPACE"})

        cur = []          # события текущего кадра: (line, tag)
        frames_seen = 0
        frames_done = 0
        collect_frames = 0
        stall = 0
        t0 = time.time()
        space_retries = 0
        # роям удержанием: сменять направление каждые HOLD кадров, чтобы герой
        # реально проехал ряд и собрал фрукты/задвинул объекты
        HOLD = 400
        roam = ["RIGHT"]
        prev_key = None
        ri = 0
        # идём по уровню -> собираем фрукты (спец-тайлы 3..14) и двигаем объекты
        while time.time() - t0 < 200 and collect_frames < NEED:
            key = roam[(ri // HOLD) % len(roam)]
            ri += 1
            if prev_key and prev_key != key:
                s.call("debug_release_key", {"key": prev_key})
            s.call("debug_press_key", {"key": key})
            prev_key = key
            s.call("debug_run")
            if not pause(6.0):
                stall += 1
                if stall >= 3 and space_retries < 3:
                    # возможно ещё на заставке: ещё одно SPACE
                    s.call("debug_press_key", {"key": "SPACE"})
                    time.sleep(0.2)
                    s.call("debug_release_key", {"key": "SPACE"})
                    space_retries += 1
                    print(f"[retry] SPACE #{space_retries}: брейкпоинты не ловятся", flush=True)
                elif stall >= 6:
                    print("!! пауза не сработала: брейкпоинты не достигаются", flush=True)
                    break
                continue
            stall = 0
            r = regs()
            pc = r['pc']
            line, _ = beam()
            if pc == MAIN:
                frames_seen += 1
                if frames_seen % 20 == 1:
                    print(f"[heartbeat] кадр #{frames_seen} line={line} "
                          f"событий в prev={len(cur)} collect={collect_frames}", flush=True)
                # граница кадра: подвести итог по предыдущему кадру
                rep = analyze(cur)
                if rep:
                    frames_done += 1
                    print(f"\n=== кадр #{frames_done} (line-порядок) ===", flush=True)
                    # схлопнуть flood draw_char ДО героя (скан огня render_all)
                    oix = next((i for i, (_, t) in enumerate(cur) if t.startswith('OR')), len(cur))
                    npre = sum(1 for (_, t) in cur[:oix] if t.startswith('draw_char'))
                    if npre:
                        print(f"   ... {npre}× draw_char (скан огня, до героя) ...", flush=True)
                    for j, (ln, tag) in enumerate(cur):
                        if j < oix and tag.startswith('draw_char'):
                            continue
                        print(f"   line {ln:3d}  {tag}", flush=True)
                    print("   >>> " + rep, flush=True)
                    if 'СБОР' in rep:
                        collect_frames += 1
                cur = []
                continue
            tag = MARKS.get(pc) or VRAM_WRITERS.get(pc)
            if tag is None:
                continue
            # кто вызвал запись в VRAM (по возврату со стека) — для атрибуции
            if pc in VRAM_WRITERS:
                caller = sym_before(rd_ret(s, r['sp']))
                tag = f"{tag}<-{caller}"
            cur.append((line, tag))
        s.call("debug_release_key", {"key": "RIGHT"})
    finally:
        s.close()
    print(f"\nкадров MAIN поймано: {frames_seen}, с OR-героем: {frames_done}, со сбором: {collect_frames}", flush=True)
    return 0


def rd_ret(s, sp):
    try:
        lo = bytes_of(s.call("debug_read_memory", {"address": sp, "size": 2}))[0]
        hi = bytes_of(s.call("debug_read_memory", {"address": (sp + 1) & 0xFFFF, "size": 1}))[0]
        return lo | (hi << 8)
    except Exception:
        return 0


def analyze(events):
    """Позиция OR-блита героя; есть ли запись VRAM/подсистема позже него в кадре."""
    or_idx = None
    for i, (ln, tag) in enumerate(events):
        if tag.startswith('OR'):
            or_idx = i
    has_collect = any(t.startswith('SCORE') for _, t in events)
    if or_idx is None:
        if has_collect:
            sc = [ln for ln, t in events if t.startswith('SCORE')]
            w = [f"line{ln}:{t.split('<-')[0]}" for ln, t in events
                 if t.startswith(('draw_to_buf', 'tile_at_ptr', 'tile_vram'))]
            return (f"СБОР БЕЗ HERO-OR в кадре: erase фрукта line{sc}, "
                    f"записи тайлов {w[:5]} — герой НЕ перекрашен после erase!")
        return None
    # ЖЁСТКОЕ нарушение: фактическая запись тайла в VRAM ПОСЛЕ OR-героя
    hard = [(ln, t) for (ln, t) in events[or_idx + 1:]
            if t.startswith(('tile_at_ptr', 'tile_vram', 'draw_objects',
                             'draw_to_buf', 'draw_char', 'SCORE'))]
    if hard:
        worst = ' / '.join(f"line{ln}:{t.split('<-')[0]}" for ln, t in hard[:5])
        base = "VRAM-ЗАПИСЬ ПОСЛЕ ГЕРОЯ (герой затёрт этим кадром!) -> [" + worst + "]"
        if has_collect:
            base = "СБОР: " + base
        return base
    # СТРУКТУРНО: подсистема game_update (внутри которой fruit erase) запущена после OR
    gu = [(ln, t) for (ln, t) in events[or_idx + 1:] if t.startswith('game_update')]
    if gu:
        return (f"struct: game_update (→стирает фрукт из тени) на line{gu[0][0]} "
                f"после OR-героя; факта erase в этом кадре не было")
    return "ok: после героя записей в VRAM нет"


if __name__ == '__main__':
    sys.exit(main())
