/*
 * main.c — putup-beam: демо beam-подсистемы (lib/gfx/beam.c) на ассетах
 * игры putup. Уровень 16×32 клетки (512px = ровно 2 кольца VRAM) с
 * аппаратным вертикальным скроллингом, плавной анимацией героя (маска,
 * субпиксель 4px по X / 2px по Y) и двумя патрулирующими врагами.
 *
 * Механика (по плану демо, без HUD/счёта/времени/Hurry Up/огня/музыки):
 *   - собрать все ключи {07,0A,0B} -> выход (клетка 23) открывается и
 *     мигает фазами 22/23 (как data_flip_tab putup);
 *   - войти в открытый выход -> рестарт уровня;
 *   - касание врага -> рестарт уровня;
 *   - ESC -> fade-out и выход.
 *
 * Контракт цикла (BEAM_TZ §2.2, ТФ-1..7): вся видимая графика — через
 * beam_*; единственный писатель VRAM в кадре — beam_render; кадровый ISR —
 * timer_start() + kbd_scan_now() (последний ещё и сбрасывает gfx_scroll_row
 * в порт 03h на VBlank — flush регистра скролла beam_set_cam, память:
 * port 03h shared scroll+kbd).
 *
 * Герой: клеточное движение как в putup — гравитация тянет вниз
 * (↓-клетка не тверда), ←/→ шагают на клетку, ↑ поднимает по шахте
 * (удобство демо); прыжок — action-клавиша (ПРОБЕЛ/СС) как
 * func_gamestate_catch оригинала: подъём на 2 клетки, зависание на
 * апексе, отпускание — сразу падение; диспетчер клавиш работает во
 * всех фазах полёта (управление в воздухе). «?»-ящики (код 04h) твёрды
 * (глифы 7Eh..82h >= 77h в оригинале). Враги: пара кадров state1/state2
 * = направление вправо/влево (тайлы tg[20]/tg[19] оригинала).
 * easing: Y попиксельно (2px/кадр), X субшагами 4px через build-time
 * варианты дескрипторов (v0/v1, ТЗ §3.3). Кадр ходьбы привязан к субшагу
 * (аналог var_page_flip): idx = 0/1 шаг вправо, 2 стойка вправо, 3/4 шаг
 * влево, 5 стойка влево (формула putup idx = work_const + 3*move_dir − 1).
 */

#include "v06.h"
#include "assets.inc"
#include "level.inc"

/* --- коды клеток (level.inc / gen_level.py) --- */
#define CODE_EMPTY   1u
#define CODE_EXIT_LT 22u   /* светлая фаза выхода (bg_tiles[22]) */
#define CODE_EXIT_DK 23u   /* тёмная фаза; до открытия — стена   */

#define KEY_CODE(c)  ((c) == 7u || (c) == 10u || (c) == 11u)
/* твёрдость putup: глифы тайла >= 77h; «?»-ящик (04h) — глифы 7Eh..82h */
#define SOLID_CODE(c) ((c) == 2u || (c) == 4u || (c) == 5u || (c) == 8u)

/* прыжок: подъём 2 клетки (4 глиф-строки оригинала), зависание апекса */
#define JUMP_PX       32u
#define HANG_FRAMES   18u   /* 3 тика оригинала по ~6 кадров */

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

/* --- скорости easing --- */
#define HERO_X_STEP   4u   /* px/кадр по X (субшаг вариантов)  */
#define HERO_Y_STEP   2u   /* px/кадр по Y (пиксельная точность) */
#define ENEMY_X_STEP  4u

#define HERO_ID       0u
#define ENEMY_ID0     1u

/* экземпляр героя + 2 врага */
#define NUM_ENEMIES   2u

/* --- состояние игры --- */
static unsigned char game_map[LEVEL_ROWS * LEVEL_COLS]; /* зеркало cellmap beam */
static unsigned char keys_left;
static unsigned char exit_open;
static unsigned char exit_phase;      /* 0/1 — мигание 22/23 */
static unsigned char exit_timer;
static unsigned int  cam_y;

