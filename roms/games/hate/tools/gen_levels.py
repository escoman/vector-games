"""Собрать include/levels.inc — карты уровней H.A.T.E. для Вектора-06Ц.

Вход — assets/level_data.bin (сырой срез $C400-$CFFF снапшота, см.
tools/extract_level_data.py). Формат исходных данных — оригинальные
байт-коды, ничего не «разворачивается» в пиксели:

  банк шаблонов     72 клетки по 8 байт, код клетки -> lv_bank + 8*код
                    (в оригинале $C400 + 8*код; коды 23 и 24 — «дорожные»
                    клетки $C4B8/$C4C0, нижняя клетка столбца);
  записи столбцов   по 15 кодов, снизу вверх: дорожная клетка + 15 = 16
                    клеток = 128 строк. Указатели оригинала стояли на
                    произвольных байтах общего куска (сдвиг на 1..4 байта
                    назад = столбец, поднятый на клетку), поэтому записи
                    сняты с реальных указателей и продедуплированы по
                    содержимому: в lv_recs попадает только рисуемое;
  таблица частей    код части -> список номеров записей через $FF
                    (в оригинале список 16-битных указателей, $C8EA+2*код);
  скрипт уровня     байт-коды частей через $FF — ровно как в оригинале,
                    читается с (адрес+1);
  таблица уровней   смещения скриптов (в оригинале $CF04, слова-указатели).

Каждый уровень = 178 столбцов = 1424 пикселя — ширина ленты в assets/maps.png.

Что выходит в levels.inc и как это читает движок (include/mission.asm):

  lv_bank    банк шаблонов;
  lv_recs    записи столбцов, 15 кодов на запись;
  lv_parts   списки номеров записей, терминатор $FF;
  lv_pofs    [код] -> смещение в lv_parts (не используемый код -> терминатор);
  lv_scripts скрипты уровней, терминатор $FF;
  lv_sofs    [уровень] -> смещение в lv_scripts;
  lv_cfg     настройки движка (число уровней, дорожные клетки, клеток);
  lv_col4    цвет рельефа по номеру уровня mod 4 (жёлтый/голубой/зелёный/
             пурпурный — порядок, которым раскрашены ленты в maps.png);
  lv_pal4    базовая палитра буфера: 0 чёрный, 1 рельеф, 2 белый, 3 красный.

Запуск:
    python3 tools/gen_levels.py [--preview]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.dirname(HERE)
ASSETS = os.path.join(PORT, 'assets')
OUT = os.path.join(PORT, 'include', 'levels.inc')
PREVIEW = os.path.join(ASSETS, 'levels_preview.png')

DATA = os.path.join(ASSETS, 'level_data.bin')
BASE = 0xC400                 # адрес первого байта level_data.bin

PARTS = 0xC8EA                # таблица частей оригинала
QUEUE = 0xCA43                # очередь оригинала: сразу за таблицей частей
SCRIPTS = 0xCF04              # таблица уровней оригинала
ROAD_A = 23                   # $C4B8 — нижняя клетка дороги
ROAD_B = 24                   # $C4C0 — через каждые 8 столбцов
CELLS = 16                    # клеток в столбце (дорожная + 15)
REC_LEN = 15                  # кодов в записи столбца
REC_STRIDE = 16               # шаг записи в lv_recs (15 кодов + заполнитель)
TERM = 0xFF                   # терминатор скрипта и списка частей
COLS = 32                     # столбцов экрана (размер кольца)
SLOPE = 4                     # сдвиг ленты на столбец, строк
SHIFT_ROWS = 0                # насколько опустить ленту в кадре 256 строк

# Цвет рельефа по номеру уровня (RRRGGGBB, V06_RGB): тот же порядок, каким
# раскрашены ленты в assets/maps.png. Синий канал — 2 бита, максимум 3.
COL4 = [
    (7, 7, 0),                # жёлтый
    (0, 7, 3),                # голубой
    (0, 7, 0),                # зелёный
    (7, 0, 3),                # пурпурный
]
PAL_REST = [(0, 0, 0), (7, 7, 3), (7, 0, 0)]   # слоты 0, 2, 3: чёрный/белый/красный


def rgb(c):
    r, g, b = c
    v = (b << 6) | (g << 3) | r
    assert v < 0x100, 'цвет %r не влезает в RRRGGGBB' % (c,)
    return v


class Mem:
    """Доступ к срезу памяти по оригинальным адресам ZX."""

    def __init__(self, blob):
        self.m = blob

    def __getitem__(self, a):
        return self.m[a - BASE]


def decode(mem):
    """Оригинальные байт-коды -> (размер банка, записи, части, скрипты)."""
    # --- таблица частей: код -> список указателей на записи столбцов ------
    parts = {}
    code = 0
    while PARTS + 2 * code + 1 < QUEUE:
        a = PARTS + 2 * code
        ptrs = []
        while mem[a + 1] != 0 and len(ptrs) <= 64:
            ptrs.append(mem[a] | (mem[a + 1] << 8))
            a += 2
        parts[code] = ptrs
        code += 1
    maxcode = code - 1

    # --- таблица уровней и скрипты ----------------------------------------
    levels = []
    a = SCRIPTS
    while (mem[a] | (mem[a + 1] << 8)) != 0xFFFF:
        p = (mem[a] | (mem[a + 1] << 8)) + 1     # скрипт читается с +1
        codes = []
        while mem[p] != TERM:
            codes.append(mem[p])
            p += 1
        levels.append(codes)
        a += 4

    used = {c for codes in levels for c in codes}

    # --- записи столбцов с реальных указателей, дедупликация --------------
    def record(p):
        return tuple(mem[p + i] for i in range(REC_LEN))

    index = {}
    recs = []
    part_recs = {}
    for c in sorted(used):
        lst = []
        for p in parts.get(c, []):
            r = record(p)
            if r not in index:
                index[r] = len(recs)
                recs.append(r)
            lst.append(index[r])
        part_recs[c] = lst
    bank_n = max(max(r) for r in recs) + 1 if recs else 0
    return bank_n, recs, part_recs, levels, maxcode


def build(mem):
    bank_n, recs, part_recs, levels, maxcode = decode(mem)

    # банк шаблонов — из оригинальной памяти, коды 0..bank_n-1
    bank = [tuple(mem[0xC400 + 8 * c + i] for i in range(8))
            for c in range(bank_n)]

    # таблицы смещений: код -> lv_parts, уровень -> lv_scripts
    pofs, parts_blob = [], []
    for c in range(maxcode + 1):
        pofs.append(len(parts_blob))
        parts_blob += list(part_recs.get(c, [])) + [TERM]
    sofs, scripts_blob = [], []
    for codes in levels:
        sofs.append(len(scripts_blob))
        scripts_blob += list(codes) + [TERM]

    # геометрия: старт нижней клетки столбца x в его 256-байтовой колонке
    # VRAM. Байт m колонки — строка 255-m, клетка столбца идёт вверх по
    # экрану, поэтому старт x = SHIFT_ROWS + SLOPE*x.
    geom = [(SHIFT_ROWS + SLOPE * x, CELLS) for x in range(COLS)]
    return dict(bank=bank, recs=recs, parts=parts_blob, pofs=pofs,
                scripts=scripts_blob, sofs=sofs, geom=geom, maxcode=maxcode,
                nlevel=len(levels), road_a=ROAD_A, road_b=ROAD_B, cells=CELLS)


def emit(d):
    L = []
    w = L.append
    w('; levels.inc — карты уровней H.A.T.E. для Вектора-06Ц.')
    w(';')
    w('; Сгенерировано tools/gen_levels.py из assets/level_data.bin — руками не')
    w('; правится; включается из include/mission.asm.')
    w(';')
    w('; Данные — ОРИГИНАЛЬНЫЕ байт-коды (ENGINE.MD §3.3), только указатели')
    w('; заменены смещениями:')
    w(';   скрипт уровня -> коды частей -> список записей столбцов ->')
    w(';   запись = 15 кодов клеток -> банк шаблонов по 8 байт.')
    w('; Столбец ландшафта = дорожная клетка + 15 = %d клеток = %d строк;'
      % (d['cells'], d['cells'] * 8))
    w('; уклон ленты %d строк на столбец задаёт не данные, а старт блита'
      % SLOPE)
    w('; (lv_geom), как в кольце оригинала: off(x+1) = off(x) + $1FC.')
    w(';')
    w('; lv_bank   — %d клеток по 8 байт (код клетки -> lv_bank + 8*код);'
      % len(d['bank']))
    w('; lv_recs   — %d уникальных записей столбцов по %d кода (шаг %d);'
      % (len(d['recs']), REC_LEN, REC_STRIDE))
    w('; lv_parts  — списки номеров записей, терминатор $FF;')
    w('; lv_pofs   — [%d смещений] код -> lv_parts;' % (d['maxcode'] + 1))
    w('; lv_scripts— скрипты %d уровней, коды частей через $FF;' % d['nlevel'])
    w('; lv_sofs   — смещения скриптов по номерам уровней;')
    w('; lv_geom   — %d пар (старт, клеток): старт нижней клетки столбца в' % len(d['geom']))
    w(';             его 256-байтовой колонке VRAM;')
    w('; lv_cfg    — число уровней, коды дорожных клеток, клеток в столбце;')
    w('; lv_col4   — цвет рельефа по номеру уровня mod 4;')
    w('; lv_pal4   — палитра буфера (слот = логический цвет).')
    w('')
    w('SECTION rodata_user')
    w('')
    for name in ('lv_bank', 'lv_recs', 'lv_parts', 'lv_pofs', 'lv_scripts',
                 'lv_sofs', 'lv_geom', 'lv_cfg', 'lv_col4', 'lv_pal4',
                 '_lv_pal4', '_lv_col4', '_lv_cfg'):
        w('PUBLIC %s' % name)
    w('')
    w('lv_cfg:')
    w('_lv_cfg:')
    w('    defb %d                  ; число уровней' % d['nlevel'])
    w('    defb %d                  ; код дорожной клетки A' % d['road_a'])
    w('    defb %d                  ; код дорожной клетки B' % d['road_b'])
    w('    defb %d                  ; клеток в столбце' % d['cells'])
    w('    defb %d                  ; столбцов кольца' % COLS)
    w('    defb %d                  ; строк на клетку' % 8)
    w('    defb %d                  ; уклон ленты, строк на столбец' % SLOPE)
    w('')
    w('_lv_pal4:')
    w('lv_pal4:')
    w('    defb 0x%02X                 ; 0: чёрный' % rgb(PAL_REST[0]))
    w('    defb 0x%02X                 ; 1: рельеф (меняется по уровню)'
      % rgb(COL4[0]))
    w('    defb 0x%02X                 ; 2: белый — текст, HUD' % rgb(PAL_REST[1]))
    w('    defb 0x%02X                 ; 3: красный — враги' % rgb(PAL_REST[2]))
    w('')
    w('_lv_col4:')
    w('lv_col4:')
    for i, c in enumerate(COL4):
        w('    defb 0x%02X                 ; %s' % (rgb(c), str(i)))
    w('')
    w('lv_bank:')
    for i, cell in enumerate(d['bank']):
        w('    defb %s%s; клетка %d'
          % (', '.join('0x%02X' % b for b in cell), ' ' * 2, i))
    w('')
    w('lv_recs:')
    for i, rec in enumerate(d['recs']):
        vals = list(rec) + [0] * (REC_STRIDE - REC_LEN)
        w('    defb %s ; запись %d' % (', '.join('%d' % c for c in vals), i))
    w('')
    w('lv_pofs:')
    for i in range(0, len(d['pofs']), 8):
        w('    defw %s' % ', '.join('lv_parts + %d' % o
                                    for o in d['pofs'][i:i + 8]))
    w('')
    w('lv_parts:')
    for i in range(0, len(d['parts']), 16):
        w('    defb %s' % ', '.join('%d' % v for v in d['parts'][i:i + 16]))
    w('')
    w('lv_sofs:')
    for i in range(0, len(d['sofs']), 8):
        w('    defw %s' % ', '.join('lv_scripts + %d' % o
                                    for o in d['sofs'][i:i + 8]))
    w('')
    w('lv_scripts:')
    for i in range(0, len(d['scripts']), 16):
        w('    defb %s' % ', '.join('%d' % v for v in d['scripts'][i:i + 16]))
    w('')
    w('lv_geom:')
    for x, (start, cnt) in enumerate(d['geom']):
        w('    defb %3d, %2d              ; x=%d: байты %d..%d'
          % (start, cnt, x, start, start + 8 * cnt - 1))
    w('')
    return '\n'.join(L) + '\n'


def preview(d):
    """Кадры миссии так, как их соберёт блиттер: несколько позиций камеры."""
    from PIL import Image
    bank_n, recs, part_recs, levels, maxcode = decode(Mem(open(DATA, 'rb').read()))
    raw = Mem(open(DATA, 'rb').read())
    bank = [tuple(raw[0xC400 + 8 * c + i] for i in range(8))
            for c in range(bank_n)]
    seq = []
    for codes in levels:
        for c in codes:
            seq.extend(part_recs[c])
    n = len(seq)
    frames = 6
    img = Image.new('P', (COLS * 8, 256 * frames), 0)
    pal = [(0, 0, 0)] + COL4
    flat = []
    for c in pal:
        flat += [v * 0x24 for v in c]
    img.putpalette(flat + [0] * (768 - len(flat)))
    px = img.load()
    for f in range(frames):
        cam = f * 8
        base = f * 256
        for x in range(COLS):
            col = cam + x
            rec = seq[col % n]
            road = ROAD_B if (((col >> 1) + 1) % 4 == 0) else ROAD_A
            cells = [bank[road]] + [bank[c] for c in recs[rec]]
            start = SHIFT_ROWS + SLOPE * x
            for k, pat in enumerate(cells):
                for i in range(8):
                    bits = pat[i]
                    if not bits:
                        continue
                    row = base + 255 - (start + 8 * k + i)
                    for j in range(8):
                        if bits & (0x80 >> j):
                            px[x * 8 + j, row] = 1
    img.save(PREVIEW)
    print('превью:', PREVIEW, img.size)


def main():
    mem = Mem(open(DATA, 'rb').read())
    d = build(mem)
    total = (len(d['bank']) * 8 + len(d['recs']) * REC_STRIDE +
             len(d['parts']) + 2 * len(d['pofs']) + len(d['scripts']) +
             2 * len(d['sofs']) + 2 * len(d['geom']))
    print('банк %d клеток, записей %d, частей %d Б, скриптов %d Б, уровней %d'
          % (len(d['bank']), len(d['recs']), len(d['parts']),
             len(d['scripts']), d['nlevel']))
    print('данных ~%d Б -> %s' % (total, os.path.relpath(OUT, PORT)))
    with open(OUT, 'w') as f:
        f.write(emit(d))
    if '--preview' in sys.argv:
        preview(d)


if __name__ == '__main__':
    main()
