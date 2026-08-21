/*
 * main.c — каркас music-ROM для Вектора-06Ц: саундтреки Castlevania.
 *          Пока — только титульная заставка title_bmp.inc.
 *
 * Всё железо — своими силами без clib z88dk (библиотека vector-games/lib):
 *   - графика:  RLE-заставка + палитра (graph.c, v06pal.asm),
 *               текст 8x8 на ассемблере (graphpr.asm);
 *   - клавиши:  опрос матрицы портами (keyboard.c).
 *
 * Звук появится следующим шагом: партитуры music/*.mus ->
 * utils/mus2inc.py -> rom_data/*_music.inc, плеер music.c (ВИ53)
 * и ударные drums.asm (шум AY-3-8910) — по образцу jackal/main.c.
 *
 * Управление:
 *   СТОП (ESC) — выход из ROM.
 *
 * Сборка: make (или make deploy — сразу в папку ROMS эмулятора PPSSPP).
 *
 * Каталог rom_data — данные для ROM (заставка, позже — партитуры).
 */

#include <intrinsic.h>

#include "v06.h"                    /* общая библиотека Вектора-06Ц */

#include "rom_data/title_bmp.inc"   /* title_bmp_screen_rle, title_bmp_palette */

/* Ожидание начала следующего кадра (счётчик ведёт кадровое прерывание) */
static void wait_one_frame(void)
{
    unsigned int start;

    start = frame_count;
    while (frame_count == start)
        intrinsic_halt();           /* лёгкий сон до прерывания */
}

/* ------------------------------- main -------------------------------- */

int main(void)
{
    unsigned char key;

    /* титульная заставка: чёрная палитра скрывает процесс распаковки,
     * по завершении — рабочая палитра картинки */
    graph_set_black_palette();
    graph_clear(0);
    graph_rle_expand(title_bmp_screen_rle, 0u, 0u);
    graph_set_palette(title_bmp_palette);

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key == 27)              /* СТОП (ESC) */
            break;
    }

    return 0;
}
