#!/usr/bin/env python3
"""Stage 5d: встроенные подсистемы (графика/звук/лента/печать/ввод-вывод) + оценщик.

Закрывает Stage 5 (п.7 ТЗ «встроенные подсистемы» + п.3 оценщик). Все адреса —
из УЖЕ ДОКАЗАННОЙ двухсегментной таблицы `data_cmd_table` `0x2700` (Stage 5a/5b):
сегмент A операторов `0x80..0x9C`, сегмент B расширений `0xCA..0xE4`. Имена
токен↔слово подтверждены в Stage 2. Тела spot-верифицированы для ✔-объектов.

1. **Поправки к таблице 5b (raw-байты, little-endian).** При перечитывании
   сегмента B найдены и исправлены две ошибки прошлой сводки:
   - `PAINT(0xE3)` -> `0x20B1` (было ошибочно `0x19B1`; `0x19B1` — середина
     тела POKE),
   - `CIRCLE(0xE4)` -> `0x3033` (было ошибочно `0x1C21`).
   `SCREEN(0xDC)` = `0x231B` — перепроверен, в доке был верен.

2. **Графика** (`PLOT/LINE/COLOR/SCREEN/PAINT/CIRCLE/GET/PUT`) используют общий
   парсер координат `0x28A0` (PLOT/PAINT/CIRCLE) и вычислитель цвета `0x10C3`;
   SCREEN переключает режим (`CALL 0x20A6` + ветвление по значению в C: SCREEN0/3/4).

3. **Звук/лента**: `PLAY` — `DI`, сброс состояния проигрывания (`0x27C8`/`0x245F`),
   список нот через `,` (драйвер на прерывании ВBlank, ТЗ п.63/65/74). `CSAVE` —
   запись на магнитофон: синхробайт `0x55`, заголовок/адрес/длина через хелперы
   `0x1D2D/1D41/1D76`, порт `0xD3`(OUT).

4. **Вывод/память**: `OUT` — самомодифицируемый `OUT порт` (`CALL 0x099E` порт →
   `STA` операнда порта → `CALL 0x10C3` значение → `OUT`). `POKE` — запись в
   память `STAX D` без guard-диапазона (ТЗ п.40/67 — таблиц адресов нет).

5. **Оценщик** (core назван в Stage 2/3): уточняем ABI-цепочку
   `func_eval_expression` `0x09B1` -> guard стека (лимит `0x0CB3` -> `JC 0069`
   «out of memory») -> `CALL 0x0A43`; цикл свёртки по приоритету `0x09D0`
   (`MVI A,77/CMP B/JNC`); строковая ветка по флагу `0x0C8C` -> конкатенация
   `0x1E6D`; диспетчер бинарных операций `0x09DD` (`SUI AB` -> индекс,
   указатель подпрограммы операции -> `0x0F45`). Метку `lbl_09dd` НЕ
   переквалифицируем в функцию — это внутренний переход, не точка вызова.

Отложено: карта `var_*` page-zero/RAM и подтверждение `memory_diff` — Stage 6;
тексты ошибок для заглушек `0x0069`/`0x0074` — Stage 8.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage5d_subsystems.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage5d_subsystems.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

# Мишени связей (существуют в RDB; висячих ссылок не создаём).
EVAL_INT = 0x099E         # func_099e — вычислить выражение -> целое (BC/DE)
EVAL_EXPR = 0x09B1        # func_eval_expression — вход в оценщик
EVAL_PRIMARY = 0x0A43     # func_eval_primary — унарный/первичный/очередной член
PUTCHAR = 0x1C95          # func_putchar — вывод кода/символа в ВГД
PROG_STEP = 0x0619        # func_prog_step — резюмируемый скан строк
FIRST_LINE = 0x3F20       # func_3f20 — указатель первой строки программы

# Хелперы без объектов (только прозой в `calls`): 0x28A0 — парсер координат
# X,Y (PLOT/PAINT/CIRCLE); 0x10C3 — вычислить выражение -> байт A (цвет/значение
# PLOT/CIRCLE/POKE/OUT); 0x20A6 — вычислить аргумент (SCREEN/CUR); лента
# 0x1D2D/0x1D41/0x1D76 — записи/заголовки CSAVE.

# адрес -> описание объекта. kind: function|label|data|variable
OBJECTS = {
    # ===== Графика =====
    0x28C2: {
        "kind": "function",
        "name": "func_cmd_plot",
        "role": "cmd_plot",
        "params": "HL = поток после PLOT; аргументы X,Y(,цвет).",
        "reads": ["вычисляемые X,Y (`CALL 0x28A0`)",
                  "необязательный цвет через `,` (`CALL 0x10C3`)"],
        "writes": ["установка точки ВГД (координатная кодировка режима экрана)"],
        "calls": ["CALL 0x28A0 — разобрать X,Y", "CALL 0x10C3 — вычислить цвет",
                  "примитив вывода точки"],
        "calls_named": [],
        "note": "PLOT X,Y(,c): установить точку. Подтверждено телом (0x28C2: "
                "CALL 28A0 / CPI 2C ',' / CALL 10C3). Токен 0x92 (сегмент A).",
    },
    0x28FD: {
        "kind": "function",
        "name": "func_cmd_line",
        "role": "cmd_line",
        "params": "HL = поток после LINE; X1,Y1-X2,Y2 (,цвет), опц. BF/BS.",
        "reads": ["две точки (координаты), цвет; флаг заливки/границы"],
        "writes": ["отрезок (или прямоугольник BF/BS) в ВГД"],
        "calls": ["разбор координат (`CALL 0x28A0`-подобный)", "драйвер линии"],
        "calls_named": [],
        "note": "LINE (X,Y)-(X,Y)[,c][BF|BS]: отрезок/прямоугольник. Адрес из "
                "плотной таблицы (токен 0x93); группа графики, рядом с PLOT.",
    },
    0x281D: {
        "kind": "function",
        "name": "func_cmd_color",
        "role": "cmd_color",
        "params": "HL = поток после COLOR; аргументы цвета/палитры.",
        "reads": ["вычисляемые компоненты цвета"],
        "writes": ["текущий цвет/палитра вывода (переменная рисования)"],
        "calls": ["вычислить аргументы цвета"],
        "calls_named": [],
        "note": "COLOR: задать текущий цвет/палитру. Токен 0xDD (сегмент B, "
                "`0x2760` -> `0x281D`).",
    },
    0x231B: {
        "kind": "function",
        "name": "func_cmd_screen",
        "role": "cmd_screen",
        "params": "HL = поток после SCREEN; режим (0/3/4).",
        "reads": ["аргумент режима (`CALL 0x20A6` -> C)"],
        "writes": ["режим экрана (ветвление JZ 0x2384/0x23B9 по значению C)"],
        "calls": ["CALL 0x20A6 — вычислить режим", "переконфигурировать ВГД"],
        "calls_named": [],
        "note": "SCREEN: переключение режимов экрана (SCREEN0/3/4 — ТЗ). "
                "Подтверждено телом (0x231B: CALL 20A6 / DCR C / JZ...). Токен "
                "0xDC -> 0x231B (в 5b-доке адрес был верен).",
    },
    0x20B1: {
        "kind": "function",
        "name": "func_cmd_paint",
        "role": "cmd_paint",
        "params": "HL = поток после PAINT; X,Y(,цвет/заливка).",
        "reads": ["текущий цвет (`LDA 0x3769` -> `0x4028`)",
                  "координаты X,Y (`CALL 0x28A0`)"],
        "writes": ["пиксельно-байтовая заливка области ВГД"],
        "calls": ["CALL 0x28A0 — разобрать X,Y", "заливка (рекурсивный flood)"],
        "calls_named": [],
        "note": "PAINT: заливка замкнутой области. Подтверждено телом (0x20B1: "
                "LDA 3769/STA 4028/CALL 28A0). ИСПРАВЛЕНИЕ 5b: адрес `0x20B1`, "
                "не `0x19B1` (то был середина POKE). Токен 0xE3 -> `0x276C`.",
    },
    0x3033: {
        "kind": "function",
        "name": "func_cmd_circle",
        "role": "cmd_circle",
        "params": "HL = поток после CIRCLE; X,Y, радиус(,цвет).",
        "reads": ["центр X,Y (`CALL 0x28A0`)", "радиус (-> `0x2B56`/`0x2B57`)",
                  "цвет (`CALL 0x10C3` -> `0x30B4`)"],
        "writes": ["окружность/дуга в ВГД (синус-таблица, ТЗ п.23)"],
        "calls": ["CALL 0x28A0 — центр", "CALL 0x10C3 — цвет", "примитив дуги"],
        "calls_named": [],
        "note": "CIRCLE (X,Y),R(,c): окружность/дуга. Подтверждено телом (0x3033: "
                "CALL 28A0/STA 2B56/CALL 10C3). ИСПРАВЛЕНИЕ 5b: адрес `0x3033`, "
                "не `0x1C21`. Токен 0xE4 -> `0x276E`.",
    },
    0x3441: {
        "kind": "function",
        "name": "func_cmd_get",
        "role": "cmd_get",
        "params": "HL = поток после GET; X,Y, размер, буфер.",
        "reads": ["прямоугольник ВГД (координаты + размеры)"],
        "writes": ["буфер памяти — считанный блок графики"],
        "calls": ["разбор координат/размера", "чтение плоскостей ВГД"],
        "calls_named": [],
        "note": "GET: считать блок изображения из экрана в память (пара PUT). "
                "Токен 0xDE -> `0x3441` (сегмент B). ТЗ п.45/47/69.",
    },
    0x357F: {
        "kind": "function",
        "name": "func_cmd_put",
        "role": "cmd_put",
        "params": "HL = поток после PUT; X,Y, размер, буфер.",
        "reads": ["буфер памяти — блок графики"],
        "writes": ["прямоугольник ВГД (восстановление изображения)"],
        "calls": ["разбор координат/размера", "запись плоскостей ВГД"],
        "calls_named": [],
        "note": "PUT: вывести блок изображения из памяти на экран (пара GET). "
                "Токен 0xDF -> `0x357F` (сегмент B). ТЗ п.45/47/69.",
    },

    # ===== Звук =====
    0x2428: {
        "kind": "function",
        "name": "func_cmd_play",
        "role": "cmd_play",
        "params": "HL = поток после PLAY; список нот через `,`.",
        "reads": ["список нот/длительностей (разбор по `,` `CPI 2C`)"],
        "writes": ["состояние проигрывания `0x27C8`/`0x245F`",
                   "тон/громкость через `DI` (драйвер на ВBlank-прерывании)"],
        "calls": ["сброс курсора воспроизведения", "инициализация звуковых счётчиков"],
        "calls_named": [],
        "note": "PLAY list$: воспроизведение нот. Подтверждено телом (0x2428: "
                "PUSH PSW/XRA A/STA 27C8/STA 245F/DI/CPI 2C). Драйвер — на "
                "прерывании (ТЗ п.63/65/74). Токен 0xE2 -> `0x276A`.",
    },

    # ===== Лента (магнитофон) =====
    0x1DA8: {
        "kind": "function",
        "name": "func_cmd_csave",
        "role": "cmd_csave",
        "params": "HL = поток после CSAVE (необяз. имя/диапазон).",
        "reads": ["программа/блок для записи", "имя (<=11 симв., ТЗ п.73)"],
        "writes": ["магнитофон-выход: синхробайт `0x55`, заголовок, данные"],
        "calls": ["CALL 0x1D2D / 0x1D41 / 0x1D76 — запись заголовка/байтов",
                  "порт ленты (`D3` OUT)"],
        "calls_named": [],
        "note": "CSAVE: записать программу на магнитофон. Подтверждено телом "
                "(0x1DA8: MVI A,D3/STA.../CALL 1D2D/1D41/1D76/MVI A,55 — синхробайт). "
                "Токен 0x9B (сегмент A).",
    },
    0x1EDA: {
        "kind": "function",
        "name": "func_cmd_cload",
        "role": "cmd_cload",
        "params": "HL = поток после CLOAD (необяз. имя).",
        "reads": ["магнитофон-вход — поток программы"],
        "writes": ["загрузка строк в память программы"],
        "calls": ["чтение с ленты (хелперы,mirror CSAVE)",
                  "вставка строк (0x012E)"],
        "calls_named": [],
        "note": "CLOAD: считать программу с магнитофона (пара CSAVE). Токен 0x9A "
                "-> `0x1EDA` (сегмент A). Детали обмена — группа ленты рядом с CSAVE.",
    },
    0x1DED: {
        "kind": "function",
        "name": "func_cmd_bsave",
        "role": "cmd_bsave",
        "params": "HL = поток после BSAVE (имя, адрес, длина).",
        "reads": ["блок памяти (адрес..длина)"],
        "writes": ["магнитофон-выход — двоичный блок"],
        "calls": ["запись блока на ленту (хелперы ленты)"],
        "calls_named": [],
        "note": "BSAVE: сохранить блок памяти на ленту в двоичном виде. Токен "
                "0xE0 -> `0x1DED` (сегмент B).",
    },
    0x1E3D: {
        "kind": "function",
        "name": "func_cmd_bload",
        "role": "cmd_bload",
        "params": "HL = поток после BLOAD (имя).",
        "reads": ["лента — двоичный блок (адрес, длина)"],
        "writes": ["блок памяти — загруженные данные"],
        "calls": ["чтение блока с ленты (хелперы ленты)"],
        "calls_named": [],
        "note": "BLOAD: загрузить блок памяти с ленты. Пара BSAVE. Токен 0xE1 -> "
                "`0x1E3D` (сегмент B).",
    },

    # ===== Печать =====
    0x2036: {
        "kind": "function",
        "name": "func_cmd_lprint",
        "role": "cmd_lprint",
        "params": "HL = поток после LPRINT (список вывода).",
        "reads": ["вычисляемые значения/строки"],
        "writes": ["печатающее устройство (порт принтера)"],
        "calls": ["тот же разбор списка, что PRINT", "вывод символа на принтер"],
        "calls_named": [],
        "note": "LPRINT: печать выражений на принтер (младший брат PRINT). Токен "
                "0xDA -> `0x2036` (сегмент B).",
    },
    0x03A1: {
        "kind": "function",
        "name": "func_cmd_llist",
        "role": "cmd_llist",
        "params": "HL = поток после LLIST (необяз. диапазон).",
        "reads": ["[LN][токены] строк программы", "data_keyword_table — детокенизация"],
        "writes": ["листинг на принтер"],
        "calls": ["обход строк (0x0619)", "детокенизация через таблицу ключ. слов"],
        "calls_named": [],
        "note": "LLIST: распечатать программу на принтер (младший брат LIST, "
                "0x03A6 — рядом). Токен 0xDB -> `0x03A1` (сегмент B).",
    },

    # ===== Ввод-вывод / память =====
    0x10A7: {
        "kind": "function",
        "name": "func_cmd_out",
        "role": "cmd_out",
        "params": "HL = поток после OUT; порт, значение.",
        "reads": ["номер порта (`CALL 0x099E`)", "значение (`CALL 0x10C3`)"],
        "writes": ["`OUT порт` (самомодиф. операнд порта по `STA 0x10B4`)"],
        "calls": ["CALL 0x099E — порт", "CALL 0x10C3 — значение", "OUT (порт)"],
        "calls_named": [(EVAL_INT, "func_099e")],
        "note": "OUT port,val: вывод байта в аппаратный порт. Подтверждено телом "
                "(0x10A7: CALL 099E/STA 10B4/CALL 10C3/OUT 00). Токен 0x90 "
                "(сегмент A).",
    },
    0x19AA: {
        "kind": "function",
        "name": "func_cmd_poke",
        "role": "cmd_poke",
        "params": "HL = поток после POKE; адрес, значение.",
        "reads": ["адрес (`CALL 0x1987`/`0x300A` -> DE)", "значение (`CALL 0x10C3`)"],
        "writes": ["`STAX D` — запись байта по адресу DE (без guard-диапазона)"],
        "calls": ["CALL 0x300A/0x1987 — вычислить адрес", "CALL 0x10C3 — значение"],
        "calls_named": [],
        "note": "POKE addr,val: запись байта в память. Подтверждено телом (0x19AA: "
                "CALL .../PUSH D/CALL 10C3/POP D/STAX D). Guard диапазона нет — "
                "таблиц адресов/масок недоступны (ТЗ п.40/67). Токен 0x94 (сегмент A).",
    },

    # ===== Оценщик (обновление существующих, Stage 2/3) =====
    EVAL_EXPR: {
        "kind": "function",
        "name": "func_eval_expression",
        "role": "eval_expression",
        "params": "HL = поток выражения; возврат значения в FAC.",
        "reads": ["0x0CB3 — лимит глубины стека", "0x0C8C — флаг строковых темпов",
                  "0x09DD — индекс бинарной операции (SUI AB)"],
        "writes": ["0x0F45 — указатель подпрограммы бинарной операции",
                   "FAC — значение выражения"],
        "calls": ["guard: LXI H,FFD1/DAD SP/JC 0069 (out of memory)",
                  "CALL 0x0A43 — разбор/unary/primary",
                  "0x09D0 — цикл свёртки по приоритету (MVI A,77/CMP B)",
                  "0x09DD — диспетчер операций; строковая ветка -> 0x1E6D"],
        "calls_named": [(EVAL_PRIMARY, "func_eval_primary")],
        "note": "Вход в оценщик выражений (рекурсивный спуск с приоритетами). "
                "Уточнён ABI (Stage 5d): стек-guard (лимит 0x0CB3 -> JC 0069), "
                "цикл свёртки по приоритету 0x09D0, диспетчер бин. операций 0x09DD "
                "(SUI AB -> индекс,Routine ptr -> 0x0F45), строковая конкатенация "
                "по флагу 0x0C8C -> 0x1E6D.",
    },
    EVAL_PRIMARY: {
        "kind": "function",
        "name": "func_eval_primary",
        "role": "eval_primary",
        "params": "HL = поток на первичном члене; значение -> FAC.",
        "reads": ["разбор литералов/переменных/скобок/унарных/вызовов FN"],
        "writes": ["FAC — значение первичного члена"],
        "calls": ["func_099e — вычислить целое", "func_var_lookup — переменная",
                  "func_exec_dispatch 0x0B09 — встроенная функция"],
        "calls_named": [(EVAL_INT, "func_099e")],
        "note": "Разбор первичного члена (литерал/переменная/скобка/унар/вызов "
                "функции). Вызывается func_eval_expression (0x09B1). Core назван в "
                "Stage 2/3; 5d подтверждает роль в цепочке приоритетов.",
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
        print("план: %d объектов Stage 5d" % len(OBJECTS))
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
