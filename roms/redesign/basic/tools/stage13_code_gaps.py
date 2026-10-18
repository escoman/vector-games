#!/usr/bin/env python3
"""Stage 13: закрыть подтверждённые CODE-дыры в RDB (3 функции, ~118 байт).

После Stage 12 осталось 42 `gap_XXXX`-блока на 1147 байт. Средний слой
разобран `debug_disassemble_range`/`debug_read_memory_range`. Большинство
блоков — это данные/паддинг/самомодиф-патчи или mis-decoded таблицы (кластер
0x17xx..0x19xx: `RST`/`0xFF`/`LXI SP`/_far_call вне образа — байт-суп, НЕ код).
Перевод их в `func_` был бы ложным.

Заводим РОВНО три блока, природа «функция» которых подтверждена (чистый
единичный вход, straight-line/достигнутый поток, корректные внешние вызовы):

    func_output_char_edit    0x0782..0x07AC  (43) формат/вывод символа: DAA/ORI F0, emit 0x0378
    func_relation_dispatch   0x0B12..0x0B39  (40) диспатч отношений: XTHL/XCHG, PCHL (выч. переход)
    func_selfmod_patch       0x366F..0x3691  (35) сборка трамплина: STA 3737<-C9/EB, CALL 372B

Подтверждения (лидирующие байты инструкции):

  * `func_output_char_edit` (0x0782) — вход `INX H / CALL 099E / DCX H / PUSH H
    / CALL 0531 / MVI A,20 / CALL 0378`; хвост `ORI F0 / DAA / CPI 60 / SBI 1F
    / JMP 0378` — классический BCD→ASCII вывод. Строка-источник `0x077E`.

  * `func_relation_dispatch` (0x0B12) — `ORI AF / PUSH PSW / CALL 09A1 / CALL
    0531 / XCHG / XTHL / CALL 14C3 / LXI H,0D97 / JNZ 0B35 / ... / PCHL`: жонглирует
    операндами (XTHL/XCHG) и уходит по вычисленному адресу (PCHL). Вход динамический
    (адрес из вычислителя), поэтому не покрыт CFG.

  * `func_selfmod_patch` (0x366F) — straight-line: `MOV A,M / INX H / ORA M ×3`,
    `MVI A,C9 / STA 3737`, `CALL 372B`, `CMA / STA 373A / STA 3740`,
    `MVI A,EB / STA 3737`. Патшит байты трамплина в 0x3737/373A/3740 (самомодиф.).

Использование:
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage13_code_gaps.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage13_code_gaps.py --apply
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
        "addr": 0x0782, "name": "func_output_char_edit", "kind": "function",
        "size": 43, "role": "output_char_edit",
        # INX H (23) — сдвиг курсора по входной строке
        "check": lambda img: img[0x0782] == 0x23,
        "note": (
            "Форматирование/вывод символа (BCD→ASCII). Вход `INX H / CALL 0x099E "
            "/ DCX H / PUSH H / CALL 0x0531 / MVI A,20 / CALL 0x0378 (emit)`; хвост "
            "`MOV B,A / RRC×4 / ORI F0 / DAA / CPI 60 / SBI 1F / JMP 0x0378`. "
            "Строка-источник 0x077E. Достигается через ветку, которую CFG от 0x0000 "
            "не прошёл (условный вызов редактора вывода)."),
        "props": {
            "emit_char": "0x0378",
            "helper": "0x0531, 0x099E",
            "src_string": "0x077E",
            "cfg_reachable": "no (branch not followed)"},
    },
    {
        "addr": 0x0B12, "name": "func_relation_dispatch", "kind": "function",
        "size": 40, "role": "relational_operator_dispatch",
        # ORI AF (F6) — установка признака операции
        "check": lambda img: img[0x0B12] == 0xF6,
        "note": (
            "Диспатч отношений (сравнение/присваивание). `ORI AF / PUSH PSW / CALL "
            "0x09A1 / CALL 0x0531 / POP PSW / XCHG / POP B / XTHL / XCHG / CALL "
            "0x14C3 / LXI H,0D97 / JNZ 0B35 / ANA|ORA D,E / PCHL` — жонглирует "
            "операндами (XTHL/XCHG) и уходит по вычисленному адресу (PCHL). Вход "
            "динамический (адрес из вычислителя), потому не покрыт CFG."),
        "props": {
            "dispatch": "PCHL (вычисленный переход)",
            "helper": "0x0531, 0x09A1, 0x14C3",
            "target_table": "0x0D97"},
    },
    {
        "addr": 0x366F, "name": "func_selfmod_patch", "kind": "function",
        "size": 35, "role": "selfmod_trampoline_patch",
        # XCHG (EB) — пролог
        "check": lambda img: img[0x366F] == 0xEB,
        "note": (
            "Самомодифицируемый сборщик трамплина. Straight-line: `MOV L,C / MOV H,B "
            "/ MOV A,M / INX H / ORA M ×3 / MOV L,A / MVI A,C9 / STA 0x3737 / CALL "
            "0x372B / CMA / STA 0x373A / STA 0x3740 / MVI A,EB / STA 0x3737 / XCHG`. "
            "Патшит байты (`C9`=RET, `EB`=JMP) в ячейки 0x3737/373A/3740 — пары с "
            "патч-областью 0x3730. Вход динамический."),
        "props": {
            "patch_cells": "0x3737, 0x373A, 0x3740",
            "patch_area": "0x3730 (residual gap)",
            "calls": "0x372B"},
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
            print("план Stage 13 (CODE-дыры):")
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
