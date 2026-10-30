/*
 * main.c — putup-beam: демо beam-подсистемы (lib/gfx/beam.c) на ассетах
 * игры putup. Уровень 16×32 клетки (512px = ровно 2 кольца VRAM) с
 * аппаратным вертикальным скроллингом, плавной анимацией героя (маска,
 * позиция идёт к клетке-цели по 4px за кадр) и тремя патрулирующими
 * врагами (ходок, ворона, вертолёт — как state1/3/5 putup).
 *
 * Механика (по плану демо, без HUD/счёта/времени/Hurry Up/огня/музыки):
 *   - собрать все предметы {07,0A..0E} -> замок (клетка 24) открывается:
 *     клетка становится выходом и мигает фазами 22/23 (как data_flip_tab
 *     putup);
 *   - войти в открытый выход -> рестарт уровня;
 *   - касание врага -> рестарт уровня;
 *   - скрытый кирпич (клетка 05h, глиф 7Dh) по нажатию ↓ (стоя на нём)
 *     становится «?»-кубиком (04h), а «?»-кубик (глиф 7Eh) — случайным
 *     фруктом: как обработчики func_player_move_d putup, которые диспетчер
 *     клавиш зовёт именно на ↓ (CPI 7Dh / CPI 7Eh на клетку под героем),
 *     а не на факт приземления;
 *   - ESC -> fade-out и выход.
 *
 * Контракт цикла (BEAM_TZ §2.2, ТФ-1..7): вся видимая графика — через
 * beam_*; единственный писатель VRAM в кадре — beam_render; кадровый ISR —
 * timer_start() + kbd_scan_now() (последний ещё и сбрасывает gfx_scroll_row
 * в порт 03h на VBlank — flush регистра скролла beam_set_cam, память:
 * port 03h shared scroll+kbd).
 *
 * Герой: целевое движение — логика задаёт цель ±16px (клетка), позиция
 * идёт к ней по 4px за кадр (как в коммите fca0746); на твёрдую клетку
 * бокс прижимается точно. ВИДИМЫЙ шаг — 4px по обеим осям, как
 * midpoint-фаза оригинала (var_glyph_hoff/voff в func_hero_render/
 * func_enemy_render). Скорость подобрана по оригиналу: там за тик в 12
 * кадров герой делает 2 клетки, враг — 1 (отношение 2:1); здесь герой
 * идёт 4px/кадр (50px за проход в 12 кадров при темпе 50 Гц), враги —
 * тем же шагом через кадр.
 * Столкновения — по ВСЕМУ боксу 16x16: при шаге вбок и в прыжке бокс
 * накрывает две клетки,
 * поэтому сквозь стены не пройти и герой встаёт вплотную к ним.
 * Гравитация тянет вниз (клетки под боксом не тверды), ↑ поднимает по шахте
 * (удобство демо); прыжок — action-клавиша (ПРОБЕЛ/СС) как
 * func_gamestate_catch оригинала: подъём на 4 клетки (там счётчик подъёма
 * останавливается на 04h), короткое зависание
 * на апексе, отпускание — сразу падение; клавиши работают во всех фазах
 * полёта (управление в воздухе). «?»-ящики (код 04h)
 * твёрды (глифы 7Eh..82h >= 77h в оригинале). Враги: пара кадров
 * state1/state2 = направление вправо/влево (тайлы tg[20]/tg[19]
 * оригинала) и ходят только по пустым клеткам — как func_entity_state1
 * (CPI 20h); шаг 4px, но через кадр (вдвое медленнее героя).
 * Кадр ходьбы привязан к субшагу (hero_x>>2)&1 (аналог var_page_flip):
 * idx = 0/1 шаг вправо, 2 стойка вправо, 3/4 шаг влево, 5 стойка влево
 * (формула putup idx = work_const + 3*move_dir − 1).
 */

#include "v06.h"
#include "assets.inc"
#include "level.inc"

/* --- коды клеток (level.inc / tools/level_editor.py) --- */
#define CODE_EMPTY   1u
#define CODE_ASK     4u    /* «?»-кубик: нажатие сверху -> фрукт        */
#define CODE_HIDDEN  5u    /* скрытый кирпич: нажатие сверху -> «?» 04h */
#define FRUIT_FIRST  10u   /* фрукты 0Ah..0Dh, 0Eh — кольцо            */
#define CODE_EXIT_LT 22u   /* светлая фаза выхода (bg_tiles[22]) */
#define CODE_EXIT_DK 23u   /* тёмная фаза; до открытия — стена   */
#define CODE_LOCK    24u   /* закрытый выход: замок с вставленным ключом */

