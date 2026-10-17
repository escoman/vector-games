/*
 * main.c — демка «racing-the-beam» для Вектора-06Ц (mario-timer).
 *
 * Идея. Устранить мерцание анимации НЕ двойной буферизацией (как в mario-dbl),
 * а синхронизацией с электронным лучом по таймеру КР580ВИ53 канал 2 (порт 09h).
 * Буфер ОДИН — пара плоскостей 0xE000 (вес1) + 0xC000 (вес2), 4 логических цвета
 * (палитра: pal[i] = screen_pal4[i & 3]; старшие биты плоскостей 0xA000/0x8000
 * в картинке не участвуют). Никакого свапа палитрой и второй пары плоскостей нет.
 *
 * Откуда знаем «где луч». Кадровое прерывание VBlank (RST 7) совпадает с концом
 * сканирования лучом видимой части экрана. На каждом VBlank в ISR перезапускаем
 * счётчик канала 2 значением 0x7500 = 29952 = ровно один кадр при такте ВИ53
 * 1.5 МГц (96 тиков таймера на строку растра, 312 строк/кадр — снято с модели
 * beam_state). Счётчик линейно убывает вместе с лучом ⇒ (29952 − счётчик) =
 * «тика elapsed» от начала кадра, т.е. известна строка луча. (src/timer.asm.)
 *
 * Почему так не мерцает. Из-за бланкинга между концом видимого скана (VBlank) и
 * верхом экрана луч проходит 312−256 = 56 строк, а до верха ПОЛОСЫ Марио
 * (BAND_TOP=104) — ещё 104, итого 160 строк = 15360 тиков после VBlank, в течение
 * которых луч ЕЩЁ НЕ коснулся полосы спрайта. Поэтому каждый кадр сразу после
 * VBlank мы успеваем стереть старого и нарисовать нового Марио, а луч до его строк
 * доходит уже на готовой картинке — tear/мерцания нет. Перед записью сверяемся со
 * счётчиком: если тяжёлый кадр не влез и луч уже у полосы — рисование в ЭТОМ кадре
 * пропускаем (пропуск = один кадр без обновления, не мерцание).
 *
 * Строка 0 (цифры FPS) лежит выше полосы (y<8), луч доходит до неё раньше
 * (~56 строк после VBlank) — обновляем её в более раннем окне.
 *
 * Фон (текст + земля) статичен, рисуется один раз. Двигается только спрайт Марио:
 * каждый кадр в окне после VBlank стираем старого (возврат фона из относительного
 * RAM-патча) и рисуем нового; перед отрисовкой фон снимается в патч.
 *
 * Марио набран кубиками 8x8, поза = 3 клетки x 4. Шаг 4 px (x кратно 4); при x
 * кратном 8 — побайтовый вывод (frac=0), при сдвиге на 4 px — тетрадный сдвиговый
 * вывод (frac=4). Вывод спрайта — 8080-ассемблер (src/render.asm): спрайт закодирован
 * КОЛОНОЧНО, столбец VRAM проходится линейно (данные +3, адрес -1), стирание —
 * копирование из относительного RAM-патча (шаг колонки = ROWS).
 */

#include "v06.h"

#include "src/tiles.inc"      /* screen_pal4, tile_ground */
#include "src/sprites.inc"    /* mario_frames[N][2], mario_turn[2][2], mario_run[3][2], MARIO_* */
#include "src/background.inc" /* bg_tileset, bg_map, BG_*  (фон из mario-8cols) */

/* Примитивы вывода из render.asm (по идиомам mario-16cols/mario.asm).
 * Параметры передаются через глобалы rs_* ниже — без стековых аргументов. */
extern void mario_draw_sprite(void);
extern void mario_zero_sprite(void);      /* стирание = обнуление следа в E000/C000 */

/* Примитивы «секундомера растра» из src/timer.asm (КР580ВИ53 канал 2, порт 09h).
 * reload — из ISR на каждом VBlank; read — опрос позиции луча в main. */
extern void mario_timer_reload(void);
extern unsigned int mario_timer_read(void);

/* Звук (src/sfx_mario.c): прыжок/приземление — тон на КР580ВИ53 (vi53.c,
 * frame-exact таблица делителей). Шумогенератора у ВИ53 нет, поэтому ветра при беге нет.
 * КАНАЛЫ ЗВУКА = 0 и 1; канал 2 зарезервирован под таймер и звуком не трогается.
 * Покадровый движок живёт в прерывании (frame_handler = mario_frame). */
