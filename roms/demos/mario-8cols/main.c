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
 *
 * ЭКРАН ОТСТАЁТ ВДВОЕ. Вертикальная камера идёт не быстрее одной тайловой
 * строки за CAM_RATE кадров, поэтому Марио обгоняет экран и кромки экрана
 * становятся игровыми границами: ВЕРХНЯЯ кромка — потолок (прыгнувший выше неё
 * Марио рисуется прижатым к ней и скользит по ней, пока экран не уйдёт выше),
 * НИЖНЯЯ кромка — гибель (ушёл ногами за край = упал в пропасть, респаун в
 * начале уровня). По горизонтали камера, как и раньше, идёт нога в ногу с
 * шагом ходьбы (тот же темп: 8 px за MOVE_DELAY кадров).
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

/* Вертикальная камера держит Марио в коридоре строк экрана [8..22] и сдвигается
 * не быстрее одной тайловой строки за CAM_RATE кадров: экран отстаёт от Марио
 * вдвое (его максимальное падение = 1 строка/кадр). Отставание и делает кромки
 * экрана границами уровня: потолок сверху и гибель снизу. */
#define CAMR_MIN_ROW 8
#define CAMR_MAX_ROW 22
#define CAM_RATE     2
#define DEATH_HOLD   40                 /* кадров «замри» на месте гибели     */

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
static int           my;         /* верх Марио по Y в МИРОВЫХ пикселях; может быть выше
                                    верха экрана — рисуем ниже (потолок кромки) */
static int           vy;         /* вертикальная скорость, + = вниз             */
static unsigned char facing;     /* 0 = вправо, 1 = влево                      */
static unsigned char grounded;   /* стоит на опоре (можно прыгать)             */
static unsigned char walkphase;  /* 0..2 кадр ходьбы                            */
static unsigned char cam_rate;   /* фаза делителя скролла: CAM_RATE кадров/строку */
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
 * RAM только OBJ_WIN_COLS колонок, запечённых из словаря вариантов и списка
 * экземпляров (pf_data/pf_rects). Читают и C (pesh,
 * solid_at), и mario.asm (EXTERN _tile_win / _tile_win_base) — поэтому глобальные.
 * tile_win_base — МИРОВАЯ колонка окна[0] (кратна OBJ_WIN_STEP).
 *
 * tile_win_prevcol — колонка-«страж» НЕПОСРЕДСТВЕННО перед окном. На кадре
 * перехода окна вперёд (base: b -> b+32, cam = b+32, old_cam = b+31) ref-указатель
 * блока 0 считается как tile_win + (old_cam - base)*LEVEL_ROWS = tile_win-64,
 * т.е. попадает ровно в tile_win_prevcol. Если там мусор, пустые клетки левой
 * колонки экрана «совпадают» с эталоном и не стираются — на границе перепечки
 * остаются кусочки уехавшего фона (измерено: 75 байт VRAM в нулевом блоке).
 * bake_shift заносит сюда УЕХАВШУЮ за левый край МИРОВУЮ колонку base-1, так
 * что diff сравнивает с настоящими старыми тайлами и правка бесплатна.
 * Порядок объявлений в одном модуле = порядок в BSS; смежность проверяется
 * tools/check_boundary.py по map-файлу. */
unsigned char tile_win_prevcol[LEVEL_ROWS];
unsigned char tile_win[OBJ_WIN_COLS * LEVEL_ROWS];
unsigned int    tile_win_base;
/* log2(tile_stride) для умножения «шаг колонки окна» сдвигом в mario.asm;
 * 0xFF, если LEVEL_ROWS не степень двойки — тогда ассемблер идёт через
 * _mulstride. Считается один раз на старте, читается ассемблером. */
unsigned char   tile_stride_shl;
static unsigned char max_cam_row;    /* = LEVEL_ROWS>32 ? LEVEL_ROWS-32 : 0 */
static unsigned char old_cam_row;    /* cam_row в прошлом кадре            */

/* Где Марио нарисован в последний раз (его пиксели сейчас в VRAM).
 * Пока совпадает с текущим состоянием и камера не двинулась — кадр целиком
 * пропускаем: в VRAM уже лежит готовое изображение. */
static unsigned char drawn_blk;
static int           drawn_y;    /* мировой y верха спрайта (с учётом потолка) */
static const unsigned char *drawn_spr;

