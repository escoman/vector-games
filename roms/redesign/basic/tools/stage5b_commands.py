#!/usr/bin/env python3
"""Stage 5b: команды интерпретатора + расширения + редактирование программы.

Развивает 5a (диспетчер команд доказан). Здесь закрываем остальное ядро REPL:

1. **Диспетчер расширений — тот же `func_cmd_dispatch`.** Таблица `data_cmd_table`
   `0x2700` ПЛОТНАЯ и двухсегментная. Формула смещения:
   `off = (2*token) mod 256`, а если `off >= 0x94` (т.е. `token >= 0xCA`) —
   вычитаем `0x5A` (ветка `SUI 5A`). Отсюда:
   - команды `0x80..0x9C` -> off `0x00..0x38` (29 записей, база `0x2700`);
   - отказ `0x9D..0xC9` (`CPI 94 -> JC 0074`) — слотов НЕ занимают;
   - расширения `0xCA..0xE4` -> off `0x3A..0x6E` (27 записей, идущих вплотную).
   Итого таблица `0x2700..0x276F` = 0x70 байт (56 записей). Проверка формулы:
   `HOME(0xCD)`->`0x2740` и `CLS(0x80)`->`0x2700` оба дают `0x4022` — совпало.

2. **CLS/HOME подтверждены как код.** `0x4022`: `MVI A,1F / JMP 1C95` — байт
   очистки экрана через общий вывод управляющих кодов `0x1C95`. Замечание 5a
   «0x4022 — обнулённая RAM» было артефактом чтения не по тому адресу (0x4042).

3. **Ветка REPL `0x012B`:** `CALL 053E` (есть номер строки? carry) +
   `CALL 01EF` (токенизировать) + `POP PSW` + `JNC 049A`: нет номера ->
   исполнить как оператор; есть номер -> вставка/замена строки (`0x012E`).

4. **Формат хранения программы:** `[LN_младш LN_старш][токены...][00]`,
   последовательно, БЕЗ указателей-связок; `00 00` = конец программы.
   `NEW` пишет пустой маркер. `func_prog_line_insert` (`0x012E`) находит
   позицию, сдвигает хвост (`CALL 003B`), пишет номер+токены+`00`, правит конец
   (`CALL 01AA`). `func_prog_step` (`0x0619`, указатель возобновления `0x0609`) —
   резюмируемый пошаговый скан строк, общий для GOTO/LIST/RUN/DELETE.

5. **`0x0074`** — stub «нет/неверный аргумент» (DELETE `JNC 0074`), он же в
   таблице как «не вызывается оператором».

Под-пакет 5d (не здесь): ввод-вывод/графика/лента (`OUT/POKE/PLOT/LINE/CLOAD/
CSAVE/LPRINT/LLIST/SCREEN/COLOR/GET/PUT/BSAVE/BLOAD/PLAY/PAINT/CIRCLE`), карта
page-zero, внутренний оценщик.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage5b_commands.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage5b_commands.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

# Мишени связей (существуют или создаются этим же инструментом).
CMD_DISPATCH = 0x049A     # func_cmd_dispatch (5a)
CMD_TABLE = 0x2700        # data_cmd_table
EVAL_NUMBER = 0x053E      # func_053e — вычислить номер строки
LINE_STEP = 0x0619        # func_prog_step — резюмируемый скан строк
LINE_INSERT = 0x012E      # func_prog_line_insert
KEYWORD_TABLE = 0x256E    # data_keyword_table (детокенизация LIST)
TOKENIZE = 0x01EF         # func_tok_tokenize
DISPLAY_CTRL = 0x1C95     # вывод управляющего кода в ВГД (CLS/CUR/PRINT)
RANGE_ARG = 0x03C7        # разбор диапазона строк (LIST/DELETE)
CMD_LET = 0x0691          # func_cmd_let
VAR_LOOKUP = 0x0BCD       # func_var_lookup

# адрес -> описание объекта. kind: function|label|data|variable
OBJECTS = {
    # === Обновление существующих (коррекция 5a) ===
    CMD_TABLE: {
        "kind": "data",
        "name": "data_cmd_table",
        "size": 0x70,
        "role": "command_table",
        "mechanism": "Плотная двухсегментная таблица 16-битных адресов "
                     "обработчиков. off=(2*token)mod256; if off>=0x94: off-=0x5A "
                     "(ветка SUI 5A). Сегмент A: токены 0x80..0x9C (off 0x00..0x38, "
                     "29). Сегмент B: расширения 0xCA..0xE4 (off 0x3A..0x6E, 27). "
                     "Токены 0x9D..0xC9 отклоняются (JC 0074) и слотов не занимают. "
                     "Запись 0x0074 = «не вызывается оператором / нет аргумента».",
        "note": "Команды 0x80..0x9C + расширения 0xCA..0xE4 (56 записей, "
                "0x2700..0x276F). CLS(0x80) и HOME(0xCD) оба указывают на 0x4022 "
                "— подтверждение формулы и плотной упаковки. Размер исправлен с "
                "0x5C (5a) на 0x70 (добавлен сегмент расширений).",
    },
    CMD_DISPATCH: {
        "kind": "function",
        "name": "func_cmd_dispatch",
        "role": "command_dispatch",
        "note": "Диспетчер КОМАНД (самомод. индексный переход, таблица 0x2700). "
                "В 5b уточнён путь расширений: ветка SUI 5A дописывает второй "
                "плотный сегмент таблицы (0xCA..0xE4 -> off 0x3A..0x6E), так что "
                "один диспетчер роутит и операторы 0x80..0x9C, и расширения "
                "0xCA..0xE4; токены 0x9D..0xC9 отклоняются range-проверкой.",
        "calls_named": [(CMD_TABLE, "data_cmd_table"), (CMD_LET, "func_cmd_let")],
    },

    # === Хранение программы / ядро редактирования ===
    LINE_INSERT: {
        "kind": "function",
        "name": "func_prog_line_insert",
        "role": "prog_insert_line",
        "params": "BC = номер строки; HL/буфер 0x3F77 = токенизированное тело "
                  "(до 0x00). Вызывается из REPL при наличии номера (0x012B).",
        "reads": ["скан программы (шаг 0x0619) для точки вставки",
                  "0x3F77 — токены строки-источника"],
        "writes": ["память программы: [LN_lo LN_hi][токены][00]",
                   "сдвиг хвоста через CALL 003B (RAM-тремплин перемещения)",
                   "0x0C33 — текстовый указатель", "указатель конца программы"],
        "calls": ["CALL 0x01AA — дописать 00 00 (конец) / поправить границы"],
        "calls_named": [(LINE_STEP, "func_prog_step"), (TOKENIZE, "func_tok_tokenize")],
        "note": "Вставка/замена нумерованной строки. Формат строки: 2-байтный "
                "номер (little-endian) + токены + 0x00; связей-указателей нет, "
                "обход последовательным сканом. Подтверждено телом (0x0162..): "
                "MOV M,E/MOV M,D (номер), копир-цикл LXI D,3F77 до 0x00.",
    },
    LINE_STEP: {
        "kind": "function",
        "name": "func_prog_step",
        "role": "prog_next_line",
        "params": "HL = текущая позиция в программе; возобновление по 0x0609.",
        "reads": ["[LN_lo LN_hi] текущей строки", "пропуск тела до 0x00"],
        "writes": ["0x0609 — адрес возобновления скана (резюмируемый корутин)"],
        "calls": ["сравнение номера строки (B/D, C/E) — matched -> HL=0/RET"],
        "calls_named": [],
        "note": "Резюмируемый пошаговый переход по строкам программы (указатель "
                "возобновления 0x0609, точка шага 0x0619). Общий механизм для "
                "GOTO/поиска, LIST, RUN, DELETE, INSERT. GOTO встраивает цикл "
                "сравнения номеров (0x060B).",
    },

    # === Операторы управления программой (сегмент A 0x80..0x9C) ===
    0x05AD: {
        "kind": "function",
        "name": "func_cmd_run",
        "role": "cmd_run",
        "params": "HL = поток после RUN; необязательный стартовый номер.",
        "reads": ["0x3F21 — база программы", "GOSUB-стек/указатели"],
        "writes": ["текстовый указатель = начало программы",
                   "0x0625 (GOSUB-стек) = пусто"],
        "calls": ["вход в цикл исполнения (0x049A dispatch по строкам)"],
        "calls_named": [(CMD_DISPATCH, "func_cmd_dispatch"), (LINE_STEP, "func_prog_step")],
        "note": "RUN: сброс указателей на начало программы и запуск цикла "
                "исполнения. Идентичность — из плотной таблицы (токен 0x89).",
    },
    0x04F3: {
        "kind": "function",
        "name": "func_cmd_stop",
        "role": "cmd_stop",
        "params": "HL = поток после STOP.",
        "reads": ["текущий текстовый указатель (0x0464) — для последующего CONT"],
        "writes": ["0x0464 — сохранить позицию останова", "режим команды (READY)"],
        "calls": ["выход из цикла исполнения в REPL"],
        "calls_named": [],
        "note": "STOP: остановка выполнения с сохранением позиции (для CONT). "
                "Токен 0x8F из таблицы.",
    },
    0x0517: {
        "kind": "function",
        "name": "func_cmd_cont",
        "role": "cmd_cont",
        "params": "HL = поток после CONT.",
        "reads": ["0x0464 — сохранённая позиция останова"],
        "writes": ["текстовый указатель = позиция CONT"],
        "calls": ["возврат в цикл исполнения"],
        "calls_named": [(CMD_DISPATCH, "func_cmd_dispatch")],
        "note": "CONT: возобновить выполнение с сохранённой STOP/CNTL-C позиции. "
                "Токен 0x97 из таблицы.",
    },
    0x03A6: {
        "kind": "function",
        "name": "func_cmd_list",
        "role": "cmd_list",
        "params": "HL = поток после LIST; необязательный диапазон строк.",
        "reads": ["[LN][токены] строк программы", "0x3F21 (база)",
                  "data_keyword_table 0x256E — детокенизация"],
        "writes": ["текстовый вывод через 0x1C95/PRINT-механизм"],
        "calls": ["CALL 0x03C7 — разбор диапазона", "CALL 0x3F20 — первая строка",
                  "шаг 0x0619 по строкам"],
        "calls_named": [(LINE_STEP, "func_prog_step"),
                        (KEYWORD_TABLE, "data_keyword_table")],
        "note": "LIST: распечатать строки (диапазон необязателен), обратно "
                "разворачивая токены в слова по таблице ключевых слов. "
                "Подтверждено телом (0x03A6: CALL 03C7/RNZ/LOAD LN).",
    },
    0x0584: {
        "kind": "function",
        "name": "func_cmd_clear",
        "role": "cmd_clear",
        "params": "HL = поток после CLEAR.",
        "reads": ["0x0EF6/0x0ED6 — границы переменных/строк"],
        "writes": ["сброс GOSUB-стека 0x0625", "очистка переменных/указателей "
                   "значений, TEXT/DATA-указатели"],
        "calls": ["инициализация таблицы переменных"],
        "calls_named": [],
        "note": "CLEAR: сброс переменных, массивов и стеков (границы RAM). "
                "Токен 0x99 из таблицы.",
    },
    0x019F: {
        "kind": "function",
        "name": "func_cmd_new",
        "role": "cmd_new",
        "params": "HL = поток после NEW.",
        "reads": ["0x3F21 — база программы"],
        "writes": ["`00 00` — маркер конца (пустая программа) по 0x3F21",
                   "0x0C33, 0x0464 — указатели", "0x0EF6 — начало переменных"],
        "calls": ["CALL 0x01AA — установить конец программы/указатели"],
        "calls_named": [(LINE_INSERT, "func_prog_line_insert")],
        "note": "NEW: стереть программу (записать пустой маркер `00 00`) и "
                "сбросить указатели. Подтверждено телом (LHLD 3F21 / MVI M,00).",
    },
    0x0BC4: {
        "kind": "function",
        "name": "func_cmd_dim",
        "role": "cmd_dim",
        "params": "HL = поток после DIM (имя + размеры).",
        "reads": ["вычисляемые размеры массивов"],
        "writes": ["таблица переменных — записи массивов", "границы heap"],
        "calls": ["CALL func_var_lookup — разыменование имени"],
        "calls_named": [(VAR_LOOKUP, "func_var_lookup")],
        "note": "DIM: объявить массив(ы) — выделить место и занести в таблицу "
                "переменных. Токен 0x85 из таблицы.",
    },
    0x04D1: {
        "kind": "function",
        "name": "func_cmd_restore",
        "role": "cmd_restore",
        "params": "HL = поток после RESTORE (необязательный номер строки).",
        "reads": ["0x3F21 (база программы)"],
        "writes": ["DATA-указатель = начало (или строка по номеру)"],
        "calls": ["шаг 0x0619 — найти строку (если задан номер)"],
        "calls_named": [(LINE_STEP, "func_prog_step")],
        "note": "RESTORE: сбросить указатель чтения DATA в начало программы (или "
                "к строке с номером). Токен 0x8B из таблицы.",
    },
    0x0672: {
        "kind": "function",
        "name": "func_cmd_rem",
        "role": "cmd_rem_skip",
        "params": "HL = поток после REM (комментарий).",
        "reads": ["`(HL)` до 0x00 (конец строки)"],
        "writes": ["текстовый указатель — перемещён на конец строки"],
        "calls": ["скан до terminator 0x00"],
        "calls_named": [],
        "note": "REM: комментарий — пропускает остальную часть строки до конца "
                "(0x00). Как исполняемый оператор ничего не делает. Тот же код "
                "используют GOTO/ELSE для «доесть до конца строки». Токен 0x8E.",
    },
    0x06F6: {
        "kind": "function",
        "name": "func_cmd_on",
        "role": "cmd_on",
        "params": "HL = поток после ON (значение, затем GOTO/GOSUB-список).",
        "reads": ["вычисленное целое (FAC 0x404F..0x4052)"],
        "writes": ["выбор элемента списка -> переход к GOTO/GOSUB-обработчику"],
        "calls": ["CALL 0x053E — вычислить индекс", "разбор списка, выбор по N"],
        "calls_named": [(EVAL_NUMBER, "func_053e")],
        "note": "ON n GOTO/GOSUB list: вычислить n и выполнить n-й переход "
                "списка. Токен 0x91 из таблицы.",
    },
    0x0DA3: {
        "kind": "function",
        "name": "func_cmd_def",
        "role": "cmd_def",
        "params": "HL = поток после DEF (FN name(args)=expr).",
        "reads": ["имя FN (после DEF)", "токены тела выражения"],
        "writes": ["таблица пользовательских FN (указатель на тело строки)"],
        "calls": ["регистрация FN -> строку с телом"],
        "calls_named": [],
        "note": "DEF FN: определить пользовательскую функцию — связать имя FN с "
                "телом выражения в строке. Токен 0x96 из таблицы.",
    },
    0x4022: {
        "kind": "function",
        "name": "func_cmd_cls_home",
        "role": "cmd_cls_home",
        "params": "HL = поток после CLS/HOME.",
        "reads": [],
        "writes": ["управляющий код 0x1F в ВГД через 0x1C95 (очистка экрана)"],
        "calls": ["JMP 0x1C95 — вывод кода"],
        "calls_named": [(DISPLAY_CTRL, "func_putchar")],
        "note": "CLS (0x80) и HOME (0xCD) — ОДИН обработчик `MVI A,1F / JMP 1C95`: "
                "послать ВГД код очистки/домашний курсор. Подтверждён телом; "
                "исправляет оговорку 5a (не RAM-мусор).",
    },

    # === Расширения редактирования (сегмент B 0xCA..0xE4) ===
    0x1AA2: {
        "kind": "function",
        "name": "func_cmd_edit",
        "role": "cmd_edit",
        "params": "HL = поток после EDIT (номер строки).",
        "reads": ["[LN][токены] найденной строки", "0x3F20 (первая строка)"],
        "writes": ["буфер 0x3F77 — строка для правки",
                   "TEXT-указатель на строку"],
        "calls": ["CALL 0x053E — номер строки (RNZ, если нет)", "CALL 0x3F20",
                  "шаг 0x0619 — найти"],
        "calls_named": [(EVAL_NUMBER, "func_053e"), (LINE_STEP, "func_prog_step")],
        "note": "EDIT: загрузить строку по номеру в буфер для изменения (затем "
                "REPL вставляет её обратно через 0x012E). Подтверждено телом.",
    },
    0x1ABE: {
        "kind": "function",
        "name": "func_cmd_delete",
        "role": "cmd_delete",
        "params": "HL = поток после DELETE (номер или диапазон; обязателен).",
        "reads": ["[LN] строк в диапазоне"],
        "writes": ["сдвиг программы вниз (удаление строк)", "0x0C33",
                   "указатель конца программы"],
        "calls": ["CALL 0x03C7 — разбор диапазона (JNC 0074, если пусто)",
                  "CALL 0x3F20", "сдвиг памяти через 0x003B"],
        "calls_named": [(LINE_STEP, "func_prog_step")],
        "note": "DELETE: удалить строку/диапазон (сдвиг хвоста). Требует аргумент "
                "(JNC 0074). Подтверждено телом (0x1ABE).",
    },
    0x1C4D: {
        "kind": "function",
        "name": "func_cmd_auto",
        "role": "cmd_auto",
        "params": "HL = поток после AUTO (необяз. шаг/стартовый номер).",
        "reads": ["текущий счётчик авто-номеров"],
        "writes": ["префикс номера перед вводом каждой строки",
                   "счётчик (инкремент на шаг)"],
        "calls": ["печать номера строки перед prompt", "REPL-вставка (0x012E)"],
        "calls_named": [(LINE_INSERT, "func_prog_line_insert")],
        "note": "AUTO: режим автонумерации при вводе — печатать следующий номер "
                "перед каждой строкой. Токен 0xD1 из таблицы (сегмент B).",
    },
    0x1AFA: {
        "kind": "function",
        "name": "func_cmd_renum",
        "role": "cmd_renum",
        "params": "HL = поток после RENUM (необяз. параметры).",
        "reads": ["все строки программы (шаг 0x0619)"],
        "writes": ["перезапись номеров строк с новым шагом",
                   "перенумерация целей GOTO/GOSUB/RUN"],
        "calls": ["обход строк", "вставка переписанных строк (0x012E)"],
        "calls_named": [(LINE_STEP, "func_prog_step"), (LINE_INSERT, "func_prog_line_insert")],
        "note": "RENUM: перенумеровать программу (равный шаг) и поправить ссылки "
                "на номера. Токен 0xD7 из таблицы (сегмент B).",
    },
    0x1A7E: {
        "kind": "function",
        "name": "func_cmd_himem",
        "role": "cmd_himem",
        "params": "HL = поток после HIMEM (необяз. адрес).",
        "reads": ["0x0EF6/границы RAM", "текущий HIMEM"],
        "writes": ["верхняя граница памяти программы/гип"],
        "calls": [],
        "calls_named": [],
        "note": "HIMEM: показать/установить верхнюю границу памяти. Токен 0xD2.",
    },
    0x1A6D: {
        "kind": "function",
        "name": "func_cmd_pause",
        "role": "cmd_pause",
        "params": "HL = поток после PAUSE (необяз. таймаут).",
        "reads": ["ожидание клавиши/таймера"],
        "writes": ["режим ожидания"],
        "calls": ["цикл опроса клавиатуры (RST key-input)"],
        "calls_named": [],
        "note": "PAUSE: приостановить выполнение до нажатия клавиши (или "
                "таймаута). Токен 0xCB.",
    },
    0x1CE2: {
        "kind": "function",
        "name": "func_cmd_beep",
        "role": "cmd_beep",
        "params": "HL = поток после BEEP (необяз. длительность/тон).",
        "reads": ["вычисляемый аргумент тона"],
        "writes": ["порт динамика (пищалка)"],
        "calls": ["генерация тона"],
        "calls_named": [],
        "note": "BEEP: звуковой сигнал простого динамика. Токен 0xCA.",
    },
    0x1ED9: {
        "kind": "function",
        "name": "func_cmd_verify",
        "role": "cmd_verify",
        "params": "HL = поток после VERIFY (диапазон строк/файл).",
        "reads": ["лента/магнитофон вход", "строки программы"],
        "writes": ["сравнение без изменения памяти"],
        "calls": ["чтение с ленты", "сверка байтов"],
        "calls_named": [],
        "note": "VERIFY: сверить записанную на ленту программу с текущей "
                "(без загрузки). Токен 0xCC. Тape-подсистема детально — в 5d.",
    },
    0x1EBD: {
        "kind": "function",
        "name": "func_cmd_merge",
        "role": "cmd_merge",
        "params": "HL = поток после MERGE (файл на ленте).",
        "reads": ["лента/магнитофон вход — строки"],
        "writes": ["вливание строк в программу (перезапись по номерам)"],
        "calls": ["чтение с ленты", "вставка строк (0x012E)"],
        "calls_named": [(LINE_INSERT, "func_prog_line_insert")],
        "note": "MERGE: добавить строки с ленты к текущей программе (слияние по "
                "номерам, без стерания). Токен 0xD0. Tape-детали — в 5d.",
    },
    0x1C7A: {
        "kind": "function",
        "name": "func_cmd_cur",
        "role": "cmd_cur",
        "params": "HL = поток после CUR (X,Y).",
        "reads": ["координаты курсора (вычисляемые)"],
        "writes": ["позиция курсора ВГД через ESC-Y последовательность (0x1C95)"],
        "calls": ["CALL 0x20A6 — вычислить", "CALL 0x1C95 — emit контрольных кодов"],
        "calls_named": [(DISPLAY_CTRL, "func_putchar")],
        "note": "CUR: позиционирование курсора. Тот же код вызывает PRINT ...AT "
                "(позиционирование вывода) — отсюда вызов из обработчика PRINT. "
                "Подтверждено телом (0x1C7A: ESC 1B / 'Y' 59 / координата). "
                "Токен 0x87 (сегмент A).",
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
        print("план: %d объектов Stage 5b" % len(OBJECTS))
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
