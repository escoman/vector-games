#!/usr/bin/env python3
"""gen_assets.py — ассеты игры «Ну, погоди!» для Вектора-06Ц.

Изображение оригинала (src/ground.png — фото аркадного «Ну, погоди!» с ЖКИ-
панелью) перекладывается на экран 256x256 Вектора в 16 цветов. Масштаб поля
2.2, левый верхний угла поля (262, 168).

Раскладка экрана по строкам:

     0..11   строка функциональных клавиш (в фоне чёрная, текст рисует ROM)
   12..27    «головка» поля: на ЖКИ заячьи уши и табло счёта стоят ВЫШЕ
             верхней границы поля, поэтому у координат спрайтов бывает
             отрицательный y — эти 16 строк и дают им место, а заодно
             верхняя кромка поля (крыша домика) перестаёт обрезаться
   28..203   поле (256x176, масштабированный кроп фотографии)
  204..255   панель: круглые красные кнопки по углам (рядом — чёрные
             стрелки и подписи клавиш), в середине логотип «Ну, погоди!»

Спрайты и их призраки задаются в координатах ПОЛЯ (y=0 — верхняя граница
поля на фото); FIELD_TOP сдвигает на экран и фон, и спрайты, поэтому призрак
на фоне и сегмент в плоскости веса 1 совпадают пиксель в пиксель.

Итоговая схема палитры (см. также main.c):

    бит 0 (плоскость 0xE000) — СЕГМЕНТЫ, то есть нарисованные объекты.
    Фон занимает только чётные слоты, так что бит 0 в фоне сброшен ВЕЗДЕ.
    Показать объект = OR его битмапы в 0xE000, стереть = AND-NOT теми же
    байтами: возвращаются ровно биты фона, никаких нейтральных патчей и
    теневых буферов не нужно.

    слот  биты  что                        цвет
      0   0000  вне поля (чёрная рамка)    0x00
      2   0010  заливка арены              0xAD
      4   0100  призраки сегментов         0xA4
      6   0110  декор: заборы, насесты     0x13
      8   1000  декор: куры, логотип       0xFF
     10   1010  декор: кусты, травинки     0x12
     12   1100  декор: крыша, кирпичи,     0x07
                        гребешки кур
      нечётные     сегменты                0x00

Заливка оригинала — диагональные полосы «небо / трава / арена» с плавным
переходом; на Векторе они дают шесть едва различимых оттенков и съедают
палитру, поэтому сводится к одному тону. Настоящие цвета декора при этом
разделяются надёжно: после усреднения BOX-ом в источнике остаются (44,56,13)
кусты, (108,75,33) заборы, (141,26,29) красная черепица и гребешки,
(236,236,236) куры и континуум 153..196 яркости, в который попадают и полосы,
и серые призраки.

Призраки НЕ извлекаются из фотографии — они рисуются из тех же масок, которые
потом идут сегментами, поэтому совпадают с объектами пиксель в пиксель.

Использование (пайплайн):
    gen_assets.py screen    # src/screen.bmp из ground.png (без призраков);
                            #   существующий НЕ перезаписывает (кроме --force)
    gen_assets.py sprites   # src/sprites/*.bmp из атласа sprites.png;
                            #   существующие НЕ перезаписывает (кроме --force)
    gen_assets.py inc       # screen.bmp + sprites/*.bmp -> bg.inc и sprites.inc;
                            #   исходники не трогает. Призраки спрайтов на фон
                            #   НЕ накладываются (так bg.inc компактнее) — их
                            #   возвращает флаг --ghosts
    gen_assets.py preview   # preview.png — как фон будет выглядеть в ROM
                            #   (без призраков; --ghosts добавляет их)
    gen_assets.py           # = screen + sprites + inc + preview (безопасно)

--ghosts — наложить призраки спрайтов на фон в inc/preview (по умолчанию
выключено). --force — пересоздать исходники screen/sprites, затерев правку.

screen.bmp и src/sprites/*.bmp — ИСХОДНИКИ, их правит человек (GIMP). Их
никогда не перезаписывает сборка ROM: только ручные цели screen/sprites с
явным --force. Финальная палитра — в main.c (bg_palette[]), не здесь.
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
SPRITE_DIR = os.path.join(SRC, 'sprites')   # спрайты 1x, правятся руками
SCREEN_BMP = os.path.join(SRC, 'screen.bmp')  # чистое поле + панель, без призраков
BG_INC = os.path.join(SRC, 'bg.inc')
SPR_INC = os.path.join(SRC, 'sprites.inc')
PREVIEW = os.path.join(SRC, 'preview.png')

SCALE = 2.2
ARENA_W, ARENA_H = 256, 176       # поле в пикселях экрана
FIELD_X, FIELD_Y = 262, 168       # левый верхний угол поля на ground.png
FIELD_W, FIELD_H = 571, 371       # размер поля на ground.png (~2.23 x 2.11)
SCR_W, SCR_H = 256, 256           # холст = весь экран: поток плоскостей
                                  # ложится в 0x8000..0xDFFF без «дыр»
MENU_H = 12                       # строка Ф-клавиш сверху
HEADROOM = 16                     # строк над полем: уши зайца, табло счёта
                                  # и верхняя кромка крыши (не обрезается)
FIELD_TOP = MENU_H + HEADROOM     # экранная строка y=0 поля = 28
BAND_TOP = FIELD_TOP - HEADROOM   # 12: выше поля ничего не рисуем
BAND_BOT = FIELD_TOP + ARENA_H    # 204: нижняя граница поля (исключительно)
PANEL_TOP = BAND_BOT              # 204: панель кнопок и логотипа

SXC = FIELD_W / ARENA_W           # масштаб фотографии по горизонтали
SYC = FIELD_H / ARENA_H           # ... и по вертикали

# --- пороги классификации фона (зазоры между кластерами > 50 яркости) -----
WHITE_MIN = 215                    # min(R,G,B): куры 236, небо 196
DARK_MAX = 55                      # средняя яркость: кусты 38, забор 72
FIELD_MIN = 128                    # ниже — декор, выше — заливка/призраки
RED_MIN = 105                      # R крышной черепицы 141, коричневого 108
RED_DRG = 45                       # R-G и R-B: у красного 115, у коричневого 33

# --- слоты палитры и их цвета ---------------------------------------------
SLOT_OUT = 0
SLOT_FIELD = 2
SLOT_GHOST = 4
SLOT_BROWN = 6
SLOT_WHITE = 8
SLOT_DARK = 10
SLOT_RED = 12
SLOT_INK = 1

BG_COLORS = {
    SLOT_OUT: 0x00,
    SLOT_FIELD: 0xAD,
    SLOT_GHOST: 0xA4,
    SLOT_BROWN: 0x13,
    SLOT_WHITE: 0xFF,
    SLOT_DARK: 0x12,
    SLOT_RED: 0x07,
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
    'lt': [(21, 43), (30, 50), (42, 54), (51, 61), (59, 72)],
    'lb': [(22, 86), (31, 91), (39, 98), (50, 102), (58, 110)],
    'rt': [(225, 40), (216, 44), (205, 51), (195, 59), (189, 65)],
    'rb': [(224, 84), (216, 91), (205, 97), (196, 103), (187, 107)],
}
EGG_FRAME = {'lt': 'egglefttop', 'lb': 'eggleftbottom',
             'rt': 'eggrighttop', 'rb': 'eggrightbottom'}

WOLF = {'wolfleft': (90, 70), 'wolfright': (129, 71)}
BASKET = {'baskettopleft': (69, 70), 'basketbottomleft': (66, 103),
          'baskettopright': (168, 73), 'basketbottomright': (163, 109)}
RABBIT = {'rabbit': (42, -2)}
CHICKEN = {
    'chickenleft0': (50, 147), 'chickenleft1': (45, 128),
    'chickenleft2': (33, 130), 'chickenleft3': (18, 132),
    'chickenleft4': (9, 131),
    'chickenright0': (180, 146), 'chickenright1': (194, 134),
    'chickenright2': (215, 134), 'chickenright3': (225, 133),
    'chickenright4': (237, 134),
}
LIFE = [(136, 22), (157, 22), (179, 22)]
DIGIT_X = [149, 164, 179, 194]
DIGIT_Y = -5

# Разбитое яйцо (последний кадр жёлоба, где его ловят/бьют) и выбегающие
# цыплята спускаются на несколько строк вниз: на прежних местах они налазят
# на траву. Отсюда координаты попадают и в заголовок blob-а живого спрайта,
# и в призраки фона, поэтому и то и то сдвигается разом.
BROKEN_EGG_DROP = 4
CHICKEN_DROP = 4


def all_positions():
    """frame -> [(x, y), ...]; у одного кадра может быть несколько мест."""
    pos = {}
    for groove, pts in EGG_SLOTS.items():
        last = len(pts) - 1
        for i, (x, y) in enumerate(pts):
            if i == last:                 # разбитое яйцо — последний кадр
                y += BROKEN_EGG_DROP
            pos[f'{EGG_FRAME[groove]}{i}'] = [(x, y)]
    pos.update({k: [v] for k, v in WOLF.items()})
    pos.update({k: [v] for k, v in BASKET.items()})
    pos.update({k: [v] for k, v in RABBIT.items()})
    pos.update({k: [(x, y + CHICKEN_DROP)] for k, (x, y) in CHICKEN.items()})
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


_ATLAS = {}


def atlas():
    """Лениво грузит атлас — он нужен только бутстрапу src/sprites/*.bmp.
    На сборке .inc атлас не требуется: спрайты читаются из готовых BMP."""
    if not _ATLAS:
        _ATLAS['frames'] = load_frames()
        _ATLAS['img'] = Image.open(ATLAS_PNG).convert('RGBA')
    return _ATLAS['img'], _ATLAS['frames']


def _mask_from_atlas(name):
    """Бинарный контур кадра атласа, приведённый к 1x (только бутстрап).

    Порог «тёмный/не тёмный» применяется к исходнику в 2.2x, усреднение
    BOX-ом считает долю площади пикселя, занятую штрихом, а 0.5 отбирает
    пиксели, где штрих занял больше половины. Так линия не обрастает
    полутеном интерполяции и не рассыпается на диагоналях.
    """
    at, frames = atlas()
    fr = frames[name]
    a = at.crop((fr['x'], fr['y'], fr['x'] + fr['w'], fr['y'] + fr['h']))
    ap = a.load()
    d = Image.new('L', a.size)
    dp = d.load()
    for y in range(a.height):
        for x in range(a.width):
            r, g, b, al = ap[x, y]
            luma = (r * 0.3 + g * 0.59 + b * 0.11) / 255.0
            dp[x, y] = 255 if (al > 127 and luma < 0.5) else 0
    w = max(1, round(fr['w'] / SCALE))
    h = max(1, round(fr['h'] / SCALE))
    cov = d.resize((w, h), Image.BOX)
    cp = cov.load()
    return {(i, j) for j in range(h) for i in range(w) if cp[i, j] >= 128}, w, h


def sprite_path(name):
    return os.path.join(SPRITE_DIR, name + '.bmp')


def mask_of(name):
    """Контур спрайта 1x из src/sprites/<name>.bmp: множество тёмных пикселей.

    BMP — итоговое разрешение (WYSIWYG): что нарисовано, то и ляжет на экран.
    Тёмный пиксель (luma < 128) — чернила сегмента, светлый — пусто. Из этого
    же контура рисуются и призраки на фоне, поэтому призрак и сегмент
    совпадают пиксель в пиксель.
    """
    path = sprite_path(name)
    if not os.path.exists(path):
        raise SystemExit(f'нет спрайта {path} — сначала: make sprites')
    im = Image.open(path).convert('L')
    w, h = im.size
    p = im.load()
    return {(i, j) for j in range(h) for i in range(w) if p[i, j] < 128}, w, h


def write_sprite_bmp(path, pts, w, h):
    """Двуцветный BMP спрайта 1x: чернила — чёрный (0), фон — белый (255).

    8-битный grayscale: значения байтов читаются обратно один-в-один, без
    палитры (индексный 'P' BMP при чтении отдаёт сырые индексы вместо яркости).
    """
    im = Image.new('L', (w, h), 255)
    p = im.load()
    for (i, j) in pts:
        p[i, j] = 0
    im.save(path)


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
# Панель под полем: красные кнопки управления и логотип в середине
# ===========================================================================

PANEL_H = SCR_H - PANEL_TOP            # 52 строки

# Круглые кнопки, как в оригинале: светлый обод, красная середина и чёрная
# стрелка-указатель на ободе, направленная в свой угол поля.
BTN_RB = 12                            # радиус светлого обода
BTN_RR = 5                             # радиус красной кнопки
BTN_CX_L = 20                          # центр левой пары
BTN_CX_R = SCR_W - BTN_CX_L            # ... и правой, зеркально = 236
BTN_CY_A = PANEL_TOP + 12              # центр верхнего ряда = 216
BTN_CY_B = PANEL_TOP + 36              # центр нижнего ряда = 240
# Вынос стрелки по каждой оси. Стрелка стоит на диагонали, поэтому её центр
# уходит от центра кнопки на BTN_ARROW*sqrt(2) ~ 8.5 — в середину кольца
# между красной серединой (BTN_RR) и ободом (BTN_RB): чёрная стрелка видна на
# светлом ободе и не залезает ни в краску кнопки, ни в чёрный фон панели.
BTN_ARROW = 6                          # вынос стрелки от центра кнопки
LOGO_RAISE = 6                         # логотип поднимаем над центром панели

# Подписи клавиш ROM рисует текстом у внутреннего края: левые в колонках
# 5..9, правые в 22..26 (согласовано с ui_key_col/ui_key_y в main.c). Между
# ними (x 84..171) — место под логотип.

# action -> центр кнопки и направление стрелки. Порядок: левый верхний
# жёлоб — левая верхняя кнопка (↖), левый нижний — ↙, правые — ↗ ↘.
BUTTONS = ((BTN_CX_L, BTN_CY_A, 'nw'), (BTN_CX_L, BTN_CY_B, 'sw'),
           (BTN_CX_R, BTN_CY_A, 'ne'), (BTN_CX_R, BTN_CY_B, 'se'))

# Стрелка 5x5: остриё в левый верхний угол, хвост по диагонали вправо-вниз.
ARROW_NW = ('11100', '11000', '10100', '00100', '00010')
ARROW_SHAPES = {
    'nw': ARROW_NW,
    'sw': ARROW_NW[::-1],                        # остриё в левый нижний угол
    'ne': tuple(r[::-1] for r in ARROW_NW),      # ... и зеркально по горизонтали
    'se': tuple(r[::-1] for r in ARROW_NW[::-1]),
}

# Куда смотрит стрелка вокруг центра кнопки (единичные векторы угла поля).
ARROW_DX = {'nw': -1, 'sw': -1, 'ne': 1, 'se': 1}
ARROW_DY = {'nw': -1, 'sw': 1, 'ne': -1, 'se': 1}

LOGO_PNG = os.path.join(SRC, 'logo.png')
LOGO_X0, LOGO_X1 = 84, 172             # горизонтальные границы логотипа


def draw_circle(grid, cx, cy, r, slot):
    """Заливной круг радиуса r с центром (cx, cy)."""
    r2 = r * r
    for j in range(cy - r, cy + r + 1):
        if not (0 <= j < SCR_H):
            continue
        for i in range(cx - r, cx + r + 1):
            if 0 <= i < SCR_W and (i - cx) ** 2 + (j - cy) ** 2 <= r2:
                grid[j][i] = slot


def draw_button(grid, cx, cy, arrow):
    """Круглая клавиша: светлый обод, красная середина, чёрная стрелка.

    Стрелка лежит на ободе (вынос BTN_ARROW между радиусом красной середины и
    обода) и смотрит в свой угол поля. Чёрная (SLOT_OUT) — видна на светлом
    ободе; на красной середине её рисовать нельзя, там она бы пропала.
    """
    draw_circle(grid, cx, cy, BTN_RB, SLOT_GHOST)   # светлый обод
    draw_circle(grid, cx, cy, BTN_RR, SLOT_RED)     # красная кнопка
    shape = ARROW_SHAPES[arrow]
    ax = cx + ARROW_DX[arrow] * BTN_ARROW - len(shape[0]) // 2
    ay = cy + ARROW_DY[arrow] * BTN_ARROW - len(shape) // 2
    for j, row in enumerate(shape):
        for i, ch in enumerate(row):
            if ch == '1' and 0 <= ay + j < SCR_H and 0 <= ax + i < SCR_W:
                grid[ay + j][ax + i] = SLOT_OUT      # чёрная стрелка


def draw_logo(grid):
    """«Ну, погоди!» из src/logo.png — растер в центр панели.

    Кириллицу шрифт 8x8 не выводит, поэтому заголовок ложится в фон
    битмапом: чёрные знаки на белом поле становятся пикселями SLOT_WHITE.
    Логотип поднимаем над центром панели на LOGO_RAISE.
    """
    im = Image.open(LOGO_PNG).convert('L')
    tw = LOGO_X1 - LOGO_X0
    th = max(1, round(im.height * tw / im.width))
    im = im.resize((tw, th), Image.LANCZOS)
    p = im.load()
    y0 = PANEL_TOP + (PANEL_H - th) // 2 - LOGO_RAISE
    for j in range(th):
        for i in range(tw):
            if p[i, j] < 128:
                grid[y0 + j][LOGO_X0 + i] = SLOT_WHITE


def build_panel(grid):
    """Две круглые кнопки слева и две справа, логотип между ними.

    Подписи клавиш в фон не попадают — их ROM рисует текстом у внутреннего
    края кнопки, поэтому между кнопкой и логотипом обязана быть чёрная
    полоса: draw_char обнуляет под знаком все активные плоскости, кроме
    своей, и текст, вставший на кнопку или логотип, съел бы их.
    """
    for (cx, cy, arrow) in BUTTONS:
        draw_button(grid, cx, cy, arrow)
    draw_logo(grid)


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


def build_screen_grid():
    """Слотовая карта экрана 256x256: заливка, декор и панель — БЕЗ призраков.

    Это содержимое src/screen.bmp, которое правится руками. Строки вне поля
    [0, BAND_TOP) и [BAND_BOT, SCR_H) остаются SLOT_OUT — чёрные, кроме
    панели, которую дорисовывает build_panel().
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
            elif r >= RED_MIN and r - gr >= RED_DRG and r - b >= RED_DRG:
                grid[y][x] = SLOT_RED          # черепица, кирпичи, гребешки
            elif luma >= FIELD_MIN:
                grid[y][x] = SLOT_FIELD
            elif luma > DARK_MAX:
                grid[y][x] = SLOT_BROWN
            else:
                grid[y][x] = SLOT_DARK

    build_panel(grid)
    return grid


def add_ghosts(grid):
    """Наложить призраки сегментов поверх чистого поля (только на заливку).

    Призрак — светлый контур (SLOT_GHOST) там, где стоит спрайт. Рисуется из
    тех же масок src/sprites/*.bmp, что и сегменты, поэтому совпадает с
    объектами пиксель в пиксель. Заменяет только заливку SLOT_FIELD: декор
    (кирпичи, заборы, куры) под спрайтами остаётся как есть.
    """
    for name, places in all_positions().items():
        pts, w, h = mask_of(name)
        for (x, y) in places:
            x0, y0, wb, hh = rect_of(x, y, w, h)
            for (i, j) in pts:
                sx, sy = x + i, srow(y + j)
                if sx >= SCR_W or sy < y0 or sy >= y0 + hh:
                    continue
                if grid[sy][sx] == SLOT_FIELD:
                    grid[sy][sx] = SLOT_GHOST


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


def emit_bg(grid, width, height):
    stream = plane_stream(grid, width, height)
    packed = zx0.compress(stream)
    assert zx0.decompress(packed) == stream, 'ZX0 round-trip не сошёлся'
    out = ["""/*
 * bg.inc — фон экрана «Ну, погоди!» (Вектор-06Ц).
 *
 * СГЕНЕРИРОВАНО tools/gen_assets.py — правки здесь сгорают при пересборке.
 * Картинку правила в src/screen.bmp (чистое поле) и src/sprites/*.bmp
 * (спрайты). Призраки спрайтов на фон по умолчанию НЕ накладываются
 * (так bg.inc компактнее); включить их — `make inc GHOSTS=1`, затем:
 *     make inc
 *
 * bg_zx0 — плоскости с весами 8, 4, 2 в порядке адресов видеопамяти, то есть
 * поток ложится ровно в 0x8000..0xDFFF и распаковывается туда одним вызовом
 * zx0_decompress(). Плоскость веса 1 (0xE000) в фоне пуста по построению:
 * все фоновые слоты чётные, её обнуляют заливанием.
 *
 * ПАЛИТРА ЗДЕСЬ НЕ ЗАДАЁТСЯ — финальные цвета слотов определяет main.c
 * (массив bg_palette[] из V06_RGB), чтобы править цвета без перегенерации
 * ассетов. Индексы (слоты) фиксированы генератором:
 *   0 вне поля · 2 заливка · 4 призраки · 6 заборы · 8 куры/лого ·
 *  10 кусты · 12 черепица; нечётные — чернила сегментов (всегда 0xE000).
 */