#define KEY_CODE(c)  ((c) == 7u || ((c) >= 10u && (c) <= 14u))
/* Предметы putup: 07h — яйцо-бонус (0x72), 0Ah..0Dh — фрукты (0x6E..0x71),
 * 0Eh — кольцо (+1 жизнь, 0x73). Все проходимы и подбираются ("ключи" демо).
 * 08h — кирпич-стена, 09h — спецклетка выхода: НЕ предметы. */
/* твёрдость putup: глифы тайла >= 77h; «?»-кубик (04h) — глифы 7Eh..82h,
 * скрытый кирпич (05h) — глиф 7Dh, твёрдый как обычный кирпич */
#define SOLID_CODE(c) ((c) == 2u || (c) == CODE_ASK || (c) == CODE_HIDDEN \
                       || (c) == 8u)

/* прыжок: подъём 4 клетки — как func_gamestate_catch putup (CPI 04h на
 * счётчике подъёма: 4 прохода по клетке), зависание апекса */
#define JUMP_PX       64u
#define HANG_FRAMES   3u    /* тиков на апексе (~0.4 с, как 3 тика putup) */

/* --- кадр героя (индексы hero_frames[7][2]) --- */
#define HF_WALK_R0 0u
#define HF_WALK_R1 1u
#define HF_STAND_R 2u
#define HF_WALK_L0 3u
#define HF_WALK_L1 4u
#define HF_STAND_L 5u

/* --- камера: коридор следования (схема mario-16cols) --- */
#define CAMR_MIN_ROW  8u   /* полос 8px от верха экрана */
#define CAMR_MAX_ROW  22u
#define CAM_MAX       ((unsigned int)LEVEL_ROWS * 16u - 256u)

/* --- скорости (схема коммита fca0746) ---
 * Движение целевое: логика задаёт цель ±16px (клетка), отображение идёт
 * к ней по 4px за кадр. Это и есть «4px за шаг»: клетка проходится
 * четырьмя кадрами, промежуточные положения рисуются вариантом
 * дескриптора со сдвигом 4px (столбец VRAM = 8px). Враги — тем же
 * шагом 4px, но через кадр: в оригинале герой ровно вдвое быстрее. */
#define HERO_X_STEP   4u   /* px/кадр по X к цели                   */
#define HERO_Y_STEP   4u   /* px/кадр по Y (подъём/гравитация)     */
#define ENEMY_X_STEP  4u   /* px/кадр по X, но через кадр           */
#define ENEMY_STEP_MASK 1u /* враг двигается через кадр: 2:1 к герою */

#define HERO_ID       0u
#define ENEMY_ID0     1u

/* экземпляр героя + 3 врага */
#define NUM_ENEMIES   3u

/* Виды врагов (индексы enemy_frames[вид][фаза][субшаг]): 0 — ходок
 * (tg[20]/tg[19], state1/state2 putup), 1 — ворона (tg[18]/tg[17]),
 * 2 — вертолёт (tg[15]/tg[16] — две фазы ротора). Для ходока и вороны
 * фаза = направление, у вертолёта — положение ротора (anim_tick).
 * Вид по слотам — level_enemy_kinds[] в level.inc (правит редактор). */
#define ENEMY_WALKER 0u
#define ENEMY_CROW   1u
#define ENEMY_HELI   2u
static unsigned char anim_tick;       /* такт анимации: ротор вертолёта, темп врагов */

/* --- состояние игры --- */
static unsigned char game_map[LEVEL_ROWS * LEVEL_COLS]; /* зеркало cellmap beam */
static unsigned char keys_left;
static unsigned char exit_open;
static unsigned char exit_phase;      /* 0/1 — мигание 22/23 */
static unsigned char exit_timer;
static unsigned int  cam_y;

static unsigned int  hero_x, hero_y;  /* мир, px, верхний левый угол 16x16 */
static unsigned int  hero_tx, hero_ty;/* цель шага (±16px от клетки)     */
static unsigned char mv_x, mv_y;      /* идёт шаг по X / по Y           */
static unsigned char rising;          /* шаг по Y — подъём             */
static unsigned char hero_vstate;     /* 0 земля/падение, 1 подъём, 2 апекс */
static unsigned char jump_left;       /* px подъёма осталось */
static unsigned char hang_left;       /* кадров зависания на апексе */
static unsigned char down_prev;       /* ↓ была нажата в прошлой итерации:
                                       * нажатие = кромка, не удержание   */
