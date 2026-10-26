#!/usr/bin/env python3
# ============================================================================
# gen_logo.py — генератор карты логотипа заставки RANDOM PUTUP (Stage 3).
#
# Кладёт в карту логотипа ПОТОКОВУЮ графику, нарисованную заказчиком
# (см. ART_WHITE / ART_RED ниже), а не шрифт из FONT: так буквы выглядят
# ровно как в согласованном эскизе.
#
#   * RANDOM -> белый шарик 0x9D (в эскизе символ 'X')
#   * PUTUP  -> красный шарик 0x9B (в эскизе символ 'O')
#   * пусто   -> 0x20 (пробел)
#
# RANDOM — 4 ряда, затем 1 пустой ряд-разделитель, PUTUP — 5 рядов.
# Итого 10 рядов карты. Оба блока 24 колонки шириной, центрируются в
# 32-колоночной полосе (одинаковый левый отступ => левые края выровнены).
#
# Запуск предпросмотра:  python3 gen_logo.py
# Генерация asm:         python3 gen_logo.py --asm > ../overlay/data/str_title_logo.asm
# ============================================================================
import sys

BALL_RED = 0x9B    # красный шарик (PUTUP)
BALL_WHITE = 0x9D  # белый шарик (RANDOM)
SPACE = 0x20
TERM = 0xFF
COLS = 32

# --- эскиз логотипа (ровно как согласован) ---------------------------------
# RANDOM — белые шарики, 4 ряда.
ART_WHITE = [
    "XXX  X  X X XX  XXX X  X",
    "X X X X XX  X X X X XXXX",
    "XX  XXX  XX X X X X X  X",
    "X X X X X X XX  XXX X  X",
]
# PUTUP — красные шарики, 5 рядов.
ART_RED = [
    "OOO  OO O OOOO OO O OOO",
    "OO O OO O  OO  OO O OO O",
    "OO O OO O  OO  OO O OO O",
    "OOO  OO O  OO  OO O OOO",
    "OO    OO   OO   OO  OO",
]
BLANK = 1          # пустой ряд-разделитель между RANDOM и PUTUP
ROWS = len(ART_WHITE) + BLANK + len(ART_RED)   # 4 + 1 + 5 = 10


def _width(art):
    return max(len(r) for r in art)


def place(canvas, art, top_row, color):
    """Положить блок art в canvas[top_row..], центрируя по COLS (levый край = LEFT)."""
    for r, line in enumerate(art):
        for c, ch in enumerate(line):
            if ch != ' ':
                canvas[top_row + r][LEFT + c] = color


def build():
    width = max(_width(ART_WHITE), _width(ART_RED))
    global LEFT
    LEFT = (COLS - width) // 2
    canvas = [[SPACE] * COLS for _ in range(ROWS)]
    place(canvas, ART_WHITE, 0, BALL_WHITE)
    place(canvas, ART_RED, len(ART_WHITE) + BLANK, BALL_RED)
    return canvas


def preview(canvas):
    for row in canvas:
        print(''.join('#' if b == BALL_RED else ('O' if b == BALL_WHITE else ' ') for b in row))


def emit_asm(canvas):
    flat = [b for row in canvas for b in row] + [TERM]
    print("; Данные: str_title_logo  (RANDOM PUTUP overlay — ЗАМЕНА заставки, Stage 3)")
    print("; Карта логотипа 10 рядов x 32 кол.: RANDOM (0x9D белый, 4 ряда) +")
    print("; пустая строка + PUTUP (0x9B красный, 5 рядов). Потковая графика по")
    print("; эскизу заказчика. Сгенерировано tools/gen_logo.py — не править руками.")
    print("str_title_logo:")
    for i in range(0, len(flat), 16):
        chunk = flat[i:i + 16]
        print("    DEFB " + ", ".join("0%02Xh" % b for b in chunk))


if __name__ == "__main__":
    LEFT = 0
    c = build()
    if "--asm" in sys.argv:
        emit_asm(c)
    else:
        preview(c)
