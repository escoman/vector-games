#!/usr/bin/env python3
"""check_parity.py — ЧЕКПОИНТ паритета объектной модели.

src/objects.json разворачивается обратно в плоскую tilemap и сверяется
побайтово с сеткой src/level.json. Формат берётся из поля version:

  v1 — список прямоугольников {t,x,y,w,h}      -> gen_assets.expand_objects;
  v2 — список экземпляров префабов {pf,x,y[,w][,h]} -> prefablib.expand_
       instances, порядок списка = z-order, т.е. ровно то, что увидит печь
       окна в main.c.

Пока расхождений 0 — модель точно воспроизводит уровень, и можно переводить
рендер/коллизии на runtime-печь, не боясь изменить картинку.

    python3 tools/check_parity.py                       # src/objects.json
    python3 tools/check_parity.py ФАЙЛ.json [ПРЕФАБЫ]  # dry-run миграции
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, HERE)
import gen_assets as G                                    # noqa: E402
import prefablib as P                                     # noqa: E402


def expand(path, prefab_file=P.PREFAB_FILE):
    """objects.json (v1 или v2) -> (cols, rows, tilemap, что именно сверяли)."""
    with open(path) as f:
        ov = json.load(f)
    cols, rows = int(ov["cols"]), int(ov["rows"])
    if int(ov.get("version", 1)) == P.PREFAB_VERSION:
        prefabs = P.load_prefabs(prefab_file)
        inst = ov["instances"]
        what = "%d экземпляров %d префабов" % (len(inst), len(prefabs))
        return cols, rows, P.expand_instances(cols, rows, prefabs, inst), what
    objects = ov["objects"]
    return (cols, rows, G.expand_objects(cols, rows, objects),
            "%d прямоугольников" % len(objects))


def main():
    with open(os.path.join(SRC, "level.json")) as f:
        lv = json.load(f)
    cols, rows, grid = int(lv["cols"]), int(lv["rows"]), lv["grid"]

    objs = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SRC,
                                                              "objects.json")
    pf = sys.argv[2] if len(sys.argv) > 2 else P.PREFAB_FILE
    if not os.path.exists(objs):
        print("%s нет — сначала: python3 tools/objects_from_grid.py" % objs)
        return 2
    o_cols, o_rows, exp, what = expand(objs, pf)
    if (o_cols, o_rows) != (cols, rows):
        print(f"РАЗМЕР: {os.path.basename(objs)} {o_cols}x{o_rows} != "
              f"level.json {cols}x{rows}")
        return 1

    diffs = [(i, grid[i], exp[i]) for i in range(cols * rows)
             if grid[i] != exp[i]]
    if diffs:
        print(f"РАСХОЖДЕНИЙ: {len(diffs)} (первые 20): col,row: grid!=objects")
        for i, g, e in diffs[:20]:
            print(f"   col={i // rows} row={i % rows}: {g} != {e}")
        return 1
    print(f"PARITY PASS: {what} разворачиваются в точную карту {cols}x{rows} "
          f"(0 расхождений)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
