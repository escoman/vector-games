"""Собрать include/levels.inc — карты уровней H.A.T.E. для Вектора-06Ц.

Вход — assets/level_data.bin (сырой срез $C400-$CFFF снапшота, см.
tools/extract_level_data.py). Формат — оригинальные байт-коды как они лежат в
памяти ZX, в пиксели ничего не разворачивается:

  банк шаблонов     72 клетки по 8 байт: код клетки -> lv_data + 8*код
                    (в оригинале $C400 + 8*код);
  таблица частей    $C8EA: слово с номером code — начало списка 16-битных
                    указателей; список идёт по словам до слова со старшим
                    байтом 0 (LD4E9, ENGINE.MD §3.3). Списки лежат встык, так
                    что список части — «хвост» таблицы с позиции code;
  скрипт уровня     байт-коды частей через $FF — ровно как в оригинале,
                    читается с (адрес+1);
  таблица уровней   смещения скриптов (в оригинале $CF04, 4-байтные записи).

СТОЛБЕЦ РЕЛЬЕФА. Страницу кольца в оригинале собирает $D51D (LD4E9_4):
дорожная клетка + 15 клеток, и КАЖДАЯ клетка берётся СВОИМ указателем:

    клетка i = lv_data[q[base + i] + i],   i = 0..14,
    q        — очередь указателей уровня (склейка списков частей по скрипту),
    base     — номер столбца уровня: на столбец очередь уходит на ОДИН
               указатель вперёд (в $D51D курсор очереди сдвигается на слово),
               а индекс клетки прибавляется к указателю в ADD HL,BC.

Отсюда диагональ: код клетки едет на байт вверх на каждый столбец. Прежняя
версия генератора читала 15 байт подряд от одного указателя — это давало
«ёлочку» вместо плит (верный образец — assets/terrain_preview.png).

ДОРОЖНАЯ КЛЕТКА: B ($C4C0) при (столбец+1) & 3 = 0, иначе A ($C4B8).
В оригинале правило считает по $C32E = 2*столбец (страница кольца на столбец
уходит на две: off(x+1) = off(x) + $1FC).

ХВОСТ ОЧЕРЕДИ. Скрипт уровня даёт 178 указателей, но очередь живёт в
буфере $CA43, который сборщик (LD4E9) не чистит: за последним записанным
словом остаётся образ программы. Конец уровня $D51D определяет НА СТОЛБЕЦ
ВПЕРЁД: в LD2E3_20 он читает старший байт указателя base+15 и, если это
$FF, строит очередь следующего уровня. Поэтому за скриптом дочитывается
хвост из образа буфера ($C643/$C655 вперемешку) и уровень кончается за
столбец до терминатора $FFFF — ровно 176 столбцов. Хвост состоит из тех же
указателей, что и начало уровня, поэтому стык уровней получается гладким:
лента выходит на ровный участок и следующий уровень начинается с него же.

Что выходит в levels.inc и как это читает движок (include/mission.asm):

  lv_cfg      настройки движка (число уровней, дорожные клетки, клеток);
  lv_col4     цвет рельефа по номеру уровня mod 4 (жёлтый/голубой/зелёный/
              пурпурный — порядок, которым раскрашены ленты в maps.png);
  lv_pal4     базовая палитра буфера: 0 чёрный, 1 рельеф, 2 белый, 3 красный;
  lv_parts    слово — адрес таблицы частей ($C8EA) внутри lv_data;
  lv_tail     хвост очереди: слова из образа буфера $CA43 после скрипта
              уровня, терминатор $FFFF (старший байт $FF = конец уровня);
  lv_delta    слово — lv_data - $C400: указатель ZX + lv_delta = адрес байта
              внутри lv_data (движок складывает их в m_pop);
  lv_data     срез $C400-$CFFF целиком (банк шаблонов + таблица частей);
  lv_scripts  скрипты уровней, терминатор $FF;
  lv_sofs     [уровень] -> смещение в lv_scripts;
  lv_geom     пара (старт, клеток) на столбец экрана: старт блита.

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
QUEUE = 0xCA43                # буфер очереди указателей ($CA43-$CF03)
SCRIPTS = 0xCF04              # таблица уровней оригинала
ROAD_A = 23                   # $C4B8 — нижняя клетка дороги
ROAD_B = 24                   # $C4C0 — через каждые 4 столбца
CELLS = 16                    # клеток в столбце (дорожная + 15)
REC_LEN = 15                  # клеток записи столбца (без дорожной)
TERM = 0xFF                   # терминатор скрипта и списка частей
COLS = 32                     # столбцов экрана (размер кольца)
SLOPE = 4                     # сдвиг ленты на столбец, строк
SHIFT_ROWS = 0                # насколько опустить ленту в кадре 256 строк
BANK_CELLS = 72               # шаблонов в банке ($C400..$C640)

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
    """Таблица $CF04 -> скрипты уровней (байт-коды частей)."""
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
    return levels


def part_list(mem, code):
    """Список указателей части code — ровно как его читает LD4E9."""
    a = PARTS + 2 * code
    ptrs = []
    while mem[a + 1] != 0 and len(ptrs) <= 64:
        ptrs.append(mem[a] | (mem[a + 1] << 8))
        a += 2
    return ptrs


def queue(mem, codes):
    """Очередь уровня: склейка списков частей в порядке скрипта."""
    q = []
    for c in codes:
        q.extend(part_list(mem, c))
    return q


def queue_tail(mem, nptr):
    """Хвост очереди — слова образа буфера $CA43 за последним записанным.

    Сборщик уровня пишет nptr указателей, буфер дальше не чистит, и там
    остаётся образ программы. Терминатор — слово со старшим байтом $FF.
    Последнее слово хвоста НЕ дочитывается: $D51D смотрит на столбец
    вперёд (base+15), поэтому уровень кончается за столбец до $FFFF.
    """
    words = []
    a = QUEUE + 2 * nptr
    while (mem[a] | (mem[a + 1] << 8)) >> 8 != 0xFF:
        words.append(mem[a] | (mem[a + 1] << 8))
        a += 2
    return words[:-1]


def column(mem, q, base):
    """Коды 15 клеток столбца base: каждая клетка — своим указателем."""
    return tuple(mem[q[base + i] + i] for i in range(REC_LEN))


def build(mem, blob):
    levels = decode(mem)
    queues = [queue(mem, codes) for codes in levels]
    nptr = min(len(q) for q in queues)
    tail = queue_tail(mem, nptr)
    # столбец дочитывает очередь на 14 указателей вперёд
    ncol = nptr + len(tail) - REC_LEN + 1
    geom = [(SHIFT_ROWS + SLOPE * x, CELLS) for x in range(COLS)]
    return dict(nlevel=len(levels), levels=levels, queues=queues, ncol=ncol,
                tail=tail, geom=geom, data=blob, parts_ofs=PARTS - BASE)


def emit(d):
    L = []
    w = L.append
    w('; levels.inc — карты уровней H.A.T.E. для Вектора-06Ц.')
    w(';')
    w('; Сгенерировано tools/gen_levels.py из assets/level_data.bin — руками не')
    w('; правится; включается из include/mission.asm.')
    w(';')
    w('; Данные — ОРИГИНАЛЬНЫЕ байт-коды (ENGINE.MD §3.3), без разворота в')
    w('; пиксели и без переписывания указателей:')
    w(';   скрипт уровня ($FF-поток кодов частей) ->')
    w(';   список указателей части ($C8EA + 2*код, до слова со старшим 0) ->')
    w(';   байт-код клетки: lv_data[q[base + i] + i], i = 0..14 ($D51D).')
    w(';')
    w('; Столбец ландшафта = дорожная клетка + %d = %d клеток = %d строк;'
      % (REC_LEN, CELLS, CELLS * 8))
    w('; уклон ленты %d строк на столбец задаёт не данные, а старт блита'
      % SLOPE)
    w('; (lv_geom), как в кольце оригинала: off(x+1) = off(x) + $1FC.')
    w(';')
    w('; lv_cfg    — число уровней, коды дорожных клеток, клеток в столбце;')
    w('; lv_pal4   — палитра буфера (слот = логический цвет);')
    w('; lv_col4   — цвет рельефа по номеру уровня mod 4;')
    w('; lv_parts  — адрес таблицы частей ($C8EA) внутри lv_data;')
    w('; lv_tail   — хвост очереди: %d слов образа буфера $CA43 за скриптом'
      % len(d['tail']))
    w(';             и терминатор $FFFF (старший байт $FF — уровень кончился);')
    w('; lv_delta  — lv_data - $C400: указатель ZX + lv_delta = адрес в lv_data;')
    w('; lv_data   — срез $C400-$CFFF: банк шаблонов + таблица частей (%d Б);'
      % len(d['data']))
    w('; lv_scripts— скрипты %d уровней, коды частей через $FF;' % d['nlevel'])
    w('; lv_sofs   — смещения скриптов по номерам уровней;')
    w('; lv_geom   — %d пар (старт, клеток): старт нижней клетки столбца в'
      % len(d['geom']))
    w(';             его 256-байтовой колонке VRAM.')
    w('')
    w('SECTION rodata_user')
    w('')
    for name in ('lv_parts', 'lv_tail', 'lv_delta', 'lv_data', 'lv_scripts',
                 'lv_sofs', 'lv_geom', 'lv_cfg', 'lv_col4', 'lv_pal4',
                 '_lv_pal4', '_lv_col4', '_lv_cfg'):
        w('PUBLIC %s' % name)
    w('')
    w('lv_cfg:')
    w('_lv_cfg:')
    w('    defb %d                  ; число уровней' % d['nlevel'])
    w('    defb %d                  ; код дорожной клетки A' % ROAD_A)
    w('    defb %d                  ; код дорожной клетки B' % ROAD_B)
    w('    defb %d                  ; клеток в столбце' % CELLS)
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
    w('lv_parts:')
    w('    defw lv_data + %d         ; $C8EA: код части -> список указателей'
      % d['parts_ofs'])
    w('lv_delta:')
    w('    defw lv_data - 0C400h      ; указатель ZX -> адрес в lv_data')
    w('')
    w('; Хвост каждого уровня: образ буфера очереди за скриптом (уровень')
    w('; дочитывает его в $D51D) и терминатор $FFFF — старший байт $FF')
    w('; означает конец уровня.')
    w('lv_tail:')
    tail = d['tail']
    for i in range(0, len(tail), 4):
        w('    defw %s%s'
          % (', '.join('0%04Xh' % v for v in tail[i:i + 4]),
             '' if i else '        ; начало уровня — стык получается гладким'))
    w('    defw 0FFFFh             ; терминатор хвоста')
    w('')
    w('lv_data:')
    for i in range(0, len(d['data']), 16):
        w('    defb %s; $%04X'
          % (', '.join('0x%02X' % b for b in d['data'][i:i + 16]), BASE + i))
    w('')
    sofs, scripts = [], []
    for codes in d['levels']:
        sofs.append(len(scripts))
        scripts += list(codes) + [TERM]
    w('lv_sofs:')
    for i in range(0, len(sofs), 8):
        w('    defw %s' % ', '.join('lv_scripts + %d' % o
                                    for o in sofs[i:i + 8]))
    w('')
    w('lv_scripts:')
    for i in range(0, len(scripts), 16):
        w('    defb %s' % ', '.join('%d' % v for v in scripts[i:i + 16]))
    w('')
    w('lv_geom:')
    for x, (start, cnt) in enumerate(d['geom']):
        w('    defb %3d, %2d              ; x=%d: байты %d..%d'
          % (start, cnt, x, start, start + 8 * cnt - 1))
    w('')
    return '\n'.join(L) + '\n'


def preview(d):
    """Лента уровня 0 так, как её собирает движок ($D51D)."""
    from PIL import Image
    mem = Mem(open(DATA, 'rb').read())
    bank = [tuple(mem[0xC400 + 8 * c + i] for i in range(8))
            for c in range(BANK_CELLS)]
    n = d['ncol']
    h = SLOPE * n + 176
    img = Image.new('P', (8 * n, h), 0)
    pal = [(0, 0, 0)] + COL4
    flat = []
    for c in pal:
        flat += [v * 0x24 for v in c]
    img.putpalette(flat + [0] * (768 - len(flat)))
    px = img.load()
    q = d['queues'][0] + d['tail']
    for b in range(n):
        road = ROAD_B if ((b + 1) & 3) == 0 else ROAD_A
        cells = (road,) + column(mem, q, b)
        y = h - SHIFT_ROWS - 16 - SLOPE * b
        for k, code in enumerate(cells):
            pat = bank[code]
            for i in range(8):
                row = y - 8 * k - i
                if not (0 <= row < h):
                    continue
                for j in range(8):
                    if pat[i] & (0x80 >> j):
                        px[b * 8 + j, row] = 1
    img.save(PREVIEW)
    print('превью:', PREVIEW, img.size)


def main():
    blob = open(DATA, 'rb').read()
    d = build(Mem(blob), blob)
    print('уровней %d, столбцов на уровень %d, данных %d Б'
          % (d['nlevel'], d['ncol'], len(d['data'])))
    for i, q in enumerate(d['queues']):
        print('  уровень %d: указателей %d (+%d хвоста), столбцов %d'
              % (i, len(q), len(d['tail']), d['ncol']))
    with open(OUT, 'w') as f:
        f.write(emit(d))
    print('->', os.path.relpath(OUT, PORT))
    if '--preview' in sys.argv:
        preview(d)


if __name__ == '__main__':
    main()
