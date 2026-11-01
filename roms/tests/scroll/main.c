/*
 * roms/tests/scroll/main.c — тест синхронизации луча и регистра скролла.
 *
 * Цель: понять, как меняется содержимое экрана при записи в порт скролла 03h
 * в разные моменты кадра относительно позиции луча.
 *
 * VRAM 256x256 (GFX_MODE_256_16): 256 строк, кольцевой буфер.
 * Регистр скролла (порт 03h) = VRAM-строка, которую луч читает на физ. линии 0.
 * Луч сканирует УБЫВАЯ: на физ. линии y читает VRAM[(scroll - y) & 0xFF].
 *
 * Тест рисует градиент: каждая VRAM-строка заполнена своим цветом (0-15).
 * При скролле видно, какие строки попадают на экран. Если регистр меняется
 * когда луч уже прошёл часть кадра, верхняя часть показывает старое,
 * нижняя — новое содержимое (разрыв на границе).
 *
 * Управление:
 *   UP/DOWN     — сдвиг скролла на ±1
 *   LEFT/RIGHT  — сдвиг на ±16
 *   SPACE       — пометить кадр для снимка (пишет метку в VRAM)
 *   ESC         — выход
 */

#include "v06.h"

/* Палитра 16 цветов: радуга (формат V06_RGB: r=0-7, g=0-7, b=0-3). */
static const unsigned char pal16[16] = {
    V06_RGB(0, 0, 0),   /* 0  чёрный   */
    V06_RGB(7, 0, 0),   /* 1  красный   */
    V06_RGB(7, 3, 0),   /* 2  оранжевый */
    V06_RGB(7, 7, 0),   /* 3  жёлтый    */
    V06_RGB(0, 7, 0),   /* 4  зелёный   */
    V06_RGB(0, 7, 3),   /* 5  голубой   */
    V06_RGB(0, 0, 3),   /* 6  синий     */
    V06_RGB(7, 0, 3),   /* 7  фиолетовый*/
    V06_RGB(7, 7, 3),   /* 8  белый     */
    V06_RGB(3, 0, 0),   /* 9  тёмн.-красн. */
    V06_RGB(3, 3, 0),   /* 10 тёмн.-жёлт.  */
    V06_RGB(0, 3, 0),   /* 11 тёмн.-зел.   */
    V06_RGB(0, 3, 3),   /* 12 тёмн.-голуб. */
    V06_RGB(0, 0, 1),   /* 13 тёмн.-син.   */
    V06_RGB(3, 0, 3),   /* 14 тёмн.-фиол.  */
    V06_RGB(3, 3, 3),   /* 15 серый     */
};

/* Заполнить VRAM-строку row цветом color.
 * Адрес: 0xE000 + col * 0x100 + (255 - row), col = 0..31. */
static void fill_vram_row(unsigned char row, unsigned char color)
{
    unsigned char col;
    for (col = 0; col < 32; col++) {
        *(unsigned char *)(0xE000u + (unsigned int)col * 0x100u + (255u - row)) = color;
    }
}

/* Нарисовать градиент: VRAM-строка i заполнена цветом (i & 15). */
static void draw_gradient(void)
{
    unsigned int i;
    for (i = 0; i < 256; i++) {
        fill_vram_row((unsigned char)i, (unsigned char)(i & 15));
    }
}

/* Преобразовать число в строку (для вывода scroll/beam). */
static void num_to_str(unsigned int n, char *buf, unsigned char digits)
{
    unsigned char i;
    buf[digits] = 0;
    for (i = digits; i > 0; i--) {
        buf[i - 1] = '0' + (n % 10);
        n /= 10;
    }
}

/* Показать статус: текущий scroll и beam position. */
static void show_status(unsigned char scroll, unsigned int beam_elapsed)
{
    char buf[16];

    /* Очистить область статуса (строки 0-15, колонки 0-7). */
    unsigned char row;
    for (row = 0; row < 16; row++) {
        fill_vram_row(row, 0);  /* чёрный фон */
    }

    /* Scroll value. */
    gfx_print(0, 0, "SCR:", 8);  /* белый */
    num_to_str(scroll, buf, 3);
    gfx_print(32, 0, buf, 8);

    /* Beam elapsed (тики таймера). */
    gfx_print(0, 8, "BEAM:", 8);
    num_to_str(beam_elapsed, buf, 5);
    gfx_print(40, 8, buf, 8);

    /* Строка луча. */
    gfx_print(0, 16, "LINE:", 8);
    num_to_str(beam_elapsed / 96, buf, 3);
    gfx_print(40, 16, buf, 8);
}

int main(void)
{
    unsigned char scroll = 0xFF;  /* начальный scroll */
    unsigned char prev_key;
    unsigned int beam;
    char marker;

    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_palette(pal16);

    /* Нарисовать градиент. */
    draw_gradient();

    /* Установить начальный scroll. */
    gfx_set_scroll(scroll);
    gfx_next_frame();  /* дождаться VBlank для применения */

    prev_key = kbd_scan();

    for (;;) {
        gfx_next_frame();

        /* Измерить позицию луча. */
        beam = timer_elapsed();

        /* Показать статус (в VRAM-строках 0-15, которые перекрывают градиент). */
        show_status(scroll, beam);

        /* Сканировать клавиатуру. */
        unsigned char key = kbd_scan();

        /* Обработка нажатий (по фронту). */
        if (key != 0 && key != prev_key) {
            switch (key) {
            case KBD_KEY_ESC:
                goto done;

            case KBD_KEY_UP:
                scroll++;  /* сдвиг на 1 вверх (VRAM-строка растёт) */
                break;

            case KBD_KEY_DOWN:
                scroll--;  /* сдвиг на 1 вниз */
                break;

            case KBD_KEY_RIGHT:
                scroll += 16;  /* быстрый сдвиг */
                break;

            case KBD_KEY_LEFT:
                scroll -= 16;
                break;

            case KBD_KEY_F1:
                /* Пометить кадр: записать маркер в VRAM-строку 128. */
                fill_vram_row(128, 8);  /* белая полоса посередине */
                break;
            }

            /* Применить новый scroll: немедленная запись в порт. */
            gfx_scroll_row = scroll;
            v06_out(V06_PIA_PA, scroll);
        }

        prev_key = key;
    }

done:
    gfx_clear(0);
    return 0;
}
