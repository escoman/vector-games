#!/usr/bin/env python3
"""PUTUP → MIDI: тонкая обёртка над универсальным `analyze.music2midi`.

Всё, что здесь специфично для PUTUP, вынесено в `music_spec.json` рядом:
адреса трёх дорожек, длина, шаг в тиках, темп, смещение ноты, дампы-эталон.
Движок (`utils/analyze/music2midi.py`) про PUTUP не знает ничего.

Источник фактов — roms/redesign/putup/reports/Stage11_music_spec.md
(Stage 11, всё проверено через MCP; «MIDI = код + 30», шаг 6 тиков VBlank).
Эталонные дампы §10 сверяются побайтово перед записью: любое расхождение
останавливает конвертер, а не превращается в подозрительную ноту.

    python3 roms/redesign/putup/tools/putup2midi.py [-o выход.mid]
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SPEC = os.path.join(HERE, "music_spec.json")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        sys.path.insert(0, os.path.join(ROOT, "utils"))
        from analyze import music2midi
    except ImportError:
        # PYTHONPATH=utils тоже работает; если пакета нет — зовём CLI напрямую
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "utils", "analyze", "cli.py"),
             "music2midi", "--spec", SPEC] + argv,
            cwd=ROOT, check=False)
        return result.returncode
    out = None
    if argv and argv[0] in ("-o", "--output") and len(argv) > 1:
        out = argv[1]
    result = music2midi.convert(SPEC, out_path=out)
    print(music2midi.format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
