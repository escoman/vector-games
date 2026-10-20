#!/usr/bin/env python3
# Пост-сборочный манифест адресов (Stage-4C).
#
# Свободная конкатенация не сохраняет адреса оригинала, поэтому поведенческие
# гейты (compare_color/compare_behavior) и линт больше НЕ могут хардкодить
# 0x03A4 (ISR) / 0x08A3 (палитра) / адрес блока глифов. Источник истины адреса —
# ассемблер: `-s` пишет asm/putup_new.sym (`label = $ADDR ; ...`). Этот скрипт
# снимает нужные метки в tools/layout.json, который читают гейты.
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYM  = os.path.join(ROOT, "asm", "putup_new.sym")
OUT  = os.path.join(ROOT, "tools", "layout.json")
GLYPH_ASM = os.path.join(ROOT, "asm", "data", "data_glyph_block_unpacked.asm")

if not os.path.exists(SYM):
    raise SystemExit("нет %s — соберите сначала (make all)" % SYM)

sym_re = re.compile(r"^(\w+)\s*=\s*\$([0-9A-Fa-f]+)")
labels = {}
for ln in open(SYM, encoding="utf-8"):
    m = sym_re.match(ln.strip())
    if m:
        labels[m.group(1)] = int(m.group(2), 16)


def glyph_defb_count():
    t = open(GLYPH_ASM, encoding="utf-8").read()
    n = 0
    for ln in t.splitlines():
        m = re.match(r"\s*DEFB\s+(.+)", ln, re.I)
        if m:
            n += len([x for x in m.group(1).split(";")[0].split(",") if x.strip()])
    return n


# ключевые метки, нужные гейтам/линту
KEYS = ["func_entry", "func_vblank_isr", "data_palette",
        "data_glyph_ptr_table", "data_glyph_block", "data_text_buffer"]
layout = {k: labels.get(k) for k in KEYS}
missing = [k for k in KEYS if layout.get(k) is None]
if missing:
    raise SystemExit("в .sym нет ключевых меток: %s" % missing)

layout["glyph_base"] = labels["data_glyph_block"]
layout["glyph_size"] = glyph_defb_count()
layout["symbols"] = labels
json.dump(layout, open(OUT, "w", encoding="utf-8"), indent=1)
print("layout.json: " + ", ".join("%s=0x%04X" % (k, layout[k]) for k in KEYS))
