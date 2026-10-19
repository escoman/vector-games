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

# --- Фаза 2: компакция мёртвых дыр (relocation-модель) ----------------------
# COMPACT=1 исключает две мёртвые data-дыры из образа и сдвигает верхнюю
# половину вверх (new_addr), понижая GLYPH_BASE. COMPACT=0 — verbatim-режим
# Фазы 1 (полная побайтовая реконструкция) для регрессии.
COMPACT = os.environ.get("COMPACT", "0") != "0"
HOLES = [(0x2761, 0x2F61), (0x3041, 0x383A)]   # data_gfx_2761(2048), data_packed_font_3041(2041)
DELTA1 = HOLES[0][1] - HOLES[0][0]             # 2048
DELTA2 = HOLES[1][1] - HOLES[1][0]             # 2041
TOTAL_DELTA = DELTA1 + DELTA2                  # 4089

def new_addr(a):
    """Оригинальный адрес -> адрес в компактном образе (дыры вырезаны)."""
    if not COMPACT:
        return a
    if a < HOLES[0][0]:
        return a                       # нижняя кодовая зона — не трогаем (byte-exact)
    if a < HOLES[0][1]:
        return a                       # внутри дыры 1 — не эмится
    if a < HOLES[1][0]:
        return a - DELTA1              # между-дырный гэп (спрайты) — сдвиг −2048
    if a < HOLES[1][1]:
        return a                       # внутри дыры 2 — не эмится
    return a - TOTAL_DELTA             # весь код/данные после дыры 2 — сдвиг −4089

# relocate-якоря: RAM-символы, чьи инициализированные значения лежат в
# перемещаемой зоне (>=0x2761). Имена больше не EQU-литералы в var_ram_symbols;
# компоновщик пишет asm/var_reloc_anchors.asm со значением new_addr(оригинал).
ANCHORS = {
    "var_music_tick":          0x383A,
    "var_music_ptr_01":        0x383B,
    "var_music_ptr_02":        0x383C,
    "var_music_ptr_03":        0x383D,
    "var_music_stream_base_01": 0x383F,
    "var_music_stream_base_02": 0x3841,
    "var_music_stream_base_03": 0x3843,
    "data_voice_param_buf":    0x3845,
    "data_voice_param_buf_end": 0x3853,
    "var_music_track_ptr":     0x3854,
    "var_music_track_base":    0x3856,
    "var_music_voice2_flag":   0x3BC8,
    "var_music_voice2_flag_hi": 0x3BC9,
}
# Встроенные 16-бит УКАЗАТЕЛИ в инициализированных RAM-значениях (var-init блок
# 0x383A..0x3857): содержат базы потоков нот, указывающие в перемещаемые data-
# таблицы. Их содержимое надо переписать через new_addr. Это ЕДИНСТВЕННЫЕ
# abs-поинтеры в verbatim-данных;Interior нотных/периодных таблиц — значения
# (периоды), НЕ патчится (иначе испортим музыку).
POINTER_SITES = (0x383F, 0x3841, 0x3843, 0x3854, 0x3856)

# compact: перемещённый код кончается на new_addr(0x4600)=0x3607 -> блок от 0x3608.
GLYPH_BASE = int(os.environ.get("GLYPH_BASE", "0x3608" if COMPACT else "0x4600"), 0)
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

CODE_END_EFF = new_addr(CODE_END)   # compact: 0x35FF; verbatim: 0x4600
assert GLYPH_BASE + GLYPH_SIZE <= 0x8000, "не влезает в нижние 32КБ"
assert GLYPH_BASE >= CODE_END_EFF, "блок не должен наезжать на (перемещённый) код"
if COMPACT:
    # перемещённые RAM-скретч-якоря не должны попасть в read-only глиф-окно.
    for _nm, _oa in ANCHORS.items():
        _na = new_addr(_oa)
        assert _na < GLYPH_BASE or _na >= GLYPH_BASE + GLYPH_SIZE, \
            "RAM-якорь %s после reloc 0x%04X попал в глиф-окно" % (_nm, _na)
    # текстовый back-буфер (Фаза 1, 0x6600) — выше компактного блока, вне коллизии.
    assert not (GLYPH_BASE <= 0x6600 < GLYPH_BASE + GLYPH_SIZE), "data_text_buffer в глиф-окне"

