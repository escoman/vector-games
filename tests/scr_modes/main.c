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

/* --- Текст 256x256 (pr.asm) --- */
extern void graph_print(unsigned char x, unsigned char y, const char *s,
                        unsigned char color) __z88dk_callee;

/* --- Текст 512x256, шрифт 16x8 (pr512.asm) --- */
extern void graph_print_512(unsigned char x, unsigned char y, const char *s,
                            unsigned char color) __z88dk_callee;

/* --- Текст 512x256, тонкий шрифт 4x8 (pr512t.asm) --- */
extern void graph_print_512t(unsigned char x, unsigned char y, const char *s,
                             unsigned char color) __z88dk_callee;

/* --- Палитра (mode.c: gfx_set_palette расширяет до 16 слотов) --- */
/* extern void gfx_set_palette(const unsigned char *colors); -- уже в v06.h */

/* --------------------------- Таблица режимов ------------------------- */

typedef struct {
    unsigned char width_div8;
    unsigned char plane_mask;
    unsigned char num_colors;
} mode_info_t;

static const mode_info_t modes[] = {
    { 32, 0x0F, 16 },  /* 0: 256x256, 16 цветов */
    { 32, 0x01,  2 },  /* 1: 256x256,  2 цвета  */
    { 64, 0x0F,  4 },  /* 2: 512x256,  4 цвета  */
    { 64, 0x05,  2 },  /* 3: 512x256,  2 цвета  */
};

static unsigned char cur_mode = 0;

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

/* -------------------------- Образцы цветов ------------------------ */

/* Рисует образцы цветов 1..num_colors-1 (цвет 0 — фон) в виде
 * квадратов 8x8. Для 256x256 — прямая запись в VRAM (плоскости
 * идентичны 256-режиму). Для 512x256 — чётные столбцы из E000/C000,
 * нечётные из A000/8000. */
static void draw_swatches(void)
{
    unsigned char nc = modes[cur_mode].num_colors;
    unsigned char c, row, col;

    if (modes[cur_mode].width_div8 <= 32) {
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
        graph_print(21 * 8, 0, "PALETTE", 0x0F);
    } else {
        /* 512x256: сетка 5×3, сдвиг вниз на 16 пикселей.
         * Чётные столбцы — E000/C000, нечётные — A000/8000.
         * На плоскость 32 столбца (0-31), не 64. */
        for (c = 1; c < nc; c++) {
            col = (c - 1) % 5;
            row = (c - 1) / 5;
            {
                unsigned char xb0 = 12 + col * 4;   /* чётный столбец */
                unsigned char xb1 = xb0 + 1;         /* нечётный столбец */
                unsigned char y0 = row * 2 + 2;   /* +16 пикселей */
                unsigned char i;
                for (i = 0; i < 8; i++) {
                    unsigned char addr = 255 - y0 * 8 - i;
                    if (c & 0x01) *((unsigned char *)0xE000 + xb0 * 256 + addr) = 0xFF;
                    if (c & 0x02) *((unsigned char *)0xC000 + xb0 * 256 + addr) = 0xFF;
                    if (c & 0x01) *((unsigned char *)0xA000 + xb1 * 256 + addr) = 0xFF;
                    if (c & 0x02) *((unsigned char *)0x8000 + xb1 * 256 + addr) = 0xFF;
                }
            }
        }
        graph_print_512(24, 0, "PALETTE", 3);
    }
}

/* -------------------------- Рисование меню ------------------------- */

/* Элемент меню: текст и позиция в координатах режима. */
typedef struct {
    const char *text;
    unsigned char x;      /* пиксель (256) или символ (512) */
    unsigned char y;      /* пиксельная строка 0-255        */
} menu_item_t;

/* Общие тексты меню (одинаковые для всех режимов). */
static const char txt_title[]  = "VECTOR-06C";
static const char txt_sep[]    = "------------";
static const char txt_m0[]     = "0-256X256 16 COLORS";
static const char txt_m1[]     = "1-256X256  2 COLORS";
static const char txt_m2[]     = "2-512X256  4 COLORS";
static const char txt_m3[]     = "3-512X256  2 COLORS";
static const char txt_key[]    = "PRESS 0-3";
static const char txt_test1[]  = "THE QUICK BROWN";
static const char txt_test2[]  = "FOX JUMPS OVER";
static const char txt_test3[]  = "THE LAZY DOG";
static const char txt_test4[]  = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char txt_test5[]  = "0123456789-:().,?!@<>=&#*+%";

/* 512-режимы: более длинные тестовые строки (больше места). */
static const char txt_test1w[] = "THE QUICK BROWN FOX";
static const char txt_test2w[] = "JUMPS OVER THE LAZY DOG";
static const char txt_test3w[] = "1234567890 A-Z TEST";

