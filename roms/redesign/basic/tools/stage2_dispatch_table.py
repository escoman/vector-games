#!/usr/bin/env python3
"""Stage 2: каркас интерпретатора в RDB — таблица слов + диспетчер функций.

Разбор доказан на живом образе `basic.r0m` (цепочка пруф-прогонов в
`.scratch/probe_*.py`, сводка — `reports/Stage2.md`):

* таблица ключевых слов `0x256E..0x26D6` — 101 слово, кодировка «посимвольно,
  bit7 = конец слова»; **токен = `0x80` + номер слова** (проверено якорями из
  кода: FN=слово32→`0xA0`, NOT=34→`0xA2`, `+`=36→`0xA4`, `-`=37→`0xA5`,
  `>`=43→`0xAB`, SGN=46→`0xAE`, `&`=73→`0xC9`);
* диспетчер встроенных ФУНКЦИЙ `0x0B09`: `LXI B,2770h / DAD B / MOV C,M /
  INX H / MOV H,M / MOV L,C / PCHL` — вычислительный прыжок по двухбайтовой
  таблице; индекс = `токен − 0AEh` = `номер слова − 46`, смещение ×2;
* таблица адресов `0x2770` — **28 записей** (слова 46..73, `SGN … &`); запись
  28 (`0x27A8` = `8379h`) лежит вне образа ⇒ длина ровно 28. Запись 26 (`AT`)
  = `0x0074` — page-zero заглушка «не реализовано» (`MVI E,02 / XRA A / STA
  03E7`), а не функция.

ВАЖНО: это НЕ диспетчер команд. Команды (`CLS..CLEAR`, токены `0x80..0x99`)
диспетчируются НЕ таблицей адресов — единственные `LXI`-ссылки на таблицы
ведут в `0x2770` (функции) и в текст слов; ни один из 18 `PCHL` образа, кроме
`0x0B09`, диспетчером не является. Механизм исполнения команд остаётся
открытым пунктом Stage 2 (см. отчёт).

Из-за `PCHL` обработчики функций статически недостижимы — каркас заводит их
вручную, сверяя адрес каждой записи с образом. Имена — по ролям ТЗ.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage2_dispatch_table.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage2_dispatch_table.py --apply
"""
from __future__ import annotations

import argparse
import os
import re
import sys

from analyze.mcp_session import addr_hex, bytes_of, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

KEYWORD_TABLE = 0x256E        # таблица слов (токенов)
KEYWORD_END = 0x26D7          # первый байт после 101-го слова
KEYWORD_COUNT = 101
KEYWORD_FIRST_TOKEN = 0x80    # токен CLS; номер слова = токен − 0x80
WORD_FIRST_FUNC = 46          # SGN — первое слово функции; токен 0xAE

DISPATCH_ROUTINE = 0x0B09     # вычислительный прыжок (PCHL)
DISPATCH_TABLE = 0x2770       # таблица адресов обработчиков ФУНКЦИЙ
DISPATCH_COUNT = 28           # записей (слова 46..73)
DISPATCH_STRIDE = 2
ERROR_STUB = 0x0074           # page-zero «не реализовано» (запись AT)

# Ключевое слово BASIC: латиница в верхнем регистре и символы синтаксиса.
# Нужна только для проверки границ таблицы слов (факт, не семантика).
PLAUSIBLE_RE = re.compile(r"^[A-Z0-9$()&+\-*/^=<>@ ]{1,8}\Z")

