/*
 * main.c — тестовый ROM для Вектор-06Ц: библиотека из 16 синтетических
 *          шумовых инструментов NES ($0..$F) + партитурный плеер music.c.
 *
 * Всё железо — своими силами без clib z88dk (библиотека vector-games/lib):
 *   - графика:  текст 8x8 (graphpr.asm), очистка экрана (graphclr.asm);
 *   - звук:     партитурный синтезатор music.c на 3 тональных канала;
 *               устройство вывода выбирается явно (Ф5):
 *                 ВИ53 (i8253) — мелодия на 3 каналах ВИ53, шум ударных
 *                                на Tape Out (PC0, LFSR)  [по умолчанию];
 *                 AY-3-8910    — мелодия на тонах A/B/C, шум ударных на
 *                                шумовом генераторе AY (канал C, Noise C);
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
 *   Ф5        — устройство вывода: ВИ53 (Tape Out) ↔ AY-3-8910 (Noise C);
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

/* Кадровое прерывание: опрос клавиатуры на VSync (луч в гашении —
 * маски строк порта 03h не дёргают скролл), затем тик плеера и ударных. */
static void on_frame(void)
{
    kbd_scan_now();
    music_tick();
    drum_tick();
}

/* Флаг текущего устройства вывода — только для выбора функции запуска/
 * перепривязки (music_start_vi53/ay, music_use_vi53/ay) и индикации.
 * Никакого глобального «режима звука»: 0 = КР580ВИ53 (Tape Out), 1 = AY-3-8910. */
static unsigned char use_ay = 0;

/* Запуск партитуры: остановить текущую, подменить данные, стартовать
 * на текущем устройстве вывода (use_ay). */
static void play_song(const music_song_t *song, unsigned char loop)
{
    music_stop();
    drum_init();
    music_set_data(song);
    music_set_loop(loop);
    if (use_ay)
        music_start_ay();
    else
        music_start_vi53();
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
    {   0u,  10u, "1-OPEN HI-HAT" },
    {   0u,  20u, "2-SNARE ATTACK" },
    {   0u,  30u, "3-SNARE BODY" },
    {   0u,  40u, "4-SNARE STANDARD" },
    {   0u,  50u, "5-CYMBAL CRASH" },
    {   0u,  60u, "6-SNARE LOW" },
    {   0u,  70u, "7-DISTANT EXPLOS" },
    /* семплы: правая колонка */
    { 17u,   0u, "8-TOM LOW" },
    { 17u,  10u, "9-TOM RUMBLE" },
    { 17u,  20u, "A-HEAVY KICK" },
    { 17u,  30u, "B-TIGHT KICK" },
    { 17u,  40u, "C-RUMBLE SUB" },
    { 17u,  50u, "D-ULTRA-LO ROAR" },
    { 17u,  60u, "E-SUB-BASS DROP" },
    { 17u,  70u, "F-CRACKLE" },
    /* управление */
    {   0u, 100u, "F1-EXAMPLE DEMO" },
    { 17u,  100u, "F2-JACKAL" },
    {   0u, 110u, "F3-CASTLEVANIA" },
    { 17u,  110u, "F4-STOP MUSIC" },
    {   0u, 120u, "F5-MUSIC MODE" },
};

static void show_menu(unsigned char selected)
{
    unsigned char y0 = (unsigned char)(logo_bmp_height + 16u);
    unsigned char i;

    for (i = 0u; i < sizeof(menu_lines) / sizeof(menu_lines[0]); ++i) {
        gfx_print(menu_lines[i].dx,
                    (unsigned char)(y0 + menu_lines[i].dy),
                    menu_lines[i].text,
                    i == selected ? HIGHLIGHT_COLOR : TEXT_COLOR);
    }
}

/* Индикация текущего устройства вывода в правой колонке строки Ф5.
 * Ячейка 8x8 непрозрачная — значение всегда из 4 символов, хвост
 * затирается пробелами. */
static void show_backend(void)
{
    unsigned char y0 = (unsigned char)(logo_bmp_height + 16u);
    gfx_print(17u, (unsigned char)(y0 + 120u),
                use_ay ? "AY  " : "VI53",
                use_ay ? HIGHLIGHT_COLOR : TEXT_COLOR);
}

/* ------------------------------- main -------------------------------- */

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;

    frame_handler = on_frame;           /* мелодия + ударные в прерывании */
    drum_init();                        /* сброс/глушение ударных; маршрут по умолчанию — Tape Out (ВИ53) */

    /* Экран: чёрный фон, логотип, текст меню. */
    gfx_set_black_palette();
    gfx_clear(0);
    gfx_rle_expand(logo_bmp_screen_rle, 8u, 0u);
    show_menu(255);
    show_backend();
    gfx_set_palette(logo_bmp_palette);

    /* Загрузка библиотеки семплов в память (не играет, но семплы доступны). */
    play_song(&nes_drums_song, 0);

    /* Стартовый трек не запускаем — ждём нажатия Ф1 или Ф2. */

    for (;;) {
        wait_one_frame();

        key = kbd_read();   /* снимок матрицы уже сделан в on_frame (kbd_scan_now) */
        if (key != prev_key) {          /* реакция на нажатие */
            unsigned char sel = 255u;
            if (key == 128) {           /* Ф1 — examples demo */
                play_song(&examples_music_song, 0);
                sel = 16u;
            } else if (key == 129) {    /* Ф2 — Jackal */
                ay_set_envelope(AY_CH_C, AY_ENV_14, 500);
                play_song(&jackal_music_song, 0);
                sel = 17u;
            } else if (key == 130) {    /* Ф3 — Castlevania */
                play_song(&castlevania_music_song, 0);
                sel = 18u;
            } else if (key == 131) {    /* Ф4 — stop music */
                music_stop();
                sel = 19u;
            } else if (key == 132) {    /* Ф5 — backend ВИ53 ↔ AY */
                use_ay = (unsigned char)(!use_ay);
                if (use_ay)
                    music_use_ay();
                else
                    music_use_vi53();
                show_backend();
                sel = 20u;
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
