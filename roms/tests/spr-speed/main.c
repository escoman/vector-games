/*
 * main.c — spr-speed: бенчмарк старого алгоритма вывода спрайтов (tile-prefab).
 * Выводит на экран анимацию идущего влево Марио (3 фазы) с замером времени
 * через таймер КР580ВИ53 канал 2 (96 тиков/строку растра).
 *
 * Методика:
 *   КР580ВИ53 канал 2 = «секундомер растра», пущен в VBlank (frame_handler ->
 *   timer_start). Длительность = t_span() после блока работы: разность
 *   timer_elapsed() плюс TIMER_FULL за каждый пересечённый VBlank (якорь по
 *   frame_count) — иначе пачки длиннее кадра занижаются ровно на кадр.
 *   Итог в volatile bm_*. Строки/операцию = bm_* / 96.
 *
 * Что меряем:
 *   bm_old_draw  — время одного вызова draw_sprite_old (тики VI53).
 *   bm_old_total — время пачки из R_OLD вызовов (среднее на один).
 *   bm_old_anim  — время анимации 3 кадров (последовательный вывод всех фаз).
 * То же для draw_sprite_new (SPR_FORMAT, flat) — bm_new_*.
 * И для варианта с маской (OR-композит, без erase) — bm_mask_*,
 * плюс bm_mask_fill — время заливки шахматной подложки.
 * И для SMC-ядра (обработчик столбца + развёрнутая «лесенка») — bm_smc_*:
 * те же дескрипторы, что у draw_sprite_new, другой блиттер.
 * Пары движков: SMC с маской (spr_smc.asm) — bm_smc_mask_*; STUB и STUB с
 * маской (spr_stub.asm; маска плоскостей и COLS развёрнуты при сборке) —
 * bm_stub_*, bm_stub_mask_*.
 *
 * После замера ROM крутит семь сцен по очереди (round-robin — по одной на
 * кадр), по колонкам экрана: слева OLD / NEW / MASK / SMC / SMC+MSK, справа
 * STUB / STUB+MSK — чтобы каждая сцена успевала дорисоваться до прохода луча:
 * стирание + вывод одной сцены — ~180 строк растра, всемером в кадр не лезут.
 */

#include "v06.h"
#include "mario_old.inc"      /* спрайты идущего влево Марио (tile-prefab) */
#include "mario_new.inc"      /* спрайты идущего влево Марио (SPR_FORMAT) */
#include "mario_new_mask.inc" /* они же: маска первой + прогоны плоскостей */

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

/* OR-композит с маской (spr_new.asm): dst = (dst AND mask) OR color.
 * Маска лежит первым блоком DATA — erase под спрайтом не нужен. */
extern void draw_sprite_new_mask(unsigned char x, unsigned int y,
                                 const unsigned char *desc) __z88dk_callee;

/* Шахматная подложка (spr_new.asm): строки 0xFF/0xAA в П0 и П1. */
extern void fill_checker(unsigned char x, unsigned char y,
                         unsigned char wcells,
                         unsigned char hpix) __z88dk_callee;

/* SMC-ядро (spr_smc.asm): flat-вывод — обработчик столбца + лесенка в ОЗУ. */
extern void draw_sprite_smc(unsigned char x, unsigned int y,
                            const unsigned char *desc) __z88dk_callee;
/* Пара к нему: та же лесенка, но с OR-композитом по маске
 * (dst = (dst AND mask) OR color) — дескриптор с маской. */
extern void draw_sprite_smc_mask(unsigned char x, unsigned int y,
                                 const unsigned char *desc) __z88dk_callee;
/* STUB-ядро (spr_stub.asm): линейный стаб класса — маска плоскостей и число
 * столбцов развёрнуты при сборке, в кадре ни загрузки флагов, ни ветвлений. */
extern void draw_sprite_stub(unsigned char x, unsigned int y,
                             const unsigned char *desc) __z88dk_callee;
/* Пара к нему: тот же стаб, но столбцы компонуются по маске. */
extern void draw_sprite_stub_mask(unsigned char x, unsigned int y,
                                  const unsigned char *desc) __z88dk_callee;