extern void mario_sfx_init(void);
extern void mario_sfx_jump(void);
extern void mario_sfx_land(void);
extern void mario_sfx_frame(void);
extern unsigned char mario_sfx_running;   /* зеркало флага бега для ISR-движка */

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
 * тиков — вдвое медленнее дуга. Импульс vy=-12 и гравитация +1 задают ВЫСОТУ,
 * а JUMP_STEP меняет лишь ДЛИТЕЛЬНОСТЬ, поэтому высота не меняется. */
#define JUMP_STEP    2                 /* прыжок: шаг физики раз в 2 тика      */

/* ------------------------------ СТАРТ ПОЗИЦИИ --------------------------- */
#define START_MX       26*8       /* x левого верха Марио на старте (кратен 8)  */
#define START_MY       GROUND_MY /* y стоящего Марио на старте                  */
#define START_FACING   0         /* 0 = лицом влево, 1 = вправо                 */

/* ------------------------------ ПЛОСКОСТИ (СПЛИТ) ----------------------- */
/* Индекс палитры = bg*4 + ch (схема mario-8cols). ФОН — старшие 2 бита
 * (плоскости веса 4 = 0xA000 и веса 8 = 0x8000). MARIO — младшие 2 бита
 * (веса 1 = 0xE000 и 2 = 0xC000). Поэтому ch=0 => «показать фон этого ряда»,
 * и Mariо — прямая запись в свои плоскости, а стирание = обнуление тех же
 * плоскостей (фон под Mariо не перерисовывается и физически не может исчезнуть). */
#define BASE_A0   0xE000       /* Mariо, вес 1 (ch бит0)  */
#define BASE_BG8  0x8000       /* фон, вес 8 (bg бит1)    */
#define BASE_BG4  0xA000       /* фон, вес 4 (bg бит0)    */

/* ------------------------- ОКНА ГОНКИ С ЛУЧОМ --------------------------- */
/* Счётчик после перезапуска на VBlank убывает от 29952; elapsed = 29952 − счётчик
 * = тикам от начала кадра. 96 тиков = 1 строка растра. Окна — сколько elapsed
 *Still допустимо, чтобы луч гарантированно ещё не дошёл до рисуемых строк
 * (с запасом на само erase+draw). */
#define T_FULL        29952u           /* полный кадр таймера (=0x7500)         */
#define T_LINES(t)    ((t) / 96u)      /* строк луча за elapsed-тика            */
#define LINES(x)      ((x) * 96u)      /* тика на x строк                       */
/* WAKE-фаза: рисуем Марио, только когда УЖЕ прошёл его коридор. Строка y
 * читается лучом на растре 40+y (256 видимых + верхняя часть гашения). Ждём
 * прохода НИЖНЕЙ строки пятна (bot-1), плюс запас на «луч ушёл». */
#define RASTER_BASE    40u              /* raster первого видимого ряда (y=0)  */
#define WAKE_MARGIN    4u               /* строк запаса после прохода низа     */
/* Строка 0 (FPS) вверху (y<8). От VBlank до y=0 луч идёт 312−256 = 56 строк.
 * Окно 44 строки — HUD пишется раньше спрайта и в узком верхнем окне. */
#define T_HUD_MAX     LINES(44)        /* 4224: окно обновления цифр FPS       */

/* --------------------------------- ВВОД --------------------------------- */
#define KEY_LEFT   8
#define KEY_RIGHT  9
#define KEY_DOWN   10
#define KEY_SPACE  32

/* Состояние СС (Shift) после kbd_scan() — задаётся в kbdscan.asm. */
extern unsigned char kbd_shift_state;

/* ------------------------------ СОСТОЯНИЕ ------------------------------- */
/* Битки звуковых событий за кадр (из update_state, исполняются после показа
 * кадра — иначе звук опережает картинку на целый кадр). */
#define EV_JUMP      1
#define EV_LAND      2

static unsigned char palA[16];

/* Параметры для render.asm (ассемблер читает/пишет их напрямую).
 * НЕ static — символы должны быть видны линкеру. */