static unsigned char rnd_state;       /* xorshift8 (3,5,1): выбор фрукта  */
static unsigned char hero_dir;        /* 1 вправо, 0 влево (стойка/кадры) */
extern unsigned char kbd_shift_state; /* СС из kbdscan.asm (action-клавиша) */

static unsigned int  enemy_x[NUM_ENEMIES], enemy_y[NUM_ENEMIES];
static signed char   enemy_dir[NUM_ENEMIES];
static unsigned char enemy_shown[NUM_ENEMIES];

static beam_pat_t hero_pat;           /* attr: mask-путь, приоритет 2 */
static beam_pat_t enemy_pat[NUM_ENEMIES]; /* attr: плоский, приоритет 1 */

static unsigned char need_fade;       /* fade_in после render рестарта */
static unsigned char ovb_seen;        /* beam_overbudget — для отладчика */

/* --- профиль цикла для отладчика (не HUD) ---
 * Три точки в цикле: после отображения героя/врагов (prof[0] — верх
 * цикла), после beam_update (prof[1] — планировщик) и после beam_render
 * (prof[2] — исполнение плана). Копим дельты frame_count — целые кадры:
 * разрешение грубое, зато опора — счётчик ISR (тики ВИ53 читаются с
 * перекосом байт и для замера не годятся). Сумма по фазам за итерацию
 * равна реальному времени итерации точно; ошибка в ±1 кадр на точку
 * усредняется на сотнях итераций. prof_iter — итераций цикла,
 * prof_ticks — тиков логики. */
static unsigned int prof_fc;          /* frame_count на прошлой точке   */
static unsigned int prof[3];          /* кадров по фазам               */
static unsigned int prof_iter;        /* итераций цикла                */
static unsigned int prof_ticks;       /* тиков логики                  */
static unsigned int prof_restart;     /* рестартов уровня              */
static unsigned char prof_i;          /* номер фазы                     */

static void prof_mark(void)
{
    unsigned int fc = frame_count;

    prof[prof_i] += (unsigned int)(fc - prof_fc);
    prof_fc = fc;
    if (++prof_i >= 3u)
        prof_i = 0;
}

static void prof_top(void)
{
    prof_iter++;
}

static void restart_level(void);

static const beam_level_t level = {
    0, level_map, bg_tiles, LEVEL_ROWS, LEVEL_COLS, 1
};

/* Кадровый ISR: фаза таймера держится каждый VBlank (схема mario-timer),
 * клавиатура сканируется на входе ISR (луч гарантированно в бланкинге) и
 * там же gfx_scroll_row уходит в порт 03h — flush скролла beam_set_cam. */
static void on_frame(void)
{
    timer_start();
    kbd_scan_now();
}

static unsigned char cell_at(unsigned char col, unsigned char row)
{
    if (col >= LEVEL_COLS || row >= LEVEL_ROWS) return 2u;  /* вне = стена */
    return game_map[row * LEVEL_COLS + col];
}

static unsigned char cell_solid(unsigned char col, unsigned char row)
{
    unsigned char c = cell_at(col, row);
    if (c == CODE_LOCK || c == CODE_EXIT_DK || c == CODE_EXIT_LT)
        return (unsigned char)(!exit_open);   /* выход/замок тверды до открытия */
    return (unsigned char)(SOLID_CODE(c) ? 1 : 0);
}

/* Проходима ли клетка для ВРАГА. Оригинал (func_entity_state1) сверяет
 * символ клетки с пробелом (CPI 20h) и разворачивается на всём остальном:
 * фрукты/ключи, «невидимый блокиратор» (код 03h), ящик, стены. Проверку
 * клетки ПОД врагом не делаем — в этом уровне под патрулями кирпич. */
static unsigned char cell_enemy_free(unsigned char col, unsigned char row)
{
    unsigned char c = cell_at(col, row);
    return (unsigned char)(c == CODE_EMPTY || c == 0u);
}

/* Твёрдость для бокса героя 16x16: перебираем ВСЕ клетки, которые бокс
 * накрывает. Проба одной центральной клетки пропускала касание стеной
 * краем бокса — в прыжке/на полшага герой проходил сквозь стену. */