/* Сборка лесенок в ОЗУ (копирование 0x7000, композиция 0x7100) — один раз. */
extern void smc_init(void);

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
volatile unsigned int bm_mask_draw;  /* один draw_sprite_new_mask (тики)    */
volatile unsigned int bm_mask_total; /* N вызовов с маской (тики)           */
volatile unsigned int bm_mask_anim;  /* анимация 3 кадров с маской (тики)   */
volatile unsigned int bm_mask_fill;  /* одна заливка шахматки (тики)        */
volatile unsigned int bm_smc_draw;   /* один draw_sprite_smc (тики)         */
volatile unsigned int bm_smc_total;  /* N вызовов через RST 1 (тики)       */
volatile unsigned int bm_smc_anim;   /* анимация 3 кадров через RST 1 (тики) */
volatile unsigned int bm_smc_mask_draw;  /* один draw_sprite_smc_mask (тики) */
volatile unsigned int bm_smc_mask_total; /* N вызовов SMC с маской (тики)  */
volatile unsigned int bm_smc_mask_anim;  /* анимация 3 кадров SMC+маска  */
volatile unsigned int bm_stub_draw;  /* один draw_sprite_stub (тики)        */
volatile unsigned int bm_stub_total; /* N вызовов через стаб (тики)         */
volatile unsigned int bm_stub_anim;  /* анимация 3 кадров через стаб (тики) */
volatile unsigned int bm_stub_mask_draw;   /* один draw_sprite_stub_mask */
volatile unsigned int bm_stub_mask_total;  /* N вызовов STUB с маской    */
volatile unsigned int bm_stub_mask_anim;   /* анимация 3 кадров STUB+маска */
volatile unsigned int bm_magic;      /* 0xBEEF = замер выполнен            */

#define R_OLD 3u

/* -------------------- БЕЗОПАСНОЕ ОКНО ПОД ЛУЧОМ ----------------------- */
/* Рисование вне окна: луч проходит строки сцены (y..y+32) на растре
 * 48..127, а erase+draw занимают ~180 строк от VBlank — луч видит стёртого
 * Марио. Поэтому ждём, пока луч пройдёт НИЗ пятна (y+32), и только потом
 * erase+draw: записи идут под лучом, следующий кадр читает их готовыми.
 * RASTER_BASE=40 — raster первого видимого ряда. */
#define RASTER_BASE  40u
#define WAKE_MARGIN  4u               /* строк запаса после прохода низа     */
#define SPR_H        32u              /* высота пятна Марио                 */

/* ---------------- ЗАМЕР С ЯКОРЕМ ПО frame_count ------------------- */
/* Таймер канала 2 — счётчик на один кадр, перезаряжаемый в каждый VBlank
 * (frame_handler -> timer_start). Разность timer_elapsed() равна длительности
 * только если интервал уложился в кадр: пачка из трёх вызовов старого движка
 * (~410 строк) переваливает через VBlank, и разность оказывается занижена
 * ровно на кадр (TIMER_FULL тиков).
 *
 * Лечимся якорем по frame_count: число пересечённых VBlank домножается на
 * TIMER_FULL и добавляется к разности. Пару (кадр, elapsed) берём
 * согласованно — перечитываем, пока кадр не перестанет меняться, иначе VBlank
 * между двумя чтениями исказил бы пару. Младший байт frame_count читается
 * одним LDA (атомарно на 8080); интервалы замера — единицы кадров, поэтому
 * разности байтов достаточно (итог и так берётся по модулю 65536). */
static unsigned int t_now(unsigned char *fcp)
{
    volatile unsigned char *fc = (volatile unsigned char *)&frame_count;
    unsigned char f;
    unsigned int e;

    do {
        f  = *fc;
        e  = timer_elapsed();
    } while (*fc != f);

    *fcp = f;
    return e;
}