# (func_index, слово, токен, обработчик, имя, код-доказательство)
# func_index = индекс записи таблицы; номер слова = 46 + func_index.
ERROR_STUB_INDEX = 26  # AT -> 0x0074, функцию не заводим
FUNCS = [
    (0, "SGN", 0xAE, 0x148D, "func_sgn",
     "RST 28 / MVI B,88 / LXI D,0000 / LXI H,4050 — знак по экспоненте FAC."),
    (1, "INT", 0xAF, 0x156C, "func_int",
     "LXI H,4050 / MOV A,M / CPI 98 / LDA 404D / RNC — отброс дроби по экспоненте."),
    (2, "ABS", 0xB0, 0x14A1, "func_abs",
     "RST 28 / RP / LXI H,404F / MOV A,M / XRI 80 / MOV M,A — сброс знакового бита FAC."),
    (3, "USR", 0xB1, 0x280E, "func_usr",
     "CALL 0531 (проверка вещественного) / ... — вызов пользовательской функции."),
    (4, "FRE", 0xB2, 0x0D6E, "func_fre",
     "LHLD 0CB3 / XCHG / LXI H,0000 / DAD SP — объём свободной памяти (границы кучи/стека)."),
    (5, "INP", 0xB3, 0x109C, "func_inp",
     "CALL 10CA / IN 00 — ввод байта из порта."),
    (6, "POS", 0xB4, 0x0D92, "func_pos",
     "CALL 3DEC / MOV C,A / XRA A — позиция курсора (обёртка над 3DEC)."),
    (7, "SQR", 0xB5, 0x179E, "func_sqr",
     "CALL 14AB / LXI H,1783 (конст. 0.5) / CALL 14BB — корень как степень 0.5."),
    (8, "RND", 0xB6, 0x1878, "func_rnd",
     "RST 28 / JM 1895 / LXI H,3DFC / CALL 14BB — ПСЧ (состояние в 3DFC)."),
    (9, "LOG", 0xB7, 0x1267, "func_log",
     "RST 28 / ORA A / JPE 0539 / LXI H,4050 / MOV A,M — натуральный логарифм."),
    (10, "EXP", 0xB8, 0x17E3, "func_exp",
     "CALL 14AB / LXI B,8138 / LXI D,AA38 — экспонента (константы мантисс)."),
    (11, "COS", 0xB9, 0x18BB, "func_cos",
     "LXI H,1901 / CALL 1103 / CALL 14AB — косинус (ряд, константа 1901)."),
    (12, "SIN", 0xBA, 0x18C1, "func_sin",
     "CALL 14AB / LXI B,8349 / LXI D,0FDB / ... CALL 156C(INT) — синус (ряд)."),
    (13, "TAN", 0xBB, 0x191E, "func_tan",
     "CALL 14AB / CALL 18C1(SIN) / ... CALL 18BB(COS) / JMP 13B6 — тангенс = SIN/COS."),
    (14, "ATN", 0xBC, 0x1933, "func_atn",
     "RST 28 / CM 1799 / CM 14A3 / LDA 4050 — арктангенс (ветвление по знаку FAC)."),
    (15, "PEEK", 0xBD, 0x197D, "func_peek",
     "CALL 0531 / CALL 1987 / LDAX D / JMP 0D95 — чтение байта по адресу (LDAX D)."),
    (16, "LEN", 0xBE, 0x100B, "func_len",
     "LXI B,0D95 / PUSH B / CALL 0FE2 — длина строки."),
    (17, "STR$", 0xBF, 0x0E40, "func_str",
     "CALL 09A1 / CALL 16AD / CALL 0E71 — число → строка."),
    (18, "VAL", 0xC0, 0x10D6, "func_val",
     "CALL 100F / JZ 119A / MOV E,A / INX H / INX H / MOV A,M — строка → число."),
    (19, "ASC", 0xC1, 0x101A, "func_asc",
     "CALL 100F / INX H / INX H / MOV E,M / MOV D,M / LDAX D — код первого символа."),
    (20, "CHR$", 0xC2, 0x102B, "func_chr",
     "MVI A,01 / CALL 0E65 / CALL 10CA — символ по коду."),
    (21, "LEFT$", 0xC3, 0x103B, "func_left",
     "CALL 10B6 / XTHL / MOV C,A / MOV A,M / CMP B — левая подстрока (ветка lbl_0ae8)."),
    (22, "RIGHT$", 0xC4, 0x106B, "func_right",
     "CALL 10B6 / POP D / LDAX D / SUB B / JMP 103F — правая подстрока."),
    (23, "MID$", 0xC5, 0x1075, "func_mid",
     "XCHG / MOV A,M / CALL 10B9 / PUSH B / MVI E,FF / CPI 29 — средняя подстрока."),
    (24, "POINT", 0xC6, 0x1C9C, "func_point",
     "CALL 10CA / CALL 1CA5 / JMP 0D95 — точка экрана (графика)."),
    (25, "INKEY$", 0xC7, 0x1A4D, "func_inkey",
     "CALL 2C40 (клавиатура) / ORA A / MOV E,A / JP 1A5F — символ с клавиатуры."),
    # индекс 26 (AT) -> 0x0074 — заглушка, функцию не заводим
    (27, "&", 0xC9, 0x15FA, "func_amp",
     "POP H / DCX H / LXI D,0000 / RST 10 / JC 160F — конкатенация строк (&)."),
]


