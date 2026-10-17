#!/usr/bin/env python3
"""Stage 6b: таблица пользовательских переменных, векторы, окно строк.

Дополняет карту RAM-интерпретатора (Stage 6) ячейками, которые автостарт-демо
не трогает (их нет в 46 рантайм-патчах), поэтому подтверждение — СТАТИЧЕСКОЕ
(инициализация в `main_loop`/boot + потребители) плюс ЖИВОЕ чтение значений
указателей в сессии отладчика.

Главный результат — ФОРМАТ таблицы переменных, доказанный разбором
`func_var_lookup` `0x0BCD` и аллокатора новой переменной `0x0C45..0x0C84`:
  * запись = 6 байт: [имя:2][значение:4]; шаг обхода `LXI D,0006` / `DAD D`;
  * имя — 1..2 буквы A..Z: первый символ через токен (`MVI A,BF / ADD B /
    CPI 1A`), второй через `SUI 41H / CPI 1A`; строковый тип по `$` (`CPI 24H`)
    ставит флаг в `var_type_flag` `0x0C8C`;
  * ВЕРШИНА таблицы (следующий свободный слот) = `var_free_limit` `0x0CB3`:
    при создании переменной `LHLD 0CB3` -> +6 (`LXI B,0006 / DAD B`) -> `SHLD
    0CB3` (`0x0C63..0x0C71`), запись обнуляется (`RST 20`). Это же — нижняя
    граница free (читает FRE). Живое значение в сессии: 0x0CB3 = 0x4303 ==
    program_end (`0x0C33` = 0x4303) => таблица пуста (демо без переменных).

DATA-указатель: отдельной ячейки НЕТ. `READ`/`DATA` идут по тексту через
`var_text_ptr`/`var_stmt_ptr`; `func_cmd_data` `0x0679` пропускает данные до
маркеров `:`/`"` (`LXI B,3A22`), `RESTORE` = перемотка к началу программы.
FOR-счётчики — не отдельная ячейка: 17-байтные блоки кладутся на стек `0x0625`
(`CALL 0x01E8`), рядом GOSUB-маркер `0x8C`.

Создаёт 4 объекта `variable`; обогащает комментарий/роль у 3 существующих
(без новых объектов). НЕ заводит `0x0C8B` (указатель значения текущей
переменной) — перекрывает `var_type_flag` `0x0C8C` (принцип «один объект на
адрес»); документируется здесь и в отчёте. `0x03E7` (cold-сентинел 0xFFFF,
пишется рядом со сбросом стека в `main_loop`, `SHLD 03E7`) — роль не доказана,
объект не создаём.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage6b_uservars.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage6b_uservars.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

# адрес -> новый объект kind=variable
OBJECTS = {
    0x0ED3: {
        "name": "var_string_window", "size": 2, "role": "string_window_ptr",
        "reads": ["FRE (`func_fre`: LHLD 0ED3)",
                  "строковые подпрограмки (`func_0f51`/`0fe9`/`lbl_0f73` LHLD 0ED3)"],
        "writes": ["`func_str_window` (SHLD 0ED3)",
                   "инициализация рядом с var_stmt_ptr (`label_01B0`)",
                   "`func_0fe9`/`label_0EF8` (SHLD 0ED3)"],
        "note": "ОКНО СТРОКОВОЙ АЛЛОКАЦИИ / базовый указатель временной строковой "
                "области (2б). Лежит чуть ниже var_free_top 0x0ED6. FRE вычисляет "
                "свободную память от него; str_window/0fe9 двигают окно. Инициали"
                "зируется в label_01B0 вместе с установкой var_stmt_ptr. Автостарт-"
                "демо строк не создаёт, поэтому в рантайм-диффе не участвует — роль "
                "подтверждена статически (инициализация + потребители).",
    },
    0x0609: {
        "name": "var_step_vector", "size": 2, "role": "step_routine_vector",
        "reads": ["трамплин `0x0608` (STA 0608 = 0xC3 JMP) целится сюда"],
        "writes": ["`main_loop 0x00F6`: LXI H,0619 / SHLD 0609",
                   "`func_prog_step` обновляет вектор шага"],
        "note": "ВЕКТОР ПОДСПРОГРАММЫ ШАГА СТРОКИ (2б). main_loop сеет адрес "
                "func_prog_step 0x0619; байт-опкод JMP (0xC3) кладётся в 0x0608, "
                "т.е. 0x0608..0x0609 — самомод-трамплин `JMP [0x0609]`. Держит "
                "адрес рутины продвижения к следующему оператору.",
    },
    0x05D1: {
        "name": "var_resume_vector", "size": 2, "role": "resume_routine_vector",
        "reads": ["трамплин `0x05D0` (STA 05D0 = 0xC3 JMP) целится сюда"],
        "writes": ["`main_loop 0x00FC`: LXI H,05E1 / SHLD 05D1",
                   "`label_05E1` (SHLD 05D1)"],
        "note": "ВЕКТОР ВОЗОБНОВЛЕНИЯ ИСПОЛНЕНИЯ (2б). main_loop сеет адрес 0x05E1; "
                "OPC JMP (0xC3) в 0x05D0 -> трамплин `JMP [0x05D1]`. Парный к "
                "var_step_vector: точка возврата/возобновления цикла исполнения.",
    },
    0x3559: {
        "name": "var_getput_ptr", "size": 2, "role": "get_put_work_ptr",
        "reads": ["обработчики GET/PUT (`label_348b`/`3498`/`34e9`/`36c0`/`3785` "
                  "lda/lhld 3559)"],
        "writes": ["парсер/вычисление блока GET/PUT (`34e9`/`3558`/`3574`/`35ab` "
                   "shld 3559)"],
        "note": "РАБОЧИЙ УКАЗАТЕЛЬ БЛОКА GET/PUT (2б). Хранит адрес/дескриптор "
                "прямоугольника graphics-областей для READ/PUT (GET `func_cmd_get` "
                "0x3441, PUT `func_cmd_put` 0x357f): читают и пишут метки 0x34xx/"
                "0x35xx. Демо рисует PLOT/COLOR, не вызывает GET/PUT -> в "
                "рантайм-диффе отсутствует; роль подтверждена статически.",
    },
}

# существующие объекты — обогатить роль/комментарий (НОВЫХ адресов НЕ заводим)
UPDATES = {
    0x0CB3: {
        "name": "var_free_limit",
        "role": "vartab_top_ptr",
        "note": "ВЕРШИНА ТАБЛИЦЫ ПЕРЕМЕННЫХ (vartab) = нижняя граница free (2б). "
                "Формат записи: 6 байт [имя:2][значение:4]; создание переменной в "
                "func_var_lookup: LHLD 0CB3 -> LXI B,0006 -> DAD B -> SHLD 0CB3 "
                "(0x0C63..0x0C71), обнуление записью (RST 20). Guard оценщика "
                "сравнивает стек с vartab (LHLD 0CB3/SUB L/JC 0069 = out-of-memory). "
                "FRE читает. ЖИВОЕ значение в сессии: 0x4303 == program_end (0x0C33="
                "0x4303) => таблица пуста (демо без переменных).",
    },
    0x0625: {
        "name": "var_stack_ptr",
        "role": "interpreter_stack_ptr",
        "note": "ВЕРШИНА СТЕКА ИНТЕРПРЕТАТОРА GOSUB/RETURN/FOR (2б). main_loop и "
                "CONT сеют 0xFFFF (LXI H,FFFF/SHLD 0625). На этом стеке лежат "
                "GOSUB-адреса (маркер 0x8C) и 17-байтные блоки FOR-счётчиков "
                "(создаются CALL 0x01E8) — отдельных ячеек под FOR нет. Живое "
                "значение пустого стека: 0xFFFF.",
    },
    0x0C8C: {
        "name": "var_type_flag",
        "role": "value_type_flag",
        "note": "ФЛАГ ТИПА ЗНАЧЕНИЯ строка/число (1б). func_var_lookup ставит 0 "
                "(число, XRA A/STA 0C8C) или 1 (строка по `$`, MVI A,01/STA 0C8C). "
                "LET/eval читают LDA 0C8C для строковой ветки. Парный старший байт "
                "0x0C8B = адрес значения текущей переменной (указатель слота); "
                "отдельным объектом НЕ заведён — перекрывает 0x0C8C (один объект на "
                "адрес).",
    },
}


def _ensure_kind(writer, session, addr, spec, log):
    """Создать/привести адрес к объекту kind=variable."""
    kind = "variable"
    name = spec["name"]
    size = spec.get("size")
    current = writer.exists(addr)
    ctype = (current or {}).get("type")
    cur_name = (current or {}).get("name")
    if not current or not current.get("address"):
        writer.ensure_object(addr, name, kind, size=size, rename=True)
        log.append("%s: СОЗДАН %s %s" % (addr_hex(addr), kind, name))
        return "create"
    if ctype != kind:
        session.call("debug_update_rdb_object",
                     {"address": addr, "name": name, "type": kind,
                      "size": to_addr(int(size if size is not None
                                          else (current.get("size") or 0)))})
        writer.actions.append({"kind": "retype", "tool": "debug_update_rdb_object",
                               "arguments": {"address": addr, "name": name,
                                             "type": kind}})
        log.append("%s: %s (%s) -> %s %s"
                   % (addr_hex(addr), cur_name, ctype, kind, name))
        return "retype"
    if size is not None:
        writer.ensure_object(addr, name, kind, size=size, rename=True)
    else:
        writer.ensure_object(addr, name, kind, rename=True)
    log.append("%s: %s -> %s" % (addr_hex(addr), cur_name, name))
    return "noop" if cur_name == name else "rename"


def plan(writer):
    """Превью: создаваемые объекты и обогащение существующих."""
    rows = []
    for addr, spec in OBJECTS.items():
        current = writer.exists(addr)
        ctype = (current or {}).get("type") or "нет"
        cur = (current or {}).get("name") or "—"
        if not current or not current.get("address"):
            kind = "create"
        elif ctype != "variable":
            kind = "retype"
        elif cur != spec["name"]:
            kind = "rename"
        else:
            kind = "noop"
        rows.append((addr, "CREATE", kind, cur, ctype, spec["name"]))
    for addr, spec in UPDATES.items():
        current = writer.exists(addr)
        ctype = (current or {}).get("type") or "нет"
        cur = (current or {}).get("name") or "—"
        rows.append((addr, "UPDATE", "comment", cur, ctype, spec["name"]))
    return rows


def apply(session, writer):
    log = []
    for addr, spec in OBJECTS.items():
        _ensure_kind(writer, session, addr, spec, log)
        writer.set_property(addr, "role", spec["role"])
        for key in ("params", "reads", "writes", "calls"):
            if key in spec:
                writer.set_property(addr, key, spec[key])
        writer.set_comment(addr, "%s — %s" % (spec["name"], spec["note"]))
    for addr, spec in UPDATES.items():
        if not writer.exists(addr):
            log.append("%s: ПРОПУСК (объект не найден для UPDATE)" % addr_hex(addr))
            continue
        writer.set_property(addr, "role", spec["role"])
        writer.set_comment(addr, "%s — %s" % (spec["name"], spec["note"]))
        log.append("%s: обновлён комментарий/роль %s" % (addr_hex(addr), spec["name"]))
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

    rdb_path = os.path.abspath(args.rdb)
    session, _cache = open_session(rom=args.rom, org=0x0000)
    try:
        info = session.call("debug_get_rdb_info")
        if os.path.abspath(info.get("path") or "") != rdb_path:
            raise SystemExit("RDB в сессии %r, ожидаем %r"
                             % (info.get("path"), args.rdb))
        writer = RdbWriter(session)
        print("план: %d новых + %d обновлений (Stage 6b)"
              % (len(OBJECTS), len(UPDATES)))
        if args.check:
            for addr, act, kind, cur, ctype, name in plan(writer):
                print("  %s %-6s [%-7s] %-22s (%-8s) -> %s"
                      % (addr_hex(addr), act, kind, cur, ctype, name))
            return 0
        for line in apply(session, writer):
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
