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

/* Очистка графических плоскостей (A000h-BFFFh + E000h-FFFFh, 16 КБ) */
static void graph_clear_512(void)
{
    unsigned char *p;
    for (p = (unsigned char *)0xA000; p < (unsigned char *)0xC000; p++)
        *p = 0;
    for (p = (unsigned char *)0xE000; p != (unsigned char *)0; p++)
        *p = 0;
}

/* RLE-распаковка: плоскость 1 (A000h) + плоскость 0 (E000h) (graphrle512.asm) */
extern void graph_rle_expand_512(const unsigned char *src);

/* Палитра для 2-цветного режима 512×256 (плоскости A000h + E000h). */
static unsigned char _pal16[16];

static void _build_palette(void)
{
    unsigned char bg = dt2_512_bmp_palette[0];
    unsigned char fg = dt2_512_bmp_palette[1];

    _pal16[0] = bg;
    _pal16[1] = fg;
    _pal16[2] = bg;
    _pal16[3] = fg;
    _pal16[4] = fg;
    _pal16[5] = bg; 
    _pal16[6] = bg; 
    _pal16[7] = bg; 
    _pal16[8] = bg;
    _pal16[9] = bg;
    _pal16[10] = bg;
    _pal16[11] = bg;
    _pal16[12] = fg;
    _pal16[13] = bg;
    _pal16[14] = bg;
    _pal16[15] = bg;
}



/* Переключение в режим 512x256 */
static void graph_set_mode_512(void)
{
#asm
        di
        ld      a, 0x88
        out     (0x00), a           ; ПИА (сбрасывает PA/PB/PC в 0)
        ld      a, 0xFF
        out     (0x03), a           ; скролл = 0xFF (компенсация направления)
        ld      a, 0x10
        out     (0x02), a           ; Режим 512x256
        ei
#endasm
}

int main(void)
{
    /* Формируем и загружаем палитру */
    _build_palette();
    v06_set_palette_asm(_pal16);

    /* Переключаем в 512x256 */
    graph_scroll_row = 0xFF;       /* скролл: верхняя строка = FF */
    graph_set_mode_512();

    /* Очищаем графические плоскости */
    graph_clear_512();

    /* Распаковываем картинку (плоскости A000h + E000h) */
    graph_rle_expand_512(dt2_512_bmp_screen_rle);
    
    /* Ждём ESC */
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
