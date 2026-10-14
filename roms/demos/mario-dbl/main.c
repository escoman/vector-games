/*
 * main.c — демка «double buffering» для Вектора-06Ц.
 *
 * Идея. Закрепляем две пары битовых плоскостей за двумя целыми экранами:
 *   буфер A = 0xE000 (вес 1) + 0xC000 (вес 2)  -> биты 0..1 палитрного индекса
 *   буфер B = 0xA000 (вес 4) + 0x8000 (вес 8)  -> биты 2..3 палитрного индекса
 * В режиме 256x256x16 каждый пиксель имеет 4-битный индекс = сумма весов битых
 * плоскостей. На каждый буфер приходится по 4 логических цвета (свой бит0/бит1).
 *
 * Маскировка — палитрой на 16 слотов:
 *   виден A: pal[i] = c4[i & 3]        (биты 2..3 игнорируются -> B не видно)
 *   виден B: pal[i] = c4[(i >> 2) & 3] (биты 0..1 игнорируются -> A не видно)
 * Смена палитры = смена активного буфера. v06_set_palette_asm сам делает
 * ei/halt и пишет 16 слотов в гасящем интервале, поэтому вызов смены палитры
 * уже синхронизирован с VSync — отдельный gfx_next_frame не нужен.
 *
 * Покадрово: рисуем кадр в НЕвидимый буфер (его плоскости замаскированы, экран
 * не дёргается), потом переключаем палитру — он становится видимым, а прежний
 * — скрытым. И так по кругу: максимально плавная анимация без tearing.
 *
 * Фон (текст + земля) статичен и ОДИНАКОВ в обоих буферах: рисуем его в буфер A
 * (gfx_print/тайлы — младшие биты цвета), затем копируем плоскости A -> B.
 * Двигается только спрайт Марио: каждый кадр в скрытом буфере стираем старого
 * Марио (возврат фона из RAM-тени по прежнему прямоугольнику) и рисуем нового.
 * Спрайт перекрывает текст, а когда уходит — текст возвращается из тени.
 *
 * Марио набран кубиками 8x8 (как на NES): поза = 3 клетки вширь x 4 ввысь.
 * Шаг движения 8 px => спрайт всегда выровнен по сетке => вывод целыми байтами
 * плоскостей, без побитового RMW.
 *
 * Вывод спрайта — на 8080-ассемблере (src/render.asm): спрайт закодирован
 * КОЛОНОЧНО, столбец VRAM проходится линейно (данные +3, адрес -1),
 * стирание — простое копирование из колоночной RAM-тени.
 */

#include "v06.h"

#include "src/tiles.inc"      /* screen_pal4, tile_ground */
#include "src/sprites.inc"    /* mario_frames[N][2], mario_turn[2][2], mario_run[3][2], MARIO_* */

/* Примитивы вывода из render.asm (по идиомам mario-16cols/mario.asm).
 * Параметры передаются через глобалы rs_* ниже — без стековых аргументов. */
extern void mario_draw_sprite(void);
extern void mario_erase_sprite(void);
extern void mario_fill_ground(void);      /* тайл земли во 4 плоскости   */
extern void mario_copy_AB(void);          /* копия A -> B, 2x8 КБ          */
extern void mario_capture_shadow(void);   /* слепок полосы в тени        */

/* ------------------------------- ГЕОМЕТРИЯ ------------------------------ */
#define SCR_W        256
#define BAND_TOP     104      /* верх полосы-тени (самый верх прыжка Марио)   */
#define BAND_BOT     223      /* низ полосы (стопы стоящего Марио)            */
#define BAND_ROWS    (BAND_BOT - BAND_TOP + 1)
#define BAND_STRIDE  128      /* шаг колонки тени (степень 2: сдвиг колонки
                               * в asm = инкремент старшего байта)            */
#define GROUND_TOP   224      /* тайлы земли: y = 224..255 (4 ряда)           */
#define GROUND_ROWS  (256 - GROUND_TOP)
#define GROUND_MY    (GROUND_TOP - MARIO_HPIX)  /* top стоящего Марио = 192    */

#define MIN_MX       0
#define MAX_MX       (SCR_W - MARIO_HCELLS * 8)  /* правый край (x верха клетки)*/

/* ---------------------------- ПЛОСКОСТИ-БУФЕРЫ -------------------------- */
/* p0 = плоскость веса 1 (лог. бит0), p1 = плоскость веса 2 (лог. бит1). */
#define BASE_A0  0xE000
#define BASE_A1  0xC000
#define BASE_B0  0xA000
#define BASE_B1  0x8000

