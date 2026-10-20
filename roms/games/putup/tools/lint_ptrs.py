#!/usr/bin/env python3
"""Свободная раскладка (Stage-4): линт asm-дерева на relocation-враждебные ссылки.

Конкатенация НЕ сохраняет адреса оригинала: метки двигаются, поэтому единственный
надёжный способ сослаться на живую метку — символьно (`LXI H, func_...`,
`DEFW data_glyph_block+N`). Линт ловит ЧИСЛОВЫЕ ссылки в живом коде:

1. ref_in_glyph_window — число/символ (через EQU-резолвинг) попадает в окно блока
   глифов (glyph_base/glyph_size из tools/layout.json, пишет mk_manifest.py). Это
   класс регрессии `MVI H,06h` (страница таблицы зашита). Легальны лишь файлы из
   ALLOW (таблица DEFW-указателей + сам блок) — там ссылки символьны.
2. общий symbolic_operand_lint (RDB-сверка) поверх: should_be_symbolic/undefined —
   справка (числовые константы-значения: LXI SP 0100h, PRNG-множитель, DEFM-текст),
   а не блокер, ибо не являются указателями на перемещаемые метки.

Удаляемый мёртвый шлак физически исключён из сборки — проверок на «внутрь
вырезанного блока» больше нет (former dead_ranges.json/COMPACT мёртв).

Использование: python3 tools/lint_ptrs.py [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(PROJ, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "utils"))

from analyze import export_asm, symbolic_operand_lint as sol  # noqa: E402

ASM = os.path.join(PROJ, "asm")
REF = os.path.join(ROOT, "roms", "redesign", "putup", "src")  # оригиналы putup.rom/rdb
MASTER = "putup_new.asm"
#skip_scan = файлы, где числовые значения — ОПРЕДЕЛЕНИЯ (EQU/incbin по константе),
#а не ссылки кода: мастер-макет и генерируемая таблица relocate-якорей
#var_reloc_anchors.asm (ее EQU-литералы = перемещённые RAM-адреса, численно
#попадают в оригинальное окно удалённого data_gfx_2761 — это не ссылки).
SKIP_SCAN = {MASTER, "var_reloc_anchors.asm"}


def _load_layout():
    """Манифест адресов tools/layout.json (пишет mk_manifest.py из .sym)."""
    path = os.path.join(PROJ, "tools", "layout.json")
    if not os.path.exists(path):
        raise SystemExit("нет tools/layout.json — сначала `make` (пишет манифест адресов)")
    return json.load(open(path, encoding="utf-8"))


LAYOUT = _load_layout()


def _resolve_glyph_base():
    """glyph_base: env -> layout.json (истина конкатенации)."""
    if "GLYPH_BASE" in os.environ:
        return int(os.environ["GLYPH_BASE"], 0)
    return LAYOUT["glyph_base"]


def _resolve_glyph_size():
    """glyph_size: layout.json (число DEFB блока); резерв 8192."""
    return LAYOUT.get("glyph_size", 8192)


GLYPH_BASE = _resolve_glyph_base()
GLYPH_SIZE = _resolve_glyph_size()
NUM_RE = re.compile(r"^[0-9][0-9A-Fa-f]*[hH]$")

# Единственные места, где ссылка в окно блока глифов осмысленна и легальна:
#   * data_glyph_ptr_table.asm — 256 DEFW уже символьные (data_glyph_block+N*32);
#   * data_glyph_block_unpacked.asm — сам блок (базовая метка + смещения).
ALLOW_GLYPH_FILES = {"data_glyph_ptr_table.asm", "data_glyph_block_unpacked.asm"}


def equ_values(files):
    """Имя -> числовое значение по EQU-строкам дерева (для резолвинга ссылок)."""
    out = {}
    for name in files:
        path = os.path.join(ASM, name)
        if not os.path.isfile(path):
            continue
        for text in export_asm.read_lines(path):
            label, directive, operand = export_asm.line_parts(text)
            if directive == "equ" and label and NUM_RE.match(operand.strip()):
                out[label.lower()] = export_asm.asm_number(operand)
    return out


def scan(files, equ, glyph_win):
    findings = []
    for name in files:
        if name in SKIP_SCAN:
            continue  # макет/таблица якорей: defs/EQU-определения по константе, не ссылки кода
        path = os.path.join(ASM, name)
        if not os.path.isfile(path):
            continue
        for number, text in enumerate(export_asm.read_lines(path), 1):
            body = text.split(";", 1)[0]
            if not body.strip() or body.strip().startswith(";"):
                continue
            for token in re.split(r"[,\s()]+", body):
                if not token:
                    continue
                value = None
                if NUM_RE.match(token):
                    value = export_asm.asm_number(token)
                elif re.match(r"^[A-Za-z_]\w*$", token):
                    value = equ.get(token.lower())
                    # data_glyph_block — метка блока (не EQU): ссылка символьна
                    # и переносима сама по себе.
                    if value is None and token.lower() == "data_glyph_block":
                        value = glyph_win[0]
                if value is None:
                    continue
                if glyph_win[0] <= value < glyph_win[1]:
                    # символьная ссылка на метку блока легальна (переносится
                    # ассемблером); блокер — ЧИСЛОВАЯ ссылка в окно глифов.
                    findings.append({
                        "rule": "ref_in_glyph_window", "file": name, "line": number,
                        "detail": "%s -> 0x%04X попадает в окно блока @0x%04X"
                                  % (token, value, GLYPH_BASE),
                        "blocking": (name not in ALLOW_GLYPH_FILES),
                        "pending": None})
    return findings


def built_files_recursive():
    """Мастер + все include любого уровня вложенности (data_level_maps тянет
    за собой data_level_NN.asm; built_files из export_asm — одноуровневый)."""
    found, queue = [MASTER], [MASTER]
    while queue:
        fn = queue.pop()
        try:
            txt = open(os.path.join(ASM, fn), encoding="utf-8").read()
        except OSError:
            continue
        for inc in re.findall(r'^\s*include\s+"([^"]+)"', txt, re.M):
            if inc not in found:
                found.append(inc)
                queue.append(inc)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(PROJ, "tools", "stage_b_lint.json"))
    args = ap.parse_args()

    built = built_files_recursive()
    equ = equ_values(built)
    glyph_win = (GLYPH_BASE, GLYPH_BASE + GLYPH_SIZE)

    findings = scan(built, equ, glyph_win)

    # общий сверочный lint по RDB: справка (числовые константы-значения, DEFM-текст)
    objects = sol.load_objects(os.path.join(REF, "putup.rdb"))
    gen_findings, stats, _ = sol.check_operands(ASM, objects, 0x100, 0x4600, built=built)
    gen_info = [f for f in gen_findings if f["rule"] != "rdb_name_not_emitted"]

    blocking = [f for f in findings if f["blocking"]]
    pend = [f for f in findings if not f["blocking"]]
    result = {
        "glyph_base": hex(GLYPH_BASE),
        "built_files": len(built),
        "operand_stats": stats,
        "findings": findings,
        "generic_lint_info": [
            {"rule": f["rule"], "file": f.get("file"), "line": f.get("line"),
             "detail": f["detail"]} for f in gen_info],
        "summary": {"blocking": len(blocking), "allowed_glyph_refs": len(pend),
                    "generic_info": len(gen_info)},
    }
    if args.json:
        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        json.dump(result, open(args.json, "w"), ensure_ascii=False, indent=1)
    for f in findings:
        print("[%s] %s:%d %s%s" % ("ERROR" if f["blocking"] else "allow",
                                   f["file"], f["line"], f["detail"],
                                   " — " + f["pending"] if f.get("pending") else ""))
    print("справка (числовые константы-значения/DEFM, не блокер): %d should_be_symbolic/undefined"
          % len(gen_info))
    print("ВЕРДИКТ %s: блокеров %d, разреш. симв. ссылок в блок %d"
          % ("CLEAN" if not blocking else "BLOCKED", len(blocking), len(pend)))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
