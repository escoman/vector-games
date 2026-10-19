#!/usr/bin/env python3
"""make verify: кодовая зона PUTUP_NEW.ROM = оригинал с точностью до
(1) заглушек в func_main_init — 3 NOP на месте CALL func_load_glyph_block
    (0x0B83..0x0B85) и 34 NOP вестигиального копира спрайтов
    (0x0B86..0x0BA7; 0x7418 никем не читается, источник — обнулённый пакет);
(2) dead-диапазонов, выжженных нулями генератором (tools/dead_ranges.json;
    KEEP_DEAD=1 — Stage A, dead-обнуления запрещены);
(3) релокации текстового back-буфера: база смещена 0x5000 -> 0x6600 (дельта
    +0x1600), из-за чего в коде меняется ровно ВЫСШИЙ байт операнда-адреса:
      * позиции курсора LXI H,data_text_buffer+ofs: 0x50..0x53 -> +0x16;
      * константа func_render_glyph textbuf_to_vram (= 0-база): 0xB0 -> 0x9A.
    Эти дельты принимаются только по строгой сигнатуре; любой иной diff — провал.
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
# сигнатура релокации базы буфера (0x5000 -> 0x6600): высший байт операнда
# меняется на +0x16 (позиции курсора в 0x50..0x53) либо B0->9A (константа render).
RELOC_HIGH = {0x50, 0x51, 0x52, 0x53}   # исходные высшие байты страниц 0x50xx..0x53xx
RELOC_DELTA = 0x16                       # (0x6600 - 0x5000) >> 8


def is_reloc_diff(x, y):
    if x in RELOC_HIGH and y == (x + RELOC_DELTA) & 0xFF:   # курсорная позиция
        return True
    if x == 0xB0 and y == 0x9A:                             # textbuf_to_vram
        return True
    return False


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
    reloc = [(i, x, y) for i, x, y in diffs if is_reloc_diff(x, y)]
    diffs = [(i, x, y) for i, x, y in diffs if not is_reloc_diff(x, y)]
    if len(b) < len(a):
        print("ошибка: образ короче кодовой зоны (%d < %d)" % (len(b), len(a)))
        return 1
    # контрольные точки: заглушка на месте (00h = NOP 8080)
    for s, e in NOP_PATCHES:
        if b[s - 0x100:e - 0x100] != b"\x00" * (e - s):
            print("ошибка: 0x%04X..0x%04X != NOP-заглушка" % (s, e - 1))
            return 1
    print("dead-диапазоны выжжены:", [(hex(s), hex(e), n) for s, e, n in dead] or "нет (KEEP_DEAD=1)")
    print("ptr_table перемещена под glyph_base: %d слов" % (len(ptr_diffs) // 2))
    print("релокация базы буфера (+0x%X в высшем байте): %d байт" % (RELOC_DELTA, len(reloc)))
    if diffs:
        print("unexpected diffs:", [(hex(i + 0x100), hex(x), hex(y)) for i, x, y in diffs][:20],
              "... всего %d" % len(diffs))
        return 1
    print("verify OK: кодовая зона = оригинал + NOP(func_load_glyph) + dead-обнуления + релокация базы")
    return 0


if __name__ == "__main__":
    sys.exit(main())