/* Адрес байта плоскости для пикселя (x кратно 8 — клетка), строка y. */
#define CELL_ADDR(base, col, y) \
    ((unsigned char *)(base) + (unsigned int)(col) * 0x100u + (255u - (y)))

/* --------------------------------- ВВОД --------------------------------- */
#define KEY_LEFT   8
#define KEY_RIGHT  9
#define KEY_DOWN   10
#define KEY_SPACE  32

/* Состояние СС (Shift) после kbd_scan() — задаётся в kbdscan.asm. */
extern unsigned char kbd_shift_state;

/* ------------------------------ СОСТОЯНИЕ ------------------------------- */
static unsigned char palA[16], palB[16];
static unsigned char front;              /* 0 = виден A, 1 = виден B          */

/* RAM-тень фона полосы: ДВЕ колоночные матрицы (для asm-копирования):
 * байт = col * BAND_STRIDE + (y - BAND_TOP). Заполняются на старте. */
unsigned char shadow0[32 * BAND_STRIDE];  /* плоскость веса 1 (E000/A000) */
unsigned char shadow1[32 * BAND_STRIDE];  /* плоскость веса 2 (C000/8000) */

/* Параметры для render.asm (ассемблер читает/пишет их напрямую).
 * НЕ static — символы должны быть видны линкеру. */
unsigned int  rs_spr;                    /* указатель на спрайт (заголовок)  */
unsigned int  rs_data;                   /* колонка данных (считает asm)     */
unsigned int  rs_p0, rs_p1;              /* VRAM-указатели верха колонки     */
unsigned int  rs_s0, rs_s1;              /* старт тени колонки               */
unsigned char rs_cols;                   /* знаковый счётчик колонок (-w..0) */

/* Прямоугольник последнего спрайта в каждом буфере (для стирания). */
static unsigned char old_x[2], old_y[2], old_w;   /* old_w в клетках, h=MARIO_HPIX */
static unsigned char old_valid[2];

/* Физика/анимация Марио. */
static unsigned char mx;                 /* x верха клетки (кратно 8)         */
static int           my;                 /* y верха спрайта (может < GROUND)  */
static int           vy;                 /* вертикальная скорость, + = вниз   */
static unsigned char facing;             /* 0 = влево, 1 = вправо             */
static unsigned char grounded;
static unsigned char crouch;
static unsigned char moving;            /* удерживается стрелка               */
static unsigned char running;           /* + СС                               */
static unsigned char turning;           /* 1 = идёт разворот                  */
static unsigned char turn_step;         /* 0=спрайт 18, 1=спрайт 19           */
static unsigned char turn_target;       /* целевое facing после поворота      */
static unsigned char anim_step;         /* 0..3 — фаза цикла ходьбы/бега     */
static const unsigned char walk_seq[4] = {0, 1, 2, 1}; /* 01->02->03->02 */
static const unsigned char run_seq[4]  = {0, 1, 2, 1}; /* 11->12->13->12 */
static unsigned char anim_timer;
static unsigned char move_timer;
static unsigned char space_prev;
static unsigned int  tick;

/* ------------------------------- УТИЛИТЫ -------------------------------- */

/* Собрать 16-слотовые палитры-маски из 4 цветов экрана. */
static void build_palettes(void)
{
    unsigned char i;
    for (i = 0; i < 16u; i++) {
        palA[i] = screen_pal4[i & 3u];
        palB[i] = screen_pal4[(i >> 2) & 3u];
    }
}

/* Зарисовать тайл земли в обе пары плоскостей (фон одинаков в A и B).
 * Данные (16 байт тайла) передаются asm'у через rs_spr. */
static void draw_ground(void)
{
    rs_spr = (unsigned int)tile_ground;
    mario_fill_ground();
}

/* Текст: gfx_print берёт x = символьная колонка (0..31), y = пиксельная
 * строка. Цвет = логический 0..3 (младшие биты -> буфер A). */
static void draw_text_line(unsigned char col, unsigned char y, const char *s)
{
    gfx_print(col, y, s, 2);   /* лог. цвет 2 = розовый */
}

/* Копия плоскостей буфера A -> B (фон становится идентичным):
 * плоскости — непрерывные 8 КБ, копируются ручным циклом в asm. */
static void copy_A_to_B(void)
{
    mario_copy_AB();
}

/* Снять RAM-тень фона полосы с плоскостей буфера A (колоночные
 * матрицы) — asm-циклом. */
static void capture_shadow(void)
{
    mario_capture_shadow();
}

