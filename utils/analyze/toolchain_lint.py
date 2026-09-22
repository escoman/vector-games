"""Линт тулчейна по дереву экспорта (ТЗ §26, §27).

Правила взяты из реальных спотыканий реконструкции (Stage 12 putup,
docs/Z88DK.md), а не из головы:

* `org` — ровно один, и он равен origin образа: у z80asm на модуль один ORG,
  поэтому сборка `main.asm + code.asm + data.asm` даёт «ORG redefined»;
* hex-литера обязана начинаться с цифры: `ANI DFh` для z80asm — это
  «undefined symbol: DFh», правильно `ANI 0DFh`;
* view-файлы (`code/*.asm`, `data/*.asm`) в сборку не входят;
* длинные `defb`-дампы лучше заменять `INCBIN` — так побайтовая точность
  данных не зависит от формата листинга;
* каждый непокрытый диапазон обязан быть выложен (`gap_*` + `defs`/`incbin`),
  иначе round-trip не сойдётся;
* байты кода + данных + непокрытых диапазонов = размер ROM (интервальная
  арифметика, разрешённая ТЗ §8).

Ничего не собирается: за диагностикю ассемблера отвечает `syntax_check`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from analyze import export_asm
from analyze.mcp_session import addr_hex, to_addr

DEFB_DUMP_BYTES = 64               # порог «слишком длинный defb»
GAP_LABEL_RE = re.compile(r"^gap_[0-9A-Fa-f]{1,4}_?[0-9A-Fa-f]*:")


def _finding(rule, severity, detail, suggestion=None, file=None, line=None,
             evidence=None):
    return {"rule": rule, "severity": severity, "file": file, "line": line,
            "detail": detail, "suggestion": suggestion,
            "evidence": evidence or []}


built_files = export_asm.built_files


def check_org(out_dir, origin, built):
    findings = []
    seen = []
    for name in built:
        full = os.path.join(out_dir, name)
        if not os.path.isfile(full):
            findings.append(_finding("org-file-missing", "error",
                                     "include ссылается на отсутствующий файл",
                                     file=name))
            continue
        for number, text in enumerate(export_asm.read_lines(full), 1):
            directive, operand = export_asm.split_line(text)
            if directive != "org" or not operand:
                continue
            value = export_asm.asm_number(operand)
            seen.append((name, number, operand, value))
    if len(seen) != 1:
        findings.append(_finding("org-exactly-once", "error" if seen else "warn",
                                 "директив org найдено: %d (нужен один на модуль "
                                 "сборки)" % len(seen),
                                 suggestion="объединить листинг в один модуль или "
                                            "вынести org в main.asm",
                                 evidence=["%s:%s %s" % item[:3] for item in seen]))
    for name, number, operand, value in seen:
        if value is None or value != to_addr(origin):
            findings.append(_finding("org-matches-image", "error",
                                     "org %s ≠ origin образа %s"
                                     % (operand, addr_hex(origin)),
                                     file=name, line=number))
    return findings


def check_hex_literals(out_dir, built):
    """Литеры вида DFh без ведущего нуля — future «undefined symbol»."""
    findings = []
    for name in built:
        full = os.path.join(out_dir, name)
        if not os.path.isfile(full):
            continue
        counters = {}
        for number, text in enumerate(export_asm.read_lines(full), 1):
            directive, operand = export_asm.split_line(text)
            if not operand or directive in ("equ", "include"):
                continue
            for literal in export_asm.HEX_LITERAL_RE.findall(operand):
                if literal[0].isdigit():
                    continue
                counters.setdefault(literal.upper(), []).append(number)
        for literal, lines in sorted(counters.items()):
            findings.append(_finding(
                "hex-leading-zero", "error",
                "литера %sh без ведущего нуля: z80asm прочитает её как символ"
                % literal,
                file=name, line=lines[0],
                suggestion="%sh → %s (пример: ANI DFh → ANI 0DFh)"
                           % (literal, "0" + literal),
                evidence=["встречается в строках: %s"
                          % ", ".join(str(item) for item in lines[:8])]))
    return findings


def check_views_not_built(out_dir, built, entry="main.asm"):
    findings = []
    for name in built:
        if name.startswith(("code/", "data/")):
            findings.append(_finding("views-are-read-only", "error",
                                     "view-файл %s включён в сборку" % name,
                                     file=name,
                                     suggestion="сборка идёт только main.asm; "
                                                "code/ и data/ — для чтения"))
    return findings


def check_defb_dumps(out_dir, built):
    findings = []
    for name in built:
        full = os.path.join(out_dir, name)
        if not os.path.isfile(full):
            continue
        run_start, run_bytes = None, 0
        for number, text in enumerate(export_asm.read_lines(full), 1):
            directive, operand = export_asm.split_line(text)
            if directive in ("defb", "db", "defw", "dw") and operand:
                item_bytes = len([part for part in
                                  export_asm.OPERAND_SPLIT_RE.split(operand)
                                  if part])
                if directive in ("defw", "dw"):
                    item_bytes *= 2
                if run_start is None:
                    run_start = number
                run_bytes += item_bytes
                continue
            if run_bytes >= DEFB_DUMP_BYTES:
                findings.append(_finding(
                    "long-defb-use-incbin", "warn",
                    "дамп из %d байт начиная со строки %d: побайтовую точность "
                    "надёжнее держать в INCBIN" % (run_bytes, run_start),
                    file=name, line=run_start,
                    suggestion="вынести байты в .bin и заменить на incbin"))
            run_start, run_bytes = None, 0
        if run_bytes >= DEFB_DUMP_BYTES:
            findings.append(_finding("long-defb-use-incbin", "warn",
                                     "дамп из %d байт в конце %s" % (run_bytes, name),
                                     file=name))
    return findings


def check_gaps(out_dir, report, built):
    """Непокрытые диапазоны из export.json должны быть материализованы в ASM."""
    findings = []
    coverage = (report or {}).get("coverage") or {}
    uncovered = coverage.get("uncovered") or []
    emitted = set()
    gap_bytes = 0
    for name in built:
        full = os.path.join(out_dir, name)
        if not os.path.isfile(full):
            continue
        for text in export_asm.read_lines(full):
            stripped = text.strip()
            match = GAP_LABEL_RE.match(stripped)
            if match:
                emitted.add(match.group(0)[:-1].lower())
    for item in uncovered:
        try:
            start, end = to_addr(item["start"]), to_addr(item["end"])
        except (KeyError, TypeError, ValueError):
            findings.append(_finding("gap-shape", "warn",
                                     "непонятная запись uncovered: %r" % item))
            continue
        gap_bytes += max(0, end - start + 1)
    expected = {"gap_%s" % str(item.get("start", "")).lower().replace("0x", "")
                for item in uncovered}
    missing = sorted(name for name in expected
                     if not any(key.startswith(name) for key in emitted))
    if missing:
        findings.append(_finding("gap-materialized", "error",
                                 "%d непокрытых диапазонов(а) без метки gap_*"
                                 % len(missing),
                                 suggestion="проверить, что экспортёр выложил "
                                            "gap-блоки в layout.asm",
                                 evidence=missing[:8]))
    return findings, {"uncovered_runs": len(uncovered),
                      "uncovered_bytes": gap_bytes,
                      "gap_labels": len(emitted)}


def check_coverage_arithmetic(report, rom_size):
    coverage = (report or {}).get("coverage") or {}
    if not coverage:
        return [_finding("coverage-present", "error",
                         "в export.json нет секции coverage")]
    code = int(coverage.get("code_bytes") or 0)
    data = int(coverage.get("data_bytes") or 0)
    uncovered = sum(max(0, to_addr(item["end"]) - to_addr(item["start"]) + 1)
                    for item in coverage.get("uncovered") or [])
    total = code + data + uncovered
    delta = total - int(rom_size or 0)
    if delta:
        return [_finding("coverage-sums-to-rom", "warn",
                         "code(%d)+data(%d)+uncovered(%d)=%d, размер ROM=%d "
                         "(расхождение %d)" % (code, data, uncovered, total,
                                               rom_size, delta),
                         suggestion="часть байт принадлежит и коду, и данным, "
                                    "либо выпала из окна экспорта")]
    return []


def run_lint(out_dir, origin=0x0100, entry="main.asm", rom_size=None):
    report = export_asm.read_export_json(out_dir) or {}
    built = built_files(out_dir, entry)
    findings = []
    findings += check_org(out_dir, origin, built)
    findings += check_hex_literals(out_dir, built)
    findings += check_views_not_built(out_dir, built, entry)
    findings += check_defb_dumps(out_dir, built)
    gaps, gap_stats = check_gaps(out_dir, report, built)
    findings += gaps
    findings += check_coverage_arithmetic(report, rom_size or report.get("rom_size"))
    errors = [item for item in findings if item["severity"] == "error"]
    by_rule = {}
    for item in findings:
        by_rule[item["rule"]] = by_rule.get(item["rule"], 0) + 1
    return {
        "out_dir": os.path.abspath(out_dir),
        "entry": entry,
        "built": built,
        "checks": ["org-exactly-once", "org-matches-image", "hex-leading-zero",
                   "views-are-read-only", "long-defb-use-incbin",
                   "gap-materialized", "coverage-sums-to-rom"],
        "gap_stats": gap_stats,
        "by_rule": by_rule,
        "findings": findings,
        "summary": {"errors": len(errors),
                    "warnings": len(findings) - len(errors)},
        "verdict": "clean" if not errors else "blocked: %s error(ов)" % len(errors),
        "status": "CANDIDATE",
        "mcp_calls": 0,
    }


def format_report(result, limit=10):
    lines = ["каталог %s" % result["out_dir"],
             "в сборку: %s" % ", ".join(result["built"]),
             "gap-статистика: %s" % result["gap_stats"],
             "по правилам: %s" % (result["by_rule"] or "—"), ""]
    if not result["findings"]:
        lines.append("находок нет — дерево соответствует правилам тулчейна")
    shown = 0
    for item in result["findings"]:
        if item["severity"] == "warn" and shown >= limit:
            rest = sum(1 for other in result["findings"]
                       if other["severity"] == "warn") - limit
            if rest > 0:
                lines.append("… ещё %d предупреждений(я) того же рода"
                             % rest)
            break
        lines.append("[%s] %-22s %s%s" % (item["severity"], item["rule"],
                                          "%s:%s " % (item["file"], item["line"])
                                          if item.get("file") else "",
                                          item["detail"]))
        if item.get("suggestion"):
            lines.append("        → %s" % item["suggestion"])
        for evidence in item.get("evidence") or []:
            lines.append("        | %s" % evidence)
        shown += 1
    lines.append("")
    lines.append("ВЕРДИКТ  %s  [%s]  mcp_calls=%s" % (result["verdict"],
                                                      result["status"],
                                                      result["mcp_calls"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.toolchain_lint",
        description="Проверка дерева экспорта под тулчейн z80asm")
    parser.add_argument("--dir", required=True, help="каталог экспорта")
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--entry", default="main.asm")
    parser.add_argument("--rom-size", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_lint(args.dir, origin=args.org, entry=args.entry,
                      rom_size=args.rom_size)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str)
          if args.json else format_report(result))
    return 1 if result["summary"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
