#!/usr/bin/env python3
"""gen_assets.py — ассеты игры «Ну, погоди!» для Вектора-06Ц.

Изображение оригинала (src/ground.png — фото аркадного «Ну, погоди!» с ЖКИ-
панелью) перекладывается на экран 256x256 Вектора в 16 цветов. Масштаб поля
2.2, левый верхний угла поля (262, 168).

Раскладка экрана по строкам:

     0..7    строка функциональных клавиш (в фоне чёрная, текст рисует ROM)
     8..15   «головка» поля: на ЖКИ заячьи уши и табло счёта стоят ВЫШЕ
             верхней границы поля, поэтому у координат спрайтов бывает
             отрицательный y — эти 8 строк и дают им место
    16..191  поле (256x176, масштабированный кроп фотографии)
   192..255  панель: четыре кнопки управления и рамки под подписи клавиш

Спрайты и их призраки задаются в координатах ПОЛЯ (y=0 — верхняя граница
поля на фото); FIELD_TOP сдвигает на экран и фон, и спрайты, поэтому призрак
на фоне и сегмент в плоскости веса 1 совпадают пиксель в пиксель.

Итоговая схема палитры (см. также main.c):

    бит 0 (плоскость 0xE000) — СЕГМЕНТЫ, то есть нарисованные объекты.
    Фон занимает только чётные слоты, так что бит 0 в фоне сброшен ВЕЗДЕ.
    Показать объект = OR его битмапы в 0xE000, стереть = AND-NOT теми же
    байтами: возвращаются ровно биты фона, никаких нейтральных патчей и
    теневых буферов не нужно.

    слот  биты  что                       цвет
      0   0000  вне поля (чёрная рамка)   0x00
      2   0010  заливка арены             0xAD
      4   0100  призраки сегментов        0xA4
      6   0110  декор: заборы, конструкция 0x13
      8   1000  декор: куры               0xFF
     10   1010  декор: кусты, травинки    0x12
      нечётные     сегменты               0x00

Заливка оригинала — диагональные полосы «небо / трава / арена» с плавным
переходом; на Векторе они дают шесть едва различимых оттенков и съедают
палитру, поэтому сводится к одному тону. Три настоящих цвета декора при этом
разделяются надёжно: после усреднения BOX-ом в источнике остаются (44,56,13)
кусты, (108,75,33) заборы, (236,236,236) куры и континуум 153..196 яркости,
в который попадают и полосы, и серые призраки.

Призраки НЕ извлекаются из фотографии — они рисуются из тех же масок, которые
потом идут сегментами, поэтому совпадают с объектами пиксель в пиксель.

Использование:
    python3 tools/gen_assets.py            # всё сразу
    python3 tools/gen_assets.py back       # только src/back.bmp
    python3 tools/gen_assets.py inc        # только .inc из готовых src/*.bmp|png
    python3 tools/gen_assets.py preview    # src/preview.png для просмотра
"""
import json
import os
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))

import bmp2inc as B   # noqa: E402  (parse_bmp, to_vector_color)
import zx0            # noqa: E402  (compress)

SRC = os.path.join(ROOT, 'roms/games/nu_pogodi/src')
GROUND = os.path.join(SRC, 'ground.png')
ATLAS_PNG = os.path.join(SRC, 'sprites.png')
ATLAS_JSON = os.path.join(SRC, 'sprites.json')
BACK_BMP = os.path.join(SRC, 'back.bmp')
BG_INC = os.path.join(SRC, 'bg.inc')
SPR_INC = os.path.join(SRC, 'sprites.inc')
PREVIEW = os.path.join(SRC, 'preview.png')

SCALE = 2.2
ARENA_W, ARENA_H = 256, 176       # поле в пикселях экрана
FIELD_X, FIELD_Y = 262, 168       # левый верхний угол поля на ground.png
FIELD_W, FIELD_H = 571, 371       # размер поля на ground.png (~2.23 x 2.11)
SCR_W, SCR_H = 256, 256           # холст = весь экран: поток плоскостей
                                  # ложится в 0x8000..0xDFFF без «дыр»
