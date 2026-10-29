/*
 * main.c — spr-demo: проверка работоспособности стандартных ядер спрайтов
 * lib/gfx/spr.asm (spr_init / spr_blit / spr_blit_mask) в 256x256x16.
 *
 * Две полосы экрана демонстрируют два способа вывода одного и того же
 * спрайта-«инопланетянина» (24×24, 3 столбца, плоскости П1+П0):
 *
 *   Верхняя полоса (шахматка в П0): spr_blit_mask — OR-композит
 *   dst = (dst AND mask) OR color. Маска не стирает прошлые позиции,
 *   поэтому фон восстанавливается перерисовкой шахматки КАЖДЫЙ кадр
 *   (как fill_checker в spr-speed). Прорезь рта показывает шахматку
 *   насквозь — для маски отдельный erase не нужен.
 *
 *   Нижняя полоса (вертикальные полоски в П1): spr_blit — плоская запись.
 *   Каждый кадр прошлая позиция затирается дескриптором-ящиком inv_erase,
 *   затем спрайт рисуется на новом месте. Ящик пишет нули, поэтому в
 *   полосатом фоне за спрайтом остаются прорехи — наглядно видно, что
 *   плоский блит фон не сохраняет и требует отдельного стирания.
 *
 * Кадровая синхронизация — gfx_next_frame() (HALT до VBlank). Палитра —
 * mario-dbl: 0=голубой, 1=красный, 2=розовый, 3=чёрный; текст — фоновые
 * плоскости (0x0C), цвет 4 (белый).
 */

#include "v06.h"
#include "spr.inc"

/* Полосы фона (координаты — пиксели, x кратен 8). */
#define CHK_Y    40u   /* верх шахматной полосы (растровые строки)   */
#define CHK_H    48u   /* высота: 6 клеток 8x8                       */
#define CHK_X    16u   /* левый край шахматки                        */
#define CHK_W    6u    /* клеток по горизонтали (48 пикс)            */

#define STR_Y    112u  /* верх полосатой полосы                      */
#define STR_H    48u
#define STR_X    80u
#define STR_W    6u

#define SPR_W    24u   /* спрайт: ширина, пикс  */
#define SPR_H    24u   /* спрайт: высота, пикс   */

static unsigned char pal16[16] = {
    0xEB, 0x07, 0xF7, 0x00,   /* 0..3: небо/красный/розовый/чёрный */
    0xFF, 0xFF, 0xFF, 0xFF,   /* 4..7: белые (текст)               */
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00
};

#define PLANE0  ((unsigned char *)0xE000u)
#define PLANE1  ((unsigned char *)0xC000u)

/* Адрес байта (x/8 = столбец, y = строка) в плоскости: адреса убывают вниз. */
#define CELL(p, col, y) \
    ((p)[(unsigned int)(255u - (y)) + ((unsigned int)(col) << 8)])

/* Шахматная клетка 8x8 в П0: чётная клетка — slot 0, нечётная — slot 1. */
static void draw_checker(unsigned char x0, unsigned char y0,
                         unsigned char w, unsigned char h) {
    unsigned char col, row;
    for (col = 0; col < w; col++)
        for (row = 0; row < h; row++)
            CELL(PLANE0, x0 / 8u + col, y0 + row) =
                (((y0 + row) / 8u + col) & 1u) ? 0xFFu : 0x00u;
}

/* Вертикальные полоски 2px (0xCC) в П1: slot 0 / slot 2. */
static void draw_stripes(unsigned char x0, unsigned char y0,
                         unsigned char w, unsigned char h) {
    unsigned char col, row;
    for (col = 0; col < w; col++)
        for (row = 0; row < h; row++)
            CELL(PLANE1, x0 / 8u + col, y0 + row) = 0xCCu;
}

int main(void) {
    signed char mdx = 2;                    /* маск-спрайт: шаг вправо     */
    signed char sdx = -2;                   /* плоский спрайт: шаг влево  */
    unsigned char mx = CHK_X;               /* текущий x маск-спрайта     */
    unsigned char px;                       /* прошлый x плоского спрайта */
    unsigned char sx = STR_X + STR_W * 8u - SPR_W;
    unsigned char frame = 0;

    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_palette(pal16);
    gfx_fill_planes(0x0F, 0x00);            /* весь экран = slot 0 */

    spr_init();                             /* лесенки -> 0x7000/0x7100 */

    draw_checker(CHK_X, CHK_Y, CHK_W, CHK_H);
    draw_stripes(STR_X, STR_Y, STR_W, STR_H);

    /* Заголовки (фоновые плоскости, цвет 4). */
    gfx_active_planes = 0x0C;
    gfx_print(1, 8, "SPR-DEMO: LIB SPR KERNELS", 4);
    gfx_print(CHK_X / 8u, 32, "SPR_BLIT_MASK: NO ERASE", 4);
    gfx_print(STR_X / 8u, 104, "SPR_BLIT: ERASE+DRAW", 4);
    gfx_active_planes = 0x0F;

    px = sx;
    for (;;) {
        unsigned char phase = (frame >> 2) % 3;  /* фаза ходьбы: 4 кадра */

        gfx_next_frame();                       /* HALT до VBlank */

        /* Маска: перерисовать шахматку, затем композит на новом месте
         * (ядро само прошлые позиции не стирает). */
        draw_checker(CHK_X, CHK_Y, CHK_W, CHK_H);
        mx += mdx;
        if (mx <= CHK_X || mx >= CHK_X + CHK_W * 8u - SPR_W)
            mdx = -mdx;
        spr_blit_mask(mx, CHK_Y + 12u, inv_frames_mask[phase]);

        /* Плоский: стереть прошлую позицию, нарисовать новую. */
        sx += sdx;
        if (sx <= STR_X || sx >= STR_X + STR_W * 8u - SPR_W)
            sdx = -sdx;
        if (frame != 0)                         /* первый кадр стирать нечего */
            spr_blit(px, STR_Y + 12u, inv_erase);
        spr_blit(sx, STR_Y + 12u, inv_frames_flat[phase]);
        px = sx;

        frame++;
    }
    return 0;
}
