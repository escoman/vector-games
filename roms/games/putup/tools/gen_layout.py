#!/usr/bin/env python3
# Компоновщик PUTUP_NEW.ROM (проект roms/games/putup): адресно-точная
# реконструкция оригинала src/putup.rom (../../redesign/putup/src, 0x0100..0x45FF)
# + РАСПАКОВАННЫЙ блок глифов по адресу GLYPH_BASE.
#
# Отличия от redesign-генератора Stage 12:
#   * к образ додаётся data_glyph_block_unpacked (8192 Б, снимок пост-иниц RAM
#     0x6000..0x7FFF, снят вербатим через MCP) — на этапе A по историческому
#     адресу распаковки GLYPH_BASE=0x6000;
#   * адрес блока — единственная константа макета; итог Фазы 1 — 0x4600:
#     текстовый back-буфер перенесён с 0x5000 на 0x6600 (EQU data_text_buffer
#     в var_ram_symbols.asm), поэтому дыра 0x4600..0x55FF схлопнута и блок
#     встаёт вплотную к концу кода (CODE_END);
#   * filler CODE_END..GLYPH_BASE (нули) остаётся только при GLYPH_BASE>CODE_END;
#     в Фазе 1 GLYPH_BASE==CODE_END, дыры нет — блок идёт вплотную за кодом.
#
# Gap-байты кодовой зоны берутся ВЛОБ из оригинала (это данные, не дизассемблер).
# MCP-выводы не обрабатываются.
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASM  = os.path.join(ROOT, "asm")
REF  = os.path.join(ROOT, "..", "..", "redesign", "putup", "src")
ROM  = os.path.join(REF, "putup.rom")
RDB  = os.path.join(REF, "putup.rdb")
ORG  = 0x0100
SIZE = 17664
CODE_END = ORG + SIZE          # 0x4600 — конец оригинального образа
GLYPH_BASE = int(os.environ.get("GLYPH_BASE", "0x4600"), 0)   # переносится константой (Фаза 1)
GLYPH_SIZE = 8192                                          # 256 глифов x 32 Б
GLYPH_ASM  = "data_glyph_block_unpacked.asm"   # снимок — побайтовые DEFB в asm
IMG_END = GLYPH_BASE + GLYPH_SIZE
# этап B: мёртвые распаковщики/пакеты выводятся из сборки (их диапазоны — нули).
# KEEP_DEAD=1 возвращает Stage-A раскладку (всё на исторических адресах).
KEEP_DEAD = os.environ.get("KEEP_DEAD", "0") != "0"
DEAD = {"func_load_glyph_block", "func_load_gfx_2761",
        "data_packed_font_3041", "data_gfx_2761"}

rom = open(ROM, "rb").read()
assert len(rom) == SIZE

rdb = json.load(open(RDB, encoding="utf-8"))
rdb_addr = {o["name"]: int(o["address"], 16) for o in rdb["objects"]}
szp = os.path.join(ROOT, "tools", "sizes.json")
real_sz = json.load(open(szp)) if os.path.exists(szp) else {}  # замеренные длины эмиссии

addr_re = re.compile(r"Адрес:\s*0x([0-9A-Fa-f]{1,4})")
size_re = re.compile(r"Размер:\s*(\d+)")

def has_instructions(txt):
    return bool(re.search(r'^\s*(?!DEFB|DEFW|DEFS|INCBIN|ORG\b)[A-Z][A-Z0-9]+\s', txt, re.M))


def defb_bytes(txt):
    """Суммарное число аргументов DEFB/DEFW-строк побайтовых данных."""
    n = 0
    for ln in txt.splitlines():
        m = re.match(r"\s*DEFB\s+(.+)", ln, re.I)
        if m:
            n += len([t for t in m.group(1).split(";")[0].split(",") if t.strip()])
    return n