/* Замечания по запеканию окна [tile_win_base, tile_win_base+OBJ_WIN_COLS):
 *   * BSS при --no-crt не зануляется, поэтому печём ВСЕ LEVEL_ROWS строк
 *     колонки — вертикальный скролл тогда не требует перепечки;
 *   * горячие циклы обнуления/копирования/заполнения — на unsigned char
 *     (сравнение с <=64 инлайнится cp), иначе sccz80 на КАЖДУЮ ячейку вставлял
 *     вызов 16-битного сравнения (l_uge/l_ge) -> миллионы вызовов -> секунды
 *     фриза;
 *   * список экземпляров отсортирован по 32-колоночным блокам, скан полосы
 *     начинается с pf_start[блок] и обрывается на конце полосы -> охватываем
 *     только узкую полосу, а не весь список. За назад отступаем на PF_BACK
 *     блоков: широкий экземпляр живёт в группе своего левого края. */

/* Обнуление локальных колонок окна [cstart, cend). */
static void bake_clear(unsigned char cstart, unsigned char cend)
{
    unsigned char  c, r;
    unsigned char *p = tile_win + (unsigned int)cstart * LEVEL_ROWS;
    for (c = cstart; c < cend; c++)
        for (r = 0; r < LEVEL_ROWS; r++)
            *p++ = 0;
}

/* Запечь в окно МИРОВЫЕ колонки [wstart, wend) — обе кратны OBJ_WIN_STEP.
 * Клип по [wstart, wend), поэтому пережившую половину можно занести отдельно
 * (memmove в bake_shift), а сюда подавать только новую половину.
 *
 * Список экземпляров отсортирован по (x>>5, z-order), поэтому полоса —
 * непрерывный отрезок [pf_start[b0], pf_start[b1+1]); влево отступаем на
 * PF_BACK блоков, иначе теряется прогон земли, лежащий в группе соседа. Клип
 * каждого прямоугольника по [wstart, wend) делает этот запас безвредным.
 * Прямоугольники пишутся в порядке словаря, экземпляры — в порядке списка, то
 * есть поздние перекрывают ранних (z-order). */
static void bake_groups(unsigned int wstart, unsigned int wend)
{
    unsigned int  base = tile_win_base;
    unsigned int  b0 = wstart >> 5, b1 = (wend - 1) >> 5;
    unsigned int  i, end, x, v, vofs, c0, c1;
    unsigned char y, dy, nn, k, c, r, nrows, ncols, t;
    const unsigned char *p, *o;
    unsigned char *q, *col;

    if (b0 > (unsigned int)PF_BACK)
        b0 -= PF_BACK;
    else
        b0 = 0;
    if (b1 >= (unsigned int)OBJ_WIN_BLOCKS)
        b1 = (unsigned int)OBJ_WIN_BLOCKS - 1;
    end = pf_start[b1 + 1];
    i = pf_start[b0];
    p = pf_data + i * 4;
    for (; i < end; i++, p += 4) {
        x = (unsigned int)p[1] | ((unsigned int)(p[0] & 0x80) << 1);
        y = p[2];
        v = (unsigned int)(p[0] & 0x7F) | ((unsigned int)(p[3] & 0x1F) << 7);
        vofs = pf_var_ofs[v];
        nn = pf_var_n[v];
        for (k = 0; k < nn; k++) {
            o = pf_rects + (vofs + (unsigned int)k) * 5;
            c0 = x + (unsigned int)o[1];              /* dx */
            if (c0 < wstart)
                c0 = wstart;
            c1 = x + (unsigned int)o[1] + (unsigned int)o[3];   /* dx + w */
            if (c1 > wend)
                c1 = wend;
            if (c0 >= c1)
                continue;                     /* прямоугольник вне полосы */
            dy = o[2];
            nrows = o[4];
            if ((unsigned int)y + (unsigned int)dy + nrows
                    > (unsigned int)LEVEL_ROWS)
                nrows = (unsigned char)(LEVEL_ROWS - y - dy);
            ncols = (unsigned char)(c1 - c0);         /* <= OBJ_WIN_COLS */
            t = o[0];
            col = tile_win + (c0 - base) * LEVEL_ROWS;
            for (c = 0; c < ncols; c++) {
                q = col + y + dy;
                for (r = 0; r < nrows; r++)
                    *q++ = t;
                col += LEVEL_ROWS;
            }
        }
    }
}

/* Полная перепечка окна [base, base+OBJ_WIN_COLS): стартовый bake и редкий
 * прыжок камеры (респаун). На обычных границях окна вызывается bake_shift. */
