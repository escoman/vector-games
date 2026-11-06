/*
 * main.c — boot-demo: ROM-заставка под второй загрузчик (stage-2).
 *
 * Спека: docs/LOADER_TZ.MD, ручная проверка: §9.5.
 *
 * Сценарий:
 *   1. boot-demo.rom — ПЕРВЫЙ файл на ленте, грузится штатно (монитором
 *      Вектора либо как обычная ROM в эмуляторе: stage-2 нужен только для
 *      второго файла);
 *   2. заставка рисует табличку, ставит чёрный бордюр и ждёт любую клавишу
 *      (`kbd_wait_any_key()` из lib/kbd — фронт-детектор, кадр за кадром);
 *   3. loader_boot_cfg(&cfg) НЕ ВОЗВРАЩАЕТСЯ: копирует blob в 0xE000, гасит
 *      прерывания и передаёт управление stage-2 — тот стирает 0x0000..0xDFFF
 *      (вместе с этой заставкой), рисует панели из cfg в углы экрана, поверх
 *      них — карту загрузки и принимает следующий файл ленты в 0x0100.
 *
 * Вторым на ленту кладём любой ROM, адресуемый 0x0100 и не длиннее 48896 Б:
 *
 *   python3 utils/rom2wav.py roms/tests/cls/cls.rom cls.wav
 *
 * Возврата в заставку нет ни у loader_boot(), ни у stage-2 — срывать приём
 * можно только перезагрузкой машины с клавиатуры (СБРОС).
 */

#include "v06.h"

/* Данные панелей и их геометрия — сгенерированы из assets/panel_*.png
 * (utils/png2panel.py, правило `panels` в Makefile). НЕ ПРАВИТЬ вручную. */
#include "include/panel_top.h"
#include "include/panel_bottom.h"

/* Конфиг второго загрузчика (docs/LOADER_TZ.MD §4.2, §5.2): фон/линии как на
 * эталоне плюс две картинки в углы. Указатели на данные смотрят в эту ROM —
 * стаб переложит картинки в слоты high RAM до стирания. */
static const struct loader_cfg loader_cfg = {
    0x00, V06_RGB(5,5,2),                                    /* фон, линии */
    { PANEL_TOP_X,    PANEL_TOP_Y,    PANEL_TOP_WB,    PANEL_TOP_H    },
    { PANEL_BOTTOM_X, PANEL_BOTTOM_Y, PANEL_BOTTOM_WB, PANEL_BOTTOM_H },
    panel_top, panel_bottom
};

/* 0 — чёрный, 15 — белый, дальше плавный серый градиент (0bBB_GGG_RRR). */
static const unsigned char splash_palette[16] = {
    0x00, 0x4A, 0x4A, 0x94, 0x94, 0xB6, 0xB6, 0xDE,
    0xDE, 0xE7, 0xE7, 0xF0, 0xF0, 0xF8, 0xF8, 0xFF
};

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

    kbd_wait_any_key();

    gfx_clear(0);
    gfx_set_black_palette();

    /* Управление уходит в 0xE000 навсегда, return ниже недостижим
     * (он только для линковки: sccz80 не переваривает пустой for(;;)). */
    loader_boot_cfg(&loader_cfg);

    return 0;
}
