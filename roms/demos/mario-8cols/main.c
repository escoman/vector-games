/*
 * main.c — демка Mario 8-цвет (сплит по плоскостям) для Вектора-06Ц.
 *
 * Марио ходит по первому уровню Super Mario Bros; экран скроллится шагом 8 px
 * (один столбец VRAM) по обеим осям. Цель — посмотреть, как быстро перемещается
 * фон и как быстро рисуется спрайт, разнесённый с фоном по битовым плоскостям.
 *
 * Горячий путь (зарисовка окна из тайлкарты + композиция спрайта) — в
 * mario.asm (8080). Здесь: инициализация, состояние Марио, ввод, камера, цикл.
 *
 * РАЗНЕСЕНИЕ ПО ПЛОСКОСТЯМ. Индекс палитры = bg*4 + ch. ФОН — старшие 2 бита
 * (плоскости веса 8/4), ПЕРСОНАЖ — младшие 2 бита (плоскости веса 2/1). Палитра
 * разложена так, что спрайт побеждает фон без маскирования (ch=0 -> цвет фона,
 * ch=1..3 -> цвет спрайта), поэтому спрайт — прямая запись в свои плоскости, а
 * стирание = обнуление тех же плоскостей (фон под Марио не перерисовывается).
 *
 * ФОН РИСУЕТСЯ РАЗНОСТЬЮ. Небо — индекс 0 палитры, поэтому тайл целиком из
 * неба = 16 нуля и в VRAM не пишется вообще; совпавшая ячейка тайлкарты —
 * пропуск; фоновая плоскость, пустая и в старой, и в новой колонке — пропуск.
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
extern void render_rowband(unsigned int world_row, unsigned int cam) __z88dk_callee;
extern void mario_draw(unsigned char x, unsigned char y,
                      const unsigned char *spr) __z88dk_callee;
extern void mario_undraw(void) __z88dk_callee;

#define CAM_NO_REF   0xFFFFu    /* в VRAM пусто (первый экран) */

#define FADE_HOLD    4          /* кадров на шаг фейда (больше — медленнее)  */

/* Регистр вертикального скролла порта 03h (spike, Этап 2): смещение вниз =
 * (gfx_scroll_row+1)&0xFF, кольцо по 256 строк. cam_y (px) => d2scroll. */
#define D2SCROLL(cam_y)  ((unsigned char)(0xFF - ((cam_y) & 0xFF)))

/* ----------------------------- ГЕОМЕТРИЯ ------------------------------- */
/* Экран 256x256 = 32x32 тайла; тайл 8 px. Мир шире экрана (LEVEL_COLS тайлов),
 * камера cam (в тайлах) листает его шагом 8 px. Строка тайла cy -> экранный
 * верх y = cy*8 (полоса уровня в tiles.png ложится на экран 1:1). */

#define TILE_PX      8
#define VIEW_BLOCKS  32                 /* 256 px / 8 = экран по горизонтали */
#define VIEW_ROWS    32                 /* 256 px / 8 = экран по вертикали    */
#define SPR_W        16                 /* спрайт Марио 16x16 = 2x2 тайла    */
#define SPR_H        16

#define GRAV         1                  /* прирост вертикальной скорости/кадр */
#define FALL_MAX     8                  /* предел скорости падения            */
#define JUMP_V0      (-11)              /* старт прыжка: ~в 3 раза выше изначальной (~55 px) */

#define CAM_MIN_BLK  10                 /* держим Марио в окне [10..20]      */
#define CAM_MAX_BLK  20
#define MAX_CAM      (LEVEL_COLS - VIEW_BLOCKS)

/* Вертикальная камера держит Марио в коридоре строк экрана [8..22]. Для уровня
 * высотой ровно экран (LEVEL_ROWS==32) MAX_CAM_ROW=0 => cam_row всегда 0 =>
 * регрессия к прежнему поведению. */
#define CAMR_MIN_ROW 8
#define CAMR_MAX_ROW 22

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
static int           my;         /* верх Марио по Y в МИРОВЫХ пикселях (0..H)  */
static int           vy;         /* вертикальная скорость, + = вниз             */
static unsigned char facing;     /* 0 = вправо, 1 = влево                      */
static unsigned char grounded;   /* стоит на опоре (можно прыгать)             */
static unsigned char walkphase;  /* 0..2 кадр ходьбы                            */
static unsigned char vy_hold;    /* ↓ удерживается                             */
static unsigned char moving;     /* удерживается направление — идёт ходьба     */
static unsigned char space_prev; /* ПРОБЕЛ в прошлом кадре — фронт для прыжка  */
static unsigned char esc_prev;   /* ESC в прошлом кадре — фронт для выхода     */

