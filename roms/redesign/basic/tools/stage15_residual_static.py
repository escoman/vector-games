#!/usr/bin/env python3
"""Stage 15: закрыть СТАТИЧЕСКИ подтверждённые residual-дыры в RDB (Phase A).

Состояние на входе: CODE ∪ RDB = 95.95% (остаток 694 байта / 32 блока).
Триаж Phase A (`debug_disassemble_range` + лидирующие байты по `src/basic.r0m`
+ анализ соседей) разложил 32 блока на три категории:

  1. STATIC-CLOSE (этот Stage) — природа доказана статически:
     * EXTEND  — байты принадлежат уже известной функции (пролог/вектор/хвост),
                 RDB просто не записал длину (size=0). Продлеваем до границы
                 следующего объекта: func_0000, func_rst_cmp_dehl,
                 func_rst_fac_sign, func_0e0d, func_str_return, func_cmd_bsave,
                 func_cmd_get.
     * NEW_FUNC — островки кода, недостижимые из CFG (вход через PCHL/выч.
                 адрес). Разобраны ПОЛНО и КОНТИГУНО, заканчиваются ровно на
                 границе блока: func_resume_guard(0x05D3), func_step_guard(0x060B),
                 func_0bbf(0x0BBF), func_133d(0x133D).
     * NEW_DATA — области, дизассемблер даёт байт-суп; подтверждены ссылкой
                 загрузчика (`LXI H,<addr>`) либо явной структурой (count+float,
                 монотонные экспоненты, repeat-byte, zero-run). data_*/str_ →
                 экспортёр печатает DEFB точных байт → round-trip сохранён.
     * NEW_STR  — кириллическое сообщение 0x2079 (KOI8-R/Vector-ширма) → str_.

  2. DEFER→STAGE16 (Phase B, поведенческий трасс) — самомодиф/граф/RAM-scratch,
     статически неотличимы код/данные: 0x27A8, 0x2B01, 0x2B3C, 0x2B58, 0x2C6F,
     0x2D7E, 0x2DDC, 0x3722, 0x3730, 0x3D03, 0x3E00, 0x4027, 0x4029, 0x4053.

  3. (нет) — отказ от ложных func_: heavy-FF/нули без ссылок называем data_/pad.

Правило round-trip: DATA как func_ ломает побайтовую пересборку (дизассемблер
выдаёт мнемоники, собирающиеся в ДРУГИЕ байты); CODE как func_ безопасен ТОЛЬКО
если дизасемблер даёт валидную континуальную инструкцию до границы. Каждый
NEW_FUNC проверен `debug_disassemble_range` (incomplete_instruction=false).
Поэтому при сомнении — data_/var_/defer.

Использование:
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage15_residual_static.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage15_residual_static.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

# ---- действия ------------------------------------------------------------
# action = "extend" (продлить существующий объект до границы следующего) или
#          "create" (новый объект в residual-дыре).
# size   = точная длина (extend — до ge включительно; create — весь блок).
# check  = жёсткая проверка байтов по image (защита от чужого ROM).
#          для extend проверяем лид функции; для create — весь блок байт-в-байт.
ACTIONS = [
    # ==== EXTEND: длина существующей функции не записана (size=0) ====
    {
        "action": "extend", "addr": 0x0000, "name": "func_0000",
        "kind": "function", "size": 8,
        # LXI SP,7FFF / JMP 19CC  (reset-вектор: 31 FF 7F C3 CC 19)
        "check": lambda img: img[0x0000:0x0004] == bytes([0x31, 0xFF, 0x7F, 0xC3]),
        "note": (
            "Reset-вектор: `LXI SP,7FFFh / JMP 19CC`. Гэп 0x0006..0x0007 — хвост "
            "JMP (адрес цели),CFG уже вёл сюда, но RDB не записал длину. След. "
            "объект func_rst_fetch_sep @0x0008 — продление ровно до 0x0007."),
    },
    {
        "action": "extend", "addr": 0x0020, "name": "func_rst_cmp_dehl",
        "kind": "function", "size": 8,
        # 7C 92 C0 B5 (MOV A,H / SUB D / RZ / MOV A,L ...)
        "check": lambda img: img[0x0020:0x0024] == bytes([0x7C, 0x92, 0xC0, 0xB5]),
        "note": (
            "RST 08h: сравнение DE,HL. Гэп 0x0026..0x0027 — хвост (MOV A,L/SUB E/"
            "ретурн-условие). След. объект func_rst_fac_sign @0x0028 — до 0x0027."),
    },
    {
        "action": "extend", "addr": 0x0028, "name": "func_rst_fac_sign",
        "kind": "function", "size": 16,
        # 3A 50 40 B7 (LDA 4050h / ORA B ...)
        "check": lambda img: img[0x0028:0x002C] == bytes([0x3A, 0x50, 0x40, 0xB7]),
        "note": (
            "RST 10h: знак/нормализация FAC. Гэп 0x0035..0x0037 — хвост обработчика. "
            "След. объект func_rst_irq @0x0038 — продление ровно до 0x0037."),
    },
    {
        "action": "extend", "addr": 0x0E0D, "name": "func_0e0d",
        "kind": "function", "size": 51,
        "check": lambda img: img[0x0E0D:0x0E11] == bytes([0xCF, 0xA0, 0x01, 0x3A]),
        "note": (
            "Гэп 0x0E3A..0x0E3F — конец тела func_0e0d (CFG покрыл, RDB длины нет). "
            "След. объект func_str @0x0E40 — продление до 0x0E3F."),
    },
    {
        "action": "extend", "addr": 0x0E97, "name": "func_str_return",
        "kind": "function", "size": 33,
        # 11 49 40 2A (LXI H,4049h / SHLD ...)
        "check": lambda img: img[0x0E97:0x0E9B] == bytes([0x11, 0x49, 0x40, 0x2A]),
        "note": (
            "Гэп 0x0EB4..0x0EB7 — хвост возврата строковой функции. След. объект "
            "func_str_window @0x0ECE — продление до 0x0EB7 (0x0EB8..0x0ECD в CFG)."),
    },
    {
        "action": "extend", "addr": 0x1DED, "name": "func_cmd_bsave",
        "kind": "function", "size": 80,
        # 3E D2 32 8D (MVI A,D2h / STA 8D..)
        "check": lambda img: img[0x1DED:0x1DF1] == bytes([0x3E, 0xD2, 0x32, 0x8D]),
        "note": (
            "Гэп 0x1E3C (1 байт) — последний байт тела BSAVE. След. объект "
            "func_cmd_bload @0x1E3D — продление ровно до 0x1E3C."),
    },
    {
        "action": "extend", "addr": 0x3441, "name": "func_cmd_get",
        "kind": "function", "size": 162,
        # CD 2A 34 E5 (CALL 342A / PUSH H)
        "check": lambda img: img[0x3441:0x3445] == bytes([0xCD, 0x2A, 0x34, 0xE5]),
        "note": (
            "Гэп 0x34DD..0x34E2 — хвост GET (после основного тела CFG дошёл лишь "
            "до 0x34DC). След. объект var_getput_ptr @0x3559 — продление до 0x34E2."),
    },

    # ==== NEW_FUNC: островки кода, недостижимые из CFG ====
    {
        "action": "create", "addr": 0x05D3, "name": "func_resume_guard",
        "kind": "function", "size": 14, "role": "resume_vector_guard",
        "check": lambda img: img[0x05D3:0x05E1] == bytes(
            [0x78, 0x92, 0xC2, 0xE6, 0x05, 0x79, 0x93, 0xC2,
             0xE6, 0x05, 0x21, 0x00, 0x00, 0xC9]),
        "note": (
            "Тест вектора CONTINUE/resume. `MOV A,B / SUB D / JNZ 05E6 / MOV A,C / "
            "SUB E / JNZ 05E6 / LXI H,0000 / RET` — сравнивает BC с DE (=вектор из "
            "var_resume_vector 0x05D1); не равно → уход 0x05E6; равно → HL=0, RET. "
            "Достижим через PCHL-вычислитель, потому вне CFG. Соседи: "
            "var_resume_vector(0x05D1) / func_cmd_goto(0x0602)."),
        "props": {"compares": "BC vs DE (resume vector 0x05D1)",
                  "miss_target": "0x05E6", "cfg_reachable": "no (PCHL entry)"},
    },
    {
        "action": "create", "addr": 0x060B, "name": "func_step_guard",
        "kind": "function", "size": 14, "role": "step_vector_guard",
        "check": lambda img: img[0x060B:0x0619] == bytes(
            [0x78, 0x92, 0xC2, 0x1E, 0x06, 0x79, 0x93, 0xC2,
             0x1E, 0x06, 0x21, 0x00, 0x00, 0xC9]),
        "note": (
            "Тест вектора шага/STOP. Зеркало func_resume_guard: сравнение BC с DE "
            "(=var_step_vector 0x0609), не равно → 0x061E, равно → HL=0, RET. "
            "Соседи: var_step_vector(0x0609) / func_prog_step(0x0619) — семантика "
            "шага подтверждения. Вне CFG (PCHL-вход)."),
        "props": {"compares": "BC vs DE (step vector 0x0609)",
                  "miss_target": "0x061E", "cfg_reachable": "no (PCHL entry)"},
    },
    {
        "action": "create", "addr": 0x0BBF, "name": "func_0bbf",
        "kind": "function", "size": 5, "role": "compare_rst_helper",
        "check": lambda img: img[0x0BBF:0x0BC4] == bytes(
            [0x2B, 0xD7, 0xC8, 0xCF, 0x2C]),
        "note": (
            "Хелпер сравнения: `DCX H / RST 10 / RZ / RST 8 / INR L` — вызывает "
            "RST 10h (func_rst_fac_sign) и RST 8h (func_rst_cmp_dehl), ранний выход "
            "по RZ. Островок кода между lbl_0ba8 и func_cmd_dim; CFG не дошёл "
            "(динамический вход)."),
        "props": {"calls": "RST 08h, RST 10h", "cfg_reachable": "no"},
    },
    {
        "action": "create", "addr": 0x133D, "name": "func_133d",
        "kind": "function", "size": 6, "role": "shift_and_tailjump",
        "check": lambda img: img[0x133D:0x1343] == bytes(
            [0x4C, 0x65, 0x6A, 0xC3, 0x87, 0x11]),
        "note": (
            "Сдвиг тройки байт + хвостовой переход: `MOV C,H / MOV H,L / MOV L,D / "
            "JMP 1187`. Заносит DE:HL в C:HL и передаёт управление 0x1187 (tail). "
            "Между lbl_132f и lbl_1343; CFG не покрыл (вход через выч. адрес)."),
        "props": {"tail_jump": "0x1187", "cfg_reachable": "no"},
    },

    # ==== NEW_DATA: байт-суп у дизассемблера; подтверждено ссылкой/структурой ====
    {
        "action": "create", "addr": 0x0398, "name": "data_0398_table",
        "kind": "data", "size": 9, "role": "small_lookup_table",
        "check": lambda img: img[0x0398:0x03A1] == bytes(
            [0x08, 0x0A, 0x0D, 0x0C, 0x1F, 0x18, 0x19, 0x1A, 0x00]),
        "note": (
            "Малая таблица из 8 элементов + терминатор 00. Дизассемблер даёт мусор "
            "(не инструкции: монотонные малые значения 08 0A 0D 0C 1F 18 19 1A). "
            "Между lbl_0391 и func_cmd_llist."),
        "props": {"format": "8 bytes + 00 terminator", "cfg_reachable": "no"},
    },
    {
        "action": "create", "addr": 0x125A, "name": "data_log_poly_coeffs",
        "kind": "data", "size": 13, "role": "log_polynomial_coefficients",
        "check": lambda img: img[0x125A:0x1267] == bytes(
            [0x03, 0xAA, 0x56, 0x19, 0x80, 0xF1, 0x22, 0x76,
             0x80, 0x45, 0xAA, 0x38, 0x82]),
        "note": (
            "Коэффициенты полинома LN/LOG: байт-счётчик 03 + 3×4-байтных packed-"
            "float (AA 56 19 80 / F1 22 76 80 / 45 AA 38 82; экспоненты 0x80). "
            "Заканчивается ровно на func_log @0x1267 (внутри только данные)."),
        "props": {"record": "count=3 + 3 packed float",
                  "consumer": "func_log (0x1267)"},
    },
    {
        "action": "create", "addr": 0x1783, "name": "data_1783_poly_coeffs",
        "kind": "data", "size": 22, "role": "poly_coefficients_sqr_region",
        "check": lambda img: img[0x1783:0x1799] == bytes(
            [0x00, 0x00, 0x00, 0x80, 0x60, 0x79, 0xFE, 0xF0,
             0xD8, 0xFF, 0x18, 0xFC, 0xFF, 0x9C, 0xFF, 0xFF,
             0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        "note": (
            "Ряд float-коэффициентов в области SQR. Подтверждён ссылкой загрузчика: "
            "`LXI H,1783h` на 0x17A1 (сразу после func_sqr 0x179E). Сам блок "
            "дизассемблируется как байт-суп (RST 38=FF, heavy FF) → данные. Хвост "
            "на func_sqr @0x179E."),
        "props": {"record": "packed float",
                  "loaded_by": "lxi h,1783h (0x17A1, near func_sqr 0x179E)",
                  "cfg_reachable": "no"},
    },
    {
        "action": "create", "addr": 0x2F4F, "name": "data_2f4f_table",
        "kind": "data", "size": 7, "role": "lookup_table",
        "check": lambda img: img[0x2F4F:0x2F56] == bytes(
            [0x12, 0x16, 0x00, 0x04, 0x08, 0x0A, 0x0E]),
        "note": (
            "Малая таблица (00 04 08 0A 0E — арифм. прогрессия + шапка 12 16). "
            "Между lbl_2f3e и lbl_2f56; код-соседи это метки, внутри блока инструкций "
            "нет."),
        "props": {"cfg_reachable": "no"},
    },
    {
        "action": "create", "addr": 0x3518, "name": "data_3518_pad",
        "kind": "data", "size": 7, "role": "repeated_byte_filler",
        "check": lambda img: img[0x3518:0x351F] == bytes(
            [0x29, 0x29, 0x29, 0x29, 0x29, 0x29, 0x29]),
        "note": (
            "Run из 7 одинаковых байт 0x29 — резерв/филлер между func_cmd_get "
            "(0x3441) и var_getput_ptr (0x3559). Не код (DCX H/SUB L повтор = "
            "несвязный), не ссылка. Честно называем filler."),
        "props": {"pattern": "0x29 ×7", "cfg_reachable": "no"},
    },
    {
        "action": "create", "addr": 0x26FC, "name": "data_26fc_pad",
        "kind": "data", "size": 4, "role": "zero_padding",
        "check": lambda img: img[0x26FC:0x2700] == bytes([0, 0, 0, 0]),
        "note": (
            "Выравнивающий zero-run между var_irq_stack_top (0x26F7) и "
            "data_cmd_table (0x2700). 4 нуля → паддинг под таблицу команд."),
        "props": {"pattern": "0x00 ×4", "cfg_reachable": "no"},
    },
    {
        "action": "create", "addr": 0x2079, "name": "str_2079_cyrillic",
        "kind": "string", "size": 35, "role": "cyrillic_message_string",
        "check": lambda img: img[0x2079:0x209C] == bytes(
            [0xC0, 0xA1, 0xA2, 0xB8, 0xA5, 0xA6, 0xB6, 0xA4, 0xB7, 0xAA,
             0xAB, 0xAC, 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xC1, 0xB2, 0xB3,
             0xB4, 0xB5, 0xA8, 0xA3, 0xBE, 0xBD, 0xA9, 0xBA, 0xBF, 0xBB,
             0xB9, 0x5F, 0xCD, 0x76, 0x2E]),
        "note": (
            "Кириллическая строка (0x2079..0x209B, 35 байт) в Vector-06C знаковом "
            "наборе: подряд идущие коды 0xA1..0xBF (аз..я), 0x5F='_', 0x2E='.'. "
            "Между lbl_206c и func_209c; дизассемблер — байт-суп → данные. Точный "
            "глифовый рендер/семантика сообщения — Phase D (render_glyphs)."),
        "props": {"charset": "Vector-06C KOI-R-like", "lang": "ru",
                  "semantic_pending": "Phase D glyph render"},
    },
]


# ---- plan / apply -------------------------------------------------------
def _row(spec, image, writer):
    addr = to_addr(spec["addr"])
    ok = spec["check"](image)
    cur = writer.exists(addr) or {}
    exists = bool(cur.get("address"))
    if spec["action"] == "extend":
        if not exists:
            act = "MISSING!"
        elif int(cur.get("size") or 0) == spec["size"]:
            act = "SKIP"
        else:
            act = "EXTEND" if ok else "CHECK!"
    else:  # create
        act = "SKIP" if exists else ("CREATE" if ok else "CHECK!")
    cur_size = int(cur.get("size") or 0) if exists else None
    return (addr, act, spec, ok, cur.get("name") or "", cur_size)


def plan(image, writer):
    return [_row(spec, image, writer) for spec in ACTIONS]


def apply(image, writer):
    log = []
    for spec in ACTIONS:
        addr = to_addr(spec["addr"])
        if not spec["check"](image):
            log.append("%s: %s ПРОПУЩЕН — байты не совпали (не тот ROM?)"
                       % (addr_hex(addr), spec["name"]))
            continue
        cur = writer.exists(addr) or {}
        exists = bool(cur.get("address"))
        if spec["action"] == "extend":
            if not exists:
                log.append("%s: EXTEND НЕЛЬЗЯ — объекта нет (%s)"
                           % (addr_hex(addr), spec["name"]))
                continue
            if int(cur.get("size") or 0) == spec["size"]:
                log.append("%s: %s уже size=%d, пропускаем"
                           % (addr_hex(addr), cur.get("name"), spec["size"]))
                continue
            writer.ensure_object(addr, cur.get("name") or spec["name"],
                                 spec["kind"], size=spec["size"])
            writer.set_comment(addr, "%s — %s"
                               % (cur.get("name") or spec["name"], spec["note"]))
            log.append("%s: EXTEND %s size %d → %d"
                       % (addr_hex(addr), cur.get("name"),
                          int(cur.get("size") or 0), spec["size"]))
        else:
            if exists:
                log.append("%s: %s уже в RDB (%s), пропускаем"
                           % (addr_hex(addr), spec["name"], cur.get("name")))
                continue
            writer.ensure_object(addr, spec["name"], spec["kind"],
                                 size=spec["size"])
            writer.set_property(addr, "role", spec.get("role", ""))
            for k, v in (spec.get("props") or {}).items():
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
            print("план Stage 15 (static residual-closure):")
            for addr, act, spec, ok, cur_name, cur_size in plan(image, writer):
                tail = "  (cur=%s size=%s)" % (cur_name, cur_size) if cur_name else ""
                print("  %-8s %s %-24s [%-8s %4d] %s%s"
                      % (act, addr_hex(addr), spec["name"], spec["kind"],
                         spec["size"],
                         "байты ОК" if ok else "БАЙТЫ НЕ СОВПАЛИ", tail))
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
