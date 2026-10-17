#!/usr/bin/env python3
"""Stage 0: выгрузить распакованный интерпретатор BASIC из RAM в `basic.r0m`.

`bas2997.rom` — самораспаковывающийся образ: стаб на `0x0100` копирует поток в
VRAM-стагинг `0x8000`, LZ-распаковщик разворачивает интерпретатор в низкую RAM
`0x0000..0x42FF`, затем reset-вектор `0x0000` (`LXI SP,7FFF; JMP 19CC`) передаёт
управление инициализации на `0x19CC`. Офлайн-декод потока ненадёжен (см. TZ.md),
поэтому «распакованный ROM» снимаем RAM-снапшотом с запущенного образа.

Точка съёма — первый вход на `0x19CC`: распаковка уже завершена, а инициализация
ещё не выполнила ни одной инструкции, значит RAM (`0x0000..0x42FF`) — ровно
декомпрессированный образ, без рантайм-мутаций. С `0x4300` начинается пустая
программная область BASIC (её в ROM не берём).

Расширение выхода — строго `.r0m`: по соглашению загрузчика `.r0m` ставится на
`0x0000`, куда образ и распакован. Под именем `.rom` тот же файл уехал бы на
`0x0100` (сдвиг на 0x100) и не запустился бы — образ начинается с reset-вектора
page zero, который при `.rom`-загрузке не исполняется.

Только через пакет `analyze` (общий MCP-сеанс), без своего декодера.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/dump_interp.py
    PYTHONPATH=utils python3 roms/redesign/basic/tools/dump_interp.py \
        --rom .../bas2997.rom --out .../basic.r0m --org 0x0100 \
        --entry 0x19CC --lo 0x0000 --hi 0x42FF
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from analyze.mcp_session import bytes_of, open_session, to_addr

# Значения по умолчанию сняты Stage 0 с живого bas2997.rom (см. Stage0_boot.md).
DEFAULT_ROM = "roms/redesign/basic/src/bas2997.rom"
DEFAULT_OUT = "roms/redesign/basic/src/basic.r0m"
DEFAULT_ORG = 0x0100        # стаб грузится по .rom-соглашению
DEFAULT_ENTRY = 0x19CC      # reset-вектор -> JMP сюда; первый вход = после распаковки
DEFAULT_LO = 0x0000         # база распакованного образа
DEFAULT_HI = 0x42FF         # конец образа (с 0x4300 — пустая программная область)
READ_CHUNK = 0x4000         # потолок debug_read_memory_range = 16384


def read_range(session, lo, hi):
    """Считать RAM [lo..hi] по чанкам; вернуть bytearray длины hi-lo+1."""
    out = bytearray()
    addr = lo
    while addr <= hi:
        n = min(READ_CHUNK, hi - addr + 1)
        payload = session.call("debug_read_memory_range",
                               {"address": addr, "length": n})
        data = bytes_of(payload)
        if len(data) != n:
            raise RuntimeError("read 0x%04X: ожидал %d байт, получил %d"
                               % (addr, n, len(data)))
        out += data
        addr += n
    return out


def wait_for_entry(session, entry, timeout=15.0):
    """Дожидаться, пока PC станет равен точке входа распакованного образа."""
    want = to_addr(entry)
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = session.call("debug_get_state") or {}
        cpu = state.get("cpu") or {}
        if to_addr(cpu.get("pc")) == want and not state.get("running", True):
            return cpu
        time.sleep(0.05)
    raise RuntimeError("таймаут: CPU не остановился на 0x%04X (точка не сработала)"
                       % want)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="dump_interp",
        description="Выгрузить распакованный интерпретатор из RAM в basic.r0m")
    parser.add_argument("--rom", default=DEFAULT_ROM)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=DEFAULT_ORG)
    parser.add_argument("--entry", type=lambda s: int(s, 0), default=DEFAULT_ENTRY,
                        help="адрес первой остановки после распаковки (reset->JMP)")
    parser.add_argument("--lo", type=lambda s: int(s, 0), default=DEFAULT_LO)
    parser.add_argument("--hi", type=lambda s: int(s, 0), default=DEFAULT_HI)
    parser.add_argument("--server", default=None)
    args = parser.parse_args(argv)

    rom = os.path.abspath(args.rom)
    if not os.path.isfile(rom):
        print("ERROR: ROM not found: %s" % rom, file=sys.stderr)
        return 3
    out = os.path.abspath(args.out)

    session, _cache = open_session(rom=rom, org=args.org, server=args.server,
                                   cache=False)
    try:
        # Канонический старт — только debug_load_rom (уже сделан open_session).
        # Точка останова на entry: ловим момент сразу после распаковки.
        session.call("debug_set_breakpoint", {"address": args.entry})
        session.call("debug_run")
        cpu = wait_for_entry(session, args.entry)

        image = read_range(session, args.lo, args.hi)
        session.call("debug_remove_breakpoint", {"address": args.entry})

        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(bytes(image))

        size = args.hi - args.lo + 1
        print("=== %s ===" % out)
        print("база 0x%04X..0x%04X (%d байт), entry 0x%04X, SP=%s"
              % (args.lo, args.hi, size, args.entry, cpu.get("sp")))
        # Контроль: первые байты — reset-вектор распакованного образа.
        head = " ".join("%02X" % b for b in image[:6])
        print("head @0x%04X: %s (ожидаем 31 FF 7F C3 CC 19)" % (args.lo, head))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
