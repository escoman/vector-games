#!/usr/bin/env python3
"""Этап B (symB6): линт asm-дерева на абсолютные ссылки на ДВИЖУЩИЕ/УДАЛЯЕМЫЕ адреса.

Двигается в этапе B только блок глифов (GLYPH_BASE, одна константа в
gen_layout.py); удаляются из сборки мёртвые блоки (tools/dead_ranges.json:
func_load_glyph_block, func_load_gfx_2761 + их данные). Всё остальное обязано
стоять на оригинальных адресах — числовые литералы на закреплённые адреса
допустимы (это обходится `should_be_symbolic`-справкой общего lint, не блокер).

Проверки по всем файлам реальной сборки (entry = putup_unpacked.asm):
1. число/символ (через EQU-резолвинг), попадающий в окно блока глифов, —
   ошибка, если источник не в списке allow (см. ALLOW ниже);
2. числовой ЛИТЕРАЛ внутрь удаляемого ROM-блока — блокер (код читал бы
   выжигаемые данные). Не блокер, если значение совпадает с EQU из
   var_ram_symbols: в хвосте окна шрифта (0x383A..0x3857) живут RAM-
   переменные секвенсора — это accesses в ОЗУ, а не ссылки на данные ROM;
3. общий symbolic_operand_lint (RDB-сверка) прогоняется поверх: его
   should_be_symbolic/undefined_symbol по ЗАКРЕПЛЁННЫМ адресям — справка.

Использование: python3 tools/lint_ptrs.py [--json out.json]
GLYPH_BASE в окружении должен совпадать с компоновкой (gen_layout.py).
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
MASTER = "putup_unpacked.asm"
GLYPH_BASE = int(os.environ.get("GLYPH_BASE", "0x6000"), 0)
GLYPH_SIZE = 8192
NUM_RE = re.compile(r"^[0-9][0-9A-Fa-f]*[hH]$")

# Единственные места, где ссылка в окно блока глифов осмысленна и легальна:
#   * data_glyph_ptr_table.asm — 256 DEFW уже символьные (data_glyph_block+N*32);
#   * data_glyph_block_unpacked.asm — сам блок (INCBIN, базовая метка).
# Копир спрайтов (7418h) выведен из сборки на deadB7 — ссылок в окно больше нет.
ALLOW_GLYPH_FILES = {"data_glyph_ptr_table.asm", "data_glyph_block_unpacked.asm"}

# A-регрессия (KEEP_DEAD=1): распаковщики возвращаются в сборку и СМЫСЛОМ
# своей работы пишут в окно блока — их ссылки помечаем pending-удалением,
# а не блокировкой (зеркало DEAD-множества gen_layout.py).
PENDING_DEAD_FILES = {"func_load_glyph_block.asm", "func_load_gfx_2761.asm",
                      "data_packed_font_3041.asm", "data_gfx_2761.asm"}


def dead_ranges():
    path = os.path.join(PROJ, "tools", "dead_ranges.json")
    if not os.path.exists(path):
        return []
    info = json.load(open(path, encoding="utf-8"))
    items = info["dead_ranges"] if isinstance(info, dict) else info
    return [(s, e, n) for s, e, n in items]


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


def scan(files, equ, glyph_win, dead_wins):
    ram_alias = set(equ.values())
    findings = []
    for name in files:
        if name == MASTER:
            continue  # макет: defs/incbin по константе, не ссылки кода
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
                literal = None
                if NUM_RE.match(token):
                    value = export_asm.asm_number(token)
                    literal = value
                elif re.match(r"^[A-Za-z_]\w*$", token):
                    value = equ.get(token.lower())
                    # data_glyph_block — метка блока (не EQU): ссылка символьна
                    # и переносима сама по себе.
                    if value is None and token.lower() == "data_glyph_block":
                        value = glyph_win[0]
                if value is None:
                    continue
                if glyph_win[0] <= value < glyph_win[1]:
                    findings.append({
                        "rule": "ref_in_glyph_window", "file": name, "line": number,
                        "detail": "%s -> 0x%04X попадает в окно блока @0x%04X"
                                  % (token, value, GLYPH_BASE),
                        "blocking": (name not in ALLOW_GLYPH_FILES
                                     and name not in PENDING_DEAD_FILES),
                        "pending": ("deadB7 (мёртвый распаковщик, KEEP_DEAD=1)"
                                    if name in PENDING_DEAD_FILES else None)})
                # в окна удалённых ROM-блоков смотрим только НАСТЯЩИЕ литералы;
                # символьные RAM-переменные (var_music_tick и т.п.) — не ссылки
                # на данные шрифта, хотя численно попадают в то же адресное окно
                if literal is not None:
                    for lo, hi, why in dead_wins:
                        if lo <= literal < hi:
                            if literal in ram_alias:
                                findings.append({
                                    "rule": "ram_var_literal", "file": name,
                                    "line": number,
                                    "detail": "%s = адрес RAM-переменной внутри %s"
                                              % (token, why),
                                    "blocking": False, "pending": None})
                            else:
                                findings.append({
                                    "rule": "ref_to_removed_block", "file": name,
                                    "line": number,
                                    "detail": "%s -> 0x%04X внутрь удаляемого %s"
                                              % (token, literal, why),
                                    "blocking": True, "pending": None})
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
    dead_wins = [(s, e, n) for s, e, n in dead_ranges()]

    findings = scan(built, equ, glyph_win, dead_wins)

    # общий сверочный lint по RDB: только справка по закреплённым адресам
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
        "summary": {"blocking": len(blocking), "pending_removal": len(pend),
                    "generic_info": len(gen_info)},
    }
    if args.json:
        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        json.dump(result, open(args.json, "w"), ensure_ascii=False, indent=1)
    for f in findings:
        print("[%s] %s:%d %s%s" % ("ERROR" if f["blocking"] else "pend",
                                   f["file"], f["line"], f["detail"],
                                   " — " + f["pending"] if f.get("pending") else ""))
    print("справка (закрепл. адреса, не блокер): %d should_be_symbolic/undefined"
          % len(gen_info))
    print("ВЕРДИКТ %s: блокеров %d, пендингов deadB7 %d"
          % ("CLEAN" if not blocking else "BLOCKED", len(blocking), len(pend)))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
