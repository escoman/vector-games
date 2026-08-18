/*
 * main.c — music-ROM для Вектор-06Ц: мелодия «Game Started Intro»
 *          из NES-игры Jackal, воспроизведение на чистой КР580ВИ53.
 *
 * Всё железо — своими силами без clib z88dk (библиотека vector-games/lib):
 *   - графика:  RLE-заставка + палитра (graph.c, v06pal.asm);
 *   - звук:     ВИ53, плеер в кадровом прерывании (sound.c, lib/startup.asm);
 *   - клавиши:  опрос матрицы портами (keyboard.c).
 *
 * Данные мелодии пересчитаны из NES-формата движка Konami (Jackal)
 * скриптом utils/music2inc.py: один шаг = один тик 50 Гц.
 * Темп задаётся music_set_tempo(num, den): 1/1 — номинал, num < den —
 * медленнее. Подобрано на слух; для подстройки поменять два числа.
 *
 * Управление:
 *   1 — запустить мелодию (по окончании — тишина, без зацикливания);
 *   0 — полная остановка звука;
 *   СТОП (ESC) — выход из ROM.
 *
 * Сборка: build.sh
 *   zcc +vector06c --no-crt ../../lib/startup.asm main.c ../../lib/...
 *
 * Каталог nes_src — исходники из NES (jackal.nes, извлечённая музыка,
 * скрипты извлечения); rom_data — данные для ROM (заставка, мелодия).
 */

#include <intrinsic.h>

#include "v06.h"                    /* общая библиотека Вектора-06Ц */

#include "rom_data/title_bmp.inc"   /* title_bmp_screen_rle, title_bmp_palette */
#include "rom_data/intro_music.inc" /* const music_step_t intro_music[]; ... */

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

    music_set_data(intro_music, intro_music_len);
    /* Темп подобан по записи оригинала (jackal_intro.wav): звуковая часть
     * клипа = 261 тик занимает ~6.98 с, т.е. движок NES делает ~37.4
     * тика/с; 3/4 от наших 50 Гц = 37.5 тика/с. */
    music_set_tempo(3u, 4u);
    frame_handler = music_tick;         /* тик плеера в кадровом прерывании */
    sound_init();                       /* все каналы ВИ53 в тишину */

    /* титульная заставка: чёрная палитра скрывает процесс распаковки,
     * по завершении — рабочая палитра картинки */
    graph_set_black_palette();
    graph_rle_expand(title_bmp_screen_rle, V06_VRAM);
    graph_set_palette(title_bmp_palette);

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key == '1') {
            if (!music_is_playing())
                music_start();
        } else if (key == '0') {
            if (music_is_playing())
                music_stop();
        } else if (key == 27) {         /* СТОП (ESC) */
            break;
        }
    }

    music_stop();
    return 0;
}
