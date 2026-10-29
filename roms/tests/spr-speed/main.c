/*
 * main.c — spr-speed: бенчмарк старого алгоритма вывода спрайтов (tile-prefab).
 * Выводит на экран анимацию идущего влево Марио (3 фазы) с замером времени
 * через таймер КР580ВИ53 канал 2 (96 тиков/строку растра).
 *
 * Методика:
 *   КР580ВИ53 канал 2 = «секундомер растра», пущен в VBlank (frame_handler ->
 *   timer_start). timer_elapsed() до/после вызова draw_sprite_old() => тики.
 *   Итог в volatile bm_*. Строки/операцию = bm_* / 96.
 *
 * Что меряем:
 *   bm_old_draw  — время одного вызова draw_sprite_old (тики VI53).
 *   bm_old_total — время пачки из R_OLD вызовов (среднее на один).
 *   bm_old_anim  — время анимации 3 кадров (последовательный вывод всех фаз).
 *
 * После замера ROM крутит анимацию Марио в цикле: каждый кадр — новая фаза
 * (0..2), визуально — идущий влево Марио на одном месте.
 */

#include "v06.h"
#include "mario_old.inc"      /* спрайты идущего влево Марио (tile-prefab) */
#include "mario_new.inc"      /* спрайты идущего влево Марио (SPR_FORMAT) */

/* Старый алгоритм вывода спрайта (spr_old.asm, tile-prefab формат).
 * Параметры передаются через глобалы rs_* — без стековых аргументов. */
extern void mario_draw_sprite(void);
unsigned int  rs_spr;                    /* указатель на спрайт (заголовок)  */
unsigned int  rs_p0, rs_p1;              /* VRAM-указатели верха колонки     */
unsigned char rs_cols;                   /* знаковый счётчик колонок (-w..0) */
unsigned char rs_frac;                   /* суб-клеточный сдвиг: 0 или 4 px */

/* Новый алгоритм вывода спрайта (spr_new.asm, SPR_FORMAT).
 * Параметры передаются через стек: draw_sprite_new(x, y, desc).
 * __z88dk_callee: каллее сам снимает аргументы со стека (16-битные слоты),
 * вызывающий код стек не чистит — как у lib/gfx/pr.asm (gfx_print). */
extern void draw_sprite_new(unsigned char x, unsigned int y,
                            const unsigned char *desc) __z88dk_callee;

/* Зачистка фона под спрайтом (spr_new.asm): нули в П0 (E000) и П1 (C000). */
extern void erase_sprite_box(unsigned char x, unsigned char y,
                             unsigned char wcells,
                             unsigned char hpix) __z88dk_callee;

/* ------------------------------ ПАЛИТРА -------------------------------- */
/* Палитра из mario-dbl: 0=голубой(небо), 1=красный, 2=розовый, 3=чёрный.
 * Текст выводится в фоновых плоскостях (цвет 4 = белый, слот палитры 4). */
static unsigned char pal16[16] = {
    0xEB, 0x07, 0xF7, 0x00,   /* 0..3: цвета Марио */
    0xFF, 0xFF, 0xFF, 0xFF,   /* 4..7: белые (для текста) */
    0x00, 0x00, 0x00, 0x00,   /* 8..11 */
    0x00, 0x00, 0x00, 0x00    /* 12..15 */
};

/* --------------------------- РЕЗУЛЬТАТЫ (volatile) --------------------- */
volatile unsigned int bm_old_draw;   /* время одного draw_sprite_old (тики) */
volatile unsigned int bm_old_total;  /* общее время N вызовов (тики)        */
volatile unsigned int bm_old_anim;   /* время анимации 3 кадров (тики)      */
volatile unsigned int bm_new_draw;   /* время одного draw_sprite_new (тики) */
volatile unsigned int bm_new_total;  /* общее время N вызовов (тики)        */
volatile unsigned int bm_new_anim;   /* время анимации 3 кадров (тики)      */
volatile unsigned int bm_magic;      /* 0xBEEF = замер выполнен            */

#define R_OLD 3u

/* ------------------------------ CADR-ISR ------------------------------- */
static void spr_frame(void)
{
    timer_start();          /* секундомер растра: старт на каждый VBlank */
}

/* ------------------- СТАРЫЙ АЛГОРИТМ (tile-prefab) -------------------- */
/* Вывод спрайта старым алгоритмом (spr_old.asm, tile-prefab формат).
 * Параметры: x, y — координаты левого верха спрайта (кратны 8),
 *            spr — указатель на спрайт (заголовок tile-prefab).
 * Плоскости: E000h (вес 1) и C000h (вес 2) — младшие 2 бита палитры. */
static void draw_sprite_old(unsigned char x, unsigned int y, const unsigned char *spr)
{
    unsigned char wcells = spr[0];
    unsigned int col = x >> 3;
    rs_p0   = 0xE000u + col * 0x100u + (255u - y);
    rs_p1   = rs_p0 - 0x2000u;
    rs_spr  = (unsigned int)spr;
    rs_cols = (unsigned char)(-(int)wcells);
    rs_frac = 0;                        /* побайтовый вывод без сдвига */
    mario_draw_sprite();
}

/* --------------------------- УТИЛИТЫ ----------------------------------- */
static const char hex_digits[] = "0123456789ABCDEF";