def read(session, addr, length):
    """Байты образа по адресу (через отладчик, без прямого чтения файла)."""
    return bytes_of(session.call("debug_read_memory_range",
                                 {"address": addr, "length": length}))


def walk_words(data, base, count):
    """Пройти `count` слов кодировки «bit7 = конец»; вернуть [(addr, слово, следующий)]."""
    out = []
    pos = 0
    for _ in range(count):
        chunk = bytearray()
        while True:
            b = data[pos]
            chunk.append(b & 0x7F)
            pos += 1
            if b & 0x80:
                break
        out.append((base + pos - len(chunk), chunk.decode("latin-1"),
                    base + pos))
    return out


def func_comment(fi, word, token, handler):
    return ("Обработчик встроенной ФУНКЦИИ `%s` — токен %s (номер слова %d в "
            "`data_keyword_table`). Адрес — запись %d таблицы `data_dispatch_table` "
            "(%s); вход по `PCHL` из `func_exec_dispatch` (индекс = токен − %s), "
            "статически недостижим. Семантика (что читает из потока токенов, как "
            "двигает текстовый указатель, что пишет в page-zero) уточняется на "
            "Stage 2."
            % (word, addr_hex(token), WORD_FIRST_FUNC + fi, fi,
               addr_hex(DISPATCH_TABLE), addr_hex(WORD_FIRST_FUNC + 0x80)))


def check(session):
    """Сверить таблицы слов и адресов с образом; вернуть список расхождений."""
    problems = []
    words = walk_words(read(session, KEYWORD_TABLE, KEYWORD_END - KEYWORD_TABLE),
                       KEYWORD_TABLE, KEYWORD_COUNT)
    # Функционные слова 46..73 обязаны совпасть с подписями.
    for fi, word, token, handler, name, _ev in FUNCS:
        got = words[WORD_FIRST_FUNC + fi][1]
        if got != word:
            problems.append("слово %d (%s): образ даёт %r, ожидаем %r"
                            % (WORD_FIRST_FUNC + fi, addr_hex(token), got, word))
    # Слова после таблицы функций (74..100) — расширения, обязаны быть ключевыми.
    for i in range(WORD_FIRST_FUNC + DISPATCH_COUNT, KEYWORD_COUNT):
        if not PLAUSIBLE_RE.match(words[i][1]):
            problems.append("слово %d (%s) %r не похоже на ключевое — граница "
                            "таблицы %s под вопросом"
                            % (i, addr_hex(words[i][0]), words[i][1],
                               addr_hex(KEYWORD_END)))
    # Правая граница таблицы слов: сразу за ней обязан быть мусор.
    extra = walk_words(read(session, KEYWORD_END, 16), KEYWORD_END, 3)
    if all(PLAUSIBLE_RE.match(item[1]) for item in extra):
        problems.append("за %s читаются ещё %d правдоподобных слов — граница "
                        "таблицы слов неверна" % (addr_hex(KEYWORD_END), len(extra)))

    # Таблица адресов функций: записи 0..27 совпадают с обработчиками.
    raw = read(session, DISPATCH_TABLE, DISPATCH_STRIDE * DISPATCH_COUNT)
    for fi, word, token, handler, name, _ev in FUNCS:
        if fi == ERROR_STUB_INDEX:
            got = raw[2 * fi] | (raw[2 * fi + 1] << 8)
            if got != ERROR_STUB:
                problems.append("dispatch[%d] (AT): ожидаем заглушку %s, образ "
                                "даёт %s" % (fi, addr_hex(ERROR_STUB), addr_hex(got)))
            continue
        got = raw[2 * fi] | (raw[2 * fi + 1] << 8)
        if got != handler:
            problems.append("dispatch[%d] (%s): образ даёт %s, ожидаем %s"
                            % (fi, word, addr_hex(got), addr_hex(handler)))
    # Граница таблицы: запись 28 (за последним) обязана быть вне образа.
    beyond = read(session, DISPATCH_TABLE + DISPATCH_STRIDE * DISPATCH_COUNT, 2)
    nxt = beyond[0] | (beyond[1] << 8)
    if nxt <= 0x42FF:
        problems.append("запись %d = %s похожа на адрес внутри образа — длина "
                        "таблицы 28 под вопросом" % (DISPATCH_COUNT, addr_hex(nxt)))
    return problems


