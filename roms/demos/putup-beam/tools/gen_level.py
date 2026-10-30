#!/usr/bin/env python3
"""Генератор карты демо putup-beam: level_01 (16x11) -> уровень 16x32.

Схема (512px = ровно 2 кольца VRAM по 256 строк — иначе мировая адресация
ring = world_y & 0xFF.aliasует хвост уровня с головой):
    ряды  0..9   копия 0: ряд 0 (верхняя стена) + interior 1..9
    ряд  10      СТЫК: стена копии 0 с ПРОХОДАМИ-шахтами (копийные сплошные
                 стены ряд 10 копии N + ряд 0 копии N+1 заменены парой рядов)
    ряд  11      открытый ряд (падение сквозь стык)
    ряды 12..20  копия 1: interior 1..9
    ряд  21      СТЫК: стена с шахтами
    ряд  22      открытый ряд
    ряды 23..30  копия 2: interior 1..8 (обрезка до 32 рядов: ряд 9 копий 2
                 съеден лимитом; его фрукты не входят в набор ключей)
    ряд  31      нижняя сплошная стена

Коллизии демо (по твёрдости putup — глифы тайла >= 77h): SOLID = {02h,04h,05h,
08h} (стены + «?»-ящик), ключи = {07h,0Ah,0Bh} (проходимы, подбираются),
выход = 23 (тёмная фаза, тверд до открытия), остальное проходимо. Вверх — свободный подъём на клетку,
вниз — гравитация (контракт демо, не байт-в-байт putup).

Выход — из data_level_params уровня 1 (X=14h,Y=10h -> клетка (8,10) копии)
в нижней копии; спавн героя — верхняя копия; спавны врагов — записи params
копий 1 и 2 (2 слота демо).

Гейт: flood-fill от спавна героя (4 направления, проходимые клетки) обязан
достичь выхода, всех ключей и обоих спавнов врагов; шахты стыков — сквозные
(клетка над и под проходимы).

Выход-файл: level.inc (массив карты + метаданные). Запуск: gen_level.py
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.dirname(HERE)
PUTUP = os.path.join(DEMO, "..", "..", "games", "putup")
OUT_INC = os.path.join(DEMO, "level.inc")

DEFB_HEX = re.compile(r"(?<![0-9A-Za-z_])0?([0-9A-Fa-f]{1,3})h(?![0-9A-Za-z_])")

ROWS, COLS = 32, 16
SOLID = {0x02, 0x04, 0x05, 0x08}
KEYS = {0x07, 0x0A, 0x0B}
EXIT_CODE = 23
SHAFTS_J1 = (3, 12)          # проходы в стыке между копиями 0 и 1
SHAFTS_J2 = (6, 13)          # проходы в стыке между копиями 1 и 2


def hexvals(line):
    return [int(t, 16) for t in DEFB_HEX.findall(line.split(";")[0])]


def parse_level01():
    vals, seen = [], False
    path = os.path.join(PUTUP, "asm", "data", "data_level_01.asm")
    for line in open(path, encoding="utf-8"):
        if line.startswith("data_level_01"):
            seen = True
            continue
        if seen and line.strip().startswith("DEFB"):
            vals += hexvals(line)
    if len(vals) != 176:
        sys.exit("level_01: %d байт, ожидалось 176" % len(vals))
    return [vals[r * 16:(r + 1) * 16] for r in range(11)]


def parse_params():
    """data_level_params: [+0] exitX, [+1] exitY, [+2..4] ent1 state/X/Y,
    [+5..7] ent2. Уровень 1 — первая запись из 8 байт."""
    path = os.path.join(PUTUP, "asm", "data", "data_level_params.asm")
    vals, seen = [], False
    for line in open(path, encoding="utf-8"):
        if line.startswith("data_level_params"):
            seen = True
            continue
        if seen and line.strip().startswith("DEFB"):
            vals += hexvals(line)
    rec = vals[8:16]                                # запись [01]: уровень 1
    exit_cell = (rec[1] // 2, rec[0] // 2)          # (row, col) клетки 2x2
    ents = [(rec[2], rec[4] // 2, rec[3] // 2),
            (rec[5], rec[7] // 2, rec[6] // 2)]     # (state, row, col)
    return exit_cell, ents


def build_map(l01, exit_cell):
    wall = [0x02] * COLS
    m = []
    m += [row[:] for row in l01[0:10]]              # копия 0: ряды 0..9
    j1 = wall[:]
    for c in SHAFTS_J1:
        j1[c] = 0x01
    m.append(j1)                                    # ряд 10: стык с шахтами
    m.append([0x01] * COLS)                         # ряд 11: открытый
    m += [row[:] for row in l01[1:10]]              # копия 1: ряды 12..20
    j2 = wall[:]
    for c in SHAFTS_J2:
        j2[c] = 0x01
    m.append(j2)                                    # ряд 21: стык с шахтами
    m.append([0x01] * COLS)                         # ряд 22: открытый
    m += [row[:] for row in l01[1:9]]               # копия 2: ряды 23..30
    m.append(wall[:])                               # ряд 31: низ
    if len(m) != ROWS:
        sys.exit("карта: %d рядов, ожидалось %d" % (len(m), ROWS))
    # выход: клетка params в нижней копии (interior 1..8 => ряд 8 недоступен:
    # ряд 8 копии 2 обрезан; выход ставится в ряд 7 копии = ряд 29 карты,
    # колонок params; клетка обязана быть стеной (выход в стене, как в putup)
    er, ec = exit_cell
    row = 23 + (er - 1)
    if er > 8:                                      # ряд 9 копии 2 обрезан
        row = 30
    if m[row][ec] not in SOLID:
        sys.exit("выход (%d,%d): клетка не стена (код %02X)" %
                 (row, ec, m[row][ec]))
    m[row][ec] = EXIT_CODE
    return m, (row, ec)


def flood_fill(m, start):
    seen = {start}
    stack = [start]
    while stack:
        r, c = stack.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < ROWS and 0 <= nc < COLS) or (nr, nc) in seen:
                continue
            code = m[nr][nc]
            if code in SOLID:
                continue
            seen.add((nr, nc))
            stack.append((nr, nc))
    return seen


def main():
    l01 = parse_level01()
    exit_cell, ents = parse_params()
    m, exit_pos = build_map(l01, exit_cell)

    hero_spawn = (1, 8)                             # верхняя копия, пусто
    if m[hero_spawn[0]][hero_spawn[1]] in SOLID:
        sys.exit("спавн героя в стене")
    # враги: ent1 копий 1 и 2 (2 слота демо); состояние из params
    espawns = [(12 + (ents[0][1] - 1), ents[0][2], ents[0][0]),
               (23 + (ents[0][1] - 1), ents[0][2], ents[0][0])]
    for r, c, _ in espawns:
        if m[r][c] in SOLID:
            sys.exit("спавн врага (%d,%d) в стене" % (r, c))

    # --- гейт: flood-fill ---
    reach = flood_fill(m, hero_spawn)
    errs = []
    if exit_pos not in reach:
        errs.append("выход %s недостижим" % (exit_pos,))
    keys = [(r, c) for r in range(ROWS) for c in range(COLS)
            if m[r][c] in KEYS]
    for k in keys:
        if k not in reach:
            errs.append("ключ %s недостижим" % (k,))
    for r, c, _ in espawns:
        if (r, c) not in reach:
            errs.append("спавн врага (%d,%d) недостижим" % (r, c))
    # шахты сквозные: над и под стыком — проходимые клетки
    for jr, shafts in ((10, SHAFTS_J1), (21, SHAFTS_J2)):
        for c in shafts:
            for rr in (jr - 1, jr + 1):
                if m[rr][c] in SOLID:
                    errs.append("шахта (%d,%d): тупик в ряду %d" % (jr, c, rr))
    if errs:
        for e in errs:
            print("FAIL:", e)
        sys.exit(1)

    # --- level.inc ---
    parts = ["/* level.inc — АВТОГЕНЕРАЦИЯ: tools/gen_level.py, не править.",
             " * Карта 16x32 клетки (512px = 2 кольца VRAM). Коды клеток —",
             " * индексы bg_tiles[] из assets.inc; 23 = выход (твёрд до",
             " * открытия). SOLID = {02h,04h,05h,08h}, ключи = {07h,0Ah,0Bh}. */",
             "#ifndef LEVEL_INC",
             "#define LEVEL_INC",
             "",
             "#define LEVEL_ROWS %d" % ROWS,
             "#define LEVEL_COLS %d" % COLS,
             "",
             "static const unsigned char level_map[%d] = {" % (ROWS * COLS)]
    for r in range(ROWS):
        parts.append("    " + ", ".join("%2d" % v for v in m[r]) + ",")
    parts += ["};",
              "",
              "/* (row, col) */",
              "static const unsigned char level_hero_spawn[2] = { %d, %d };"
              % hero_spawn,
              "static const unsigned char level_exit[2] = { %d, %d };"
              % exit_pos,
              "static const unsigned char level_enemy_spawns[2][2] = {",
              "    { %d, %d }, { %d, %d }," % (espawns[0][0], espawns[0][1],
                                               espawns[1][0], espawns[1][1]),
              "};",
              "static const unsigned char level_enemy_state = %d;"
              % espawns[0][2],
              "",
              "#endif /* LEVEL_INC */"]
    with open(OUT_INC, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")

    print("level.inc: %dx%d, ключей %d, выход %s, враги %s / %s" %
          (ROWS, COLS, len(keys), exit_pos,
           tuple(espawns[0][:2]), tuple(espawns[1][:2])))
    print("flood-fill: OK (достижимо клеток %d)" % len(reach))
    sym = {0x02: "#", 0x05: "#", 0x08: "#", 0x01: ".", 0x00: ".",
           0x03: ",", 0x04: "d", 0x07: "o", 0x0A: "k", 0x0B: "K",
           EXIT_CODE: "X"}
    for r in range(ROWS):
        print("%2d %s" % (r, "".join(sym.get(v, "?") for v in m[r])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
