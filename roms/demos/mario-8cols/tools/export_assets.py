#!/usr/bin/env python3
"""export_assets.py — разложить ассеты демки на редактируемые файлы.

Одноразовая (повторяемая) затравка перед переходом на редактор уровня:

  src/tiles/tile_NNN.png   — каждый уникальный тайл 8x8 (RGB, палитра Вектора);
  src/sprites/mario_NN.png — все 18 спрайтов Small Mario 16x16 (RGBA, альфа);
  src/level.json           — сетка уровня: grid[col*rows+row] = индекс тайла;
  src/tiles.json           — свойства тайла: solid (none|platform|wall), transparent.

Источник — те же gen_assets.build_level()/build_collision(), что и прошивка,
поэтому затравка точно повторяет текущий уровень. solid считается ПО ТАЙЛАМ
(агрегат из потайловой карты wall/plat): где тайлUsed и как стена, и как опора —
конфликт, выбираем более строгое (wall) и печатаем список на разбор в редакторе.

    python3 tools/export_assets.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_assets as G                                    # noqa: E402
from PIL import Image                                     # noqa: E402

SRC = G.SRC
TILES_DIR = os.path.join(SRC, "tiles")
SPRITES_DIR = os.path.join(SRC, "sprites")


def tile_to_grid(t):
    """32-байтный тайл (4 плоскости x 8 строк) -> grid[8][8] индексов палитры."""
    grid = [[0] * 8 for _ in range(8)]
    for p, w in enumerate((8, 4, 2, 1)):
        plane = t[p * 8:(p + 1) * 8]
        for r in range(8):
            b = plane[r]
            for c in range(8):
                if b & (1 << (7 - c)):
                    grid[r][c] |= w
    return grid


def export_tiles(tileset):
    os.makedirs(TILES_DIR, exist_ok=True)
    for i, t in enumerate(tileset):
        grid = tile_to_grid(t)
        im = Image.new("RGB", (8, 8))
        px = im.load()
        for r in range(8):
            for c in range(8):
                px[c, r] = G.PAL_RGB[grid[r][c]]
        im.save(os.path.join(TILES_DIR, f"tile_{i:03d}.png"))
    print(f"tiles: {len(tileset)} файлов -> {TILES_DIR}")


def export_sprites():
    os.makedirs(SPRITES_DIR, exist_ok=True)
    im = Image.open(os.path.join(SRC, "mario.png")).convert("RGB")
    px = im.load()
    n = 0
    for num in range(1, 19):
        grid = G.extract_cell(px, num)          # None = прозрачный
        out = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        opx = out.load()
        for r in range(16):
            for c in range(16):
                idx = grid[r][c]
                if idx is None:
                    continue
                rr, gg, bb = G.PAL_RGB[idx]
                opx[c, r] = (rr, gg, bb, 255)
        out.save(os.path.join(SPRITES_DIR, f"mario_{num:02d}.png"))
        n += 1
    print(f"sprites: {n} файлов -> {SPRITES_DIR}")


def tile_solid_from_maps(cols, rows, tilemap, wall, plat):
    """Вариант C: потайловая битовая маска. wall = тайл ХОТЬ ГДЕ-ТО стена,
    platform = хоть где-то опора. Тайл двойного назначения (земля/кирпич:
    и опора сверху, и стена по бокам) получает оба флага — это и есть смысл C.
    Возвращает (props, dual): props[ti] = (wall_bool, plat_bool)."""
    per = {}   # ti -> [n_cell, n_wall, n_plat]
    for col in range(cols):
        for row in range(rows):
            ti = tilemap[col * rows + row]
            bit = row * cols + col
            m = 1 << (bit & 7)
            w = bool(wall[bit >> 3] & m)
            p = bool(plat[bit >> 3] & m)
            rec = per.setdefault(ti, [0, 0, 0])
            rec[0] += 1
            if w:
                rec[1] += 1
            if p:
                rec[2] += 1
    props, dual = {}, []
    for ti, (n, nw, np_) in per.items():
        # platform — если хоть одна клетка опора (перестраховка безвредна:
        # «можно встать сверху» почти никогда не мешает). wall — только если
        # БОЛЬШИНСТВО клеток стена, иначе единичный выброс (тайл земли на краю
        # ямы) превратил бы всю поверхность в глухую стену.
        p = np_ > 0
        w = nw * 2 > n
        props[ti] = (w, p)
        if w and p:
            dual.append((ti, n, nw, np_))
    return props, dual


def export_jsons(cols, rows, tilemap, tile_nz, wall, plat):
    props, dual = tile_solid_from_maps(cols, rows, tilemap, wall, plat)
    tiles = []
    for ti in range(len(tile_nz)):
        w, p = props.get(ti, (False, False))
        tiles.append({
            "index": ti,
            "file": f"tiles/tile_{ti:03d}.png",
            "wall": w,                # непроходимо (бит COLL_WALL=2)
            "platform": p,            # опора сверху (бит COLL_PLAT=1)
            "transparent": tile_nz[ti] == 0,   # пустой (небо) тайл
        })
    with open(os.path.join(SRC, "tiles.json"), "w") as f:
        json.dump({"count": len(tiles), "tiles": tiles}, f,
                  ensure_ascii=False, indent=1)
    with open(os.path.join(SRC, "level.json"), "w") as f:
        json.dump({"cols": cols, "rows": rows, "tile": 8,
                   "grid": list(tilemap)}, f)
    nwall = sum(1 for t in tiles if t["wall"])
    nplat = sum(1 for t in tiles if t["platform"])
    print(f"tiles.json: {len(tiles)} тайлов (wall={nwall} platform={nplat}, "
          f"двойных={len(dual)})")
    print(f"level.json: {cols}x{rows}")
    if dual:
        print(f"тайлы двойного назначения (wall+platform, вариант C их и хранит):")
        for ti, n, nw, np_ in dual[:40]:
            print(f"   tile {ti:3d}: клеток={n} wall={nw} plat={np_}")


def main():
    cols, rows, tileset, tilemap, tile_nz, pair_top = G.build_level()
    wall, plat = G.build_collision(cols, rows, tilemap)
    export_tiles(tileset)
    export_sprites()
    export_jsons(cols, rows, tilemap, tile_nz, wall, plat)


if __name__ == "__main__":
    main()
