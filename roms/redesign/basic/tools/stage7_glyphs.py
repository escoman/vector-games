#!/usr/bin/env python3
"""Stage 7: знакоместо (char generator) -> data_glyph_block + asm/glyphs.inc.

Главный результат — найден и закреплён блок знакогенератора:

  * адрес `0x379F`, размер `640` = 128 глифов x 5 байт;
  * ФОРМАТ: байт = вертикальный СТОЛБЕЦ (x=0..4), биты = строки,
    bit0 = ВЕРХ ... bit7 = низ; ШРИФТ 5x7 (bit0 — служебный пустой верхний
    ряд-зазор, забит лишь у полуграф. #6); индекс глифа = код символа & 0x7F;
  * читается НА МЕСТЕ из загруженного образа (runtime 0x379F == файл; область
    0x6000 = нули => boot НЕ копирует шрифт в RAM; гипотеза vram_credits про
    RAM-блок 0x6000 для этого ROM ошибочна).

Доказательство базы и шага — статикой по рутине печати:
  * `func_term_putc` (`0x3E9F`/`0x3EA0`) -> путь `lbl_3d4d`:
    `MOV C,A / MVI B,00 / LXI H,379Fh / DAD B x5` => адрес глифа = `0x379F + 5*код`,
    затем `XCHG / PUSH D` (адрес глифа сохраняется);
  * `func_render_glyph` (`0x2BEB`, был `func_2beb`): `LHLD 3D8D` (VRAM-курсор),
    `MVI B,05` и цикл `CALL func_render_glyph_column; INR C; DCR B` — 5 колонок;
  * `func_render_glyph_column` (`0x327A`, был `func_327a`): пишет колонку в 4
    плоскости VRAM шагом `LXI B,2000h` (`DAD B` между записями).

Подтверждение сетки/содержимого:
  * `glyph_scan` (mono, width 8, height 5, stride 5) даёт читаемый ASCII;
    код == индекс (пробел на 32 пуст, NUL на 0 пуст, 127 = сплошной блок);
  * граница блока: `0x379F + 640 = 0x3A1F` — упирается ровно в уже закреплённый
    `var_irq_prescaler` (`0x3A1F`), перекрытия нет;
  * ЖИВОЙ тест: на READY набраны `B`/`C`/`D` — символы появились на кадре
    (печать идёт из этого блока).

В образе ОДНА 128-глифовая растровая таблица: 0..31 полуграфика, 32 пробел,
33..95 ASCII (цифры, знаки, латиница A..Z), 96..126 КИРИЛЛИЦА А..Я (без Ъ/Ё,
порядок — перестановка), 127 блок. Строчных латинских глифов НЕТ — кириллица
занимает верхнюю половину кодовой страницы. Отдельного кириллического битмапа
нет => РУС/ЛАТ делается на уровне токенизатора (Stage 5), а не второй таблицей
шрифта.

Создаёт 1 объект `data`, переименовывает 2 существующие функции (роли печати),
обогащает комментарий `func_term_putc`, вешает ссылку putc->шрифт и пишет
`asm/glyphs.inc` (DEFB по глифу с ASCII-комментарием).

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage7_glyphs.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage7_glyphs.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"
DEFAULT_INC = "roms/redesign/basic/asm/glyphs.inc"

GLYPH_ADDR = 0x379F
GLYPH_COUNT = 128
GLYPH_STRIDE = 5
GLYPH_SIZE = GLYPH_COUNT * GLYPH_STRIDE          # 640 = 0x280

# ---- создаваемый объект данных -------------------------------------------
DATA_OBJECTS = {
    GLYPH_ADDR: {
        "name": "data_glyph_block", "size": GLYPH_SIZE, "role": "char_generator",
        "note": "ЗНАКОГЕНЕРАТОР (char generator): 128 глифов x 5 байт = 640 "
                "(0x379F..0x3A1E). Формат: байт = вертикальный столбец (x=0..4), "
                "биты = строки, bit0=верх..bit7=низ; ШРИФТ 5x7 (bit0 — служебный "
                "пустой верхний ряд-зазор, забит лишь у полуграф. #6); индекс = код "
                "символа & 0x7F. Набор: 0..31 полуграфика, 32 пробел, 33..95 ASCII "
                "(цифры/знаки/латиница A..Z), 96..126 КИРИЛЛИЦА А..Я (без Ъ/Ё), 127 "
                "блок; строчных латинских НЕТ. Читается НА МЕСТЕ из образа (без "
                "boot-копирования: 0x6000=нули). Потребитель: func_term_putc "
                "вычисляет адрес глифа `LXI H,379F / DAD B x5` (=база+5*код) -> "
                "func_render_glyph (0x2BEB, цикл MVI B,05) -> func_render_glyph_column "
                "(0x327A, письмо в 4 плоскости VRAM шагом 0x2000). Подтверждено "
                "glyph_scan, границей (0x3A1F = var_irq_prescaler), живым вводом и "
                "PNG-рендером всех 128 глифов.",
        "properties": {
            "glyphs": GLYPH_COUNT, "stride": GLYPH_STRIDE,
            "layout": "col5x7_bit0top_bit0blank", "code_mask": "0x7F",
            "source": "in-place (no boot copy)",
            "charset": "0-31 graph; 32 space; 33-95 ASCII; 96-126 Cyrillic; 127 block",
        },
    },
}

# ---- переименование существующих функций (роль печати) -------------------
RENAMES = {
    0x2BEB: {
        "name": "func_render_glyph", "role": "render_glyph",
        "note": "ОТРИСОВКА ГЛИФА СИМВОЛА В VRAM (был func_2beb). LHLD 3D8D "
                "(адрес текстового курсора в плоскостях), MVI A,0F8/ADD L, MOV C,H, "
                "MVI B,05 -> цикл CALL func_render_glyph_column / INR C / DCR B "
                "(5 колонок). Зовётся из refresh-контура терминала label_2C21 "
                "(рядом func_kbd_dequeue, опрос var_irq_prescaler bit3). Источник "
                "бит глифа — data_glyph_block (адрес готовит func_term_putc).",
    },
    0x327A: {
        "name": "func_render_glyph_column", "role": "render_glyph_column",
        "note": "ЗАПИСЬ ОДНОЙ КОЛОНКИ ГЛИФА в 4 плоскости VRAM (был func_327a). "
                "Берёт байт колонки, раскладывает биты по плоскостям: LXI B,2000h / "
                "DAD B — шаг между плоскостями (0x8000=plane3..0xE000=plane0). "
                "Вызывается 5 раз из func_render_glyph (по одной на колонку).",
    },
}

# ---- обогащение существующего объекта (без смены имени) ------------------
UPDATES = {
    0x3E9F: {
        "name": "func_term_putc", "role": "terminal_putc",
        "note": "func_term_putc — ВВОД СИМВОЛА В ТЕРМИНАЛ (putchar->putc). Маскирует "
                "код `MVI A,7FH / ANA C` (128 глифов) и вычисляет адрес глифа в "
                "data_glyph_block: `LXI H,379Fh / DAD B x5` (=база + 5*код, путь "
                "lbl_3d4d), сохраняет (XCHG/PUSH D) и передаёт управление на отрисовку "
                "func_render_glyph (0x2BEB). Обработчики спец-кодов (CURSOR/ inversion) "
                "на lbl_3d36/lbl_3d44. Источник растровых глифов — data_glyph_block "
                "0x379F (Stage 7).",
    },
}

# ---- ссылки: putc читает знакогенератор ---------------------------------
LINKS = [(0x3E9F, GLYPH_ADDR)]


def _fmt_byte(b):
    """0xAA -> '0AAh', 0x03 -> '03h' (ведущий 0 только при старте с A..F)."""
    h = "%02X" % b
    return ("0" + h if h[0] in "ABCDEF" else h) + "h"


# КИРИЛЛИЧЕСКИЕ глифы занимают коды 96..126 (порядок — перестановка, НЕ подряд
# А..Я); строчных латинских в этом знакогенераторе нет. Буквы Ъ и Ё отсутствуют.
CYRILLIC = {
    96: "Ю", 97: "А", 98: "Б", 99: "Ц", 100: "Д", 101: "Е", 102: "Ф", 103: "Г",
    104: "Х", 105: "И", 106: "Й", 107: "К", 108: "Л", 109: "М", 110: "Н",
    111: "О", 112: "П", 113: "Я", 114: "Р", 115: "С", 116: "Т", 117: "У",
    118: "Ж", 119: "В", 120: "Ь", 121: "Ы", 122: "З", 123: "Ш", 124: "Э",
    125: "Щ", 126: "Ч",
}


def glyph_name(code):
    if code == 0:
        return "пусто (NUL)"
    if code == 32:
        return "пробел"
    if code == 127:
        return "сплошной блок"
    if code in CYRILLIC:
        return "кириллица '%s'" % CYRILLIC[code]
    if 33 <= code <= 126:
        return "символ '%s'" % chr(code)
    return "полуграфика/символ #%d" % code


def generate_inc(rom_path, inc_path):
    """Собрать asm/glyphs.inc: DEFB по глифу, комментарий = код + символ."""
    with open(rom_path, "rb") as fh:
        image = fh.read()
    base = GLYPH_ADDR
    lines = [
        "; Данные: data_glyph_block  (знакоместо / char generator)",
        "; Адрес: %s" % addr_hex(base),
        "; Размер: %d байт (%s..%s; следующий объект var_irq_prescaler @%s)"
        % (GLYPH_SIZE, addr_hex(base), addr_hex(base + GLYPH_SIZE - 1),
           addr_hex(base + GLYPH_SIZE)),
        "; Формат: %d глифов x %d байт. Байт = вертикальный столбец (x=0..4);"
        % (GLYPH_COUNT, GLYPH_STRIDE),
        ";   биты = строки, ШРИФТ 5x7: bit0 = служебный пустой верхний ряд-зазор",
        ";   (забит лишь у полуграф. #6), видимое содержимое в bit1..bit7 (bit7=низ);",
        ";   индекс = код & 0x7F.",
        "; Набор: 0..31 полуграфика; 32 пробел; 33..95 ASCII (цифры, знаки, A..Z);",
        ";   96..126 КИРИЛЛИЦА А..Я (без Ъ/Ё, порядок — перестановка); 127 блок.",
        ";   Строчных латинских глифов НЕТ.",
        "; Источник: читается на месте из образа (boot НЕ копирует в RAM; 0x6000=нули).",
        "; Потребитель: func_term_putc (LXI H,379F / DAD B x5 = база+5*код) ->",
        ";   func_render_glyph (0x2BEB) -> func_render_glyph_column (0x327A, 4 плоскости).",
        "; VERIFIED: glyph_scan + живой ввод + PNG-рендер всех 128 глифов",
        ";   (reports/glyphs_chart.png); runtime 0x379F == образ; граница 0x3A1F.",
        "",
        "data_glyph_block:",
    ]
    for code in range(GLYPH_COUNT):
        off = base + code * GLYPH_STRIDE
        row = image[off:off + GLYPH_STRIDE]
        body = ", ".join(_fmt_byte(b) for b in row)
        comment = "; %3d 0x%02X  %s" % (code, code, glyph_name(code))
        lines.append("    DEFB %-20s %s" % (body, comment))
    os.makedirs(os.path.dirname(os.path.abspath(inc_path)), exist_ok=True)
    with open(inc_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return inc_path, len(lines)


def _ensure_data(writer, addr, spec):
    """Создать/привести адрес к объекту kind=data."""
    current = writer.exists(addr)
    ctype = (current or {}).get("type")
    cur_name = (current or {}).get("name")
    if not current or not current.get("address"):
        writer.ensure_object(addr, spec["name"], "data", size=spec["size"])
        return "create"
    if ctype != "data" or (cur_name != spec["name"]):
        writer.ensure_object(addr, spec["name"], "data", size=spec["size"],
                             rename=True)
        return "retype" if ctype != "data" else "rename"
    return "noop"


def plan(writer):
    rows = []
    for addr, spec in DATA_OBJECTS.items():
        current = writer.exists(addr)
        ctype = (current or {}).get("type") or "нет"
        cur = (current or {}).get("name") or "—"
        rows.append((addr, "CREATE", cur, ctype, spec["name"], "data"))
    for addr, spec in RENAMES.items():
        current = writer.exists(addr)
        ctype = (current or {}).get("type") or "нет"
        cur = (current or {}).get("name") or "—"
        rows.append((addr, "RENAME", cur, ctype, spec["name"], "function"))
    for addr, spec in UPDATES.items():
        current = writer.exists(addr)
        ctype = (current or {}).get("type") or "нет"
        cur = (current or {}).get("name") or "—"
        rows.append((addr, "UPDATE", cur, ctype, spec["name"], ctype))
    return rows


def apply(writer):
    log = []
    for addr, spec in DATA_OBJECTS.items():
        act = _ensure_data(writer, addr, spec)
        writer.set_property(addr, "role", spec["role"])
        for key, value in spec.get("properties", {}).items():
            writer.set_property(addr, key, value)
        writer.set_comment(addr, "%s — %s" % (spec["name"], spec["note"]))
        log.append("%s: %s data %s" % (addr_hex(addr), act, spec["name"]))
    for addr, spec in RENAMES.items():
        if not writer.exists(addr):
            log.append("%s: ПРОПУСК rename (объект не найден)" % addr_hex(addr))
            continue
        writer.ensure_object(addr, spec["name"], "function", rename=True)
        writer.set_property(addr, "role", spec["role"])
        writer.set_comment(addr, "%s — %s" % (spec["name"], spec["note"]))
        log.append("%s: переименован/подписан -> %s" % (addr_hex(addr), spec["name"]))
    for addr, spec in UPDATES.items():
        if not writer.exists(addr):
            log.append("%s: ПРОПУСК update (объект не найден)" % addr_hex(addr))
            continue
        writer.set_property(addr, "role", spec["role"])
        writer.set_comment(addr, "%s — %s" % (spec["name"], spec["note"]))
        log.append("%s: обновлён комментарий/роль %s" % (addr_hex(addr), spec["name"]))
    for src, dst in LINKS:
        writer.add_link(src, dst)
        log.append("%s -> %s: ссылка (putc читает знакогенератор)"
                   % (addr_hex(src), addr_hex(dst)))
    return log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--rdb", default=DEFAULT_RDB)
    ap.add_argument("--inc", default=DEFAULT_INC)
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
        print("план: %d data + %d rename + %d update (Stage 7)"
              % (len(DATA_OBJECTS), len(RENAMES), len(UPDATES)))
        if args.check:
            for addr, act, cur, ctype, name, want in plan(writer):
                print("  %s %-6s %-22s (%-8s) -> %s [%s]"
                      % (addr_hex(addr), act, cur, ctype, name, want))
            print("  .inc: будет %s (~%d строк)" % (args.inc, GLYPH_COUNT + 12))
            return 0
        for line in apply(writer):
            print("  " + line)
        writer.save()
        inc, nlines = generate_inc(args.rom, args.inc)
        print("  записан %s (%d строк)" % (inc, nlines))
        print("итог: %s" % (writer.summary(),))
        info = session.call("debug_get_rdb_info")
        print("объектов: %s, dirty: %s"
              % (info.get("object_count"), info.get("dirty")))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
