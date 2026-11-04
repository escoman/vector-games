/*
 * main.c — boot-demo: ROM-заставка под второй загрузчик (stage-2).
 *
 * Спека: docs/LOADER_TZ.MD, ручная проверка: §9.5.
 *
 * Сценарий:
 *   1. boot-demo.rom — ПЕРВЫЙ файл на ленте, грузится штатно (монитором
 *      Вектора либо как обычная ROM в эмуляторе: stage-2 нужен только для
 *      второго файла);
 *   2. заставка рисует табличку, пульсирует бордюром и ждёт любую клавишу;
 *   3. loader_boot() НЕ ВОЗВРАЩАЕТСЯ: копирует blob в 0xE000, гасит
 *      прерывания и передаёт управление stage-2 — тот стирает 0x0000..0xDFFF
 *      (вместе с этой заставкой), рисует карту загрузки и принимает следующий
 *      файл ленты в 0x0100.
 *
 * Вторым на ленту кладём любой ROM, адресуемый 0x0100 и не длиннее 48896 Б:
 *
 *   python3 utils/rom2wav.py roms/tests/cls/cls.rom cls.wav
 *
 * Возврата в заставку нет ни у loader_boot(), ни у stage-2 — срывать приём
 * можно только перезагрузкой машины с клавиатуры (СБРОС).
 */

#include "v06.h"

/* Бордюр пульсирует по кругу: показывает, что заставка жива, и заодно
 * тренирует запись палитры/порта в гашении — то же делает stage-2. */
static const unsigned char border_cycle[8] = { 1, 2, 4, 6, 9, 11, 13, 15 };

/* 0 — чёрный, 15 — белый, дальше плавный серый градиент (0bBB_GGG_RRR). */
static const unsigned char splash_palette[16] = {
    0x00, 0x4A, 0x4A, 0x94, 0x94, 0xB6, 0xB6, 0xDE,
    0xDE, 0xE7, 0xE7, 0xF0, 0xF0, 0xF8, 0xF8, 0xFF
};

/* Ожидание фронта любой клавиши. Кадры ждём через v06_wait_frame(): он
 * спит до кадрового прерывания, матрицу опрашивает kbd_scan(). */
static void wait_any_key(void)
{
    unsigned char prev = kbd_scan();
    unsigned char tick = 0;

    for (;;) {
        unsigned char key;

        v06_wait_frame();

        /* Бордюр: биты 0..3 порта B, бит 4 (режим 512x256) не трогаем. */
        if ((++tick & 7) == 0) {
            unsigned char pb = v06_in(V06_PIA_PB) & 0xF0;
            v06_out(V06_PIA_PB,
                    pb | border_cycle[(tick >> 3) & 7]);
        }

        key = kbd_scan();
        if (key != 0 && key != prev)
            return;
        prev = key;
    }
}

int main(void)
{
    gfx_clear(0);
    gfx_set_palette(splash_palette);
    v06_out(V06_PIA_PB, 0);             /* бордюр чёрный, режим 256x256 */

    gfx_print(2,  32, "VECTOR-06C",                 15u);
    gfx_print(2,  48, "STAGE-2 TAPE LOADER DEMO",   11u);
    gfx_print(2,  80, "STAGE-2 RUNS AT 0E000",       7u);
    gfx_print(2,  96, "NEXT FILE LOADS AT 0100",     7u);
    gfx_print(2, 112, "MAX SIZE 48896 BYTES",        7u);
    gfx_print(2, 152, "PRESS ANY KEY",              14u);
    gfx_print(2, 176, "THEN PLAY THE SECOND TAPE",  11u);
    gfx_print(2, 232, "NO RETURN FROM HERE",         7u);

    wait_any_key();

    /* Управление уходит в 0xE000 навсегда, return ниже недостижим
     * (он только для линковки: sccz80 не переваривает пустой for(;;)). */
    loader_boot();

    return 0;
}
