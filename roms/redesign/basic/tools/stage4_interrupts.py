#!/usr/bin/env python3
"""Stage 4: прерывания и фоновые службы — именование + свойства + связи.

Документирует трак обрабатчика прерываний 50 Гц и его спутников (клавиатура,
палитра-синхронизация, кадровый таймер, мигание курсора). Факты — из дизасма
тел через MCP-отладчик (`.scratch/dis.py`); адреса и имена не изобретаются,
каждое подтверждено телом функции/метками сохранения контекста и местами вызова
в `layout.asm`. Ключевой доказанный факт: в ROM 0x `DI`, 2x `EI`, 0x `IM`,
0x `IRET` — интерпретатор прозрачен к прерываниям, безопасность обеспечивает
сам ISR (полное сохранение/восстановление контекста + свой стек 0x26F7). Это
объясняет инварианты change log п.18/п.72/п.31 (толерантность к прерыванию,
экран/дуги без `DI`), а палитра-тикер с намеренными задержками `XTHL` — п.93.

Для каждого объекта: создать/переименовать/переквалифицировать в нужный тип
(метка `lbl_*`/`label_*` -> функция одним `debug_update_rdb_object`, чтобы не
потерять links/properties), затем записать `role`/`params`/`reads`/`writes`/
`calls`/`size`, комментарий и связи вызовов.

Открытый пункт (не выдумываем): точный эффект палитра-тикера (какие цвета и
зачем каждый кадр) не вскрываем — доказан только механизм (цикл `OUT 02`/`OUT
0C` по таблице `0x2C7E` с задержками). Декодирование клавиатурных таблиц
`0x2D7E`/`0x2D8E` -> символы — Stage 5 (токенизатор/РЕПЛ).

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage4_interrupts.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage4_interrupts.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

CTX = "блок сохранения контекста 0x2D04(SP)/0x2D07(HL)/0x2D0B(PC)"

# адрес -> описание объекта. kind: function|label|data|variable
OBJECTS = {
    # === Функции-обработчики ===
    0x0038: {
        "kind": "function",
        "name": "func_rst_irq",
        "role": "rst_irq_jump",
        "params": "RST 7 (вектор прерывания, вход по INT от КР580ВМ80А)",
        "reads": [],
        "writes": [],
        "calls": ["JMP 0x2C7F func_irq_handler (тикер 50 Гц)"],
        "calls_named": [(0x2C7F, "func_irq_handler")],
        "note": "Вектор прерываний 0x0038: JMP в обработчик 0x2C7F. Единственный "
                "точка входа прерываний в ROM; режим IM не выставляется (см. "
                "Stage4.md) — используется векторная схема ВМ80А.",
    },
    0x2C7F: {
        "kind": "function",
        "name": "func_irq_handler",
        "role": "irq_vblank_handler",
        "params": "вход по прерыванию; контекст в HL/SP/PSW сохраняется в " + CTX,
        "reads": ["IN 01 bit7 (РУС/ЛАТ)", "IN 02 (состояние матрицы клавиатуры)",
                  "прескейлер 0x3A1F / strobe 0x3A22"],
        "writes": [CTX, "свой стек: LXI SP,0x26F7",
                   "0x3A1F++ / 0x3A20:21++ (кадровый счётчик)",
                   "OUT 00 (упр. ВВ55#1) = 0x8A", "0x2CB1 (за latch РУС/ЛАТ)",
                   "0x2DCD bit3 (мигание курсора XRI 08)",
                   "OUT 03/IN 02 (скан строк матрицы)"],
        "calls": ["CALL 0x239D func_irq_palette_refresh",
                  "CALL 0x2DC8 func_kbd_matrix_prime",
                  "падение в хвост 0x2D00 lbl_irq_resume (EI/JMP)"],
        "calls_named": [(0x239D, "func_irq_palette_refresh"),
                        (0x2DC8, "func_kbd_matrix_prime")],
        "note": "Главный обработчик прерываний 50 Гц: сохранить PSW/HL/SP/PC в "
                + CTX + ", переключить стек на 0x26F7, обновить палитру (0x239D), "
                "инкрементить прескейлер 0x3A1F и кадровый счётчик 0x3A20, "
                "выдать управление экраном OUT 00=0x8A, снять latch РУС/ЛАТ "
                "(IN 01/ANI 80), заморгать курсор (XRI 08 на 0x2DCD), сканировать "
                "матрицу клавиатуры (OUT 03/IN 02). Возврат — через lbl_irq_resume.",
    },
    0x239D: {
        "kind": "function",
        "name": "func_irq_palette_refresh",
        "role": "irq_palette_sync",
        "params": "таблица цветов 0x2C7E (16 ячеек); вызывается из 0x2C7F",
        "reads": ["0x2C7E.. (LDAX D — цвета ячеек)"],
        "writes": ["OUT 02 (адрес/бордюр)", "OUT 0C (физический цвет в палитру)"],
        "calls": ["цикл B=0x0F..00: OUT 02 / LDAX D / OUT 0C",
                  "XTHL/XTHL (намеренные задержки — racing the beam)"],
        "calls_named": [(0x2C7E, "data_irq_palette_table")],
        "note": "Попиксельная синхронизация палитры на каждый кадр (racing-the-"
                "beam): 16 пар OUT 02/OUT 0C из таблицы 0x2C7E с увеличенными "
                "паузами (XTHL) — это п.93 change log. Точный подбираемый эффект "
                "не вскрываем (открытый пункт Stage 4).",
    },
    0x2C40: {
        "kind": "function",
        "name": "func_kbd_dequeue",
        "role": "kbd_read_key",
        "params": "(нет); возвращает A = код клавиши или 0xFF/знак<0, если пусто",
        "reads": ["0x2B3F (счётчик буфера клавиш)", "кольцевой буфер 0x4012",
                  "0x2DCF (состояние мигания/повтора)"],
        "writes": ["0x2B3F-- (DCR M — израсходован символ)",
                   "0x2DCF bit1 (XRI 02 — сдвиг фазы курсора)"],
        "calls": ["JZ/JP на пустой буфер (0x2C6D: A:=<0, RET)",
                  "CPI 0x84 (проверка special-кода)"],
        "calls_named": [],
        "note": "Выборка клавиши из буфера, собираемого ISR: возвращает код в A "
                "(или <0/0xFF если буфер пуст). Зовут func_inkey (INKEY$) и "
                "редакторский цикл ожидания символа. Был func_2c40.",
    },
    0x2DC8: {
        "kind": "function",
        "name": "func_kbd_matrix_prime",
        "role": "kbd_scan_prime",
        "params": "(нет); строк/столбец задаётся 0x3A22",
        "reads": ["0x3A22 (выбранная строка strobe)"],
        "writes": ["OUT 00 = 0x88 (упр. ВВ55#1)", "OUT 01",
                   "OUT 03 (0x3A22: маска строки)", "OUT 02 = 0 (подтяжка)"],
        "calls": ["MVI A,88/OUT 00; OUT 01; LDA 3A22/OUT 03; OUT 02"],
        "calls_named": [(0x3A22, "var_kbd_strobe")],
        "note": "Аппаратная подготовка клавиатурной матрицы перед чтением порта "
                "0x02: выставить strobe строки и подтяжку. Зовётся из ISR (0x2CE0, "
                "0x2D15) и из dequeue-цикла. Был func_2dc8.",
    },

    # === Метка хвоста возврата ISR (inline, объектом-функцией не плодим) ===
    0x2D00: {
        "kind": "label",
        "name": "lbl_irq_resume",
        "role": "irq_resume_tail",
        "params": "(вход из func_irq_handler в хвосте)",
        "reads": [CTX],
        "writes": ["SP := 0x2D04 (самомод.)", "HL := 0x2D07 (самомод.)"],
        "calls": ["POP D/B/PSW", "EI", "JMP 0x0000 (самомод. на PC из 0x2D0B)"],
        "calls_named": [(0x2D04, "var_irq_context_block")],
        "note": "Хвост возврата из прерывания: восстановить D/B/PSW, SP и HL из "
                + CTX + (", затем EI и самомодифицируемый JMP на сохранённый PC "
                "(без IRET — возврат прыжком). Это п.18/п.72 change log: "
                "обработчик сам восстанавливает контекст, DI нигде не выполняется."),
    },

    # === Данные и переменные состояния прерываний ===
    0x2C7E: {
        "kind": "data", "name": "data_irq_palette_table", "size": 16,
        "role": "palette_color_table",
        "note": "16 ячеек физических цветов, из которых func_irq_palette_refresh "
                "каждый кадр перезаписывает палитру через OUT 02/OUT 0C.",
        "reads": [], "writes": [], "calls": [], "calls_named": [],
    },
    0x3A1F: {
        "kind": "variable", "name": "var_irq_prescaler", "size": 1,
        "role": "tick_prescaler",
        "note": "Делитель тика: func_irq_handler INR M на каждом прерывании; при "
                "переполнении через 0 инкрементится var_irq_frame_counter (0x3A20). "
                "Биты (напр. 0x08) читают как фазу мигания курсора (func_2c40-цикл).",
        "reads": [], "writes": [], "calls": [], "calls_named": [],
    },
    0x3A20: {
        "kind": "variable", "name": "var_irq_frame_counter", "size": 2,
        "role": "frame_counter",
        "note": "16-битный счётчик кадров (LHLD/INX H/SHLD 0x3A20 по переполнению "
                "прескалера). Кадровые часы интерпретатора.",
        "reads": [], "writes": [], "calls": [], "calls_named": [],
    },
    0x2D04: {
        "kind": "variable", "name": "var_irq_context_block", "size": 8,
        "role": "irq_saved_context",
        "note": "Блок сохранения прерванного контекста: 0x2D04 SP, 0x2D07 HL, "
                "0x2D0B PC (записывает func_irq_handler, читает lbl_irq_resume).",
        "reads": [], "writes": [], "calls": [], "calls_named": [],
    },
    0x2DCD: {
        "kind": "variable", "name": "var_cursor_blink", "size": 1,
        "role": "cursor_blink_state",
        "note": "Состояние курсора: func_irq_handler заморгивает бит 3 (XRI 0x08) "
                "на каждом кадре; рядом 0x2DCF используют для фазы повтора клавиш.",
        "reads": [], "writes": [], "calls": [], "calls_named": [],
    },
    0x3A22: {
        "kind": "variable", "name": "var_kbd_strobe", "size": 1,
        "role": "kbd_row_strobe",
        "note": "Маска выбранной строки клавиатурной матрицы: func_kbd_matrix_prime "
                "пишет её в порт 0x03 перед чтением порта 0x02.",
        "reads": [], "writes": [], "calls": [], "calls_named": [],
    },
    0x26F7: {
        "kind": "variable", "name": "var_irq_stack_top", "size": 1,
        "role": "irq_stack_pointer",
        "note": "Вершина выделенного IRQ-стека: func_irq_handler делает LXI SP,"
                "0x26F7, чтобы обработка прерывания шла на своём стеке (п.18 "
                "change log — толерантность к прерыванию в любом коде).",
        "reads": [], "writes": [], "calls": [], "calls_named": [],
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
        action = "create"
        log.append("%s: СОЗДАН %s %s" % (addr_hex(addr), kind, name))
    elif ctype != kind:
        session.call("debug_update_rdb_object",
                     {"address": addr, "name": name, "type": kind,
                      "size": to_addr(int(size if size is not None
                                          else (current.get("size") or 0)))})
        writer.actions.append({"kind": "retype", "tool": "debug_update_rdb_object",
                               "arguments": {"address": addr, "name": name,
                                             "type": kind}})
        action = "retype"
        log.append("%s: %s (%s) -> %s %s"
                   % (addr_hex(addr), cur_name, ctype, kind, name))
    else:
        if size is not None:
            writer.ensure_object(addr, name, kind, size=size, rename=True)
        else:
            writer.ensure_object(addr, name, kind, rename=True)
        action = "noop" if cur_name == name else "rename"
        log.append("%s: %s -> %s" % (addr_hex(addr), cur_name, name))
    return action


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
        print("план: %d объектов Stage 4" % len(OBJECTS))
        if args.check:
            for addr, kind, cur, ctype, spec in plan(writer):
                print("  %s [%-6s] %-24s (%-8s) -> %s %s"
                      % (addr_hex(addr), kind, cur, ctype, spec["kind"],
                         spec["name"]))
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
