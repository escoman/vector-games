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

# relocate-якоря var_music_* / data_voice_param_buf переведены (Stage-4) в РЕАЛЬНЫЕ
# метки на байтах emit-файлов данных (data_music_init.asm / var_music_voice2_flag_init.asm),
# поэтому отдельный словарь ANCHORS и генерируемый var_reloc_anchors.asm больше не нужны:
# метки едут за блоком автоматически в любом режиме компоновки.
# Встроенные 16-бит УКАЗАТЕЛИ в инициализированных RAM-значениях (var-init блок
# 0x383A..0x3857): содержат базы потоков нот, указывающие в перемещаемые data-
# таблицы. Их содержимое надо переписать через new_addr. Это ЕДИНСТВЕННЫЕ
# abs-поинтеры в verbatim-данных;Interior нотных/периодных таблиц — значения
# (периоды), НЕ патчится (иначе испортим музыку).
POINTER_SITES = (0x383F, 0x3841, 0x3843, 0x3854, 0x3856)

# Релокация СТАРЫХ абсолютных курсоров текста в verbatim gap-коде. redesign перенёс
# базу текстового back-буфера 0x5000 -> data_text_buffer(0x6600) (+0x1600). Именованные
# функции обновились через метку `data_text_buffer+ofs`, но gap-байты (verbatim
# оригинала) остались со старыми 0x5xxx -> строки печатались не в своей клетке
# («HURRY UP» сползла вниз; game-over-текст — тоже). Ключ — адрес инструкции LXI H
# (op 21); 16-бит операнд лежит в site+1 (lo) / site+2 (hi) — правим их в chunk.
# verify_image разрешает дельт высшим байтом +0x16 (RELOC_HIGH 0x50..0x53).
# Курсоры текстового буфера теперь СИМВОЛИЧНЫ в исходниках cluster B
# (func_gamestate_handlers 0x1296, func_collision_death 0x143B): LXI H,
# data_text_buffer+смещение. Побайтовая релокация gap-байтов больше не нужна.
TEXTBUF_BASE_RELOC = {}
RELOC_PATCHED: set = set()             # контроль: все ли курсоры найдены в gap-зоне

# compact: перемещённый код кончается на new_addr(0x4600)=0x3607 -> блок от 0x3608.
GLYPH_BASE = int(os.environ.get("GLYPH_BASE", "0x3608" if COMPACT else "0x4600"), 0)
GLYPH_ASM  = "data_glyph_block_unpacked.asm"   # снимок — побайтовые DEFB в asm
# Tier 2: размер компактного блока = фактическое число DEFB-байт снимка (буквы
# сжаты 32->8 Б). Не хардкод: блок читается ниже (glyph_txt) и там же сверяется.
def _glyph_defb_count():
    _t = open(os.path.join(ASM, "data", GLYPH_ASM), encoding="utf-8").read()
    n = 0
    for _ln in _t.splitlines():
        _m = re.match(r"\s*DEFB\s+(.+)", _ln, re.I)
        if _m:
            n += len([x for x in _m.group(1).split(";")[0].split(",") if x.strip()])
    return n
GLYPH_SIZE = _glyph_defb_count()               # 8192 verbatim / 5048 Tier-2
IMG_END = GLYPH_BASE + GLYPH_SIZE
# этап B: мёртвые распаковщики/пакеты выводятся из сборки (их диапазоны — нули).
# KEEP_DEAD=1 возвращает Stage-A раскладку (всё на исторических адресах).
KEEP_DEAD = os.environ.get("KEEP_DEAD", "0") != "0"
DEAD = {"func_load_gfx_2761",
        "data_packed_font_3041", "data_gfx_2761",
        # Stage-4 2b: legacy-движок блита — замкнутый мёртвый остров.
        # Функции удалены из анализа/эмиссии (диапазоны занулены по месту;
        # физическое удаление байтов — на 3B свободной конкатенации).
        # доказательства мёртвости: 0 прямых CALL (debug_get_xrefs), адрес blit
        # (0x0542) не встречается в ROM как значение (0x42 0x05 — 0 совпадений,
        # PCHL/таблица не достроит), unreachable в CFG от reset (uncovered
        # 0x051B..0x07FF), ни один живой emit не пишет вектор 0x0015. Живой
        # рендер: func_draw_game_objects -> sync_/func_render_tile_vram.
        "func_blit_object_tile", "func_call_vector_053B",
        "func_blit_plane_mask10", "func_blit_plane_mask20",
        "func_blit_plane_mask40", "func_blit_plane_mask80"}
# func_load_glyph_block (0x0401..0x0439) выведен из DEAD: слот занят живыми
# VBlank-sync трамплинами (см. funcs/func_load_glyph_block.asm) — эмитится как код.

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
    """Суммарное число байт побайтовых данных: DEFB-аргументы (×1) +
    DEFW/DW-аргументы (×2). Допускает метку перед директивой (`label: DEFB ...`)
    — data_music_init/voice2_flag несут пометки на байтах как reloc-метки."""
    n = 0
    for ln in txt.splitlines():
        code = ln.split(";")[0]
        m = re.search(r"\bDEFB\s+(.+)", code, re.I)
        if m:
            n += len([t for t in m.group(1).split(",") if t.strip()])
            continue
        m = re.search(r"\b(?:DEFW|DW)\s+(.+)", code, re.I)
        if m:
            n += 2 * len([t for t in m.group(1).split(",") if t.strip()])
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
    for site, new_imm in TEXTBUF_BASE_RELOC.items():
        if s <= site and site + 2 < e:        # op(LXI H) в site, операнд в site+1/+2
            assert chunk[site - s] == 0x21, "TEXTBUF_BASE_RELOC 0x%04X: ожидали op 21" % site
            chunk[site - s + 1] = new_imm & 0xFF
            chunk[site - s + 2] = new_imm >> 8
            RELOC_PATCHED.add(site)
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

# (var_reloc_anchors.asm не генерируется: relocate-якоря — теперь метки в emit-данных.)

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

assert RELOC_PATCHED == set(TEXTBUF_BASE_RELOC), \
    "не все курсоры TEXTBUF_BASE_RELOC найдены в gap-зоне: %s" % \
    (set(TEXTBUF_BASE_RELOC) - RELOC_PATCHED)

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
open(os.path.join(ASM, "putup_new.asm"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

# список разрешённых расхождений с оригиналом для make verify
import json as _json
rep = os.path.join(ROOT, "tools")           # состояние инструментов сборки
os.makedirs(rep, exist_ok=True)
ptr = emit.get("data_glyph_ptr_table")
with open(os.path.join(rep, "dead_ranges.json"), "w", encoding="utf-8") as f:
    _json.dump({"dead_ranges": [[s, e, n] for s, e, n in dead_ranges],
                "glyph_base": GLYPH_BASE,
                "glyph_size": GLYPH_SIZE,          # Tier 2: компактный блок < 8192
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

# putup_compact.rdb больше не генерируется: потребителей не было (только lint/
# disassembly по оригинальному putup.rdb), а flat-delta-модель new_addr/HOLES
# уходит вместе со свободной конкатенацией (Stage-4).

emitbytes = sum(k[2] for k in kept)
imgsize = IMG_END - ORG
print("kept emit files: %d (%d bytes)" % (len(kept), emitbytes))
print("gaps: %d (%d bytes) -> inline DEFB в мастере" % (gapcount, gapbytes))
print("glyph block @0x%X..0x%X" % (GLYPH_BASE, IMG_END - 1))
print("image: %d bytes (0x%X..0x%X)" % (imgsize, ORG, IMG_END - 1))
