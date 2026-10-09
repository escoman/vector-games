/*
 * main.c — демка Mario 16-цвет для Вектора-06Ц.
 *
 * Марио ходит по первому уровню Super Mario Bros; экран скроллится шагом 8 px
 * (один столбец VRAM). Цель — посмотреть, как быстро перемещается фон и как
 * быстро рисуется 16-цветный спрайт с маской.
 *
 * Горячий путь (зарисовка окна из тайлкарты + композиция спрайта) — в
 * mario.asm (8080). Здесь: инициализация, состояние Марио, ввод, камера, цикл.
 *
 * Управление: ← / → — ходьба, ↓ — пригнуться, ПРОБЕЛ — прыжок.
 */

#include "v06.h"

#include "src/level.inc"      /* level_palette, tileset, tilemap, LEVEL_* */
#include "src/mario.inc"      /* mario_<frame>_<r|l>                     */

/* Горячие функции — см. mario.asm. */
extern void render_window(unsigned int cam, unsigned char blk0,
                          unsigned char nblk) __z88dk_callee;
extern void mario_draw(unsigned char x, unsigned char y,
                       const unsigned char *spr) __z88dk_callee;

/* ----------------------------- ГЕОМЕТРИЯ ------------------------------- */

#define VIEW_BLOCKS  32                 /* 256 px / 8 = экран по горизонтали */
#define GROUND_Y     224                /* строка поверхности земли (ноги)  */
#define STAND_TOP    (GROUND_Y - 16)    /* верх Марио стоя = 208             */
#define JUMP_APEX    120                /* верх прыжка (верх спрайта)        */

#define CAM_MIN_BLK  10                 /* держим Марио в окне [10..20]      */
#define CAM_MAX_BLK  20
#define MAX_CAM      (LEVEL_COLS - VIEW_BLOCKS)

#define MOVE_DELAY   2                  /* кадров на один шаг (8 px)         */

/* Кадры анимации: [направление][0..2]. */
static const unsigned char * const walkR[3] =
    { mario_walk0_r, mario_walk1_r, mario_walk2_r };
static const unsigned char * const walkL[3] =
    { mario_walk0_l, mario_walk1_l, mario_walk2_l };

/* ------------------------------ СОСТОЯНИЕ ------------------------------ */

static unsigned int  wblk;       /* мировой тайловый столбец Марио (левый)  */
static unsigned int  cam;        /* мировой столбец у левого края экрана     */
static unsigned char mblk;       /* экран столбец Марио = wblk - cam         */
static int           my;         /* верх Марио по Y (пиксели)               */
static int           vy;         /* вертикальная скорость, + = вниз          */
static unsigned char facing;     /* 0 = вправо, 1 = влево                    */
static unsigned char jumping;    /* в воздухе                                */
static unsigned char walkphase;  /* 0..2 кадр ходьбы                          */
static unsigned char vy_hold;    /* ↓ удерживается (пригнуться)             */
static unsigned char moving;     /* идёт горизонтальное движение этот кадр   */

/* Старт прыжка. */
static void jump_start(void)
{
    if (!jumping) {
        jumping = 1;
        vy = -6;
    }
}

/* Вернуть указатель на нужный спрайт текущего состояния. */
static const unsigned char *pick_sprite(void)
{
    if (jumping)
        return facing ? mario_jump_l : mario_jump_r;
    if (vy_hold)
        return facing ? mario_duck_l : mario_duck_r;
    if (moving)
        return (facing ? walkL : walkR)[walkphase];
    return facing ? mario_stand_l : mario_stand_r;
}

int main(void)
{
    unsigned char frame;
    unsigned char dir;

    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_black_palette();
    gfx_clear(0);
    gfx_set_bmp_palette(level_palette);

    /* Старт: Марио у левого края, камера 0. */
    wblk = 4;
    cam = 0;
    mblk = (unsigned char)wblk;
    my = STAND_TOP;
    vy = 0;
    jumping = 0;
    facing = 0;
    walkphase = 0;
    frame = 0;

    render_window(cam, 0, VIEW_BLOCKS);

    for (;;) {
        unsigned int  old_cam;
        unsigned char old_blk;
        unsigned char key;

        gfx_next_frame();

        /* ---- ввод ---- */
        key = kbd_scan();
        dir = 0;
        vy_hold = 0;
        if (key == KBD_KEY_LEFT)  { dir = 1; facing = 1; }
        if (key == KBD_KEY_RIGHT) { dir = 2; facing = 0; }
        if (key == KBD_KEY_DOWN)  { vy_hold = 1; }
        if (key == 32)            { jump_start(); }

        /* ---- горизонтальное движение (шаг 8 px, не чаще раза в MOVE_DELAY) ---- */
        moving = 0;
        old_cam = cam;
        old_blk = mblk;

        if (dir && !vy_hold) {
            if (++frame >= MOVE_DELAY) {
                frame = 0;
                moving = 1;
                if (dir == 2) {                 /* вправо */
                    if (wblk < MAX_CAM + VIEW_BLOCKS - 2) wblk++;
                } else {                         /* влево */
                    if (wblk > 0) wblk--;
                }
                walkphase = (walkphase + 1) % 3;
            }
        }

        /* ---- камера: держим Марио в окне [CAM_MIN..CAM_MAX] ---- */
        {
            unsigned int rel = wblk - cam;
            if (rel > CAM_MAX_BLK && cam < MAX_CAM) {
                cam = wblk - CAM_MAX_BLK;
                if (cam > MAX_CAM) cam = MAX_CAM;
            } else if (rel < CAM_MIN_BLK) {
                /* Не даём cam уйти в минус (wblk < CAM_MIN_BLK на старте). */
                cam = (wblk > CAM_MIN_BLK) ? (wblk - CAM_MIN_BLK) : 0;
            }
            mblk = (unsigned char)(wblk - cam);
        }

        /* ---- вертикаль: прыжок/гравитация (каждый кадр) ---- */
        if (jumping) {
            my += vy;
            vy += 1;                            /* гравитация */
            if (my <= JUMP_APEX) { my = JUMP_APEX; if (vy < 0) vy = 0; }
            if (my >= STAND_TOP) { my = STAND_TOP; vy = 0; jumping = 0; }
        }

        /* ---- отрисовка ---- */
        if (cam != old_cam) {
            /* Скролл: перерисовать весь экран из тайлкарты. */
            render_window(cam, 0, VIEW_BLOCKS);
        } else {
            /* Без скролла: стереть Марио со старого места (2 блока) и,
             * если сменился экран столбец, со старого тоже. */
            render_window(cam, old_blk, 2);
            if (mblk != old_blk)
                render_window(cam, mblk, 2);
        }
        mario_draw((unsigned char)(mblk * 8), (unsigned char)my, pick_sprite());
    }

    return 0;
}