glyph_txt = open(os.path.join(ASM, "data", GLYPH_ASM), encoding="utf-8").read()
assert "DEFB" in glyph_txt, ("нет снимка глиф-блока в %s — сначала tools/get_glyph_block" % GLYPH_ASM)
assert defb_bytes(glyph_txt) == GLYPH_SIZE, "DEFB-снимок глиф-блока != 8192 Б"

# --- asm-эмиттеры -----------------------------------------------------------
def clip_holes(a, b):
    """Подынтервалы [s,e) диапазона [a,b) за вычетом мёртвых дыр (только compact)."""
    if not COMPACT:
        yield a, b
        return
    cur = a
    for hs, he in sorted(HOLES):
        if he <= cur or hs >= b:
            continue
        if hs > cur:
            yield cur, hs
        cur = max(cur, he)
    if cur < b:
        yield cur, b

def emit_gap(s, e, out):
    """Гэп [s,e): байты влоб из оригинала, dead-поддиапазоны -> нули, встроенные
    указатели (POINTER_SITES) -> DW new_addr(содержимое). Размещение по new_addr(s)."""
    global gapcount, gapbytes
    chunk = bytearray(rom[s - ORG: e - ORG])
    for ds, de, _nm in dead_ranges:
        lo, hi = max(s, ds), min(e, de)
        if lo < hi:
            chunk[lo - s: hi - s] = b"\x00" * (hi - lo)
    na = new_addr(s)
    tag = (" @reloc 0x%04X" % na) if COMPACT else ""
    out.append("; --- gap 0x%04X..0x%04X (%d bytes) from original image%s ---" % (s, e, e - s, tag))
    out.append("    defs 0x%04X - $ ; align" % na)
    gapcount += 1; gapbytes += (e - s)
    i = s
    while i < e:
        if i in POINTER_SITES:
            content = rom[i - ORG] | (rom[i - ORG + 1] << 8)
            if content >= HOLES[0][0]:      # указатель в перемещаемую зону
                out.append("    DW 0%04Xh   ; reloc-указатель (orig 0x%04X -> 0x%04X)" %
                           (new_addr(content), i, content))
            else:                            # указатель в неизменную зону — как есть
                out.append("    DW 0%04Xh   ; abs-ptr (не reloc)" % content)
            i += 2
            continue
        run = []
        while i < e and i not in POINTER_SITES:
            run.append(chunk[i - s]); i += 1
        for j in range(0, len(run), 8):
            octet = run[j:j + 8]
            body = ", ".join("0%Xh" % b for b in octet)
            out.append("    DEFB %s" % body)

# relocate-якоря — генерируемый include (значение = new_addr(оригинал)).
anch_lines = ["; var_reloc_anchors.asm — ГЕНЕРИРУЕТСЯ tools/gen_layout.py, не править руками.",
              "; RAM-символы перемещаемой зоны: verbatim = исходный адрес, compact = new_addr.", ""]
for nm in sorted(ANCHORS, key=lambda k: ANCHORS[k]):
    anch_lines.append("%-24s EQU 0%04Xh" % (nm + ":", new_addr(ANCHORS[nm])))
open(os.path.join(ASM, "var_reloc_anchors.asm"), "w", encoding="utf-8").write("\n".join(anch_lines) + "\n")

lines = []
lines.append("; PUTUP_NEW.ROM (games/putup) — putup с РАСПАКОВАННЫМИ данными")
lines.append("; ГЕНЕРАТОР tools/gen_layout.py — не править руками.")
if COMPACT:
    lines.append("; РЕЖИМ COMPACT (Фаза 2): мёртвые дыры [0x2761,0x2F61)+[0x3041,0x383A) вырезаны;")
    lines.append("; объекты >=0x2761 сдвинуты вверх (new_addr, суммарный сдвиг -%d Б);" % TOTAL_DELTA)
    lines.append("; byte-exact сохранён только для [0x0100,0x2761); выше — поведенческая сверка.")
else:
    lines.append("; РЕЖИМ VERBATIM (Фаза 1): все объекты на ИСХОДНЫХ адресах, гэпы — вербатим из putup.rom;")
lines.append("; 0x%X..0x%X: data_glyph_block_unpacked (%d Б, снимок пост-иниц 0x6000..0x7FFF)."
             % (GLYPH_BASE, IMG_END - 1, GLYPH_SIZE))
