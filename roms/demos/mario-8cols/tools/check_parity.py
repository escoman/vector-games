#!/usr/bin/env python3
"""check_parity.py — ЧЕКПОИНТ паритета объектной модели (Фаза 1).

Разворачиваем src/objects.json обратно в плоскую tilemap (gen_assets.expand_
objects) и сверяем побайтово с сеткой src/level.json. Пока расхождений 0 —
объектная модель точно воспроизводит уровень, и можно переводить рендер/
коллизии на runtime-печь (Фаза 3), не боясь изменить картинку.

    python3 tools/check_parity.py        # exit 0 при 0 расхождений, иначе 1
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, HERE)
import gen_assets as G                                    # noqa: E402


def main():
    with open(os.path.join(SRC, "level.json")) as f:
        lv = json.load(f)
    cols, rows, grid = int(lv["cols"]), int(lv["rows"]), lv["grid"]

    o_cols, o_rows, objects = G.load_objects()
    if objects is None:
        print("objects.json нет — сначала: python3 tools/objects_from_grid.py")
        return 2
    if (o_cols, o_rows) != (cols, rows):
        print(f"РАЗМЕР: objects.json {o_cols}x{o_rows} != level.json "
              f"{cols}x{rows}")
        return 1

    exp = G.expand_objects(cols, rows, objects)
    diffs = [(i, grid[i], exp[i]) for i in range(cols * rows) if grid[i] != exp[i]]
    if diffs:
        print(f"РАСХОЖДЕНИЙ: {len(diffs)} (первые 20): col,row: grid!=objects")
        for i, g, e in diffs[:20]:
            print(f"   col={i // rows} row={i % rows}: {g} != {e}")
        return 1
    print(f"PARITY PASS: {len(objects)} объектов разворачиваются в точную "
          f"карту {cols}x{rows} (0 расхождений)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
