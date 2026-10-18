#!/usr/bin/env python3
"""Stage 11: закрыть DATA-дыры в RDB (7 объектов, ~1100 байт).

После Stage 10 осталось 48 `gap_XXXX`-блоков на 2962 байт. Часть — чистая
DATA, не поднятая CFG-анализом (`debug_analyze_code` hard-cap 10000 инструкций
+ динамическая диспетчеризация через `JP (HL)`). Здесь заводим РОВНО те
участки, чья природа «данные» подтверждена (байтовый паттерн + потребитель):

    data_render_lut_preamble   0x40FC..0x40FF  (4б)  LE-указатель 0x0B4C
    data_x_to_page_h_lut       0x4100..0x41FF  (256) 0x80 + (X>>3)
    data_x_to_bit_mask_lut     0x4200..0x42FF  (256) 0x80 >> (X&7)
    data_bit_clear_masks       0x3F00..0x3F1F  (32б) маски погашения старших битов
    data_pixel_read_dispatch   0x2132..0x2151  (32б) 16 LE-указателей в POINT-варианты
    var_scratch_high           0x3A23..0x3BB9  (407) RAM scratch (все нули)
    var_scratch_tail           0x3F87..0x4057  (113) RAM scratch (все нули)

Подтверждение LUT (Stage 7 §8.3): дизассемблировали `func_3bd3` (POINT-читалка)
через `debug_disassemble_range` — там `MVI H,41 / MOV D,M` (page_h) и
`INR H / MOV B,M` (bit_mask). Две соседние LUT-страницы `0x41xx/0x42xx` —
текущие. Это ЗАКРЫВАЕТ открытый пункт Stage 7 §7.

`data_bit_clear_masks` — парная таблица, индексируется числом старших бит,
которые надо сбросить; встречается в графических `0x2ABF`/`0x327A` (расчистка
бита = `CMA / AND mask`).

`data_pixel_read_dispatch` — 16 little-endian 2-байтных адресов внутри
`0x3C69..0x3C90` (варианты POINT для каждой из комбинаций 4 плоскостей).
Используется через `MVI A,color / RAL / RAL / ... / DAD H / PCHL` — не CFG.

`var_scratch_high` / `var_scratch_tail` — RAM-области целиком из нулей, идут
сразу за `var_kbd_strobe 0x3A22` и `var_input_buffer 0x3F77+16`. Не переменные
в классическом смысле, но `type=variable` — единственная корректная модель
для «ячеек, которые НЕ код» в текущей RDB-схеме.

Использование:
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage11_data_gaps.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage11_data_gaps.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

# ---- объекты ------------------------------------------------------------
# kind: data | table | variable. Проверяем содержимое по image перед --apply.
OBJECTS = [
    {
        "addr": 0x40FC, "name": "data_render_lut_preamble", "kind": "data",
        "size": 4, "role": "render_lut_preamble",
        "check": lambda img: img[0x40FC:0x4100] == bytes([0x4C, 0x0B, 0x00, 0x00]),
        "note": (
            "ПРЕАМБУЛА пары LUT (0x4100/0x4200). 4C 0B = little-endian 0x0B4C — "
            "самомодифицируемый слот (код-адрес в области LET/eval, gap_0B4C). "
            "Два нулевых байта — padding/second operand. Физически примыкает к "
            "page_h-LUT, потому заводится отдельным 4-байтным объектом."),
        "props": {"preamble_le": "4C 0B 00 00", "points_to": "0x0B4C"},
    },
    {
        "addr": 0x4100, "name": "data_x_to_page_h_lut", "kind": "data",
        "size": 256, "role": "pixel_x_to_vram_page_hi",
        "check": lambda img: all(
            img[0x4100 + X] == 0x80 + (X >> 3) for X in range(256)),
        "note": (
            "LUT: пиксельный X (0..255) -> старший байт адреса плоскости VRAM "
            "= 0x80 + (X>>3). Плоскости E000/C000/A000/8000 покрываются "
            "инкрементом H на 0x20 (=2000h stride) после ADD D. Читается в "
            "func_render_glyph (0x2BEB) и func_3bd3 (POINT) через MVI H,41 / "
            "MOV D,M. Подтверждает Stage 7 §8.3 (открытый пункт §7 закрыт)."),
        "props": {"formula": "0x80 + (X>>3)",
                  "consumer": "func_render_glyph (0x2BEB) / func_3bd3 (POINT)"},
    },
    {
        "addr": 0x4200, "name": "data_x_to_bit_mask_lut", "kind": "data",
        "size": 256, "role": "pixel_x_to_bit_mask",
        "check": lambda img: all(
            img[0x4200 + X] == (0x80 >> (X & 7)) for X in range(256)),
        "note": (
            "LUT: пиксельный X -> битовая маска 0x80 >> (X & 7). Парная к "
            "data_x_to_page_h_lut. Установка бита (чернила) = OR, сброс "
            "(расчистка) = AND ~mask. Читается там же: INR H / MOV B,M. "
            "Подтверждает Stage 7 §8.3."),
        "props": {"formula": "0x80 >> (X & 7)",
                  "consumer": "func_render_glyph (0x2BEB) / func_3bd3 (POINT)"},
    },
    {
        "addr": 0x3F00, "name": "data_bit_clear_masks", "kind": "data",
        "size": 32, "role": "bit_clear_pattern_lut",
        "check": lambda img: img[0x3F00:0x3F20] == bytes([
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0x00, 0xFC, 0x00, 0x7E, 0x00, 0x3F, 0x80, 0x1F,
            0xC0, 0x0F, 0xE0, 0x07, 0xF0, 0x03, 0xF8, 0x01,
            0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01]),
        "note": (
            "Маски «погасить биты сверху» для LINE/CIRCLE (32б = 16 слов). "
            "Паттерн FF*8 | 00FC 007E 003F 801F | C00F E007 F003 F801 | "
            "FF 7F 3F 1F 0F 07 03 01. Используется в паре 0x2ABF/0x327A "
            "(расчистка бита = CMA / ANA D / MOV M,A)."),
        "props": {"layout": "16 слов x 2 байта",
                  "consumer": "graf_clear_bit (0x2ABF / 0x327A)"},
    },
    {
        "addr": 0x2132, "name": "data_pixel_read_dispatch", "kind": "table",
        "size": 32, "role": "pixel_read_dispatch_table",
        "check": lambda img: all(
            0x3C69 <= int.from_bytes(img[0x2132 + 2 * i:0x2132 + 2 * i + 2], "little") <= 0x3C93
            for i in range(16)),
        "note": (
            "16 LE-указателей в POINT-варианты (0x3C69..0x3C90). Индекс — "
            "номер комбинации 4 бит E000/C000/A000/8000 (bit-plane mask). "
            "Прыжок через PCHL после MVI A,idx / RAL / RAL / DAD H. В "
            "code.asm gap_2132 — только первые 32 байта таблица, остальное "
            "код (не покрыт CFG из-за динамического dispatch)."),
        "props": {"entries": 16, "stride": 2,
                  "targets_lo": "0x3C69", "targets_hi": "0x3C93"},
    },
    {
        "addr": 0x3A23, "name": "var_scratch_high", "kind": "variable",
        "size": 407, "role": "ram_scratch_workspace",
        "check": lambda img: all(b == 0 for b in img[0x3A23:0x3A23 + 407]),
        "note": (
            "RAM scratch: 407 байт нолей сразу после var_kbd_strobe 0x3A22. "
            "В boot не инициализируется, автостарт-демо не трогает (memory_diff "
            "не даёт патчей здесь). Заводим как variable — единственный "
            "корректный тип для «не-код» области в RDB-модели."),
        "props": {"init": "none", "region": "high-RAM workspace"},
    },
    {
        "addr": 0x3F87, "name": "var_scratch_tail", "kind": "variable",
        "size": 113, "role": "ram_scratch_tail",
        "check": lambda img: all(b == 0 for b in img[0x3F87:0x3F87 + 113]),
        "note": (
            "RAM scratch: 113 байт нолей сразу после var_input_buffer "
            "(0x3F77+16). Резерв под строку ввода / временные значения. В "
            "диффе не подтверждён (автостарт-демо не трогает)."),
        "props": {"init": "none", "region": "high-RAM workspace"},
    },
]


# ---- plan / apply -------------------------------------------------------
def plan(image, writer):
    rows = []
    for spec in OBJECTS:
        addr = spec["addr"]
        ok = spec["check"](image)
        cur = writer.exists(addr) or {}
        act = "SKIP" if cur.get("address") else ("CREATE" if ok else "CHECK!")
        rows.append((addr, act, spec["name"], spec["kind"], spec["size"],
                     "паттерн ОК" if ok else "ПАТТЕРН НЕ СОВПАЛ",
                     cur.get("name") or ""))
    return rows


def apply(image, writer):
    log = []
    for spec in OBJECTS:
        addr = to_addr(spec["addr"])
        if not spec["check"](image):
            log.append("%s: %s ПРОПУЩЕН — байты образа не совпали с ожидаемым паттерном"
                       % (addr_hex(addr), spec["name"]))
            continue
        cur = writer.exists(addr) or {}
        if cur.get("address"):
            log.append("%s: %s уже в RDB (%s), пропускаем"
                       % (addr_hex(addr), spec["name"], cur.get("name")))
            continue
        writer.ensure_object(addr, spec["name"], spec["kind"], size=spec["size"])
        writer.set_property(addr, "role", spec["role"])
        for k, v in spec["props"].items():
            writer.set_property(addr, k, v)
        writer.set_comment(addr, "%s — %s" % (spec["name"], spec["note"]))
        log.append("%s: CREATE %s %s (%d байт)"
                   % (addr_hex(addr), spec["kind"], spec["name"], spec["size"]))
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
            print("план Stage 11 (DATA-дыры):")
            for addr, act, name, typ, size, note, cur_name in plan(image, writer):
                tail = "  (уже: %s)" % cur_name if cur_name else ""
                print("  %-6s %s %-26s [%-8s %4d] %s%s"
                      % (act, addr_hex(addr), name, typ, size, note, tail))
            return 0
        for line in apply(image, writer):
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
