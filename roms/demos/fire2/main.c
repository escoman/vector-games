/*
 * fire2.c — огонь для Вектора-06Ц.
 *
 * Вся логика (ГСЧ, буфер, генерация, рендеринг) — в fire.asm.
 * Здесь только инициализация графики и основной цикл.
 *
 * Размер буфера огня задаётся константами в fire.asm:
 *   FIRE_W  — ширина в пикселях (64)
 *   FIRE_H  — высота в пикселях (64)
 */

#include "v06.h"

/* ----------------------------- ПАЛИТРА --------------------------------
 * 16 цветов огня. Формат V06: BB_GGG_RRR.
 * 0 = чёрный (фон), 15 = белое пламя.
 * --------------------------------------------------------------- */

static const unsigned char fire_palette[16] = {
    V06_RGB(0, 0, 0),
    V06_RGB(1, 0, 0),
    V06_RGB(2, 0, 0),
    V06_RGB(3, 0, 0),
    V06_RGB(4, 0, 0),
    V06_RGB(5, 0, 0),
    V06_RGB(6, 0, 0),
    V06_RGB(7, 0, 0),
    V06_RGB(7, 1, 0),
    V06_RGB(7, 2, 0),
    V06_RGB(7, 3, 1),
    V06_RGB(7, 4, 1),
    V06_RGB(7, 5, 2),
    V06_RGB(7, 6, 2),
    V06_RGB(7, 7, 3),
    V06_RGB(7, 7, 3)
};

/* --- функции огня (fire.asm) --- */
extern void rnd_init(void) __z88dk_callee;
extern void fire_generate(unsigned char power) __z88dk_callee;
extern void fire_render(void) __z88dk_callee;

/* ----------------------------- MAIN ---------------------------------- */

int main(void)
{
    /* Инициализация: чёрный экран, палитра огня */
    graph_set_black_palette();
    gfx_clear(0);
    graph_set_palette(fire_palette);

    rnd_init();

    /* Основной цикл: генерация + отрисовка кадра огня (50 Гц) */
    for (;;) {
        gfx_next_frame();

        fire_generate(100);
        fire_render();
    }

    return 0;
}
