#!/usr/bin/env python3
"""Выгрузка блока глифов PUTUP из RUNTIME RAM в tools/glyph_block.bin.

Блок глифов putup.rom собирается в рантайме (func_load_glyph_block из
упакованного источника @0x3041), в ROM его байтов нет — поэтому читаем
RAM уже запущенной игры, как это делает roms/redesign/putup/tools/glyph_sheet.py:

    RAM 0x6000, 256 глифов x 32 байта = 4 плоскости x 8 строк.

Плоскость 0 — битмап символа, плоскость 3 = ~плоскость 0; коды, у которых
это не так, шрифтом не являются (см. gen_putup_font.py).

Запуск (нужен сервер v06c-mcp):

    V06C_MCP=/path/to/v06c-mcp python3 tools/dump_glyph_block.py

Результат: tools/glyph_block.bin (8192 байта) — вход для gen_putup_font.py.
Его можно не переснимать: файл лежит в репозитории.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'utils'))

from analyze.mcp_session import open_session       # noqa: E402
from analyze.probe import run_for                  # noqa: E402

ROM = os.path.join(REPO, 'roms/redesign/putup/src/putup.rom')
ORG = 0x0100
BLOCK = 0x6000
GLYPHS, STRIDE, ROWS = 256, 32, 8
OUT = os.path.join(HERE, 'glyph_block.bin')

session, cache = open_session(rom=ROM, org=ORG,
                              cache_dir=os.path.join(HERE, '.analyze'))
try:
    run_for(session, cache, rom=ROM, org=ORG, seconds=3.0)
    resp = session.call('debug_read_memory_range',
                        address=BLOCK, length=GLYPHS * STRIDE)
finally:
    stats = session.stats()
    session.close()

data = resp.get('data') or resp.get('bytes') or resp.get('values')
if isinstance(data, str):
    raw = bytes.fromhex(data.replace(' ', ''))
else:
    raw = bytes(int(x, 16) if isinstance(x, str) else int(x) & 0xFF for x in data)

assert len(raw) == GLYPHS * STRIDE, f'прочитано {len(raw)} байт'
open(OUT, 'wb').write(raw)

plane0 = b''.join(raw[g * STRIDE:g * STRIDE + ROWS] for g in range(GLYPHS))
nonempty = sum(1 for g in range(GLYPHS)
               if any(plane0[g * ROWS:(g + 1) * ROWS]))
print(f'{OUT}: {len(raw)} Б, mcp-вызовов: {stats["total_calls"]}')
print(f'непустых глифов (плоскость 0): {nonempty} из {GLYPHS}')
