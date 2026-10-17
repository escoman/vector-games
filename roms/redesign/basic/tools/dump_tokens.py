#!/usr/bin/env python3
"""Stage 5: декодировать таблицу ключевых слов basic.r0m -> токен <-> слово.

Таблица слов `data_keyword_table` = 0x256E..0x26D6 (101 слово, кодировка
«байт на символ, bit7 = конец слова»), токен = 0x80 + номер слова. Печатает
карту для `tools/tokens.md`; при расхождении с Basic_Vector-06C.pdf авторитет —
образ ROM.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/dump_tokens.py
"""
import os
import sys

from analyze.mcp_session import addr_hex, bytes_of, open_session

ROM = os.path.join(os.path.dirname(__file__), "..", "src", "basic.r0m")
KEYWORD_TABLE = 0x256E
KEYWORD_END = 0x26D7
KEYWORD_COUNT = 101
TOKEN_BASE = 0x80


def decode(data):
    words, pos = [], 0
    for _ in range(KEYWORD_COUNT):
        chunk = bytearray()
        while True:
            b = data[pos]
            chunk.append(b & 0x7F)
            pos += 1
            if b & 0x80:
                break
        words.append(chunk.decode("latin-1"))
    return words


def main():
    session, _cache = open_session(rom=ROM, org=0x0000)
    try:
        data = bytes_of(session.call("debug_read_memory_range", {
            "address": KEYWORD_TABLE, "length": KEYWORD_END - KEYWORD_TABLE}))
    finally:
        session.close()
    for i, word in enumerate(decode(data)):
        print("%s  %3d  %s" % (addr_hex(TOKEN_BASE + i), i, word))
    return 0


if __name__ == "__main__":
    sys.exit(main())
