#!/usr/bin/env python3
# Компоновщик putup_new.rom (проект roms/games/putup) — СВОБОДНАЯ КОНКАТАЕНАЦИЯ.
#
# Stage-4: отказ от адресной модели фиксированного оригинала. Файлы идут ПОДРЯД
# в порядке tools/order.json; единственный закреплённый адрес — точка входа
# (func_entry на org 0x0100). Гэпов нет: никаких `defs ADDR - $`-якорей, new_addr,
# COMPACT, HOLES/DELTA, GROWTH, POINTER_SITES, TEXTBUF_BASE_RELOC, DEAD-zeroing.
# Мёртвый шлак (распаковщики/пакеты/legacy-blit) физически ИСКЛЮЧЁН из образа.
#
# Все межфайловые ссылки символьны (Step 3A + Stage-4A: таблица глифов через
# `LXI H, data_glyph_ptr_table`; палитра через метку data_palette; значения
# таблицы — `DEFW data_glyph_block+N`), поэтому конкатенация сохраняет семантику:
# ассемблер раскладывает подряд, а реальные адреса меток даёт .sym
# (tools/mk_manifest.py -> tools/layout.json для поведенческих гейтов).
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASM  = os.path.join(ROOT, "asm")
REF  = os.path.join(ROOT, "..", "..", "redesign", "putup", "src")
RDB  = os.path.join(REF, "putup.rdb")
ORG  = 0x0100
CODE_END = 0x4600          # конец оригинальной кодовой зоны (отсечение emit-скана)

GLYPH_REL = "data/data_glyph_block_unpacked.asm"

addr_re = re.compile(r"Адрес:\s*0x([0-9A-Fa-f]{1,4})")

# Мёртвый шлак: распаковщики/пакеты/legacy-blit-движок — НЕ эмитятся.
# Доказательства мёртвости: 0 живых CALL/xref, unreachable в CFG от reset,
# адрес не встречается как значение, векторы (0x0015/0x000C) никто живой не пишет.
DEAD = {
    "func_blit_object_tile", "func_call_vector_053B",
    "func_blit_plane_mask10", "func_blit_plane_mask20",
    "func_blit_plane_mask40", "func_blit_plane_mask80",
    "func_load_gfx_2761", "data_gfx_2761", "data_packed_font_3041",
}

rdb = json.load(open(RDB, encoding="utf-8"))
rdb_addr = {o["name"]: int(o["address"], 16) for o in rdb["objects"]}

# --- скан emit-файлов кодовой зоны (funcs/ + data/ с «Адрес:») --------------
cands = []                                   # (addr, name, rel)
name2rel = {}
for sub in ("funcs", "data"):
    d = os.path.join(ASM, sub)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".asm"):
            continue
        nm = fn[:-4]
        rel = "%s/%s" % (sub, fn)
        head = "\n".join(open(os.path.join(d, fn), encoding="utf-8").read().splitlines()[:12])
        a = addr_re.search(head)
        if not a:
            continue                          # RAM/EQU-обвязка, не emit-слот
        addr = rdb_addr.get(nm, int(a.group(1), 16))
        if not (ORG <= addr < CODE_END):
            continue                          # напр. блок глифов @0x6000 — эмитится отдельно
        if nm in DEAD:
            continue                          # физически удалён из образа
        cands.append((addr, nm, rel))
        name2rel[nm] = rel

# --- порядок эмиссии: tools/order.json (источник истины) или адресный --------
order_path = os.path.join(ROOT, "tools", "order.json")
addr_order = [nm for _a, nm, _r in sorted(cands, key=lambda c: (c[0], c[1] != "data_level_maps"))]
if os.path.exists(order_path):
    order = json.load(open(order_path, encoding="utf-8"))
    # докинуть неучтённые живые файлы (устойчивость к добавлению emit-ов)
    known = set(order)
    for nm in addr_order:
        if nm not in known:
            order.append(nm)
            print("  order.json: добавлен неучтённый emit:", nm)
else:
    order = list(addr_order)
    json.dump(order, open(order_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  создан tools/order.json (порядок по умолчанию = адресный):", len(order), "файлов")

# компоненты карт эмитятся обёрткой data_level_maps — исключить дубли меток
order = [nm for nm in order if not re.match(r"data_level_\d+$", nm)]

# --- мастер asm --------------------------------------------------------------
lines = []
lines.append("; putup_new.rom (games/putup) — СВОБОДНАЯ КОНКАТАЕНАЦИЯ (Stage-4)")
lines.append("; ГЕНЕТОР tools/gen_layout.py — не править руками.")
lines.append("; Порядок: tools/order.json. Закреплён только вход (0x0100). Гэпов нет.")
lines.append("; Блок глифов — вплотную за кодом; адрес меток — из .sym (tools/layout.json).")
lines.append("")
lines.append("    org 0h")
lines.append('    include "var_ram_symbols.asm"')
lines.append("")
lines.append("    defs 0x0100 - $ ; точка входа")
for nm in order:
    lines.append('    include "%s"' % name2rel[nm])
# data_glyph_block обязан быть ЧЁТНЫМ: Tier-2 занимает бит0 слова указателя в
# data_glyph_ptr_table как ТЕГ компактности (offset+1 = compact). При нечётной базе
# каждый DEFW data_glyph_block+N теряет инвариант -> все глифы читаются как compact
# и адрес записи съезжает на 1 (compare_color ловит полный мусор). 1 байт padding.
lines.append("    defs $ & 1 ; выровнять блок глифов на чётный (бит0 = тег compactness)")
lines.append('    include "%s"   ; блок глифов' % GLYPH_REL)
lines.append("")
open(os.path.join(ASM, "putup_new.asm"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

print("emit-файлов в порядке: %d (+ обёртка карт, + блок глифов)" % len(order))
print("gaps: 0 (свободная конкатенация)")
