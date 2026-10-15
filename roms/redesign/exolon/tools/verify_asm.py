#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8: побайтовая сверка asm/<name>.asm ↔ exolon.rom.

Разбирает директивы DEFB/DEFW/DEFM/INCBIN (символьные DEFW data_enemy_patterns+N
резолвятся от базы 0x2429), реконструирует байты и сравнивает с ROM-срезом по
адресу из заголовка. Выход 0 — все объекты байт-в-байт совпали.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROM_DIR = os.path.dirname(HERE)
SRC = os.path.join(ROM_DIR, "src")
ASM = os.path.join(ROM_DIR, "asm")
ORG = 0x0100
ENEMY_BASE = 0x2429

rom = open(os.path.join(SRC, "exolon.rom"), "rb").read()

def rb(a, n):
    return rom[a - ORG:a - ORG + n]

def parse_hex(tok):
    return int(tok, 16) if tok.lower().startswith("0x") else int(tok)

def expand_defw(arg):
    arg = arg.strip()
    m = re.match(r"^data_enemy_patterns\s*\+\s*(0x[0-9A-Fa-f]+|\d+)$", arg)
    if m:
        return (ENEMY_BASE + parse_hex(m.group(1))) & 0xFFFF
    if arg.lower().startswith("0x") or arg.isdigit():
        return parse_hex(arg)
    raise ValueError("неизвестный DEFW-операнд: %r" % arg)

def parse_asm(path):
    txt = open(path, encoding="utf-8").read()
    addr = int(re.search(r";\s*Адрес:\s*(0x[0-9A-Fa-f]+)", txt).group(1), 16)
    size = int(re.search(r";\s*Размер:\s*(\d+)\s*байт", txt).group(1))
    out = bytearray()
    for raw in txt.splitlines():
        line = raw.split(";", 1)[0].rstrip()
        if not line.strip():
            continue
        d = line.strip()
        if d.upper().startswith("DEFB"):
            for tok in d[4:].split(","):
                tok = tok.strip()
                if tok:
                    out.append(parse_hex(tok) & 0xFF)
        elif d.upper().startswith("DEFW"):
            w = expand_defw(d[4:])
            out += bytes([w & 0xFF, (w >> 8) & 0xFF])
        elif d.upper().startswith("DEFM"):
            s = re.match(r'DEFM\s+"(.*)"$', d, re.I).group(1)
            s = s.replace('\\"', '"').replace("\\\\", "\\")
            out += s.encode("ascii")
        elif d.upper().startswith("INCBIN"):
            fn = re.match(r'INCBIN\s+"(.*)"$', d, re.I).group(1)
            out += open(os.path.join(ASM, fn), "rb").read()
    return addr, size, bytes(out)

def main():
    files = sorted(f for f in os.listdir(ASM) if f.endswith(".asm")
                   and f not in ("var_ram_symbols.asm", "exolon_data_index.asm"))
    bad = 0
    for f in files:
        addr, size, got = parse_asm(os.path.join(ASM, f))
        want = rb(addr, size)
        ok = got == want
        if not ok:
            bad += 1
            print(f"  МИССМЕТЧ {f}: declared={size} got={len(got)} "
                  f"@0x{addr:04X}")
            for i in range(min(len(got), len(want))):
                if got[i] != want[i]:
                    print(f"    first diff @0x{addr+i:04X}: got {got[i]:02X} "
                          f"want {want[i]:02X}")
                    break
    print(f"Сверено файлов: {len(files)}, рассогласований: {bad}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
