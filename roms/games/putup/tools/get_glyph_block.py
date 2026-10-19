#!/usr/bin/env python3
"""Снимок распакованного глиф-блока 0x6000..0x7FFF через MCP (этап A, шаг 2).

Загружает оригинал ../../redesign/putup/src/putup.rom (org 0x0100), даёт отработать ~4 с (полная
инициализация: загрузка глифов, seed 0x2761, копир спрайтов 0x7418), паузит
CPU и сохраняет debug_read_memory_range(0x6000, 8192) ВЕРБАТИМ как
побайтовые DEFB в asm/data/data_glyph_block_unpacked.asm (ТЗ §3: байты перевозит
отладчик; 2 строки по 16 Б на глиф).

Использование: python3 tools/get_glyph_block.py [--seconds 4]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(PROJ, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "utils", "analyze"))

from mcp_session import McpSession, bytes_of  # noqa: E402

ROM = os.path.join(ROOT, "roms", "redesign", "putup", "src", "putup.rom")
OUT = os.path.join(PROJ, "asm", "data", "data_glyph_block_unpacked.asm")
ADDR, LENGTH = 0x6000, 8192


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=4.0,
                    help="сколько времени дать инициализации отработать")
    args = ap.parse_args()

    with McpSession() as s:
        s.load_rom(ROM, org=0x0100)
        s.call("debug_run")
        time.sleep(args.seconds)
        s.call("debug_pause")
        payload = s.call("debug_read_memory_range",
                         {"address": ADDR, "length": LENGTH})
        data = bytes_of(payload)

    if len(data) != LENGTH:
        sys.exit("ошибка: получено %d байт, ожидалось %d" % (len(data), LENGTH))
    # Контрольная точка: глиф 0 засейджен func_load_gfx_2761 → 24×00 затем 8×FF.
    if data[:24] != b"\x00" * 24 or data[24:32] != b"\xFF" * 8:
        sys.exit("ошибка: первые 32 байта не похожи на засейджненный глиф 0 — "
                 "инициализация не завершилась?")

    defb = []
    for g in range(LENGTH // 32):
        gl = data[g * 32:(g + 1) * 32]
        row = lambda ch: ", ".join("0%Xh" % b for b in ch)
        defb.append("    DEFB %s   ; глиф %d @0x%04X" % (row(gl[:16]), g, ADDR + g * 32))
        defb.append("    DEFB %s" % row(gl[16:]))
    txt = "\n".join([
        "; Данные: data_glyph_block_unpacked",
        "; Адрес: 0x6000 (исторический адрес распаковки; в сборке переносится GLYPH_BASE)",
        "; Размер: 8192 байта (256 глифов x 32 Б)",
        "; Снят tools/get_glyph_block.py через MCP; sha256 = %s." % hashlib.sha256(data).hexdigest(),
        "; ВЕРБАТИМ снимка; см. историчный комментарий этапов A/B в git.",
        "",
        "data_glyph_block:                  ; историческое имя (ptr_table, стр. заставки)",
        "data_glyph_block_unpacked:",
    ] + defb + [""])
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(txt)
    print("сохранено %d Б (DEFB) → %s" % (len(data), os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
