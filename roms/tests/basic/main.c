/*
 * roms/tests/basic/main.c — вывод текста шрифтом BASIC (5x8, СТОЛБЦАМИ).
 *
 * Демонстрирует алгоритм, восстановленный из живого BASIC (см.
 * roms/redesign/basic/tools/trace_glyph.py): шрифт хранится вертикальными
 * колонками, а кадр Вектора — горизонтальными байтами (1 байт = 8 пикселей,
 * бит7 = левый), поэтому между ними нужен поворот на 90°. Главное, что
 * проверяет этот тест: горизонтальное позиционирование — ПОПИКСЕЛЬНОЕ,
 * глиф можно поставить на любой X, а не только кратный 8 байту.
 *
 * Формат глифа basic_font (128 x 5):
 *   байт col (0..4)  = вертикальная колонка символа;
 *   бит0 = верхний пиксель строки ряда, бит7 = нижний;
 *   колонок 5, высота 8 (верхняя строка обычно пустая — межстрочный зазор),
 *   значит видимая часть 5x7.
 *
 * Адресация кадра 256x256 (режим GFX_MODE_256_2, активна плоскость 0xE000):
 *   адрес пикселя (X,Y) = 0xE000 + (X/8)*0x100 + (255 - Y).
 *
 * Рисование одного столбца глифа:
 *   X  = x0 + col                      (x0 — пиксельный левый край символа)
 *   байт колонки  = X/8,  бит внутри   = 7 - (X%8)   (бит7 = самый левый)
 *   для каждого установленного бита row: Y = y0 + row, ставим этот бит
 *   в нужном байте — то есть разворачиваем вертикальный run колонок в
 *   отдельные байты строки. Если X глифа пересекает границу байта, соседние
 *   колонки попадают в разные байты — именно это и даёт точность до пикселя.
 *
 * ТАБ — переключить режим шага ячейки (6 px как в BASIC / 8 px ровно).
 * АП2 (ESC) — выход.
 */

#include "v06.h"

/* Шрифт BASIC — метка _basic_font в basic_font.asm (генератор tools/gen_font.py). */
extern const unsigned char basic_font[];

#define FONT_COLS   5
#define CELL_BASIC  6       /* как в терминале BASIC: шаг 6 px, глиф 5 px + 1 зазор */
#define CELL_STRAIGHT 8     /* ровно байт: глифы не наезжают друг на друга          */

/* 2 цвета: слот 0 — фон (чёрный), слот 1 — чернила (белый). */
static const unsigned char pal2[2] = {
    V06_RGB(0, 0, 0),
    V06_RGB(7, 7, 3),
};

/* Плоскость в режиме 256x256x2 — только 0xE000 (вес бита 0). */
#define PLANE       0xE000u

/* ---------------------------------------------------------------
 * Поставить один символ: transpose колонок шрифта в пиксели кадра.
 *   x0, y0 — пиксельный левый-верхний угол символа (X не кратен 8 — можно).
 * --------------------------------------------------------------- */
static void bx_put_char(unsigned int x0, unsigned int y0, unsigned char code)
{
    unsigned char col, row;
    const unsigned char *g = basic_font + (unsigned int)code * FONT_COLS;

    for (col = 0; col < FONT_COLS; col++) {
        unsigned char bits = g[col];
        unsigned int  X, byte_col;
        unsigned char mask;
        unsigned char *base;

        if (bits == 0)
            continue;                       /* пустая колонка — ничего не ставим */

        X        = x0 + col;
        byte_col = X >> 3;                  /* номер байта-колонки (X/8)          */
        mask     = 0x80 >> (X & 7);         /* бит внутри байта, бит7 = левый      */
        base     = (unsigned char *)(PLANE + byte_col * 0x100u);

        for (row = 0; row < 8; row++) {
            if (bits & (1 << row))          /* бит0 = верхняя строка               */
                base[255u - (y0 + row)] |= mask;
        }
    }
}

/* Строка с заданным шагом ячейки (в пикселях). */
static void bx_print(unsigned int x0, unsigned int y0, const char *s,
                     unsigned int cell)
{
    unsigned int x = x0;
    while (*s) {
        bx_put_char(x, y0, (unsigned char)*s);
        x += cell;
        s++;
    }
}

/* ---------------------------------------------------------------
 * Полоса фаз: одна и та же строка, сдвинутая на 0..7 пикселей.
 * Видно, что глиф встаёт в любой битовый сдвиг внутри байта.
 * --------------------------------------------------------------- */
static void draw_phase(unsigned int y_top)
{
    static const char word[] = "VECTOR06C";
    unsigned char o;
    unsigned int y = y_top;

    for (o = 0; o < 8; o++) {
        bx_put_char(0, y, (unsigned char)('0' + o));   /* метка фазы */
        bx_print(16 + o, y, word, CELL_STRAIGHT);      /* строка со сдвигом o */
        y += 9;
    }
}

static void draw_screen(unsigned int cell)
{
    static const char head[]  = "BASIC FONT 5X8 COLUMNS";
    static const char sub[]   = "TRANSPOSE + PIXEL X";
    static const char pang[]  = "THE QUICK BROWN FOX JUMPS 0123456789";
    unsigned int y;
    unsigned char i;

    gfx_clear(0);

    bx_print(4, 2, head, cell);
    bx_print(4, 12, sub, cell);

    /* Весь набор 0x20..0x7F (96 глифов) сеткой 32 x 3. */
    y = 26;
    for (i = 0; i < 96; i++) {
        unsigned int x = 4 + (i % 32) * cell;
        unsigned int yy = y + (i / 32) * 9;
        bx_put_char(x, yy, (unsigned char)(0x20 + i));
    }

    /* Панграмма — читаемая строка. */
    bx_print(4, 62, pang, cell);

    /* Полоса фаз 0..7 — попиксельное позиционирование. */
    draw_phase(76);

    /* Подпись режима шага. */
    bx_print(4, 156, (cell == CELL_BASIC) ? "CELL=6 (BASIC OVERLAP)"
                                          : "CELL=8 (BYTE ALIGNED)", cell);
    bx_print(4, 168, "TAB-CELL  ESC-EXIT", cell);
}

int main(void)
{
    unsigned int cell = CELL_BASIC;
    unsigned char prev, key;

    gfx_set_mode(GFX_MODE_256_2);
    gfx_set_palette(pal2);

    draw_screen(cell);

    prev = kbd_scan();

    for (;;) {
        v06_wait_frame();

        key = kbd_scan();
        if (key == 0) {
            prev = 0;
            continue;
        }
        if (key == prev)
            continue;
        prev = key;

        if (key == KBD_KEY_ESC)
            break;

        if (key == KBD_KEY_TAB) {
            cell = (cell == CELL_BASIC) ? CELL_STRAIGHT : CELL_BASIC;
            draw_screen(cell);
        }
    }

    gfx_clear(0);
    return 0;
}
