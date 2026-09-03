/*
 * scr_modes.c — тест переключения видеорежимов Вектора-06Ц.
 *
 * Стартует в режиме 0 (256x256, 16 цветов). Выводит меню со списком
 * всех поддерживаемых режимов (0-3). По нажатию клавиши 0-3
 * переключает режим, очищает экран и выводит меню заново.
 *
 * Для 256x256 используется graph_print (шрифт 8x8, pr.asm).
 * Для 512x256 — graph_print_512 (шрифт 16x8, pr512.asm)
 * и graph_print_512t (тонкий шрифт 4x8, pr512t.asm).
 */

#include "v06.h"
#include "../assets/logo16_bmp.inc"

/* ---------------------------- Палитры ------------------------------ */

/* 16-цветная палитра для режима 0 (256x256).
 * 0  — чёрный фон;
 * 1-5  — оттенки красного;
 * 6-10 — оттенки зелёного;
 * 11-13 — оттенки синего;
 * 14 — серый, 15 — белый. */
static const unsigned char pal16[16] = {
    V06_RGB(0,0,0),  /*  0: чёрный (фон)   */
    V06_RGB(1,0,0),  /*  1: 0x20 тёмно-красный   */
    V06_RGB(3,0,0),  /*  2: 0x60 красный          */
    V06_RGB(4,0,0),  /*  3: 0x80 средне-красный   */
    V06_RGB(6,0,0),  /*  4: 0xC0 ярко-красный     */
    V06_RGB(7,0,0),  /*  5: 0xE0 алый             */
    V06_RGB(0,1,0),  /*  6: 0x08 тёмно-зелёный   */
    V06_RGB(0,2,0),  /*  7: 0x10 зелёный          */
    V06_RGB(0,4,0),  /*  8: 0x20 средне-зелёный   */
    V06_RGB(0,6,0),  /*  9: 0x30 ярко-зелёный     */
    V06_RGB(0,7,0),  /* 10: 0x38 салатовый        */
    V06_RGB(0,0,1),  /* 11: 0x03 тёмно-синий      */
    V06_RGB(0,0,2),  /* 12: 0x06 синий            */
    V06_RGB(0,0,3),  /* 13: 0x09 голубой          */
    V06_RGB(3,3,1),  /* 14: серый           */
    V06_RGB(7,7,3),  /* 15: белый           */
};

/* 2-цветная палитра для режима 1 (256x256 2-color).
 * Плоскость: 0xE000. */
static const unsigned char pal2[2] = {
    V06_RGB(0,0,0),  /* 0: чёрный (фон) */
    V06_RGB(7,7,3),  /* 1: белый */
};

/* 4-цветная палитра для режима 2 (512x256 4-color).
 * Плоскости: bit0 → E000/A000, bit1 → C000/8000. */
static const unsigned char pal4[4] = {
    V06_RGB(0,0,0),  /* 0: чёрный (фон) */
    V06_RGB(7,0,0),  /* 1: красный (E000/A000) */
    V06_RGB(0,7,0),  /* 2: зелёный (C000/8000) */
    V06_RGB(7,7,3),  /* 3: белый (обе плоскости) */
};

/* 2-цветная палитра для режима 3 (512x256 2-color).
 * Плоскости: E000+A000 (нечётные пиксели). */
static const unsigned char pal2w[2] = {
    V06_RGB(0,0,0),  /* 0: чёрный (фон) */
    V06_RGB(7,7,3),  /* 1: белый (E000/A000) */
};

static void set_palette()
{
    /* Загружаем палитру (gfx_set_palette расширяет до 16 слотов) */
    switch (gfx_current_mode) {
    case GFX_MODE_256_16: gfx_set_palette(pal16); break;
    case GFX_MODE_256_2:  gfx_set_palette(pal2);  break;
    case GFX_MODE_512_4:  gfx_set_palette(pal4);  break;
    default:              gfx_set_palette(pal2w); break;
    }
}



/* Белый цвет для текущего режима. */
#define WHITE_16  15     /* 256x256 16-color */
#define WHITE_2   1      /* 256x256  2-color */
#define WHITE_4   3      /* 512x256  4-color */
#define WHITE_2w  1      /* 512x256  2-color */

static unsigned char getModeColor()
{
    /* Цвет текста: белый для текущего режима. */
    switch (gfx_current_mode) {
        case GFX_MODE_256_16: return WHITE_16;
        case GFX_MODE_256_2:  return WHITE_2;
        case GFX_MODE_512_4:  return WHITE_4;
        default:              return WHITE_2w;
    }
}

/* -------------------------- Образцы цветов ------------------------ */

