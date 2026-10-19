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
 * Марио (возврат фона из относительного RAM-патча по прежнему пятну) и рисуем
 * нового. Перед отрисовкой нового пятна его фон снимается в патч (capture_patch).
 * Спрайт перекрывает текст, а когда уходит — текст возвращается из патча.
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
 * Вывод спрайта — на 8080-ассемблере (include/render.asm): спрайт закодирован
 * КОЛОНОЧНО, столбец VRAM проходится линейно (данные +3, адрес -1),
 * стирание — копирование из относительного RAM-патча (шаг колонки = ROWS).
 */

#include "v06.h"

#include "tiles.inc"      /* screen_pal4, tile_ground */
#include "sprites.inc"    /* mario_frames[N][2], mario_turn[2][2], mario_run[3][2], MARIO_* */

/* Примитивы вывода из render.asm (по идиомам mario-16cols/mario.asm).
 * Параметры передаются через глобалы rs_* ниже — без стековых аргументов. */
extern void mario_draw_sprite(void);
extern void mario_erase_sprite(void);
extern void mario_fill_ground(void);      /* тайл земли во 4 плоскости   */
extern void mario_copy_AB(void);          /* копия A -> B, 2x8 КБ          */
extern void mario_capture_patch(void);    /* слепок пятна в RAM-патч      */

/* Звук (include/sfx_mario.c): прыжок/приземление — тон на КР580ВИ53 (vi53.c,
 * frame-exact таблица делителей). Шумогенератора у ВИ53 нет, поэтому ветра при беге нет.
 * Покадровый движок живёт в прерывании (frame_handler = mario_frame), НО ПОСЛЕ
 * смены палитры — так звук не сдвигает raster-критичный цикл записи 0C.
 * Из цикла лишь выставляем флаг бега (mario_sfx_running) и просим эффекты. */
extern void mario_sfx_init(void);
extern void mario_sfx_jump(void);
extern void mario_sfx_land(void);
extern void mario_sfx_frame(void);
extern unsigned char mario_sfx_running;   /* зеркало флага бега для ISR-движка */

/* Загрузка палитры ИЗ ISR: тот же v06_pal_write, но БЕЗ ei/halt (мы уже в
 * прерывании, в гасящем интервале; ei внутри ISR открыл бы реентерабельный вход). */
extern void v06_set_palette_isr(const unsigned char *pal);

/* ------------------------------- ГЕОМЕТРИЯ ------------------------------ */
#define SCR_W        256
#define BAND_TOP     104      /* верх зоны движения (самый верх прыжка Марио)  */
#define BAND_BOT     223      /* низ зоны (стопы стоящего Марио)               */
#define GROUND_TOP   224      /* тайлы земли: y = 224..255 (4 ряда)           */
#define GROUND_ROWS  (256 - GROUND_TOP)
#define GROUND_MY    (GROUND_TOP - MARIO_HPIX)  /* top стоящего Марио = 192    */

#define FADE_HOLD    2       /* кадров на шаг фейда появления (больше — медленнее) */

#define MIN_MX       0
#define MAX_MX       (SCR_W - 3 * 8)  /* правый край (x верха клетки)*/

/* Тиков (по 1/VSync) на один 4px-шаг. Шаг обязан быть 4px (mx кратно 4 →
 * frac ∈ {0,4}); 2px сломал бы тетрадный сдвиговый рендер, поэтому скорость
 * задаём частотой шага, а не размером. Ходьба вдвое медленнее бега. */
#define RUN_STEP     2                 /* бег:   4px раз в 2 тика  (~100 px/с) */
#define WALK_STEP    4                 /* ходьба: 4px раз в 4 тика (~50 px/с)  */

/* Прыжок: вертикальную физику (my+=vy, vy+=1) интегрируем раз в JUMP_STEP
 * тиков — вдвое медленнее дуга, как замедляли шаг бега/ходьбы. Импульс
 * vy=-12 и гравитация +1 задают ВЫСОТУ (сумма приращений по шагам), а
 * JUMP_STEP меняет лишь ДЛИТЕЛЬНОСТЬ, поэтому высота прыжка не меняется —
 * тормозится только его темп. */
