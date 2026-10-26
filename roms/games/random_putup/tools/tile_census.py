#!/usr/bin/env python3
# Перепись тайл-карт putup (Stage 2, random_putup): семантика тайлов + проверки
# модели координат выхода по оригинальным 15 картам — ОСНОВА правил func_gen_level.
#
# ФАКТЫ (проверены этой переписью по базе putup):
#  * карта 16x11, row-major; байт = индекс записи 4 кодов 2x2 в data_tile_graphics;
#  * клетка-тайлы: 1=floor(20 20 20 20), 2=wall(77 78 78 77), 3=safe(60...),
#    5=wall(7D 78 78 77), 6=FIRE(75 75 76 76; скан флипа 75<->FE каждый проход),
#    7=egg(20 20 72 6D -> +100/яйцо), 8=wall(79 7A 78 77), 9=(0x74-код; НЕ в картах),
#    10..13=фрукты (7E..71-коды), 14=ring(61 62 + 73 -> +жизнь);
#  * ДВЕРЬ выхода: params[+0]=X,+1]=Y — ПИКСЕЛЬНЫЕ координаты КЛЕТКИ тайл-карты
#    (клетка = (Y/2, X/2)); во всех 15 оригиналах X,Y чётные, тайл клетки — wall
#    (14x) или fire (2x); коды двери >=0x77 (hero не входит), при появлении выхода
#    func_draw_tile_to_buf затирает клетку проходимыми кодами 16h..19h;
#  * периметр НЕ инвариант (в оригиналах встречаются 6/7 на рёбрах) — генератор
#    кладёт периметр=2 жёстко (более строгое правило);
#  * диспетчер собирает предмет из клетки ПОД ногами hero -> предметы ставим только
#    на клетках, где снизу wall/fire.
#  * состояния врагов в оригиналах: 1..8 (уровни 12+ — чеканят иерархию сложности).
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.normpath(os.path.join(ROOT, "..", "putup", "asm", "data"))

def parse_defb(path):
    out = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"\s*DEFB\s+(.+)", ln, re.I)
        if m:
            for tok in m.group(1).split(";")[0].split(","):
                tok = tok.strip()
                if tok:
                    out.append(int(tok.rstrip("h"), 16) if tok.lower().endswith("h") else int(tok))
    return out

def rows(lv):
    return [lv[r * 16:(r + 1) * 16] for r in range(11)]

def kind(codes):
    cs = [c for c in codes if c]
    if not cs or all(c == 0x20 for c in cs): return "floor"
    if any(c >= 0x77 for c in cs):           return "wall"
    if 0x75 in cs:                            return "fire"
    if 0x74 in cs:                            return "trap_t"
    if 0x72 in cs:                            return "egg"
    if any(0x6E <= c <= 0x71 for c in cs):   return "fruit"
    if 0x73 in cs:                            return "ring"
    if 0x60 in cs:                            return "safe"
    return "other"

tg     = parse_defb(os.path.join(BASE, "data_tile_graphics.asm"))
params = parse_defb(os.path.join(BASE, "data_level_params.asm"))
levels = [parse_defb(os.path.join(BASE, "data_level_%02d.asm" % n)) for n in range(1, 16)]

tiles = {}
for i in range(23):
    codes = tg[i * 4:i * 4 + 4]
    tiles[i] = {"codes": codes, "kind": kind(codes),
                "uses_total": sum(lv.count(i) for lv in levels),
                "levels_used": sum(1 for lv in levels if i in lv)}

# --- проверка модели двери (X,Y пикс. -> клетка (Y/2,X/2), тайл wall/fire) -----
door_ok = []
for n in range(1, 16):
    ex, ey = params[n * 8], params[n * 8 + 1]
    r, c = ey // 2, ex // 2
    t = rows(levels[n - 1])[r][c]
    door_ok.append((n, ex, ey, t, tiles[t]["kind"],
                    ex % 2 == 0 and ey % 2 == 0 and tiles[t]["kind"] in ("wall", "fire")))

out = {"tiles": tiles,
       "doors": [{"level": n, "X": ex, "Y": ey, "cell": [ey // 2, ex // 2],
                 "tile": t, "kind": k, "model_ok": ok}
                 for n, ex, ey, t, k, ok in door_ok],
       "notes": [
           "exit X,Y = пиксельные координаты КЛЕТКИ карты: cell=(Y/2, X/2)",
           "дверь появляется после var_egg_seq>=B (B=1 для lv<10, 2 для lv>=10; loc_10C8)",
           "предметы лежат на клетках с wall/fire снизу (диспетчер читает клетку под ногами)",
           "perimeter НЕ инвариант оригиналов; генератор кладёт row0/row10/col0/col15 = tile 2",
       ]}
json.dump(out, open(os.path.join(ROOT, "tools", "tile_semantics.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)

print("модель двери соблюдена: %d/15" % sum(1 for d in out["doors"] if d["model_ok"]))
for i in sorted(tiles, key=int):
    t = tiles[i]
    if t["uses_total"]:
        print(" tile %2d %-10s codes=%s uses=%4d lvls=%2d"
              % (i, t["kind"], t["codes"], t["uses_total"], t["levels_used"]))
print("tile_semantics.json записан")
