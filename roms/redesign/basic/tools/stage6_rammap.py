#!/usr/bin/env python3
"""Stage 6: карта RAM-интерпретатора (служебные ячейки `var_*`).

Переносит спеку v2.5 (docs/vector_techinfo.md §15) в ПОДТВЕРЖДЁННУЮ на этом ROM
карту переменных BASIC 2.997. Каждая ячейка закрепляется как объект `variable`
(`var_*`) с размером, ролью и комментарием — это фундамент EQU-переносимости
(Stage 11). Двойное подтверждение:

1. **Статика (boot + контекст).** `func_boot_init` `0x19CC` расставляет
   указатели: `LHLD 0026 / SHLD 3F21` (база программы из page-zero монитора),
   `LXI H,7FFE/SHLD 0EF6`, `LXI H,7FCC/SHLD 0ED6`, `LXI H,804F/SHLD 3DFC/3DFE`,
   `MVI A,2C/STA 3F76`. Подыннициализатор `0x07BC` обнуляет `0x038A`. Роли
   уточнены по тому, КАКИЕ функции читают/пишут каждую ячейку (STOP/CONT/NEW/
   LET/FRE/eval/PLOT/PLAY).

2. **Динамика (рантайм-дифф, ТЗ §13).** `memory_diff.json` пайплайна сравнивает
   образ (область переменных = нули) с RAM после исполнения: 46 изменений.
   Ячейки, ставшие правдоподобными RAM-адресами (0x3F21->0x4301, 0x0CB3->0x4303,
   0x404F->..., 0x3769->0x0F), — подтверждённые ПЕРЕМЕННЫЕ. Часть «патчей» —
   это САМОМОД-код (0x19F3 CD->21, 0x2C97, 0x15D6, 0x4086, 0x32xx AF->00), их
   В переменные не заводим.

Расхождение со спекой. Образ грузится в `0x0000` и заменяет знакогенератор,
поэтому карта v2.5 «знакоместо 0..639, таймер 768..770, сдвиг 771, счётчики
772..775» (это page-zero МОНИТОРА свежей машины) к данному ROM неприменима
директно: здесь workspace — high-RAM `0x3DFC..0x42FF` + scattered page-zero.
Из спеки подтверждён только диапазон базы программы ~`0x4300` (§15.2): рантайм
даёт `var_program_base=0x4301`, `var_program_end/var_free_limit=0x4303`.

Не классифицированы (роль не доказана, объект НЕ создаём): 0x03E7, 0x086C,
0x0F07-adj, 0x2D04/0x2D07/0x2D0B, 0x3A1F, 0x3D8D. Ячейка монитора 0x0026
(читается один раз в boot) документируется, объект не заводится.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage6_rammap.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage6_rammap.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

# адрес -> описание объекта-переменной. kind всегда "variable".
OBJECTS = {
    # ===== Программа и исполнение =====
    0x3F21: {
        "name": "var_program_base", "size": 2, "role": "program_base_ptr",
        "reads": ["адрес загрузки из page-zero монитора (`LHLD 0026` в boot)"],
        "writes": ["база программы в high-RAM (`SHLD 3F21` в boot)"],
        "note": "BAЗA ПРОГРАММЫ — указатель на начало строк (2б). boot: LHLD 0026 / "
                "SHLD 3F21. NEW/скан/LIST читают (LHLD x8). рантайм-дифф: 00 00 -> "
                "01 43 (=0x4301) => high-RAM ~0x4300, совпадает со спекой v2.5 §15.2.",
    },
    0x0464: {
        "name": "var_stmt_ptr", "size": 2, "role": "current_stmt_ptr",
        "reads": ["текущая исполняемая команда (цикл диспетчера, CONT)"],
        "writes": ["STOP/LET/NEXT сохраняют позицию выполнения"],
        "note": "УКАЗАТЕЛЬ ТЕКУЩЕЙ КОМАНДЫ (2б). STOP пишет, CONT/диспетчер читают; "
                "LET/NEXT обновляют. рантайм-дифф: 00 00 -> 80 3F (=0x3F80, в область "
                "текста/программы).",
    },
    0x0625: {
        "name": "var_stack_ptr", "size": 2, "role": "interpreter_stack_ptr",
        "reads": ["GOSUB возвращает по стеку"],
        "writes": ["main_loop/CONT сбрасывают вершину стека"],
        "note": "ВЕРШИНА СТЕКА ИНТЕРПРЕТАТОРА GOSUB/RETURN/FOR (2б). main_loop и CONT "
                "сбрасывают, GOSUB читает/пишет. рантайм-дифф: 00 00 -> FF FF (пустой "
                "стек = верх памяти).",
    },
    0x0C30: {
        "name": "var_scan_ptr", "size": 2, "role": "line_scan_ptr",
        "reads": ["LIST/обход строк, высвобождение"],
        "writes": ["резюме построчного скана"],
        "note": "КУРСОР ПОСТРОЧНОГО СКАНА (2б). Используется при обходе/List и "
                "высвобождении строк. рантайм-дифф: 00 00 -> 03 43 (=0x4303).",
    },
    0x0C33: {
        "name": "var_program_end", "size": 2, "role": "program_end_ptr",
        "reads": ["NEW/CLEAR устанавливают конец", "prog_line_insert расширяет"],
        "writes": ["адрес после последней строки"],
        "note": "КОНЕЦ ПРОГРАММЫ (адрес после последней строки) (2б). NEW/CLEAR задают, "
                "вставка строки (prog_line_insert) сдвигает. рантайм-дифф: -> 0x4303 "
                "(=base+2, пустая программа с маркером конца).",
    },

    # ===== Оценщик и вычисления =====
    0x404D: {
        "name": "var_text_ptr", "size": 2, "role": "text_stream_ptr",
        "reads": ["RST 1/RST 2 сдвигают поток токенов"],
        "writes": ["оценщик/LET/команды передвигают указатель"],
        "note": "ГЛАВНЫЙ ТЕКСТОВЫЙ УКАЗАТЕЛЬ потока токенов (2б, ~30 обращений "
                "lhld/shld). RST 1 (сверка разделителя) и RST 2 (продвинуть на "
                "непробел) работают через него.",
    },
    0x404F: {
        "name": "var_fac", "size": 4, "role": "floating_accumulator",
        "reads": ["IF/PRINT/арифметика читают значение"],
        "writes": ["eval/LET/операции пишут результат"],
        "note": "ПЛАВАЮЩИЙ АККУМУЛЯТОР FAC (4б, 0x404F..0x4052). Центр арифметики: "
                "eval пишет, IF читает 0x4050 (истина). рантайм-дифф: 0x4050 -> 81 80 "
                "(знак/младшие байты значения).",
    },
    0x09CD: {
        "name": "var_eval_temp_ptr", "size": 2, "role": "eval_temp_ptr",
        "reads": ["eval/primary читают сохранённый"],
        "writes": ["eval_expression SHLD 09CD"],
        "note": "ВРЕМЕННЫЙ УКАЗАТЕЛЬ ОЦЕНЩИКА (2б). func_eval_expression `0x09B1` "
                "сохраняет сюда позицию (SHLD 09CD); далее читают первичные/операции. "
                "рантайм-дифф: -> 0x3F7E (в буфер ввода).",
    },
    0x0F45: {
        "name": "var_binop_operand", "size": 2, "role": "binop_operand_ptr",
        "reads": ["подпрограммы бинарных операций (LHLD)"],
        "writes": ["диспетчер операций `0x09DD` (SHLD 0F45)"],
        "note": "ОПЕРАНД/УКАЗАТЕЛЬ ПОДПРОГРАММЫ БИНАРНОЙ ОПЕРАЦИИ (2б). Диспетчер "
                "оценщика `0x09DD` (SUI AB -> индекс) пишет 0x0F45; операции читают. "
                "рантайм-дифф: -> 0x3F7E.",
    },
    0x0C8C: {
        "name": "var_type_flag", "size": 1, "role": "value_type_flag",
        "reads": ["LET/eval/высвобождение строк (LDA 0C8C)"],
        "writes": ["оценщик при различении строка/число"],
        "note": "ФЛАГ ТИПА ЗНАЧЕНИЯ строка/число (1б). LET и оценщик читают LDA 0C8C "
                "для ветки строковой конкатенации (-> 0x1E6D).",
    },
    0x0F07: {
        "name": "var_string_ptr", "size": 2, "role": "string_work_ptr",
        "reads": ["func_str_return / 0fe9 (LHLD)"],
        "writes": ["строковые подпрограмки (SHLD)"],
        "note": "РАБОЧИЙ УКАЗАТЕЛЬ СТРОКИ (2б). Строковые функции (func_str_return, "
                "func_0fe9) сохраняют/восстанавливают его. рантайм-дифф: -> 0x403D.",
    },

    # ===== Память / границы =====
    0x0CB3: {
        "name": "var_free_limit", "size": 2, "role": "free_space_limit",
        "reads": ["FRE читает границу", "guard eval: LHLD 0CB3 / SUB L / JC 0069"],
        "writes": ["NEW/CLEAR/работа со строками обновляют"],
        "note": "НИЖНЯЯ ГРАНИЦА СВОБОДНОЙ ПАМЯТИ / порог out-of-memory (2б). Функция "
                "FRE читает; guard оценщика сравнивает стек с ней (JC 0069). рантайм: "
                "-> 0x4303 (=конец программы).",
    },
    0x0EF6: {
        "name": "var_mem_top", "size": 2, "role": "mem_upper_bound",
        "reads": ["проверки свободной памяти"],
        "writes": ["boot: LXI H,7FFE / SHLD 0EF6"],
        "note": "ВЕРХНЯЯ ГРАНИЦА ПАМЯТИ (2б). boot сеет 0x7FFE. рантайм-дифф: -> 7FFE.",
    },
    0x0ED6: {
        "name": "var_free_top", "size": 2, "role": "memory_top_ptr",
        "reads": ["аллокация строк/темп"],
        "writes": ["boot: LXI H,7FCC / SHLD 0ED6"],
        "note": "ВЕРХ ОБЛАСТИ АЛЛОКАЦИИ (2б). boot сеет 0x7FCC (чуть ниже mem_top). "
                "рантайм-дифф: -> 7FCC.",
    },
    0x3DFC: {
        "name": "var_string_alloc_ptr", "size": 4, "role": "string_alloc_ptr",
        "reads": ["строки/темппы Allocate"],
        "writes": ["boot: LXI H,804F / SHLD 3DFC / SHLD 3DFE"],
        "note": "УКАЗАТЕЛЬ АЛЛОКАЦИИ СТРОК/ТЕМП (0x3DFC..0x3DFF, 4б: два смежных "
                "слова). boot сеет оба 0x804F. рантайм-дифф: -> 4F 80 4F 80.",
    },

    # ===== Ввод / текст =====
    0x3F76: {
        "name": "var_input_delim", "size": 1, "role": "input_delimiter",
        "reads": ["разбор разделителей строки ввода"],
        "writes": ["boot: MVI A,2C / STA 3F76"],
        "note": "РАЗДЕЛИТЕЛЬ/ПЕРВЫЙ БАЙТ БУФЕРА ВВОДА (1б). boot сеет запятую `2C`. "
                "рантайм-дифф: 00 -> 2C.",
    },
    0x3F77: {
        "name": "var_input_buffer", "size": 16, "role": "input_line_buffer",
        "reads": ["REPL/токенизатор наполняют"],
        "writes": ["отредактированная строка/токены (0x3F77..)"],
        "note": "БУФЕР ОТРЕДАКТИРОВАННОЙ СТРОКИ ВВОДА/ТОКЕНОВ (16б, 0x3F77..). Сюда "
                "пишется токенизированная команда. рантайм-дифф: 0x3F78 -> '15,0,1:' "
                "+ 80, 0x3F83 -> 'CLS' (автостарт-демо) — подтверждает назначение.",
    },
    0x038A: {
        "name": "var_print_column", "size": 1, "role": "print_column",
        "reads": ["путь вывода символа (0x028f/0346/037f)"],
        "writes": ["инкремент колонки; boot-подыннициализатор 0x07BC обнуляет"],
        "note": "КОЛОНКА ПЕЧАТИ/КУРСОРА (1б). 0x07BC: XRA A / STA 038A (сброс в 0 на "
                "старте); вывод символа сдвигает колонку.",
    },

    # ===== Графика (состояние подсистем 5d) =====
    0x3769: {
        "name": "var_color_current", "size": 1, "role": "current_color",
        "reads": ["PLOT/PAINT (LDA 3769) берут текущий цвет"],
        "writes": ["COLOR/граф-команды задают"],
        "note": "ТЕКУЩИЙ ЦВЕТ РИСОВАНИЯ (1б). Читают PLOT/PAINT (LDA 0x3769). "
                "рантайм-дифф: 00 -> 0F (=15) — автостарт COLOR15.",
    },
    0x2B56: {
        "name": "var_graph_xy", "size": 2, "role": "graph_coords",
        "reads": ["PLOT/LINE/CIRCLE читают координаты (lhld/lda)"],
        "writes": ["парсер координат `0x28A0` -> STA 2B56/2B57"],
        "note": "РАБОЧИЕ КООРДИНАТЫ X,Y ГРАФИКИ (2б: 0x2B56=X, 0x2B57=Y). PLOT/LINE/"
                "CIRCLE кладут сюда разобранные координаты (STA 2B56 / STA 2B57); "
                "читается и как слово (LHLD), и побайтно.",
    },
    0x30B4: {
        "name": "var_circle_color", "size": 1, "role": "circle_color",
        "reads": ["драйвер дуги при отрисовке"],
        "writes": ["func_cmd_circle: CALL 0x10C3 -> STA 30B4"],
        "note": "ЦВЕТ ОКРУЖНОСТИ/ДУГИ (1б). func_cmd_circle `0x3033` вычисляет цвет "
                "(CALL 0x10C3) и сохраняет в 0x30B4.",
    },
    0x4028: {
        "name": "var_paint_field", "size": 1, "role": "paint_color",
        "reads": ["заливка использует как целевое значение"],
        "writes": ["func_cmd_paint: LDA 0x3769 / STA 4028"],
        "note": "ЦВЕТ/ЗНАЧЕНИЕ ЗАЛИВКИ PAINT (1б). func_cmd_paint `0x20B1` копирует "
                "текущий цвет (LDA 3769) в 0x4028 перед flood-заливкой.",
    },

    # ===== Звук (PLAY, состояние 5d) =====
    0x27C8: {
        "name": "var_play_active", "size": 1, "role": "play_active_flag",
        "reads": ["драйвер ВBlank проверяет активность"],
        "writes": ["func_cmd_play: XRA A / STA 27C8 при старте"],
        "note": "ФЛАГ АКТИВНОСТИ PLAY (1б). func_cmd_play `0x2428` сбрасывает "
                "(XRA A/STA 27C8) при инициализации списка нот; проигрывание идёт на "
                "прерывании ВBlank (ТЗ п.63/65/74).",
    },
    0x245F: {
        "name": "var_play_pos", "size": 1, "role": "play_position",
        "reads": ["драйвер продвигает курсор"],
        "writes": ["func_cmd_play: XRA A / STA 245F при старте"],
        "note": "ПОЗИЦИЯ/КУРСОР ВОСПРОИЗВЕДЕНИЯ PLAY (1б). func_cmd_play сбрасывает "
                "(STA 245F) вместе с 0x27C8 при старте списка нот.",
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
    """Что инструмент сделает с каждым адресом (для --check/превью)."""
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
        rows.append((addr, kind, cur, ctype, spec))
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
        print("план: %d объектов Stage 6" % len(OBJECTS))
        if args.check:
            for addr, kind, cur, ctype, spec in plan(writer):
                print("  %s [%-6s] size=%s %-24s (%-8s) -> variable %s"
                      % (addr_hex(addr), kind, spec.get("size"), cur, ctype,
                         spec["name"]))
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
