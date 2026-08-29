/*
 * dt2_512.c — тест вывода картинки в режиме 512x256 Вектора-06Ц.
 *
 * Загружает RLE-сжатую 2-цветную картинку из dt2_512_bmp.inc,
 * выводит на экран в режиме 512x256 и ждёт клавиши ESC.
 *
 * Режим 512x256 (2 цвета):
 *   - порт 02h, бит 4 = 1
 *   - расширенная плоскость B (16 КБ):
 *       plane 1 (C000h): бит 1, нечётные X
 *       plane 0 (E000h): бит 0, чётные X
 *   - 0000h-BFFFh — обычное ОЗУ (48 КБ)
 *   - палитра: все ненулевые мат. цвета → цвет переднего плана
 */

#include "v06.h"
#include "dt2_512_bmp.inc"

/* Переключение в режим 512x256 (порт 02h, бит 4 = 1) */
static void graph_set_mode_512(void)
{
    /* Читаем текущее значение порта B (бордюр + режим) */
    unsigned char val = v06_in(V06_PIA_PB);
    /* Устанавливаем бит 4 (режим 512x256), сохраняя биты 0-3 (бордюр) */
    v06_out(V06_PIA_PB, val | 0x10);
}

/* Переключение в режим 256x256 (порт 02h, бит 4 = 0) */
static void graph_set_mode_256(void)
{
    unsigned char val = v06_in(V06_PIA_PB);
    v06_out(V06_PIA_PB, val & 0xEF);
}

/* Загрузка палитры для режима 512x256 (2 цвета).
 * Математические цвета 0-3, но используем только 0 и 1.
 * Для 2-цветного режима на плоскости B:
 *   - цвет 0 (00b) — фон
 *   - цвет 1 (01b) — передний план (бит 0 в плоскости 0)
 *   - цвета 2,3 (10b, 11b) — тоже передний план (для совместимости)
 */
/* asm-загрузчик палитры для 512x256 (4 слота, v06pal.asm) */
extern void v06_set_palette4_asm(const unsigned char *pal);

static void graph_set_palette_512(const unsigned char *pal)
{
    /* В режиме 512x256 (2 цвета) палитра имеет только 4 слота:
     * цвет 0 (00b) — фон, цвета 1-3 — передний план.
     * Загружаем 4 цвета через v06_set_palette4_asm, чтобы не
     * переполнить палитру и не затереть экранную память. */
    unsigned char full_pal[4];
    full_pal[0] = pal[0];  /* цвет 0 (00b) — фон */
    full_pal[1] = pal[1];  /* цвет 1 (01b) — передний план */
    full_pal[2] = pal[1];  /* цвет 2 (10b) — передний план */
    full_pal[3] = pal[1];  /* цвет 3 (11b) — передний план */
    v06_set_palette4_asm(full_pal);
}

/* Очистка экрана в режиме 512x256 (плоскость B: C000h-FFFFh, 16 КБ) */
static void graph_clear_512(void)
{
    /* Заливаем плоскость B нулём (16 КБ: C000h-FFFFh) */
    unsigned char *p;
    for (p = (unsigned char *)0xC000; p < (unsigned char *)0xE000; p++) {
        *p = 0;
    }
    for (p = (unsigned char *)0xE000; p != (unsigned char *)0; p++) {
        *p = 0;
    }
}

/* RLE-распаковка: плоскость 1 (C000h) + плоскость 0 (E000h) (graphrle512.asm) */
extern void graph_rle_expand_512(const unsigned char *src);

int main(void)
{
    /* Переключаемся в режим 512x256 */
    graph_set_mode_512();
    
    /* Очищаем экран (плоскость B: C000h-FFFFh, 16 КБ) */
    graph_clear_512();
    
    /* Распаковываем картинку */
    graph_rle_expand_512(dt2_512_bmp_screen_rle);
    
    /* Загружаем палитру (2 цвета, 4 слота) */
    graph_set_palette_512(dt2_512_bmp_palette);
    
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
    
    /* Возвращаемся в режим 256x256 перед выходом */
    graph_set_mode_256();
    
    return 0;
}