/* Вывод 16-битного числа в hex (4 цифры) по адресу (col, y). */
static void print_hex_u16(unsigned char col, unsigned char y, unsigned int v)
{
    char buf[5];
    buf[0] = hex_digits[(v >> 12) & 0x0F];
    buf[1] = hex_digits[(v >>  8) & 0x0F];
    buf[2] = hex_digits[(v >>  4) & 0x0F];
    buf[3] = hex_digits[ v        & 0x0F];
    buf[4] = '\0';
    gfx_print(col, y, buf, 4);
}

/* ------------------------------ ЗАМЕРЫ --------------------------------- */
static void measure(void)
{
    unsigned char old_x = 0;            /* x левого края спрайта (кратен 8) */
    unsigned char old_y = 8;            /* y верха: уровень надписи OLD ENGINE */
    unsigned char new_y = 56;           /* y верха: уровень надписи NEW ENGINE */
    unsigned char phase;
    unsigned int e0, e1;
    unsigned char i;

    /* 1) Одиночный вызов draw_sprite_old: замер времени одного вывода. */
    v06_wait_frame();
    e0 = timer_elapsed();
    draw_sprite_old(old_x, old_y, mario_frames_old[0]);
    e1 = timer_elapsed();
    bm_old_draw = e1 - e0;

    /* 2) Пачка из R_OLD вызовов: среднее время одного вывода. */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_OLD; ++i)
        draw_sprite_old(old_x, old_y, mario_frames_old[i % 3]);
    e1 = timer_elapsed();
    bm_old_total = e1 - e0;

    /* 3) Анимация 3 кадров: последовательный вывод всех фаз. */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (phase = 0; phase < 3; ++phase)
        draw_sprite_old(old_x, old_y, mario_frames_old[phase]);
    e1 = timer_elapsed();
    bm_old_anim = e1 - e0;

    /* === Замеры нового алгоритма (SPR_FORMAT) === */
    /* 4) Одиночный вызов draw_sprite_new: замер времени одного вывода. */
    v06_wait_frame();
    e0 = timer_elapsed();
    draw_sprite_new(old_x, new_y, mario_frames_new[0]);
    e1 = timer_elapsed();
    bm_new_draw = e1 - e0;

    /* 5) Пачка из R_OLD вызовов: среднее время одного вывода. */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_OLD; ++i)
        draw_sprite_new(old_x, new_y, mario_frames_new[i % 3]);
    e1 = timer_elapsed();
    bm_new_total = e1 - e0;

    /* 6) Анимация 3 кадров: последовательный вывод всех фаз. */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (phase = 0; phase < 3; ++phase)
        draw_sprite_new(old_x, new_y, mario_frames_new[phase]);
    e1 = timer_elapsed();
    bm_new_anim = e1 - e0;

    bm_magic = 0xBEEFu;
}

/* -------------------------------- MAIN --------------------------------- */
int main(void)
{
    unsigned char phase = 0;
    volatile unsigned char *fc_lo;
    unsigned char last_fc;

    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_palette(pal16);
    gfx_fill_planes(0x0F, 0x00);          /* все плоскости = 0 (чёрный фон) */

    frame_handler = spr_frame;
    timer_start_sync();

    /* Статичный текст: заголовок и подписи метрик (фоновые плоскости, цвет 4). */
    gfx_active_planes = 0x0C;             /* только фоновые биты 2..3 */
    gfx_print(8, 8, "OLD ENGINE", 4);
    gfx_print(8, 24, "DRAW:", 4);
    gfx_print(8, 32, "TOTAL:", 4);
    gfx_print(8, 40, "ANIM:", 4);
    gfx_print(8, 56, "NEW ENGINE", 4);
    gfx_print(8, 72, "DRAW:", 4);
    gfx_print(8, 80, "TOTAL:", 4);
    gfx_print(8, 88, "ANIM:", 4);
    gfx_active_planes = 0x0F;

    measure();

    /* Вывод результатов замера (фоновые плоскости, цвет 4). */
    gfx_active_planes = 0x0C;
    print_hex_u16(16, 24, bm_old_draw);
    print_hex_u16(16, 32, bm_old_total);
    print_hex_u16(16, 40, bm_old_anim);
    print_hex_u16(16, 72, bm_new_draw);
    print_hex_u16(16, 80, bm_new_total);
    print_hex_u16(16, 88, bm_new_anim);
    gfx_active_planes = 0x0F;

    /* Замер выполнен — крутим анимацию Марио в цикле. */
    fc_lo   = (volatile unsigned char *)&frame_count;
    last_fc = *fc_lo;

    for (;;) {
        /* Ждём нового VBlank. */
        while (*fc_lo == last_fc) { }
        last_fc = *fc_lo;

        /*
         * Зачистка фона перед выводом: спрайты рисуются OR/перезаписью,
         * поэтому без erase старые фазы накладываются друг на друга.
         */
        erase_sprite_box(0, 8, 3, 32);    /* под старым Марио (уровень OLD) */
        erase_sprite_box(0, 56, 3, 32);   /* под новым Марио (уровень NEW) */

        /* Выводим текущую фазу анимации. */
        draw_sprite_old(0, 8, mario_frames_old[phase]);
        draw_sprite_new(0, 56, mario_frames_new[phase]);

        /* Следующая фаза. */
        phase = (phase + 1) % 3;
    }

    return 0;
}
