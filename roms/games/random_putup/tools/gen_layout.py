#!/usr/bin/env python3
# Компоновщик random_putup.rom (проект roms/games/random_putup) — OVERLAY-ВАРИАНТ
# игры putup (база: roms/games/putup). БЕЗ symlink'ов: только относительные пути.
#
# Идея «патча к имеющемуся исходному коду»: файлы-источники НЕ копируются —
# мастер включает базу по путям ../../putup/asm/... и патч-файлы ../../overlay/.
# z80asm запускается из asm/ проекта random_putup с -i ../../putup/asm (Makefile):
#   * явные пути мастера резолвятся от CWD (asm/);
#   * вложенные include самой базы (`data/data_level_01.asm` внутри
#     data_level_maps.asm) находятся по -i-пути ../../putup/asm — база собирается
#     точно так же, как своя (её Makefile делает `cd asm && z80asm`).
#
# Порядок эмиссии = include-список собранного мастера базы (putup/asm/putup_new.asm —
# истина; putup/tools/order.json устаревший и генератором базы не дописывается),
# на который наложены:
#   * overlay/funcs|data/<имя>.asm  EXISTS  => вместо базы с тем же именем;
#   * overlay/splice.json  => [{"name","file","after"}] — вставка новых файлов
#     («after» = имя из порядка, "HEAD" — сразу после var_ram_symbols);
#   * DEAD (ниже) => файл исключён из образа.
# Как и в базе: закреплён только вход 0x0100, гэпов нет, все межфайловые ссылки
# символьны; реальные адреса — из .sym (tools/mk_manifest.py -> layout.json).
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))          # .../random_putup/tools
ROOT = os.path.dirname(HERE)                                # .../random_putup
BASE   = os.path.join(ROOT, "..", "putup")                  # .../roms/games/putup
BASE_ASM = os.path.join(BASE, "asm")
BASE_MAST = os.path.join(BASE_ASM, "putup_new.asm")
ASM = os.path.join(ROOT, "asm")          # CWD z80asm при сборке
OVR = os.path.join(ROOT, "overlay")

# Мёртвый шлак в random-ветке. Stage-0/2a: пусто. Рантайм-генератор func_gen_level
# заполняет СУЩЕСТВУЮЩИЕ массивы data_level_maps/data_level_params по месту (ОНИ
# в ОЗУ, образ грузится на 0x0100), поэтому func_level_loader остаётся нетронутым,
# а исключать карты из образа НЕ нужно (минимальные правки исходной игры).
DEAD = set()

if not os.path.exists(BASE_MAST):
    raise SystemExit("нет базового мастера %s — соберите putup сначала" % BASE_MAST)

# Истинный порядок эмиссии базы — include-список собранного мастера: putup's
# gen_layout докидывает «неучтённые» живые файлы в конец мастера, но НЕ пишет
# их обратно в order.json.
inc_re = re.compile(r'^\s*include\s+"(?:\w+/)?([\w.]+)\.asm"', re.I)
base_order = []
for ln in open(BASE_MAST, encoding="utf-8"):
    m = inc_re.match(ln)
    if m and m.group(1) not in ("var_ram_symbols", "data_glyph_block_unpacked"):
        base_order.append(m.group(1))

# --- overlay: замены и вставки ----------------------------------------------
overrides = {}
for sub in ("funcs", "data"):
    d = os.path.join(OVR, sub)
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".asm"):
                overrides[fn[:-4]] = "%s/%s" % (sub, fn)

splice = []
sp_path = os.path.join(OVR, "splice.json")
if os.path.exists(sp_path):
    splice = json.load(open(sp_path, encoding="utf-8"))

# --- итоговый порядок --------------------------------------------------------
order = [nm for nm in base_order if nm not in DEAD]
for nm in overrides:                    # замены стоят на месте базы в порядке
    if nm not in order:
        order.append(nm)                # новый файл без якоря — в конец
for ent in splice:                      # HEAD-вставки эмитятся отдельным блоком
    nm = ent["name"]
    if nm in DEAD or ent.get("after") == "HEAD":
        continue
    if nm in order:
        continue
    idx = order.index(ent["after"]) + 1 if ent.get("after") in order else len(order)
    order.insert(idx, nm)

# --- разрешение имён в пути (относительно CWD=asm/) --------------------------
def base_path(nm):
    for sub in ("funcs", "data"):
        if os.path.exists(os.path.join(BASE_ASM, sub, nm + ".asm")):
            return "../../putup/asm/%s/%s.asm" % (sub, nm)
    if os.path.exists(os.path.join(BASE_ASM, nm + ".asm")):
        return "../../putup/asm/%s.asm" % nm
    return None

name2src = {}
for nm in order:
    p = overrides.get(nm)
    if p:
        name2src[nm] = "../overlay/%s" % p
    else:
        p = base_path(nm)
        if p is None:
            raise SystemExit("emit %r: нет ни в базе, ни в overlay/" % nm)
        name2src[nm] = p
for ent in splice:                      # новые splice-файлы (не-HEAD)
    nm = ent["name"]
    if nm in overrides:
        name2src[nm] = "../overlay/%s" % overrides[nm]
    elif ent.get("after") != "HEAD":
        name2src[nm] = "../overlay/%s" % ent["file"]

# --- мастер asm (пишется в asm/, пути — от CWD=asm/) --------------------------
lines = []
lines.append("; random_putup.rom (games/random_putup) — OVERLAY-вариант putup, СВОБОДНАЯ КОНКАТАЕНАЦИЯ")
lines.append("; ГЕНЕТОР tools/gen_layout.py — не править руками.")
lines.append("; База: ../../putup/asm (порядок = include-список putup_new.asm). Патч: ../overlay/.")
lines.append("; Закреплён только вход (0x0100). Гэпов нет. Блок глифов — вплотную за кодом.")
lines.append("")
lines.append("    org 0h")
lines.append('    include "../../putup/asm/var_ram_symbols.asm"')
for ent in splice:
    if ent.get("after") != "HEAD":
        continue
    nm = ent["name"]
    if nm in DEAD or nm in overrides:
        continue
    src = os.path.join(OVR, ent["file"])
    if not os.path.exists(src):
        raise SystemExit("splice(HEAD) %r: нет файла %s" % (nm, src))
    lines.append('    include "../overlay/%s"' % ent["file"])
lines.append("")
lines.append("    defs 0x0100 - $ ; точка входа")
for nm in order:
    lines.append('    include "%s"' % name2src[nm])
# data_glyph_block обязан быть ЧЁТНЫМ (бит0 слова указателя = тег compactness) —
# тот же инвариант, что в базе (см. putup/tools/gen_layout.py).
lines.append("    defs $ & 1 ; выровнять блок глифов на чётный (бит0 = тег compact)")
lines.append('    include "../../putup/asm/data/data_glyph_block_unpacked.asm"   ; блок глифов')
lines.append("")
os.makedirs(ASM, exist_ok=True)
open(os.path.join(ASM, "random_putup.asm"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

# свой order.json — для диагностики/следующих прогонов (пересобирается всегда)
json.dump(order, open(os.path.join(ROOT, "tools", "order.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("база: %d emit + overlay: %d замен, %d вставок, DEAD: %d"
      % (len(base_order), len(overrides), len(splice), len(DEAD)))
print("итого emit-файлов: %d (+ блок глифов)" % len(order))
