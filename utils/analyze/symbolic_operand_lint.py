"""Символьные операнды в экспорте: числа против имён (ТЗ §26, §11, §12).

Экспортёр подставляет имена RDB в операнды, где может. Модуль сверяет три
вещи — все они арифметика интервалов и поиск по тексту, без разбора кодов:

1. числовой операнд попадает под RDB-объект ⇒ имя могло бы стоять здесь, но
   стоит число (`should_be_symbolic`);
2. именованный операнд нигде в дереве не определён ⇒ сборка упадёт
   (`undefined_symbol`);
3. метка дерева не соответствует ни одному имени RDB ⇒ экспорт и база
   разошлись (`orphan_label`).

`defb/defw/defs/incbin` в расчёт не берутся: там числа — это данные, а не
адреса.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from analyze import export_asm
from analyze.mcp_session import addr_hex, to_addr
from analyze.rdb import Rdb

DATA_DIRECTIVES = ("defb", "db", "defw", "dw", "defs", "ds", "equ", "org",
                   "include", "incbin", "includebin", "assert")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
UNKNOWN_RE = re.compile(r"_unknown\b|\bunknown_", re.IGNORECASE)
# Синтезированные метки экспортёра (`label_3DB9`, `gap_2F61_…`): их сознательно
# нет в RDB — это якоря для байтов без объекта, а не расхождение имён.
SYNTH_RE = re.compile(r"^(?:label|gap|sub|unk|tmp)_[0-9A-Fa-f_]*\Z",
                      re.IGNORECASE)
# Операнды в скобках — адрес может стоять и внутри: (0100h), (data_table)
PAREN_RE = re.compile(r"^\((?P<inner>.*)\)$")


def unwrap(item):
    """'(HL)' → 'HL'; скобки — это косвенная адресация, а не другое имя."""
    match = PAREN_RE.match(item.strip())
    return match.group("inner").strip() if match else item.strip()


def load_objects(rdb_path):
    rdb = Rdb.load(rdb_path)
    return [item for item in rdb.objects if item.name and item.size_known]


def name_at(objects, address):
    """Объект, начинающийся по адресу, либо накрывающий его диапазон."""
    best = None
    for obj in objects:
        if obj.address == address:
            return obj
        if obj.contains(address) and obj.type in ("function", "code", "data",
                                                  "table", "string", "music",
                                                  "variable", "label"):
            best = best or obj
    return best


def check_operands(out_dir, objects, origin, rom_size, built=None):
    findings = []
    built = built or export_asm.built_files(out_dir)
    defined = export_asm.defined_symbols(out_dir, built)
    lo, hi = to_addr(origin), to_addr(origin) + int(rom_size) - 1
    stats = {"numeric": 0, "symbolic": 0, "numeric_in_window": 0}
    for name in built:
        full = os.path.join(out_dir, name)
        if not os.path.isfile(full):
            continue
        for number, text in enumerate(export_asm.read_lines(full), 1):
            directive, operand = export_asm.split_line(text)
            if not directive or not operand or directive in DATA_DIRECTIVES:
                continue
            if directive == "label":
                continue
            for item in export_asm.OPERAND_SPLIT_RE.split(operand):
                item = unwrap(item)
                if not item:
                    continue
                value = export_asm.asm_number(item)
                if value is not None:
                    stats["numeric"] += 1
                    if lo <= value <= hi:
                        stats["numeric_in_window"] += 1
                        obj = name_at(objects, value)
                        if obj is not None and not UNKNOWN_RE.search(obj.name):
                            findings.append({
                                "rule": "should_be_symbolic", "severity": "info",
                                "file": name, "line": number,
                                "detail": "%s %s: число %s попадает под %s (%s)"
                                          % (directive, item, addr_hex(value),
                                             obj.name, obj.type),
                                "suggestion": "заменить на %s" % obj.name})
                    continue
                if IDENT_RE.match(item):
                    if item.upper() in export_asm.RESERVED_OPERANDS:
                        continue          # регистр/условие — это не ссылка
                    stats["symbolic"] += 1
                    if item not in defined:
                        findings.append({
                            "rule": "undefined_symbol", "severity": "error",
                            "file": name, "line": number,
                            "detail": "операнд %s (%s) не определён в дереве"
                                      % (item, directive),
                            "suggestion": "проверить, что RDB-объект с таким "
                                          "именем выгружен, или добавить equ"})
    return findings, stats, defined


def check_labels(out_dir, objects, defined):
    """Метки экспорта ↔ имена RDB: обе стороны расхождения полезны."""
    findings = []
    names = {obj.name for obj in objects}
    used = set()
    for name in sorted(defined):
        if UNKNOWN_RE.search(name) or SYNTH_RE.search(name):
            continue
        if name not in names:
            findings.append({"rule": "orphan_label", "severity": "warn",
                             "file": defined[name]["file"],
                             "line": defined[name]["line"],
                             "detail": "метка %s есть в ASM, но нет в RDB" % name,
                             "suggestion": "создать объект в RDB или снять "
                                           "расхождение перезаписью экспорта"})
        else:
            used.add(name)
    unused = sorted(names - used)
    for name in unused[:40]:
        findings.append({"rule": "rdb_name_not_emitted", "severity": "info",
                         "file": None, "line": None,
                         "detail": "имя %s из RDB не появилось в дереве" % name,
                         "suggestion": "объект мог быть вне окна ROM или "
                                       "перекрыт другим диапазоном"})
    return findings


def run_lint(out_dir, rom, rdb=None, origin=0x0100):
    report = export_asm.read_export_json(out_dir) or {}
    rom_size = int(report.get("rom_size") or os.path.getsize(rom))
    rdb_path = rdb or os.path.splitext(rom)[0] + ".rdb"
    objects = load_objects(rdb_path) if os.path.isfile(rdb_path) else []
    findings, stats, defined = check_operands(out_dir, objects, origin, rom_size)
    if objects:
        findings += check_labels(out_dir, objects, defined)
    errors = [item for item in findings if item["severity"] == "error"]
    by_rule = {}
    for item in findings:
        by_rule[item["rule"]] = by_rule.get(item["rule"], 0) + 1
    return {
        "out_dir": os.path.abspath(out_dir),
        "rdb": rdb_path if objects else None,
        "objects": len(objects),
        "defined_symbols": len(defined),
        "stats": stats,
        "by_rule": by_rule,
        "findings": findings,
        "summary": {"errors": len(errors), "findings": len(findings)},
        "verdict": ("clean: все адресные операнды именованные" if not findings
                    else "%d находок, %s блокирующих" % (len(findings), len(errors))),
        "by_severity": {key: sum(1 for item in findings if item["severity"] == key)
                        for key in ("error", "warn", "info")},
        "status": "CANDIDATE",
        "mcp_calls": 0,
    }


def format_report(result, limit=8):
    lines = ["каталог  %s" % result["out_dir"],
             "rdb      %s (%d объектов)" % (result["rdb"], result["objects"]),
             "символов в сборке: %d" % result["defined_symbols"],
             "операнды: %s" % result["stats"],
             "по правилам: %s" % (result["by_rule"] or "—"),
             "по важности: %s" % result["by_severity"], ""]
    shown = {}
    for item in result["findings"]:
        key = (item["rule"], item["severity"])
        shown[key] = shown.get(key, 0) + 1
        if item["severity"] != "error" and shown[key] > limit:
            if shown[key] == limit + 1:
                total = result["by_rule"][item["rule"]]
                lines.append("… %s: ещё %d таких же (полный список в --json)"
                             % (item["rule"], total - limit))
            continue
        lines.append("[%s] %-24s %s%s" % (item["severity"], item["rule"],
                                          "%s:%s " % (item["file"], item["line"])
                                          if item["file"] else "",
                                          item["detail"]))
        if item.get("suggestion") and shown[key] <= limit:
            lines.append("        → %s" % item["suggestion"])
    lines.append("")
    lines.append("ВЕРДИКТ  %s  [%s]  mcp_calls=%s" % (result["verdict"],
                                                      result["status"],
                                                      result["mcp_calls"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.symbolic_operand_lint",
        description="Сверка числовых и именованных операндов экспорта с RDB")
    parser.add_argument("--dir", required=True)
    parser.add_argument("--rom", required=True)
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_lint(args.dir, args.rom, rdb=args.rdb, origin=args.org)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str)
          if args.json else format_report(result))
    return 1 if result["summary"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
