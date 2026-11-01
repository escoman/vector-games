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
 *
 * ГОНКА С ЛУЧОМ (как в mario-timer). Буфер один, поэтому erase+draw Марио
 * нельзя делать «когда успели»: раз тяжёлый кадр (перепечка окна, diff-рендер
 * фона) сдвигает фазу, развёртка ловит спрайт на середине стирания — периодическое
 * мерцание. Позицию луча читаем с «секундомера растра» КР580ВИ53 канал 2
 * (lib/timer/timer.asm), который кадровый ISR перезапускает на каждом VBlank:
 * ждём, пока луч ПРОЙДЁТ нижнюю строку пятна, и только потом
 * пишем erase+draw подряд. См. блок «ГОНКА С ЛУЧОМ» ниже и docs/BEAM_TIMING.MD.
 */

#include "v06.h"

#include "level.inc"      /* level_palette, tileset, tilemap, LEVEL_* */
#include "mario.inc"      /* mario_<frame>_<r|l>                     */

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
 * RAM только OBJ_WIN_COLS колонок, запечённых из по-колоночных спанов
 * (pf_spans/pf_span_ofs). Читают и C (pesh,
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

/* ЗАПЕКАНИЕ ОКНА — в include/bake.asm. Замечания по алгоритму:
 *   * BSS при --no-crt не зануляется, поэтому печём ВСЕ LEVEL_ROWS строк
 *     колонки — вертикальный скролл тогда не требует перепечки;
 *   * в ROM лежат не экземпляры с прямоугольниками, а ГОТОВЫЕ по-колоночные
 *     спаны (максимальные прогоны одинакового тайла): словарь читала только
 *     печка, а рендер и коллизии работают с уже запечённым окном. Печка стала
 *     копированием спанов — без клипа, без bbox, без умножения на stride;
 *   * сдвиг базы окна перепекает окно целиком: на 8080 memmove выжившей
 *     половины (~70k T) плюс печка новых 32 колонок дороже, чем обнуление
 *     всего окна заливкой через SP (39.5k T) + копирование спанов всех 64
 *     колонок (~65k T) — половина окна не сдвигается, а меняет локальный
 *     номер, так что её всё равно пришлось бы переносить. Из-за этого
 *     bake_shift не возвращает признак «прыжок» — он обрабатывает все
 *     случаи сам (см. include/bake.asm).
 * Кто читает: mario.asm (_tile_win/_tile_win_base), solid_at ниже,
 * tools/check_bake.py и tools/check_boundary.py (зовут _bake_* напрямую). */
extern void bake_clear(unsigned char cstart, unsigned char cend) __z88dk_callee;
extern void bake_cols(unsigned int wstart, unsigned int wend) __z88dk_callee;
extern void bake_window(void);
extern void bake_shift(unsigned int nb) __z88dk_callee;

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

/* ------------------------- ГОНКА С ЛУЧОМ (beam) ------------------------
 * Как узнать, где луч. Порта, отдающего позицию луча, нет (03h — это скролл,
 * не счётчик), поэтому луч считают по времени: КР580ВИ53 канал 2
 * (порт 09h) на каждом VBlank перезапускают значением 0x7500 = ровно один
 * кадр при такте ВИ53 1.5 МГц (96 тиков на строку, 312 строк в кадре).
 * Счётчик линейно убывает вместе с лучом => timer_elapsed() = тики от начала
 * кадра, а растр строки экрана y = RASTER_BASE + y (первые 40 строк —
 * гашение: docs/BEAM_TIMING.MD §4). Режим 0, не 3: меандр канала 2 выведен
 * на динамик (был бы гул) и счётчик сам перезагружается на середине кадра.
 *
 * КУДА ПЕРЕСТАВИТЬ РИСОВАНИЕ. Марио пишется в живой буфер: если начать стирать,
 * когда луч ВНУТРИ пятна, нижнюю его часть луч прочитает уже стёртой — это и
 * есть мерцание. Безопасны оба края пятна: писать либо ДО того, как луч дошёл
 * до ВЕРХА (этот же кадр и покажет новый спрайт, задержки нет), либо ПОСЛЕ того,
 * как луч прошёл НИЗ (новые пиксели увидит следующий кадр). Выбор делает спин
 * по текущему timer_elapsed(): если до чтения верхней строки втискивается весь
 * шаг спрайта (DRAW_ROWS) плюс запас — рисуем немедленно, иначе ждём прохода
 * низа. Стереть и нарисовать надо без длинных операций между ними: пауза между
 * erase и draw показывает пустое место ровно один кадр.
 *
 * Почему НЕ «ждать низ пятна всегда». Спин только по нижней строке пятна
 * корректен, но ломает темп: Марио стоит на земле у нижнего края экрана, нижняя
 * строка пятна — ряд 240, то есть растр 296 из 312, и 34 строки erase+draw
 * переходят границу кадра. Замер на эмуляторе (одинаковый протокол: держим
 * RIGHT, 15 с): 2,71 кадра на итерацию против 1,87 в близнеце с выключенным
 * спином. Переход кадра стоит целый кадр темпа, потому что gfx_next_frame на
 * следующем шаге снимает frame_count уже ПОСЛЕ этого VBlank и ждёт ещё одного.
 * То же убийство темпа у варианта «рисовать всегда в гашении» (окно 56 строк
 * вмещает шаг спрайта, цель — константа): 3,11 кадра на итерацию.
 * Выбор края возвращает долг почти полностью: 1,80…2,08 (два замера, разброс
 * от участка уровня), причём dbg_ahead == dbg_draws (на равнине все шаги идут
 * впереди луча), а переносов рисования за VBlank нет вовсе (dbg_margin_min
 * остался 32767).
 *
 * Цены здесь две. Первая — геометрия: нужен ОДИН скролл — тот, что в порту 03h
 * ЗАФИКСИРОВАН (scr_top_prev), а не сегодняшний. Строки, написанные ниже луча,
 * ЭТИМ кадром всё равно листаются вчерашним значением регистра — kbd_scan
 * сбрасывает gfx_scroll_row только на VBlank. Второму скроллу места нет и в
 * диагностике переноса: там худший случай (растр строки 0). VRAM адресован
 * МИРОВЫМ рядом, поэтому пиксели спрайта привязаны к миру и от выбора края не
 * зависят — меняется только то, какой кадр их покажет.
 * Вторая — арифметика: sccz80 на каждое 16-битное действие зовёт библиотечного
 * помощника (l_sub, l_lt, l_gint4sp), а `* 96` и `/ 96` ещё и
 * __mulint/__divuint. Наивный спин по обоим скроллам стоил 7 688 T — дороже
 * самого erase+draw; спин только по нижнему краю — 2 112 T; выбор края —
 * 2 924 T, из них 372 T самого timer_wait (впереди луча он не зовётся вовсе).
 * Умножение на 96 свёрнуто в два сдвига (96 = 2^6 + 2^5), остальное — байтовые
 * действия.
 */
#define RASTER_BASE    40u    /* растр первой видимой строки экрана (y = 0)     */
#define WAKE_MARGIN      4u    /* строк запаса: после прохода низа, перед верхом */
#define SCR_ROWS       256u    /* строк экрана = кольцо VRAM по вертикали        */
#define DRAW_ROWS       34u    /* erase+draw целиком: 6 476 T = 33,7 строки      */

#define TICKS_LO         5u   /* 96 = (1<<6) + (1<<5): два сдвига вместо __mulint */
#define TICKS_HI         6u

/* Растр -> тики таймера (96 тиков на строку). */
#define RASTER_TICKS(r)  (((r) << TICKS_HI) + ((r) << TICKS_LO))

/* Кадровый ISR: перезапуск секундомера растра + опрос клавиатуры.
 * kbd_scan_now() пишет gfx_scroll_row в порт 03h в гашении — скролл
 * применяется синхронно с VBlank, не дёргает экран во время сканирования. */
static void mario_frame(void)
{
    timer_start();
    kbd_scan_now();
}

/* Мировой y верхнего края экрана МЛАДШИМ байтом (экранный номер мирового ряда w
 * есть (w - scr_top) & 0xFF, а младший байт разности от старших не зависит —
 * байтовые действия sccz80 делает на месте, 16-битные зовут помощника).
 * scr_top_prev — что ЗАФИКСИРОВАНО в порту 03h СЕЙЧАС: kbd_scan_now в ISR
 * сбрасывает gfx_scroll_row на VBlank, значит в этом кадре регистр ещё вчерашний. */
static unsigned char scr_top_px;
static unsigned char scr_top_prev;

/* Спин к ближайшему КРАЮ пятна (union старого спрайта, который сотрёт
 * mario_undraw, и нового): рисуем ЛИБО до того, как луч дошёл до верха пятна,
 * ЛИБО сразу после того, как он прошёл низ. Возвращает цель спина в тиках
 * таймера; 0 = ждать нечего (пишем немедленно). Пятно в мире — непрерывный
 * интервал [lo, lo+len); при скролле s он ложится на экран как [(lo-s) & 0xFF,
 * ...+len). Если интервал задевает шов кольца (или камера прыгнула — respawn),
 * ждём прохода всего экрана: закрашенное на «хвосте» кольца луч прочитает в
 * начале кадра, впереди нас. Знак ОДНОЙ разности drawn_y - y_new отвечает и на
 * «какой из спрайтов выше», и на «какова высота пятна». */
static unsigned int wake_below_sprite(int y_new)
{
    int d = drawn_y - y_new;
    unsigned int bot;                      /* экранная строка НИЗА пятна + 1    */
    unsigned char lo, off;
    unsigned int t_top, ticks;

    if (d >= 0) {
        lo = (unsigned char)y_new;        /* новый выше — считаем от него */
    } else {
        lo = (unsigned char)drawn_y;
        d = -d;
    }
    off = (unsigned char)(lo - scr_top_prev);
    bot = (unsigned int)off + (unsigned int)d + SPR_H;
    /* Впереди луча пишем, только если весь шаг спрайта с запасом втискивается
     * до чтения ВЕРХНЕЙ строки пятна (луч за это время уйдёт ниже на DRAW_ROWS
     * строк, а мы перепишем 16 — считаем консервативно по самому верхнему ряду)
     * и если пятно не заворачивается через шов кольца. */
    t_top = RASTER_TICKS(RASTER_BASE + (unsigned int)off);
    if (bot <= SCR_ROWS && timer_elapsed() + RASTER_TICKS(DRAW_ROWS + WAKE_MARGIN) <= t_top)
        return 0u;                         /* луч ещё выше — рисуем немедленно  */
    if (bot > SCR_ROWS) {
        bot = SCR_ROWS;                    /* шов кольца — ждём весь экран      */
    }
    /* Растр нижней строки пятна + запас; счётчик считает ОБРАТНО, поэтому
     * ждём, когда остаток станет не больше цели. timer_wait выходит и раньше
     * цели (луч уже ниже), и на перезагрузке счётчика (окно кадра упущено —
     * рисуем немедленно, в гашении сразу за VBlank). */
    ticks = RASTER_TICKS(RASTER_BASE + bot + WAKE_MARGIN);
    timer_wait(TIMER_REMAIN(ticks));
    return ticks;
}

/* ---- диагностика гонки (значения читаются из отладчика по символам _dbg_) --
 * Опасен только перенос рисования за начало видимой части следующего кадра:
 * тогда луч догонит строки, которые мы ещё пишем. margin — запас в строках до
 * растра, на котором луч начнёт читать строку 0 экрана (худший случай, не
 * зависящий от того, где на экране Марио). BSS при --no-crt не обнуляется,
 * поэтому значения инициализируем в main. */
unsigned int dbg_draws;        /* сколько erase+draw реально состоялось         */
unsigned int dbg_ahead;        /* из них нарисовано ДО луча (верх пятна цел)   */
unsigned int dbg_iters;        /* сколько итераций цикла: frame_count / dbg_iters
                                * = кадров на итерацию, то есть темп игры        */
unsigned int dbg_tear;         /* из них — законченных уже под лучом             */
unsigned int dbg_missed;       /* окно гашения этого кадра прошло, ждали до
                                * следующего VBlank (кадр был тяжелее окна)    */
int          dbg_margin_min;   /* худший запас в строках (по перенесённым)      */

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

    /* Секундомер растра заводим из кадрового ISR — с этого момента
     * timer_elapsed() даёт положение луча внутри кадра. */
    frame_handler = mario_frame;
    dbg_draws = 0;
    dbg_ahead = 0;
    dbg_iters = 0;
    dbg_tear = 0;
    dbg_missed = 0;
    dbg_margin_min = 32767;

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
    /* Порт 03h печатается сейчас — «вчерашнего» скролла ещё нет. */
    scr_top_px = scr_top_prev = (unsigned char)(cam_row * TILE_PX);
    tile_win_base = 0;                 /* стартовое окно: колонки [0,64) */
    bake_window();
    render_window(cam, CAM_NO_REF, 0, VIEW_BLOCKS);
    spr = pick_sprite();
    mario_draw((unsigned char)(mblk * 8), (unsigned char)my, spr);
    drawn_blk = mblk;
    drawn_y = my;
    drawn_spr = spr;

    gfx_fade_in(level_palette, FADE_HOLD);   /* появление сцены из чёрного */

    /* Разовая привязка счётчика к фазе луча (ei; halt; пуск): дальше
     * timer_start делает ISR на каждом VBlank. */
    timer_start_sync();

    for (;;) {
        unsigned int  old_cam;

        gfx_next_frame();

        /* ---- ввод: держим несколько клавиш сразу (стрелка + пробел).
         * Снимок матрицы уже готов: kbd_scan_now() в mario_frame (ISR)
         * опрашивает клавиатуру на VBlank. kbd_is_down() проверяет по нему
         * каждую клавишу отдельно без повторного дёрганья порта 03h. ---- */
        dbg_iters++;            /* диагностика темпа (см. блок _dbg_ выше)  */
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
                top_px = (int)cam_row * TILE_PX;   /* камера прыгнула на дно */
            }
            /* Учёт скролла для спина: gfx_set_scroll выше обновил РЕГИСТР, но в
             * порт 03h он уйдёт только на ближайшем VBlank внутри kbd_scan. Так
             * что «вчерашний» — это то, что scr_top_px хранил с прошлого витка. */
            scr_top_prev = scr_top_px;
            scr_top_px   = (unsigned char)top_px;
        }

        /* ---- сдвиг окна тайлкарты: перепечь при переходе границы окна ----
         * Окно привязано к cam шагом OBJ_WIN_STEP; пока cam в пределах окна,
         * перепечки нет. cam остаётся непрерывным, а содержимое видимых
         * МИРОВЫХ колонок перепечка не меняет (меняется лишь локальный
         * индекс), поэтому обычный покадровый diff-рендер справляется сам —
         * полный редрав здесь НЕ нужен и раньше именно он давал подвисание.
         * Обычный переход границы окна и прыжок камеры (респаун) обслуживает
         * bake_shift из include/bake.asm: он сам ставит tile_win_base и печёт
         * окно (на границе — с колонкой-стражем для diff-рендера). */
        {
            unsigned int nb = (unsigned int)cam & (unsigned int)~(OBJ_WIN_STEP - 1);
            if (nb != tile_win_base) {
                bake_shift(nb);
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
         * и тем же строкам VRAM.
         * Порядок «фон → выбор края → erase+draw» обязателен: тяжёлый фон
         * идёт ДО спина (иначе спин отсчитывал бы позицию луча, которая к
         * моменту записи уже устарела), а erase и draw стоят подряд — любой
         * длинный разрыв между ними показывает пустое место один кадр. */
        {
            unsigned int target, s_t, e_t;

            target = wake_below_sprite(dy);
            if (target == 0u)
                dbg_ahead++;              /* рисование впереди луча             */
            s_t = timer_elapsed();
            if (s_t < target)
                dbg_missed++;             /* спин не дождался: окно кадра упущено,
                                           * рисуем в гашении сразу за VBlank */
            mario_undraw();
            mario_draw((unsigned char)(mblk * 8), (unsigned char)dy, spr);
            e_t = timer_elapsed();
            dbg_draws++;
            if (e_t < s_t) {              /* счётчик перезапустился: рисование
                                           * перенесло через VBlank */
                /* Худший случай: луч начнёт читать строку 0 экрана на растре
                 * RASTER_BASE. Деление тиков на 96 — только здесь, на редком
                 * переносе; в обычном кадре одно сравнение 16-битных. */
                int margin = (int)((TIMER_LINES(RASTER_BASE) - e_t)
                                   / TIMER_TICKS_PER_LINE);
                if (margin < dbg_margin_min) dbg_margin_min = margin;
                if (margin < 0) dbg_tear++;
            }
        }
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