def _ensure_function(writer, session, handler, name, log):
    """Создать/переименовать/переквалифицировать обработчик в `function`."""
    current = writer.exists(handler)
    ctype = (current or {}).get("type")
    if ctype and ctype not in ("function", "code"):
        # метка/данные → функция одним update, чтобы не потерять links/properties
        session.call("debug_update_rdb_object",
                     {"address": handler, "name": name, "type": "function",
                      "size": to_addr((current or {}).get("size") or 0)})
        writer.actions.append({"kind": "retype",
                               "tool": "debug_update_rdb_object",
                               "arguments": {"address": handler, "name": name,
                                             "type": "function"}})
        log.append("%s: %s -> функция %s (был тип %s)"
                   % (addr_hex(handler), current.get("name"), name, ctype))
    else:
        action = writer.ensure_object(handler, name, "function", size=0,
                                      rename=True)
        if action.get("created"):
            log.append("%s: создана функция %s" % (addr_hex(handler), name))
        elif (current or {}).get("name") != name:
            log.append("%s: переименована %s -> %s"
                       % (addr_hex(handler), current.get("name"), name))
        else:
            log.append("%s: %s без изменений" % (addr_hex(handler), name))


def apply(session, writer):
    """Завести каркас: таблицы слов/адресов, диспетчер функций, обработчики."""
    log = []
    # 1. Таблица слов.
    writer.ensure_object(KEYWORD_TABLE, "data_keyword_table", "table",
                         size=KEYWORD_END - KEYWORD_TABLE, rename=True)
    writer.set_comment(KEYWORD_TABLE,
                       "Таблица ключевых слов BASIC: %d слов, кодировка "
                       "«посимвольно, bit7 = конец слова». Токен = %s + номер "
                       "слова (CLS=0 … CIRCLE=100). Слова 46..73 (SGN..&) — "
                       "встроенные функции, их исполняет %s."
                       % (KEYWORD_COUNT, addr_hex(KEYWORD_FIRST_TOKEN),
                          addr_hex(DISPATCH_TABLE)))
    writer.set_property(KEYWORD_TABLE, "words", KEYWORD_COUNT)
    writer.set_property(KEYWORD_TABLE, "encoding", "bit7=end-of-word")
    writer.set_property(KEYWORD_TABLE, "token_base", addr_hex(KEYWORD_FIRST_TOKEN))

    # 2. Таблица адресов функций.
    writer.ensure_object(DISPATCH_TABLE, "data_dispatch_table", "table",
                         size=DISPATCH_STRIDE * DISPATCH_COUNT, rename=True)
    writer.set_comment(DISPATCH_TABLE,
                       "Таблица адресов обработчиков встроенных ФУНКЦИЙ "
                       "(%d записей по %d байта, little-endian, слова 46..73 = "
                       "SGN..&). Индекс = токен − %s = номер слова − %d. Запись "
                       "%d (AT) = %s — page-zero заглушка «не реализовано», не "
                       "функция. Запись %d (%s) лежит вне образа — граница "
                       "таблицы. КОМАНДЫ (CLS..CLEAR, токены 0x80..0x99) здесь "
                       "НЕ диспетчатся — их механизм остаётся открытым."
                       % (DISPATCH_COUNT, DISPATCH_STRIDE,
                          addr_hex(WORD_FIRST_FUNC + 0x80), WORD_FIRST_FUNC,
                          ERROR_STUB_INDEX, addr_hex(ERROR_STUB), DISPATCH_COUNT,
                          addr_hex(0x8379)))
    writer.set_property(DISPATCH_TABLE, "entries", DISPATCH_COUNT)
    writer.set_property(DISPATCH_TABLE, "stride", DISPATCH_STRIDE)
    writer.set_property(DISPATCH_TABLE, "index_formula", "token - 0AEh = word - 46")
    writer.set_property(DISPATCH_TABLE, "covers", "built-in functions SGN..& (words 46..73)")

    # 3. Диспетчер функций.
    writer.ensure_object(DISPATCH_ROUTINE, "func_exec_dispatch", "function",
                         rename=True)
    writer.set_comment(DISPATCH_ROUTINE,
                       "Диспетчер встроенных ФУНКЦИЙ: `LXI B,%s / DAD B / MOV C,M "
                       "/ INX H / MOV H,M / MOV L,C / PCHL` — вычислительный "
                       "прыжок по `data_dispatch_table`, индекс = токен − %s "
                       "(смещение ×2). Достигается из оценщика выражений (`lbl_0ad0` "
                       "после `sui 0aeh`). ВНИМАНИЕ: это НЕ диспетчер команд — "
                       "исполнение операторов CLS..CLEAR идёт иным путём (не "
                       "вскрыт, открытый пункт Stage 2)."
                       % (addr_hex(DISPATCH_TABLE), addr_hex(WORD_FIRST_FUNC + 0x80)))
    writer.set_property(DISPATCH_ROUTINE, "role", "function_dispatch")
    writer.set_property(DISPATCH_ROUTINE, "index_formula", "token - 0AEh")
    writer.add_link(DISPATCH_ROUTINE, DISPATCH_TABLE)

    # 4. Обработчики функций.
    for fi, word, token, handler, name, evidence in FUNCS:
        if fi == ERROR_STUB_INDEX:
            log.append("%s (AT): запись %s — заглушка «не реализовано», функцию "
                       "не заводим" % (word, addr_hex(ERROR_STUB)))
            continue
        _ensure_function(writer, session, handler, name, log)
        writer.set_property(handler, "role", "function_handler")
        writer.set_property(handler, "function", word)
        writer.set_property(handler, "token", addr_hex(token))
        writer.set_property(handler, "word_index", WORD_FIRST_FUNC + fi)
        writer.set_property(handler, "dispatch_index", fi)
        writer.set_comment(handler, "%s %s — токен %s (запись %d). %s"
                           % (name, word, addr_hex(token), fi, evidence))
        writer.add_link(DISPATCH_ROUTINE, handler)
    return log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--rdb", default=DEFAULT_RDB)
    ap.add_argument("--check", action="store_true", help="только сверка таблиц")
    ap.add_argument("--apply", action="store_true", help="сверка + запись каркаса")
    args = ap.parse_args(argv)
    if not (args.check or args.apply):
        args.check = True

    rdb_path = os.path.abspath(args.rdb)
    session, _cache = open_session(rom=args.rom, org=0x0000)
    try:
        # RDB обязан быть тот же, что и у сессии отладчика: save пути не принимает
        info = session.call("debug_get_rdb_info")
        if os.path.abspath(info.get("path") or "") != rdb_path:
            raise SystemExit("RDB в сессии %r, ожидаем %r — сначала debug_load_rom "
                             "нужного образа" % (info.get("path"), args.rdb))
        problems = check(session)
        for line in problems:
            print("РАСХОЖДЕНИЕ: " + line, file=sys.stderr)
        if problems:
            return 1
        print("таблицы сверены: слов %d, функций %d (заглушек 1), расхождений 0"
              % (KEYWORD_COUNT, len(FUNCS)))
        if not args.apply:
            return 0
        writer = RdbWriter(session)
        for line in apply(session, writer):
            print("  " + line)
        writer.save()
        print("итог: %s" % (writer.summary(),))
        info = session.call("debug_get_rdb_info")
        print("объектов в RDB: %s, dirty: %s"
              % (info.get("object_count"), info.get("dirty")))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