static void bake_window(void)
{
    unsigned int b = tile_win_base;
    bake_clear(0, OBJ_WIN_COLS);
    bake_groups(b, b + OBJ_WIN_COLS);
}

/* Инкрементальный сдвиг базы на ОДИН шаг окна: сдвигаем выжившую половину
 * окна копированием и запекаем ТОЛЬКО новую половину — вдвое меньше затираний
 * и объектов, чем при полной перепечке. Обновляет tile_win_base сам. Возвращает
 * 1 при инкрементальном сдвиге (±шаг) и 0 при прыжке камеры — тогда caller
 * печет окно целиком (bake_window). */
static unsigned char bake_shift(unsigned int nb)
{
    unsigned int  old = tile_win_base;
    unsigned char cc, rr;
    unsigned char *d, *s;

    if (nb == old + OBJ_WIN_STEP) {
        /* Камера вперёд: мир ушёл влево, выживает старшая половина
         * local[32..64) -> local[0..32); справа входит новая половина.
         * Перед сдвигом сохраняем колонку, которая уезжает за левый край:
         * это МИРОВАЯ колонка nb-1, её diff-рендер следующего кадра использует
         * как эталон нулевого блока (см. tile_win_prevcol). */
        d = tile_win + (OBJ_WIN_STEP - 1) * LEVEL_ROWS;
        s = tile_win_prevcol;
        for (rr = 0; rr < LEVEL_ROWS; rr++)
            *s++ = *d++;
        d = tile_win;
        s = tile_win + OBJ_WIN_STEP * LEVEL_ROWS;
        for (cc = 0; cc < OBJ_WIN_STEP; cc++)
            for (rr = 0; rr < LEVEL_ROWS; rr++)
                *d++ = *s++;
        tile_win_base = nb;
        bake_clear(OBJ_WIN_STEP, OBJ_WIN_COLS);
        bake_groups(nb + OBJ_WIN_STEP, nb + OBJ_WIN_COLS);
        return 1;
    }
    if (nb + OBJ_WIN_STEP == old) {
        /* Камера назад: выживает младшая половина local[0..32) -> local[32..64);
         * слева входит новая половина. */
        d = tile_win + OBJ_WIN_STEP * LEVEL_ROWS;
        s = tile_win;
        for (cc = 0; cc < OBJ_WIN_STEP; cc++)
            for (rr = 0; rr < LEVEL_ROWS; rr++)
                *d++ = *s++;
        tile_win_base = nb;
        bake_clear(0, OBJ_WIN_STEP);
        bake_groups(nb, nb + OBJ_WIN_STEP);
        return 1;
    }
    return 0;                               /* прыжок: нужна полная перепечка */
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

/* Возврат на точку старта после гибели: мир, камера и делитель скролла
 * сбрасываются разом. Камера прыгает (old_cam != cam) — полный редрав ниже
 * сделает обычный путь отрисовки. */
static void respawn(void)
{
    wblk = 4; cam = 0; mblk = 4;
    my = (int)(LEVEL_ROWS - 4) * TILE_PX;
    cam_row = max_cam_row;
    cam_rate = 0;
    vy = 0; grounded = 1;
    gfx_set_scroll(D2SCROLL(cam_row * TILE_PX));
}

int main(void)
{
    unsigned char frame;
    unsigned char dir;
    unsigned char hold;
    const unsigned char *spr;
    int dy;                     /* мировой y верха спрайта с учётом потолка экрана */

    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_black_palette();
    gfx_clear(0);
    /* Целевую палитру здесь НЕ ставим: первый кадр рисуем при чёрной
     * палитре (экран скрыт), потом плавно покажем его gfx_fade_in. */

    /* Старт: Марио у земли в НИЖНЕЙ части мира, камера прижата к низу.
     * tile_stride/cam_row читаются ассемблером до первого рендера. */
    tile_stride  = (unsigned char)LEVEL_ROWS;
    /* шаг окна = степень двойки? ищем s, что 1<<s == LEVEL_ROWS. */
    {
        unsigned char s = 0;
        while (s < 8 && (1 << s) < LEVEL_ROWS)
            s++;
        tile_stride_shl = ((1 << s) == LEVEL_ROWS) ? s : 0xFF;
    }
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
    cam_rate = 0;              /* делитель скролла обнулён                    */
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
            if (my >= (int)LEVEL_TILE_H)    /* утонул за дном мира — респаун */
                respawn();
        }

        /* ---- вертикальная камера: коридор строк экрана + ДЕЛИТЕЛЬ СКРОЛЛА ----
         * Камера хочет вернуть Марио в [CAMR_MIN_ROW..CAMR_MAX_ROW], но едет не
         * быстрее одной тайловой строки за CAM_RATE кадров: экран отстаёт от Марио
         * вдвое (его предельное падение = 1 строка/кадр). Темп ограничен по времени,
         * а не «половиной приращения Марио»: при прижатом к потолку Марио обратная
         * связь «камера тянет край вверх» разгонила бы скролл до верха мира. ---- */
        {
            int mrow = my / TILE_PX;
            int rel = mrow - (int)cam_row;
            int want = cam_row;
            if (rel > CAMR_MAX_ROW) {
                want = mrow - CAMR_MAX_ROW;
                if (want > (int)max_cam_row) want = (int)max_cam_row;
            } else if (rel < CAMR_MIN_ROW) {
                want = mrow - CAMR_MIN_ROW;
                if (want < 0) want = 0;
            }
            if (want != (int)cam_row) {
                if (++cam_rate >= CAM_RATE) {
                    cam_rate = 0;
                    cam_row = (unsigned char)
                        ((want > (int)cam_row) ? cam_row + 1 : cam_row - 1);
                }
            } else {
                cam_rate = 0;    /* в коридоре — фаза не копится, ход начнётся сразу */
            }
            gfx_set_scroll(D2SCROLL(cam_row * TILE_PX));
        }

        /* ---- КРОМКИ ЭКРАНА. Отставание камеры делает край игровой границей:
         * выше верхней кромки Марио не рисуется (бьётся головой и скользит по
         * ней, пока экран не уйдёт выше), за нижнюю кромку ногами — гибель. ---- */
        {
            int top_px = (int)cam_row * TILE_PX;
            dy = (my < top_px) ? top_px : my;
            if (my + SPR_H > top_px + VIEW_ROWS * TILE_PX) {
                /* Гибель: держим последний кадр, затем респаун. В гибнущей
                 * позиции спрайт НЕ рисуем — VRAM кольцевой (256 строк), и
                 * строка за нижним краем закрутилась бы в верх экрана. */
                for (hold = 0; hold < DEATH_HOLD; hold++)
                    gfx_next_frame();
                respawn();
                dy = my;
            }
        }

        /* ---- сдвиг окна тайлкарты: перепечь при переходе границы окна ----
         * Окно привязано к cam шагом OBJ_WIN_STEP; пока cam в пределах окна,
         * перепечки нет. cam остаётся непрерывным, а содержимое видимых
         * МИРОВЫХ колонок перепечка не меняет (меняется лишь локальный
         * индекс), поэтому обычный покадровый diff-рендер справляется сам —
         * полный редрав здесь НЕ нужен и раньше именно он давал подвисание.
         * Обычный переход (±шаг) печём инкрементально (bake_shift): только
         * вошедшая половина окна. Прыжок камеры (респаун — cam меняется
         * более чем на шаг) даёт nb вдали от текущей базы: тогда полная bake_window. */
        {
            unsigned int nb = (unsigned int)cam & (unsigned int)~(OBJ_WIN_STEP - 1);
            if (nb != tile_win_base && !bake_shift(nb)) {
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
            } else if (mblk == drawn_blk && dy == drawn_y && spr == drawn_spr) {
                continue;                   /* на экране ничего не изменилось */
            }
        }
        /* Фон и спрайт лежат на разных плоскостях (вес 8/4 против 2/1), поэтому
         * перерисовка фона не трогает Марио: стираем и рисуем его одним быстрым
         * шагом уже ПОСЛЕ фона. Раньше mario_undraw() шёл до тяжёлого
         * render_window() — развёртка заставала Марио стёртым → мерцание при
         * ходьбе.
         * Рисуем по dy, а не по my: dy — тот же мировой y, но не выше верхней
         * кромки экрана (потолок), поэтому undraw/draw всегда идут по одним
         * и тем же строкам VRAM. */
        mario_undraw();
        mario_draw((unsigned char)(mblk * 8), (unsigned char)dy, spr);
        drawn_blk = mblk;
        drawn_y = dy;
        drawn_spr = spr;
    }

    /* Выход по ESC: плавно гасим текущий кадр к чёрному и держим его. */
    gfx_fade_out(FADE_HOLD);
    for (;;)
        gfx_next_frame();

    return 0;
}
