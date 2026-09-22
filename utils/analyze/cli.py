#!/usr/bin/env python3
"""Точка входа пакета: `python3 utils/analyze/cli.py <команда> …`.

Модули пакета — часть пакета `analyze`, поэтому прямое `python3
utils/analyze/coverage.py` не работает (импорты идут как `from analyze.x`).
Этот диспетчер подкладывает корень `utils/` в sys.path и вызывает `main()`
нужного модуля, так что одинаково работают:

    python3 utils/analyze/cli.py coverage --rom …
    python3 -m analyze.coverage --rom …
    PYTHONPATH=utils python3 -c "from analyze import coverage"
"""
from __future__ import annotations

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UTILS = os.path.dirname(HERE)
if UTILS not in sys.path:
    sys.path.insert(0, UTILS)

# Команда → модуль. Совпадает с именами файлов пакета.
COMMANDS = [
    "probe", "disassembly", "coverage", "seed_rdb", "rdb_lint", "memory_diff",
    "io_signature", "abi_scan", "strings_scan", "table_shape", "glyph_scan",
    "vram_credits", "export_asm", "symbolic_operand_lint", "syntax_check",
    "roundtrip_verify", "measure_sizes", "toolchain_lint", "music2midi",
    "report_gen", "pipeline", "clear_cache",
]


def usage(code=2):
    print("использование: cli.py <команда> [параметры …]\n")
    print("команды:")
    for name in COMMANDS:
        print("  " + name)
    print("\nсправка по команде: cli.py <команда> --help")
    return code


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        return usage()
    command, rest = argv[0], argv[1:]
    if command not in COMMANDS:
        print("неизвестная команда: %s" % command, file=sys.stderr)
        return usage()
    module = importlib.import_module("analyze.%s" % command)
    entry = getattr(module, "main", None)
    if entry is None:
        print("модуль analyze.%s не реализует main()" % command, file=sys.stderr)
        return 3
    return entry(rest) or 0


if __name__ == "__main__":
    sys.exit(main())