#define JUMP_STEP    2                 /* прыжок: шаг физики раз в 2 тика      */

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
/* Flip буфера выполняет ISR (mario_frame): main выставляет жедаемую палитру в
 * show_pal и поднимает pal_dirty; ISR грузит её ПЕРВОЙ (до звука) и сбрасывает
 * флаг. Флаг нужен, чтобы на лишних VBlank тяжёлого/пропущенного кадра палитру
 * не перезаписывать впустую (между показами она не меняется). */
static const unsigned char *show_pal;    /* палитра, которую ISR грузит на VBlank */
static volatile unsigned char pal_dirty; /* 1 = show_pal_changed → перезаписать   */

/* Относительный RAM-патч фона ПОД СПРАЙТОМ (вместо полноширинной тени): по
 * одному патчу на плоскость и на буфер A/B. Байт = relcol * PATCH_ROWS + row
 * (шаг колонки = ROWS=32 в asm). Хранит ровно то, что было под пятном перед
 * отрисовкой — erase возвращает фон отсюда. Берётся из кучи (mem/heap.c),
 * в ROM не попадает: 5*32=160 Б/плоскость × 4 = 640 Б (было 8 КБ на полосу). */
#define PATCH_ROWS   32                     /* = MARIO_HPIX, строк пятна        */
#define PATCH_COLS   5                      /* max wcells(3)+spill(1) + запас    */
#define PATCH_BYTES  (PATCH_COLS * PATCH_ROWS)
static unsigned char *patch0[2];           /* плоскость веса 1 (E000/A000), по буферам */
static unsigned char *patch1[2];           /* плоскость веса 2 (C000/8000), по буферам */

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
/* Поза (указатель спрайта), реально нарисованная в паре A/B. Вместе с
 * old_x/old_y задаёт «состояние сцены спрайта» в этом буфере: пока все три
 * совпадают с текущими — кадр в этой паре идентичен уже нарисованному, и
 * erase+draw можно пропустить. При ходьбе спрайт меняется раз в WALK_STEP
 * тиков, а рисуемся каждый тик → лишние перерисовки и есть просадка в ране. */
static const unsigned char *last_spr[2];

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
static unsigned char step_timer;      /* счётчик тиков между 4px-шагами   */
static unsigned char jump_timer;      /* счётчик тиков между шагами физики */
static unsigned char space_prev;
static unsigned char land_played;       /* 1 = чпок приземления уже сыгран (early) */
static unsigned int  tick;

/* HUD частоты кадров: показанных (draw_frame) кадров за окно VBlank -> FPS.
 * Считаем за ~50 VBlank (≈1 с при 50 Гц): если тяжёлые кадры пропускают
 * VSync, кадров в окне меньше 50 — число «плавает» вниз. */
static unsigned char fps_val = 50;            /* текущее показываемое число FPS (0..99) */
static unsigned char hud_val[2] = { 0xFF, 0xFF }; /* значение FPS, уже напечатанное в паре A / B */
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

/* Выделить относительные патчи под спрайт (по одному на плоскость и буфер).
 * 640 Б из кучи до 0x8000 — заведомо хватает, проверки OOM нет (пустой
 * for(;;){} + &&/|| ломает кодогенерацию sccz80). */
static void init_patches(void)
{
    patch0[0] = (unsigned char *)heap_alloc(PATCH_BYTES);
    patch1[0] = (unsigned char *)heap_alloc(PATCH_BYTES);
    patch0[1] = (unsigned char *)heap_alloc(PATCH_BYTES);
    patch1[1] = (unsigned char *)heap_alloc(PATCH_BYTES);
}

/* Снять фон под новым пятном в патч буфера buf (перед отрисовкой спрайта).
 * x = пиксельный левый верх, y = пиксельный верх, w = колонок пятна (с spill). */
static void capture_patch(unsigned char buf, unsigned char x, unsigned char y,
                          unsigned char w)
{
    unsigned int col  = x >> 3;
    unsigned int base = (buf == 0) ? BASE_A0 : BASE_B0;
    rs_p0   = base + col * 0x100u + (255u - (unsigned int)y);
    rs_p1   = rs_p0 - 0x2000u;
    rs_s0   = (unsigned int)patch0[buf];
    rs_s1   = (unsigned int)patch1[buf];
    rs_cols = (unsigned char)(-(int)w);
    mario_capture_patch();
}

