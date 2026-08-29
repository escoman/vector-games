/*
 * dt2_bmp_lz/main.c — тест LZ-распаковки картинки на Векторе-06Ц.
 *
 * Загружает LZ-сжатую картинку из dt2_bmp.inc (256x240, 16 цветов,
 * конвертирована bmp2inc_lz.py), выводит на чёрный экран и ждёт ESC.
 */

#include "v06.h"
#include "../assets/dt2_bmp.inc"

/* LZ-распаковщик (lib/graphlz.asm) */
extern void graph_lz_expand(const unsigned char *src);

int main(void)
{
    /* Рисуем на чёрном экране. */
    //graph_set_black_palette();
    graph_clear(0);
    graph_lz_expand(dt2_bmp_screen_lz);
    graph_set_palette(dt2_bmp_palette);

    while(1);

    return 0;
}