static unsigned char hero_box_solid(int x0, int y0)
{
    unsigned char c0, c1, r0, r1, r, c;

    if (x0 < 0 || y0 < 0) return 1;
    c0 = (unsigned char)(x0 >> 4);
    c1 = (unsigned char)((x0 + 15) >> 4);
    r0 = (unsigned char)(y0 >> 4);
    r1 = (unsigned char)((y0 + 15) >> 4);
    for (r = r0; r <= r1; r++)
        for (c = c0; c <= c1; c++)
            if (cell_solid(c, r)) return 1;
    return 0;
}

/* --- скрытый кирпич / «?»-кубик (механика putup) --- */

/* xorshift8 (3,5,1): период 255, без деления и без state-таблиц. */
static unsigned char rnd8(void)
{
    unsigned char x = rnd_state;

    x ^= (unsigned char)(x << 3);
    x ^= (unsigned char)(x >> 5);
    x ^= (unsigned char)(x << 1);
    return rnd_state = x;
}

/* 0..n-1 без смещения: отбрасываем хвост маски 7 (n <= 5). */
static unsigned char rnd_slot(unsigned char n)
{
    unsigned char v;

    do v = (unsigned char)(rnd8() & 7u); while (v >= n);
    return v;
}

/* Случайный фрукт — как func_spawn_egg putup: 4 равных слота (0Ah..0Dh
 * вишни/яблоко/ананас/виноград) + кольцо 0Eh, но реже вдвое (отбраковка
 * половины попыток, CPI 04h/JNZ loc_111A). */
static unsigned char fruit_pick(void)
{
    unsigned char slot = rnd_slot(5u);

    if (slot == 4u && (rnd8() & 1u)) slot = rnd_slot(4u);
    return (unsigned char)(FRUIT_FIRST + slot);
}

/* Превращение клетки под боксом по нажатию ↓. putup: func_player_move_d
 * сверяет глиф клетки, ЛЕЖАЩЕЙ НИЖЕ игрока: 7Dh (скрытый кирпич) -> новый
 * тайл в этой же клетке; 7Eh («?») -> func_spawn_egg — ставит в клетку
 * случайный фрукт. Твёрдость 04h/05h одинаковая, так что герой после
 * превращения продолжает стоять сверху. */
static void hero_press_cell(unsigned char col, unsigned char row)
{
    unsigned char c = cell_at(col, row);

    if (c == CODE_HIDDEN) {
        game_map[row * LEVEL_COLS + col] = CODE_ASK;
        beam_bg_put(col, row, CODE_ASK);
    } else if (c == CODE_ASK) {
        unsigned char f = fruit_pick();

        game_map[row * LEVEL_COLS + col] = f;
        beam_bg_put(col, row, f);
        /* Счёт предметов не трогаем: фрукт из кубика — бонус, уровень
         * остаётся выигрышным даже если его не подобрать. */
    }
}

/* Нажатие ↓, стоя на клетке. Само нажатие (кромку, не удержание) считает
 * hero_logic — иначе «?»-кубик срабатывал бы каждую итерацию, а скрытый
 * кирпич и кубик превращались бы в один фрукт за один кадр. */
static void hero_press_down(void)
{
    hero_press_cell((unsigned char)((hero_x + 8u) >> 4),
                    (unsigned char)((hero_y + 16u) >> 4));
}

/* Клетка ПОД центром героя: подбор предмета, вход в открытый выход. */
static void hero_enter_cell(void)
{
    unsigned char cx = (unsigned char)((hero_x + 8u) >> 4);
    unsigned char cy = (unsigned char)((hero_y + 8u) >> 4);
    unsigned char c = cell_at(cx, cy);

    if (KEY_CODE(c)) {
        game_map[cy * LEVEL_COLS + cx] = CODE_EMPTY;
        beam_bg_put(cx, cy, CODE_EMPTY);
        if (keys_left) keys_left--;
        if (!keys_left) {
            exit_open = 1;            /* выход открыт — мигает фазой 22 */
            exit_phase = 0;
            exit_timer = 0;
        }
    }
    if (exit_open && cy == level_exit[0] && cx == level_exit[1])
        restart_level();              /* выход достигнут — рестарт */
}