unsigned int  rs_spr;                    /* указатель на спрайт (заголовок)  */
unsigned int  rs_data;                   /* колонка данных (считает asm)     */
unsigned int  rs_p0, rs_p1;              /* VRAM-указатели верха колонки     */
unsigned char rs_cols;                   /* знаковый счётчик колонок (-w..0) */
unsigned char rs_frac;                   /* суб-клеточный сдвиг: 0 или 4 px */

/* ВРЕМЕННАЯ диагностика wake-гонки (учёт перехода через VBlank). */
unsigned char dbg_frac;                  /* frac текущего кадра (0 или 4)     */
unsigned int  dbg_start;                 /* raster старта erase (кадр N)      */
unsigned int  dbg_mid;                   /* raster после erase (старт draw)   */
unsigned int  dbg_eline;                 /* длительность erase, строк         */
unsigned int  dbg_dline;                  /* длительность draw, строк          */
unsigned int  dbg_elmax4;                /* макс. erase строк среди frac=4    */
unsigned int  dbg_dlmax4;                /* макс. draw  строк среди frac=4    */
unsigned int  dbg_elmax0;                /* макс. erase строк среди frac=0    */
unsigned int  dbg_dlmax0;                /* макс. draw  строк среди frac=0    */
unsigned int  dbg_endr;                  /* raster конца draw (в СВОЁМ кадре)  */
unsigned int  dbg_earliest;              /* 40 + min(old_y,my): raster первого  */
                                         /*   чтения написанных строк в N+1     */
int           dbg_minmargin;             /* мин. запас (earliest-endr, wrap)    */
int           dbg_minm4;                 /* то же, но только для frac=4         */
unsigned int  dbg_tear;                  /* кадров с margin<0                   */
unsigned int  dbg_tear4;                 /* кадров с margin<0 И frac=4          */
unsigned int  dbg_draws;                 /* сколько реальных erase+draw         */

/* Прямоугольник последнего НАРИСОВАННОГО спрайта (для стирания). Заполняется
 * только при фактической отрисовке — если кадр-гейтskip’нул, остаётся прежним,
 * и следующий erase сотрёт именно то пятно, что реально на экране. */
static unsigned char old_x, old_y, old_w;   /* old_w в клетках, h=MARIO_HPIX */
static unsigned char old_valid;
static const unsigned char *last_spr;       /* поза, реально нарисованная */

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

/* Пропуск перерисовки: сколько кадров подряд спрайт в той же позиции/позе
 * (x/y/поза не менялись) — после первого показа erase+draw можно пропустить. */
static unsigned char draw_skipped;

/* HUD частоты кадров: показанных (draw_frame) кадров за окно VBlank -> FPS. */
static unsigned char fps_val = 50;            /* текущее показываемое число FPS (0..99) */
static unsigned char hud_val = 0xFF;          /* значение FPS, уже напечатанное на экране */
static unsigned int fps_vbl;                    /* VBlank накоплено в окне          */
static unsigned int fps_frames;                 /* показанных кадров в окне          */

/* ------------------------------- УТИЛИТЫ -------------------------------- */

/* Собрать 16-слотовую палитру «сплит по плоскостям»: слот = bg*4 + ch.
 * bg (плоскости 8/4): 0=небо 0xFD, 1=чёрный 0x00, 2=белый 0xFF, 3=зелёный 0x2A.
 * ch (плоскости 2/1): 0=прозрачно (показать фон ряда), 1=красный, 2=розовый,
 * 3=чёрный — один и тот же RGB во всех четырёх «рядах» bg (Mariо побеждает
 * фон без маскирования). Таблица идентична level_palette mario-8cols. */
static void build_palette(void)
{
    /* Присваивания константами вместо локального `static const p[16]`:
     * sccz80 ненадёжно инициализирует локальные static-массивы. */
    palA[0]  = 0xFD; palA[1]  = 0x0D; palA[2]  = 0xF7; palA[3]  = 0x00; /* bg0 небо */
    palA[4]  = 0x00; palA[5]  = 0x0D; palA[6]  = 0xF7; palA[7]  = 0x00; /* bg1 чёрн */
    palA[8]  = 0xFF; palA[9]  = 0x0D; palA[10] = 0xF7; palA[11] = 0x00; /* bg2 бел  */
    palA[12] = 0x2A; palA[13] = 0x0D; palA[14] = 0xF7; palA[15] = 0x00; /* bg3 зел  */
}