/* Вернуть фон по пятну спрайта в буфере buf: asm-копирование ROWS строк x
 * wcells колонок из относительного патча (старт = начало патча). */
static void erase_sprite(unsigned char buf, unsigned char x, unsigned char y,
                         unsigned char wcells)
{
    unsigned int col  = x >> 3;
    unsigned int base = (buf == 0) ? BASE_A0 : BASE_B0;
    rs_p0   = base + col * 0x100u + (255u - (unsigned int)y);
    rs_p1   = rs_p0 - 0x2000u;
    /* Патч относительный: начинается с верха-лево пятна, шаг колонки = ROWS. */
    rs_s0   = (unsigned int)patch0[buf];
    rs_s1   = (unsigned int)patch1[buf];
    rs_cols = (unsigned char)(-(int)wcells);
    mario_erase_sprite();
}

/* Нарисовать спрайт-позу в буфер buf: asm-композиция колонок с
 * прозрачностью. Шаг движения 4 px => x кратен 4; младший бит клетки
 * (x & 7 == 4) asm трактует как сдвиг тетрады вправо на 4 px (drs-путь). */
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

    /* Двигаемся. Шаг всегда 4 px (см. RUN_STEP/WALK_STEP выше), скорость —
     * частотой шага: раз в RUN_STEP тиков бегом, раз в WALK_STEP — ходьбой. */
    if (moving) {
        if (++step_timer >= (running ? RUN_STEP : WALK_STEP)) {
            int nx;
            step_timer = 0;
            nx = (int)mx + (facing ? 4 : -4);
            if (nx >= MIN_MX && nx <= MAX_MX) mx = (unsigned char)nx;
            anim_step = (anim_step + 1) & 3;   /* ноги шагают вместе с шагом */
        }
    } else {
        move_timer = 0;
        step_timer = 0;                       /* сброс: со старта отсчёт заново */
        /* Мавок хвостом на месте — медленный таймер. */
        if (++anim_timer >= 16) { anim_timer = 0; anim_step = (anim_step + 1) & 3; }
    }

    /* Прыжок по фронту пробела, только с опоры. */
    {
        unsigned char sp = kbd_is_down(KEY_SPACE);
        if (sp && !space_prev && grounded && !crouch) {
            vy = -12;                /* импульс вверх (высокий прыжок) */
            grounded = 0;
            jump_timer = 0;          /* новый полёт — отсчёт дуги заново */
            land_played = 0;         /* новый полёт — приземление ещё не сыграно */
            ev |= EV_JUMP;           /* свист прыжка — после показа кадра */
        }
        space_prev = sp;
    }

    /* Вертикальная физика. Интегрируем раз в JUMP_STEP тиков (см. выше):
     * тормозит дугу прыжка, не меняя её высоты. */
    if (!grounded && ++jump_timer >= JUMP_STEP) {
        jump_timer = 0;
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

/* Пересчитать окно измерений в текущее число FPS (0..99). */
static void fps_refresh(void)
{
    unsigned char v = (unsigned char)((fps_frames * 50u) / fps_vbl);
    if (v > 99u) v = 99u;                /* два разряда «NN», больше не влезает */
    fps_val = v;
}

/* Нарисовать ТОЛЬКО две цифры FPS (колонки 17,18; строка 0) в плоскости
 * back-буфера: A — маска 0x03 / цвет 2, B — маска 0x0C / цвет 8. Приставка
 * «FPS=» статична и печатается один раз при инициализации. */
static void hud_paint_digits(unsigned char back)
{
    unsigned char col = (back == 0) ? 2 : 8;
    gfx_active_planes = (back == 0) ? 0x03 : 0x0C;
    gfx_put_char(17, 0, (char)('0' + fps_val / 10u), col);
    gfx_put_char(18, 0, (char)('0' + fps_val % 10u), col);
    gfx_active_planes = 0x0F;
}

/* Обработчик кадрового прерывания (50 Гц). ПОРЯДОК важен:
 * 1) если запрошен flip — загрузить палитру ПЕРВОЙ: она пишется в порт 0C
 *    «под лучом», цикл из 16 записей обязан стартовать в начале гашения.
 *    pal_dirty выставляется на каждый показанный кадр и снимается здесь же
 *    (ack), поэтому на лишних VBlank тяжёлого кадра палитра не трогается.
 * 2) затем — покадровый звук. Он долгий, но пишет только ВИ53/AY-порты
 *    (не 02/0C), поэтому после палитры безопасен, даже если вылезет из гашения. */
static void mario_frame(void)
{
    if (pal_dirty) {
        v06_set_palette_isr(show_pal);
        pal_dirty = 0;                     /* ack: main спит до этого момента */
    }
    mario_sfx_frame();                     /* ровно 1 такт звука за VBlank    */
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
    unsigned char w_new;

    /* Пропуск перерисовки: если спрайт уже нарисован в этой паре плоскостей
     * с тем же состоянием (x/y/поза) — кадр идентичен, erase+draw не нужны.
     * Фон полосы (тень) и HUD-строка 0 вне спрайтовой области не меняются,
     * поэтому совпадение этих трёх полей полностью задаёт картинку буфера.
     * Каждой паре нужен ровно ОДИН показ состояния → при постоянном кадре
     * рисуем 2 кадра из 4, остальные пропускаем. Свап палитры ниже всё равно
     * происходит (он даёт ei/halt-синхронизацию с VSync и не трогает VRAM). */
    if (old_valid[back] && spr == last_spr[back]
        && mx == old_x[back] && (unsigned char)my == old_y[back]) {
        /* спрайтовая сцена в back-буфере уже верна — ничего не рисуем */
    } else {
        /* 1. Стереть прежнего Марио в скрытом буфере (возврат фона из патча). */
        if (old_valid[back])
            erase_sprite(back, old_x[back], old_y[back], old_w[back]);

        /* 2. Снять фон под НОВЫМ пятном в патч — после стирания (здесь VRAM
         * чистый фон) и до отрисовки. Ширина пятна = wcells + spill при frac=4. */
        w_new = (unsigned char)(wcells + ((mx & 7u) ? 1u : 0u));
        capture_patch(back, mx, (unsigned char)my, w_new);

        /* 3. Нарисовать нового. */
        draw_sprite(back, mx, (unsigned int)my, spr);

        /* 4. Запомнить пятно для следующего обращения к этому буферу. */
        old_x[back] = mx;
        old_y[back] = (unsigned char)my;
        old_w[back] = w_new;
        old_valid[back] = 1;
        last_spr[back] = spr;
    }

    /* HUD: цифры FPS в тот же скрытый (back) буфер — но только когда это
     * число ещё не напечатано именно в данной паре плоскостей (меняется
     * ~раз в секунду, а не каждый кадр). hud_val[2] хранит значение, уже
     * отрисованное в паре A / B; печатаем по расхождению — tearing нет
     * (пишем лишь в back-маску), а обе пары сходятся к новому числу за 2
     * кадра. Row 0 (пикс. 0..7) выше полосы BAND_TOP=104 — erase_sprite её
     * не задевает. */
    if (hud_val[back] != fps_val) {
        hud_paint_digits(back);
        hud_val[back] = fps_val;
    }

    /* Этот буфер теперь держит текущий кадр — независимо от показа. */
    front = back;

    /* 4. Показать этот буфер: НЕ грузим палитру напрямую (это делало ei/halt),
     *    а просим ISR сделать flip на ближайшем VBlank (палитра — первой в
     *    mario_frame). Само ожидание VBlank даёт v06_wait_frame в main-цикле. */
    if (present) {
        gfx_active_planes = 0x0F;
        show_pal = (back == 0) ? palA : palB;
        pal_dirty = 1;
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

    /* FPS-приставка «FPS=» статична — печатаем один раз в обе пары плоскостей
     * (как индикаторы буферов). Цифры поверх обновляет draw_frame по требованию.
     * Начальные цифры (fps_val=50) кладём сразу в обе пары, чтобы до первого
     * окна измерений не было расхождения A/B. */
    gfx_active_planes = 0x03; gfx_print(13, 0, "FPS=", 2);
    gfx_active_planes = 0x0C; gfx_print(13, 0, "FPS=", 8);
    gfx_active_planes = 0x0F;
    hud_paint_digits(0); hud_val[0] = fps_val;
    hud_paint_digits(1); hud_val[1] = fps_val;

    init_patches();                         /* относительные патчи под спрайт */
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

    /* Кадровое прерывание ведёт flip буфера (палитра ПЕРВОЙ) + звук. Назначаем
     * после фейда: пока идёт fade, палитрой владеет gfx_fade_in. A уже показан,
     * так что стартовый flip не нужен (pal_dirty=0). */
    show_pal = palA;
    pal_dirty = 0;
    frame_handler = mario_frame;

    /* fixed timestep. Младший байт frame_count (его инкрементирует VBlank-ISR
     * на startup.asm) читаем одним LDA — atomic на 8080. Дельта по нему =
     * сколько настоящих VBlank ушло на предыдущий виток цикла. */
    fc_lo   = (volatile unsigned char *)&frame_count;
    last_fc = *fc_lo;
    fps_vbl = 0; fps_frames = 0;

    for (;;) {
        /* Неблокирующий снимок матрицы: сами мы прямо сейчас в гасящем
         * интервале — только что вернулись из v06_wait_frame прошлого витка
         * (cadence синхронизирована с VSync). kbd_scan() сделал бы ЕЩЁ один
         * halt и удвоил бы цену кадра (2 VBlank/цикл → ~16 Гц); здесь мы
         * переиспользуем уже достигнутый VBlank → 1 VBlank/цикл. */
        kbd_scan_now();                       /* обновить kbd_rows + shift, без halt */

        /* Догон симуляции по числу реально прошедших VBlank. Тяжёлый кадр
         * (сдвиг тетрады) может не влезть в 20 мс и пропустить VSync — тогда
         * цикл отстал, frame_count вырос на 2+, и update_state крутится столько
         * же раз, чтобы скорость игры осталась честной 50 Гц (взамен — лёгкий
         * джаггер отрисовки на пропусках). Звук тем временем сам идёт по 1 разу
         * за VBlank из ISR — его темпу догон цикла не нужен. */
        fc = *fc_lo;
        raw = (unsigned char)(fc - last_fc); /* mod 256: РЕАЛЬНО ушло VBlank за виток */
        last_fc = fc;
        /* Догон симуляции клампим (иначе spiral: лишний догон добавляет CPU и
         * усиливает пропуск), но для HUD копит СЫРОЙ raw — иначе кламп прячет
         * правдивое число (пол 50/3≈16). */
        n = raw;
        if (n == 0) n = 1;                   /* не стоять: минимум шаг за виток */
        if (n > 3)  n = 3;                    /* после долгого простоя — догон с потолка */
        /* Anti-latch: стоя на земле нечего догонять — принудительно 1 тик. Иначе
         * цикл залипает в тяжёлом равновесии «3 тика/кадр» (звук ×3 раздувает
         * виток → raw=3 → снова 3 тика) и FPS в покое не поднимается с ~16. */
        if (!moving && grounded && vy == 0 && !crouch) n = 1;

        ev = 0;
        for (i = 0; i < n; i++)
            ev |= update_state();            /* физика + битки звуковых событий */
        mario_sfx_running = running;         /* зеркало флага бега для ISR-движка */

        draw_frame(1);                       /* рендер в скрытый буфер + заявка flip */
        /* Звук событий — только просим (байтовый флаг), исполнит ISR на
         * ближайшем VBlank (движок принадлежит ISR, прямого sfx_play из main нет). */
        if (ev & EV_JUMP) mario_sfx_jump();
        if (ev & EV_LAND) mario_sfx_land();

        /* Синхронизация с VSync: сон до ближайшего VBlank, на котором ISR
         * применит запрошенный flip (палитру — первой) и отзвучит звук. Теперь
         * это единственная блокировка цикла (свап палитры больше не halt-ит). */
        v06_wait_frame();
        tick++;

        /* Частота показанных кадров: виток = один shown-кадр; в знаменатель
         * кладём СЫРОЙ raw (не клампованный n), чтобы HUD не врал при просадке
         * ниже пола. Окно ~50 VBlank. */
        fps_frames++;
        fps_vbl   += raw;
        if (fps_vbl >= 50) { fps_refresh(); fps_vbl = 0; fps_frames = 0; }
    }
}