/* Тики VI53 от момента (e0, f0), снятого t_now(), до сейчас. */
static unsigned int t_span(unsigned int e0, unsigned char f0)
{
    unsigned char f1;
    unsigned int e1 = t_now(&f1);

    return (unsigned int)(f1 - f0) * TIMER_FULL + (e1 - e0);
}

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
    unsigned char mask_y = 104;         /* y верха: уровень MASK ENGINE */
    unsigned char smc_y = 152;          /* y верха: уровень SMC ENGINE */
    unsigned char smcm_y = 200;         /* y верха: SMC с маской (пл. STUB) */
    unsigned char stub_x = 128;         /* x начала второй колонки */
    unsigned char stub_y = 8;           /* y верха: уровень STUB ENGINE */
    unsigned char stubm_y = 56;         /* y верха: STUB с маской */
    unsigned char phase;
    unsigned int e0;
    unsigned char f0;
    unsigned char i;

    /* 1) Одиночный вызов draw_sprite_old: замер времени одного вывода. */
    v06_wait_frame();
    e0 = t_now(&f0);
    draw_sprite_old(old_x, old_y, mario_frames_old[0]);
    bm_old_draw = t_span(e0, f0);

    /* 2) Пачка из R_OLD вызовов: среднее время одного вывода. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (i = 0; i < R_OLD; ++i)
        draw_sprite_old(old_x, old_y, mario_frames_old[i % 3]);
    bm_old_total = t_span(e0, f0);

    /* 3) Анимация 3 кадров: последовательный вывод всех фаз. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (phase = 0; phase < 3; ++phase)
        draw_sprite_old(old_x, old_y, mario_frames_old[phase]);
    bm_old_anim = t_span(e0, f0);

    /* === Замеры нового алгоритма (SPR_FORMAT) === */
    /* 4) Одиночный вызов draw_sprite_new: замер времени одного вывода. */
    v06_wait_frame();
    e0 = t_now(&f0);
    draw_sprite_new(old_x, new_y, mario_frames_new[0]);
    bm_new_draw = t_span(e0, f0);

    /* 5) Пачка из R_OLD вызовов: среднее время одного вывода. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (i = 0; i < R_OLD; ++i)
        draw_sprite_new(old_x, new_y, mario_frames_new[i % 3]);
    bm_new_total = t_span(e0, f0);

    /* 6) Анимация 3 кадров: последовательный вывод всех фаз. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (phase = 0; phase < 3; ++phase)
        draw_sprite_new(old_x, new_y, mario_frames_new[phase]);
    bm_new_anim = t_span(e0, f0);

    /* === Замеры варианта с маской (OR-композит, без erase) === */
    /* 7) Заливка шахматной подложки: цена фона без erase. */
    v06_wait_frame();
    e0 = t_now(&f0);
    fill_checker(old_x, mask_y, 3, SPR_H);
    bm_mask_fill = t_span(e0, f0);

    /* 8) Одиночный вызов draw_sprite_new_mask. */
    v06_wait_frame();
    e0 = t_now(&f0);
    draw_sprite_new_mask(old_x, mask_y, mario_frames_new_mask[0]);
    bm_mask_draw = t_span(e0, f0);

    /* 9) Пачка из R_OLD вызовов. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (i = 0; i < R_OLD; ++i)
        draw_sprite_new_mask(old_x, mask_y, mario_frames_new_mask[i % 3]);
    bm_mask_total = t_span(e0, f0);

    /* 10) Анимация 3 кадров. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (phase = 0; phase < 3; ++phase)
        draw_sprite_new_mask(old_x, mask_y, mario_frames_new_mask[phase]);
    bm_mask_anim = t_span(e0, f0);

    /* === Замеры SMC-ядра (RST 1, те же дескрипторы, что у NEW) === */
    /* 11) Одиночный вызов draw_sprite_smc. */
    v06_wait_frame();
    e0 = t_now(&f0);
    draw_sprite_smc(old_x, smc_y, mario_frames_new[0]);
    bm_smc_draw = t_span(e0, f0);

    /* 12) Пачка из R_OLD вызовов. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (i = 0; i < R_OLD; ++i)
        draw_sprite_smc(old_x, smc_y, mario_frames_new[i % 3]);
    bm_smc_total = t_span(e0, f0);

    /* 13) Анимация 3 кадров. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (phase = 0; phase < 3; ++phase)
        draw_sprite_smc(old_x, smc_y, mario_frames_new[phase]);
    bm_smc_anim = t_span(e0, f0);

    /* === Замеры SMC с маской (та же лесенка, композит по маске) === */
    /* 14) Одиночный вызов draw_sprite_smc_mask. */
    v06_wait_frame();
    e0 = t_now(&f0);
    draw_sprite_smc_mask(old_x, smcm_y, mario_frames_new_mask[0]);
    bm_smc_mask_draw = t_span(e0, f0);

    /* 15) Пачка из R_OLD вызовов. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (i = 0; i < R_OLD; ++i)
        draw_sprite_smc_mask(old_x, smcm_y, mario_frames_new_mask[i % 3]);
    bm_smc_mask_total = t_span(e0, f0);

    /* 16) Анимация 3 кадров. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (phase = 0; phase < 3; ++phase)
        draw_sprite_smc_mask(old_x, smcm_y, mario_frames_new_mask[phase]);
    bm_smc_mask_anim = t_span(e0, f0);

    /* === Замеры STUB-ядра (линейный стаб, вторая колонка экрана) === */
    /* 17) Одиночный вызов draw_sprite_stub. */
    v06_wait_frame();
    e0 = t_now(&f0);
    draw_sprite_stub(stub_x, stub_y, mario_frames_new[0]);
    bm_stub_draw = t_span(e0, f0);

    /* 18) Пачка из R_OLD вызовов. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (i = 0; i < R_OLD; ++i)
        draw_sprite_stub(stub_x, stub_y, mario_frames_new[i % 3]);
    bm_stub_total = t_span(e0, f0);

    /* 19) Анимация 3 кадров. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (phase = 0; phase < 3; ++phase)
        draw_sprite_stub(stub_x, stub_y, mario_frames_new[phase]);
    bm_stub_anim = t_span(e0, f0);

    /* === Замеры STUB-ядра с маской (та же пара, дескрипторы с маской) === */
    /* 20) Одиночный вызов draw_sprite_stub_mask. */
    v06_wait_frame();
    e0 = t_now(&f0);
    draw_sprite_stub_mask(stub_x, stubm_y, mario_frames_new_mask[0]);
    bm_stub_mask_draw = t_span(e0, f0);

    /* 21) Пачка из R_OLD вызовов. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (i = 0; i < R_OLD; ++i)
        draw_sprite_stub_mask(stub_x, stubm_y, mario_frames_new_mask[i % 3]);
    bm_stub_mask_total = t_span(e0, f0);

    /* 22) Анимация 3 кадров. */
    v06_wait_frame();
    e0 = t_now(&f0);
    for (phase = 0; phase < 3; ++phase)
        draw_sprite_stub_mask(stub_x, stubm_y, mario_frames_new_mask[phase]);
    bm_stub_mask_anim = t_span(e0, f0);

    bm_magic = 0xBEEFu;
}

