#!/usr/bin/env python3
"""Stage 5a: архитектура интерпретатора — диспетчер команд + ядро REPL + операторы.

Закрывает открытый пункт Stage 2: **диспетчер команд** (исполнение операторов
`0x80..0xAD`). В отличие от диспетчера ФУНКЦИЙ (`func_exec_dispatch` `0x0B09`,
таблица `0x2770`), команды исполняются **самомодифицируемым индексным переходом**:
```
0x04AC  ADD A        ; A = 2*token (carry = бит7 -> token<0x80 = идентификатор)
0x04AD  JNC 0691     ; токен без флага команды -> путь присваивания (LET)
...      ; проверки диапазона (CPI 3A / CPI 94 / SUI 5A)
0x04BD  STA 04C1     ; младший байт адреса LHLD <- A   (самомодификация)
0x04C0  LHLD 2700    ; HL = word из data_cmd_table[0x2700 + (token-0x80)*2]
```
т.е. смещение = (токен - 0x80)*2, таблица `data_cmd_table` лежит в `0x2700`,
записи — 16-битные адреса обработчиков, `0x0074` = «не реализовано». Регион
`0x26D7..0x2770`, казавшийся «мусором», — это и есть таблица команд (артефакт
линейного дизасемблирования поверх встроенных данных).

Каждый подписанный обработчик подтверждён телом (дизасембл через MCP с
загруженным `basic.r0m`): GOTO->поиск строки по номеру, GOSUB/RETURN->стек
возвратов `0x0625` с маркером `0x8C`, IF->`CALL 09B1`+`CPI A1`(THEN)+`LDA 4050`
(FAC), FOR->`CALL 0691`(LET)+маркер `0x81`, NEXT->проверка маркера `0x81`,
PRINT->разделители `,`/`;`+`TAB(`/`SPC(`/`AT`, INPUT->prompt `"`+`,;`-список,
READ->вызов `func_var_lookup`, DATA->пропуск до `:`/конца.

Не выдумываем: CLS (токен `0x80`) указывает на `0x4022` — обнулённую RAM-область
(вероятно, установщик boot или RAM-резидентный код) — обработчик НЕ именуем,
переносим на сверку в runtime (Stage 6 карта RAM). Расширения `0xCA..0xE4`
(путь `SUI 5A`) и подсистемыEvaluator/хранение строк — следующие под-пакеты S5.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage5_interpreter.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage5_interpreter.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

# Существующие связи-мишени (Stage 2/3) — на них вешаем links вызовов.
EVAL_EXPR = 0x09B1      # func_eval_expression
VAR_LOOKUP = 0x0BCD     # func_var_lookup
EVAL_NUMBER = 0x053E    # func_053e — вычислить номер строки (целочисленное)
KEYWORD_TABLE = 0x256E  # data_keyword_table
CMD_LET = 0x0691        # func_cmd_let (путь присваивания)

# адрес -> описание объекта. kind: function|label|data|variable
OBJECTS = {
    # === Каркас исполнителя ===
    0x049A: {
        "kind": "function",
        "name": "func_cmd_dispatch",
        "role": "command_dispatch",
        "params": "HL = текстовый указатель на поток токенов команды; вход из "
                  "цикла исполнения (0x012B). Контракт: по выходу HL — после "
                  "команды; `0x3A`(:) — разделитель, `0x00` — конец строки.",
        "reads": ["(HL) — текущий токен", "0x3A/0x20 — пропуск разделителей и пробелов"],
        "writes": ["самомодификация LHLD-операнда по 0x04C1 (младший байт)"],
        "calls": ["самомод. LHLD 2700 -> word из data_cmd_table (адрес обработчика)",
                  "JNC 0x0691 func_cmd_let (токен без флага команды -> присваивание)"],
        "calls_named": [(0x2700, "data_cmd_table"), (CMD_LET, "func_cmd_let")],
        "note": "Диспетчер КОМАНД (открытый пункт Stage 2). Самомодифицируемый "
                "индексный переход: смещение=(token-0x80)*2, таблица "
                "data_cmd_table 0x2700, запись=адрес обработчика, 0x0074=«нет». "
                "Не путать с func_exec_dispatch (0x0B09, диспетчер функций).",
        "index_formula": "(token - 080h) * 2, база 0x2700",
        "mechanism": "self-modifying indexed jump (STA 04C1 / LHLD 2700 / PCHL-семантика)",
    },
    0x2700: {
        "kind": "data",
        "name": "data_cmd_table",
        "size": 0x5C,
        "role": "command_handler_table",
        "note": "Таблица адресов обработчиков команд `0x80..0xAD` (46 слов по 2 "
                "байта, смещение=(токен-0x80)*2). Читается func_cmd_dispatch через "
                "самомод. LHLD. `0x0074` = оператор не реализован/не вызывается из "
                "позиции команды (операторы `* / ^ AND OR > =`). Соседствует с "
                "таблицей функций data_dispatch_table (0x2770).",
        "reads": [], "writes": [], "calls": [], "calls_named": [],
    },
    0x01EF: {
        "kind": "function",
        "name": "func_tok_tokenize",
        "role": "tokenizer",
        "params": "HL = буфер ASCII-ввода; пишет внутренние токены в рабочий "
                  "буфер строки программы.",
        "reads": ["буфер ввода 0x3F77", "data_keyword_table 0x256E (LXI D,256D)"],
        "writes": ["токенизированная строка (код = 0x80 + номер слова)"],
        "calls": ["скан слов keyword-таблицы (маркер bit7 = конец слова)"],
        "calls_named": [(KEYWORD_TABLE, "data_keyword_table")],
        "note": "Токенизатор: превращает ASCII-ввод (лат/кир, РУС/ЛАТ) во "
                "внутренние коды; токен = 0x80 + индекс слова keyword-таблицы "
                "(MOV A,B / ORI 80). Подтверждён вызовом из REPL-цикла.",
    },
    0x00E5: {
        "kind": "function",
        "name": "func_main_loop",
        "role": "repl_ready_loop",
        "params": "(нет) — точка входа после boot; не возвращает (замкнутый цикл).",
        "reads": ["состояние `_READY`", "буфер строки ввода (до 127 симв., п.85 change log)"],
        "writes": ["баннер READY (строка 0x254B)", "самомод. JMP (STA 0608/05D0)"],
        "calls": ["CALL 0x01EF func_tok_tokenize", "вход в цикл исполнения строк",
                  "CALL 0x0276/0x07AD (инициализация)"],
        "calls_named": [(0x01EF, "func_tok_tokenize"), (0x049A, "func_cmd_dispatch")],
        "note": "Главный цикл REPL (`_READY`): печать приглашения, ввод/редактиро-"
                "вание строки -> func_tok_tokenize; строка с номером -> вставка в "
                "программу, без номера -> immediate-exec. Cold-start путь: "
                "0x19CC func_boot_init -> JMP 0x00E5.",
    },
    0x19CC: {
        "kind": "function",
        "name": "func_boot_init",
        "role": "boot_init",
        "params": "вход с 0x0000 (LXI SP,7FFF / JMP 19CC).",
        "reads": ["константы инициализации указателей 0x3F21/0EF6/0ED6/3DFC"],
        "writes": ["OUT 04 = 0x81 (PIA2)", "служебные указатели интерпретатора"],
        "calls": ["CALL 0x07BC/0x019F/0x01C5", "самомод. нач. адресов",
                  "JMP 0x00E5 func_main_loop"],
        "calls_named": [(0x00E5, "func_main_loop")],
        "note": "Инициализация при старте: PIA2 (OUT 04=81), растановка "
                "текстовых указателей, первичные вызовы, самомодификация, затем "
                "переход в REPL-цикл. Детальная RAM-карта ячеек — Stage 6.",
    },

    # === Обработчики команд (акцепт-критерий Stage 5) ===
    0x0691: {
        "kind": "function",
        "name": "func_cmd_let",
        "role": "cmd_let_assign",
        "params": "HL = указатель на имя переменной (без флага команды). Общий "
                  "путь присваивания (LET неявный и явный).",
        "reads": ["поток токенов: имя, `=` (0xAC), правая часть"],
        "writes": ["текстовый указатель (0x404D) на конец выражения",
                   "слот переменной по адресу из func_var_lookup"],
        "calls": ["CALL 0x0BCD func_var_lookup", "CPI 0xAC (`=`, иначе ошибка)",
                  "CALL 0x09B1 func_eval_expression"],
        "calls_named": [(VAR_LOOKUP, "func_var_lookup"), (EVAL_EXPR, "func_eval_expression")],
        "note": "Обработчик присваивания/LET: разбор имени (0x0BCD) -> `=` (0xAC) "
                "-> вычисление выражения (0x09B1) -> запись. Сюда попадает "
                "func_cmd_dispatch при токене без флага команды (JNC 0x0691). "
                "Также инициализирует переменную цикла FOR (CALL из 0x03F3).",
    },
    0x072D: {
        "kind": "function",
        "name": "func_cmd_print",
        "role": "cmd_print",
        "params": "HL = поток токенов после PRINT.",
        "reads": ["разделители `,`(0x2C)/`;`(0x3B)", "TAB( 0x9D / SPC( 0x9F / AT 0xC8",
                  "0x0C8C (строковый временный флаг — различает строка/число)"],
        "writes": ["текстовый указатель (0x404D)", "поток вывода на экран (func_putchar)"],
        "calls": ["CALL 0x09B1 func_eval_expression (каждый элемент)",
                  "CALL 0x1C7A func_cmd_cur (позицион TAB/AT)", "RST 10 (вывод строки)"],
        "calls_named": [(EVAL_EXPR, "func_eval_expression")],
        "note": "PRINT: цикл по элементам, разделители `,`/`;` (табуляция/без "
                "перевод), модификаторы TAB(/SPC(/AT; строки vs числа по 0x0C8C. "
                "Позиционирование курсора — через обработчик CUR (0x1C7A).",
    },
    0x0602: {
        "kind": "function",
        "name": "func_cmd_goto",
        "role": "cmd_goto",
        "params": "HL = поток после GOTO; цель — номер строки.",
        "reads": ["номер строки (через 0x053E)", "цепочка строк программы (num/next)"],
        "writes": ["текстовый указатель (0x404D) на найденную строку"],
        "calls": ["CALL 0x053E func_053e (вычислить номер)",
                  "поиск строки по номеру (цикл сравнения BC/DE), нет -> ошибка"],
        "calls_named": [(EVAL_NUMBER, "func_053e")],
        "note": "GOTO: вычислить номер (0x053E), найти строку в цепочке программы "
                "(сравнение номера с каждой записью, возврат указателя или 0). "
                "Механизм line_find оформим отдельным объектом в под-пакете 5c.",
    },
    0x05B9: {
        "kind": "function",
        "name": "func_cmd_gosub",
        "role": "cmd_gosub",
        "params": "HL = поток после GOSUB.",
        "reads": ["номер строки (0x053E)", "указатель возврата (0x0625 — стек GOSUB)"],
        "writes": ["0x0625 (stek GOSUB): пуш текущий текстовый указатель + маркер 0x8C"],
        "calls": ["MVI D,0x8C / PUSH D (маркер GOSUB в стек возвратов)",
                  "CALL 0x053E func_053e (номер)", "затем семантика GOTO к цели"],
        "calls_named": [(EVAL_NUMBER, "func_053e")],
        "note": "GOSUB: сохранить точку возврата в стек (0x0625) с маркером "
                "0x8C (его ищет RETURN), затем переход к строке. Парность с "
                "func_cmd_return подтверждена маркером 0x8C.",
    },
    0x063C: {
        "kind": "function",
        "name": "func_cmd_return",
        "role": "cmd_return",
        "params": "HL = поток после RETURN.",
        "reads": ["стек возвратов от 0x0625 (поиск маркера 0x8C)",
                  "PSW (POP PSW / CPI 0x8C)"],
        "writes": ["текстовый указатель (0x404D) на строку возврата"],
        "calls": ["POP PSW / CPI 0x8C (маркер GOSUB)",
                  "размотка стека (DAD SP/INX H) до точки возврата"],
        "calls_named": [],
        "note": "RETURN: размотать стек возвратов, сопоставить маркер 0x8C "
                "(кладёт GOSUB), восстановить текстовый указатель на строку "
                "вызова. Пустой стек -> STOP/READY.",
    },
    0x0712: {
        "kind": "function",
        "name": "func_cmd_if",
        "role": "cmd_if_then",
        "params": "HL = поток после IF (условие + THEN/GOTO/GOSUB).",
        "reads": ["условие (0x09B1) -> FAC", "FAC экспонента 0x4050 (истина/ложь)",
                  "THEN (0xA1) — ожидаемый разделитель"],
        "writes": ["текстовый указатель (0x404D)"],
        "calls": ["CALL 0x09B1 func_eval_expression (условие)",
                  "CPI 0xA1 (THEN)", "LDA 0x4050 (проверка истинности)",
                  "JZ 0x0672 (ложь -> пропуск ветки)"],
        "calls_named": [(EVAL_EXPR, "func_eval_expression")],
        "note": "IF/THEN: вычислить условие, потребовать THEN (0xA1), проверить "
                "FAC (0x4050==0 -> ложь -> пропуск). Истина -> fallthrough к "
                "GOTO/GOSUB/присваиванию в ветке.",
    },
    0x03F3: {
        "kind": "function",
        "name": "func_cmd_for",
        "role": "cmd_for",
        "params": "HL = поток после FOR (переменная = нач TO конец [STEP шаг]).",
        "reads": ["переменная/выражения (0x0691, 0x09B1)", "TO (0x9E) / STEP (0xA3)"],
        "writes": ["выделение блока FOR (0x01E8, A=0x11=17 байт)",
                   "маркер FOR (0x81) в стеке блоков", "текстовый указатель (0x404D)"],
        "calls": ["MVI A,0x11 / CALL 0x01E8 (выделить 17 байт под контрольный блок)",
                  "CALL 0x0691 func_cmd_let (инициализировать переменную)",
                  "CPI 0x81 (проверка вложенного FOR)"],
        "calls_named": [(CMD_LET, "func_cmd_let")],
        "note": "FOR: резервирует 17-байтный контрольный блок (0x01E8), "
                "инициализирует переменную через путь LET (0x0691), кладёт маркер "
                "FOR (0x81) на стек блоков, затем разбирает TO/STEP. Парность с "
                "func_cmd_next подтверждена маркером 0x81.",
    },
    0x08F6: {
        "kind": "function",
        "name": "func_cmd_next",
        "role": "cmd_next",
        "params": "HL = поток после NEXT (список переменных).",
        "reads": ["стек блоков FOR (маркер 0x81)", "шаг/предел контрольного блока"],
        "writes": ["переменная цикла (инкремент на шаг)", "текстовый указатель (0x404D)"],
        "calls": ["CPI 0x81 (найти FOR-блок)", "JNZ 0x007E (NEXT без FOR -> ошибка)",
                  "SPHL/INX H (забрать адрес переменной из блока)"],
        "calls_named": [],
        "note": "NEXT: соstack'а блоков достаёт ближайший FOR (проверка маркера "
                "0x81; нет -> ошибка), инкрементит переменную на шаг, сравнивает с "
                "пределом; при переходе — переход к телу, иначе — снимаем блок.",
    },
    0x0819: {
        "kind": "function",
        "name": "func_cmd_input",
        "role": "cmd_input",
        "params": "HL = поток после INPUT (опц. prompt-строка \"...\" и список "
                  "переменных через `,`/`;`).",
        "reads": ["prompt `\"` (0x22) — литерал до закрывающей кавычки",
                  "разделители `,`(0x2C)/`;`(0x3B)"],
        "writes": ["слоты переменных (0x0BCD)", "текстовый указатель (0x404D)"],
        "calls": ["CALL 0x0E72 (напечатать prompt-строку)",
                  "ожидание символа (0x2C40 func_kbd_dequeue)", "разбор/присваивание"],
        "calls_named": [],
        "note": "INPUT: опциональный prompt в кавычках (0x22), печать (0x0E72), "
                "затем по списку переменных через `,`/`;` — запрос значения и "
                "присваивание. Токенизация строковых переменных (prompt) — п.6/59 "
                "change log.",
    },
    0x0869: {
        "kind": "function",
        "name": "func_cmd_read",
        "role": "cmd_read",
        "params": "HL = поток после READ (список переменных).",
        "reads": ["указатель DATA (служебная ячейка)", "текущий элемент DATA"],
        "writes": ["слоты переменных (0x0BCD)", "указатель DATA (продвинуть)",
                   "текстовый указатель (0x404D)"],
        "calls": ["CALL 0x0BCD func_var_lookup (назначить переменной)",
                  "CALL 0x0BCD (разбор следующих имён списка)",
                  "поиск следующего элемента DATA"],
        "calls_named": [(VAR_LOOKUP, "func_var_lookup")],
        "note": "READ: читает следующий элемент из потока DATA и присваивает "
                "переменной (0x0BCD); двигает указатель DATA. Семантику указателя "
                "DATA/RESTORE уточним в под-пакете 5d (карта page-zero).",
    },
    0x0679: {
        "kind": "function",
        "name": "func_cmd_data",
        "role": "cmd_data_skip",
        "params": "HL = поток после DATA.",
        "reads": ["`(HL)` до разделителя `:`(0x3A) или `\"`(0x22) или конца (0x00)"],
        "writes": ["текстовый указатель (0x404D) — пропускает список констант"],
        "calls": ["скан до 0x3A/0x22/0x00 (RZ на конце строки)"],
        "calls_named": [],
        "note": "DATA как исполняемый оператор — ничего не делает: пропускает "
                "список констант до разделителя/конца строки (данные читаются "
                "обработчиком READ через отдельный указатель DATA).",
    },
}


def _ensure_kind(writer, session, addr, spec, log):
    """Создать/переименовать/переквалифицировать адрес к spec['kind']."""
    kind = spec["kind"]
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
        elif ctype != spec["kind"]:
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
        for key in ("index_formula", "mechanism"):
            if key in spec:
                writer.set_property(addr, key, spec[key])
        writer.set_comment(addr, "%s — %s" % (spec["name"], spec["note"]))
        for target, _tname in spec.get("calls_named", []):
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
        print("план: %d объектов Stage 5a" % len(OBJECTS))
        if args.check:
            for addr, kind, cur, ctype, spec in plan(writer):
                print("  %s [%-6s] %-26s (%-8s) -> %s %s"
                      % (addr_hex(addr), kind, cur, ctype, spec["kind"],
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
