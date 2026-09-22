"""Экспорт ASM: обёртка над `v06c-asm-export`, не генератор ASM (ТЗ §24, §25).

ASM пишет экспортер из отладчика, а не Python: пакет только находит бинарь,
запускает его, разбирает `export.json` и складывает результат в доказательста
с провенансом. Собственных правил форматирования ассемблерного текста здесь
нет — их изобретать запрещено.

Экспортёров два источника истины не имеют: ASM строится из образа ROM и RDB,
поэтому runtime-патчи (ТЗ §16) в выдаче не появляется — в образе по адресу
патча лежат нули, и round-trip обязан это воспроизводить (см.
`roundtrip_verify`).

Поиск бинаря: $V06C_ASM_EXPORT → --exporter → PATH → ../vector-debugger →
~/Projects/vector-debugger/debugger/build. Пересборка целевого проекта не
входит в задачи пакета.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

from analyze.mcp_session import addr_hex, envelope, open_session, to_addr

EXPORTER_ENV = "V06C_ASM_EXPORT"
Z80ASM_ENV = "Z80ASM"
EXPORT_FILES = ("main.asm", "layout.asm", "export.json")
DEFAULT_BUILD_FLAGS = ["-b", "-m=8080_strict"]
# Сообщения z80asm: "<файл>:<строка>: error: текст" + карательная строка
ASM_MESSAGE_RE = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+): "
                            r"(?P<kind>error|warning|fatal):\s*(?P<text>.*)$")


def project_root(start=None):
    """Корень репозитория: тот, где лежит пакет analyze."""
    here = os.path.abspath(start or os.path.dirname(__file__))
    return os.path.dirname(os.path.dirname(here))


def find_exporter(explicit=None, root=None):
    """Путь к v06c-asm-export или None."""
    root = root or project_root()
    candidates = [explicit, os.environ.get(EXPORTER_ENV),
                  shutil.which("v06c-asm-export")]
    candidates += [
        os.path.join(root, "..", "vector-debugger", "debugger", "build",
                     "v06c-asm-export"),
        os.path.expanduser("~/Projects/vector-debugger/debugger/build/"
                           "v06c-asm-export"),
        "/home/alexey/Projects/vector-debugger/debugger/build/v06c-asm-export",
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return os.path.abspath(path)
    return None


def find_z80asm(explicit=None, root=None):
    """Путь к z80asm (z88dk). Правило one-module см. `toolchain_lint`."""
    root = root or project_root()
    candidates = [explicit, os.environ.get(Z80ASM_ENV), shutil.which("z80asm")]
    candidates += [os.path.join(root, "z88dk", "bin", name)
                   for name in ("z80asm", "z88dk-z80asm")]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return os.path.abspath(path)
    return None


def run_export(rom, out_dir, exporter=None, rdb=None, origin=0x0100,
               strict=False, timeout=600):
    """Вызвать CLI-экспортёр. Вернуть (export.json, stdout, stderr, rc)."""
    exporter = exporter or find_exporter()
    if not exporter:
        raise SystemExit("v06c-asm-export не найден. Задайте %s=… или "
                         "--exporter …" % EXPORTER_ENV)
    os.makedirs(out_dir, exist_ok=True)
    command = [exporter, "--rom", os.path.abspath(rom),
               "--output", os.path.abspath(out_dir),
               "--origin", "%04X" % to_addr(origin)]
    if rdb:
        command += ["--rdb", os.path.abspath(rdb)]
    if strict:
        command.append("--strict")
    process = subprocess.run(command, capture_output=True, text=True,
                             timeout=timeout, cwd=out_dir)
    report = read_export_json(out_dir)
    return report, process.stdout, process.stderr, process.returncode, command


def read_export_json(out_dir):
    path = os.path.join(out_dir, "export.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return json.load(handle)


def assemble(out_dir, z80asm=None, main="main.asm", output=None,
             flags=None, timeout=600):
    """Собрать дерево экспорта. Один модуль — иначе «ORG redefined»."""
    z80asm = z80asm or find_z80asm()
    if not z80asm:
        raise SystemExit("z80asm не найден. Задайте %s=… или --z80asm …"
                         % Z80ASM_ENV)
    output = output or os.path.join(out_dir, "roundtrip.bin")
    command = [z80asm] + list(flags or DEFAULT_BUILD_FLAGS) + \
        ["-o=%s" % os.path.abspath(output), main]
    process = subprocess.run(command, capture_output=True, text=True,
                             timeout=timeout, cwd=out_dir)
    return {"command": command, "z80asm": z80asm, "output": output,
            "returncode": process.returncode,
            "stdout": process.stdout, "stderr": process.stderr,
            "messages": parse_asm_messages(process.stdout + process.stderr,
                                           out_dir)}


def parse_asm_messages(text, out_dir=""):
    """Диагностику ассемблера → структурированные находки."""
    findings = []
    for raw in (text or "").splitlines():
        match = ASM_MESSAGE_RE.match(raw.strip())
        if not match:
            continue
        findings.append({
            "file": match.group("file"),
            "line": int(match.group("line")),
            "kind": match.group("kind"),
            "text": match.group("text").strip(),
            "path": os.path.abspath(os.path.join(out_dir, match.group("file")))
            if out_dir else None,
        })
    return findings


def tree(out_dir):
    """Файлы экспорта: имя → путь (только .asm/.json/.bin у корня и в подпапках)."""
    listing = {}
    for base, _dirs, files in os.walk(out_dir):
        for name in files:
            if name.endswith((".asm", ".json", ".bin", ".sym", ".o")):
                path = os.path.join(base, name)
                listing[os.path.relpath(path, out_dir)] = path
    return listing


def read_lines(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read().splitlines()


# ---------------------------------------------------------------------------
# Разбор текста экспорта (только синтаксис листинга, семантики нет)
# ---------------------------------------------------------------------------

LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(?:;.*)?$")
DIRECTIVE_RE = re.compile(r"^\s*([.:]?[A-Za-z_][A-Za-z0-9_]*)\s*(.*)$")
HEX_LITERAL_RE = re.compile(r"\b([0-9A-Fa-f]+)h\b", re.IGNORECASE)
OPERAND_SPLIT_RE = re.compile(r"[,\s]+")
COMMENT_SPLIT_RE = re.compile(r"\s;.*$")
WHITESPACE_RE = re.compile(r"[ \t]+")
ASM_NUMBER_RE = re.compile(r"^(?:([0-9A-Fa-f]+)h|0x([0-9A-Fa-f]+)|(\d+))$",
                           re.IGNORECASE)
INCLUDE_RE = re.compile(r'^\s*include\s+"([^"]+)"', re.IGNORECASE)

# Зарезервированные слова листинга: операнд-регистр никогда не бывает меткой.
# Список — синтаксис 8080/z80-мнемоник, а не знание о конкретной ROM.
REGISTERS_8080 = ("A", "B", "C", "D", "E", "H", "L", "M",
                  "PSW", "BC", "DE", "HL", "SP")
RESERVED_OPERANDS = frozenset(
    list(REGISTERS_8080)
    + ["AF", "BC'", "DE'", "HL'", "IX", "IY", "IXH", "IXL", "IYH", "IYL",
       "I", "R", "ALL"]                                      # z80-надстройки
    + ["NZ", "Z", "NC", "C", "PO", "PE", "P", "M"])         # условия

# Метка в начале строки, после неё может стоять мнемоника или директива
LINE_LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:(.*)$")


def asm_number(text):
    """Число из листинга z80asm: '0FFh' / '0x0100' / '256' → int или None."""
    if text is None:
        return None
    if isinstance(text, int):
        return text
    match = ASM_NUMBER_RE.match(str(text).strip())
    if not match:
        return None
    body = next((item for item in match.groups() if item), None)
    if body is None:
        return None
    return int(body, 10) if match.group(3) else int(body, 16)


def built_files(out_dir, entry="main.asm"):
    """Файлы, реально участвующие в сборке: entry плюс его незакомментированные include.

    View-каталоги (`code/`, `data/`) в этот список не попадают — они только
    для чтения, а два ORG в сборке z80asm не переваривает.
    """
    path = os.path.join(out_dir, entry)
    if not os.path.isfile(path):
        return []
    included = [entry]
    for text in read_lines(path):
        match = INCLUDE_RE.match(text)
        if match and not text.strip().startswith(";"):
            included.append(match.group(1))
    return included


def split_line(text):
    """'call func_x  ; комм.' → ('call', 'func_x').

    Разделитель — произвольные пробельные символы: листинг экспортёра
    использует табы и между мнемоникой, и между операндами.
    Ведущая метка снимается, иначе `gap_x: defb …` выглядело бы как
    неизвестная директива `gap_x:`.
    """
    label, directive, operand = line_parts(text)
    return directive, operand


def line_parts(text):
    """Строка листинга → (метка, директива, операнды); всё в нижнем регистре.

    Покрывает и `name: mov a,b`, и чистую метку `name:`, и `name: equ 5`.
    """
    body = COMMENT_SPLIT_RE.sub("", text).rstrip()
    if not body or body.lstrip().startswith(";"):
        return None, None, None
    stripped = body.strip()
    label = None
    match = LINE_LABEL_RE.match(stripped)
    if match:
        label = match.group(1)
        stripped = match.group(2).strip()
    if not stripped:
        return label, "label", ""
    parts = WHITESPACE_RE.split(stripped, 1)
    directive = parts[0].lower().rstrip(":")
    operand = (parts[1] if len(parts) > 1 else "").strip()
    # «name equ 5»: эквивалент записывается без метки-двоеточия, поэтому имя
    # оказывается в поле директивы, а `equ` — в операндах
    tail = WHITESPACE_RE.split(operand, 1) if operand else []
    if not label and tail and tail[0].lower() in ("equ", "=") and len(tail) > 1:
        return directive, "equ", tail[1].strip()
    return label, directive, operand


def iter_instructions(out_dir, files=None):
    """(файл, номер строки, мнемоника/директива, операнды, сырая строка)."""
    listing = tree(out_dir)
    for name in (files or sorted(listing)):
        if not name.endswith(".asm"):
            continue
        number = 0
        for text in read_lines(listing[name]):
            number += 1
            if LABEL_RE.match(text.strip()):
                yield (name, number, "label", [], text)
                continue
            directive, operand = split_line(text)
            if not directive:
                continue
            operands = [item for item in OPERAND_SPLIT_RE.split(operand) if item] \
                if operand else []
            yield (name, number, directive, operands, text)


def defined_symbols(out_dir, files=None):
    """Имя → где определено (метка или EQU-псевдоним).

    `files` — ограничить список (например только сборочными файлами): view-
    каталоги повторяют те же метки, и без фильтра непонятно, где символ
    определён на самом деле.
    """
    names = {}
    listing = tree(out_dir)
    for path in (files if files is not None else sorted(listing)):
        full = listing.get(path) or os.path.join(out_dir, path)
        if not path.endswith(".asm") or not os.path.isfile(full):
            continue
        for number, text in enumerate(read_lines(full), 1):
            label, directive, operand = line_parts(text)
            if label:
                names.setdefault(label, {"file": path, "line": number,
                                         "kind": "equ" if directive == "equ"
                                         else "label",
                                         "value": operand if directive == "equ"
                                         else ""})
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.export_asm",
        description="Запуск v06c-asm-export и разбор export.json")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--rdb", default=None,
                        help="по умолчанию экспортёр сам возьмёт <rom>.rdb")
    parser.add_argument("--out", default=None, help="куда класть дерево экспорта")
    parser.add_argument("--exporter", default=None)
    parser.add_argument("--strict", action="store_true",
                        help="передать --strict экспортёру (ненулевой rc при "
                             "неполном покрытии)")
    parser.add_argument("--assemble", action="store_true",
                        help="сразу собрать дерево z80asm и показать диагностику")
    parser.add_argument("--z80asm", default=None)
    parser.add_argument("--cache", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    out_dir = args.out or os.path.join(".scratch", "export",
                                       os.path.splitext(
                                           os.path.basename(args.rom))[0])
    report, stdout, stderr, code, command = run_export(
        args.rom, out_dir, exporter=args.exporter, rdb=args.rdb,
        origin=args.org, strict=args.strict)
    result = {
        "command": command,
        "exporter": find_exporter(args.exporter),
        "origin": addr_hex(args.org),
        "out_dir": os.path.abspath(out_dir),
        "returncode": code,
        "export_json": report,
        "files": sorted(tree(out_dir)),
        "stdout_tail": stdout.splitlines()[-12:] if stdout else [],
        "stderr_tail": stderr.splitlines()[-12:] if stderr else [],
        "note": "ASM генерирует v06c-asm-export; пакет только запускает и "
                "разбирает (ТЗ §24)",
    }
    if args.assemble and report:
        result["assemble"] = assemble(out_dir, z80asm=args.z80asm)
    verdict = "экспортёр: rc=%s, файлов %d" % (code, len(result["files"]))
    build = result.get("assemble") or {}
    if build:
        binary = build.get("output")
        size = (os.path.getsize(binary) if binary and os.path.isfile(binary)
                else None)
        verdict = ("экспортёр: rc=%s, файлов %d, сборка: rc=%s%s"
                   % (code, len(result["files"]), build["returncode"],
                      ", %d байт" % size if size is not None else ""))
    result = envelope(result, module="export_asm", status="DERIVED",
                      verdict=verdict)
    # провенанс: дерево — производное от ROM+RDB
    try:
        _save_provenance(out_dir, result)
    except Exception as error:                                # noqa: BLE001
        result["provenance_error"] = str(error)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_report(result))
    return 0 if code == 0 else 1


def _save_provenance(out_dir, result):
    path = os.path.join(out_dir, "provenance.json")
    payload = {"rom": result.get("command", [None, None])[1],
               "exporter": result["exporter"], "origin": result["origin"],
               "status": "DERIVED", "export_json": result["export_json"],
               "note": result["note"]}
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)


def format_report(result):
    report = result.get("export_json") or {}
    coverage = report.get("coverage") or {}
    lines = ["экспортёр %s" % result["exporter"],
             "команда:  %s" % " ".join(result["command"]),
             "каталог:  %s" % result["out_dir"],
             "rc:       %s" % result["returncode"],
             "",
             "ROM       %s (%s байт, origin %s)" % (report.get("rom"),
                                                    report.get("rom_size"),
                                                    report.get("origin")),
             "объектов  %s, связей %s, диапазонов кода %s, данных %s"
             % (report.get("objects"), report.get("links"),
                report.get("code_ranges"), report.get("data_ranges")),
             "var/warn  errors=%s warnings=%s conflicts=%s unresolved=%s"
             % (report.get("errors"), report.get("warnings"),
                report.get("conflicts"), report.get("unresolved_references")),
             "покрытие  code=%s data=%s из %s байт, вне окна отброшено %s, "
             "непокрыто %s прогон(ов), complete=%s"
             % (coverage.get("code_bytes"), coverage.get("data_bytes"),
                coverage.get("rom_bytes"), coverage.get("outside_window_dropped"),
                len(coverage.get("uncovered") or []), coverage.get("complete")),
             "файлы     " + ", ".join(result["files"][:8]) +
             (" …" if len(result["files"]) > 8 else ""),
             "доказательство: %s (происхождение — DERIVED из ROM+RDB)"
             % os.path.join(result["out_dir"], "provenance.json")]
    build = result.get("assemble")
    if build:
        lines.append("")
        lines.append("сборка:   %s → %s (rc=%s)"
                     % (" ".join(build["command"][-3:]), build["output"],
                        build["returncode"]))
        for message in build["messages"][:20]:
            lines.append("  %s:%s %s: %s" % (message["file"], message["line"],
                                             message["kind"], message["text"]))
        if not build["messages"] and build["returncode"] == 0:
            lines.append("  диагностика пустая: собралось чисто")
    for tail in (result["stdout_tail"] or [])[-6:]:
        lines.append("  | " + tail)
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
