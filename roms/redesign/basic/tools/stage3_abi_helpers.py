#!/usr/bin/env python3
"""Stage 3: ABI сквозных точек интерпретатора — именование + свойства + связи.

Документирует помощники, на которые опираются все обработчики Stage 2 (см.
`reports/Stage2.md`), и три ключевые сквозные точки из ТЗ: `func_putchar`
(символ → экран), `func_eval_expression` (указатель на текст → значение),
`func_var_lookup` (имя → слот переменной). Факты — из дизасма тел через
MCP-отладчик (`.scratch/dis.py`); адреса и имена не изобретаются, каждое
подтверждено телом функции и(или) местами вызова в `layout.asm`.

Для каждого объекта: создать/переименовать/переквалифицировать в `function`
(метка `lbl_*`/`label_*` → функция одним `debug_update_rdb_object`, чтобы не
потерять links/properties), затем записать `params`/`reads`/`writes`/`calls`/
`role`, комментарий и связи вызовов.

Открытый пункт (не выдумываем): контракт обработчиков **команд** не вскрыт —
диспетчер команд остаётся за Stage 5. Внутренние хвосты `0x0DF9`/`0x0DFF` не
плодим отдельными объектами (свёрнуты в `func_str_make`).

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage3_abi_helpers.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage3_abi_helpers.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

FAC = "FAC 0x404F..0x4052 (знак=404F bit7, экспонента=4050)"
TXTPTR = "текстовый указатель (HL, в page-zero 0x404D)"

# адрес -> {name, role, params, reads, writes, calls, calls_named, note}
HELPERS = {
    # === A. Сквозные точки интерпретатора (цель Stage 3) ===
    0x09B1: {
        "name": "func_eval_expression",
        "role": "evaluator_entry",
        "params": "HL = текстовый указатель на начало выражения",
        "reads": ["SP против 0x0CB3 (низ занятой памяти) — страховка от переполнения",
                  "поток токенов по HL"],
        "writes": [TXTPTR + " (двигается на конец разобранного выражения)",
                   FAC + " (значение выражения)"],
        "calls": ["CALL 0x0A43 func_eval_primary (ядро разбора)",
                  "JC 0x0069 (OUT OF MEMORY при нехватке стека)",
                  "падение в 0x09DD (реляционные операторы >0xAB)"],
        "calls_named": [(0x0A43, "func_eval_primary")],
        "note": "Точка входа оценщика выражений: страховка памяти (LHLD 0CB3 / "
                "DAD SP / JC 0069), вызов ядра 0x0A43, затем цепочка реляционных "
                "операторов. Хелперы Stage 2 зовут её, чтобы вычислить аргумент.",
    },
    0x0A43: {
        "name": "func_eval_primary",
        "role": "evaluator_core",
        "params": "HL = текстовый указатель",
        "reads": ["0x0C8C (флаг строковой зоны — сбрасывается на входе)",
                  "поток токенов/литералов по HL"],
        "writes": [TXTPTR, FAC],
        "calls": ["RST 0x10 (продвинуть указатель, следующий непробельный символ)",
                  "0x15A9 func_num_digitize (числовой литерал)",
                  "0x0ABF func_eval_ref (переменная/функция)",
                  "рекурсия на себя (бинарные операторы +,-,NOT,FN,^...)"],
        "calls_named": [(0x0ABF, "func_eval_ref")],
        "note": "Ядро оценщика: сброс строкового флага, разбор унарных/бинарных "
                "операторов и литералов (dispatch по диапазону токенов), рекурсия. "
                "Вызывается из func_eval_expression.",
    },
    0x0BCD: {
        "name": "func_var_lookup",
        "role": "variable_lookup",
        "params": "HL = текстовый указатель на имя переменной",
        "reads": ["(HL) — первый байт-токен имени (CPI 1A -> ошибка)",
                  "следующие символы имени: `$` (0x24), вторая буква A–Z, пробелы",
                  "0x0C8C (сбрасается)"],
        "writes": [TXTPTR + " (на конец имени)", "0x0C8C=0"],
        "calls": ["0x0074 func_error_stub (некорректное имя)",
                  "0x0BF5/0x0BFC/0x0C20 (разбор второго символа/модификатора)"],
        "calls_named": [(0x0074, "func_error_stub")],
        "note": "Разбор имени переменной по (HL): кодировка буквы, `$`/"
                "целочисленный модификатор, опциональная вторая буква → поиск/создание "
                "слота. Одна из трёх сквозных точек ТЗ.",
    },
    0x0ABF: {
        "name": "func_eval_ref",
        "role": "reference_eval",
        "params": "HL = указатель на токен переменной/функции",
        "reads": ["0x0C8C (флаг: строка/число)", "0x404D (текстовый указатель)"],
        "writes": ["0x404D (продвинут за аргумент)", "FAC (значение переменной)"],
        "calls": ["CALL 0x0BCD func_var_lookup",
                  "CALL 0x09B1 func_eval_expression (аргумент функции/скобка)",
                  "JMP 0x0B09 func_exec_dispatch (встройка по индексу токена)"],
        "calls_named": [(0x0BCD, "func_var_lookup"), (0x09B1, "func_eval_expression")],
        "note": "Ветка оценщика «ссылка на переменную или встроенную функцию»: "
                "var_lookup для идентификатора, иначе вычислительный прыжок в "
                "таблицу функций (0x0B09). Была меткой lbl_0abf.",
    },
    0x1C95: {
        "name": "func_putchar",
        "role": "output_char",
        "params": "A = код символа для вывода",
        "reads": [],
        "writes": ["экран/терминал через 0x3E9F"],
        "calls": ["MOV C,A (переложить код)", "PUSH/POP B (сохранить BC)",
                  "CALL 0x3E9F func_term_putc"],
        "calls_named": [(0x3E9F, "func_term_putc")],
        "note": "Вывод одного символа: код в A→C, сохранение BC, вызов "
                "терминального бэкенда 0x3E9F. Его зовёт печатающая петля 0x00A1 "
                "(строка до bit7) и boot-сообщения. Одна из трёх точек ТЗ.",
    },
    0x3E9F: {
        "name": "func_term_putc",
        "role": "output_char_backend",
        "params": "C = код символа (маскируется 0x7F)",
        "reads": ["0x402E (состояние терминала)"],
        "writes": ["символьный экран/курсор (область BIOS 0x3EXX)"],
        "calls": ["EI; PUSH PSW/B/D/H (полное сохранение регистров)"],
        "calls_named": [],
        "note": "Низкоуровневый вывод символа C в терминал (аппаратный бэкенд "
                "putchar). Лежит в области драйвера экрана, вызывается из func_putchar.",
    },

    # === B. Числовой путь / FAC ===
    0x0531: {
        "name": "func_fac_require_int",
        "role": "fac_integer_guard",
        "params": "FAC (ожидаемое целое)",
        "reads": ["0x4050 (экспонента) — CPI 0x91"],
        "writes": [],
        "calls": ["JC 0x152A (преобразовать дробное к целому)",
                  "MVI E,08 / JMP 0x0083 func_error_raise (INT REQUIRED)"],
        "calls_named": [(0x0083, "func_error_raise")],
        "note": "Требовать целое во FAC (экспонента < 0x91), иначе ошибка 08. "
                "Используют PEEK/USR (eval числа → адрес).",
    },
    0x10CA: {
        "name": "func_fac_require_byte",
        "role": "fac_byte_arg",
        "params": "HL = текстовый указатель на число",
        "reads": ["0x4050/0x4051 (младший байт значения FAC)"],
        "writes": [TXTPTR],
        "calls": ["CALL 0x052D (eval → целое в DE)", "ORA D / JNZ 0x0539 "
                  "(диапазон 0..255, иначе ошибка)", "RST 0x10 (продвинуть указатель)"],
        "calls_named": [],
        "note": "Вычислить числовое выражение → байт в A с проверкой диапазона. "
                "Используют INP/POINT/CHR$. Была меткой label_10CA.",
    },
    0x1493: {
        "name": "func_fac_store_int",
        "role": "fac_store",
        "params": "A = значение, B = шкала экспоненты (0x98 целое, 0x90/0x91 прочие)",
        "reads": [],
        "writes": ["0x4050=B (экспонента)", "0x4051 (мантисса/знак)", "0x404F (знак)"],
        "calls": ["LXI H,0x4050 / MOV M,B", "JMP 0x1183 func_fac_normalize"],
        "calls_named": [(0x1183, "func_fac_normalize")],
        "note": "Записать целое (A) во FAC с указанной шкалой (B) и нормализовать. "
                "Общий return-хвост 0x0D95 для POS/INP/PEEK/POINT/LEN/ASC и `&`.",
    },
    0x1183: {
        "name": "func_fac_normalize",
        "role": "fac_normalize",
        "params": "FAC (мантисса/экспонента)",
        "reads": ["0x4050 (экспонента)"],
        "writes": ["0x4050=0 (underflow → FAC := 0)", "FAC (нормализованный)"],
        "calls": ["CC 0x1245 (хвост нормализации)", "XCHG"],
        "calls_named": [],
        "note": "Нормализация FAC; при уходе экспоненты обнуляет 0x4050 (число → 0).",
    },
    0x14AB: {
        "name": "func_fac_continuation",
        "role": "fac_trampoline",
        "params": "FAC + 0x404D (текстовый указатель)",
        "reads": ["0x404D", "0x404F (знак FAC)"],
        "writes": ["стек (пуш FAC/текста)", "0x14B8/0x14B9 (самопатч JMP-адреса)"],
        "calls": ["XTHL/SHLD 0x14B9", "PUSH H", "JMP 0x0000 (сапомодифицируемый трамплин)"],
        "calls_named": [],
        "note": "Самый горячий хелпер (12 вызовов): сохранить FAC и текст в стек и "
                "перехватить продолжение через self-modified JMP в 0x14B8. Используют "
                "EXP/SIN/COS/TAN/ATN/SQR/RND/STR$/VAL.",
    },
    0x14BB: {
        "name": "func_fac_fetch_operand",
        "role": "fac_operand_load",
        "params": "HL = указатель на inline 4-байтный операнд (константу)",
        "reads": ["4 байта по HL (манистсса+экспонента константы)"],
        "writes": ["0x404D (текстовый указатель за операнд)", "0x404F (FAC)"],
        "calls": ["MOV E,M/INX H... (загрузка 4 байт)", "SHLD 0x404D / SHLD 0x404F"],
        "calls_named": [],
        "note": "Загрузить inline-константу из потока программы во FAC и сдвинуть "
                "текстовый указатель. Хвост 0x14C3. Используют SQR (0.5), возведение в "
                "степень.",
    },
    0x15A8: {
        "name": "func_num_digitize",
        "role": "number_parser",
        "params": "HL = текстовый указатель на числовой литерал",
        "reads": ["символы: знак (+/-), цифры 0-9, экспонента"],
        "writes": ["0x4050 (экспонента FAC)", "0x4060 (накопитель мантиссы)",
                   "0x00AE/0x00B0/0x00B1 (флаги разбора)", TXTPTR],
        "calls": ["RST 0x10 (следующий символ)", "0x1631/0x15F3/0x15BF (ветки "
                  "цифры/точки/экспоненты)"],
        "calls_named": [],
        "note": "Парсер числового литерала из текста → FAC (знак, цифры, порядок). "
                "Его зовёт VAL (CALL 15A8) и func_eval_primary. Был меткой label_15A8.",
    },

    # === C. Строковый путь ===
    0x0E65: {
        "name": "func_str_make",
        "role": "string_descriptor_build",
        "params": "A = длина (dim)",
        "reads": [],
        "writes": ["0x4049 (dim)", "0x404B (data-ptr через хвост 0x0DF9)"],
        "calls": ["CALL 0x0ECE func_str_window (выделение)",
                  "LXI H,0x4049 / MOV M,A", "хвост 0x0DF9 (записать DE как data-ptr)"],
        "calls_named": [(0x0ECE, "func_str_window")],
        "note": "Собрать строковый дескриптор: dim в 0x4049, data-ptr в 0x404B "
                "(внутренний хвост 0x0DF9/0x0DFF — не отдельные объекты). CHR$/INKEY$.",
    },
    0x0E97: {
        "name": "func_str_return",
        "role": "string_return",
        "params": "0x4049 (дескриптор), 0x0F07 (указатель аллокации строк)",
        "reads": ["0x4049", "0x0F07", "0x404F (проверка RST 0x20)"],
        "writes": ["0x404D (текстовый указатель)", "0x0F07 (сдвиг аллокации)",
                   "0x0C8C=1 (флаг временной строки)"],
        "calls": ["LHLD 0x0F07 / SHLD 0x404D", "STA 0x0C8C=1", "CALL 0x18AA",
                  "RST 0x20 (сверка)", "MVI E,1E / JZ 0x0083 (переполнение строки)"],
        "calls_named": [(0x0083, "func_error_raise")],
        "note": "Вернуть временную строку как результат выражения: обновить указатель "
                "аллокации 0x0F07, текстовый 0x404D, флаг 0x0C8C. CHR$/STR$/LEFT$/"
                "RIGHT$/MID$/INKEY$. Был меткой label_0E97 (8 ссылок).",
    },
    0x0ECE: {
        "name": "func_str_window",
        "role": "string_alloc_window",
        "params": "A = требуемая длина",
        "reads": ["0x0ED3/0x0ED6 (границы строковой зоны)"],
        "writes": ["0x0ED3 (окно строки)", "стек (RST 0x20)"],
        "calls": ["RST 0x20 (сравнение границы)", "JC 0x0EE9 (OUT OF MEMORY/сборка)",
                  "SHLD 0x0ED3"],
        "calls_named": [],
        "note": "Выделить и заокнировать окно под строку заданной длины в "
                "строковой зоне (0x0ED3/0x0ED6). Зовёт func_str_make.",
    },
    0x09A1: {
        "name": "func_str_flush_guard",
        "role": "string_flush_guard",
        "params": "0x0C8C (флаг незавершённой временной строки)",
        "reads": ["0x0C8C"],
        "writes": [],
        "calls": ["ORA A / RZ (ничего нет — быстрый выход)",
                  "JMP 0x1E6D (финализировать временную строку)"],
        "calls_named": [],
        "note": "Гард: если есть незавершённая временная строка (0x0C8C<>0) — "
                "доделать её перед операцией. 4 вызова в eval-пути.",
    },

    # === D. Page-zero RST-векторы и обработка ошибок ===
    0x0008: {
        "name": "func_rst_fetch_sep",
        "role": "rst_get_token",
        "params": "RST 1; HL = текстовый указатель",
        "reads": ["(HL), XTHL, CMP M (сверить ожидаемый символ)"],
        "writes": [TXTPTR],
        "calls": ["JNZ 0x0074 func_error_stub (разделитель не совпал)",
                  "fall-through в RST 2 (0x0010)"],
        "calls_named": [(0x0010, "func_rst_advance_text"), (0x0074, "func_error_stub")],
        "note": "RST 1 (0x0008): прочитать/сверить разделитель из потока токенов; при "
                "совпадении падает в RST 2 (продвинуть указатель).",
    },
    0x0010: {
        "name": "func_rst_advance_text",
        "role": "rst_advance_ptr",
        "params": "RST 2; HL = текстовый указатель",
        "reads": ["(HL) — следующий непробельный символ"],
        "writes": [TXTPTR],
        "calls": ["INX H / CPI 3A (':' — конец строки) / RNC", "CPI 20 (пробел) / JZ 0x0010"],
        "calls_named": [],
        "note": "RST 2 (0x0010): продвинуть текстовый указатель на следующий "
                "непробельный символ; возвращает его в A с признаком диапазона.",
    },
    0x0020: {
        "name": "func_rst_cmp_dehl",
        "role": "rst_compare",
        "params": "RST 4; HL и DE",
        "reads": ["H/L против D/E"],
        "writes": ["флаги (Z = HL==DE)"],
        "calls": ["MOV A,H / SBB D / RNZ / ORA L / SBB E / RET"],
        "calls_named": [],
        "note": "RST 4 (0x0020): сравнить HL с DE, выставить Z (равенство). Сверка "
                "границ строки/окна.",
    },
    0x0028: {
        "name": "func_rst_fac_sign",
        "role": "rst_fac_test",
        "params": "RST 5; FAC",
        "reads": ["0x4050 (экспонента)", "0x404F (знак)"],
        "writes": ["A (0 = положительно, 0xFF = отрицательно)"],
        "calls": ["ORA A / RZ (FAC==0)", "RAL / SBB A / RNZ / INR A"],
        "calls_named": [],
        "note": "RST 5 (0x0028): тест знака/нуля FAC. RZ если FAC=0; A=0 для "
                "положительного, 0xFF для отрицательного. Зовут арифметики и ABS/SGN.",
    },
    0x0038: {
        "name": "func_rst_irq",
        "role": "rst_irq_jump",
        "params": "RST 7 (вектор прерывания)",
        "reads": [],
        "writes": [],
        "calls": ["JMP 0x2C7F (VBlank/IRQ тикер — область Stage 4)"],
        "calls_named": [],
        "note": "RST 7 (0x0038): переход к обработчику прерываний 0x2C7F (смена стека "
                "на 0x26F7, счётчик тиков 0x3A1F, OUT 00/IN 01). Подробный разбор — "
                "Stage 4 (прерывания).",
    },
    0x0074: {
        "name": "func_error_stub",
        "role": "error_not_implemented",
        "params": "(нет; fall-through/вызов при синтаксической ошибке)",
        "reads": [],
        "writes": ["0x03E7=0 (MVI E,02 / XRA A / STA 03E7)"],
        "calls": ["генерирует код ошибки 02"],
        "calls_named": [],
        "note": "Page-zero заглушка «не реализовано»/синтаксическая ошибка (запись AT "
                "в таблице функций; сюда ведут JC/JNZ из RST и var_lookup). Была меткой.",
    },
    0x0083: {
        "name": "func_error_raise",
        "role": "error_raise",
        "params": "E = код ошибки (08 INT, 16 OOM, 1A SUBSCRIPT, 1E STRING)",
        "reads": ["E (код)"],
        "writes": ["состояние ошибки/стоп интерпретатора"],
        "calls": ["MVI E,nn / JMP 0x0083 (стандартный шаблон RaiseError)"],
        "calls_named": [],
        "note": "Единая точка поднятия ошибки: вызывающий грузит E=код и прыгает сюда. "
                "Коды подтверждены в телах Stage 2. Была меткой.",
    },
}


def _ensure_function(writer, session, addr, name, log):
    """Создать/переименовать/переквалифицировать адрес в `function`. Возвращает действие."""
    current = writer.exists(addr)
    ctype = (current or {}).get("type")
    cur_name = (current or {}).get("name")
    if not current or not current.get("address"):
        writer.ensure_object(addr, name, "function", size=0, rename=True)
        action = "create"
        log.append("%s: СОЗДАНА функция %s" % (addr_hex(addr), name))
    elif ctype and ctype not in ("function", "code"):
        session.call("debug_update_rdb_object",
                     {"address": addr, "name": name, "type": "function",
                      "size": to_addr(int((current or {}).get("size") or 0))})
        writer.actions.append({"kind": "retype", "tool": "debug_update_rdb_object",
                               "arguments": {"address": addr, "name": name,
                                             "type": "function"}})
        action = "retype"
        log.append("%s: %s (%s) -> функция %s"
                   % (addr_hex(addr), cur_name, ctype, name))
    else:
        writer.ensure_object(addr, name, "function", size=0, rename=True)
        action = "noop" if cur_name == name else "rename"
        log.append("%s: %s -> %s" % (addr_hex(addr), cur_name, name))
    return action


def plan():
    """Что инструмент сделает с каждым адресом (для --check/превью)."""
    return {addr: h["name"] for addr, h in HELPERS.items()}


def apply(session, writer):
    log = []
    for addr, h in HELPERS.items():
        _ensure_function(writer, session, addr, h["name"], log)
        writer.set_property(addr, "role", h["role"])
        writer.set_property(addr, "params", h["params"])
        writer.set_property(addr, "reads", h["reads"])
        writer.set_property(addr, "writes", h["writes"])
        writer.set_property(addr, "calls", h["calls"])
        writer.set_comment(addr, "%s — %s" % (h["name"], h["note"]))
        for target, _tname in h["calls_named"]:
            writer.add_link(addr, target)
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
        print("план: %d сквозных объектов" % len(HELPERS))
        if args.check:
            for addr, name in sorted(plan().items()):
                current = writer.exists(addr)
                ctype = (current or {}).get("type") or "нет"
                cur = (current or {}).get("name") or "—"
                kind = ("create" if (current or {}).get("address") is None
                        else "retype" if ctype not in ("function", "code")
                        else "rename" if cur != name else "noop")
                print("  %s [%-6s] %s (%s) -> %s"
                      % (addr_hex(addr), kind, cur, ctype, name))
            return 0
        if not args.apply:
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