static unsigned int  hero_x, hero_y;  /* мир, px, верхний левый угол 16x16 */
static unsigned int  hero_tx, hero_ty;
static unsigned char mv_x, mv_y;      /* easing по осям независимый (полёт) */
static unsigned char rising;          /* mv_y вверх — фаза прыжка */
static unsigned char hero_vstate;     /* 0 земля/падение, 1 подъём, 2 апекс */
static unsigned char jump_left;       /* px подъёма осталось */
static unsigned char hang_left;       /* кадров зависания на апексе */
static unsigned char hero_dir;        /* 1 вправо, 0 влево (стойка/кадры) */
extern unsigned char kbd_shift_state; /* СС из kbdscan.asm (action-клавиша) */

static unsigned int  enemy_x[NUM_ENEMIES], enemy_y[NUM_ENEMIES];
static signed char   enemy_dir[NUM_ENEMIES];
static unsigned char enemy_shown[NUM_ENEMIES];

static beam_pat_t hero_pat;           /* attr: mask-путь, приоритет 2 */
static beam_pat_t enemy_pat[NUM_ENEMIES]; /* attr: плоский, приоритет 1 */

static unsigned char need_fade;       /* fade_in после render рестарта */
static unsigned char ovb_seen;        /* beam_overbudget — для отладчика */

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
    if (c == CODE_EXIT_DK || c == CODE_EXIT_LT)
        return (unsigned char)(!exit_open);   /* выход тверд до открытия */
    return (unsigned char)(SOLID_CODE(c) ? 1 : 0);
}

/* Клетка под героем: подбор ключа, вход в открытый выход. */
static void hero_enter_cell(void)
{
    unsigned char cx = (unsigned char)(hero_x >> 4);
    unsigned char cy = (unsigned char)(hero_y >> 4);
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

    hero_x = (unsigned int)level_hero_spawn[1] * 16u;
    hero_y = (unsigned int)level_hero_spawn[0] * 16u;
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
        enemy_pat[i].desc = enemy_frames[level_enemy_state - 1][0];
    }

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
    unsigned char cx = (unsigned char)(hero_x >> 4);
    unsigned char cy = (unsigned char)(hero_y >> 4);
    unsigned char jump_held;

    /* X: шаг на клетку; допустим в любой вертикальной фазе — в оригинале
     * диспетчер клавиш работает и в catch/evade (управление в полёте). */
    if (mv_x) {
        if (hero_x < hero_tx) hero_x += HERO_X_STEP;
        else if (hero_x > hero_tx) hero_x -= HERO_X_STEP;
        if (hero_x == hero_tx) { mv_x = 0; hero_enter_cell(); }
    } else if ((hero_x & 15u) == 0) {
        if (kbd_is_down(KBD_KEY_LEFT) && cx > 0 &&
            !cell_solid((unsigned char)(cx - 1), cy)) {
            mv_x = 1;
            hero_dir = 0;
            hero_tx = hero_x - 16u;
        } else if (kbd_is_down(KBD_KEY_RIGHT) && cx + 1 < LEVEL_COLS &&
                   !cell_solid((unsigned char)(cx + 1), cy)) {
            mv_x = 1;
            hero_dir = 1;
            hero_tx = hero_x + 16u;
        }
    }

    /* Y: подъём/зависание/падение/подъём по шахте. */
    if (mv_y) {
        if (hero_y < hero_ty) hero_y += HERO_Y_STEP;
        else if (hero_y > hero_ty) hero_y -= HERO_Y_STEP;
        if (hero_y == hero_ty) {
            mv_y = 0;
            if (rising && jump_left >= 16u) jump_left -= 16u;
            hero_enter_cell();
        }
        return;
    }
    if ((hero_y & 15u) != 0) return;

    jump_held = (unsigned char)(kbd_is_down((unsigned char)' ') ||
                                kbd_shift_state);
    if (hero_vstate == 2) {               /* апекс: отпускание — сразу вниз */
        if (!jump_held || --hang_left == 0) hero_vstate = 0;
        return;
    }
    if (hero_vstate == 1) {               /* подъём прыжка */
        if (!jump_held) { hero_vstate = 0; return; }
        if (jump_left == 0) {
            hero_vstate = 2;
            hang_left = HANG_FRAMES;
            return;
        }
        if (cell_solid(cx, (unsigned char)(cy - 1))) { hero_vstate = 0; return; }
        mv_y = 1;
        rising = 1;
        hero_ty = hero_y - 16u;
        return;
    }
    /* земля: ↑ — шахта (удобство демо); прыжок с опоры; иначе гравитация */
    if (kbd_is_down(KBD_KEY_UP) && !cell_solid(cx, (unsigned char)(cy - 1))) {
        mv_y = 1;
        rising = 0;
        hero_ty = hero_y - 16u;
    } else if (jump_held && cell_solid(cx, (unsigned char)(cy + 1))) {
        hero_vstate = 1;
        jump_left = JUMP_PX;
    } else if (!cell_solid(cx, (unsigned char)(cy + 1))) {
        mv_y = 1;
        rising = 0;
        hero_ty = hero_y + 16u;
    }
}

