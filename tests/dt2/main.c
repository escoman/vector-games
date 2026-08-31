/*
 * dt2.c — тест вывода картинки на экран Вектора-06Ц.
 *
 * Загружает RLE-сжатую картинку из dt2_bmp.inc
 * (256x240, 16 цветов, конвертирована bmp2inc.py), выводит
 * на чёрный экран и ждёт клавиши ESC.
 */

#include "v06.h"
#include "dt2_bmp.inc"

int main(void)
{
    /* Рисуем на чёрном экране: картинка не видна до загрузки палитры. */
    graph_set_black_palette();
    graph_clear(0);
    graph_rle_expand(dt2_bmp_screen_rle, 0, 0);
    graph_set_palette(dt2_bmp_palette);

    /* Ждём ESC, опрашивая клавиатуру раз в кадр,
     * чтобы не дёргать порты ПИА непрерывно. */
    {
        unsigned int last_frame = frame_count;
        for (;;) {
            while (frame_count == last_frame)
                ;
            last_frame = frame_count;
            if (kbd_scan() == 27)
                break;
        }
    }

    return 0;
}
