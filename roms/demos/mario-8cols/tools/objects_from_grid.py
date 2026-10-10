#!/usr/bin/env python3
"""objects_from_grid.py — разложить плоскую сетку уровня на список объектов.

Затравка объектной модели (Фаза 1): читаем src/level.json (grid col-major,
grid[col*rows+row] = индекс тайла) и покрываем все непустые клетки набором
максимальных прямоугольников ОДНОГО тайла. Каждый прямоугольник -> объект
{t, x, y, w, h} (t — индекс тайла, x/y — левый-верхний угол в тайлах).

Такая декомпозиция ВОСПРОИЗВОДИТ карту точно (каждая непустая клетка покрыта
ровно один раз своим тайлом), поэтому годится как чекпоинт паритета перед
переходом на runtime-печь. Пустые (небо, тайл 0) клетки не эмитятся вовсе —
за счёт этого список и компактен: пол = несколько широких полос, а не тысячи
ячеек.

Порядок объектов = порядок обхода (сверху-вниз, слева-направо) — детерминирован.

    python3 tools/objects_from_grid.py        # -> src/objects.json
"""
import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")


def cover_rectangles(cols, rows, grid):
    """Покрыть непустые клетки максимальными одно-тайловыми прямоугольниками.

    Жадный обход по колонкам (col-major): от первой непокрытой непустой клетки
    растягиваем прямоугольник вширь (соседние колонки, та же строка, тот же
    тайл), затем ввысь (полосы той же ширины). grid[col*rows + row].
    """
    covered = [False] * (cols * rows)
    objects = []
    for col in range(cols):
        for row in range(rows):
            idx = col * rows + row
            if covered[idx]:
                continue
            t = grid[idx]
            if t == 0:                       # небо — покрываем «впустую»
                covered[idx] = True
                continue
            # ширина: те же строки, следующие колонки, тот же тайл, не покрыт
            w = 1
            while col + w < cols:
                j = (col + w) * rows + row
                if covered[j] or grid[j] != t:
                    break
                w += 1
            # высота: вся полоса шириной w сохраняет тот же тайл и не покрыта
            h = 1
            while row + h < rows:
                if any(covered[(col + dx) * rows + row + h]
                       or grid[(col + dx) * rows + row + h] != t
                       for dx in range(w)):
                    break
                h += 1
            for dy in range(h):
                for dx in range(w):
                    covered[(col + dx) * rows + row + dy] = True
            objects.append({"t": t, "x": col, "y": row, "w": w, "h": h})
    return objects


def main():
    with open(os.path.join(SRC, "level.json")) as f:
        lv = json.load(f)
    cols, rows, tile, grid = lv["cols"], lv["rows"], lv["tile"], lv["grid"]
    objects = cover_rectangles(cols, rows, grid)
    area = sum(o["w"] * o["h"] for o in objects)
    out = {"cols": cols, "rows": rows, "tile": tile, "objects": objects}
    path = os.path.join(SRC, "objects.json")
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"objects.json: {len(objects)} объектов покрывают {area} непустых "
          f"клеток ({cols}x{rows}, тайл {tile} px)")


if __name__ == "__main__":
    main()