/* Вертикальная камера. cam_row — МИРОВАЯ тайловая строка у верха экрана;
 * tile_stride = LEVEL_ROWS (шаг колонки тайлкарты). Оба читаются ассемблером
 * (EXTERN _cam_row / _tile_stride), поэтому это глобальные (не static) с
 * внешней линковкой — компилятор обязан выпустить символы. */
unsigned char cam_row;
unsigned char tile_stride;

/* Кольцевое RAM-окно тайлкарты (Фаза 3). Вместо 20-КиБ tilemap в ROM держим в
 * RAM только OBJ_WIN_COLS колонок, запечённых из obj_data. Читают и C (pesh,
 * solid_at), и mario.asm (EXTERN _tile_win / _tile_win_base) — поэтому глобальные.
 * tile_win_base — МИРОВАЯ колонка окна[0] (кратна OBJ_WIN_STEP). */
unsigned char tile_win[OBJ_WIN_COLS * LEVEL_ROWS];
unsigned int    tile_win_base;
static unsigned char max_cam_row;    /* = LEVEL_ROWS>32 ? LEVEL_ROWS-32 : 0 */
static unsigned char old_cam_row;    /* cam_row в прошлом кадре            */

/* Где Марио нарисован в последний раз (его пиксели сейчас в VRAM).
 * Пока совпадает с текущим состоянием и камера не двинулась — кадр целиком
 * пропускаем: в VRAM уже лежит готовое изображение. */
static unsigned char drawn_blk;
static int           drawn_y;    /* мировой y (совпадение по всему значению) */
static const unsigned char *drawn_spr;

/* Испечь окно колонок [tile_win_base, tile_win_base+OBJ_WIN_COLS) из списка
 * объектов в tile_win. Обнуляем всё окно (BSS при --no-crt не зануляется),
 * затем затаптываем объекты, накрывающие окно. Печём ВСЕ LEVEL_ROWS строк
 * колонки, поэтому вертикальный скролл не требует перепечки. Вызывается на
 * старте и при сдвиге окна.
 *
 * Быстродействие (объектов ~1300, а перепечка на каждой границе окна):
 *   * горячие циклы обнуления/заполнения — на unsigned char (сравнение с 64
 *     инлайнится cp), иначе sccz80 на КАЖДУЮ ячейку вставлял вызов 16-битного
 *     сравнения (l_uge/l_ge) -> миллионы вызовов -> секунды фриза;
 *   * объекты отсортированы по x, скан начинается с obj_start[блок] (первый,
 *     способный достать до окна) и обрывается на x >= bend -> охватываем только
 *     полосу ~окно+max_w колонок, а не весь список. */
static void bake_window(void)
{
    unsigned int  b = tile_win_base, bend = tile_win_base + OBJ_WIN_COLS;
    unsigned int  i, x, c0, c1;
    unsigned char c, r, y, w, h, nrows, ncols, t;
    const unsigned char *o;
    unsigned char *p, *col;

    /* Обнуление окна: 8-битные вложенные счётчики, без 16-битных сравнений. */
    p = tile_win;
    for (c = 0; c < OBJ_WIN_COLS; c++)
        for (r = 0; r < LEVEL_ROWS; r++)
            *p++ = 0;

    /* Скан по отсортированному по x списку: старт с нужного блока, ранний выход. */
    i = obj_start[b >> 5];
    o = obj_data + i * 5;
    for (; i < (unsigned int)OBJ_COUNT; i++, o += 5) {
        x = (unsigned int)o[1] | ((unsigned int)(o[0] & 0x80) << 1);
        if (x >= bend)
            break;                          /* дальше только правее окна */
        y = o[2]; w = o[3]; h = o[4];
        if (x + w <= b)
            continue;                       /* левее окна */
        t = o[0] & 0x7F;
        c0 = (x > b) ? x : b;
        c1 = x + w;
        if (c1 > bend) c1 = bend;
        nrows = h;                          /* байт: высота с обрезкой по низу */
        if ((unsigned int)y + nrows > (unsigned int)LEVEL_ROWS)
            nrows = (unsigned char)(LEVEL_ROWS - y);
        ncols = (unsigned char)(c1 - c0);   /* <= OBJ_WIN_COLS, влезает в байт */
        col = tile_win + (c0 - b) * LEVEL_ROWS;
        for (c = 0; c < ncols; c++) {
            p = col + y;
            for (r = 0; r < nrows; r++)
                *p++ = t;
            col += LEVEL_ROWS;
        }
    }
}