def file_bytesize(path, declared):
    """Инструкциям верим замером (sizes.json выше); чистым данным — DEFB-счёт,
    затем заголовок «Размер:»; INCBIN — размер .bin (наследие этапа A)."""
    txt = open(path, encoding="utf-8").read()
    bins = re.findall(r'^\s*INCBIN\s+"([^"]+)"', txt, re.M)
    if bins and not re.search(r'^\s*DEF', txt, re.M):
        return sum(os.path.getsize(os.path.join(ASM, b)) for b in bins)
    if not has_instructions(txt) and re.search(r'^\s*DEF', txt, re.M):
        return defb_bytes(txt) or declared
    return declared

# собираем emit-файлы кодовой зоны; dead-диапазоны — под обнуление (этап B).
# код в asm/funcs/, данные в asm/data/ — rel включает подкаталог, nm нет
emit = {}
dead_ranges = []
for sub in ("funcs", "data"):
  for fn in sorted(os.listdir(os.path.join(ASM, sub))):
    if not fn.endswith(".asm"):
        continue
    rel = "%s/%s" % (sub, fn)
    path = os.path.join(ASM, rel)
    head = "\n".join(open(path, encoding="utf-8").read().splitlines()[:12])
    a = addr_re.search(head)
    if not a:
        print("  no addr:", fn, "-> skipped (RAM/EQU)"); continue
    s = size_re.search(head)
    declared = int(s.group(1)) if s else -1
    addr = int(a.group(1), 16)
    addr = rdb_addr.get(fn[:-4], addr)  # канонический адрес — из RDB
    if not (ORG <= addr < CODE_END):
        print("  out of code zone:", fn, hex(addr)); continue
    nm = fn[:-4]
    sz = real_sz.get(nm) or (declared if nm == "data_level_maps"
                             else file_bytesize(path, declared))
    if not KEEP_DEAD and nm in DEAD:
        dead_ranges.append((addr, addr + sz, nm))
        print("  dead-out (zeroed):", nm, "0x%04X..0x%04X" % (addr, addr + sz - 1))
        continue
    emit[nm] = (addr, sz, rel)

# сортировка + отброс перекрытий (вложенные дубликаты адресов).
# data_level_maps — include-обёртка карт: эмитится ОДИН слот (алиас базы +
# все 15 include-ов), компоненты data_level_NN из мастера пропускаются,
# иначе метки определились бы дважды
items = sorted(((nm, v[0], v[1], v[2]) for nm, v in emit.items()),
               key=lambda it: (it[1], it[0] != "data_level_maps"))
kept, cov = [], ORG
for name, a, sz, rel in items:
    if kept and kept[-1][0] == "data_level_maps" and re.match(r"data_level_\d+", name):
        print("  wrapper-component (уже в data_level_maps):", name, hex(a)); continue
    if a < cov:
        print("  overlap-skipped (dup):", name, hex(a)); continue
    kept.append((name, a, sz, rel))
    cov = a + sz

# этап B: dead-диапазоны — ровно измеренные слоты (real_sz/DEFB-счёт), без
# расширения: в slack-хвостах гэпов живут инициализированные RAM-переменные
# (var_music_tick@0x383A), их трогать нельзя.

# сегменты: emit-слоты + gap-дополнения кодовой зоны
segs = []
cur = ORG
for name, a, sz, rel in kept:
    if a > cur:
        segs.append(("gap", cur, a - cur))
    segs.append(("emit", a, sz, name, rel))
    cur = a + sz
if cur < CODE_END:
    segs.append(("gap", cur, CODE_END - cur))

assert GLYPH_BASE + GLYPH_SIZE <= 0x8000, "не влезает в нижние 32КБ"
assert GLYPH_BASE >= CODE_END, "блок не должен наезжать на код"

glyph_txt = open(os.path.join(ASM, "data", GLYPH_ASM), encoding="utf-8").read()
assert "DEFB" in glyph_txt, ("нет снимка глиф-блока в %s — сначала tools/get_glyph_block" % GLYPH_ASM)
assert defb_bytes(glyph_txt) == GLYPH_SIZE, "DEFB-снимок глиф-блока != 8192 Б"

