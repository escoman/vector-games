#!/usr/bin/env python3
"""Калибровка раскладки по байтам буфера ввода 0x3F77 (точнее, чем OCR).

Для каждого ключа набираем его в трёх слоях (без модификатора / SS / US),
читаем байт в 0x3F77 и печатаем код+символ. В конце — карта: какой ключ и
модификатор дают нужный ASCII (0x2B '+', 0x2A '*', 0x26 '&', 0x28 '(', ...).
"""
from __future__ import annotations
import os, time
from analyze.mcp_session import bytes_of, open_session

BASIC = "/home/alexey/Projects/vector-games/roms/redesign/basic"
NEW = os.path.join(BASIC, "src", "basic_new.r0m")
BUF = 0x3F77

session, _ = open_session(rom=NEW, org=0x0000, cache=False)
try:
    session.load_rom(NEW, org=0x0000)
    session.call("debug_run"); time.sleep(3.0)
    def tap(k): session.call("debug_type_key", {"key": k}); time.sleep(0.16)
    def press(k): session.call("debug_press_key", {"key": k}); time.sleep(0.06)
    def release(k): session.call("debug_release_key", {"key": k}); time.sleep(0.06)

    def first_byte():
        b = bytes_of(session.call("debug_read_memory_range",
                                  {"address": BUF, "length": 2}))
        return b[0]

    def probe(key, mod):
        # маркер-буква 'Z' потом кандидата -> читаем 2-й байт (0x3F78)
        tap("Z")
        if mod: press(mod)
        tap(key)
        if mod: release(mod)
        b = bytes_of(session.call("debug_read_memory_range",
                                  {"address": BUF + 1, "length": 1}))[0]
        # стереть набранное: два backspace
        tap("BACKSPACE"); tap("BACKSPACE")
        return b

    def show(ch):
        return chr(ch) if 32 <= ch < 127 else "\\x%02X" % ch

    keys = ["1","2","3","4","5","6","7","8","9","0",
            "MINUS","EQUALS","COMMA","PERIOD","SLASH","SEMICOLON",
            "APOSTROPHE","LBRACKET","RBRACKET","GRAVE","B","V","C"]
    print("key          none    SS      US")
    for k in keys:
        n = probe(k, None); s = probe(k, "SS"); u = probe(k, "US")
        print("%-11s  %02X'%s'  %02X'%s'  %02X'%s'"
              % (k, n, show(n), s, show(s), u, show(u)))
finally:
    session.close()