/* Кадр героя: субшаг X = (hero_x>>2)&1 даёт фазу ходьбы (var_page_flip);
 * вариант v1 = сдвиг 4px. Стойка — 2 (вправо) / 5 (влево). */
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

static void enemies_logic(void)
{
    unsigned char i;

    for (i = 0; i < NUM_ENEMIES; i++) {
        unsigned int id = ENEMY_ID0 + i;
        int rel = (int)enemy_y[i] - (int)cam_y;

        /* патруль по строке: 4px/кадр, разворот у стены/края */
        {
            int nx = (int)enemy_x[i] + (int)enemy_dir[i] * ENEMY_X_STEP;
            unsigned char probe_col, row = (unsigned char)(enemy_y[i] >> 4);
            if (nx < 0 || nx > 240) {
                enemy_dir[i] = (signed char)-enemy_dir[i];
            } else {
                probe_col = (unsigned char)((enemy_dir[i] > 0 ? nx + 15 : nx) >> 4);
                if (cell_solid(probe_col, row))
                    enemy_dir[i] = (signed char)-enemy_dir[i];
                else
                    enemy_x[i] = (unsigned int)nx;
            }
        }

        /* окно 256px: вне его — алиас кольца, инстанс скрываем */
        if (rel < -16 || rel > 256) {
            if (enemy_shown[i]) { beam_hide((unsigned char)id); enemy_shown[i] = 0; }
        } else {
            unsigned char sub = (unsigned char)((enemy_x[i] >> 2) & 1u);
            /* state1/state2 оригинала = направление: tg[20] вправо,
             * tg[19] влево */
            enemy_pat[i].desc = enemy_frames[enemy_dir[i] > 0 ? 0 : 1][sub];
            beam_show((unsigned char)id, &enemy_pat[i]);
            beam_move((unsigned char)id,
                      (unsigned char)(enemy_x[i] & 0xF8u), enemy_y[i]);
            enemy_shown[i] = 1;
            /* касание героя — рестарт уровня */
            {
                int dx = (int)hero_x - (int)enemy_x[i];
                int dy = (int)hero_y - (int)enemy_y[i];
                if (dx < 0) dx = -dx;
                if (dy < 0) dy = -dy;
                if (dx < 12 && dy < 12) { restart_level(); return; }
            }
        }
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
    hero_logic();
    enemies_logic();
    camera_logic();
    exit_blink();
    hero_render_commit();
    ovb_seen = beam_overbudget();       /* для часов отладчика, не HUD */
}

int main(void)
{
    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_black_palette();
    frame_handler = on_frame;

    restart_level();

    for (;;) {
        v06_wait_frame();

        if (kbd_read() == KBD_KEY_ESC) {
            gfx_fade_out(1);
            break;
        }

        game_logic();     /* только мутаторы beam_* (ТФ-4) */
        beam_update();
        beam_render();    /* блокирует до конца кадра: темп 50 Гц (Г3) */

        if (need_fade) {  /* первое окно уже нарисовано — показываем */
            need_fade = 0;
            gfx_fade_in(asset_palette, 1);
        }
    }
    return 0;
}