lines = []
lines.append("; PUTUP_NEW.ROM (games/putup) — putup с РАСПАКОВАННЫМИ данными")
lines.append("; ГЕНЕРАТОР tools/gen_layout.py — не править руками.")
lines.append("; 0x0100..0x45FF: все объекты на ИСХОДНЫХ адресах, гэпы — вербатим из putup.rom;")
lines.append("; 0x4600..0x%X: нули (в оригинале — RAM);" % (GLYPH_BASE - 1))
lines.append("; 0x%X..0x%X: data_glyph_block_unpacked (%d Б, снимок пост-иниц 0x6000..0x7FFF)."
             % (GLYPH_BASE, IMG_END - 1, GLYPH_SIZE))
lines.append("")
lines.append("    org 0h")
lines.append('    include "var_ram_symbols.asm"')
lines.append("")
gapcount = gapbytes = 0
for seg in segs:
    if seg[0] == "emit":
        _, a, sz, name, rel = seg
        lines.append("; --- emit %s @0x%04X (%d bytes) ---" % (name, a, sz))
        lines.append("    defs 0x%04X - $ ; align" % a)
        lines.append('    include "%s"' % rel)
        lines.append("")
    else:
        _, a, sz = seg
        chunk = bytearray(rom[a - ORG : a - ORG + sz])
        # этап B: мёртвые диапазоны внутри гэпов выжигаем нулями
        for ds, de, _nm in dead_ranges:
            lo, hi = max(a, ds), min(a + sz, de)
            if lo < hi:
                chunk[lo - a : hi - a] = b"\x00" * (hi - lo)
        gapcount += 1; gapbytes += sz
        lines.append("; --- gap 0x%04X..0x%04X (%d bytes) from original image ---" % (a, a + sz, sz))
        lines.append("    defs 0x%04X - $ ; align" % a)
        for i in range(0, len(chunk), 8):
            octet = chunk[i:i + 8]
            body = ", ".join("0%Xh" % b for b in octet)   # 0C1h: ведущий 0 обязателен
            cmt = "   ; 0x%04X" % (a + i) if i == 0 else ""
            lines.append("    DEFB %s%s" % (body, cmt))
        lines.append("")

# дыра между концом кода и блоком — нули (эмулятор при старте держит её чистой RAM)
if GLYPH_BASE > CODE_END:
    lines.append("; --- filler 0x%04X..0x%04X (%d bytes) zeros (RAM в оригинале) ---"
                 % (CODE_END, GLYPH_BASE - 1, GLYPH_BASE - CODE_END))
    lines.append("    defs 0x%04X - $ ; align" % GLYPH_BASE)
    lines.append("")

lines.append("; --- unpacked glyph block @0x%04X (%d bytes) ---" % (GLYPH_BASE, GLYPH_SIZE))
lines.append('    include "data/%s"' % GLYPH_ASM)
lines.append("")
lines.append("; image end @0x%04X" % IMG_END)
open(os.path.join(ASM, "putup_unpacked.asm"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

# список разрешённых расхождений с оригиналом для make verify
import json as _json
rep = os.path.join(ROOT, "tools")           # состояние инструментов сборки
os.makedirs(rep, exist_ok=True)
ptr = emit.get("data_glyph_ptr_table")
with open(os.path.join(rep, "dead_ranges.json"), "w", encoding="utf-8") as f:
    _json.dump({"dead_ranges": [[s, e, n] for s, e, n in dead_ranges],
                "glyph_base": GLYPH_BASE,
                "ptr_table": [ptr[0], ptr[0] + 512] if ptr else None}, f)

emitbytes = sum(k[2] for k in kept)
imgsize = IMG_END - ORG
print("kept emit files: %d (%d bytes)" % (len(kept), emitbytes))
print("gaps: %d (%d bytes) -> inline DEFB в мастере" % (gapcount, gapbytes))
print("glyph block @0x%X..0x%X" % (GLYPH_BASE, IMG_END - 1))
print("image: %d bytes (0x%X..0x%X)" % (imgsize, ORG, IMG_END - 1))