/* Твёрдость ячейки мира (col,row): маска COLL_* свойства тайла (вариант C).
 * COLL_PLAT (1) — one-way опора, COLL_WALL (2) — непроходимо, 3 — и то, и др.
 * 0 — пусто. Берём тайл из RAM-окна tile_win (колонка-мажор, локальная колонка
 * = col - tile_win_base) и его свойство tile_solid. */
static unsigned char solid_at(int col, int row)
{
    int lc;
    if (col < 0 || row < 0 || col >= (int)LEVEL_COLS || row >= (int)LEVEL_ROWS)
        return 0;
    lc = col - (int)tile_win_base;
    if (lc < 0 || lc >= OBJ_WIN_COLS)
        return 0;                           /* вне окна (за границей уровня) */
    return tile_solid[tile_win[lc * LEVEL_ROWS + row]];
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
    /* Целевую палитру здесь НЕ ставим: первый кадр рисуем при чёрной
     * палитре (экран скрыт), потом плавно покажем его gfx_fade_in. */

    /* Старт: Марио у земли в НИЖНЕЙ части мира, камера прижата к низу.
     * tile_stride/cam_row читаются ассемблером до первого рендера. Для уровня
     * высотой ровно экран (LEVEL_ROWS==32): max_cam_row=0, cam_row=0,
     * my=(32-4)*8=224 — в точность прежнему поведению. */
    tile_stride  = (unsigned char)LEVEL_ROWS;
    max_cam_row  = (LEVEL_ROWS >= VIEW_ROWS)
                       ? (unsigned char)(LEVEL_ROWS - VIEW_ROWS) : 0;
    wblk = 4;
    cam = 0;
    mblk = (unsigned char)wblk;
    cam_row = max_cam_row;
    old_cam_row = cam_row;
    my = (int)(LEVEL_ROWS - 4) * TILE_PX;   /* ноги у нижней границы        */
    vy = 0;
    grounded = 1;
    facing = 0;
    walkphase = 0;
    frame = 0;
    space_prev = 0;            /* BSS не обнуляется (--no-crt): фронта нет   */
    esc_prev = 0;

    gfx_set_scroll(D2SCROLL(cam_row * TILE_PX));
    tile_win_base = 0;                 /* стартовое окно: колонки [0,64) */
    bake_window();
    render_window(cam, CAM_NO_REF, 0, VIEW_BLOCKS);
    spr = pick_sprite();
    mario_draw((unsigned char)(mblk * 8), (unsigned char)my, spr);
    drawn_blk = mblk;
    drawn_y = my;
    drawn_spr = spr;

    gfx_fade_in(level_palette, FADE_HOLD);   /* появление сцены из чёрного */

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
        {
            /* Выход по фронту ESC: выходим из цикла, ниже — гашение. */
            unsigned char esc = kbd_is_down(KBD_KEY_ESC);
            if (esc && !esc_prev)
                break;
            esc_prev = esc;
        }

        /* ---- горизонтальное движение (шаг 8 px, с проверкой стен) ---- */
        /* moving — удерживаемый признак ходьбы (пока зажато направление и не в
         * приседе), а НЕ импульс на один шаг: раньше между шагами pick_sprite
         * возвращал стойку, и ноги «перебирали» вдвое реже. */
        moving = (unsigned char)(dir && !vy_hold);
        old_cam = cam;
        old_cam_row = cam_row;

        if (moving) {
            /* Фазу переставляем каждый кадр ходьбы, независимо от того, что
             * тело смещается на тайл реже (раз в MOVE_DELAY). */
            walkphase = (unsigned char)((walkphase + 1) % 3);
            if (++frame >= MOVE_DELAY) {
                int nb, edge, d = (dir == 2) ? 1 : -1;
                int r0, r1;
                frame = 0;
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
            }
        } else {
            frame = 0;   /* встал — следующий шаг начнёт отсчёт заново        */
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
            if (my >= (int)LEVEL_TILE_H) {  /* утонул в яме — респавн в начале */
                wblk = 4; cam = 0; mblk = 4;
                my = (int)(LEVEL_ROWS - 4) * TILE_PX;
                cam_row = max_cam_row;
                vy = 0; grounded = 1;
            }
        }

        /* ---- вертикальная камера: держим Марио в коридоре строк экрана ----
         * Для уровня в один экран (max_cam_row=0) cam_row остаётся 0. ---- */
        {
            int mrow = my / TILE_PX;
            int rel = mrow - (int)cam_row;
            if (rel > CAMR_MAX_ROW && cam_row < max_cam_row) {
                cam_row = (unsigned char)(mrow - CAMR_MAX_ROW);
                if (cam_row > max_cam_row) cam_row = max_cam_row;
            } else if (rel < CAMR_MIN_ROW) {
                int nc = mrow - CAMR_MIN_ROW;
                cam_row = (unsigned char)(nc < 0 ? 0 : nc);
            }
            gfx_set_scroll(D2SCROLL(cam_row * TILE_PX));
        }

        /* ---- сдвиг окна тайлкарты: перепечь при переходе границы окна ----
         * Окно привязано к cam шагом OBJ_WIN_STEP; пока cam в пределах окна,
         * перепечки нет. cam остаётся непрерывным, а содержимое видимых
         * МИРОВЫХ колонок перепечка не меняет (меняется лишь локальный
         * индекс), поэтому обычный покадровый diff-рендер справляется сам —
         * полный редрав здесь НЕ нужен и раньше именно он давал подвисание. */
        {
            unsigned int nb = (unsigned int)cam & (unsigned int)~(OBJ_WIN_STEP - 1);
            if (nb != tile_win_base) {
                tile_win_base = nb;
                bake_window();
            }
        }

        /* ---- отрисовка ---- */
        spr = pick_sprite();
        {
            int dv = (int)cam_row - (int)old_cam_row;
            if (dv != 0) {
                /* Вертикаль: регистр скролла аппаратно сдвигает готовые
                 * строки (VRAM адресован МИРОВЫМ рядом => содержимое на
                 * месте). Дорисовываем только открытую полосу. */
                if (dv == 1 || dv == -1) {
                    unsigned int revealed = (dv == 1)
                        ? (unsigned int)(cam_row + VIEW_ROWS - 1) /* снизу */
                        : (unsigned int)cam_row;                  /* сверху */
                    render_rowband(revealed, cam);
                    if (cam != old_cam) {
                        if (cam == old_cam + 1 || old_cam == cam + 1)
                            render_window(cam, old_cam, 0, VIEW_BLOCKS);
                        else {
                            gfx_clear(0);   /* CAM_NO_REF рисует только не-небо */
                            render_window(cam, CAM_NO_REF, 0, VIEW_BLOCKS);
                        }
                    }
                } else {
                    /* >1 строки (редко): полный редрав с очисткой неба. */
                    gfx_clear(0);
                    render_window(cam, CAM_NO_REF, 0, VIEW_BLOCKS);
                }
            } else if (cam != old_cam) {
                /* Только горизонталь: разность колонок (как раньше). */
                if (cam == old_cam + 1 || old_cam == cam + 1)
                    render_window(cam, old_cam, 0, VIEW_BLOCKS);
                else {
                    gfx_clear(0);       /* респавн/прыжок камеры: CAM_NO_REF
                                         * рисует только не-небо, иначе останутся
                                         * кусочки тайлов с места гибели */
                    render_window(cam, CAM_NO_REF, 0, VIEW_BLOCKS);
                }
            } else if (mblk == drawn_blk && my == drawn_y && spr == drawn_spr) {
                continue;                   /* на экране ничего не изменилось */
            }
        }
        /* Фон и спрайт лежат на разных плоскостях (вес 8/4 против 2/1), поэтому
         * перерисовка фона не трогает Марио: стираем и рисуем его одним быстрым
         * шагом уже ПОСЛЕ фона. Раньше mario_undraw() шёл до тяжёлого
         * render_window() — развёртка заставала Марио стёртым → мерцание при
         * ходьбе. */
        mario_undraw();
        mario_draw((unsigned char)(mblk * 8), (unsigned char)my, spr);
        drawn_blk = mblk;
        drawn_y = my;
        drawn_spr = spr;
    }

    /* Выход по ESC: плавно гасим текущий кадр к чёрному и держим его. */
    gfx_fade_out(FADE_HOLD);
    for (;;)
        gfx_next_frame();

    return 0;
}
