/*
 * main.c — демо-ROM для Вектор-06Ц: библиотека синтетических ударных
 *          на канале шума AY-3-8910 (drums.asm).
 *
 * Всё железо — своими силами без clib z88dk (библиотека vector-games/lib):
 *   - графика:  RLE-заставка + палитра (graph.c, v06pal.asm),
 *               текст 8x8 на ассемблере (graphpr.asm);
 *   - звук:     AY-3-8910, только канал шума, канал C «tone off,
 *               noise on»; тоновые каналы и ВИ53 не используются;
 *   - клавиши:  опрос матрицы портами (keyboard.c).
 *
 * Тоновые каналы AY полностью свободны для мелодии: библиотека не
 * пишет в R0-R5, микшер R7 настраивается один раз в drum_init(),
 * огибающая программная — drum_tick() из кадрового прерывания.
 *
 * Управление:
 *   1 — KICK (бочка);
 *   2 — SNARE (малый барабан);
 *   3 — HAT CLOSED (закрытый хэт);
 *   4 — HAT OPEN (открытый хэт);
 *   5 — TOM;
 *   6 — CLAP (хлопок);
 *   7 — RIM (щелчок);
 *   СТОП (ESC) — выход из ROM.
 *
 * Сборка: make (или make deploy — сразу в папку ROMS эмулятора PPSSPP).
 *
 * Каталог rom_data — данные для ROM (заставка).
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

/* Меню под заставкой (шрифт 8x8; цвет 8 — яркий в палитре title.bmp).
 * Картинка занимает строки 0..title_bmp_height, текст — под ней.
 * Каждая строка задаётся смещением (dx, dy) от начальной точки. */
static const struct {
    unsigned char dx;           /* смещение по горизонтали от x = 16 */
    unsigned char dy;           /* смещение по вертикали от верха меню */
    const char *text;
} menu_lines[] = {
    { 40u,  0u, "DRUMS (AY NOISE):" },
    { 0u,  16u, "1 - KICK" },
    { 0u,  32u, "2 - SNARE" },
    { 0u,  48u, "3 - HAT CLOSED" },
    { 0u,  64u, "4 - HAT OPEN" },
    { 136u, 16u, "5 - TOM" },
    { 136u, 32u, "6 - CLAP" },
    { 136u, 48u, "7 - RIM" },
    { 136u, 64u, "ESC - EXIT" },
};

static void show_menu(void)
{
    unsigned char x0 = 16u;
    unsigned char y0 = (unsigned char)(title_bmp_height + 16u);
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

    frame_handler = drum_tick;      /* огибающие — из кадрового прерывания */
    drum_init();                    /* микшер: тон C выкл, шум C вкл */

    /* титульная заставка: чёрная палитра скрывает процесс распаковки,
     * по завершении — рабочая палитра картинки и текст меню */
    graph_set_black_palette();
    graph_rle_expand(title_bmp_screen_rle, 8u, 0u);
    show_menu();
    graph_set_palette(title_bmp_palette);

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {          /* реакция на нажатие, не на удержание */
            if (key == '1') {
                drum_kick();
            } else if (key == '2') {
                drum_snare();
            } else if (key == '3') {
                drum_hat_c();
            } else if (key == '4') {
                drum_hat_o();
            } else if (key == '5') {
                drum_tom();
            } else if (key == '6') {
                drum_clap();
            } else if (key == '7') {
                drum_rim();
            } else if (key == 27) {     /* СТОП (ESC) */
                break;
            }
        }
        prev_key = key;
    }

    return 0;
}