static void restart_level(void)
{
    unsigned int i;

    gfx_set_black_palette();          /* первое окно рисуется без пейсинга */

    for (i = 0; i < (unsigned int)LEVEL_ROWS * LEVEL_COLS; i++)
        game_map[i] = level_map[i];
    keys_left = 0;
    for (i = 0; i < (unsigned int)LEVEL_ROWS * LEVEL_COLS; i++)
        if (KEY_CODE(game_map[i])) keys_left++;

    exit_open = 0;
    exit_phase = 0;
    exit_timer = 0;

    /* состояние выбора фруктов через рестарт НЕ сбрасываем (каждая игра
     * получает другое продолжение ряда), но гарантируем ненулевое: из 0
     * xorshift8 не выходит */
    if (!rnd_state) rnd_state = 0x5Au;
    down_prev = 0;                    /* ↓ перечитывается на новой карте */

    hero_x = (unsigned int)level_hero_spawn[1] * 16u;
    hero_y = (unsigned int)level_hero_spawn[0] * 16u;
    hero_tx = hero_x;                 /* цель = текущая клетка */
    hero_ty = hero_y;
    mv_x = mv_y = rising = 0;
    hero_vstate = 0;
    jump_left = 0;
    hang_left = 0;
    hero_dir = 1;
    hero_pat.attr = 0x12u;            /* бит4 = mask-путь, приоритет 2 */
    hero_pat.desc = hero_frames[HF_STAND_R][0];
    beam_init(&level);                /* spr_init внутри, окно целиком */
    beam_show(HERO_ID, &hero_pat);
    beam_move(HERO_ID, (unsigned char)(hero_x & 0xF8u), hero_y);

    for (i = 0; i < NUM_ENEMIES; i++) {
        enemy_x[i] = (unsigned int)level_enemy_spawns[i][1] * 16u;
        enemy_y[i] = (unsigned int)level_enemy_spawns[i][0] * 16u;
        enemy_dir[i] = (i & 1) ? -1 : 1;
        enemy_shown[i] = 0;
        enemy_pat[i].attr = 0x01u;    /* плоский путь, приоритет 1 */
        enemy_pat[i].desc = enemy_frames[level_enemy_kinds[i]][0][0];
    }
    anim_tick = 0;

    /* профиль с нуля — рестарт не должен попадать в замер (сам рестарт
     * считаем: полная перерисовка окна не бесплатна) */
    prof_fc = frame_count;
    prof[0] = 0;
    prof[1] = 0;
    prof[2] = 0;
    prof_iter = 0;
    prof_ticks = 0;
    prof_restart++;
    prof_i = 0;

    /* камера: спавн героя — в коридоре CAMR_MIN..MAX */
    {
        int cy = (int)hero_y - (int)(CAMR_MIN_ROW * 8u);
        if (cy < 0) cy = 0;
        cam_y = (unsigned int)cy;
        if (cam_y > CAM_MAX) cam_y = CAM_MAX;
    }
    beam_set_cam(cam_y);

    need_fade = 1;
}

