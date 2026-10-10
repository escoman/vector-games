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
 * ФОН РИСУЕТСЯ РАЗНОСТЬЮ. Небо — индекс 0 палитры, поэтому тайл целиком из
 * неба = 32 нуля и в VRAM не пишется вообще; совпавшая ячейка тайлкарты —
 * пропуск; плоскость, пустая и в старой, и в новой колонке — пропуск. Марио
 * стирается слепком VRAM (mario_undraw), а не перерисовкой двух блоков.
 *
 * Управление: ← / → — ходьба, ПРОБЕЛ — прыжок (только с опоры). Коллизии с
 * уровнем (см. tiles2.png): земля/трубы/кирпич — стены (не пройти), коробки и
 * верх опор — one-way платформы (запрыгнуть можно, пройти насквозь — тоже).
 */

#include "v06.h"

#include "src/level.inc"      /* level_palette, tileset, tilemap, LEVEL_* */
#include "src/mario.inc"      /* mario_<frame>_<r|l>                     */

/* Горячие функции — см. mario.asm. */
extern void render_window(unsigned int cam, unsigned int old_cam,
                          unsigned char blk0, unsigned char nblk) __z88dk_callee;
extern void mario_draw(unsigned char x, unsigned char y,
                       const unsigned char *spr) __z88dk_callee;
extern void mario_undraw(void) __z88dk_callee;

#define CAM_NO_REF   0xFFFFu    /* в VRAM пусто (первый экран) */

/* ----------------------------- ГЕОМЕТРИЯ ------------------------------- */
/* Экран 256x256 = 32x32 тайла; тайл 8 px. Мир шире экрана (LEVEL_COLS тайлов),
 * камера cam (в тайлах) листает его шагом 8 px. Строка тайла cy -> экранный
 * верх y = cy*8 (полоса уровня в tiles.png ложится на экран 1:1). */

#define TILE_PX      8
#define VIEW_BLOCKS  32                 /* 256 px / 8 = экран по горизонтали */
#define SPR_W        16                 /* спрайт Марио 16x16 = 2x2 тайла    */
#define SPR_H        16

#define GRAV         1                  /* прирост вертикальной скорости/кадр */
#define FALL_MAX     8                  /* предел скорости падения            */
#define JUMP_V0      (-11)              /* старт прыжка: ~в 3 раза выше изначальной (~55 px) */

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

static unsigned int  wblk;       /* мировой тайловый столбец левого края Марио */
static unsigned int  cam;        /* мировой столбец у левого края экрана       */
static unsigned char mblk;       /* экран столбец Марио = wblk - cam           */
static int           my;         /* верх Марио по Y (пиксели, 0..240)          */
static int           vy;         /* вертикальная скорость, + = вниз             */
static unsigned char facing;     /* 0 = вправо, 1 = влево                      */
static unsigned char grounded;   /* стоит на опоре (можно прыгать)             */
static unsigned char walkphase;  /* 0..2 кадр ходьбы                            */
static unsigned char vy_hold;    /* ↓ удерживается                             */
static unsigned char moving;     /* идёт горизонтальное движение этот кадр      */
static unsigned char space_prev; /* ПРОБЕЛ в прошлом кадре — фронт для прыжка  */

/* Где Марио нарисован в последний раз (его пиксели сейчас в VRAM).
 * Пока совпадает с текущим состоянием и камера не двинулась — кадр целиком
 * пропускаем: в VRAM уже лежит готовое изображение. */
static unsigned char drawn_blk;
static unsigned char drawn_y;
static const unsigned char *drawn_spr;

/* Твёрдость ячейки мира (col,row): маска COLL_* свойства тайла (вариант C).
 * COLL_PLAT (1) — one-way опора, COLL_WALL (2) — непроходимо, 3 — и то, и др.
 * 0 — пусто. Берём тайл из tilemap (колонка-мажор) и его свойство tile_solid. */
static unsigned char solid_at(int col, int row)
{
    if (col < 0 || row < 0 || col >= (int)LEVEL_COLS || row >= (int)LEVEL_ROWS)
        return 0;
    return tile_solid[tilemap[(unsigned int)col * LEVEL_ROWS + (unsigned int)row]];
}

/* Старт прыжка — только с опоры. */
static void jump_start(void)
{
    if (grounded) {
        vy = JUMP_V0;
        grounded = 0;
    }
}