/* Рисует образцы цветов 1..num_colors-1 (цвет 0 — фон) в виде
 * квадратов 8x8. Для 256x256 — прямая запись в VRAM (плоскости
 * идентичны 256-режиму). Для 512x256 — чётные столбцы из E000/C000,
 * нечётные из A000/8000. */
static void draw_swatches(void)
{
    unsigned char nc = gfx_modes[gfx_current_mode].num_colors;
    unsigned char c, row, col;
    unsigned char color = getModeColor();

    if (gfx_modes[gfx_current_mode].width_div8 <= 32) {
        /* 256x256: сетка 5×3, шаг 16 пикселей, сдвиг вниз на 16.
         * Блок 8x8 на (col*8, row*8): адрес = 0x8000 + xb*256 + (255-y). */
        for (c = 1; c < nc; c++) {
            col = (c - 1) % 5;
            row = (c - 1) / 5;
            {
                unsigned char xb = 21 + col * 2;  /* блоки 21-30 */
                unsigned char y0 = row * 2 + 2;   /* +16 пикселей */
                unsigned char i;
                for (i = 0; i < 8; i++) {
                    unsigned char addr = 255 - y0 * 8 - i;
                    if (c & 0x01) *((unsigned char *)0xE000 + xb * 256 + addr) = 0xFF;
                    if (c & 0x02) *((unsigned char *)0xC000 + xb * 256 + addr) = 0xFF;
                    if (c & 0x04) *((unsigned char *)0xA000 + xb * 256 + addr) = 0xFF;
                    if (c & 0x08) *((unsigned char *)0x8000 + xb * 256 + addr) = 0xFF;
                }
                xb++;
                for (i = 0; i < 8; i++) {
                    unsigned char addr = 255 - y0 * 8 - i;
                    if (c & 0x01) *((unsigned char *)0xE000 + xb * 256 + addr) = 0xFF;
                    if (c & 0x02) *((unsigned char *)0xC000 + xb * 256 + addr) = 0xFF;
                    if (c & 0x04) *((unsigned char *)0xA000 + xb * 256 + addr) = 0xFF;
                    if (c & 0x08) *((unsigned char *)0x8000 + xb * 256 + addr) = 0xFF;
                }
            }
        }
        graph_print(21, 0, "PALETTE", color);
    } else {
        /* 512x256: сетка 5×3, сдвиг вниз на 16 пикселей.
         * Чётные столбцы — E000/C000, нечётные — A000/8000.
         * На плоскость 32 столбца (0-31), не 64. */
        for (c = 1; c < nc; c++) {
            col = (c - 1) % 5;
            row = (c - 1) / 5;
            {
                unsigned char xb0 = 21 + col * 2;   /* чётный столбец */
                unsigned char xb1 = xb0 + 1;         /* нечётный столбец */
                unsigned char y0 = row * 2 + 2;   /* +16 пикселей */
                unsigned char i;
                for (i = 0; i < 8; i++) {
                    unsigned char addr = 255 - y0 * 8 - i;
                    if (c & 0x01) *((unsigned char *)0xE000 + xb0 * 256 + addr) = 0xFF;
                    if (c & 0x02) *((unsigned char *)0xC000 + xb0 * 256 + addr) = 0xFF;
                    if (c & 0x01) *((unsigned char *)0xA000 + xb1 * 256 + addr) = 0xFF;
                    if (c & 0x02) *((unsigned char *)0x8000 + xb1 * 256 + addr) = 0xFF;

                    if (c & 0x01) *((unsigned char *)0xA000 + xb0 * 256 + addr) = 0xFF;
                    if (c & 0x02) *((unsigned char *)0x8000 + xb0 * 256 + addr) = 0xFF;
                    if (c & 0x01) *((unsigned char *)0xE000 + xb1 * 256 + addr) = 0xFF;
                    if (c & 0x02) *((unsigned char *)0xC000 + xb1 * 256 + addr) = 0xFF;
                }
            }
        }
        graph_print_512(21, 0, "PALETTE", color);
    }
}

/* -------------------------- Рисование меню ------------------------- */

/* Элемент меню: текст и позиция в координатах режима. */
typedef struct {
    const char *text;
    unsigned char x;      /* пиксель (256) или символ (512) */
    unsigned char y;      /* пиксельная строка 0-255        */
    unsigned char t;      /* узкие символы, если возможно   */
} menu_item_t;

/* Общие тексты меню (одинаковые для всех режимов). */
static const char txt_title[]  = "VECTOR-06C";
static const char txt_sep[]    = "-------------------";
static const char txt_m0[]     = "0-256X256 16 COLORS";
static const char txt_m1[]     = "1-256X256  2 COLORS";
static const char txt_m2[]     = "2-512X256  4 COLORS";
static const char txt_m3[]     = "3-512X256  2 COLORS";
static const char txt_key[]    = "PRESS 0-3 FOR MODE";
static const char txt_image[]    = "PRESS SPACE FOR IMAGE";