static void hero_logic(void)
{
    unsigned char jump_held, down_held, grounded = 0;

    /* X: шаг начат — доводим до цели по 4px; иначе стартуем с клетки.
     * Бокс проверяется целиком — допустимо в любой вертикальной фазе. */
    if (mv_x) {
        if (hero_x < hero_tx) hero_x += HERO_X_STEP;
        else if (hero_x > hero_tx) hero_x -= HERO_X_STEP;
        if (hero_x == hero_tx) mv_x = 0;
    } else if ((hero_x & 15u) == 0u) {
        signed char dir = 0;

        if (kbd_is_down(KBD_KEY_LEFT)) dir = -1;
        else if (kbd_is_down(KBD_KEY_RIGHT)) dir = 1;
        if (dir) {
            int nx = (int)hero_x + (int)dir * 16;
            hero_dir = (unsigned char)(dir > 0);
            if (nx >= 0 && !hero_box_solid(nx, (int)hero_y)) {
                mv_x = 1;
                hero_tx = (unsigned int)nx;
            }
        }
    }

    /* Y: шаг начат — доводим до цели (подъём/спуск/прыжок). */
    if (mv_y) {
        if (hero_y < hero_ty) hero_y += HERO_Y_STEP;
        else if (hero_y > hero_ty) hero_y -= HERO_Y_STEP;
        if (hero_y == hero_ty) {
            mv_y = 0;
            if (rising && jump_left >= 16u)
                jump_left = (unsigned char)(jump_left - 16u);
            if (!rising) grounded = 1;    /* сели на клетку */
        }
        hero_enter_cell();
        return;
    }
    if ((hero_y & 15u) != 0u) return;     /* середина шага по Y */

    /* Решение о следующем шаге по Y — только с клетки. */
    jump_held = (unsigned char)(kbd_is_down((unsigned char)' ') ||
                                kbd_shift_state);
    if (hero_vstate == 2) {               /* апекс: отпускание — сразу вниз */
        if (!jump_held || --hang_left == 0) hero_vstate = 0;
    } else if (hero_vstate == 1) {        /* подъём прыжка */
        if (!jump_held)
            hero_vstate = 0;
        else if (jump_left == 0u ||
                 hero_box_solid((int)hero_x, (int)hero_y - 16)) {
            hero_vstate = 2;              /* запас кончился/потолок */
            hang_left = HANG_FRAMES;
        } else {
            mv_y = 1;
            rising = 1;
            hero_ty = hero_y - 16u;
        }
    } else if (kbd_is_down(KBD_KEY_UP) &&
               !hero_box_solid((int)hero_x, (int)hero_y - 16)) {
        mv_y = 1;                         /* ↑ — подъём по шахте */
        rising = 0;
        hero_ty = hero_y - 16u;
    } else if (jump_held &&
               hero_box_solid((int)hero_x, (int)hero_y + 16)) {
        hero_vstate = 1;                  /* опора под боксом — прыжок */
        jump_left = JUMP_PX;
    } else if (!hero_box_solid((int)hero_x, (int)hero_y + 16)) {
        mv_y = 1;                         /* гравитация */
        rising = 0;
        hero_ty = hero_y + 16u;
    } else {
        grounded = 1;                     /* стоим на твёрдой клетке */
    }

    /* Секреты и «?»-кубики открываются ТОЛЬКО клавишей ↓ и только стоя на
     * клетке (как в putup: обработчик клавиши func_player_move_d, а не
     * следствие приземления). Учитывается кромка нажатия — удержание ↓ не
     * повторяется, отпустить и нажать снова = следующее превращение. */
    down_held = (unsigned char)kbd_is_down(KBD_KEY_DOWN);
    if (grounded && down_held && !down_prev) hero_press_down();
    down_prev = down_held;

    hero_enter_cell();
}

/* Кадр героя: субшаг X = (hero_x>>2)&1 — фаза ходьбы (var_page_flip
 * putup) и вариант дескриптора со сдвигом 4px (столбец VRAM = 8px,
 * tools/gen_assets.py: v0 на x = 0/8, v1 на x = 4/12).
 * Стойка — 2 (вправо) / 5 (влево). */
static void hero_render_commit(void)
{
    unsigned char sub = (unsigned char)((hero_x >> 2) & 1u);
    unsigned char f;

    if (mv_x)
        f = hero_dir ? (unsigned char)(HF_WALK_R0 + sub)
                     : (unsigned char)(HF_WALK_L0 + sub);
    else
        f = hero_dir ? HF_STAND_R : HF_STAND_L;

    hero_pat.desc = hero_frames[f][sub];
    beam_show(HERO_ID, &hero_pat);
    beam_move(HERO_ID, (unsigned char)(hero_x & 0xF8u), hero_y);
}

/* Патруль врагов — только логика (клеточный шаг, коллизии); вид и
 * отображаемую позицию выставляет enemies_render_commit. */
static void enemies_logic(void)
{
    unsigned char i;
    /* Враги — вдвое медленнее героя: шаг тот же 4px, но через кадр
     * (ENEMY_STEP_MASK) — в оригинале герой проходит две клетки за тик
     * против одной у врага. */
    unsigned char move_now = (unsigned char)((anim_tick & ENEMY_STEP_MASK) == 0u);

    for (i = 0; i < NUM_ENEMIES; i++) {
        int rel = (int)enemy_y[i] - (int)cam_y;

        /* патруль по строке: 4px за свой кадр, разворот у стены/
         * фрукта/края */
        if (move_now) {
            int nx = (int)enemy_x[i] + (int)enemy_dir[i] * ENEMY_X_STEP;
            unsigned char probe_col, row = (unsigned char)(enemy_y[i] >> 4);
            if (nx < 0 || nx > 240) {
                enemy_dir[i] = (signed char)-enemy_dir[i];
            } else {
                probe_col = (unsigned char)((enemy_dir[i] > 0 ? nx + 15 : nx) >> 4);
                if (!cell_enemy_free(probe_col, row))
                    enemy_dir[i] = (signed char)-enemy_dir[i];
                else
                    enemy_x[i] = (unsigned int)nx;
            }
        }

        /* касание героя — рестарт уровня; вне окна 256px инстанс — алиас
         * кольца и не рисуется, поэтому и не кусается */
        if (rel < -16 || rel > 256) continue;
        {
            int dx = (int)hero_x - (int)enemy_x[i];
            int dy = (int)hero_y - (int)enemy_y[i];
            if (dx < 0) dx = -dx;
            if (dy < 0) dy = -dy;
            if (dx < 12 && dy < 12) { restart_level(); return; }
        }
    }
}

