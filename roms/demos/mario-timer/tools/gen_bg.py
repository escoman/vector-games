#!/usr/bin/env python3
"""gen_bg.py — статичный фон (старшие плоскости) для mario-timer.

Схема — сплит по плоскостям, как в mario-8cols: индекс палитры = bg*4 + ch.
ФОН живёт в старших плоскостях (вес 8 = 0x8000, вес 4 = 0xA000), Mariо — в
младших (вес 2/1 = C000/E000). Экран статичный (без скроллинга), поэтому весь
фон — одна сетка 32x32 тайлов, заливаемая в VRAM ОДИН раз при инициализации.

Тайлы и формы префабов (кусты/облака/земля) берутся НЕ перекодируя из соседней
демки mario-8cols:
  * тайлсет — массив `tileset[]` в ../mario-8cols/src/level.inc (130 тайлов по
    16 байт = 2 фоновые плоскости, порядок весов 8,4; байт r = строка сверху
    вниз, бит 0x80 = левый пиксель);
  * формы составных объектов — `prefabs.json` (grid глобальных индексов тайлов).

Результат — include/background.inc: компактный bg_tileset (только использованные
тайлы, перенумерованные локально; локальный 0 = пустое небо) и bg_map[32*32]
локальных индексов (порядок row-major: [row*BG_COLS + col]).

    python3 tools/gen_bg.py
"""
import os
import re
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'include')      # результат: .inc для сборки
M8 = os.path.abspath(os.path.join(ROOT, '..', 'mario-8cols', 'src'))
LEVEL_INC = os.path.join(M8, 'level.inc')
PREFABS_JSON = os.path.join(M8, 'prefabs.json')

BG_COLS = 32
BG_ROWS = 32

# Полоса земли: tile-ряды 28..31 (y=224..255) — совпадает с GROUND_TOP=224 в
# main.c; ноги стоящего Mariо (GROUND_MY=192..223) стоят на верхнем краю земли.
GROUND_ROW0 = 28


def load_tileset():
    txt = open(LEVEL_INC).read()
    m = re.search(r'const unsigned char tileset\[\d+\]\s*=\s*\{(.*?)\};', txt, re.S)
    data = [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', m.group(1))]
    assert len(data) % 16 == 0
    return [data[i * 16:(i + 1) * 16] for i in range(len(data) // 16)]


def load_prefabs():
    d = json.load(open(PREFABS_JSON))
    return {p['name']: p for p in d['prefabs']}


def main():
    tiles = load_tileset()
    pf = load_prefabs()
    grid_of = lambda name: pf[name]['grid']       # list of rows of global tile idx

    grid = [[0] * BG_COLS for _ in range(BG_ROWS)]  # [row][col] global tile index

    def place(g, col0, row0):
        """Положить прямоугольник-грид (row-major) левым верхом в (col0,row0)."""
        for r, row in enumerate(g):
            for c, t in enumerate(row):
                rr, cc = row0 + r, col0 + c
                if 0 <= rr < BG_ROWS and 0 <= cc < BG_COLS:
                    grid[rr][cc] = t

    def tile_rect(g, col0, col1, row0, row1):
        """Замостить прямоугольник [col0..col1] x [row0..row1] тайлами грида по
        модулю (горизонтальный повтор узора префаба)."""
        gh = len(g)
        gw = max(len(r) for r in g)
        for rr in range(row0, row1 + 1):
            for cc in range(col0, col1 + 1):
                grow = g[(rr - row0) % gh]
                grid[rr][cc] = grow[(cc - col0) % len(grow)]

    # ---- земля: замостить ряды 28..31 узором 'Земля Тип 2' ----
    earth = grid_of(u'Земля Тип 2')
    tile_rect(earth, 0, BG_COLS - 1, GROUND_ROW0, BG_ROWS - 1)
    # верхний газонный край (surface) на ряд 28, если есть — для читаемой кромки
    surf = grid_of(u'Поверхность')
    tile_rect(surf, 0, BG_COLS - 1, GROUND_ROW0, GROUND_ROW0 + len(surf) - 1)

    # ---- кусты: стоят на земле (низ ряда 27) ----
    bush = grid_of(u'Кустик')                       # 2x2
    place(bush, 2, GROUND_ROW0 - len(bush))         # col 2..3
    place(bush, 21, GROUND_ROW0 - len(bush))        # col 21..22
    bush_top = grid_of(u'Кусты верхушка 1')         # 2x4 (широкий куст)
    place(bush_top, 10, GROUND_ROW0 - len(bush_top))

    # ---- облака в небе ----
    cloud_big = grid_of(u'Облако Большое')          # 3 rows x 4 cols
    place(cloud_big, 7, 3)
    cloud_face = grid_of(u'Облачко с лицом')        # 2x2
    place(cloud_face, 24, 8)
    place(cloud_big, 17, 10)

    # ---- перенумеровать использованные тайлы (глобальный -> локальный) ----
    used = []
    lookup = {}
    def loc(gidx):
        if gidx == 0:
            return 0                       # пустое небо — всегда локальный 0
        if gidx not in lookup:
            lookup[gidx] = len(used)
            used.append(gidx)
        return lookup[gidx]

    local_map = [[loc(grid[r][c]) for c in range(BG_COLS)] for r in range(BG_ROWS)]
    # локальный 0 резервируем под тайл 0 (небо); сдвигаем остальные на +1
    out_tiles = [tiles[0]] + [tiles[g] for g in used]
    remap = {0: 0}
    for gidx, l in lookup.items():
        remap[gidx] = l + 1
    local_map = [[(remap[grid[r][c]] if grid[r][c] != 0 else 0)
                  for c in range(BG_COLS)] for r in range(BG_ROWS)]

    # ---- запись include/background.inc ----
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'background.inc'), 'w') as f:
        f.write('/* автоген: tools/gen_bg.py (фон из mario-8cols, сплит по '
                'плоскостям). НЕ править руками */\n\n')
        f.write('#define BG_COLS %d\n' % BG_COLS)
        f.write('#define BG_ROWS %d\n' % BG_ROWS)
        f.write('#define BG_TILE_N %d\n\n' % len(out_tiles))
        f.write('/* bg-тайлсет: 2 фоновые плоскости по 8 байт, порядок весов 8,4. */\n')
        f.write('static const unsigned char bg_tileset[%d] = {\n' % (len(out_tiles) * 16))
        for i, t in enumerate(out_tiles):
            f.write('    /* %3d */ ' % i)
            f.write(', '.join('0x%02X' % b for b in t) + ',\n')
        f.write('};\n\n')
        f.write('/* статичная карта фона: локальный индекс тайла, row-major '
                '[row*BG_COLS+col]. 0 = небо (не пишется). */\n')
        f.write('static const unsigned char bg_map[%d] = {\n' % (BG_ROWS * BG_COLS))
        for r in range(BG_ROWS):
            row = local_map[r]
            f.write('    /* r%2d */ ' % r)
            f.write(', '.join('%d' % v for v in row) + ',\n')
        f.write('};\n')

    print('OK: bg_tileset %d тайлов, %d байт; уникальных глобальных %d'
          % (len(out_tiles), len(out_tiles) * 16, len(used)))


if __name__ == '__main__':
    main()