MENU_H = 8                        # строка Ф-клавиш сверху
HEADROOM = 8                      # строк над полем: уши зайца и табло счёта
FIELD_TOP = MENU_H + HEADROOM     # экранная строка y=0 поля = 16
BAND_TOP = FIELD_TOP - HEADROOM   # 8: выше поля ничего не рисуем
BAND_BOT = FIELD_TOP + ARENA_H    # 192: нижняя граница поля (исключительно)
PANEL_TOP = BAND_BOT              # 192: панель кнопок

SXC = FIELD_W / ARENA_W           # масштаб фотографии по горизонтали
SYC = FIELD_H / ARENA_H           # ... и по вертикали

# --- пороги классификации фона (зазоры между кластерами > 50 яркости) -----
WHITE_MIN = 215                    # min(R,G,B): куры 236, небо 196
DARK_MAX = 55                      # средняя яркость: кусты 38, забор 72
FIELD_MIN = 128                    # ниже — декор, выше — заливка/призраки

# --- слоты палитры и их цвета ---------------------------------------------
SLOT_OUT = 0
SLOT_FIELD = 2
SLOT_GHOST = 4
SLOT_BROWN = 6
SLOT_WHITE = 8
SLOT_DARK = 10
SLOT_INK = 1

BG_COLORS = {
    SLOT_OUT: 0x00,
    SLOT_FIELD: 0xAD,
    SLOT_GHOST: 0xA4,
    SLOT_BROWN: 0x13,
    SLOT_WHITE: 0xFF,
    SLOT_DARK: 0x12,
}

INK_COLOR = 0x00


def palette16():
    """16 байт в порт 0C: чётные — фон, нечётные — чернила."""
    pal = [INK_COLOR] * 16
    for slot, col in BG_COLORS.items():
        pal[slot] = col
    return pal


