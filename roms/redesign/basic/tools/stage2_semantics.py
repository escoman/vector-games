#!/usr/bin/env python3
"""Stage 2: семантика обработчиков функций — пачки свойств и связей.

Дополняет каркас `stage2_dispatch_table.py`: для уже именованных `func_*`
пишет свойства `params`/`reads`/`writes`/`calls` (что читает из потока токенов,
как двигает текстовый указатель `0x404D`, что пишет в page-zero/FAC
`0x404F..0x4052`) и связи вызовов между обработчиками. Факты взяты из дизасма
тел через MCP-отладчик (см. `.scratch/dis.py`), имена/адреса не изобретаются.

Карта page-zero FAC (проверена на телах):
  0x404F  — байт знака FAC (bit7 = отрицательное); его инвертирует ABS
  0x4050  — экспонента FAC; точка целого = 0x98; читают/пишут все арифметики
  0x404D  — текстовый указатель (LHLD/SHLD), двигается при разборе аргумента
  0x0028  — RST 5 (проверка/загрузка FAC); 0x1183 — нормализация/сохранение FAC

Добавляй новые пачки в словарь FACTS (ключ — адрес обработчика каркаса).

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage2_semantics.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage2_semantics.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

FAC = "FAC 0x404F..0x4052 (знак=404F bit7, экспонента=4050)"
TXTPTR = "текстовый указатель 0x404D"
# Строковый временный дескриптор: dim(длина) 0x4049, data-ptr 0x404B; сборка
# через 0x0E65/0x0E68, выделение памяти 0x0DF9, возврат во FAC 0x0E97.
STRTMP = "стр. дескриптор: dim 0x4049, data-ptr 0x404B"

# адрес -> {name, params, reads, writes, calls, calls_named(link), note}
FACTS = {
    0x148D: {
        "name": "func_sgn",
        "params": FAC,
        "reads": ["0x4050 (экспонента/знак FAC)"],
        "writes": ["0x4050=0x88 (масштаб результата)", "0x4051=0x80 (знак результата)"],
        "calls": ["RST 28 -> 0x0028 (проверка/загрузка FAC)",
                  "JMP 0x1183 (нормализация/сохранение FAC)"],
        "calls_named": [],
        "note": "SGN: результат -1/0/+1 константой в FAC.",
    },
    0x156C: {
        "name": "func_int",
        "params": FAC,
        "reads": ["0x4050 (экспонента)", "0x404D (текстовый указатель)"],
        "writes": ["0x4050=0x98 (сдвиг на границу целого)"],
        "calls": ["CALL 0x152A (усечение мантиссы)",
                  "CALL 0x1183 (нормализация/сохранение FAC)"],
        "calls_named": [],
        "note": "INT: отбрасывает дробную часть; RNC ранний выход, если уже целое.",
    },
    0x14A1: {
        "name": "func_abs",
        "params": FAC,
        "reads": ["0x404F (знак FAC)"],
        "writes": ["0x404F (сброс bit7 знака)"],
        "calls": ["RST 28 -> 0x0028 (проверка FAC)", "RP ранний выход если >= 0"],
        "calls_named": [],
        "note": "ABS: инвертирует знаковый бит FAC. Её зовёт унарный минус "
                "(lbl_0aae: call func_14a3) и EXP (call 14A3).",
    },
    0x1267: {
        "name": "func_log",
        "params": FAC,
        "reads": ["0x4050 (экспонента)"],
        "writes": ["FAC (через float-хелперы)"],
        "calls": ["RST 28 -> 0x0028 (проверка, 0 -> ошибка JPE 0539)",
                  "CALL 0x1112 / 0x1109 / 0x13B8 / 0x1844 / 0x167D (float-ряд)",
                  "константы 0x1840, 0x125A (табличные)"],
        "calls_named": [],
        "note": "LOG: натуральный логарифм рядом; ноль/отрицательное -> ошибка.",
    },
    0x17E3: {
        "name": "func_exp",
        "params": FAC,
        "reads": ["0x4050 (экспонента)"],
        "writes": ["FAC (итог), переполнение -> 0x1466"],
        "calls": ["CALL 0x14AB (сохранить FAC/текст)",
                  "CALL 0x12A6 (сборка ряда)",
                  "CALL 0x156C func_int", "CALL 0x14A3 func_abs",
                  "CALL 0x1103 / 0x110F / 0x129D / 0x1853 (float)",
                  "константы 0x8138/0xAA38 (мантиссы)"],
        "calls_named": [(0x156C, "func_int"), (0x14A1, "func_abs")],
        "note": "EXP: exp(x); переполнение по CPI 88 -> 0x1466. Явно зовёт INT и ABS.",
    },
    # --- пачка 2: тригонометрия и степень (богатые межфункциональные связи) ---
    0x18BB: {
        "name": "func_cos",
        "params": FAC,
        "reads": ["FAC (аргумент x)"],
        "writes": ["FAC (x + pi/2 перед падением в SIN)"],
        "calls": ["LXI H,0x1901 (константа pi/2)", "CALL 0x1103 (float-сложение)",
                  "падение в 0x18C1 func_sin (cos x = sin(x+pi/2))"],
        "calls_named": [(0x18C1, "func_sin")],
        "note": "COS: сдвиг фазы на pi/2 и вычисление синуса (fall-through в SIN).",
    },
    0x18C1: {
        "name": "func_sin",
        "params": FAC,
        "reads": ["0x4050 (экспонента)", "константы 0x1901/0x1905/0x1909 (pi/2, ряд)"],
        "writes": ["FAC (итог ряда)"],
        "calls": ["CALL 0x14AB (сохранить FAC/текст)", "CALL 0x14C3 (деление)",
                  "CALL 0x13B8 (умножение)", "CALL 0x156C func_int",
                  "CALL 0x110F / 0x1109 / 0x1100 (float)", "CNC 0x14A3 func_abs",
                  "JMP 0x1844 (сборка ряда)"],
        "calls_named": [(0x156C, "func_int"), (0x14A1, "func_abs")],
        "note": "SIN: ряд Тейлора с приведением аргумента (зовёт INT и ABS).",
    },
    0x191E: {
        "name": "func_tan",
        "params": FAC,
        "reads": ["FAC (аргумент x)"],
        "writes": ["FAC (SIN/COS)"],
        "calls": ["CALL 0x14AB", "CALL 0x18C1 func_sin", "CALL 0x14AB",
                  "CALL 0x14C3", "CALL 0x18BB func_cos", "JMP 0x13B6 (деление SIN/COS)"],
        "calls_named": [(0x18C1, "func_sin"), (0x18BB, "func_cos")],
        "note": "TAN = SIN/COS: сохраняет SIN, вычисляет COS, делит (JMP 13B6).",
    },
    0x1933: {
        "name": "func_atn",
        "params": FAC,
        "reads": ["0x4050 (экспонента, порог CPI 81)", "константы 0x1901/0x1958"],
        "writes": ["FAC (итог ряда)"],
        "calls": ["RST 28 -> 0x0028", "CM 0x1799 (если отрицательное -> знак)",
                  "CM 0x14A3 func_abs (если отрицательное)", "CALL 0x13B8",
                  "CALL 0x1844 (ряд)"],
        "calls_named": [(0x14A1, "func_abs")],
        "note": "ATN: арктангенс рядом; нечётность через условный вызов ABS.",
    },
    0x179E: {
        "name": "func_sqr",
        "params": FAC,
        "reads": ["константа 0x1783 (0.5)"],
        "writes": ["FAC (x^0.5)"],
        "calls": ["CALL 0x14AB", "LXI H,0x1783 (0.5)", "CALL 0x14BB (степень)",
                  "RST 28", "JZ 0x17E3 func_exp (особый путь)"],
        "calls_named": [(0x17E3, "func_exp")],
        "note": "SQR = x^0.5 через возведение в степень; ветка в EXP.",
    },
    0x1878: {
        "name": "func_rnd",
        "params": FAC + "; состояние ГПСЧ в 0x3DFC",
        "reads": ["0x3DFC.. (состояние ПСЧ)", "константы 0x9835/0x447A, 0x6828/0xB146"],
        "writes": ["0x3DFC.. (новое состояние ПСЧ)", "FAC (результат)"],
        "calls": ["RST 28", "JM 0x1895", "CALL 0x14BB", "CALL 0x12A6 (умножение)",
                  "CALL 0x1112 (сложение)", "CALL 0x14CE", "CALL 0x1186"],
        "calls_named": [],
        "note": "RND: линейный конгруэнтный ГПСЧ, состояние в 0x3DFC.",
    },
    # --- пачка 3: строковые операции (общий eval-хвост 0x100F и экстрактор подстроки 0x103F) ---
    0x100B: {
        "name": "func_len",
        "params": "строка (eval через 0x0FE2)",
        "reads": ["дескриптор строки (длина в (HL))", "0x0C8C (флаг стр. зоны)"],
        "writes": ["0x0C8C=0"],
        "calls": ["CONT 0x0D95 (положить результат)", "CALL 0x0FE2 (eval строки -> дескриптор)",
                  "хвост 0x100F переиспользуют ASC/VAL"],
        "calls_named": [],
        "note": "LEN: вычисляет строковый аргумент и возвращает его длину (байт счётчика). "
                "Его хвост 0x100F — общий eval-помощник для ASC/VAL.",
    },
    0x101A: {
        "name": "func_asc",
        "params": "строка",
        "reads": ["data-ptr дескриптора (LDAX D) — первый байт строки"],
        "writes": [],
        "calls": ["CALL 0x100F (eval строки, хвост func_len)",
                  "JNZ 0x0D95 (код символа), пустая строка -> MVI A,FF"],
        "calls_named": [(0x100B, "func_len")],
        "note": "ASC: код первого символа строки; пустая строка -> 255.",
    },
    0x102B: {
        "name": "func_chr",
        "params": FAC + "; код символа",
        "reads": ["0x404B (data-ptr временной строки)"],
        "writes": [STRTMP, "0x404B-> (символ)"],
        "calls": ["CALL 0x0E65 (собрать дескриптор из 1 байта, dim=1)",
                  "CALL 0x10CA (числовой аргумент)", "LHLD 0x404B / MOV M,E",
                  "JMP 0x0E97 (вернуть временную строку)"],
        "calls_named": [],
        "note": "CHR$: строка из одного символа по его коду.",
    },
    0x103B: {
        "name": "func_left",
        "params": "строка, число (0x10B6 eval)",
        "reads": ["дескриптор строки (dim/data-ptr)"],
        "writes": ["новый дескриптор подстроки"],
        "calls": ["CALL 0x10B6 (eval 2 аргумента)", "CLAMP n к длине (CMP B/JC)",
                  "CALL 0x0ECE (копировать) / 0x0E68 (dim) / 0x0FD8",
                  "хвост 0x103F.. переиспользуют RIGHT/MID", "JMP 0x0E97"],
        "calls_named": [],
        "note": "LEFT$: первые n байт; его хвост 0x103F — общий экстрактор подстроки для RIGHT$/MID$.",
    },
    0x106B: {
        "name": "func_right",
        "params": "строка, число",
        "reads": ["дескриптор строки"],
        "writes": ["дескриптор подстроки"],
        "calls": ["CALL 0x10B6 (eval)", "LDAX D / SUB B (старт = len - n)",
                  "JMP 0x103F (хвост func_left)"],
        "calls_named": [(0x103B, "func_left")],
        "note": "RIGHT$: сдвиг стартовой позиции на len-n и падение в общий экстрактор LEFT$.",
    },
    0x1075: {
        "name": "func_mid",
        "params": "строка, позиция[, длина]",
        "reads": ["дескриптор строки"],
        "writes": ["дескриптор подстроки"],
        "calls": ["CALL 0x10B9 (eval до 3 аргументов)", "MVI E,FF / CPI 29 (необязательный len)",
                  "RST 08 (след. токен)", "LXI B,0x1041 / PUSH B (общий хвост func_left)"],
        "calls_named": [(0x103B, "func_left")],
        "note": "MID$: start=p, len опционален; входит в общий экстрактор подстроки на 0x1041.",
    },
    0x0E40: {
        "name": "func_str",
        "params": FAC + " (число)",
        "reads": [STRTMP],
        "writes": [STRTMP, "строковая зона (0x0DF9 alloc)"],
        "calls": ["CALL 0x09A1 (взять FAC)", "CALL 0x16AD (float->ASCII в буфер)",
                  "CALL 0x0E71 (посчитать длину)", "CALL 0x0FE5 / 0x0ECE (выделить/скопировать)",
                  "CALL 0x0E68 (dim) / 0x0FD8"],
        "calls_named": [],
        "note": "STR$: число -> строка через float->ASCII форматировщик 0x16AD.",
    },
    0x10D6: {
        "name": "func_val",
        "params": "строка",
        "reads": ["data-ptr строки (HL из дескриптора)"],
        "writes": ["0x00AE (текст. указатель парсера)", "0x00B0/0x00B1 (флаги разбора)", "FAC"],
        "calls": ["CALL 0x100F (eval строки, хвост func_len)", "JZ 0x119A (пусто -> 0)",
                  "CALL 0x15A8 (числовой парсер -> FAC)"],
        "calls_named": [(0x100B, "func_len")],
        "note": "VAL: прогоняет строку через арифметический парсер 0x15A8; пусто -> 0.",
    },
    # --- пачка 4: системные функции (порт/память/клавиатура/курсор/&hex) ---
    0x109C: {
        "name": "func_inp",
        "params": "число (номер порта)",
        "reads": ["порт ввода IN 00 (номер подставляется)"],
        "writes": ["0x10A3 (самомодифицируемый операнд порта инструкции IN)"],
        "calls": ["CALL 0x10CA (eval числа -> A)", "STA 0x10A3 (patch IN), IN 00",
                  "JMP 0x0D95 (хвост func_pos: байт A -> FAC)"],
        "calls_named": [],
        "note": "INP(n): чтение порта n; номер порта патчится самомодификацией IN-инструкции.",
    },
    0x0D92: {
        "name": "func_pos",
        "params": FAC + "; позиция курсора",
        "reads": ["состояние экрана через 0x3DEC"],
        "writes": ["0x0C8C (флаг стр. зоны)"],
        "calls": ["CALL 0x3DEC (колонка курсора -> A)",
                  "хвост 0x0D95: MOV C,A / MVI E,00 / MVI B,90 / JMP 0x1493 (байт->FAC)"],
        "calls_named": [],
        "note": "POS: колонка курсора. Её хвост 0x0D95 — общий return-помощник байт->FAC "
                "для INP/PEEK/POINT/LEN/ASC.",
    },
    0x197D: {
        "name": "func_peek",
        "params": "число (адрес)",
        "reads": ["(DE) — байт памяти по адресу"],
        "writes": [],
        "calls": ["CALL 0x0531 (eval числа -> DE = адрес)", "CALL 0x1987 (граница: D>=3 -> ошибка)",
                  "LDAX D (чтение байта)", "JMP 0x0D95 (байт->FAC)"],
        "calls_named": [],
        "note": "PEEK(a): чтение байта памяти по адресу с проверкой диапазона.",
    },
    0x0D6E: {
        "name": "func_fre",
        "params": "0 (значения не имеет)",
        "reads": ["0x0CB3 (верх занятой памяти)", "0x0C8C (флаг стр. зоны)", "SP (стек)",
                  "0x0ED6/0x0ED3 (границы строк)"],
        "writes": ["строковая зона (сборка мусора)"],
        "calls": ["LXI H,0000 / DAD SP (запас стека)",
                  "CALL 0x0FE5 / 0x0EF5 (сборка мусора строк, если 0x0C8C<>0)",
                  "JMP 0x0D97 (результат DE -> FAC)"],
        "calls_named": [],
        "note": "FRE(0): объём свободной памяти; при активных строках делает сборку мусора.",
    },
    0x1C9C: {
        "name": "func_point",
        "params": "выражение (координаты)",
        "reads": ["0x2B56 (состояние экрана/луча)"],
        "writes": [],
        "calls": ["CALL 0x10CA (eval аргумента)", "CALL 0x1CA5 -> CALL 0x3BD3 (чтение пиксела)",
                  "JMP 0x0D95 (результат->FAC)"],
        "calls_named": [],
        "note": "POINT: состояние точки экрана (чтение пиксела через 0x3BD3, база 0x2B56).",
    },
    0x280E: {
        "name": "func_usr",
        "params": "число (адрес машинного кода)",
        "reads": ["(DE) — пользовательская подпрограмма"],
        "writes": [],
        "calls": ["CALL 0x0531 (eval числа -> DE = адрес)",
                  "CMP 42 / JNC 0x0539 (адрес 0x42.. -> ошибка)",
                  "XCHG / LXI D,0x0D95 / PUSH D / PCHL (хвост-вызов по адресу)"],
        "calls_named": [],
        "note": "USR(a): прыжок PCHL в машинный код по адресу a; возврат через 0x0D95 (байт->FAC).",
    },
    0x1A4D: {
        "name": "func_inkey",
        "params": "(без аргумента)",
        "reads": ["клавиатура через 0x2C40"],
        "writes": [STRTMP],
        "calls": ["CALL 0x2C40 (скан клавиатуры -> A: код или <0 если пуста)",
                  "JP 0x1A5F (есть клавиша -> строка 1 символ) / XRA A (пусто -> пустая строка)",
                  "CALL 0x0E65 (собрать дескриптор) / JMP 0x0E97 (вернуть строку)"],
        "calls_named": [],
        "note": "INKEY$: строка из нажатой клавиши или пустая, если клавиш нет.",
    },
    0x15FA: {
        "name": "func_amp",
        "params": "hex-константа после `&` (адреса памяти и вообще шестнадцатеричные числа)",
        "reads": ["поток токенов (RST 0x10 — следующий символ числа)"],
        "writes": ["FAC (числовое значение hex-литерала, шкала целого 0x98)"],
        "calls": ["RST 0x10 (след. символ), JC 0x160F (цифра 0-9) / 'A'..'F' (CPI 41/47, SUI 07)",
                  "CPI 10 / JNC 0x0074 (не hex -> ошибка)",
                  "DAD H x4 (*16) + ADD E — накопление 16-битного значения",
                  "MOV A,D / RLC / SBB A (знак) / MVI B,98 / CALL 0x1493 (число->FAC)"],
        "calls_named": [],
        "note": "`&` — шестнадцатеричная константа: разбор hex-цифр (0-9,A-F), "
                "накопление 16-битного числа (x16+digit) и выдача его в FAC (шкала 0x98). "
                "Так задают адреса памяти и hex-числа. НЕ конкатенация и НЕ строка/символ.",
    },
}


def check(session):
    """Все адреса пачки обязаны существовать в RDB с ожидаемым именем."""
    problems = []
    for addr, f in FACTS.items():
        obj = session.call("debug_get_rdb_object", {"address": addr})
        if not obj or not obj.get("address"):
            problems.append("%s: объекта нет — сначала stage2_dispatch_table --apply"
                            % addr_hex(addr))
        elif obj.get("name") != f["name"]:
            problems.append("%s: имя в RDB %r, ожидаем %r"
                            % (addr_hex(addr), obj.get("name"), f["name"]))
    return problems


def apply(writer):
    log = []
    for addr, f in FACTS.items():
        writer.set_property(addr, "params", f["params"])
        writer.set_property(addr, "reads", f["reads"])
        writer.set_property(addr, "writes", f["writes"])
        writer.set_property(addr, "calls", f["calls"])
        # дополнение к комменту каркаса: короткий семантический вывод
        writer.set_comment(addr, "%s — %s" % (f["name"], f["note"]))
        for target, tname in f["calls_named"]:
            writer.add_link(addr, target)
        log.append("%s %s: params/reads/writes/calls + %d связей"
                   % (addr_hex(addr), f["name"], len(f["calls_named"])))
    return log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--rdb", default=DEFAULT_RDB)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    if not (args.check or args.apply):
        args.check = True

    rdb_path = os.path.abspath(args.rdb)
    session, _cache = open_session(rom=args.rom, org=0x0000)
    try:
        info = session.call("debug_get_rdb_info")
        if os.path.abspath(info.get("path") or "") != rdb_path:
            raise SystemExit("RDB в сессии %r, ожидаем %r"
                             % (info.get("path"), args.rdb))
        problems = check(session)
        for line in problems:
            print("РАСХОЖДЕНИЕ: " + line, file=sys.stderr)
        if problems:
            return 1
        print("пачка сверена: %d обработчиков, расхождений 0" % len(FACTS))
        if not args.apply:
            return 0
        writer = RdbWriter(session)
        for line in apply(writer):
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
