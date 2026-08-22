/*
 * main.c — music-ROM для Вектора-06Ц: саундтреки из NES-игры Castlevania.
 *
 * Всё железо — своими силами без clib z88dk (библиотека vector-games/lib):
 *   - графика:  RLE-заставка + палитра (graph.c, v06pal.asm),
 *               текст 8x8 на ассемблере (graphpr.asm);
 *   - звук:     мелодия — ВИ53 (3 тональных канала), ударные —
 *               канал шума AY-3-8910 (drums.asm); всё от единого
 *               музыкального времени в кадровом прерывании
 *               (music.c, drums.asm, startup.asm);
 *   - клавиши:  опрос матрицы портами (keyboard.c).
 *
 * Данные мелодий: дорожки NES-движка Konami (Castlevania) конвертированы
 * скриптом utils/music2mus.py в партитуры music/*.mus, те скомпилиро-
 * ваны utils/mus2inc.py в rom_data/*_music.inc (music_song_t).
 *
 * Управление:
 *   1 — Intro;
 *   2 — Level 1;
 *   0 — остановить музыку;
 *   СТОП (ESC) — выход из ROM.
 *
 * Сборка: make (или make deploy — сразу в папку ROMS эмулятора PPSSPP).
 */

#include <intrinsic.h>

#include "v06.h"                    /* общая библиотека Вектора-06Ц */
#include "nes_drums.h"              /* общая библиотека ударных NES */

#include "rom_data/title_bmp.inc"      /* title_bmp_screen_rle, title_bmp_palette */
#include "rom_data/track_0_music.inc"  /* music_song_t track_0_music_song */
#include "rom_data/track_1_music.inc"  /* music_song_t track_1_music_song */

/* Ожидание начала следующего кадра (счётчик ведёт кадровое прерывание) */
static void wait_one_frame(void)
{
    unsigned int start;

    start = frame_count;
    while (frame_count == start)
        intrinsic_halt();           /* лёгкий сон до прерывания */
}

/* Кадровое прерывание: тик плеера мелодии (ВИ53) и огибающие
 * ударных (шум AY-3-8910). */
static void on_frame(void)
{
    music_tick();
    drum_tick();
}

/* Запуск мелодии: остановить текущую, подменить данные, стартовать. */
static void play_song(const music_song_t *song, unsigned char loop)
{
    music_set_data(song);           /* внутри — остановка текущей */
    music_set_loop(loop);
    music_start();
}

/* Меню под заставкой (шрифт 8x8; цвет 8 — белый в палитре title.bmp).
 * Картинка занимает строки 0..title_bmp_height, текст — под ней.
 * Каждая строка задаётся смещением (dx, dy) от начальной точки. */
static const struct {
    unsigned char dx;           /* смещение по горизонтали от x = 24 */
    unsigned char dy;           /* смещение по вертикали от верха меню */
    const char *text;
} menu_lines[] = {
    { 8u,  0u,      "CASTLEVANIA (NES) SOUNDTRACKS:" },

    { 0u,  16u,     "1 - INTRO" },
    { 128u,  24u,   "2 - LEVEL 1" },
    { 0u,  34u,     "0 - STOP MUSIC" },

    { 0u,  60u,     "KONAMI,1987" },
    { 112u, 60u,    "SARMIN ALEXEY,2026" },
    { 112u, 70u,    "    FOR VECTOR-06C" }
};

static void show_menu(unsigned char selected)
{
    unsigned char x0 = 0u;
    unsigned char y0 = (unsigned char)(title_bmp_height + 16u);
    unsigned char i;

    for (i = 0u; i < sizeof(menu_lines) / sizeof(menu_lines[0]); ++i) {
        graph_print((unsigned char)(x0 + menu_lines[i].dx),
                    (unsigned char)(y0 + menu_lines[i].dy),
                    menu_lines[i].text, selected == i ? 8u : 4u);
    }
}

/* ------------------------------- main -------------------------------- */

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;

    frame_handler = on_frame;           /* мелодия + ударные в прерывании */
    drum_init();                        /* микшер AY: шум канала C */

    /* титульная заставка: чёрная палитра скрывает процесс распаковки,
     * по завершении — рабочая палитра картинки и текст меню */
    graph_set_black_palette();
    graph_clear(0);
    graph_rle_expand(title_bmp_screen_rle, 0u, 0u);
    show_menu(100);
    graph_set_palette(title_bmp_palette);

    /* Загрузка библиотеки семплов NES в память. */
    play_song(&nes_drums_song, 0);

    unsigned char track;

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {          /* реакция на нажатие, не на удержание */
            if (key == '0') {
                music_stop();
                show_menu(100);
            } else if (key >= '1' && key <= '2') {
                track = key - '1';
                const music_song_t *songs[] = {
                    &track_0_music_song, &track_1_music_song
                };
                play_song(songs[track], 0);
                show_menu(track+1);
            } else if (key == 27) {     /* СТОП (ESC) */
                break;
            }
        }
        prev_key = key;
    }

    music_stop();
    return 0;
}