def vector_rgb(byte):
    return ((byte & 7) * 255 // 7,
            ((byte >> 3) & 7) * 255 // 7,
            ((byte >> 6) & 3) * 255 // 3)


# ===========================================================================
# Координаты. SPRITES.md — источник истины; здесь те же числа.
# Это координаты ПОЛЯ: y=0 — верхняя граница поля на фотографии. Y может быть
# отрицательным: спрайт выходит за верх поля (уши зайца, табло счёта на ЖКИ
# рисуются над полем). На экран координаты переводит srow().
# ===========================================================================

EGG_SLOTS = {
    'lt': [(21, 40), (30, 47), (42, 51), (51, 58), (59, 72)],
    'lb': [(22, 82), (31, 87), (39, 94), (50, 98), (58, 112)],
    'rt': [(227, 40), (218, 44), (207, 51), (197, 59), (189, 65)],
    'rb': [(229, 84), (218, 88), (207, 94), (198, 100), (187, 110)],
}
EGG_FRAME = {'lt': 'egglefttop', 'lb': 'eggleftbottom',
             'rt': 'eggrighttop', 'rb': 'eggrightbottom'}

WOLF = {'wolfleft': (90, 70), 'wolfright': (129, 71)}
BASKET = {'baskettopleft': (69, 70), 'basketbottomleft': (66, 103),
          'baskettopright': (170, 73), 'basketbottomright': (165, 109)}
RABBIT = {'rabbit': (42, -2)}
CHICKEN = {
    'chickenleft0': (50, 147), 'chickenleft1': (45, 128),
    'chickenleft2': (33, 130), 'chickenleft3': (18, 132),
    'chickenleft4': (9, 131),
    'chickenright0': (182, 146), 'chickenright1': (194, 134),
    'chickenright2': (215, 134), 'chickenright3': (225, 133),
    'chickenright4': (237, 134),
}
LIFE = [(136, 22), (157, 22), (179, 22)]
DIGIT_X = [149, 164, 179, 194]
DIGIT_Y = -5


def all_positions():
    """frame -> [(x, y), ...]; у одного кадра может быть несколько мест."""
    pos = {}
    for groove, pts in EGG_SLOTS.items():
        for i, p in enumerate(pts):
            pos[f'{EGG_FRAME[groove]}{i}'] = [p]
    pos.update({k: [v] for k, v in WOLF.items()})
    pos.update({k: [v] for k, v in BASKET.items()})
    pos.update({k: [v] for k, v in RABBIT.items()})
    pos.update({k: [v] for k, v in CHICKEN.items()})
    pos['life'] = list(LIFE)
    for d in '0123456789':
        pos[d] = [(x, DIGIT_Y) for x in DIGIT_X]
    return pos


# ===========================================================================
# Спрайтовые маски
# ===========================================================================

def load_frames():
    with open(ATLAS_JSON) as f:
        js = json.load(f)
    return {fr['filename']: fr['frame'] for fr in js['frames']}


FRAMES = load_frames()
ATLAS = Image.open(ATLAS_PNG).convert('RGBA')


def sprite_size(frame):
    return (max(1, round(frame['w'] / SCALE)),
            max(1, round(frame['h'] / SCALE)))


def mask_of(name):
    """Бинарный контур кадра атласа, приведённый к 1x.

    Порог «тёмный/не тёмный» применяется к исходнику в 2.2x, усреднение
    BOX-ом считает долю площади пикселя, занятую штрихом, а 0.5 отбирает
    пиксели, где штрих занял больше половины. Так линия не обрастает
    полутеном интерполяции и не рассыпается на диагоналях.
    """
    fr = FRAMES[name]
    a = ATLAS.crop((fr['x'], fr['y'], fr['x'] + fr['w'], fr['y'] + fr['h']))
    ap = a.load()
    d = Image.new('L', a.size)
    dp = d.load()
    for y in range(a.height):
        for x in range(a.width):
            r, g, b, al = ap[x, y]
            luma = (r * 0.3 + g * 0.59 + b * 0.11) / 255.0
            dp[x, y] = 255 if (al > 127 and luma < 0.5) else 0
    w, h = sprite_size(fr)
    cov = d.resize((w, h), Image.BOX)
    cp = cov.load()
    return {(i, j) for j in range(h) for i in range(w) if cp[i, j] >= 128}, w, h


def srow(y):
    """Строка поля -> строка экрана. Отрицательные y попадают в «головку»."""
    return y + FIELD_TOP


def rect_of(x, y, w, h):
    """Выровненный по байту прямоугольник на ЭКРАНЕ: x0, y0, ширина в байтах,
    высота.

    Колонка VRAM несёт 8 пикселей строки, так что по горизонтали спрайт
    можно поставить только с шагом 8. Сдвиг зашивается в сами данные.
    Обрезка — по полосе поля [BAND_TOP, BAND_BOT): за нижнюю границу поля
    сегменты не заходят, там панель. По горизонтали сегмент не должен
    перелезать за блок 31 (x=256): иначе блиттер уйдёт за конец плоскости.
    """
    x0 = x & ~7
    wb = min((SCR_W - x0 + 7) // 8, (x + w - x0 + 7) // 8)
    y0 = max(BAND_TOP, srow(y))
    y1 = min(BAND_BOT, srow(y + h))
    return x0, y0, wb, y1 - y0


def pack_rect(pts, x, y, w, h):
    """Битмапа (wb*h) байт: сначала колонка 0 сверху вниз, затем колонка 1...

    Порядок байт совпадает с порядком адресов в VRAM при обходе одного
    блока, поэтому блиттер идёт по ROM и по памяти линейно.
    """
    x0, y0, wb, hh = rect_of(x, y, w, h)
    rows = [0] * (wb * hh)
    for (i, j) in pts:
        sy = srow(y + j)
        b = x + i - x0
        if sy < y0 or sy >= y0 + hh or b < 0 or b >= wb * 8:
            continue
        rows[(sy - y0) * wb + (b >> 3)] |= 0x80 >> (b & 7)
    # колоночный порядок: (r, c) -> c*hh + r
    cols = [0] * (wb * hh)
    for r in range(hh):
        for c in range(wb):
            cols[c * hh + r] = rows[r * wb + c]
    return x0, y0, wb, hh, bytes(cols)


# ===========================================================================
# Панель под полем: кнопки управления и рамки под подписи клавиш
# ===========================================================================

BTN_W, BTN_H = 32, 20                # кнопка-клавиша
BTN_XL = 6                           # левый край левой пары
BTN_XR = SCR_W - BTN_W - BTN_XL      # ... и правой, зеркально = 218
LBL_W = 48                           # рамка под подпись клавиши (5 знаков)
LBL_XL = BTN_XL + BTN_W + 4          # = 42
LBL_XR = SCR_W - LBL_XL - LBL_W      # = 166, зеркально левой
BAND_A_Y = PANEL_TOP + 4             # верхний ряд кнопок = 196
BAND_B_Y = PANEL_TOP + 28            # нижний ряд кнопок = 220

# action -> (кнопка, рамка подписи). Порядок повторяет экран: левый верхний
# жёлоб — левая верхняя кнопка, правый нижний — правая нижняя.
UI_SLOTS = (((BTN_XL, BAND_A_Y), (LBL_XL, BAND_A_Y)),
            ((BTN_XL, BAND_B_Y), (LBL_XL, BAND_B_Y)),
            ((BTN_XR, BAND_A_Y), (LBL_XR, BAND_A_Y)),
            ((BTN_XR, BAND_B_Y), (LBL_XR, BAND_B_Y)))

# Стрелка 5x5: остриё в левый верхний угол, хвост по диагонали вправо-вниз.
ARROW_NW = ('11100', '11000', '10100', '00100', '00010')
ARROWS = ('nw', 'sw', 'ne', 'se')
ARROW_SHAPES = {
    'nw': ARROW_NW,
    'sw': ARROW_NW[::-1],                        # остриё в левый нижний угол
    'ne': tuple(r[::-1] for r in ARROW_NW),      # ... и зеркально по горизонтали
    'se': tuple(r[::-1] for r in ARROW_NW[::-1]),
}


def draw_frame(grid, x, y, w, h, slot):
    """Тонкая рамка w x h: верхняя и нижняя линии, левая и правая."""
    for i in range(w):
        grid[y][x + i] = slot
        grid[y + h - 1][x + i] = slot
    for j in range(h):
        grid[y + j][x] = slot
        grid[y + j][x + w - 1] = slot


def build_panel(grid):
    """Четыре клавиши по углам поля и четыре рамки для подписей.

    Две слева и две справа, одна над другой — как жёлобы, которые они
    двигают. Внутри рамки подписи ROM рисует название назначенной клавиши,
    поэтому её внутренний контур обязан оставаться чёрным: draw_char обнуляет
    все активные плоскости, кроме своей, и рамка под текстом исчезнет.
    """
    for (btn, lbl), arrow in zip(UI_SLOTS, ARROWS):
        draw_frame(grid, btn[0], btn[1], BTN_W, BTN_H, SLOT_GHOST)
        shape = ARROW_SHAPES[arrow]
        ax = btn[0] + (BTN_W - len(shape[0])) // 2
        ay = btn[1] + (BTN_H - len(shape)) // 2
        for j, row in enumerate(shape):
            for i, ch in enumerate(row):
                if ch == '1':
                    grid[ay + j][ax + i] = SLOT_WHITE
        draw_frame(grid, lbl[0], lbl[1], LBL_W, BTN_H, SLOT_GHOST)


# ===========================================================================
# Фон
# ===========================================================================

def load_ground():
    """Фото поля, приведённое к 256x184 усреднением по площади.

    Кроп захватывает и «головку» — 8 строк над верхней границей поля, где на
    ЖКИ рисуются уши зайца и табло счёта.
    """
    im = Image.open(GROUND).convert('RGB')
    y0 = round(FIELD_Y - HEADROOM * SYC)
    field = im.crop((FIELD_X, y0, FIELD_X + FIELD_W, FIELD_Y + FIELD_H))
    return field.resize((ARENA_W, BAND_BOT - BAND_TOP), Image.BOX)


def build_background():
    """Слотовая карта экрана 256x256: панель, заливка, декор и призраки.

    Строки вне поля [0, BAND_TOP) и [BAND_BOT, SCR_H) остаются SLOT_OUT —
    чёрные, кроме панели, которую дорисовывает build_panel().
    """
    g = load_ground()
    gp = g.load()
    grid = [[SLOT_OUT] * SCR_W for _ in range(SCR_H)]
    for y in range(BAND_TOP, BAND_BOT):
        for x in range(SCR_W):
            r, gr, b = gp[x, y - BAND_TOP]
            luma = r * 0.3 + gr * 0.59 + b * 0.11
            if min(r, gr, b) >= WHITE_MIN:
                grid[y][x] = SLOT_WHITE
            elif luma >= FIELD_MIN:
                grid[y][x] = SLOT_FIELD
            elif luma > DARK_MAX:
                grid[y][x] = SLOT_BROWN
            else:
                grid[y][x] = SLOT_DARK

    # Призраки — из тех же масок, что и сегменты: совпадение гарантировано.
    for name, places in all_positions().items():
        if name not in FRAMES:
            continue
        pts, w, h = mask_of(name)
        for (x, y) in places:
            x0, y0, wb, hh = rect_of(x, y, w, h)
            for (i, j) in pts:
                sx, sy = x + i, srow(y + j)
                if sx >= SCR_W or sy < y0 or sy >= y0 + hh:
                    continue
                if grid[sy][sx] == SLOT_FIELD:
                    grid[sy][sx] = SLOT_GHOST

    build_panel(grid)
    return grid


def write_bmp4(path, width, height, grid, palette):
    """4-битный BMP без сжатия, bottom-up, палитра BGRA.

    В BMP старший ниббл байта — ЛЕВЫЙ пиксель (так же читает parse_bmp и так
    же смотрит любой viewer). Если перепутать местами, картинка поедет парами
    по горизонтали: фон это единственные данные, которые проходят через BMP.
    """
    stride = ((4 * width + 31) // 32) * 4
    pixels = bytearray()
    for y in range(height - 1, -1, -1):
        row = bytearray()
        for x in range(0, width, 2):
            hi = grid[y][x]
            lo = grid[y][x + 1] if x + 1 < width else 0
            row.append((hi << 4) | lo)
        row.extend(b'\x00' * (stride - len(row)))
        pixels.extend(row)
    pal = b''.join(struct.pack('<BBBB', b, g, r, 0) for r, g, b in
                   [vector_rgb(palette[i]) for i in range(16)])
    off = 14 + 40 + len(pal)
    with open(path, 'wb') as f:
        f.write(b'BM' + struct.pack('<IHHI', off + len(pixels), 0, 0, off))
        f.write(struct.pack('<IiiHHIIiiII', 40, width, height, 1, 4, 0,
                            len(pixels), 0, 0, 16, 0))
        f.write(pal)
        f.write(pixels)


def read_bmp4(path):
    w, h, rows, pal = B.parse_bmp(path)
    grid = [list(r) for r in rows]
    vecpal = [B.to_vector_color(*c) for c in pal]
    vecpal += [0x00] * (16 - len(vecpal))
    return w, h, grid, vecpal


# ===========================================================================
# Потоки в ROM
# ===========================================================================

def plane_stream(grid, width, height):
    """24 КБ плоскостей 8,4,2 в порядке адресов VRAM 0x8000..0xDFFF.

    Внутри блока адреса растут вниз экрана, поэтому строки идут снизу вверх:
    смещение 0 в блоке — это y=255, смещение 255 — y=0.
    """
    out = bytearray()
    for bit in (3, 2, 1):
        for xb in range(32):
            for i in range(256):
                y = 255 - i
                byte = 0
                if y < height and xb * 8 < width:
                    for b in range(8):
                        x = xb * 8 + b
                        if x < width and (grid[y][x] >> bit) & 1:
                            byte |= 0x80 >> b
                out.append(byte)
    return bytes(out)


def c_array(name, data, comment=''):
    lines = [f'static const unsigned char {name}[{len(data)}] = '
             f'{{{comment}\n']
    for i in range(0, len(data), 16):
        lines.append('    ' + ', '.join(f'0x{v:02X}' for v in
                                        data[i:i + 16]) + ',\n')
    lines.append('};\n')
    return ''.join(lines)


def c_ident(name):
    return ('spr_digit' + name) if name.isdigit() else 'spr_' + name


def emit_bg(grid, width, height, pal):
    stream = plane_stream(grid, width, height)
    packed = zx0.compress(stream)
    assert zx0.decompress(packed) == stream, 'ZX0 round-trip не сошёлся'
    out = ["""/*
 * bg.inc — фон экрана «Ну, погоди!» (Вектор-06Ц).
 *
 * СГЕНЕРИРОВАНО tools/gen_assets.py — правки здесь сгорают при пересборке,
 * картинку правила в src/back.bmp и перегенерируй:
 *     python3 tools/gen_assets.py inc
 *
 * bg_zx0 — плоскости с весами 8, 4, 2 в порядке адресов видеопамяти,
 * то есть поток ложится ровно в 0x8000..0xDFFF и распаковывается туда
 * одним вызовом zx0_decompress(). Плоскость веса 1 (0xE000) в фоне
 * пуста по построению: все фоновые слоты чётные. Её обнуляют заливанием.
 */
""",
            'static const unsigned char bg_palette[16] = {\n']
    for i, byte in enumerate(pal):
        role = ('вне поля' if i == SLOT_OUT else
                'заливка' if i == SLOT_FIELD else
                'призраки' if i == SLOT_GHOST else
                'декор кусты' if i == SLOT_DARK else
                'декор забор' if i == SLOT_BROWN else
                'декор куры' if i == SLOT_WHITE else 'СЕГМЕНТ')
        r, g, b = vector_rgb(byte)
        out.append(f'    V06_RGB({(r * 7 + 127) // 255},'
                   f'{(g * 7 + 127) // 255},{(b * 3 + 127) // 255}),  '
                   f'/* {i:2d}: 0x{byte:02X} — {role} */\n')
    out.append('};\n\n')
    out.append(c_array('bg_zx0', packed,
                       f'  /* {len(stream)} КБ сырых -> {len(packed)} */'))
    return ''.join(out)


def emit_sprites():
    out = ["""/*
 * sprites.inc — битмапы сегментов «Ну, погоди!» (Вектор-06Ц).
 *
 * СГЕНЕРИРОВАНО tools/gen_assets.py — не править руками.
 *
 * Формат каждого массива: 4 байта заголовка и затем wb*h байт данных.
 *   [0] x0  — левый край прямоугольника, кратен 8
 *   [1] y0  — верхняя строка
 *   [2] wb  — ширина в байтах (по 8 пикселей)
 *   [3] h   — высота в строках
 * Данные — колонки одна за другой: внутри колонки строки сверху вниз,
 * то есть в том же порядке, в котором идут адреса внутри блока VRAM.
 * Старший бит байта — левый пиксель.
 *
 * Это маски для плоскости веса 1 (0xE000): показать сегмент — OR, стереть
 * — AND-NOT теми же байтами. Сжатия нет: данные пишутся из ROM в VRAM
 * линейно, и блиттеру не на что тратить такты.
 */
"""]
    total = 0
    for name, places in sorted(all_positions().items()):
        if name not in FRAMES:
            continue
        pts, w, h = mask_of(name)
        for n, (x, y) in enumerate(places):
            x0, y0, wb, hh, data = pack_rect(pts, x, y, w, h)
            total += 4 + wb * hh
            ident = c_ident(name)
            if len(places) > 1:
                ident += f'_{n}'
            out.append(f'/* {name} @ ({x},{y}) поля -> экран y={srow(y)} '
                       f'{w}x{h} -> rect {wb}B x {hh}r */\n')
            out.append(c_array(ident, bytes([x0, y0, wb, hh]) + data))
            out.append('\n')
    out.append(f'/* итого сегментных данных: {total} байт */\n')
    return ''.join(out), total


# ===========================================================================
# Режимы
# ===========================================================================

def do_back():
    grid = build_background()
    write_bmp4(BACK_BMP, SCR_W, SCR_H, grid, palette16())
    print(f'{BACK_BMP}: {SCR_W}x{SCR_H}, '
          f'{len({v for r in grid for v in r})} слотов')


def do_inc():
    w, h, grid, bmp_pal = read_bmp4(BACK_BMP)
    with open(BG_INC, 'w') as f:
        f.write(emit_bg(grid, w, h, bmp_pal))
    text, total = emit_sprites()
    with open(SPR_INC, 'w') as f:
        f.write(text)
    st = plane_stream(grid, w, h)
    print(f'{BG_INC}: фон {len(st)} сырых -> '
          f'{len(zx0.compress(st))} ZX0')
    print(f'{SPR_INC}: сегменты {total} байт (без сжатия)')


def do_preview():
    w, h, grid, bmp_pal = read_bmp4(BACK_BMP)
    out = Image.new('RGB', (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            op[x, y] = vector_rgb(bmp_pal[grid[y][x]])
    out.resize((w * 3, h * 3), Image.NEAREST).save(PREVIEW)
    print(f'{PREVIEW}')


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('all', 'back'):
        do_back()
    if what in ('all', 'inc'):
        do_inc()
    if what in ('all', 'preview'):
        do_preview()


if __name__ == '__main__':
    main()
