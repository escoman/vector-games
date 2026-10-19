#!/usr/bin/env python3
"""make verify: кодовая зона PUTUP_NEW.ROM = оригинал с точностью до
заглушек в func_main_init — 3 NOP на месте CALL func_load_glyph_block
(0x0B83..0x0B85) и 34 NOP выжженного копира спрайтов (0x0B86..0x0BA7) —
и dead-диапазонов, выжженных нулями генератором (tools/dead_ranges.json;
KEEP_DEAD=1 — Stage A, dead-обнуления запрещены).
"""
import json
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(PROJ))),
                   "roms", "redesign", "putup", "src")   # оригиналы putup.rom/rdb
# узаконенные заглушки внутри func_main_init (метки патчей, НЕ dead-диапазоны)
NOP_PATCHES = [(0x0B83, 0x0B86), (0x0B86, 0x0BA8)]
NOP = {a for s, e in NOP_PATCHES for a in range(s - 0x100, e - 0x100)}


def main():
    keep_dead = os.environ.get("KEEP_DEAD", "0") != "0"
    a = open(os.path.join(REF, "putup.rom"), "rb").read()
    b = open(os.path.join(PROJ, "PUTUP_NEW.ROM"), "rb").read()[:len(a)]
    allow = set(NOP)
    dr_path = os.path.join(PROJ, "tools", "dead_ranges.json")
    dead, ptr_diffs = [], set()
    if not keep_dead and os.path.exists(dr_path):
        info = json.load(open(dr_path, encoding="utf-8"))
        dead = info["dead_ranges"]
        allow |= {i for s, e, _ in dead for i in range(s - 0x100, e - 0x100)}
        # таблица указателей: слово N обязано быть = glyph_base + N*32
        gb, pt = info["glyph_base"], info["ptr_table"]
        if pt:
            for n in range(256):
                off = pt[0] - 0x100 + 2 * n
                want = (gb + n * 32) & 0xFFFF
                got = b[off] | (b[off + 1] << 8)
                if got == want:
                    ptr_diffs |= {off, off + 1}
    diffs = [(i, x, y) for i, (x, y) in enumerate(zip(a, b))
             if x != y and i not in allow and i not in ptr_diffs]
    if len(b) < len(a):
        print("ошибка: образ короче кодовой зоны (%d < %d)" % (len(b), len(a)))
        return 1
    # контрольные точки: обе заглушки действительно на месте (00h = NOP 8080)
    for s, e in NOP_PATCHES:
        if b[s - 0x100:e - 0x100] != b"\x00" * (e - s):
            print("ошибка: 0x%04X..0x%04X != NOP-заглушка" % (s, e - 1))
            return 1
    print("dead-диапазоны выжжены:", [(hex(s), hex(e), n) for s, e, n in dead] or "нет (KEEP_DEAD=1)")
    print("ptr_table перемещена под glyph_base: %d слов" % (len(ptr_diffs) // 2))
    if diffs:
        print("unexpected diffs:", [(hex(i + 0x100), hex(x), hex(y)) for i, x, y in diffs][:20],
              "... всего %d" % len(diffs))
        return 1
    print("verify OK: кодовая зона = оригинал + NOP-заглушки func_main_init + dead-обнуления")
    return 0


if __name__ == "__main__":
    sys.exit(main())
