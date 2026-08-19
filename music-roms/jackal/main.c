/*
 * main.c — music-ROM для Вектор-06Ц: саундтреки из NES-игры Jackal,
 *          воспроизведение на чистой КР580ВИ53.
 *
 * Всё железо — своими силами без clib z88dk (библиотека vector-games/lib):
 *   - графика:  RLE-заставка + палитра + текст 8x8 (graph.c, v06pal.asm);
 *   - звук:     ВИ53, плеер в кадровом прерывании (sound.c, lib/startup.asm);
 *   - клавиши:  опрос матрицы портами (keyboard.c).
 *
 * Данные мелодий пересчитаны из NES-формата движка Konami (Jackal)
 * скриптом utils/music2inc.py: один шаг = один тик движка NES.
 * Темп задаётся music_set_tempo(num, den): 1/1 — номинал, num < den —
 * медленнее. Intro подобрано на слух; для подстройки поменять два числа.
 *
 * Управление:
 *   1 — Intro (по окончании — тишина, без зацикливания);
 *   2 — Level 1 (по кругу);
 *   3 — Level 2 (по кругу);
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
#include "rom_data/level1_music.inc" /* const music_step_t level1_music[]; ... */
#include "rom_data/level2_music.inc" /* const music_step_t level2_music[]; ... */

/* Ожидание начала следующего кадра (счётчик ведёт кадровое прерывание) */
static void wait_one_frame(void)
{
    unsigned int start;

    start = frame_count;
    while (frame_count == start)
        intrinsic_halt();           /* лёгкий сон до прерывания */
}

/* Запуск мелодии: остановить текущую, подменить данные/темп, стартовать. */
static void play_song(const music_step_t *steps, unsigned int len,
                      unsigned char tempo_num, unsigned char tempo_den,
                      unsigned char loop)
{
    music_stop();
    music_set_data(steps, len);
    music_set_tempo(tempo_num, tempo_den);
    music_set_loop(loop);
    music_start();
}

/* Меню под заставкой (шрифт 8x8; цвет 9 — белый в палитре title.bmp).
 * Картинка занимает строки 0..title_bmp_height, текст — под ней. */
static void show_menu(void)
{
    unsigned char y = (unsigned char)(title_bmp_height + 6u);

    graph_print(24u, y, "JACKAL (NES) SOUNDTRACKS:", 8u);
    graph_print(24u, (unsigned char)(y + 8u), "1 - INTRO", 8u);
    graph_print(24u, (unsigned char)(y + 16u), "2 - LEVEL 1", 8u);
    graph_print(24u, (unsigned char)(y + 24u), "3 - LEVEL 2", 8u);
    graph_print(24u, (unsigned char)(y + 32u), "0 - STOP MUSIC", 8u);
}

/* ------------------------------- main -------------------------------- */

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;

    frame_handler = music_tick;         /* тик плеера в кадровом прерывании */
    sound_init();                       /* все каналы ВИ53 в тишину */

    /* титульная заставка: чёрная палитра скрывает процесс распаковки,
     * по завершении — рабочая палитра картинки и текст меню */
    graph_set_black_palette();
    graph_rle_expand(title_bmp_screen_rle, V06_VRAM);
    graph_set_palette(title_bmp_palette);
    show_menu();

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {          /* реакция на нажатие, не на удержание */
            if (key == '1') {
                /* Темп подобан по записи оригинала (jackal_intro.wav):
                 * звуковая часть клипа = 261 тик занимает ~6.98 с, т.е.
                 * движок NES делает ~37.4 тика/с; 3/4 от наших 50 Гц =
                 * 37.5 тика/с. */
                play_song(intro_music, intro_music_len, 3u, 4u, 0u);
            } else if (key == '2') {
                /* треки уровней: движок NES идёт 60 тиков/с, плеер 50 Гц,
                 * поэтому темп 6/5. */
                play_song(level1_music, level1_music_len, 6u, 5u, 1u);
            } else if (key == '3') {
                play_song(level2_music, level2_music_len, 6u, 5u, 1u);
            } else if (key == '0') {
                music_stop();
            } else if (key == 27) {     /* СТОП (ESC) */
                break;
            }
        }
        prev_key = key;
    }

    music_stop();
    return 0;
}
