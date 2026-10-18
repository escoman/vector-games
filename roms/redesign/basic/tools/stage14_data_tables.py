#!/usr/bin/env python3
"""Stage 14: завести подтверждённые float-ряды (таблицы коэффициентов) в RDB.

Средний слой `0x17xx..0x19xx` разобран через `debug_disassemble_range` и
`code.asm`: это НЕ байт-суп, а области вокруг трансцендентных функций
(`func_exp` 0x17E3, `func_sin` 0x18C1, `func_cos` 0x18BB, `func_tan` 0x191E,
`func_atn` 0x1933). `func_1844`/`func_1853` — evaluator полинома (Horner),
читающий коэффициенты порциями по 4 байта (`mov e,m/inx h … mov b,m`) — формат
упакованного float (байт знака/экспоненты + 3 байта мантиссы).

Каждый gap-остров подтверждён ЖЁСТКО: старт совпадает с адресом загрузки
указателя `LXI H,<addr>`, а конец приходится ровно на начало следующей кодовой
функции (gap целиком = данные, кода внутри нет):

    data_exp_poly_coeffs      0x1823..0x1843 (33)  lxi h,1823h  -> end func_1844
    data_sin_atn_poly_coeffs  0x1901..0x191D (29)  lxi h,1901h/05/09 -> end func_tan
    data_atn_poly_coeffs      0x1958..0x197C (37)  lxi h,1958h в func_atn -> end func_peek

Семантика уже была в RDB: комментарий `func_atn` говорит `reads: "константы
0x1901/0x1958"`. Экспоненты ряда ATN монотонны (0x78,0x7B,0x7C,0x7D,0x7D,0x7E,
0x7E,0x7F) — признак полинома.

Не заводим (осознанно): `0x1783` (heavy 0xFF, ссылок нет — паддинг/резерв),
`0x2D7E` (16б арифм-таблица + код — нужен сплит), `0x2DDC` (самомодиф. — нужен
поведенческий трасс).

Использование:
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage14_data_tables.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage14_data_tables.py --apply
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
# kind = data. size = точная длина gap-блока (стыкуется со следующей функцией).
# Проверяем лидирующие байты по image перед --apply (защита от чужого ROM).
OBJECTS = [
    {
        "addr": 0x1823, "name": "data_exp_poly_coeffs", "kind": "data",
        "size": 33, "role": "exp_polynomial_coefficients",
        # 08 40 2E 94 — первый коэффициент; хвост 00 00 00 81 (ст. степень)
        "check": lambda img: img[0x1823:0x1827] == bytes([0x08, 0x40, 0x2E, 0x94]),
        "note": (
            "Ряд коэффициентов EXP. Указатель грузится `LXI H,1823h` (в `func_exp`, "
            "0x17E3) перед вызовом evaluator-а `func_1844`. Массив 4-байтных float; "
            "блок кончается ровно на `func_1844` (0x1844) — внутри только данные."),
        "props": {
            "record": "4-byte packed float (sign/exp + 3 mantissa)",
            "loaded_by": "lxi h,1823h (func_exp 0x17E3)",
            "consumer": "func_1844 (Horner series evaluator)"},
    },
    {
        "addr": 0x1901, "name": "data_sin_atn_poly_coeffs", "kind": "data",
        "size": 29, "role": "sin_atn_polynomial_coefficients",
        # DB 0F 49 81 — первый коэффициент
        "check": lambda img: img[0x1901:0x1905] == bytes([0xDB, 0x0F, 0x49, 0x81]),
        "note": (
            "Ряд коэффициентов SIN/ATN. Грузится `LXI H,1901h`, затем `LXI H,1905h`/"
            "`LXI H,1909h` — то есть 0x1905=0x1901+4 и 0x1909=0x1901+8 это отдельные "
            "4-байтные члены того же массива (нормировка/первый член ряда). Блок "
            "кончается ровно на `func_tan` (0x191E). RDB `func_atn` уже отмечает "
            "`reads: константа 0x1901`."),
        "props": {
            "record": "4-byte packed float",
            "loaded_by": "lxi h,1901h / 1905h / 1909h (func_sin/func_atn)",
            "consumer": "func_1844 / func_atn"},
    },
    {
        "addr": 0x1958, "name": "data_atn_poly_coeffs", "kind": "data",
        "size": 37, "role": "atn_polynomial_coefficients",
        # 09 4A D7 3B — первый; терминатор 7F 00 00 00 на 0x1978
        "check": lambda img: (img[0x1958:0x195C] == bytes([0x09, 0x4A, 0xD7, 0x3B])
                              and img[0x1978:0x197C] == bytes([0x7F, 0x00, 0x00, 0x00])),
        "note": (
            "Главный ряд коэффициентов ATN. Внутри `func_atn` (0x1933): "
            "`lbl_194e: LXI H,1958h / CALL func_1844`. Экспоненты членов монотонно "
            "растут (0x78,0x7B,0x7C,0x7D,0x7D,0x7E,0x7E,0x7F) с мантиссами `AA AA`/"
            "`00 00 00` — классический полином арктангенса. Блок кончается ровно на "
            "`func_peek` (0x197D). RDB `func_atn`: `reads: константы 0x1901/0x1958`."),
        "props": {
            "record": "4-byte packed float",
            "loaded_by": "lxi h,1958h in func_atn (lbl_194e)",
            "consumer": "func_1844 (Horner series evaluator)",
            "exponent_seq": "0x78..0x7F (monotonic)"},
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
            log.append("%s: %s ПРОПУЩЕН — лидирующие байты не совпали"
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
            print("план Stage 14 (float-ряды):")
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
