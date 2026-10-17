#!/usr/bin/env python3
"""Stage 8: данные -> keywords.inc / messages.inc / demo.inc + объекты RDB.

Закрепляем три ROM-блока данных (кроме знакогенератора Stage 7):

  * data_keyword_table (`0x256E..0x26D6`, 101 слово) -> asm/keywords.inc;
    объект уже в RDB (Stage 2), здесь лишь обогащаем и выгружаем;
  * пул сообщений об ошибках / промптов (`0x2465..0x256D`, 23 строки)
    -> asm/messages.inc + новый объект data_error_messages;
  * строка автозапуска `COLOR15,0,1:CLS` (`0x4012..0x4021`) -> asm/demo.inc
    + новый объект str_autoload.

КОДИРОВКА СООБЩЕНИЙ (главная находка, подтверждена ЖИВЬЁМ). Сообщения
хранятся НЕ транслитом, а настоящими русскими буквами через знакогенератор
Stage 7: коды 0x60..0x7E в этом ROM — КИРИЛЛИЦА (не строчная латиница).
Поэтому байты «bez» (62 65 7A) печатаются как «БЕЗ», «o{ibka» (6F 7B 69 62
6B 61) — как «ОШИБКА». Ключевые слова внутри сообщения (NEXT, FOR, DATA,
GOSUB, DEF) набраны латиницей старшего регистра (0x41..0x5A = ASCII A..Z).
Тест: на READY набрано `NEXT` -> экран «NEXT БЕЗ FOR ОШИБКА» (строка №0 пула
+ суффикс « ОШИБКА»).

МЕХАНИЗМ ВЫВОДА. func_error_raise (`0x0083`): `LXI H,2465` (база пула) и цикл
`MOV A,M / INX H / ORA A / JP` шагает по строкам (каждая заканчивается байтом
с bit7), отсчитывая индекс от кода ошибки (`MOV A,E / RAR / DCR E` на путях
`MVI E,nn / JMP 0x0083`). Точный источник кода (регистр/подпрограммы 01C5/07B2)
уточняется при портировании; для Stage 8 авторитетно: ПОРЯДОК строк в пуле и
привязка NEXT->строка0 подтверждены.

Спека v2.5 «демо @0x3C60» в этом ROM НЕ подтверждена: по 0x3C60 лежит КОД, а
не программа. Зона `5A xx` — артефакт ZX0-потока, в распакованном basic.r0m
отсутствует. Оба пункта — N/A в отчёте.

Создаёт 2 объекта `data`, обогащает data_keyword_table, пишет 3 .inc-файла.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage8_data.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage8_data.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session
from analyze.rdb import RdbWriter

from stage7_glyphs import CYRILLIC  # карта кодов 96..126 -> кириллица (Stage 7)

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"
ASM_DIR = "roms/redesign/basic/asm"

# ---- адреса блоков -------------------------------------------------------
KEYWORD_ADDR = 0x256E
KEYWORD_END = 0x26D6                    # включительно, 361 байт, 101 слово
MSG_ADDR = 0x2465                       # база пула сообщений
AUTOLOAD_ADDR = 0x4012                  # строка автозапуска
AUTOLOAD_LEN = 16                       # "COLOR15,0,1:CLS" + 0D


# ---- декодирование -------------------------------------------------------
def decode_words(image, lo, hi):
    """Таблица слов: байт=символ, bit7=конец слова. -> [(addr, word)]."""
    out, buf, start = [], [], lo
    for addr in range(lo, hi + 1):
        b = image[addr]
        buf.append(b & 0x7F)
        if b & 0x80:
            out.append((start, bytes(buf).decode("latin1")))
            buf, start = [], addr + 1
    return out


def decode_strings(image, lo, hi):
    """Пул строк: каждая заканчивается байтом с bit7. -> [(addr, raw_bytes)]."""
    out, buf, start = [], [], lo
    for addr in range(lo, hi + 1):
        b = image[addr]
        buf.append(b)
        if b & 0x80:
            out.append((start, bytes(buf)))
            buf, start = [], addr + 1
    if buf:
        out.append((start, bytes(buf)))
    return out


def display(code):
    """Код знакогенератора -> печатаемый символ (кириллица 0x60..0x7E)."""
    if code in CYRILLIC:
        return CYRILLIC[code]
    if code == 0x0D:
        return "\\r"
    if code == 0x0A:
        return "\\n"
    if 32 <= code <= 126:
        return chr(code)
    return "\\x%02X" % code


def render(raw):
    """Сырые байты строки (bit7-терминатор снят) -> человекочитаемый текст."""
    return "".join(display(b & 0x7F) for b in raw)


# ---- классификация строк пула -------------------------------------------
# Русские переводы зафиксированы вручную по живому рендеру + карте Stage 7.
GLOSS = {
    "NEXT bez FOR": "NEXT без FOR",
    "sintaksi~eskaq": "синтаксическая",
    "RETURN bez GOSUB": "RETURN без GOSUB",
    "malo dannyh w DATA": "мало данных в DATA",
    "newernyj argument": "неверный аргумент",
    "perepolnenie": "переполнение",
    "net pamqti": "нет памяти",
    "net stroki": "нет строки",
    "newernyj indeks": "неверный индекс",
    "powtornoe opisanie": "повторное описание",
    "delenie na nolx": "деление на ноль",
    "tolxko w programme": "только в programme",
    "nesootw.dannyh": "несоответствие данных",
    "mal bufer": "мал буфер",
    "X$>255": "X$>255",
    "slovno": "сложно",
    "nelxzq": "нельзя",
    "net DEF": "нет DEF",
    " o{ibka": " ошибка",
}


def classify(plain):
    """Имя метки и род строки: ошибка (str_err_) или промпт (str_prompt_)."""
    if plain in GLOSS:
        return "err"
    return "prompt"


def label_for(plain, idx):
    key = "".join(c if c.isalnum() else "_" for c in plain.strip()).strip("_")
    key = "_".join(w for w in key.split("_") if w)[:24] or "msg"
    kind = classify(plain)
    prefix = "str_err" if kind == "err" else "str_prompt"
    return "%s_%s" % (prefix, key.lower())


def _fmt_byte(b):
    h = "%02X" % b
    return ("0" + h if h[0] in "ABCDEF" else h) + "h"


# ---- генерация .inc ------------------------------------------------------
def gen_keywords(image, path):
    words = decode_words(image, KEYWORD_ADDR, KEYWORD_END)
    lines = [
        "; Данные: data_keyword_table  (таблица ключевых слов BASIC)",
        "; Адрес: %s..%s (%d байт, %d слов)"
        % (addr_hex(KEYWORD_ADDR), addr_hex(KEYWORD_END),
           KEYWORD_END - KEYWORD_ADDR + 1, len(words)),
        "; Формат: байт = символ слова; bit7 последнего байта = конец слова.",
        "; Токен = 0x80 + номер слова (func_tok_tokenize: MOV A,B / ORI 80).",
        "; Потребитель: токенизатор (0x256E, LXI D,256D) и детокенизация LIST.",
        "; Сверено с tools/tokens.md и Basic_Vector-06C.pdf (Приложение 1).",
        "",
        "data_keyword_table:",
    ]
    for i, (addr, word) in enumerate(words):
        body = ", ".join(_fmt_byte(ord(c)) for c in word[:-1])
        last = _fmt_byte(ord(word[-1]) | 0x80)
        body = (body + ", " + last) if body else last
        comment = "; 0x%02X  %-8s  %s" % (0x80 + i, "#" + str(i), word)
        lines.append("    DEFB %-22s %s" % (body, comment))
    _write(path, lines)
    return path, len(lines), len(words)


def gen_messages(image, path):
    hi = KEYWORD_ADDR - 1
    strings = decode_strings(image, MSG_ADDR, hi)
    lines = [
        "; Данные: data_error_messages  (пул сообщений об ошибках и промптов)",
        "; Адрес: %s..%s (%d байт, %d строк)"
        % (addr_hex(MSG_ADDR), addr_hex(strings[-1][0] + len(strings[-1][1]) - 1),
           sum(len(s) for _, s in strings), len(strings)),
        "; Формат: ASCII-байты; старший бит (bit7) ПОСЛЕДНЕГО байта = конец",
        ";   строки; между строками разделителей нет (плотный пул).",
        "; КОДИРОВКА: коды 0x60..0x7E в этом ROM — КИРИЛЛИЦА (знакогенератор",
        ";   Stage 7), поэтому сообщения набраны русскими буквами: байты",
        ";   62 65 7A = «БЕЗ», 6F 7B 69 62 6B 61 = «ОШИБКА». Ключевые слова",
        ";   (NEXT/FOR/DATA/GOSUB/DEF) — латиницей A..Z (0x41..0x5A).",
        "; Вывод: func_error_raise (0x0083): LXI H,2465 и проход пула по",
        ";   bit7-терминаторам, индекс от кода ошибки (RAR/DCR). NEXT->строка0",
        ";   подтверждён живым тестом (экран «NEXT БЕЗ FOR ОШИБКА»).",
        "",
        "data_error_messages:",
    ]
    for idx, (addr, raw) in enumerate(strings):
        plain = "".join(chr(b & 0x7F) for b in raw)
        shown = render(raw)
        lbl = label_for(plain, idx)
        gloss = GLOSS.get(plain)
        comment = "; %s  @%s  #%d" % (lbl, addr_hex(addr), idx)
        if gloss:
            comment += "  [%s]" % gloss
        lines.append("%s:" % lbl)
        body = ", ".join(_fmt_byte(b) for b in raw)
        lines.append("    DEFB %s %s" % (body, comment))
        lines.append("    ;   текст: %r" % shown)
    _write(path, lines)
    return path, len(lines), len(strings)


def gen_demo(image, path):
    raw = image[AUTOLOAD_ADDR:AUTOLOAD_ADDR + AUTOLOAD_LEN]
    text = "".join(chr(b) for b in raw if b != 0x0D)
    lines = [
        "; Данные: str_autoload  (строка автозапуска интерпретатора)",
        "; Адрес: %s..%s (%d байт)"
        % (addr_hex(AUTOLOAD_ADDR),
           addr_hex(AUTOLOAD_ADDR + AUTOLOAD_LEN - 1), AUTOLOAD_LEN),
        "; Природа: data-остров в кодовой области (сразу за JMP @%s)."
        % addr_hex(AUTOLOAD_ADDR - 3),
        "; Исполняется при boot до REPL: задаёт палитру и очищает экран.",
        "; Спека v2.5 «демо-программа @0x3C60» НЕ подтверждена: там код.",
        "; Зона 5A xx — артефакт ZX0-потока, в распакованном образе отсутствует.",
        "",
        "str_autoload:",
        "    DEFB %s   ; %r + CR" % (", ".join(_fmt_byte(b) for b in raw), text),
    ]
    _write(path, lines)
    return path, len(lines), text


def _write(path, lines):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# ---- объекты RDB ---------------------------------------------------------
def _ensure_data(writer, addr, name, size, typ="data"):
    current = writer.exists(addr)
    ctype = (current or {}).get("type")
    cur_name = (current or {}).get("name")
    if not current or not current.get("address"):
        writer.ensure_object(addr, name, typ, size=size)
        return "create"
    if ctype != typ or cur_name != name:
        writer.ensure_object(addr, name, typ, size=size, rename=True)
        return "retype/rename"
    return "noop"


MSG_NOTE = ("ПУЛ СООБЩЕНИЙ ОБ ОШИБКАХ и промптов: 23 строки с 0x2465 (плотный,"
            " каждая заканчивается байтом с bit7). КОДИРОВКА: коды 0x60..0x7E —"
            " КИРИЛЛИЦА (знакогенератор Stage 7), сообщения набраны русскими"
            " буквами (bez=БЕЗ, o{ibka=ОШИБКА); ключевые слова NEXT/FOR/DATA/"
            " GOSUB/DEF — латиницей A..Z. Выводит func_error_raise (0x0083):"
            " LXI H,2465 + проход пула по bit7-терминаторам, индекс от кода"
            " ошибки (RAR/DCR). NEXT->строка0 подтверждён живьём (экран «NEXT"
            " БЕЗ FOR ОШИБКА»). Полный список и переводы — asm/messages.inc.")

AUTOLOAD_NOTE = ("СТРОКА АВТОЗАПУСКА «COLOR15,0,1:CLS» + CR (data-остров в"
                 " коде, сразу за JMP). Исполняется при boot до REPL: задаёт"
                 " палитру и очищает экран. Спека v2.5 «демо @0x3C60» здесь —"
                 " код, не программа; зона 5A — артефакт ZX0-потока (N/A).")

KEYWORD_NOTE = ("ТАБЛИЦА КЛЮЧЕВЫХ СЛОВ: 101 слово, байт=символ, bit7=конец"
                " слова; токен = 0x80 + номер (func_tok_tokenize). Потребители:"
                " токенизатор (LXI D,256D) и детокенизация LIST/LLIST."
                " Полная карта токен<->слово<->обработчик — tools/tokens.md;"
                " построчная выгрузка — asm/keywords.inc.")


def plan(image, writer):
    rows = []
    strings = decode_strings(image, MSG_ADDR, KEYWORD_ADDR - 1)
    msg_size = sum(len(s) for _, s in strings)
    msg_end = strings[-1][0] + len(strings[-1][1]) - 1
    rows.append((MSG_ADDR, "CREATE", "data_error_messages", "data", msg_size,
                 "%s..%s, %d строк" % (addr_hex(MSG_ADDR), addr_hex(msg_end),
                                       len(strings))))
    rows.append((AUTOLOAD_ADDR, "CREATE", "str_autoload", "data", AUTOLOAD_LEN,
                 "COLOR15,0,1:CLS"))
    kw = writer.exists(KEYWORD_ADDR) or {}
    rows.append((KEYWORD_ADDR, "ENRICH", kw.get("name") or "data_keyword_table",
                 kw.get("type") or "table", KEYWORD_END - KEYWORD_ADDR + 1,
                 "комментарий/свойства"))
    return rows


def apply(image, writer):
    log = []
    strings = decode_strings(image, MSG_ADDR, KEYWORD_ADDR - 1)
    msg_size = sum(len(s) for _, s in strings)
    act = _ensure_data(writer, MSG_ADDR, "data_error_messages", msg_size)
    writer.set_property(MSG_ADDR, "role", "error_message_pool")
    writer.set_property(MSG_ADDR, "strings", len(strings))
    writer.set_property(MSG_ADDR, "encoding",
                        "cyrillic via glyph codes 0x60-0x7E; bit7 = EOL")
    writer.set_property(MSG_ADDR, "emitter", "func_error_raise (0x0083)")
    writer.set_comment(MSG_ADDR, "data_error_messages — " + MSG_NOTE)
    log.append("%s: %s data data_error_messages (%d байт, %d строк)"
               % (addr_hex(MSG_ADDR), act, msg_size, len(strings)))

    act = _ensure_data(writer, AUTOLOAD_ADDR, "str_autoload", AUTOLOAD_LEN,
                       typ="string")
    writer.set_property(AUTOLOAD_ADDR, "role", "autoload_program")
    writer.set_property(AUTOLOAD_ADDR, "text", "COLOR15,0,1:CLS")
    writer.set_comment(AUTOLOAD_ADDR, "str_autoload — " + AUTOLOAD_NOTE)
    log.append("%s: %s data str_autoload (COLOR15,0,1:CLS)"
               % (addr_hex(AUTOLOAD_ADDR), act))

    writer.set_property(KEYWORD_ADDR, "role", "keyword_table")
    writer.set_property(KEYWORD_ADDR, "encoding",
                        "byte/char, bit7 = end of word")
    writer.set_property(KEYWORD_ADDR, "token_base", "0x80")
    writer.set_property(KEYWORD_ADDR, "listing", "asm/keywords.inc")
    writer.set_comment(KEYWORD_ADDR, "data_keyword_table — " + KEYWORD_NOTE)
    log.append("%s: обогащён data_keyword_table" % addr_hex(KEYWORD_ADDR))
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
            print("план Stage 8 (data-блоки):")
            for addr, act, name, typ, size, note in plan(image, writer):
                print("  %-6s %s %-22s [%s %d] %s"
                      % (act, addr_hex(addr), name, typ, size, note))
            print("  .inc: keywords.inc / messages.inc / demo.inc")
            return 0
        for line in apply(image, writer):
            print("  " + line)
        writer.save()
        kw = gen_keywords(image, os.path.join(ASM_DIR, "keywords.inc"))
        ms = gen_messages(image, os.path.join(ASM_DIR, "messages.inc"))
        dm = gen_demo(image, os.path.join(ASM_DIR, "demo.inc"))
        print("  записан %s (%d строк, %d слов)" % (kw[0], kw[1], kw[2]))
        print("  записан %s (%d строк, %d сообщений)" % (ms[0], ms[1], ms[2]))
        print("  записан %s (%d строк, %r)" % (dm[0], dm[1], dm[2]))
        print("итог: %s" % (writer.summary(),))
        info = session.call("debug_get_rdb_info")
        print("объектов: %s, dirty: %s"
              % (info.get("object_count"), info.get("dirty")))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
