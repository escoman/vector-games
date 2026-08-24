/*
 * main.c — тестовый ROM для Вектор-06Ц: библиотека из 16 синтетических
 *          шумовых инструментов NES ($0..$F) на AY-3-8910.
 *
 * Всё железо — своими силами без clib z88dk (библиотека vector-games/lib):
 *   - графика:  текст 8x8 (graphpr.asm), очистка экрана (graphclr.asm);
 *   - звук:     AY-3-8910, канал шума, канал C «tone off, noise on»;
 *               тоновые каналы и ВИ53 не используются;
 *   - клавиши:  опрос матрицы портами (keyboard.c).
 *
 * Воспроизведение:
 *   - Библиотека nes_drums загружается при старте (семплы в памяти);
 *   - Ф1 — демозапись examples (все 16 звуков + ритмы);
 *   - Ф2 — Jackal (из NSF-экспорта);
 *   - Ф3 — Castlevania (из NSF-экспорта);
 *   - клавиши 0-9, A-F запускают соответствующий семпл.
 *
 * Управление:
 *   Ф1        — демозапись examples;
 *   Ф2        — Jackal;
 *   Ф3        — Castlevania;
 *   Ф4        — остановить музыку;
 *   0..9, A-F — семпл $0..$F.
 *
 * Сборка: make (или make deploy — сразу в папку ROMS эмулятора PPSSPP).
 */

#include <intrinsic.h>

#include "v06.h"                        /* общая библиотека Вектора-06Ц */
#include "nes_drums.h"              /* nes_drums_song, nes_drums_samples */
#include "rom_data/logo_bmp.inc"        /* logo_bmp_screen_rle, logo_bmp_palette */
#include "rom_data/examples.inc"        /* examples_music_song (демо) */
#include "rom_data/jackal.inc"          /* jackal_music_song */
#include "rom_data/castlevania.inc"     /* castlevania_music_song */

/* Ожидание начала следующего кадра (счётчик ведёт кадровое прерывание) */
static void wait_one_frame(void)
{
    unsigned int start;

    start = frame_count;
    while (frame_count == start)
        intrinsic_halt();               /* лёгкий сон до прерывания */
}

/* Кадровое прерывание: тик плеера мелодии и огибающие ударных. */
static void on_frame(void)
{
    music_tick();
    drum_tick();
}

/* Запуск партитуры: остановить текущую, подменить данные, стартовать. */
static void play_song(const music_song_t *song, unsigned char loop)
{
    music_stop();
    drum_init();
    music_set_data(song);
    music_set_loop(loop);
    music_start();
}

/* Запуск отдельного семпла по индексу 0..15. */
static void play_sample(unsigned char idx)
{
    if (idx < 16u)
        drum_sample_play(nes_drums_samples[idx]);
}

/* Преобразование hex-символа ('0'-'9','a'-'f','A'-'F') в индекс 0..15.
 * Возвращает 16, если символ не распознан. */
static unsigned char hex_to_idx(unsigned char ch)
{
    if (ch >= '0' && ch <= '9')
        return ch - '0';
    if (ch >= 'a' && ch <= 'f')
        return ch - 'a' + 10u;
    if (ch >= 'A' && ch <= 'F')
        return ch - 'A' + 10u;
    return 16u;
}

const unsigned char TEXT_COLOR = 12u;           /* белый в палитре logo.bmp */
const unsigned char HIGHLIGHT_COLOR = 9u;       /* красный в палитре logo.bmp */

/* Меню: семплы $0..$F (две колонки) + управление.
 * Каждая строка — смещение (dx, dy) от начала меню (x=0, y=logo_bmp_height+16). */
static const struct {
    unsigned char dx;
    unsigned char dy;
    const char *text;
} menu_lines[] = {
    /* семплы: левая колонка */
    {   0u,   0u, "0-CLOSED HI-HAT" },
    {   0u,   8u, "1-OPEN HI-HAT" },
    {   0u,  16u, "2-SNARE ATTACK" },
    {   0u,  24u, "3-SNARE BODY" },
    {   0u,  32u, "4-SNARE STANDARD" },
    {   0u,  40u, "5-CYMBAL CRASH" },
    {   0u,  48u, "6-SNARE LOW" },
    {   0u,  56u, "7-DISTANT EXPLOS" },
    /* семплы: правая колонка */
    { 142u,   0u, "8-TOM LOW" },
    { 142u,   8u, "9-TOM RUMBLE" },
    { 142u,  16u, "A-HEAVY KICK" },
    { 142u,  24u, "B-TIGHT KICK" },
    { 142u,  32u, "C-RUMBLE SUB" },
    { 142u,  40u, "D-ULTRA-LO ROAR" },
    { 142u,  48u, "E-SUB-BASS DROP" },
    { 142u,  56u, "F-CRACKLE" },
    /* управление */
    {   0u,  72u, "F1-EXAMPLE DEMO" },
    { 142u,  72u, "F2-JACKAL" },
    {   0u,  80u, "F3-CASTLEVANIA" },
    { 142u,  80u, "F4-STOP MUSIC" },
};

static void show_menu(unsigned char selected)
{
    unsigned char y0 = (unsigned char)(logo_bmp_height + 16u);
    unsigned char i;

    for (i = 0u; i < sizeof(menu_lines) / sizeof(menu_lines[0]); ++i) {
        graph_print(menu_lines[i].dx,
                    (unsigned char)(y0 + menu_lines[i].dy),
                    menu_lines[i].text,
                    i == selected ? HIGHLIGHT_COLOR : TEXT_COLOR);
    }
}

/* ------------------------------- main -------------------------------- */

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;

    frame_handler = on_frame;           /* мелодия + ударные в прерывании */
    drum_init();                        /* микшер AY: шум канала C */

    /* Экран: чёрный фон, логотип, текст меню. */
    graph_set_black_palette();
    graph_clear(0);
    graph_rle_expand(logo_bmp_screen_rle, 8u, 0u);
    show_menu(255);
    graph_set_palette(logo_bmp_palette);

    /* Загрузка библиотеки семплов в память (не играет, но семплы доступны). */
    play_song(&nes_drums_song, 0);

    /* Стартовый трек не запускаем — ждём нажатия Ф1 или Ф2. */

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {          /* реакция на нажатие */
            unsigned char sel = 255u;
            if (key == 128) {           /* Ф1 — examples demo */
                play_song(&examples_music_song, 0);
                sel = 16u;
            } else if (key == 129) {    /* Ф2 — Jackal */
                play_song(&jackal_music_song, 0);
                sel = 17u;
            } else if (key == 130) {    /* Ф3 — Castlevania */
                play_song(&castlevania_music_song, 0);
                sel = 18u;
            } else if (key == 131) {    /* Ф4 — stop music */
                music_stop();
                sel = 19u;
            } else if (key >= '0' && key <= '9') {
                play_sample(hex_to_idx(key));
                sel = hex_to_idx(key);
            } else if ((key >= 'a' && key <= 'f') ||
                       (key >= 'A' && key <= 'F')) {
                play_sample(hex_to_idx(key));
                sel = hex_to_idx(key);
            }
            show_menu(sel);
        }
        prev_key = key;
    }
}
