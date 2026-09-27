#!/usr/bin/env python3
"""Extract per-opcode v_cycles from the vector-psp emulator source.

Usage: ./extract_vcycles.py > vcycles.json
"""
import json
import re
import sys

SRC = "/home/alexey/Projects/vector-psp/src/i8080.cpp"

case_re = re.compile(r"case\s+0x([0-9A-Fa-f]{2})\s*:")
vc_re = re.compile(r"v_cycles\s*=\s*(\d+)\s*;")


def main():
    table = {}
    stack = []      # consecutive case labels awaiting a shared body
    with open(SRC) as f:
        for line in f:
            m = case_re.search(line)
            if m:
                stack.append(int(m.group(1), 16))
                continue
            m = vc_re.search(line)
            if m and stack:
                for op in stack:
                    table.setdefault(op, int(m.group(1)))
                stack = []
    json.dump({hex(k): v for k, v in sorted(table.items())}, sys.stdout, indent=0)


if __name__ == "__main__":
    main()
