/*
 * main.c — огонь 64×20 в 4 оттенка с ДВОЙНОЙ ОТРИСОВКОЙ (double buffer).
 *
 * Технология как в mario-dbl: экран 256×256×16 — это четыре битовые
 * плоскости; пары плоскостей образуют два независимых «буфера» по 4 цвета:
 *
 *   буфер A = E000 (вес 1) + C000 (вес 2)  → биты 0..1 цветного индекса
 *   буфер B = A000 (вес 4) + 8000 (вес 8)  → биты 2..3 цветного индекса
 *
 * Один и тот же кадр на виду определяется палитрой из 16 слотов:
 *   palA[i] = c4[i & 3]        — виден буфер A
 *   palB[i] = c4[(i >> 2) & 3] — виден буфер B
 *
 * Смена кадра = загрузка маскирующей палитры в интервале гашения
 * (gfx_set_palette внутри делает ei/halt, то есть сам синхронизируется с
 * VBlank). Отрисовка идёт в НЕвидимый буфер, поэтому гонки с лучом нет,
 * картинка не мигает и не рвётся, а скорость ограничена только временем
 * генерации и тайлинга.
 *
 * Симуляция и тайлинг — fire.asm (8080): fire_generate(power) + fire_paint(back).
 */

#include "v06.h"

/* ----------------------------- ПАЛИТРА --------------------------------
 * 4 оттенка пламени: чёрный + три красных, от тёмного к яркому.
 * Формат V06: BB_GGG_RRR.
 * ---------------------------------------------------------------------- */

static const unsigned char fire_pal4[4] = {
    V06_RGB(0, 0, 0),       /* 0: чёрный (фон)   */
    V06_RGB(2, 0, 0),       /* 1: тёмно-красный  */
    V06_RGB(5, 0, 0),       /* 2: красный        */
    V06_RGB(7, 2, 0)        /* 3: оранжевое пламя*/
};

static unsigned char palA[16], palB[16];

static void build_palettes(void)
{
    unsigned char i;
    for (i = 0; i < 16; i++) {
        palA[i] = fire_pal4[i & 3u];
        palB[i] = fire_pal4[(i >> 2) & 3u];
    }
}

/* ------------------ ГОРЯЧИЕ ФУНКЦИИ (см. fire.asm) --------------------
 * rnd_init дополнительно обнуляет fire_buf (BSS при --no-crt не обнуляется).
 * ---------------------------------------------------------------------- */

extern void rnd_init(void) __z88dk_callee;
extern void fire_generate(unsigned char power) __z88dk_callee;
extern void fire_paint(unsigned char back) __z88dk_callee;

/* ----------------------------- FPS-ИНДИКАТОР --------------------------
 * Рисуется в ОБА буфера сразу: виден тот, чья маска сейчас в палитре, так
 * что одна печать на «текущий» буфер давала бы мерцание HUD через кадр.
 * Pen: 3 → биты 0..1 (маска 0x03, буфер A), 15 → биты 2..3 (маска 0x0C,
 * буфер B) — в обоих случаях это самый яркий оттенок своей четвёрки.
 * Строки 0..7 (верхние 8 экрановых строк) находятся вне огненной зоны.
 * Колонки 12..19 — по центру 32-колоночного экрана.
 * ---------------------------------------------------------------------- */

static volatile unsigned char *fc_lo;   /* мл. байт frame_count (0..255) */
static unsigned char prev_fc;
static unsigned char vblanks;
static unsigned char flips;
static unsigned int fps10;              /* fps × 10: «05.5» отличает 9 кадров */
                                        /* на флип от 10 (5.55 против 5.00)  */

static void hud_draw(unsigned char planes, unsigned char pen)
{
    unsigned char d0 = (unsigned char)('0' + fps10 / 100u);
    unsigned char d1 = (unsigned char)('0' + (fps10 / 10u) % 10u);
    unsigned char d2 = (unsigned char)('0' + fps10 % 10u);

    gfx_active_planes = planes;
    gfx_print(12, 0, "FPS=", pen);
    gfx_put_char(16, 0, (char)d0, pen);
    gfx_put_char(17, 0, (char)d1, pen);
    gfx_put_char(18, 0, '.', pen);
    gfx_put_char(19, 0, (char)d2, pen);
}

static void hud_update(void)
{
    unsigned char f = *fc_lo;
    unsigned char d = f - prev_fc;      /* VBlank'ов с прошлого замера */
    prev_fc = f;
    vblanks += d;
    flips++;

    if (vblanks >= 100) {               /* окно ~2 с */
        fps10 = (unsigned int)flips * 500u / vblanks;
        vblanks = 0;
        flips = 0;

        hud_draw(0x03, 3);              /* буфер A */
        hud_draw(0x0C, 15);             /* буфер B */
        gfx_active_planes = 0x0F;
    }
}

/* ----------------------------- MAIN ---------------------------------- */

int main(void)
{
    unsigned char back = 0;             /* куда рисуем на этом витке */

    gfx_set_black_palette();
    gfx_set_mode(GFX_MODE_256_16);
    gfx_clear(0);                       /* все четыре плоскости → чёрный */
    build_palettes();
    rnd_init();

    fc_lo = (volatile unsigned char *)&frame_count;
    prev_fc = *fc_lo;
    fps10 = 0;
    hud_draw(0x03, 3);                  /* рамка «FPS=» видна с первого кадра */
    hud_draw(0x0C, 15);
    gfx_active_planes = 0x0F;

    gfx_set_palette(palA);              /* показать буфер A (он пуст) */

    /* Основной цикл: скорость = сколько витков умещается в один VBlank-интервал.
     * gfx_set_palette сам ждёт VBlank и пишет палитру в гашении, поэтому
     * отдельный gfx_next_frame() в цикле не нужен. */
    for (;;) {
        fire_generate(153);             /* ~60% очагов в базовой строке */
        fire_paint(back);
        hud_update();
        gfx_set_palette(back ? palB : palA);
        back ^= 1;
    }
}