""",
            c_array('bg_zx0', packed,
                    f'  /* {len(stream)} КБ сырых -> {len(packed)} */')]
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

FORCE = '--force' in sys.argv
# Призраки спрайтов на фоне ПО УМОЛЧАНИЮ ОТКЛЮЧЕНЫ: они съедают место в
# ZX0-пакованном bg.inc, а в игре сегменты рисуются поверх чистого поля и без
# них. Флаг --ghosts возвращает наложение (для preview/сравнения). Касается
# только do_inc()/do_preview(): screen.bmp всегда чистое поле без призраков,
# а светлые ободки кнопок панели (SLOT_GHOST) рисуются в build_panel() и от
# этого флага не зависят.
GHOSTS = '--ghosts' in sys.argv


def do_screen():
    """src/screen.bmp — чистое поле + панель, без призраков.

    Существующий файл НЕ перезаписывает (правки руками в безопасности),
    кроме явного --force.
    """
    if os.path.exists(SCREEN_BMP) and not FORCE:
        print(f'  есть {SCREEN_BMP} — не трогаю (--force пересоздаст)')
        return
    grid = build_screen_grid()
    write_bmp4(SCREEN_BMP, SCR_W, SCR_H, grid, palette16())
    print(f'  wrote {SCREEN_BMP}: {SCR_W}x{SCR_H}, '
          f'{len({v for r in grid for v in r})} слотов (без призраков)')


def do_sprites():
    """src/sprites/*.bmp — спрайты 1x из атласа. Каждый файл создаётся раз и
    больше не перезаписывается (кроме --force), чтобы правки не пропали."""
    os.makedirs(SPRITE_DIR, exist_ok=True)
    names = sorted(all_positions())
    made = skip = 0
    for name in names:
        path = sprite_path(name)
        if os.path.exists(path) and not FORCE:
            skip += 1
            continue
        pts, w, h = _mask_from_atlas(name)
        write_sprite_bmp(path, pts, w, h)
        made += 1
    print(f'  src/sprites: новых {made}, уже было {skip} '
          f'(всего {len(names)}; --force пересоздаст все)')


def do_inc():
    """screen.bmp + src/sprites/*.bmp -> bg.inc и sprites.inc.

    Призраки спрайтов на фон накладываются только с --ghosts (по умолчанию
    фон чистый — так bg.inc компактнее). Исходники только читаются:
    screen.bmp и спрайты не трогаются."""
    w, h, grid, bmp_pal = read_bmp4(SCREEN_BMP)
    if GHOSTS:
        add_ghosts(grid)
    with open(BG_INC, 'w') as f:
        f.write(emit_bg(grid, w, h))
    text, total = emit_sprites()
    with open(SPR_INC, 'w') as f:
        f.write(text)
    st = plane_stream(grid, w, h)
    print(f'  {BG_INC}: фон {len(st)} сырых -> '
          f'{len(zx0.compress(st))} ZX0 '
          f'({"призраки наложены" if GHOSTS else "без призраков"})')
    print(f'  {SPR_INC}: сегменты {total} байт (без сжатия)')


def do_preview():
    """preview.png — как будет выглядеть фон в ROM (screen.bmp; призраки —
    только с --ghosts, чтобы preview совпадал с собранным bg.inc)."""
    w, h, grid, bmp_pal = read_bmp4(SCREEN_BMP)
    if GHOSTS:
        add_ghosts(grid)
    out = Image.new('RGB', (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            op[x, y] = vector_rgb(bmp_pal[grid[y][x]])
    out.resize((w * 3, h * 3), Image.NEAREST).save(PREVIEW)
    print(f'  {PREVIEW}')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    what = args[0] if args else 'all'
    if what in ('all', 'screen'):
        do_screen()
    if what in ('all', 'sprites'):
        do_sprites()
    if what in ('all', 'inc'):
        do_inc()
    if what in ('all', 'preview'):
        do_preview()


if __name__ == '__main__':
    main()