/* Вернуть указатель на нужный спрайт текущего состояния. */
static const unsigned char *pick_sprite(void)
{
    if (!grounded)
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
    const unsigned char *spr;

    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_black_palette();
    gfx_clear(0);
    gfx_set_bmp_palette(level_palette);

    /* Старт: Марио у левого края на земле (верх ряда 30 = y240, ноги там). */
    wblk = 4;
    cam = 0;
    mblk = (unsigned char)wblk;
    my = 224;
    vy = 0;
    grounded = 1;
    facing = 0;
    walkphase = 0;
    frame = 0;

    render_window(cam, CAM_NO_REF, 0, VIEW_BLOCKS);
    spr = pick_sprite();
    mario_draw((unsigned char)(mblk * 8), (unsigned char)my, spr);
    drawn_blk = mblk;
    drawn_y = (unsigned char)my;
    drawn_spr = spr;

    for (;;) {
        unsigned int  old_cam;

        gfx_next_frame();

        /* ---- ввод: держим несколько клавиш сразу (стрелка + пробел).
         * kbd_scan() обновляет снимок матрицы; kbd_is_down() проверяет по нему
         * каждую клавишу отдельно. Иначе kbd_read() отдаёт ПЕРВУЮ нажатую, а
         * стрелки живут в строке 0 и маскировали пробел из строки 7. ---- */
        kbd_scan();
        dir = 0;
        vy_hold = 0;
        if (kbd_is_down(KBD_KEY_LEFT))  { dir = 1; facing = 1; }
        if (kbd_is_down(KBD_KEY_RIGHT)) { dir = 2; facing = 0; }
        if (kbd_is_down(KBD_KEY_DOWN))  { vy_hold = 1; }
        {
            /* Прыжок по фронту ПРОБЕЛА: удержание не должно авто-подпрыгивать
             * при приземлении. */
            unsigned char sp = kbd_is_down(32);
            if (sp && !space_prev) jump_start();
            space_prev = sp;
        }

        /* ---- горизонтальное движение (шаг 8 px, с проверкой стен) ---- */
        moving = 0;
        old_cam = cam;

        if (dir && !vy_hold) {
            if (++frame >= MOVE_DELAY) {
                int nb, edge, d = (dir == 2) ? 1 : -1;
                int r0, r1;
                frame = 0;
                moving = 1;
                nb = (int)wblk + d;
                if (nb < 0) nb = 0;
                if (nb > (int)LEVEL_COLS - 2) nb = (int)LEVEL_COLS - 2;
                edge = (d > 0) ? nb + 1 : nb;      /* вводимый столбец */
                r0 = my / TILE_PX;
                r1 = (my + SPR_H - 1) / TILE_PX;
                /* в стену (бит COLL_WALL) не входим; one-way платформа не мешает */
                if (!(solid_at(edge, r0) & COLL_WALL) &&
                    !(solid_at(edge, r1) & COLL_WALL))
                    wblk = (unsigned int)nb;
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

        /* ---- вертикаль: гравитация + коллизии (каждый кадр) ---- */
        {
            int nmy;
            vy += GRAV;
            if (vy > FALL_MAX) vy = FALL_MAX;
            nmy = my + vy;
            grounded = 0;
            if (vy >= 0) {
                /* падаем: тайл под нижним пикселем; опора (платформа или
                 * стена) останавливает, ставим ноги на её верх */
                int brow = (nmy + SPR_H - 1) / TILE_PX;
                if (solid_at((int)wblk, brow) || solid_at((int)wblk + 1, brow)) {
                    nmy = brow * TILE_PX - SPR_H;
                    vy = 0;
                    grounded = 1;
                }
            } else {
                /* поднимаемся: головой только о непроходимую стену (бит WALL) */
                int trow = nmy / TILE_PX;
                if (solid_at((int)wblk, trow) & COLL_WALL ||
                    solid_at((int)wblk + 1, trow) & COLL_WALL) {
                    nmy = (trow + 1) * TILE_PX;
                    vy = 0;
                }
            }
            my = nmy;
            if (my < 0) { my = 0; if (vy < 0) vy = 0; }
            if (my > 240) {                 /* утонул в яме — респавн в начале */
                wblk = 4; cam = 0; mblk = 4;
                my = 224; vy = 0; grounded = 1;
            }
        }

        /* ---- отрисовка ---- */
        spr = pick_sprite();
        if (cam != old_cam) {
            /* Скролл: сначала стереть Марио (иначе его пиксели уедут в
             * «фон» и останутся в VRAM), затем дорисовать разность колонок.
             * pair_top валиден только для шага +-1, больше — полный редрав. */
            mario_undraw();
            if (cam == old_cam + 1 || old_cam == cam + 1)
                render_window(cam, old_cam, 0, VIEW_BLOCKS);
            else
                render_window(cam, CAM_NO_REF, 0, VIEW_BLOCKS);
        } else if (mblk == drawn_blk && my == drawn_y && spr == drawn_spr) {
            continue;                   /* на экране ничего не изменилось */
        } else {
            mario_undraw();
        }
        mario_draw((unsigned char)(mblk * 8), (unsigned char)my, spr);
        drawn_blk = mblk;
        drawn_y = (unsigned char)my;
        drawn_spr = spr;
    }

    return 0;
}