/* Вернуть фон по прямоугольнику спрайта в буфере buf: asm-копирование
 * из колоночной тени (32 строки x wcells колонок, всё в пределах полосы). */
static void erase_sprite(unsigned char buf, unsigned char x, unsigned char y,
                         unsigned char wcells)
{
    unsigned int col  = x >> 3;
    unsigned int base = (buf == 0) ? BASE_A0 : BASE_B0;
    rs_p0   = base + col * 0x100u + (255u - (unsigned int)y);
    rs_p1   = rs_p0 - 0x2000u;
    /* Тень колоночная: байт = col*BAND_STRIDE + (yy - BAND_TOP),
     * поэтому тень прямоугольника начинается с (y - BAND_TOP). */
    rs_s0   = (unsigned int)shadow0 + col * BAND_STRIDE + (y - BAND_TOP);
    rs_s1   = (unsigned int)shadow1 + col * BAND_STRIDE + (y - BAND_TOP);
    rs_cols = (unsigned char)(-(int)wcells);
    mario_erase_sprite();
}

/* Нарисовать спрайт-позу в буфер buf: asm-композиция колонок с
 * прозрачностью. Марио всегда целиком в полосе BAND_TOP..BAND_BOT
 * (my клампится), выровнен по сетке 8 px — клип не нужен. */
static void draw_sprite(unsigned char buf, unsigned char x, unsigned int y,
                        const unsigned char *spr)
{
    unsigned int col = x >> 3;
    unsigned int base = (buf == 0) ? BASE_A0 : BASE_B0;
    rs_p0  = base + col * 0x100u + (255u - y);
    rs_p1  = rs_p0 - 0x2000u;
    rs_spr = (unsigned int)spr;
    mario_draw_sprite();
}

/* ------------------------------ ЛОГИКА КАДРА ---------------------------- */

/* Выбрать позу [0..7] по состоянию. */
static const unsigned char *pick_sprite(void)
{
    unsigned char f;
    if (turning) {
        /* Разворот: шаг 0 = поза 18 (на камеру), шаг 1 = поза 19 (завершение). */
        if (turn_step == 0)
            return mario_turn[0][0];       /* фронтальная — не зеркалим */
        else
            return mario_turn[1][turn_target];
    }
    if (crouch)                 f = 6;              /* присел            */
    else if (!grounded)         f = 7;              /* прыжок            */
    else if (running && moving) return mario_run[run_seq[anim_step]][facing ? 1 : 0];
    else if (moving)            f = walk_seq[anim_step]; /* ходьба 01->02->03->02 */
    else                        f = ((anim_step & 1) ? 3 : 0); /* стойка 00/03 (мавок) */
    return mario_frames[f][facing ? 1 : 0];
}

static void update_state(void)
{
    unsigned char left, right, down;

    left  = kbd_is_down(KEY_LEFT);
    right = kbd_is_down(KEY_RIGHT);
    down  = kbd_is_down(KEY_DOWN);
    running = kbd_shift_state;
    crouch  = down && grounded;

    moving = (unsigned char)((left || right) && !crouch);

    /* Разворот: при смене направления стоя на месте — анимация через 18/19. */
    if (turning) {
        /* Уже крутимся — продвигаем шаги по тому же таймеру. */
        unsigned char rate = running ? 1 : 3;
        if (++move_timer >= rate) {
            move_timer = 0;
            turn_step++;
            if (turn_step > 1) {
                turning = 0;
                facing = turn_target;
            }
        }
        moving = 0;                     /* во время поворота не идём */
    } else {
        unsigned char want = 0;
        if (left && !right && facing) want = 1;
        if (right && !left && !facing) want = 1;
        if (want && !moving) {
            /* Начинаем разворот. */
            turning = 1;
            turn_step = 0;
            turn_target = (left && !right) ? 0 : 1;
            move_timer = 0;
            moving = 0;
        } else {
            if (left && !right) facing = 0;
            if (right && !left) facing = 1;
        }
    }

    /* Шаг 8 px: ходьба медленнее бега. */
    if (moving) {
        unsigned char rate = running ? 1 : 3;
        if (++move_timer >= rate) {
            int nx = (int)mx + (facing ? 8 : -8);
            move_timer = 0;
            if (nx >= MIN_MX && nx <= MAX_MX) mx = (unsigned char)nx;
            anim_step = (anim_step + 1) & 3;
        }
    } else {
        move_timer = 0;
        /* Мавок хвостом на месте — медленный таймер. */
        if (++anim_timer >= 16) { anim_timer = 0; anim_step = (anim_step + 1) & 3; }
    }

    /* Прыжок по фронту пробела, только с опоры. */
    {
        unsigned char sp = kbd_is_down(KEY_SPACE);
        if (sp && !space_prev && grounded && !crouch) {
            vy = -12;                /* импульс вверх (высокий прыжок) */
            grounded = 0;
        }
        space_prev = sp;
    }

    /* Вертикальная физика. */
    if (!grounded) {
        my += vy;
        vy += 1;                      /* гравитация */
        if (my >= GROUND_MY) { my = GROUND_MY; vy = 0; grounded = 1; }
        if (my < (int)(BAND_TOP)) { my = BAND_TOP; if (vy < 0) vy = 0; }
    }
}

