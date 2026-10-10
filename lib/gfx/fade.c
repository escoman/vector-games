/*
 * fade.c — плавное появление / гашение экрана интерполяцией палитры.
 *
 * Обе публичные функции только пересчитывают 16-слотовую палитру на один
 * шаг и зовут существующий gfx_set_palette — всю остальную работу
 * (раскладку по видеорежиму и запись в кадровом гасящем интервале) делает
 * он. Модуль ничего не добавляет в gfx.c / mode.c и не ведёт общей тени.
 *
 * Формат байта цвета 0bRRRGGGBB (см. v06.h): R — биты 0-2 (0..7),
 * G — биты 3-5 (0..7), B — биты 6-7 (0..3). За один шаг каждый канал
 * сдвигается ровно на 1 грань к цели, поэтому яркость меняется линейно
 * (чёрный <-> заданный цвет).
 *
 * hold — скорость перехода: сколько кадров держать каждый промежуточный
 * шаг. Одна загрузка палитры (v06_set_palette_asm внутри gfx_set_palette)
 * сама стоит один кадр (ei/halt ловит гашение), так что hold считает и его:
 * hold = 1 — смена каждый кадр (быстро), больше — медленнее.
 *
 * ВАЖНО про стек. Стек ROM-а Вектора — 256 байт под SP (STACK_TOP 0x0100),
 * а во время ei/halt внутри gfx_set_palette сверху приходит кадровое
 * прерывание. Рабочие массивы палитры поэтому держим СТАТИЧЕСКИМИ: локальный
 * unsigned char cur[16] на стеке вытесняет SP за 0x0000 в видеопамять —
 * PUSH портят экран, POP возвращают мусор, программа уходит вразнос.
 */

#include "v06.h"

static unsigned char fade_cur[16];  /* текущий промежуточный шаг        */
static unsigned char fade_goal[16]; /* цель gfx_fade_in — от неё гасим  */

/* Один шаг канала p -> dst: приблизить на 1 грань. */
static unsigned char fade_step(unsigned char p, unsigned char dst)
{
    unsigned char r = p & 7u;
    unsigned char g = (p >> 3) & 7u;
    unsigned char b = (p >> 6) & 3u;

    if ((dst & 7u) > r)             ++r;
    else if ((dst & 7u) < r)        --r;

    if (((dst >> 3) & 7u) > g)      ++g;
    else if (((dst >> 3) & 7u) < g) --g;

    if (((dst >> 6) & 3u) > b)      ++b;
    else if (((dst >> 6) & 3u) < b) --b;

    return (unsigned char)(r | (g << 3) | (b << 6));
}

/* Все 16 слотов уже равны цели? */
static unsigned char fade_reached(const unsigned char *cur,
                                  const unsigned char *dst)
{
    unsigned char i;

    for (i = 0; i < 16; i++)
        if (cur[i] != dst[i])
            return 0;
    return 1;
}

/* Все 16 слотов чёрные (байт == 0)? */
static unsigned char fade_black(const unsigned char *cur)
{
    unsigned char i;

    for (i = 0; i < 16; i++)
        if (cur[i])
            return 0;
    return 1;
}

/* Дождаться конца шага: загрузка палитры уже стоила один кадр, держим
 * ещё (hold - 1). */
static void fade_hold(unsigned char hold)
{
    while (hold > 1) {
        v06_wait_frame();
        --hold;
    }
}

/* Появление: от полностью чёрного экрана к палитре pal, hold кадров на шаг.
 * Экран до вызова должен быть чёрным (gfx_set_black_palette) — тогда ничего
 * не мелькнёт до первого шага. */
void gfx_fade_in(const unsigned char *pal, unsigned char hold)
{
    unsigned char i;

    for (i = 0; i < 16; i++) {
        fade_cur[i]  = 0;         /* старт от чёрного           */
        fade_goal[i] = pal[i];    /* запомнить цель для fade_out */
    }

    for (;;) {
        for (i = 0; i < 16; i++)
            fade_cur[i] = fade_step(fade_cur[i], fade_goal[i]);
        gfx_set_palette(fade_cur);
        fade_hold(hold);
        if (fade_reached(fade_cur, fade_goal))
            break;
    }
}

/* Гашение: от палитры, которую показал gfx_fade_in, к чёрному. */
void gfx_fade_out(unsigned char hold)
{
    unsigned char i;

    for (i = 0; i < 16; i++)
        fade_cur[i] = fade_goal[i];   /* старт от последней показанной */

    for (;;) {
        for (i = 0; i < 16; i++)
            fade_cur[i] = fade_step(fade_cur[i], 0);
        gfx_set_palette(fade_cur);
        fade_hold(hold);
        if (fade_black(fade_cur))
            break;
    }
}