static const char txt_test1[]  = "THE QUICK BROWN FOX";
static const char txt_test2[]  = "JUMPS OVER THE LAZY DOG";
static const char txt_test3[]  = "1234567890 A-Z TEST";
static const char txt_test4[]  = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char txt_test5[]  = "0123456789-:().,?!@<>=&#*+%";

/* Отрисовка одной строки меню через нужный шрифт. */
static void print_line(unsigned char x, unsigned char y,
                        const char *s, unsigned char t, unsigned char color)
{
    switch (gfx_current_mode) {
    case GFX_MODE_256_16:
    case GFX_MODE_256_2:
        graph_print(x, y, s, color);
        break;
    case GFX_MODE_512_4:
    case GFX_MODE_512_2:
        if (t)
            graph_print_512t(x, y, s, color);
        else
            graph_print_512(x, y, s, color);
        break;
    }
}

static void draw_menu(void)
{
    /* Координаты: x = символ/колонка, y = строка (в единицах 8px). */
    static const menu_item_t items[] = {
        { txt_title, 1,  0, 0 },
        { txt_sep,   1,  2, 0 },
        { txt_m0,    1,  4, 0 },
        { txt_m1,    1,  6, 0 },
        { txt_m2,    1,  8, 0 },
        { txt_m3,    1, 10, 0 },
        { txt_sep,   1, 12, 0 },
        { txt_key,   1, 14, 0 },
        { txt_image, 1, 16, 0 },
        { txt_test1, 1, 20, 1 },
        { txt_test2, 1, 21, 1 },
        { txt_test3, 1, 22, 1 },
        { txt_test4, 1, 24, 1 },
        { txt_test5, 1, 26, 1 },
    };

    unsigned char color = getModeColor();

    for (unsigned char i = 0; i < sizeof(items) / sizeof(items[0]); i++) {
        const menu_item_t *m = &items[i];
        print_line(m->x, m->y * 8, m->text, m->t, color);
    }

    /* Маркер '>' напротив текущего режима (y = 4 + mode * 2). */
    print_line(0, (4 + gfx_current_mode * 2) * 8, ">", 0, color);
}

/* ------------------------ Показ логотипа --------------------------- */

static void switch_mode(unsigned char mode);  /* опережающее объявление */

/* Показывает логотип для текущего режима (пока только 256x256x16).
 * Выводит "PRESS SPACE KEY" под картинкой и ждёт пробела.
 * По нажатию — возврат в меню через switch_mode. */
static void show_logo(void)
{
    unsigned char saved_mode = gfx_current_mode;

    graph_set_black_palette();
    gfx_clear(0);

    if (saved_mode == GFX_MODE_256_16) {
        /* Картинка 120x120, центрируем: x = (256-120)/8 = 17 (округлено до чётного) */
        graph_rle_expand(logo16_bmp_screen_rle, 64, 48);
        graph_set_palette(logo16_bmp_palette);
        graph_print(8, 176, "PRESS SPACE KEY", WHITE_16);
    } else {
        set_palette();
        graph_print(1, 200, "PRESS SPACE KEY", getModeColor());
    }

    /* Ждём пробела и возвращаемся в меню */
    kbd_wait_key(' ');

    switch_mode(saved_mode);
}

/* ------------------------ Переключение режима ---------------------- */

static void switch_mode(unsigned char mode)
{
    graph_set_black_palette();

    /* Переключаем аппарат: для 512x256 — ПИА + скролл, для 256x256 —
     * не трогаем (аппаратный режим по умолчанию). */
    gfx_set_mode(mode);

    /* Очищаем все плоскости (включая мусор от предыдущего режима) */
    gfx_clear(0);

    /* Рисуем меню и образцы цветов */
    draw_menu();
    draw_swatches();

    set_palette();
}

/* ------------------------------- Main ------------------------------ */

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;

    /* Начальный режим: 256x256, 16 цветов (аппаратный по умолчанию) */
    switch_mode(0);

    /* Основной цикл: опрос клавиатуры */
    for (;;) {
        key = kbd_scan();

        if (key != 0 && key != prev_key) {
            switch (key) {
            case '0': switch_mode(0); break;
            case '1': switch_mode(1); break;
            case '2': switch_mode(2); break;
            case '3': switch_mode(3); break;
            case ' ': show_logo();  break;
            }
        }

        prev_key = key;
    }

    return 0;
}