static void draw_frame(void)
{
    unsigned char back = (unsigned char)(front ^ 1u);
    const unsigned char *spr = pick_sprite();
    unsigned char wcells = spr[0];

    /* 1. Стереть прежнего Марио в скрытом буфере (возврат фона из тени). */
    if (old_valid[back])
        erase_sprite(back, old_x[back], old_y[back], old_w);

    /* 2. Нарисовать нового. */
    draw_sprite(back, mx, (unsigned int)my, spr);

    /* 3. Запомнить прямоугольник для следующего обращения к этому буферу. */
    old_x[back] = mx;
    old_y[back] = (unsigned char)my;
    old_w = wcells;
    old_valid[back] = 1;

    /* 4. Показать этот буфер (смена палитры = VSync-синхронно). */
    gfx_set_bmp_palette(back == 0 ? palA : palB);
    front = back;
}

/* --------------------------------- MAIN --------------------------------- */
static void init_background(void)
{
    unsigned char y = 0;
    /* Сразу скрыть экран чёрной палитрой: фон строится вживую
     * (print/земля/копия A->B), при дефолтной 16-цветной палитре эта
     * сборка была видна как «чтение» (горизонтальный и вертикальный скан). */
    gfx_set_black_palette();
    gfx_set_mode(GFX_MODE_256_16);
    gfx_fill_planes(0x0F, 0x00);          /* небо = лог. 0 во всех плоскостях */

    draw_ground();

    /* Текст — в полосе движения Марио, чтобы спрайт его перекрывал.
     * x = колонка (0..31): старт с кол.1, строки <= 30 символов
     * (32-я колонка переполняется и хвост заворачивается влево). */
    y = BAND_TOP;
    draw_text_line(1,  y,       "VECTOR-06C DOUBLE BUFFER");
    draw_text_line(1,  y += 12, "THIS ROM SHOWS DOUBLE");
    draw_text_line(1,  y += 12, "BUFFERING FOR VECTOR-06C");
    draw_text_line(1,  y += 12, "2 PLANE PAIRS SWAP PALETTE");
    draw_text_line(1,  y += 12, "------------------------------");
    draw_text_line(1,  y += 12, "ARROWS - WALK    SHIFT - RUN");
    draw_text_line(1,  y += 12, "SPACE  - JUMP    DOWN  - DUCK");
    draw_text_line(1,  y += 12, "MARIO OVERLAPS THIS TEXT");

    copy_A_to_B();                          /* фон одинаков в A и B */

    /* Индикаторы буферов: цифра «1» — ТОЛЬКО в плоскостях A (E000/C000),
     * верхний левый угол; цифра «2» — ТОЛЬКО в плоскостях B (A000/8000),
     * верхний правый. Палитра-маска прячет неактивный буфер, поэтому на
     * экране всегда видна ровно одна цифра — переключение наглядно.
     * Рисуем ПОСЛЕ copy_A_to_B, иначе «1» перекочевала бы в B.
     * Цвет = бит той же весовой плоскости: A — лог. 2 (w2), B — 8 (w8),
     * под palB (i>>2)&3 = 2 — тот же розовый. */
    gfx_active_planes = 0x03;               /* только буфер A */
    gfx_print(0, 0, "1", 2);
    gfx_active_planes = 0x0C;               /* только буфер B */
    gfx_print(31, 0, "2", 8);
    gfx_active_planes = 0x0F;

    capture_shadow();                       /* тень полосы с буфера A */
}

void main(void)
{
    build_palettes();
    init_background();

    mx = 40;
    my = GROUND_MY;
    vy = 0;
    facing = 0;
    grounded = 1;
    old_valid[0] = old_valid[1] = 0;

    gfx_set_bmp_palette(palA);              /* стартово виден A */
    front = 0;

    for (;;) {
        kbd_scan();                          /* обновить kbd_rows + shift */
        update_state();
        draw_frame();
        tick++;
    }
}
