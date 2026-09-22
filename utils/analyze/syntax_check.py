"""Синтаксическая проверка дерева экспорта (ТЗ §26, §27).

Единственный источник правды по синтаксису — сам `z80asm`: Python не знает
правил ассемблера и не изобретает их, а только запускает сборку и разбирает
диагностику. Отсюда два правила:

* собирается ровно один модуль (`main.asm`), потому что два ORG z80asm не
  переваривает — это проверка дерева, а не выдумка линейки;
* находка про каждую строку диагностики сохраняется как есть, с файлом и
  номером строки, плюс «что обычно это значит» из реальных спотыканий
  реконструкции (ведущий ноль в hex, view-файл в сборке, отсутствующий
  include).

Модуль не правит экспорт: ASM генерирует `v06c-asm-export`, а не мы (ТЗ §24).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze import export_asm

# Подсказки по частым диагностикам: сопоставление по подстроке сообщения.
HINTS = (
    ("undefined symbol", "имя есть в RDB, но не выгружено в ASM, либо hex-литера "
                         "без ведущего нуля (DFh → 0DFh)"),
    ("ORG redefined", "в сборку попало два модуля или view-файл; собирается "
                      "только main.asm"),
    ("orphan", "непарная кавычка/скобка в строке"),
    ("syntax error", "строка не разбирается: проверить операнды и разделители"),
    ("already defined", "метка продублирована — обычно main.asm и layout.asm "
                        "определяют одно и то же"),
    ("file not found", "include ссылается на файл вне каталога экспорта"),
    ("value out of range", "число не влезает в поле инструкции"),
)


def hint_for(text):
    low = (text or "").lower()
    for needle, hint in HINTS:
        if needle in low:
            return hint
    return None


def classify(messages):
    findings = []
    for message in messages:
        kind = message.get("kind", "error")
        findings.append({
            "rule": "assembler-%s" % kind,
            "severity": "error" if kind in ("error", "fatal") else "warn",
            "file": message.get("file"),
            "line": message.get("line"),
            "detail": message.get("text", ""),
            "suggestion": hint_for(message.get("text", "")),
            "evidence": [],
        })
    return findings


def run_check(out_dir, z80asm=None, entry="main.asm", output=None,
              flags=None, export_first=False, rom=None, rdb=None,
              origin=0x0100):
    """Собрать дерево и вернуть разбор диагностики.

    `export_first=True` пересоздаёт ASM через v06c-asm-export: так проверка
    не зависит от того, что лежало в каталоге раньше.
    """
    result = {"out_dir": os.path.abspath(out_dir), "entry": entry,
              "mcp_calls": 0, "status": "DERIVED"}
    if export_first:
        if not rom:
            raise SystemExit("--export-first требует --rom")
        report, stdout, stderr, code, command = export_asm.run_export(
            rom, out_dir, rdb=rdb, origin=origin)
        result["export"] = {"command": command, "returncode": code,
                            "rom_size": (report or {}).get("rom_size")}
        if code != 0:
            result.update(build=None,
                          findings=[{"rule": "export-failed", "severity": "error",
                                     "file": None, "line": None,
                                     "detail": "экспортёр вернул rc=%s" % code,
                                     "suggestion": (stderr or stdout).strip()[:400],
                                     "evidence": []}],
                          counts={"error": 1},
                          verdict="blocked: ASM не выгружен",
                          summary={"errors": 1, "warnings": 0})
            return result
    build = export_asm.assemble(out_dir, z80asm=z80asm, main=entry,
                                output=output, flags=flags)
    findings = classify(build["messages"])
    errors = [item for item in findings if item["severity"] == "error"]
    counts = {}
    for item in findings:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1
    if build["returncode"] == 0 and not findings:
        verdict = "clean: собралось без единой претензии"
    elif build["returncode"] != 0 and not findings:
        verdict = ("blocked: rc=%s, но диагностика не разобралась — смотреть "
                   "stderr целиком" % build["returncode"])
        findings.append({"rule": "unparsed-output", "severity": "error",
                         "file": None, "line": None,
                         "detail": "ассемблер ругался, но строки не похожи на "
                                   "«файл:строка: error: …»",
                         "suggestion": "взять stdout/stderr из --json",
                         "evidence": (build["stdout"] + "\n"
                                      + build["stderr"]).splitlines()[:10]})
        errors = findings
    elif errors:
        verdict = "blocked: %d ошибка(ов) сборки" % len(errors)
    else:
        verdict = "clean: собралось, но с %d предупреждением(ями)" % len(findings)
    result.update(build={"command": build["command"], "z80asm": build["z80asm"],
                         "output": build["output"],
                         "returncode": build["returncode"],
                         "bytes": (os.path.getsize(build["output"])
                                   if os.path.isfile(build["output"]) else None)},
                findings=findings, counts=counts, verdict=verdict,
                summary={"errors": len(errors),
                         "warnings": len(findings) - len(errors)})
    return result


def format_report(result, limit=15):
    build = result.get("build") or {}
    lines = ["каталог  %s" % result["out_dir"],
             "модуль   %s" % result["entry"],
             "команда  %s" % " ".join(build.get("command", [])[:2] +
                                      build.get("command", [])[-2:]),
             "результат rc=%s, %s байт на выходе"
             % (build.get("returncode"), build.get("bytes")),
             "находки  %s" % (result["counts"] or "—"), ""]
    if not result["findings"]:
        lines.append("диагностика пустая — синтаксис дерева чист")
    for index, item in enumerate(result["findings"]):
        if index >= limit:
            lines.append("… ещё %d (полный список в --json)"
                         % (len(result["findings"]) - limit))
            break
        lines.append("[%s] %-22s %s%s" % (item["severity"], item["rule"],
                                          "%s:%s " % (item["file"], item["line"])
                                          if item.get("file") else "",
                                          item["detail"]))
        if item.get("suggestion"):
            lines.append("        → %s" % item["suggestion"])
        for evidence in item.get("evidence") or []:
            lines.append("        | %s" % evidence)
    lines.append("")
    lines.append("ВЕРДИКТ  %s  [%s]  mcp_calls=%s" % (result["verdict"],
                                                      result["status"],
                                                      result["mcp_calls"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.syntax_check",
        description="Сборка дерева экспорта настоящим z80asm и разбор диагностики")
    parser.add_argument("--dir", required=True, help="каталог экспорта")
    parser.add_argument("--entry", default="main.asm")
    parser.add_argument("--z80asm", default=None)
    parser.add_argument("--out", default=None,
                        help="куда положить бинарь (по умолчанию roundtrip.bin)")
    parser.add_argument("--export-first", action="store_true",
                        help="пересоздать ASM перед сборкой")
    parser.add_argument("--rom", default=None)
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_check(args.dir, z80asm=args.z80asm, entry=args.entry,
                       output=args.out, export_first=args.export_first,
                       rom=args.rom, rdb=args.rdb, origin=args.org)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str)
          if args.json else format_report(result))
    return 1 if result["summary"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
