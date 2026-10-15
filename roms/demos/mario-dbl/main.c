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
 * Движение — каждый кадр: бег 4 px, ходьба — те же 4 px раз в 2 кадра (вдвое
 * медленнее). Когда x кратен 8 —
 * спрайт выровнен по сетке, вывод идёт целыми байтами плоскостей (быстрый
 * путь). Когда x кратно 4, но не 8 (шаг ходьбы), Марио сдвинут внутри клетки
 * на 4 px = одну тетраду: вывод собирает каждый выходной байт из двух соседних
 * клеток спрайта (сдвиг тетрады при выводе), поэтому спрайт занимает на одну
 * клетку шире (spill вправо).
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

/* Звук (src/sfx_mario.c): прыжок/приземление — тон (sfx.c), ветер при беге —
 * шум канала C AY (drums.asm). На КР580ВИ53 ветер отсутствует (нет шума). */
extern void mario_sfx_init(void);
extern void mario_sfx_jump(void);
extern void mario_sfx_land(void);
extern void mario_sfx_update(unsigned char running);

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

#define FADE_HOLD    2       /* кадров на шаг фейда появления (больше — медленнее) */

#define MIN_MX       0
#define MAX_MX       (SCR_W - 3 * 8)  /* правый край (x верха клетки)*/

/* ------------------------------ СТАРТ ПОЗИЦИИ --------------------------- */
#define START_MX       26*8       /* x левого верха Марио на старте (кратен 8)  */
#define START_MY       GROUND_MY /* y стоящего Марио на старте                  */
#define START_FACING   0         /* 0 = лицом влево, 1 = вправо                 */

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
/* Битки звуковых событий за кадр (из update_state, исполняются после показа
 * кадра — см. main-цикл; иначе звук опережает картинку на целый кадр). */
#define EV_JUMP      1
#define EV_LAND      2

static unsigned char palA[16], palB[16];
static unsigned char front;              /* 0 = виден A, 1 = виден B          */

/* RAM-тень фона полосы: ДВЕ колоночные матрицы (для asm-копирования):
 * байт = col * BAND_STRIDE + (y - BAND_TOP). Буферы берутся из кучи
 * (mem/heap.c): куча стартует от конца образа __tail и в ROM-файл не
 * попадает — 8 KB теней не раздувают образ. Освобождения нет: буфер
 * живёт от capture_shadow() до перезапуска.
 * НЕ static — символы читают render.asm (lhld _shadow0/_shadow1). */
#define SHADOW_BYTES  (32 * BAND_STRIDE)   /* 4 KB на плоскость        */
unsigned char *shadow0;                    /* плоскость веса 1 (E000/A000) */
unsigned char *shadow1;                    /* плоскость веса 2 (C000/8000) */

/* Параметры для render.asm (ассемблер читает/пишет их напрямую).
 * НЕ static — символы должны быть видны линкеру. */
unsigned int  rs_spr;                    /* указатель на спрайт (заголовок)  */
unsigned int  rs_data;                   /* колонка данных (считает asm)     */
unsigned int  rs_p0, rs_p1;              /* VRAM-указатели верха колонки     */
unsigned int  rs_s0, rs_s1;              /* старт тени колонки               */
unsigned char rs_cols;                   /* знаковый счётчик колонок (-w..0) */
unsigned char rs_frac;                   /* суб-клеточный сдвиг: 0 или 4 px */

/* Прямоугольник последнего спрайта в каждом буфере (для стирания).
 * ВСЕ поля — по буферам: спрайг в скрытом буфере был нарисован 2 кадра
 * назад и мог иметь ДРУГУЮ ширину (frac=4 шире на spill-клетку), чем
 * последний спрайт в другом буфере. Общий old_w стирал бы не ту ширину и
 * оставлял нестёртый кусок. */
static unsigned char old_x[2], old_y[2], old_w[2];   /* old_w в клетках, h=MARIO_HPIX */
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
static unsigned char walk_phase;        /* фаза ходьбы: шаг 4 px раз в 2 кадра */
static unsigned char space_prev;
static unsigned char land_played;       /* 1 = чпок приземления уже сыгран (early) */
static unsigned int  tick;

