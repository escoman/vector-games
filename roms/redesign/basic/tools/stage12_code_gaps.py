#!/usr/bin/env python3
"""Stage 12: закрыть CODE-дыры в RDB (6 функций, ~940 байт).

После Stage 11 осталось 45 `gap_XXXX`-блоков на 1862 байта. Крупнейшие — это
НЕ данные, а код, который CFG-анализ (`debug_analyze_code`, hard-cap 10000
инструкций + обход только статических ветвей от точки входа 0x0000) не достиг:
вход в них динамический — trampoline `LXI D,addr / PUSH D / RET`, прыжок через
`JP (HL)`/таблицу `JMP`, или `RST 20`. Дизассемблировали каждый блок через
`debug_disassemble_range` и сопоставили с уже именованными соседями.

Заводим РОВНО те блоки, чья природа «функция» подтверждена (лидирующие байты
инструкции + вызываемые/вызывающие адреса):

    func_paint_floodfill      0x2152..0x230B (442) тело PAINT-flood; trampoline из func_cmd_paint
    func_coord_variant_table  0x3181..0x3252 (210) JP-таблица вариантов координат (RST 20, var 3BA9/3BA7)
    func_line_draw            0x2A49..0x2ABA (113) прорисовка линии/дуги; зовёт plot-хелперы 0x26D8/9/DD
    func_str_compare_let      0x0B4C..0x0BA5  (92) сравнение строк / LET-конкатенация (var_type 0C8C)
    func_point_read_planes    0x3C60..0x3C93  (52) POINT-читалка 4 плоскостей через LUT 0x4100
    func_plot_column_step     0x26D7..0x26F6  (32) шаг по колонке + CALL func_render_glyph_column (0x327A)

Подтверждения (побайтно, через `debug_read_memory_range` / `debug_disassemble_range`):

  * `func_point_read_planes` (0x3C60) — ровно те 16 целей (`0x3C69..0x3C93`), на
    которые указывает таблица `data_pixel_read_dispatch` (Stage 11). Тело читает
    `MVI H,41 / MOV D,M` (page_h LUT) и `LXI B,2000 / DAD B` (stride), комбинируя
    4 плоскости через `ANA E`. Прямое подтверждение Stage 7 §8.3 на уровне кода.

  * `func_paint_floodfill` (0x2152) — вначале `POP H / CALL 3BD3(POINT) / RZ`,
    writes VRAM через `0x3281/0x3284`, рекурсия через trampoline-стек. Конец
    ровно на `lbl_230c` (442 байта).

  * `func_str_compare_let` (0x0B4C) — `XRA A / ORA C / RAR / ... / LDA 0C8C
    (var_type_flag) / JPO 1E6D(concat)`, цикл сравнения `LDAX B / CMP M`, хвост
    пишет `SHLD 404D/404F`.

Использование:
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage12_code_gaps.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage12_code_gaps.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

# ---- объекты ------------------------------------------------------------
# kind = function. Проверяем лидирующие байты инструкции по image перед --apply.
# size = точная длина текущего gap-блока (чтобы целиком его покрыть).
OBJECTS = [
    {
        "addr": 0x2152, "name": "func_paint_floodfill", "kind": "function",
        "size": 442, "role": "paint_flood_fill_body",
        # POP H (E1) — вход по trampoline-адресу со стека
        "check": lambda img: img[0x2152] == 0xE1,
        "note": (
            "Тело заливки PAINT (рекурсивный flood). Вход из func_cmd_paint "
            "(0x20B1) через trampoline `LXI D,2152 / PUSH D / RET` — потому "
            "CFG от 0x0000 сюда не доходит. Начало `POP H / CALL 0x3BD3(POINT) "
            "/ RZ`; обход соседей, writes ВГД через 0x3281/0x3284; проверка "
            "стека 0x2301. Конец ровно на lbl_230c (442 байта)."),
        "props": {
            "entry": "trampoline from func_cmd_paint (0x20B1)",
            "calls": "0x3BD3 (POINT), 0x3C60 (planes), 0x3281/0x3284 (VRAM)",
            "cfg_reachable": "no (dynamic PUSH/RET entry)"},
    },
    {
        "addr": 0x3181, "name": "func_coord_variant_table", "kind": "function",
        "size": 210, "role": "coord_transform_variant_table",
        # JMP 3190 (C3 90 31) — таблица векторов прыжков
        "check": lambda img: img[0x3181:0x3184] == bytes([0xC3, 0x90, 0x31]),
        "note": (
            "JP-таблица вариантов координатной рутины: `JMP 3190 / JMP 319A / "
            "JMP 3253 / JMP 31A4 / CALL 319A`, далее тела `XCHG / LHLD 3BA9 "
            "или 3BA7 / XCHG / RST 20 / JP 3253`. Общий `RST 20` + две именованные "
            "RAM-ячейки 0x3BA9/0x3BA7 (кандидаты в var_). Вход через адрес из "
            "таблицы (PCHL/JP), поэтому не покрыт CFG."),
        "props": {
            "layout": "5 JMP/CALL-векторов + тела",
            "shared_vector": "RST 20 (0x0020)",
            "ram_cells": "0x3BA9, 0x3BA7"},
    },
    {
        "addr": 0x2A49, "name": "func_line_draw", "kind": "function",
        "size": 113, "role": "line_arc_draw",
        # MVI A,80 (3E 80) — инициализация направления обхода
        "check": lambda img: img[0x2A49:0x2A4B] == bytes([0x3E, 0x80]),
        "note": (
            "Прорисовка линии/дуги (Брезенхэм-подобный обход). Считает дельты "
            "по var 0x2B56/0x2B57, состояние-байт 0x2A8C (самомодиф.), зовёт "
            "plot-хелперы 0x26D8/0x26D9/0x26DD (см. func_plot_column_step). "
            "Циклы `DCR C / DCR B`, возврат по переполнению. Вход динамический "
            "(адрес рутины из вычислителя графических команд)."),
        "props": {
            "vars": "0x2B56, 0x2B57 (текущая позиция)",
            "state_cell": "0x2A8C (самомодифицируемый счётчик обхода)",
            "calls": "0x26D8/0x26D9/0x26DD (plot step)"},
    },
    {
        "addr": 0x0B4C, "name": "func_str_compare_let", "kind": "function",
        "size": 92, "role": "string_compare_let_concat",
        # XRA A (AF) — начало разбора типа/длины строки
        "check": lambda img: img[0x0B4C] == 0xAF,
        "note": (
            "Сравнение строк и путь LET-конкатенации. Читает флаг типа "
            "0x0C8C (`LDA 0C8C / ADC A / ORA A / JPO 1E6D` — ветвь concat), "
            "цикл сравнения `LDAX B / CMP M / INX H / INX B`, хвост (0x0B93) "
            "пишет результат `SHLD 404D / SHLD 404F`. Самомодиф. слот "
            "data_render_lut_preamble (0x40FC) ссылается на 0x0B4C."),
        "props": {
            "type_flag": "0x0C8C (var_type_flag)",
            "concat_branch": "0x1E6D",
            "result_cells": "0x404D, 0x404F"},
    },
    {
        "addr": 0x3C60, "name": "func_point_read_planes", "kind": "function",
        "size": 52, "role": "point_read_4_planes",
        # PUSH H (E5) — пролог сохранения HL
        "check": lambda img: img[0x3C60] == 0xE5,
        "note": (
            "POINT-читалка 4 плоскостей (E000/C000/A000/8000). Пролог `PUSH H / "
            "MOV E,H / MVI H,41 / MOV D,M` читает page_h из LUT 0x4100, затем "
            "`LXI B,2000 / DAD B` — stride плоскостей; комбинирование битов "
            "`MOV A,M / NOP / ANA E`. Это ровно цели 0x3C69..0x3C93 из таблицы "
            "data_pixel_read_dispatch (Stage 11). Подтверждение Stage 7 §8.3."),
        "props": {
            "dispatch_table": "data_pixel_read_dispatch (0x2132)",
            "lut": "data_x_to_page_h_lut (0x4100)",
            "stride": "0x2000 (LXI B,2000)"},
    },
    {
        "addr": 0x26D7, "name": "func_plot_column_step", "kind": "function",
        "size": 32, "role": "plot_column_step",
        # LXI H,2B57 (21 57 2B) на 0x26D9 — шаг по колонке символа
        "check": lambda img: img[0x26D9:0x26DC] == bytes([0x21, 0x57, 0x2B]),
        "note": (
            "Мелкий plot-хелпер (несколько точек входа: 0x26D8/0x26D9/0x26DD). "
            "Тело: `LXI H,2B57 / PUSH B / MOV C,M / MOV L,H / CALL 0x327A "
            "(func_render_glyph_column) / POP B / RET`. Хвост 0x26E5..0x26F6 — "
            "выравнивающий паддинг (нули). Вызывается из func_line_draw."),
        "props": {
            "entry_points": "0x26D8, 0x26D9, 0x26DD",
            "calls": "0x327A (func_render_glyph_column)",
            "tail": "0x26E5..0x26F6 padding"},
    },
]


# ---- plan / apply -------------------------------------------------------
def plan(image, writer):
    rows = []
    for spec in OBJECTS:
        addr = spec["addr"]
        ok = spec["check"](image)
        cur = writer.exists(addr) or {}
        act = "SKIP" if cur.get("address") else ("CREATE" if ok else "CHECK!")
        rows.append((addr, act, spec["name"], spec["kind"], spec["size"],
                     "паттерн ОК" if ok else "ПАТТЕРН НЕ СОВПАЛ",
                     cur.get("name") or ""))
    return rows


def apply(image, writer):
    log = []
    for spec in OBJECTS:
        addr = to_addr(spec["addr"])
        if not spec["check"](image):
            log.append("%s: %s ПРОПУЩЕН — лидирующие байты не совпали с ожидаемой инструкцией"
                       % (addr_hex(addr), spec["name"]))
            continue
        cur = writer.exists(addr) or {}
        if cur.get("address"):
            log.append("%s: %s уже в RDB (%s), пропускаем"
                       % (addr_hex(addr), spec["name"], cur.get("name")))
            continue
        writer.ensure_object(addr, spec["name"], spec["kind"], size=spec["size"])
        writer.set_property(addr, "role", spec["role"])
        for k, v in spec["props"].items():
            writer.set_property(addr, k, v)
        writer.set_comment(addr, "%s — %s" % (spec["name"], spec["note"]))
        log.append("%s: CREATE %s %s (%d байт)"
                   % (addr_hex(addr), spec["kind"], spec["name"], spec["size"]))
    return log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--rdb", default=DEFAULT_RDB)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    if not (args.check or args.apply):
        args.apply = True

    with open(args.rom, "rb") as fh:
        image = fh.read()

    rdb_path = os.path.abspath(args.rdb)
    session, _cache = open_session(rom=args.rom, org=0x0000)
    try:
        info = session.call("debug_get_rdb_info")
        if os.path.abspath(info.get("path") or "") != rdb_path:
            raise SystemExit("RDB в сессии %r, ожидаем %r"
                             % (info.get("path"), args.rdb))
        writer = RdbWriter(session)
        if args.check:
            print("план Stage 12 (CODE-дыры):")
            for addr, act, name, typ, size, note, cur_name in plan(image, writer):
                tail = "  (уже: %s)" % cur_name if cur_name else ""
                print("  %-6s %s %-26s [%-8s %4d] %s%s"
                      % (act, addr_hex(addr), name, typ, size, note, tail))
            return 0
        for line in apply(image, writer):
            print("  " + line)
        writer.save()
        print("итог: %s" % (writer.summary(),))
        info = session.call("debug_get_rdb_info")
        print("объектов: %s, dirty: %s"
              % (info.get("object_count"), info.get("dirty")))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