/* -------------------------------- MAIN --------------------------------- */
int main(void)
{
    unsigned char phase = 0;               /* текущая сцена 0..4 (round-robin) */
    unsigned char next = 0;                /* фаза анимации Марио 0..2 */
    volatile unsigned char *fc_lo;
    unsigned char last_fc;

    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_palette(pal16);
    gfx_fill_planes(0x0F, 0x00);          /* все плоскости = 0 (чёрный фон) */

    frame_handler = spr_frame;
    timer_start_sync();
    smc_init();                           /* лесенки -> 0x7000 и 0x7100 */

    /* Статичный текст: заголовок и подписи метрик (фоновые плоскости, цвет 4). */
    gfx_active_planes = 0x0C;             /* только фоновые биты 2..3 */
    unsigned char x = 4;
    gfx_print(x, 8, "OLD ENGINE", 4);
    gfx_print(x, 16, "DRAW:", 4);
    gfx_print(x, 24, "TOTAL:", 4);
    gfx_print(x, 32, "ANIM:", 4);

    gfx_print(x, 56, "NEW ENGINE", 4);
    gfx_print(x, 64, "DRAW:", 4);
    gfx_print(x, 72, "TOTAL:", 4);
    gfx_print(x, 80, "ANIM:", 4);

    gfx_print(x, 104, "MASK ENGINE", 4);
    gfx_print(x, 112, "DRAW:", 4);
    gfx_print(x, 120, "TOTAL:", 4);
    gfx_print(x, 128, "ANIM:", 4);
    gfx_print(x, 136, "FILL:", 4);

    gfx_print(x, 152, "SMC ENGINE", 4);
    gfx_print(x, 160, "DRAW:", 4);
    gfx_print(x, 168, "TOTAL:", 4);
    gfx_print(x, 176, "ANIM:", 4);

    gfx_print(x, 200, "SMC MASK", 4);
    gfx_print(x, 208, "DRAW:", 4);
    gfx_print(x, 216, "TOTAL:", 4);
    gfx_print(x, 224, "ANIM:", 4);

    /* Вторая колонка: спрайты с x=128, подписи — за ними. */
    x = 20;
    gfx_print(x, 8, "STUB ENGINE", 4);
    gfx_print(x, 16, "DRAW:", 4);
    gfx_print(x, 24, "TOTAL:", 4);
    gfx_print(x, 32, "ANIM:", 4);

    gfx_print(x, 56, "STUB MASK", 4);
    gfx_print(x, 64, "DRAW:", 4);
    gfx_print(x, 72, "TOTAL:", 4);
    gfx_print(x, 80, "ANIM:", 4);
    gfx_active_planes = 0x0F;

    measure();

    /* Вывод результатов замера (фоновые плоскости, цвет 4). */
    gfx_active_planes = 0x0C;
    x = 11;
    print_hex_u16(x, 16, bm_old_draw);
    print_hex_u16(x, 24, bm_old_total);
    print_hex_u16(x, 32, bm_old_anim);

    print_hex_u16(x, 64, bm_new_draw);
    print_hex_u16(x, 72, bm_new_total);
    print_hex_u16(x, 80, bm_new_anim);

    print_hex_u16(x, 112, bm_mask_draw);
    print_hex_u16(x, 120, bm_mask_total);
    print_hex_u16(x, 128, bm_mask_anim);
    print_hex_u16(x, 136, bm_mask_fill);

    print_hex_u16(x, 160, bm_smc_draw);
    print_hex_u16(x, 168, bm_smc_total);
    print_hex_u16(x, 176, bm_smc_anim);

    print_hex_u16(x, 208, bm_smc_mask_draw);
    print_hex_u16(x, 216, bm_smc_mask_total);
    print_hex_u16(x, 224, bm_smc_mask_anim);

    x = 27;                             /* вторая колонка: значения за подписями */
    print_hex_u16(x, 16, bm_stub_draw);
    print_hex_u16(x, 24, bm_stub_total);
    print_hex_u16(x, 32, bm_stub_anim);

    print_hex_u16(x, 64, bm_stub_mask_draw);
    print_hex_u16(x, 72, bm_stub_mask_total);
    print_hex_u16(x, 80, bm_stub_mask_anim);
    gfx_active_planes = 0x0F;

    /* Замер выполнен — крутим семь сцен по очереди (по одной на кадр). */
    fc_lo   = (volatile unsigned char *)&frame_count;
    last_fc = *fc_lo;

    for (;;) {
        /* Ждём нового VBlank. */
        while (*fc_lo == last_fc) { }
        last_fc = *fc_lo;

        /*
         * WAKE: ждём, пока луч пройдёт НИЗ пятна текущей сцены, и только
         * затем erase+draw ПОДРЯД. Иначе луч сканирует строки Марио в момент
         * между erase и draw и на реальном экране видит пустое место.
         * Стирание и вывод одной сцены (~180 строк) успевают за кадр;
         * семь сцен вместе — нет, поэтому обновляется одна за кадр.
         */
        switch (phase) {
        case 0:                             /* OLD: erase + flat */
            timer_wait(TIMER_REMAIN(TIMER_LINES(
                RASTER_BASE + 8 + SPR_H + WAKE_MARGIN)));
            erase_sprite_box(0, 8, 3, SPR_H);
            draw_sprite_old(0, 8, mario_frames_old[next]);
            break;
        case 1:                             /* NEW: erase + flat */
            timer_wait(TIMER_REMAIN(TIMER_LINES(
                RASTER_BASE + 56 + SPR_H + WAKE_MARGIN)));
            erase_sprite_box(0, 56, 3, SPR_H);
            draw_sprite_new(0, 56, mario_frames_new[next]);
            break;
        case 2:                             /* MASK: подложка + OR-композит */
            timer_wait(TIMER_REMAIN(TIMER_LINES(
                RASTER_BASE + 104 + SPR_H + WAKE_MARGIN)));
            fill_checker(0, 104, 3, SPR_H);
            draw_sprite_new_mask(0, 104, mario_frames_new_mask[next]);
            break;
        case 3:                             /* SMC: erase + CALL столбца */
            timer_wait(TIMER_REMAIN(TIMER_LINES(
                RASTER_BASE + 152 + SPR_H + WAKE_MARGIN)));
            erase_sprite_box(0, 152, 3, SPR_H);
            draw_sprite_smc(0, 152, mario_frames_new[next]);
            break;
        case 4:                             /* SMC+MSK: подложка + композит */
            timer_wait(TIMER_REMAIN(TIMER_LINES(
                RASTER_BASE + 200 + SPR_H + WAKE_MARGIN)));
            fill_checker(0, 200, 3, SPR_H);
            draw_sprite_smc_mask(0, 200, mario_frames_new_mask[next]);
            break;
        case 5:                             /* STUB: erase + линейный стаб */
            timer_wait(TIMER_REMAIN(TIMER_LINES(
                RASTER_BASE + 8 + SPR_H + WAKE_MARGIN)));
            erase_sprite_box(128, 8, 3, SPR_H);
            draw_sprite_stub(128, 8, mario_frames_new[next]);
            break;
        default:                            /* STUB+MSK: подложка + стаб */
            timer_wait(TIMER_REMAIN(TIMER_LINES(
                RASTER_BASE + 56 + SPR_H + WAKE_MARGIN)));
            fill_checker(128, 56, 3, SPR_H);
            draw_sprite_stub_mask(128, 56, mario_frames_new_mask[next]);
            break;
        }

        /* Очередь и фаза анимации. */
        phase = (phase + 1) % 7;
        if (phase == 0)
            next = (next + 1) % 3;
    }

    return 0;
}