/* Белый цвет для текущего режима. */
#define WHITE_16  0x0F   /* 256x256 16-color */
#define WHITE_2   1      /* 256x256  2-color */
#define WHITE_4   3      /* 512x256  4-color */
#define WHITE_2w  3      /* 512x256  2-color */

/* Отрисовка одной строки меню через нужный шрифт. */
static void print_line(unsigned char x, unsigned char y,
                        const char *s, unsigned char color)
{
    switch (cur_mode) {
    case GFX_MODE_256_16:
    case GFX_MODE_256_2:
        graph_print(x, y, s, color);
        break;
    case GFX_MODE_512_4:
        graph_print_512(x, y, s, color);
        break;
    default:
        graph_print_512t(x, y, s, color);
        break;
    }
}

static void draw_menu(void)
{
    /* Координаты: x = символ/колонка, y = строка (в единицах 8px). */
    static const menu_item_t items[] = {
        { txt_title, 1,  0 },
        { txt_sep,   1,  2 },
        { txt_m0,    1,  4 },
        { txt_m1,    1,  6 },
        { txt_m2,    1,  8 },
        { txt_m3,    1, 10 },
        { txt_sep,   1, 12 },
        { txt_key,   1, 14 },
        { txt_test4, 1, 24 },
        { txt_test5, 1, 26 },
    };
    unsigned char i, color;

    /* Цвет текста: белый для текущего режима. */
    switch (cur_mode) {
        case GFX_MODE_256_16: color = WHITE_16; break;
        case GFX_MODE_256_2:  color = WHITE_2;  break;
        case GFX_MODE_512_4:  color = WHITE_4;  break;
        default:              color = WHITE_2w; break;
    }

    for (i = 0; i < sizeof(items) / sizeof(items[0]); i++) {
        unsigned char px, py;
        const menu_item_t *m = &items[i];

        /* Пересчёт координат в пиксели/символы режима. */
        if (cur_mode <= GFX_MODE_256_2) {
            px = m->x * 8;        /* символы -> пиксели */
            py = m->y * 8;
        } else if (cur_mode == GFX_MODE_512_4) {
            px = m->x + 1;        /* сдвиг на 1 символ от края */
            py = m->y * 8;
        } else {
            px = m->x + 2;        /* тонкий шрифт: колонка */
            py = m->y * 8;
        }

        print_line(px, py, m->text, color);
    }

    /* Маркер '>' напротив текущего режима (y = 4 + mode * 2). */
    {
        unsigned char my = (4 + cur_mode * 2) * 8;
        print_line(0, my, ">", color);
    }

    /* 512-режимы: более длинные тестовые строки. */
    if (cur_mode >= GFX_MODE_512_4) {
        unsigned char ty = 17 * 8;
        if (cur_mode == GFX_MODE_512_4) {
            graph_print_512(1, ty,      txt_test1w, color);
            graph_print_512(1, ty + 8,  txt_test2w, color);
            graph_print_512(1, ty + 16, txt_test3w, color);
        } else {
            graph_print_512t(1, ty,      txt_test1w, color);
            graph_print_512t(1, ty + 8,  txt_test2w, color);
            graph_print_512t(1, ty + 16, txt_test3w, color);
        }
    } else {
        /* 256-режимы: короткие тестовые строки. */
        unsigned char ty = 17 * 8;
        graph_print(1, ty,      txt_test1, color);
        graph_print(1, ty + 8,  txt_test2, color);
        graph_print(1, ty + 16, txt_test3, color);
    }
}

/* ------------------------ Переключение режима ---------------------- */

static void switch_mode(unsigned char mode)
{
    cur_mode = mode;
    gfx_current_mode = mode;

    /* Переключаем аппарат: для 512x256 — ПИА + скролл, для 256x256 —
     * не трогаем (аппаратный режим по умолчанию). */
    gfx_set_mode(mode);

    /* Загружаем палитру (gfx_set_palette расширяет до 16 слотов) */
    switch (mode) {
    case GFX_MODE_256_16: gfx_set_palette(pal16); break;
    case GFX_MODE_256_2:  gfx_set_palette(pal2);  break;
    case GFX_MODE_512_4:  gfx_set_palette(pal4);  break;
    default:              gfx_set_palette(pal2w); break;
    }

    /* Очищаем все плоскости (включая мусор от предыдущего режима) */
    gfx_clear(0);

    /* Рисуем меню и образцы цветов */
    draw_menu();
    draw_swatches();
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
            }
        }

        prev_key = key;
    }

    return 0;
}
