/*
 * graph.c — вывод графики на экран Вектора-06Ц (библиотека vector-games).
 *
 * Видеопамять: 32 КБ по адресам 0x8000-0xFFFF, 4 битовые плоскости:
 *   0x8000 — плоскость веса 8, 0xA000 — веса 4,
 *   0xC000 — веса 2,           0xE000 — веса 1.
 * Экранная картинка хранится в ROM в RLE-виде (utils/bmp2inc.py);
 * распаковывает её graph_rle_expand на ассемблере (graphrle.asm).
 *
 * Заливка экрана graph_clear — тоже на ассемблере (graphclr.asm).
 *
 * Палитра загружается ассемблерной v06_set_palette_asm (v06pal.asm):
 * запись слота идёт через бордюр в кадровый гасящий интервал, т.к.
 * порт 0C пишет в регистр цвета, отображаемого в момент записи.
 */

#include "v06.h"

/* asm-загрузчик палитры (v06pal.asm) */
extern void v06_set_palette_asm(const unsigned char *pal);

/* Текущий регистр строки; keyboard.c восстанавливает его после опроса */
unsigned char graph_scroll_row = 0;

/* RLE-распаковка (graph_rle_expand) — на ассемблере в graphrle.asm.
 * Заливка экрана (graph_clear) — на ассемблере в graphclr.asm. */

/* Загрузка 16 цветов палитры (формат байта 0bBBGGGRRR) */
void graph_set_palette(const unsigned char *pal)
{
    v06_set_palette_asm(pal);
}

/* Нулевая палитра: все 16 цветов чёрные. Экран становится полностью
 * чёрным, хотя видеопамять не трогается — удобно, чтобы скрыть
 * процесс отрисовки заставки. */
void graph_set_black_palette(void)
{
    static const unsigned char black[16] = { 0 };

    v06_set_palette_asm(black);
}

/* Регистр строки (порт 3); запоминается для keyboard.c */
void graph_set_scroll(unsigned char row)
{
    graph_scroll_row = row;
    v06_out(V06_PIA_PA, row);
}

/* ------------------------- Текст: шрифт 8x8 ------------------------- */

/* graph_put_char и graph_print (и шрифт font8x8) — на ассемблере
 * в graphpr.asm. */