lines.append("")
lines.append("    org 0h")
lines.append('    include "var_ram_symbols.asm"')
lines.append('    include "var_reloc_anchors.asm"')
lines.append("")
gapcount = gapbytes = 0
for seg in segs:
    if seg[0] == "emit":
        _, a, sz, name, rel = seg
        na = new_addr(a)
        tag = (" @reloc 0x%04X" % na) if COMPACT and na != a else ""
        lines.append("; --- emit %s @0x%04X (%d bytes)%s ---" % (name, a, sz, tag))
        lines.append("    defs 0x%04X - $ ; align" % na)
        lines.append('    include "%s"' % rel)
        lines.append("")
    else:
        _, a, sz = seg
        for cs, ce in clip_holes(a, a + sz):
            emit_gap(cs, ce, lines)

# дыра между концом кода и блоком — нули (эмулятор при старте держит её чистой RAM)
if GLYPH_BASE > CODE_END_EFF:
    lines.append("; --- filler 0x%04X..0x%04X (%d bytes) zeros (RAM в оригинале) ---"
                 % (CODE_END_EFF, GLYPH_BASE - 1, GLYPH_BASE - CODE_END_EFF))
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
                "ptr_table": [ptr[0], ptr[0] + 512] if ptr else None,
                # Фаза 2: relocate-метаданные для verify/lint (compact-режим).
                "compact": COMPACT,
                "byte_exact_end": HOLES[0][0],          # 0x2761 — ниже строго byte-exact
                "holes": [list(h) for h in HOLES],       # вырезанные дыры (ориг-адреса)
                "delta_total": TOTAL_DELTA,              # 4089 — суммарный сдвиг верха
                "code_end_orig": CODE_END,               # 0x4600
                "code_end_new": CODE_END_EFF,            # verbatim 0x4600 / compact 0x3607
                "pointer_sites": list(POINTER_SITES)},   # var-init embedded-указатели
              f)

# --- compact: RDB перемещённого образа (не мутируем исходный redesign/putup.rdb) ---
# Адреса объектов/ссылок >=0x2761 проходят через new_addr; объекты, целиком
# лежащие в вырезанной дыре, удаляются (их нет в компактном образе). Используется
# для disassembly/линтов компактного PUTUP_NEW.ROM. Компактный режим только.
if COMPACT:
    def _in_hole(x):
        return any(hs <= x < he for hs, he in HOLES)
    # Артефакты рантайм-RAM на/выше конца кодового образа (>= CODE_END) НЕ едут
    # по new_addr — компакция кода их не двигает; их компактная позиция задаётся
    # явно: глиф-блок печётся на GLYPH_BASE, текстовый back-буфер (Фаза 1) на 0x6600.
    RAM_REMAP = {0x6000: GLYPH_BASE, 0x5000: 0x6600}

    def _map(x):
        if x >= CODE_END:
            return RAM_REMAP.get(x, x)
        return new_addr(x)
    cobjs = []
    for o in rdb["objects"]:
        a = int(o["address"], 16)
        if _in_hole(a):
            continue
        no = dict(o)
        no["address"] = "0x%04X" % _map(a)
        if "links" in o and isinstance(o["links"], list):
            no["links"] = ["0x%04X" % _map(int(L, 16))
                           for L in o["links"]
                           if not _in_hole(int(L, 16))]
        cobjs.append(no)
    compact_rdb = dict(rdb)
    compact_rdb["objects"] = cobjs
    compact_rdb["rom"] = dict(rdb.get("rom", {}))
    compact_rdb["rom"]["comment"] = (
        "COMPACT (Фаза 2): дыры %s вырезаны; объекты >=0x%04X сдвинуты new_addr (-%d); "
        "byte-exact только [0x0100,0x%04X)." % (
            [list(h) for h in HOLES], HOLES[0][0], TOTAL_DELTA, HOLES[0][0]))
    compact_rdb["rom"]["size"] = IMG_END - ORG
    with open(os.path.join(ROOT, "putup_compact.rdb"), "w", encoding="utf-8") as f:
        _json.dump(compact_rdb, f, ensure_ascii=False, indent=1)
    dropped = len(rdb["objects"]) - len(cobjs)
    print("putup_compact.rdb: %d объектов (%d в дырах -> удалено), reloc >=0x%04X"
          % (len(cobjs), dropped, HOLES[0][0]))

emitbytes = sum(k[2] for k in kept)
imgsize = IMG_END - ORG
print("kept emit files: %d (%d bytes)" % (len(kept), emitbytes))
print("gaps: %d (%d bytes) -> inline DEFB в мастере" % (gapcount, gapbytes))
print("glyph block @0x%X..0x%X" % (GLYPH_BASE, IMG_END - 1))
print("image: %d bytes (0x%X..0x%X)" % (imgsize, ORG, IMG_END - 1))
