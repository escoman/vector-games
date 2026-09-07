/*
 * dt2_512.c — тест вывода картинки в режиме 512x256 Вектора-06Ц.
 *
 * Загружает RLE-сжатую 2-цветную картинку из dt2_512_bmp.inc,
 * выводит на экран в режиме 512x256 и ждёт клавиши ESC.
 *
 * Режим 512x256 (2 цвета):
 *   - порт 02h, бит 4 = 1
 *   - графические плоскости:
 *       plane 1 (A000h): бит 1
 *       plane 0 (E000h): бит 0
 *   - 8000h+C000h — данные программы (невидимы через палитру)
 */

#include "v06.h"
#include "dt2_512_bmp.inc"

/* RLE-распаковка: плоскость 1 (A000h) + плоскость 0 (E000h) (graphrle512.asm) */
extern void graph_rle_expand_512(const unsigned char *src);

int main(void)
{
    gfx_set_mode(GFX_MODE_512_2);
    gfx_set_palette(dt2_512_bmp_palette);
    /* Распаковываем картинку (плоскости A000h + E000h) */
    graph_rle_expand_512(dt2_512_bmp_screen_rle);
    
    while(1);

    return 0;
}