/* Залить одну клетку фона (col c, row r, локальный тайл t) в СТАРШИЕ
 * плоскости: байты src[0..7] -> вес8 (0x8000), src[8..15] -> вес4 (0xA000).
 * Внутри блока строка тайла j (сверху вниз) идёт по убыванию адреса
 * (base + c*0x100 + (255 - r*8 - j)) — как в mario-8cols _rw_copy8. */
static void draw_bg_cell(unsigned char c, unsigned char r, unsigned char t)
{
    const unsigned char *src = bg_tileset + (unsigned int)t * 16u;
    unsigned int a8 = BASE_BG8 + (unsigned int)c * 0x100u
                          + (255u - (unsigned int)r * 8u);
    unsigned int a4 = BASE_BG4 + (unsigned int)c * 0x100u
                          + (255u - (unsigned int)r * 8u);
    unsigned char *p8 = (unsigned char *)a8;
    unsigned char *p4 = (unsigned char *)a4;
    unsigned char j;
    for (j = 0; j < 8u; j++) {
        *p8-- = src[j];
        *p4-- = src[8u + j];
    }
}

/* Один раз при старте: залить статичный фон (bg_map) в старшие плоскости. */
static void draw_background(void)
{
    unsigned char c, r, t;
    for (r = 0; r < BG_ROWS; r++)
        for (c = 0; c < BG_COLS; c++) {
            t = bg_map[(unsigned int)r * BG_COLS + c];
            if (t) draw_bg_cell(c, r, t);     /* 0 = небо, обе плоскости 0 */
        }
}

/* Текст/цифры печатаем ФОНОВЫМ цветом (индекс кратен 4 => ch=0, младшие
 * плоскости Mariо не трогает). Цвет 8 = белый фон (bg2, slot 8). */
static void draw_text_line(unsigned char col, unsigned char y, const char *s)
{
    gfx_print(col, y, s, 8);   /* bg2 = белый, только старшие плоскости */
}

/* Обнулить пятно прежнего Mariо в МЛАДШИХ плоскостях (E000/C000): ch=0 =>
 * сквозь него снова виден фон из старших плоскостей. Слепок/патч не нужен. */
static void erase_sprite(unsigned char x, unsigned char y, unsigned char wcells)
{
    unsigned int col  = x >> 3;
    rs_p0   = BASE_A0 + col * 0x100u + (255u - (unsigned int)y);
    rs_p1   = rs_p0 - 0x2000u;
    rs_cols = (unsigned char)(-(int)wcells);
    mario_zero_sprite();
}

/* Нарисовать спрайт-позу. Суб-пиксельный сдвиг +4 px (x не выровнен по сетке
 * 8 px) считается на РАНТАЙМЕ: rs_frac = x&7 (0 или 4); при 4 render.asm
 * собирает сдвинутые тайлы через SBYTE-стейджинг и рисует wcells+1 колонок. */
static void draw_sprite(unsigned char x, unsigned int y, const unsigned char *spr)
{
    unsigned int col = x >> 3;
    rs_p0  = BASE_A0 + col * 0x100u + (255u - y);
    rs_p1  = rs_p0 - 0x2000u;
    rs_spr = (unsigned int)spr;
    rs_frac = (unsigned char)(x & 7u);
    mario_draw_sprite();
}

/* ------------------------------ ЛОГИКА КАДРА ---------------------------- */

/* Выбрать позу [0..7] по состоянию. Суб-пиксельный сдвиг (mx & 7 == 4)
 * обрабатывается рантайм-путём render.asm (rs_frac), поэтому здесь всегда
 * отдаётся ВЫРОВНЕННЫЙ префаб — двойные _sh-варианты в ROM больше не нужны. */