/* Видимость, кадр и позиция врагов. Позиция — та же, что у логики
 * (enemy_x), с шагом 4px: вариант дескриптора и фаза берутся по ней. */
static void enemies_render_commit(void)
{
    unsigned char i;

    for (i = 0; i < NUM_ENEMIES; i++) {
        unsigned int id = ENEMY_ID0 + i;
        int rel = (int)enemy_y[i] - (int)cam_y;
        unsigned char ph, sh;

        /* окно 256px: вне его — алиас кольца, инстанс скрываем */
        if (rel < -16 || rel > 256) {
            if (enemy_shown[i]) { beam_hide((unsigned char)id); enemy_shown[i] = 0; }
            continue;
        }
        /* ходок/ворона: фаза = направление (state1/state2 putup),
         * вертолёт: две фазы ротора; вариант дескриптора — по сдвигу */
        ph = (unsigned char)(level_enemy_kinds[i] == ENEMY_HELI
                             ? (unsigned char)((anim_tick >> 2) & 1u)
                             : (unsigned char)(enemy_dir[i] > 0 ? 0 : 1));
        sh = (unsigned char)((enemy_x[i] >> 2) & 1u);
        enemy_pat[i].desc = enemy_frames[level_enemy_kinds[i]][ph][sh];
        beam_show((unsigned char)id, &enemy_pat[i]);
        beam_move((unsigned char)id, (unsigned char)(enemy_x[i] & 0xF8u),
                  enemy_y[i]);
        enemy_shown[i] = 1;
    }
}

static void camera_logic(void)
{
    int rel = ((int)hero_y - (int)cam_y) >> 3;  /* полоса героя на экране */
    unsigned int ny = cam_y;

    if (rel > (int)CAMR_MAX_ROW && cam_y < CAM_MAX) ny = cam_y + 8u;
    else if (rel < (int)CAMR_MIN_ROW && cam_y > 0)  ny = cam_y - 8u;
    if (ny != cam_y) {
        cam_y = ny;
        beam_set_cam(cam_y);            /* шаг 8px, flush на VBlank */
    }
}

static void exit_blink(void)
{
    if (!exit_open) return;
    if (++exit_timer < 8u) return;      /* смена фазы каждые 8 кадров */
    exit_timer = 0;
    exit_phase ^= 1u;
    beam_bg_put(level_exit[1], level_exit[0],
                (unsigned char)(exit_phase ? CODE_EXIT_LT : CODE_EXIT_DK));
}

static void game_logic(void)
{
    anim_tick++;
    hero_logic();
    enemies_logic();
    camera_logic();
    exit_blink();
}

int main(void)
{
    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_black_palette();
    frame_handler = on_frame;

    restart_level();

    for (;;) {
        prof_top();                        /* prof_iter: итераций цикла  */
        if (kbd_read() == KBD_KEY_ESC) {
            gfx_fade_out(1);
            break;
        }

        /* Логика и отрисовка — каждый кадр: шаг 4px виден только при
         * темпе 50 Гц (beam_render в конце итерации выравнивает цикл). */
        prof_ticks++;
        game_logic();                      /* только мутаторы beam_* (ТФ-4) */

        hero_render_commit();              /* отображение: +4px к цели */
        enemies_render_commit();
        prof_mark();                       /* prof[0]: верх цикла        */

        beam_update();
        prof_mark();                       /* prof[1]: планировщик       */

        beam_render();    /* блокирует до конца кадра: темп 50 Гц (Г3) */
        prof_mark();                       /* prof[2]: исполнение плана   */
        ovb_seen = beam_overbudget();       /* для часов отладчика, не HUD */

        if (need_fade) {  /* первое окно уже нарисовано — показываем */
            need_fade = 0;
            gfx_fade_in(asset_palette, 1);
        }
    }
    return 0;
}