/* HUD частоты кадров: показанных (draw_frame) кадров за окно VBlank -> FPS.
 * Считаем за ~50 VBlank (≈1 с при 50 Гц): если тяжёлые кадры пропускают
 * VSync, кадров в окне меньше 50 — число «плавает» вниз. */
static char         fps_str[7]  = "FPS=50";   /* фикс. ширина — перекрывает без остатка */
static unsigned int fps_vbl;                    /* VBlank накоплено в окне          */
static unsigned int fps_frames;                 /* показанных кадров в окне          */

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
 * матрицы) — asm-циклом. Буферы теней выделяем из кучи прямо перед
 * слепком: дальше они только читаются erase_sprite(). */
static void capture_shadow(void)
{
    /* 8 KB из кучи до 0x8000 — заведомо хватает, поэтому проверки OOM нет
     * (пустой for(;;){} + &&/|| ломает кодогенерацию sccz80). */
    shadow0 = (unsigned char *)heap_alloc(SHADOW_BYTES);
    shadow1 = (unsigned char *)heap_alloc(SHADOW_BYTES);
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
 * (my клампится). Шаг движения 4 px => x кратен 4; младший бит клетки
 * (x & 7 == 4) asm трактует как сдвиг тетрады вправо на 4 px. */
static void draw_sprite(unsigned char buf, unsigned char x, unsigned int y,
                        const unsigned char *spr)
{
    unsigned int col = x >> 3;
    unsigned int base = (buf == 0) ? BASE_A0 : BASE_B0;
    rs_p0  = base + col * 0x100u + (255u - y);
    rs_p1  = rs_p0 - 0x2000u;
    rs_spr = (unsigned int)spr;
    rs_frac = (unsigned char)(x & 7u);
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

static unsigned char update_state(void)
{
    unsigned char left, right, down;
    unsigned char ev = 0;

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

    /* Двигаемся. Бег: 4 px каждый кадр. Ходьба: те же 4 px, но раз в 2 кадра
     * (вдвое медленнее бега). mx всегда кратен 4 → frac ∈ {0,4}; шаг 2 px дал
     * бы frac=2 и сломал бы сдвиговый рендер (он фиксирован на тетраду). */
    if (moving) {
        unsigned char advance = 1;
        if (!running) { walk_phase ^= 1; advance = walk_phase; }
        if (advance) {
            int nx = (int)mx + (facing ? 4 : -4);
            if (nx >= MIN_MX && nx <= MAX_MX) mx = (unsigned char)nx;
            anim_step = (anim_step + 1) & 3;   /* ноги шагают вместе с шагом */
        }
    } else {
        move_timer = 0;
        walk_phase = 0;                     /* сброс: со старта шагнём сразу */
        /* Мавок хвостом на месте — медленный таймер. */
        if (++anim_timer >= 16) { anim_timer = 0; anim_step = (anim_step + 1) & 3; }
    }

    /* Прыжок по фронту пробела, только с опоры. */
    {
        unsigned char sp = kbd_is_down(KEY_SPACE);
        if (sp && !space_prev && grounded && !crouch) {
            vy = -12;                /* импульс вверх (высокий прыжок) */
            grounded = 0;
            land_played = 0;         /* новый полёт — приземление ещё не сыграно */
            ev |= EV_JUMP;           /* свист прыжка — после показа кадра */
        }
        space_prev = sp;
    }

    /* Вертикальная физика. */
    if (!grounded) {
        /* Приземление на КАДР раньше фактического касания: пока падаем и
         * через две интегрирования (my+vy, затем +(vy+1)) упрёмся в землю —
         * запускаем чпок сейчас. Звук ляжет чуть раньше удара стопы.
         * my+vy < GROUND_MY — в этом кадре ещё не коснулись;
         * my+2*vy+1 >= GROUND_MY — коснёмся в следующем. */
        if (!land_played && vy > 0 &&
            (my + vy) < (int)GROUND_MY && (my + 2 * vy + 1) >= (int)GROUND_MY) {
            ev |= EV_LAND;
            land_played = 1;
        }
        my += vy;
        vy += 1;                      /* гравитация */
        if (my >= GROUND_MY) {
            my = GROUND_MY; vy = 0; grounded = 1;
            if (!land_played) ev |= EV_LAND;   /* подстраховка, если окно пропущено */
            land_played = 0;
        }
        if (my < (int)(BAND_TOP)) { my = BAND_TOP; if (vy < 0) vy = 0; }
    }

    return ev;
}

/* Пересчитать окно измерений в строку "FPS=NN" (6 симв., NN в индексах 4,5). */
static void fps_refresh(void)
{
    unsigned char v = (unsigned char)((fps_frames * 50u) / fps_vbl);
    fps_str[4] = (char)('0' + v / 10u);
    fps_str[5] = (char)('0' + v % 10u);
}

/* present != 0 — показать наполненный буфер: переключить палитру-маску
 * (= свап видимого буфера, VSync-синхронно) и активные плоскости.
 * present == 0 — только нарисовать в скрытый буфер, экран НЕ трогать
 * (нужно для пред-фейдового кадра: иначе палитра мигнёт ярким кадром до fade). */
static void draw_frame(unsigned char present)
{
    unsigned char back = (unsigned char)(front ^ 1u);
    const unsigned char *spr = pick_sprite();
    unsigned char wcells = spr[0];

    /* 1. Стереть прежнего Марио в скрытом буфере (возврат фона из тени). */
    if (old_valid[back])
        erase_sprite(back, old_x[back], old_y[back], old_w[back]);

    /* 2. Нарисовать нового. */
    draw_sprite(back, mx, (unsigned int)my, spr);

    /* 3. Запомнить прямоугольник для следующего обращения к этому буферу.
     * При сдвиге тетрады (mx & 7 == 4) спрайг занимает на одну клетку
     * шире (spill вправо) — стирать надо покрывать ровно отрисованное. */
    old_x[back] = mx;
    old_y[back] = (unsigned char)my;
    old_w[back] = (unsigned char)(wcells + ((mx & 7u) ? 1u : 0u));
    old_valid[back] = 1;

    /* HUD: частота кадров по центру вверху — в тот же скрытый (back) буфер.
     * Пишем только в плоскости back-буфера (маска 0x03 для A / 0x0C для B),
     * поэтому обновление не даёт tearing; строка фикс. ширины перекрывает
     * прежние цифры без остатка. Row 0 (пикс. 0..7) выше полосы BAND_TOP=104 —
     * erase_sprite её не задевает. */
    gfx_active_planes = (back == 0) ? 0x03 : 0x0C;
    gfx_print(13, 0, fps_str, (back == 0) ? 2 : 8);
    gfx_active_planes = 0x0F;

    /* Этот буфер теперь держит текущий кадр — независимо от показа. */
    front = back;

    /* 4. Показать этот буфер (смена палитры = VSync-синхронно). */
    if (present) {
        gfx_active_planes = 0x0F;
        gfx_set_bmp_palette(back == 0 ? palA : palB);
    }
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
    y = 48;
    draw_text_line(1,  y,       "VECTOR-06C DOUBLE BUFFER");
    draw_text_line(1,  y += 12, "");
    draw_text_line(1,  y += 12, "THIS ROM SHOWS DOUBLE");
    draw_text_line(1,  y += 12, "BUFFERING FOR VECTOR-06C");
    draw_text_line(1,  y += 12, "2 PLANE PAIRS SWAP PALETTE");
    draw_text_line(1,  y += 12, "");
    draw_text_line(1,  y += 12, "GOAL: ACHIEVE MAXIMUM");
    draw_text_line(1,  y += 12, "SMOOTHNESS IN MARIOS MOVEMENT");
    draw_text_line(1,  y += 12, "");
    draw_text_line(1,  y += 12, "ARROWS - WALK    SHIFT - RUN");
    draw_text_line(1,  y += 12, "SPACE  - JUMP    DOWN  - DUCK");
    draw_text_line(1,  y += 12, "");
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
    gfx_print(0, 0, "BUFFER 1", 2);
    gfx_active_planes = 0x0C;               /* только буфер B */
    gfx_print(24, 0, "BUFFER 2", 8);
    gfx_active_planes = 0x0F;

    capture_shadow();                       /* тень полосы с буфера A */
}

void main(void)
{
    unsigned char ev;
    unsigned char n, i;
    unsigned char fc, last_fc, raw;
    volatile unsigned char *fc_lo;

    build_palettes();
    mario_sfx_init();
    init_background();

    mx = START_MX;
    my = START_MY;
    vy = 0;
    facing = START_FACING;
    grounded = 1;
    old_valid[0] = old_valid[1] = 0;

    /* Первый кадр рисуем в A (front=1 → back=0=A), НО не показываем
     * (present=0): экран остаётся чёрным, fade_in ниже сам проявит A с
     * Марио — без лишней вспышки палитры. */
    front = 1;
    draw_frame(0);

    gfx_fade_in(palA, FADE_HOLD);   /* проявить A уже с Марио */
    front = 0;

    /* fixed timestep. Младший байт frame_count (его инкрементирует VBlank-ISR
     * на startup.asm) читаем одним LDA — atomic на 8080. Дельта по нему =
     * сколько настоящих VBlank ушло на предыдущий виток цикла. */
    fc_lo   = (volatile unsigned char *)&frame_count;
    last_fc = *fc_lo;
    fps_vbl = 0; fps_frames = 0;

    for (;;) {
        /* Неблокирующий снимок матрицы: сами мы прямо сейчас в гасящем
         * интервале — только что вернулись из ei/halt прошлого draw_frame
         * (смена палитры синхронизирована с VSync). kbd_scan() сделал бы ЕЩЁ
         * один halt и удвоил бы цену кадра (2 VBlank/цикл → ~16 Гц); здесь мы
         * переиспользуем уже достигнутый VBlank → 1 VBlank/цикл. */
        kbd_scan_now();                       /* обновить kbd_rows + shift, без halt */

        /* Догон симуляции/звука по числу реально прошедших VBlank. Тяжёлый
         * кадр (сдвиг тетрады) может не влезть в 20 мс и пропустить VSync —
         * тогда цикл отстал, frame_count вырос на 2+, и update_state/sfx
         * крутятся столько же раз, чтобы скорость игры и темп звука остались
         * честными 50 Гц (взамен — лёгкий джаггер отрисовки на пропусках). */
        fc = *fc_lo;
        raw = (unsigned char)(fc - last_fc); /* mod 256: РЕАЛЬНО ушло VBlank за виток */
        last_fc = fc;
        /* Догон симуляции клампим (иначе spiral: лишний догон добавляет CPU и
         * усиливает пропуск), но для HUD копит СЫРОЙ raw — иначе кламп прячет
         * правдивое число (пол 50/3≈16). */
        n = raw;
        if (n == 0) n = 1;                   /* не стоять: минимум шаг за виток */
        if (n > 3)  n = 3;                    /* после долгого простоя — догон с потолка */

        ev = 0;
        for (i = 0; i < n; i++) {
            ev |= update_state();            /* физика + битки звуковых событий */
            mario_sfx_update(running);       /* голоса + ветер (непрерывный)     */
        }

        draw_frame(1);                       /* рендер + свап палитры на VSync */
        /* Звук событий — СРАЗУ после показа кадра: draw_frame блокируется в
         * ei/halt до VSync, и только теперь новый кадр виден. Если запускать
         * звук в update_state (до draw_frame), он опережал картинку на кадр. */
        if (ev & EV_JUMP) mario_sfx_jump();
        if (ev & EV_LAND) mario_sfx_land();
        tick++;

        /* Частота показанных кадров: виток = один shown-кадр; в знаменатель
         * кладём СЫРОЙ raw (не клампованный n), чтобы HUD не врал при просадке
         * ниже пола. Окно ~50 VBlank. */
        fps_frames++;
        fps_vbl   += raw;
        if (fps_vbl >= 50) { fps_refresh(); fps_vbl = 0; fps_frames = 0; }
    }
}
