/*
 * main.c — music-ROM для Вектор-06Ц: саундтреки из NES-игры Jackal,
 *          воспроизведение на чистой КР580ВИ53.
 *
 * Всё железо — своими силами без clib z88dk (библиотека vector-games/lib):
 *   - графика:  RLE-заставка + палитра (graph.c, v06pal.asm),
 *               текст 8x8 на ассемблере (graphpr.asm);
 *   - звук:     мелодия — ВИ53 (3 тональных канала), ударные —
 *               канал шума AY-3-8910 (drums.asm); оба тика — в
 *               кадровом прерывании (sound.c, drums.asm, startup.asm);
 *   - клавиши:  опрос матрицы портами (keyboard.c).
 *
 * Данные мелодий пересчитаны из NES-формата движка Konami (Jackal)
 * скриптом utils/music2inc.py: ретайминг шкалы источника (60 Гц,
 * Intro — 53.33 Гц) под кадровые 50 Гц Вектора, в .inc — целые тики.
 * Темп везде 1/1: ровно один тик плеера на кадр, без дробных темпов,
 * дающих дрожание ритма.
 *
 * Управление:
 *   1 — Intro (по окончании — тишина, без зацикливания);
 *   2 — Level 1 (по кругу);
 *   3 — Level 2 (по кругу);
 *   4 — Level 3 (по кругу);
 *   5 — Boss (по кругу);
 *   6 — Final Boss (по кругу);
 *   7 — Stage Clear (без зацикливания);
 *   8 — Game Over (без зацикливания);
 *   9 — Ending (без зацикливания);
 *   0 — полная остановка звука;
 *   СТОП (ESC) — выход из ROM.
 *
 * Сборка: make (или make deploy — сразу в папку ROMS эмулятора PPSSPP)
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
#include "rom_data/level3_music.inc" /* const music_step_t level3_music[]; ... */
#include "rom_data/boss_music.inc"  /* const music_step_t boss_music[]; ... */
#include "rom_data/final_boss_music.inc" /* const music_step_t final_boss_music[]; */
#include "rom_data/stage_clear_music.inc" /* const music_step_t stage_clear_music[]; */
#include "rom_data/game_over_music.inc" /* const music_step_t game_over_music[]; */
#include "rom_data/ending_music.inc" /* const music_step_t ending_music[]; ... */

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

/* Меню под заставкой (шрифт 8x8; цвет 8 — белый в палитре title.bmp).
 * Картинка занимает строки 0..title_bmp_height, текст — под ней.
 * Каждая строка задаётся смещением (dx, dy) от начальной точки. */
static const struct {
    unsigned char dx;           /* смещение по горизонтали от x = 24 */
    unsigned char dy;           /* смещение по вертикали от верха меню */
    const char *text;
} menu_lines[] = {
    { 16u,  0u, "JACKAL (NES) SOUNDTRACKS:" },
    { 0u,  16u, "1 - INTRO" },
    { 0u, 32u, "2 - LEVEL 1" },
    { 0u, 48u, "3 - LEVEL 2" },
    { 0u, 64u, "4 - LEVEL 3" },
    { 0u, 80u, "5 - BOSS" },
    { 112u, 16u, "6 - FINAL BOSS" },
    { 112u, 32u, "7 - STAGE CLEAR" },
    { 112u, 48u, "8 - GAME OVER" },
    { 112u, 64u, "9 - ENDING" },
    { 112u, 80u, "0 - STOP MUSIC" },
};

static void show_menu(void)
{
    unsigned char x0 = 16u;
    unsigned char y0 = (unsigned char)(title_bmp_height + 6u);
    unsigned char i;

    for (i = 0u; i < sizeof(menu_lines) / sizeof(menu_lines[0]); ++i) {
        graph_print((unsigned char)(x0 + menu_lines[i].dx),
                    (unsigned char)(y0 + menu_lines[i].dy),
                    menu_lines[i].text, 8u);
    }
}

/* ------------------------------- main -------------------------------- */

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;

    frame_handler = on_frame;           /* мелодия + ударные в прерывании */
    sound_init();                       /* все каналы ВИ53 в тишину */
    drum_init();                        /* миксер AY: шум канала C */

    /* титульная заставка: чёрная палитра скрывает процесс распаковки,
     * по завершении — рабочая палитра картинки и текст меню */
    graph_set_black_palette();
    graph_rle_expand(title_bmp_screen_rle, 0u, 0u);
    show_menu();
    graph_set_palette(title_bmp_palette);

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {          /* реакция на нажатие, не на удержание */
            if (key == '1') {
                /* данные уже ретаймнуты под 50 Гц конвертером */
                play_song(intro_music, intro_music_len, 1u, 1u, 0u);
            } else if (key == '2') {
                play_song(level1_music, level1_music_len, 1u, 1u, 1u);
            } else if (key == '3') {
                play_song(level2_music, level2_music_len, 1u, 1u, 1u);
            } else if (key == '4') {
                play_song(level3_music, level3_music_len, 1u, 1u, 1u);
            } else if (key == '5') {
                play_song(boss_music, boss_music_len, 1u, 1u, 1u);
            } else if (key == '6') {
                play_song(final_boss_music, final_boss_music_len, 1u, 1u, 1u);
            } else if (key == '7') {
                play_song(stage_clear_music, stage_clear_music_len,
                          1u, 1u, 0u);
            } else if (key == '8') {
                play_song(game_over_music, game_over_music_len, 1u, 1u, 0u);
            } else if (key == '9') {
                play_song(ending_music, ending_music_len, 1u, 1u, 0u);
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
