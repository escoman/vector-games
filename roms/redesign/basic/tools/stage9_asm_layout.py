#!/usr/bin/env python3
"""Stage 9: консолидированный ASM (ветвь A — монолит, byte-identical).

Собираем дерево `roms/redesign/basic/asm/` из выхода экспортёра кода
(`v06c-asm-export`, стадия `export_asm` пайплайна) и карты RDB. Один логический
класс — один файл; НЕ дробим на «по файлу/блобу на функцию».

Развилка (ТЗ §9): выбрана **A — монолит с побайтовой идентичностью**, потому
что page-zero (`0x0000..00FF`) неподвижен, интерпретатор адресно-зависим
(само-ссылочные `JMP/CALL`), а byte-for-byte round-trip — сквозной контракт.
Релокация (ветвь B) отложена на Stage 11 (аудит само-ссылок).

Итоговые файлы:
  * `asm/code.asm`     — адресно-упорядоченный монолит (весь код мнемониками +
                         ROM-backed данные `DEFB`), ровно по одному байту на
                         окно ROM. Это `layout.asm` экспортёра без правок.
  * `asm/basic_new.asm`— мастер компоновки: `ORG 0000h` + `equates.asm` +
                         `code.asm`. Единственный вход сборки.
  * `asm/equates.asm`  — аппаратные EQU (порты PIA/ВИ53/палитра/банки,
                         плоскости VRAM, вершина стека, база знакогенератора)
                         с комментарием-источником. `EQU` не эмитит байт, поэтому
                         включение в мастер не сдвигает адресацию.

Справочные read-only просмотры (в сборку НЕ входят, чтобы не дублировать
`DEFB`): `glyphs.inc`, `keywords.inc`, `messages.inc`, `demo.inc` (Stage 7/8).

Проверка: `z80asm -b -m=8080_strict basic_new.asm` -> `.bin`, затем побайтовое
`cmp` с `src/basic.r0m` (эталон Stage 0). 0 расхождений = приёмка.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage9_asm_layout.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage9_asm_layout.py --apply
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyze import export_asm
from analyze.rdb import Rdb

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"
ASM_DIR = "roms/redesign/basic/asm"
# куда экспортёр кладёт свежее дерево, если нет готового layout из пайплайна
SCRATCH_EXPORT = ".scratch/stage9_export"
PIPELINE_LAYOUT = ".scratch/export/pipeline/layout.asm"

# ---- карта аппаратных констант (проверено: docs/VECTOR_VERIFIED.md) ------
# (имя, адрес, комментарий-источник). Имена НЕ пересекаются с метками code.asm.
HARDWARE_EQU = [
    ("PORT_PIA_CW",   0x00, "КР580ВВ55 управляющее слово: D7=1 режим, D7=0 BSR порта C"),
    ("PORT_PIA_PC",   0x01, "Port C: служебные клавиши (ст. биты); бит0 = магнитофон/бипер"),
    ("PORT_PIA_PB",   0x02, "Port B: out бит0-3 бордюр, бит4 режим 512px; in — клавиатура"),
    ("PORT_PIA_PA",   0x03, "Port A: вертикальный скролл + маска строк клавиатуры"),
    ("PORT_VI53_CW",  0x08, "КР580ВИ53 управляющее слово таймера"),
    ("PORT_VI53_C2",  0x09, "ВИ53 счётчик канала 2 (тон/звук)"),
    ("PORT_VI53_C1",  0x0A, "ВИ53 счётчик канала 1"),
    ("PORT_VI53_C0",  0x0B, "ВИ53 счётчик канала 0"),
    ("PORT_PALETTE",  0x0C, "запись физ. цвета в палитру (адрес = 4 бита пикселя); зеркала 0D..0F"),
    ("PORT_BANK",     0x10, "банковая память"),
    ("PLANE3_BASE",   0x8000, "VRAM плоскость 3 (бит 3 цвета)"),
    ("PLANE2_BASE",   0xA000, "VRAM плоскость 2 (бит 2 цвета)"),
    ("PLANE1_BASE",   0xC000, "VRAM плоскость 1 (бит 1 цвета)"),
    ("PLANE0_BASE",   0xE000, "VRAM плоскость 0 (бит 0 цвета)"),
    ("STACK_TOP",     0x7FFF, "вершина стека при boot (LXI SP,7FFFh в func_0000)"),
    ("GLYPH_BASE",    0x379F, "data_glyph_block — знакогенератор 128x5 (Stage 7)"),
    ("KEYWORD_BASE",  0x256E, "data_keyword_table — 101 слово (Stage 8)"),
    ("MSGPOOL_BASE",  0x2465, "data_error_messages — пул 23 строк (Stage 8)"),
    ("AUTOLOAD_BASE", 0x4012, "str_autoload — COLOR15,0,1:CLS (Stage 8)"),
]

_LABEL_RE = re.compile(r"^[ \t]*([A-Za-z_][A-Za-z0-9_$]*)[ \t]*:", re.M)
_EQU_RE = re.compile(r"^[ \t]*([A-Za-z_][A-Za-z0-9_$]*)[ \t]+(?:equ|defc)\b",
                     re.M | re.I)


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(PROJ, p)


def load_layout(layout_arg, rom, rdb):
    """Взять адресный монолит: из готового layout, либо сгенерировать экспортёром."""
    if layout_arg:
        with open(_abs(layout_arg), encoding="utf-8", errors="replace") as fh:
            return fh.read(), "готовый %s" % layout_arg
    cand = _abs(PIPELINE_LAYOUT)
    if os.path.isfile(cand):
        with open(cand, encoding="utf-8", errors="replace") as fh:
            return fh.read(), "из пайплайна (%s)" % PIPELINE_LAYOUT
    out_dir = _abs(SCRATCH_EXPORT)
    report, _o, err, rc, cmd = export_asm.run_export(
        _abs(rom), out_dir, rdb=_abs(rdb), origin=0x0000)
    if rc != 0 or not report:
        raise SystemExit("экспортёр упал (rc=%d): %s" % (rc, err[-400:]))
    with open(os.path.join(out_dir, "layout.asm"),
              encoding="utf-8", errors="replace") as fh:
        return fh.read(), "сгенерирован (%s)" % " ".join(os.path.basename(c)
                                                         for c in cmd[:1])


def code_labels(layout_text):
    """Метки, определённые в монолите (чтобы equates.asm не конфликтовал)."""
    names = set(m.lower() for m in _LABEL_RE.findall(layout_text))
    names |= set(m.lower() for m in _EQU_RE.findall(layout_text))
    return names


def gen_code(layout_text):
    head = [
        "; code.asm — адресно-упорядоченный монолит RAM-образа BASIC 2.997.",
        "; Ветвь A (byte-identical): весь код мнемониками + ROM-backed данные",
        "; (таблицы/глифы/сообщения) как DEFB по меткам RDB. Ровно один байт на",
        "; каждый адрес окна 0x0000..0x42FF. ORG задаёт мастер basic_new.asm.",
        "; Сгенерировано tools/stage9_asm_layout.py из v06c-asm-export (не править",
        "; руками — источник истины: RDB + Stage 7/8 .inc-инструменты).",
        "",
    ]
    return "\n".join(head) + layout_text.rstrip("\n") + "\n"


def _hex16(val):
    """16-битное значение -> синтаксис z80asm (ведущий 0, если старт с A..F)."""
    h = "%04X" % val
    return ("0" + h if h[0] in "ABCDEF" else h) + "h"


def gen_equates(layout_text):
    taken = code_labels(layout_text)
    lines = [
        "; equates.asm — аппаратные и структурные константы образа (ветвь A).",
        "; Только EQU (байт не эмитит) -> включение в мастер не сдвигает адреса.",
        "; Источники: docs/VECTOR_VERIFIED.md (VERIFIED_BY_CODE) и карта RDB.",
        "; Метки var_*/data_*/func_* уже определены в code.asm — здесь их нет,",
        "; чтобы не было коллизий имён при сборке.",
        "",
    ]
    skipped = []
    for name, val, note in HARDWARE_EQU:
        if name.lower() in taken:
            skipped.append(name)
            continue
        lines.append("%-14s equ %s   ; %s" % (name, _hex16(val), note))
    lines += [
        "",
        "; ---- зеркала порта палитры ----",
        "PORT_PALETTE1 equ 000Dh   ; зеркало 0Ch",
        "PORT_PALETTE2 equ 000Eh   ; зеркало 0Ch",
        "PORT_PALETTE3 equ 000Fh   ; зеркало 0Ch",
        "",
        "; ---- размер образа ----",
        "RAM_IMAGE_SIZE equ 4300h   ; 17152 байт (0x0000..0x42FF)",
    ]
    return "\n".join(lines) + "\n", skipped


def gen_master():
    return "\n".join([
        "; basic_new.asm — мастер компоновки RAM-образа BASIC 2.997 (ветвь A).",
        "; Единый ORG + адресный монолит. EQU-справочник подключается до кода",
        "; (байт не добавляет). Собирается строго побайтово в src/basic.r0m.",
        ";",
        ";   z80asm -b -m=8080_strict basic_new.asm -o=basic_new.bin",
        "",
        "        org     00000h",
        '        include "equates.asm"',
        '        include "code.asm"',
        "",
    ])


def build_and_verify(asm_dir, rom, out_bin):
    z80asm = export_asm.find_z80asm()
    if not z80asm:
        raise SystemExit("z80asm не найден (задайте V06C_Z80ASM или --z80asm)")
    res = export_asm.assemble(asm_dir, z80asm=z80asm, main="basic_new.asm",
                              output=out_bin)
    if res["returncode"] != 0:
        return res, None
    with open(out_bin, "rb") as fh:
        got = fh.read()
    with open(_abs(rom), "rb") as fh:
        want = fh.read()
    if len(got) != len(want):
        diff = min(len(got), len(want))
        nbad = sum(1 for i in range(diff) if got[i] != want[i]) + \
            abs(len(got) - len(want))
    else:
        nbad = sum(1 for i in range(len(got)) if got[i] != want[i])
    return res, {"size_got": len(got), "size_want": len(want), "diff_bytes": nbad}


def plan(rom, rdb, layout_arg):
    layout, src = load_layout(layout_arg, rom, rdb)
    lines = [
        "план Stage 9 (ветвь A — монолит, byte-identical):",
        "  источник монолита: %s (%d строк)" % (src, layout.count("\n") + 1),
        "  -> asm/code.asm      (адресный поток, ORG из мастера)",
        "  -> asm/basic_new.asm (ORG 0000h + equates + code)",
        "  -> asm/equates.asm   (%d аппаратных EQU)" % len(HARDWARE_EQU),
        "  read-only просмотры (в сборку не входят): glyphs.inc / keywords.inc /",
        "                       messages.inc / demo.inc",
        "  сборка: z80asm -b -m=8080_strict basic_new.asm; сверка cmp с basic.r0m",
    ]
    return lines


def apply_(rom, rdb, asm_dir, layout_arg):
    log = []
    layout, src = load_layout(layout_arg, rom, rdb)
    os.makedirs(_abs(asm_dir), exist_ok=True)
    with open(os.path.join(_abs(asm_dir), "code.asm"), "w",
              encoding="utf-8") as fh:
        fh.write(gen_code(layout))
    log.append("asm/code.asm (%d строк, из %s)"
               % (layout.count("\n") + 1, src))
    eq, skipped = gen_equates(layout)
    with open(os.path.join(_abs(asm_dir), "equates.asm"), "w",
              encoding="utf-8") as fh:
        fh.write(eq)
    log.append("asm/equates.asm (%d EQU%s)"
               % (len(HARDWARE_EQU) - len(skipped),
                  ", пропущено коллизий: %s" % skipped if skipped else ""))
    with open(os.path.join(_abs(asm_dir), "basic_new.asm"), "w",
              encoding="utf-8") as fh:
        fh.write(gen_master())
    log.append("asm/basic_new.asm (мастер)")

    out_bin = os.path.join(_abs(asm_dir), "basic_new.bin")
    res, cmpinfo = build_and_verify(_abs(asm_dir), rom, out_bin)
    if res["returncode"] != 0:
        log.append("СБОРКА УПАЛА rc=%d" % res["returncode"])
        log.append((res["stdout"] + res["stderr"])[-1500:])
        return log, False
    ok = cmpinfo and cmpinfo["diff_bytes"] == 0 and \
        cmpinfo["size_got"] == cmpinfo["size_want"]
    log.append("сборка OK -> basic_new.bin (%d байт)" % cmpinfo["size_got"])
    log.append("round-trip vs basic.r0m: %s (%d/%d, расхождений %d)"
               % ("BYTE-FOR-BYTE OK" if ok else "РАСХОЖДЕНИЕ",
                  cmpinfo["size_got"], cmpinfo["size_want"],
                  cmpinfo["diff_bytes"]))
    return log, ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--rdb", default=DEFAULT_RDB)
    ap.add_argument("--asm-dir", default=ASM_DIR)
    ap.add_argument("--layout", default=None,
                    help="готовый layout.asm (иначе из пайплайна/экспортёра)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    if not (args.check or args.apply):
        args.apply = True

    if args.check:
        for line in plan(args.rom, args.rdb, args.layout):
            print(line)
        return 0

    log, ok = apply_(args.rom, args.rdb, args.asm_dir, args.layout)
    for line in log:
        print("  " + line)
    print("итог: %s" % ("round-trip BYTE-FOR-BYTE" if ok else "ПРОВАЛ"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
