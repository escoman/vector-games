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
 *   - Ф2 — Jackal track_0 (мелодия + ударные из общей библиотеки);
 *   - клавиши 0-9, A-F запускают соответствующий семпл.
 *
 * Управление:
 *   Ф1        — демозапись examples;
 *   Ф2        — Jackal track 0;
 *   0..9, A-F — семпл $0..$F;
 *   СТОП (ESC) — выход из ROM.
 *
 * Сборка: make (или make deploy — сразу в папку ROMS эмулятора PPSSPP).
 */

#include <intrinsic.h>

#include "v06.h"                        /* общая библиотека Вектора-06Ц */
#include "nes_drums.h"              /* nes_drums_song, nes_drums_samples */
#include "rom_data/examples.inc"        /* examples_music_song (демо) */
#include "rom_data/track_0.inc"         /* track_0_music_song (Jackal) */

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

/* Палитра: цвет 0 — чёрный (фон), цвет 8 — белый (текст). */
static const unsigned char nes_pal[16] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xFF, 0x24, 0x12, 0x03, 0x00, 0x00, 0x00, 0x00
};

/* Меню на экране (шрифт 8x8, цвет 8 — белый).
 * Экран 256×192, видимая область до ~192 по Y. */
static const struct {
    unsigned char dy;
    const char *text;
} menu_lines[] = {
    {   0u, "NES DRUMS LIBRARY" },

    {  16u, "0 - CLOSED HI-HAT" },
    {  24u, "1 - OPEN HI-HAT" },
    {  32u, "2 - SNARE ATTACK" },
    {  40u, "3 - SNARE BODY" },
    {  48u, "4 - SNARE STANDARD" },
    {  56u, "5 - CYMBAL CRASH" },
    {  64u, "6 - SNARE LOW" },
    {  72u, "7 - DISTANT EXPLOS" },
    {  80u, "8 - TOM LOW" },
    {  88u, "9 - TOM RUMBLE" },
    {  96u, "A - HEAVY KICK" },
    { 104u, "B - TIGHT KICK" },
    { 112u, "C - RUMBLE SUB" },
    { 120u, "D - ULTRA-LOW ROAR" },
    { 128u, "E - SUB-BASS DROP" },
    { 136u, "F - CRACKLE" },

    { 152u, "F1 - EXAMPLES DEMO" },
    { 160u, "F2 - JACKAL TRACK 0" },
    { 168u, "ESC - EXIT" },
};

static void show_menu(void)
{
    unsigned char x0 = 16u;
    unsigned char y0 = 8u;
    unsigned char i;

    for (i = 0u; i < sizeof(menu_lines) / sizeof(menu_lines[0]); ++i) {
        graph_print(x0,
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
    drum_init();                        /* микшер AY: шум канала C */

    /* Экран: чёрный фон, текст меню. */
    graph_set_black_palette();
    graph_clear(0);
    show_menu();
    graph_set_palette(nes_pal);

    /* Загрузка библиотеки семплов в память (не играет, но семплы доступны). */
    play_song(&nes_drums_song, 0);

    /* Стартовый трек не запускаем — ждём нажатия Ф1 или Ф2. */

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {          /* реакция на нажатие */
            if (key == 128) {           /* Ф1 — examples demo */
                play_song(&examples_music_song, 0);
            } else if (key == 129) {    /* Ф2 — Jackal track 0 */
                play_song(&track_0_music_song, 0);
            } else if (key >= '0' && key <= '9') {
                play_sample(hex_to_idx(key));
            } else if ((key >= 'a' && key <= 'f') ||
                       (key >= 'A' && key <= 'F')) {
                play_sample(hex_to_idx(key));
            } else if (key == 27) {     /* СТОП (ESC) */
                break;
            }
        }
        prev_key = key;
    }

    music_stop();
    return 0;
}