static const unsigned char *pick_sprite(void)
{
    unsigned char f;
    unsigned char d  = facing ? 1u : 0u;
    if (turning) {
        if (turn_step == 0)
            return mario_turn[0][0];                     /* фронтальная */
        else
            return mario_turn[1][turn_target];
    }
    if (crouch)                 f = 6;              /* присел            */
    else if (!grounded)         f = 7;              /* прыжок            */
    else if (running && moving)
        return mario_run[run_seq[anim_step]][d];
    else if (moving)            f = walk_seq[anim_step]; /* ходьба 01->02->03->02 */
    else                        f = 0;              /* стойка статична (мавок убран: он каждые ~16 кадров дёргал полный redraw) */
    return mario_frames[f][d];
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

    /* Двигаемся. Шаг всегда 4 px; скорость — частотой шага. */
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

    /* Вертикальная физика (интегрируем раз в JUMP_STEP тиков). */
    if (!grounded && ++jump_timer >= JUMP_STEP) {
        jump_timer = 0;
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

/* Нарисовать ТОЛЬКО две цифры FPS (колонки 17,18; строка 0) в ФОНОВЫх
 * плоскостях A000/8000 белым (bg2) — младшие плоскости Mariо не трогает.
 * Приставка «FPS=» статична и печатается один раз при инициализации. */
static void hud_paint_digits(void)
{
    gfx_active_planes = 0x0C;                 /* только фоновые биты 2..3 (A000/8000) */
    gfx_put_char(17, 0, (char)('0' + fps_val / 10u), 8);
    gfx_put_char(18, 0, (char)('0' + fps_val % 10u), 8);
    gfx_active_planes = 0x0F;
}

/* Обработчик кадрового прерывания (50 Гц). ПОРЯДОК важен:
 * 1) перезапустить «секундомер растра» (канал 2) на полный кадр — этим мы
 *    привязываем фазу счётчика к VBlank и весь кадр он линейно отсчитывает
 *    положение луча. Дешёвые 3 OUT в порт ВИ53 (не 02/0C) — растру не мешают.
 * 2) затем — покадровый звук. Он долгий, но пишет только ВИ53-порты каналов
 *    0/1 (не 02/0C), поэтому после reload безопасен. */
static void mario_frame(void)
{
    mario_timer_reload();                    /* старт нового кадра под луч     */
    mario_sfx_frame();                       /* ровно 1 такт звука за VBlank   */
}

/* Спин до raster-строки `target` (в тиках от VBlank). Читаем таймер-«секундомер»
 * луча; выход, когда elapsed >= target (луч ушёл достаточно низко) ИЛИ когда
 * elapsed ПЕРЕСТАЛ расти — значит пересекли VBlank (счётчик перезагрузился),
 * этот кадр упущен, рисуем немедленно. Никаких обращений к VRAM здесь нет. */
static void spin_to_raster(unsigned int target)
{
    unsigned int t, e, prev;
    t = mario_timer_read();
    prev = (t <= T_FULL) ? (T_FULL - t) : 0u;
    while (prev < target) {
        t = mario_timer_read();
        e = (t <= T_FULL) ? (T_FULL - t) : 0u;
        if (e < prev) break;            /* перезагрузка на VBlank → поздно     */
        if (e >= target) break;         /* достиг нужной raster-строки         */
        prev = e;
    }
}

/* Стереть/нарисовать спрайт и (опционально) HUD, но только пока луч не дошёл
 * до соответствующих строк. Опрос таймера — источник истины о позиции луча. */
static void draw_frame(void)
{
    const unsigned char *spr = pick_sprite();
    unsigned char wcells = spr[0];
    unsigned char w_new;
    unsigned int t, elapsed;

    /* Строка 0 (FPS) — раньше спрайта: окно T_HUD_MAX. Пишется редко (~1/с). */
    if (hud_val != fps_val) {
        t = mario_timer_read();
        elapsed = (t <= T_FULL) ? (T_FULL - t) : 0u;
        if (elapsed <= T_HUD_MAX) {
            hud_paint_digits();
            hud_val = fps_val;
        }
    }

    /* Пропуск перерисовки: поза/x/y не менялись с прошлого фактического показа —
     * картинка спрайта та же, erase+draw не нужны (экономит окно под луч). */
    if (old_valid && spr == last_spr && mx == old_x && (unsigned char)my == old_y) {
        draw_skipped = 0;                    /* сцена верна — тихо пропускаем  */
        return;
    }

    /* WAKE: ждём, пока луч ПРОЙДЁТ нижнюю строку пятна (старого или нового —
     * что ниже), и только затем рисуем, чтобы ни один байт не писался под
     * лучом. bot = my+MARIO_HPIX (исключающая нижняя строка). Ряд (bot-1)
     * читается на растре RASTER_BASE+(bot-1); ждём RASTER_BASE+bot+запас. */
    {
        int bot = my + MARIO_HPIX;
        if (old_valid) {
            int bo = (int)old_y + MARIO_HPIX;
            if (bo > bot) bot = bo;
        }
        spin_to_raster(LINES(RASTER_BASE + (unsigned int)bot + WAKE_MARGIN));
    }

    /* 1. Стереть прежнего Mariо: обнулить его след в младших плоскостях. */
    {
        unsigned int tS, tM, tE;
        int sl, el, ey, miny, wrap, margin;
        int midl, eln, dln;
        tS = mario_timer_read();
        sl = (int)((T_FULL - tS) / 96u);
        miny = my;
        if (old_valid && (int)old_y < miny) miny = (int)old_y;
        ey = (int)RASTER_BASE + miny;             /* raster первого чтения в N+1 */

        if (old_valid)
            erase_sprite(old_x, old_y, old_w);

        tM = mario_timer_read();
        midl = (int)((T_FULL - tM) / 96u);

        /* 2. Нарисовать нового (прямой bitblit в E000/C000; фон в других
         *    плоскостях, слепок не нужен). При рантайм-сдвиге (mx&7!=0) спрайт
         *    занимает wcells+1 колонок -> на ширину стирания следующего кадра. */
        w_new = (unsigned char)(wcells + ((mx & 7u) ? 1u : 0u));
        draw_sprite(mx, (unsigned int)my, spr);

        tE = mario_timer_read();
        el = (int)((T_FULL - tE) / 96u);
        /* длительности в строках с учётом возможного пересечения VBlank */
        eln = (midl >= sl) ? (midl - sl) : (midl + (int)(312 - (unsigned int)sl));
        dln = (el  >= midl) ? (el - midl)  : (el  + (int)(312 - (unsigned int)midl));
        dbg_mid    = (unsigned int)midl;
        dbg_eline  = (unsigned int)eln;
        dbg_dline  = (unsigned int)dln;
        if (mx & 7u) {
            if ((unsigned int)eln > dbg_elmax4) dbg_elmax4 = (unsigned int)eln;
            if ((unsigned int)dln > dbg_dlmax4) dbg_dlmax4 = (unsigned int)dln;
        } else {
            if ((unsigned int)eln > dbg_elmax0) dbg_elmax0 = (unsigned int)eln;
            if ((unsigned int)dln > dbg_dlmax0) dbg_dlmax0 = (unsigned int)dln;
        }
        wrap = (el < sl) ? 1 : 0;                  /* crossing VBlank */
        dbg_frac    = (unsigned char)(mx & 7u);
        dbg_start   = (unsigned int)sl;
        dbg_endr    = (unsigned int)el;
        dbg_earliest= (unsigned int)ey;
        /* Tear возможен только если draw перелился в кадр N+1 и закончился
         * не раньше, чем луч начал читать верхнюю написанную строку. */
        if (wrap) margin = ey - el; else margin = 10000;
        if (dbg_draws == 0) dbg_minmargin = margin;
        else if (margin < dbg_minmargin) dbg_minmargin = margin;
        if (mx & 7u) {                              /* только сдвинутые кадры   */
            if (margin < dbg_minm4) dbg_minm4 = margin;
        }
        if (wrap && el >= ey) {
            dbg_tear++;
            if (mx & 7u) dbg_tear4++;
        }
        dbg_draws++;
    }

    /* 4. Запомнить пятно и позу для следующего обращения. */
    old_x = mx;
    old_y = (unsigned char)my;
    old_w = w_new;
    old_valid = 1;
    last_spr = spr;
    draw_skipped = 0;
}

/* --------------------------------- MAIN --------------------------------- */
static void init_background(void)
{
    unsigned char y = 0;
    /* Сразу скрыть экран чёрной палитрой: фон строится вживую (print/тайлы),
     * при дефолтной 16-цветной палитре эта сборка была бы видна как «чтение». */
    gfx_set_black_palette();
    gfx_set_mode(GFX_MODE_256_16);
    gfx_fill_planes(0x0F, 0x00);          /* все плоскости = 0 (небо, Mariо чисто) */

    draw_background();                    /* земля/кусты/облака в старшие плоскости */

    /* Текст — фоновым белым в полосе движения Mariо: спрайт перекрывает его
     * своими цветами без маскирования (ch!=0 => цвет Mariо, ch=0 => фон ряда). */
    y = 48;
    draw_text_line(1,  y,       "VECTOR-06C RACING THE BEAM");
    draw_text_line(1,  y += 12, "");
    draw_text_line(1,  y += 12, "PLANE SPLIT (mario-8cols):");
    draw_text_line(1,  y += 12, "BG = A000/8000  MARIO=E000/C000");
    draw_text_line(1,  y += 12, "PAL IDX = bg*4 + ch");
    draw_text_line(1,  y += 12, "");
    draw_text_line(1,  y += 12, "ERASE = ZERO MARIO PLANES");
    draw_text_line(1,  y += 12, "BG ALWAYS SHOWS (ch=0)");
    draw_text_line(1,  y += 12, "");
    draw_text_line(1,  y += 12, "ARROWS - WALK    SHIFT - RUN");
    draw_text_line(1,  y += 12, "SPACE  - JUMP    DOWN  - DUCK");
    draw_text_line(1,  y += 12, "");
    draw_text_line(1,  y += 12, "SMOOTH LIKE DBL, NO SWAP");

    /* FPS-приставка «FPS=» статична — печатаем один раз (bg-белый, plane 4/8). */
    gfx_active_planes = 0x0C; gfx_print(13, 0, "FPS=", 8);
    gfx_active_planes = 0x0F;
    hud_paint_digits(); hud_val = fps_val;
}

void main(void)
{
    unsigned char ev;
    unsigned char last_fc;
    volatile unsigned char *fc_lo;

    build_palette();
    mario_sfx_init();

    /* Кадровый ISR (reload таймера + звук) ставим ДО первой отрисовки: после
     * первого же VBlank счётчик канала 2 синхронизируется с лучом, и draw_frame
     * сможет читать реальную фазу. Пока ISR не сработал ни разу — выждём один
     * VBlank. */
    frame_handler = mario_frame;

    init_background();

    mx = START_MX;
    my = START_MY;
    vy = 0;
    facing = START_FACING;
    grounded = 1;
    old_valid = 0;
    last_spr = 0;
    draw_skipped = 0;
    dbg_minmargin = 32000;
    dbg_minm4 = 32000;

    v06_wait_frame();                       /* первый VBlank: reload таймера   */

    draw_frame();                           /* первый кадр Марио (в окне)      */

    gfx_fade_in(palA, FADE_HOLD);           /* проявить экран */

    /* fixed timestep. Младший байт frame_count читаем одним LDA (atomic 8080). */
    fc_lo   = (volatile unsigned char *)&frame_count;
    last_fc = *fc_lo;
    fps_vbl = 0; fps_frames = 0;

    for (;;) {
        /* Кадранс wake-фазы. Якорь — младший байт frame_count (один LDA,
         * atomic на 8080): ждём нового VBlank. На ДВИЖУЩИХся кадрах draw уже
         * долился за границу кадра, поэтому выход из спинаImmediate (луч
         * мы уже «догнали»); на статичных (draw скипанулся рано) — спин до
         * ближайшего VBlank. В обоих случаях ровно 1 итерация = 1 кадр 50 Гц. */
        while (*fc_lo == last_fc) { /* spin: луч идёт, VRAM не трогаем */ }
        last_fc = *fc_lo;

        /* Ввод+физика — ДО спина ожидания луча (к VRAM не прикасаемся, позицию
         * нужно знать заранее). Снимок матрицы неблокирующий. */
        kbd_scan_now();                     /* обновить kbd_rows + shift, без halt */

        ev = update_state();                /* РОВНО 1 шаг физики на кадр */
        mario_sfx_running = running;        /* зеркало флага бега для ISR-движка */

        draw_frame();                        /* spin_to_raster(wake) -> erase+draw */
        /* Звук событий — только просим (байтовый флаг), исполнит ISR. */
        if (ev & EV_JUMP) mario_sfx_jump();
        if (ev & EV_LAND) mario_sfx_land();

        tick++;

        /* Частота показанных кадров: виток = один shown-кадр (cadence замкнут
         * на VBlank якорем выше). Окно ~50 витков. */
        fps_frames++;
        fps_vbl++;
        if (fps_vbl >= 50) { fps_refresh(); fps_vbl = 0; fps_frames = 0; }
    }
}
