/*
 * Ну, погоди! — порт на Вектор-06Ц.
 *
 * --------------------------------------------------------------------------- 
 * СХЕМА ВЫВОДА
 * ---------------------------------------------------------------------------
 * Фон (bg.inc) занимает только чётные индексы палитры, поэтому бит 0 —
 * плоскость веса 1 (0xE000) — в фоне сброшен везде. Эта плоскость и есть
 * «плоскость сегментов»: все нарисованные объекты (волк, заяц, яйца,
 * цыплята, цифры, жизни) — её биты.
 *
 *   показать сегмент = gfx_plane_or(mask)
 *   стереть  сегмент = gfx_plane_andn(mask)   тем же массивом
 *
 * Сброс бита 0 возвращает ровно тот индекс фона, что был под сегментом, так
 * что стирание не нуждается ни в нейтральных патчах, ни в теневом буфере в
 * ОЗУ, а цвет сегмента не зависит от фона (все нечётные индексы палитры
 * заданы одинаково). В призрачной обводке на фоне сегмент виден как тёмное
 * ядро поверх светлого контура.
 *
 * Битмапы сегментов (src/sprites.inc) готовит tools/gen_assets.py; левый
 * край каждого прямоугольника кратен 8, потому что колонка VRAM несёт сразу
 * 8 пикселей строки и по горизонтали объект можно поставить только с шагом 8.
 * Сдвиг зашит в сами данные.
 *
 * Чтобы один сегмент, стираясь, не прожевал дыру в другом, все одновременно
 * видимые сегменты не должны иметь общих битов. Это так и есть: перебором по
 * 80 битмапам общие пиксели находятся только у разных ЦИФР одного разряда
 * (например digit0_0 и digit8_0), а они в одном слоте и по одному за раз.
 *
 * ---------------------------------------------------------------------------
 * ИГРОВАЯ ЛОГИКА
 * ---------------------------------------------------------------------------
 * Порт src/scene_play.js по семантике 1:1: те же состояния, те же таблицы,
 * те же пороги таймеров. Имена функций повторяют имена из JS, чтобы порт
 * читался рядом с оригиналом. Что сознательно отличается:
 *
 *   - delta у Phaser переменная (~16.7 мс), у нас кадр = 20 мс (50 Гц),
 *     поэтому все таймеры — целые счётчики миллисекунд;
 *   - gameSpeed — дробное число (4.00..12.x), здесь с фиксированной точкой
 *     1/16: speed16 = gameSpeed * 16, приращение таймера тика за кадр
 *     tick_inc = speed16 * 20. Порог тика — 1000 мс << 4;
 *   - gameCountFactor (+0.2 за круг) хранится как factor5 = factor * 5, то
 *     есть шагами по ровно 1 байту. Сверху ограничен FACTOR_MAX, иначе
 *     ratio * delta * factor переполняет 16 бит;
 *   - дублирующие переменные newLeftUpEgg/newLeftDownEgg/... свёрнуты в
 *     массив new_egg[4] по номеру жёлоба, четыре шага мигания жизни — в
 *     массивы anim_blink*;
 *   - animationSpeed в оригинале везде равен 1 и нигде не меняется — не
 *     портируется;
 *   - newEggsCleared в оригинале только записывается, но не читается —
 *     не портируется;
 *   - звук (8 дорожек) и SceneMenu в этой версии нет; рекорды живут в ОЗУ и
 *     сгорают при выключении;
 *   - выхода из игры нет: операционной системы у Вектора нет, сворачивать
 *     игру некуда. Заставка крутится вечно, АП2 возвращает в неё из игры;
 *   - клавиши управления не зашиты: каждое из четырёх действий вешается на
 *     любой ключ матрицы (строка + бит колонки). По умолчанию — ↖ ← СТР →,
 *     переназначение по Ф3 с миганием подписи у соответствующей кнопки.
 *
 * Опечатки и странности оригинала сохранены и помечены на месте: GameTick
 * вызывает CalcCurrentSpeed(), но результат выбрасывает (скорость меняется
 * только при ловле яйца); при lifeCount 1|0 GenerateNewEgg пишет в
 * this.reviousNewEgg, не обновляя previousNewEgg; ShowDigit при переходе
 * через 1000 не обновляется и до ближайшей ловли на табло висит 1000;
 * таблица ShowLives устроена не так, как подсказывает интуиция (показываются
 * ПТЕРЯННЫЕ жизни).
 */

#include "v06.h"
#include "src/bg.inc"
#include "src/sprites.inc"
#include "src/title_music.inc"


/* ----------------------------------------------------------------------- */
/*  Палитра фона                                                          */
/* ----------------------------------------------------------------------- */

/* Финальная палитра: индекс пикселя BMP (слот) -> цвет Вектора. Задаётся
 * ЗДЕСЬ, а не в bg.inc, чтобы подправить цвета можно было правкой этого
 * массива, без перегенерации ассетов (screen.bmp/sprites не трогаются).
 *
 * Фон занимает только ЧЁТНЫЕ слоты, поэтому бит 0 (плоскость 0xE000) в фоне
 * сброшен везде — это «плоскость сегментов». Нечётные слоты — чернила
 * сегментов, их цвет не важен (сегмент всегда 0x00, см. gfx_set_black_palette),
 * но держим чёрными. Индексы фиксированы tools/gen_assets.py.
 *
 * V06_RGB(r,g,b): R,G в 0..7, B в 0..3. */
static const unsigned char bg_palette[16] = {
    V06_RGB(2, 2, 1),   /*  0  вне поля (чёрная рамка)        */
    V06_RGB(0, 0, 0),   /*  1  чернила                        */
    V06_RGB(5, 5, 2),   /*  2  заливка арены                  */
    V06_RGB(0, 0, 0),   /*  3  чернила                        */
    V06_RGB(4, 4, 2),   /*  4  призраки сегментов             */
    V06_RGB(0, 0, 0),   /*  5  чернила                        */
    V06_RGB(3, 2, 0),   /*  6  декор: заборы, насесты         */
    V06_RGB(0, 0, 0),   /*  7  чернила                        */
    V06_RGB(7, 7, 3),   /*  8  декор: куры, логотип           */
    V06_RGB(0, 0, 0),   /*  9  чернила                        */
    V06_RGB(2, 2, 0),   /* 10  декор: кусты, травинки         */
    V06_RGB(0, 0, 0),   /* 11  чернила                        */
    V06_RGB(5, 0, 0),   /* 12  декор: крыша, кирпичи, гребешки */
    V06_RGB(0, 0, 0),   /* 13  чернила                        */
    V06_RGB(0, 0, 0),   /* 14  не исп.                        */
    V06_RGB(0, 0, 0),   /* 15  чернила                        */
};


/* ----------------------------------------------------------------------- */
/*  Позиции                                                               */
/* ----------------------------------------------------------------------- */

/* Один и тот же номер для жёлобов и для поз волка: 0..3.
 * Совпадает с groovePositions/wolfPositions из scene_play.js. */
#define POS_LU  0       /* левый верх */
#define POS_LD  1       /* левый низ  */
#define POS_RU  2       /* правый верх */
#define POS_RD  3       /* правый низ  */

#define EGGS_PER_GROOVE 5
#define GROOVE_LAST     (EGGS_PER_GROOVE - 1)   /* слот, где яйцо ловят/бьют */

/* Сторона разбитого яйца: brokenEggsSides left=0, right=2 — здесь 0/1,
 * это старшая половина индекса в chicken_blob[]. */
#define SIDE_LEFT   0
#define SIDE_RIGHT  1

#define GAME_A  0
#define GAME_B  1

/* HIDE — «сегмента в слоте нет». */
#define HIDE ((const unsigned char *)0)


/* ----------------------------------------------------------------------- */
/*  Таблицы сегментов                                                       */
/* ----------------------------------------------------------------------- */

/* Яйца: [позиция жёлоба][номер в жёлобе 0..4]. 0 — место входа, там яйцо
   появляется у зайца; 4 — у края, там яйцо ловится или бьётся. Порядок
   совпадает с номерами спрайтов в src/sprites.inc (egglefttop0 у зайца,
   egglefttop4 у корзины волка). */
static const unsigned char * const egg_blob[20] = {
    spr_egglefttop0,      spr_egglefttop1,      spr_egglefttop2,
    spr_egglefttop3,      spr_egglefttop4,
    spr_eggleftbottom0,   spr_eggleftbottom1,   spr_eggleftbottom2,
    spr_eggleftbottom3,   spr_eggleftbottom4,
    spr_eggrighttop0,     spr_eggrighttop1,     spr_eggrighttop2,
    spr_eggrighttop3,     spr_eggrighttop4,
    spr_eggrightbottom0,  spr_eggrightbottom1,  spr_eggrightbottom2,
    spr_eggrightbottom3,  spr_eggrightbottom4,
};

/* Волк: туловище смотрит влево или вправо, корзина зависит от позиции.
 * Туловище при переходе верх<->низ не меняется — меняется только корзина. */
static const unsigned char * const wolf_body[2] = {
    spr_wolfleft, spr_wolfright,
};
static const unsigned char * const wolf_basket[4] = {
    spr_baskettopleft, spr_basketbottomleft,
    spr_baskettopright, spr_basketbottomright,
};

/* Цыплёнок: [сторона][кадр 0..4], кадр 0 — у края. */
static const unsigned char * const chicken_blob[10] = {
    spr_chickenleft0,  spr_chickenleft1,  spr_chickenleft2,
    spr_chickenleft3,  spr_chickenleft4,
    spr_chickenright0, spr_chickenright1, spr_chickenright2,
    spr_chickenright3, spr_chickenright4,
};

/* Цифра результата: [цифра 0..9][разряд 0..3], разряд 0 — левый. */
static const unsigned char * const digit_blob[40] = {
    spr_digit0_0, spr_digit0_1, spr_digit0_2, spr_digit0_3,
    spr_digit1_0, spr_digit1_1, spr_digit1_2, spr_digit1_3,
    spr_digit2_0, spr_digit2_1, spr_digit2_2, spr_digit2_3,
    spr_digit3_0, spr_digit3_1, spr_digit3_2, spr_digit3_3,
    spr_digit4_0, spr_digit4_1, spr_digit4_2, spr_digit4_3,
    spr_digit5_0, spr_digit5_1, spr_digit5_2, spr_digit5_3,
    spr_digit6_0, spr_digit6_1, spr_digit6_2, spr_digit6_3,
    spr_digit7_0, spr_digit7_1, spr_digit7_2, spr_digit7_3,
    spr_digit8_0, spr_digit8_1, spr_digit8_2, spr_digit8_3,
    spr_digit9_0, spr_digit9_1, spr_digit9_2, spr_digit9_3,
};

/* Заставки (жизни): три места. */
static const unsigned char * const life_blob[3] = {
    spr_life_0, spr_life_1, spr_life_2,
};


/* ----------------------------------------------------------------------- */
/*  Слоты сегментов                                                        */
/* ----------------------------------------------------------------------- */

/* Каждый выводимый объект занимает один слот. В слоте лежит массив, который
 * сейчас в плоскости, либо 0. Перерисовка = AND-NOT старого и OR нового,
 * поэтому сегменты никогда не наслаиваются друг на друга и не оставляют
 * «трупа» после стирания. */
#define SLOT_WOLF_BODY  0
#define SLOT_WOLF_BASK  1
#define SLOT_RABBIT     2
#define SLOT_EGGS       3       /* 20: POS*5 + номер в жёлобе */
#define SLOT_CHICKEN0   23      /* цыплёнок у края: в оригинале кадр 0 висит
                                 * всё время анимации и не перекрывается
                                 * кадрами 1..4 */
#define SLOT_CHICKEN    24      /* кадры 1..4 бегущего цыплёнка */
#define SLOT_LIVES      25      /* 3 */
#define SLOT_DIGITS     28      /* 4 */
#define SLOT_COUNT      32

static const unsigned char *slot_blob[SLOT_COUNT];

/* Поставить в слот новый битмап (HIDE — просто стереть). */
static void slot_put(unsigned char which, const unsigned char *blob)
{
    if (slot_blob[which] == blob)
        return;
    if (slot_blob[which])
        gfx_plane_andn(slot_blob[which]);
    slot_blob[which] = blob;
    if (blob)
        gfx_plane_or(blob);
}


/* ----------------------------------------------------------------------- */
/*  Экран                                                                  */
/* ----------------------------------------------------------------------- */

/* Фон: 24 КБ плоскостей 8,4,2 лежат в bg_zx0 линейно в порядке адресов VRAM,
 * поэтому распаковка — один вызов прямо в 0x8000. Это весь экран 256x256:
 * поле 256x176, сдвинутое на 24 строки вниз, панель кнопок и логотипа снизу
 * и чёрные строки под текст.
 *
 * Фон за время игры не меняется, поэтому он распаковывается ОДИН раз при
 * старте (bg_load). Смена состояния (заставка <-> игра) трогает только
 * плоскость сегментов 0xE000 — её обнуляет screen_reset(). Распаковка 24 КБ
 * стоит ~55 кадров, и делать её на каждом старте означало бы заставлять
 * пользователя ждать без всякого толка. */
static unsigned char bg_ready;

static void bg_load(void)
{
    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_black_palette();
    gfx_fill_planes(0x01, 0x00);        /* плоскость сегментов пуста */
    zx0_decompress(bg_zx0, V06_VRAM);
    gfx_set_palette(bg_palette);
    bg_ready = 1;
}

/* Сброс перед новым состоянием: ни одного сегмента в плоскости, все слоты
 * пусты. Фон (плоскости 8,4,2) и текст поверх него остаются. */
static void screen_reset(void)
{
    unsigned char i;

    if (!bg_ready)
        bg_load();
    for (i = 0; i < SLOT_COUNT; i++)
        slot_blob[i] = 0;
    gfx_fill_planes(0x01, 0x00);
}


/* ----------------------------------------------------------------------- */
/*  Вывод сегментов                                                        */
/* ----------------------------------------------------------------------- */

static void wolf_put(unsigned char position)
{
    slot_put(SLOT_WOLF_BODY, wolf_body[position >> 1]);
    slot_put(SLOT_WOLF_BASK, wolf_basket[position]);
}

static void chicken_put_edge(unsigned char side, unsigned char on)
{
    slot_put(SLOT_CHICKEN0, on ? chicken_blob[side * 5] : HIDE);
}

/* Кадры 1..4 бегут по нижнему ярусу в одном слоте. */
static void chicken_put_run(unsigned char side, unsigned char frame)
{
    slot_put(SLOT_CHICKEN, chicken_blob[side * 5 + frame]);
}

/* ShowDigit: четыре разряда, ведущие нули ПОКАЗЫВАЮТСЯ — в оригинале
 * ("0000"+number).slice(-4), так что на старте висит «0000». */
static void digits_show(unsigned int value)
{
    unsigned char i;
    unsigned int q;
    unsigned char d[4];

    q = value / 1000u; d[0] = (unsigned char)q; value -= q * 1000u;
    q = value / 100u;  d[1] = (unsigned char)q; value -= q * 100u;
    q = value / 10u;   d[2] = (unsigned char)q;
    d[3] = (unsigned char)(value - q * 10u);

    for (i = 0; i < 4; i++)
        slot_put(SLOT_DIGITS + i, digit_blob[d[i] * 4u + i]);
}

static void life_put(unsigned char which, unsigned char on)
{
    slot_put(SLOT_LIVES + which, on ? life_blob[which] : HIDE);
}

static void rabbit_put(unsigned char on)
{
    slot_put(SLOT_RABBIT, on ? spr_rabbit : HIDE);
}


/* ----------------------------------------------------------------------- */
/*  Состояние игры                                                         */
/* ----------------------------------------------------------------------- */

/* gameStates из JS: idle/initialise/starting свёрнуты в ST_MENU, pause нет
 * (АП2 из игры сразу уходит в меню, как кнопка Pause в оригинале). */
#define ST_MENU      0
#define ST_PLAYING   1
#define ST_LOOSE     2
#define ST_ANIMATION 3

static unsigned char state;
static unsigned char game_type;                 /* GAME_A / GAME_B */
static unsigned char wolf_position;

/* Четыре жёлоба по пять флагов: 1 — в этом месте жёлоба лежит яйцо. */
static unsigned char groove[4][EGGS_PER_GROOVE];
/* newLeftUpEgg..newRightDownEgg: в какой жёлоб при следующем сдвиге встанет
 * новое яйцо. */
static unsigned char new_egg[4];

static unsigned char eggs_needed;               /* currentEggOnScreenNeeded */
static unsigned char groove_cursor;             /* currentGroove */
static unsigned char previous_new_egg;          /* previousNewEgg */
static unsigned char life_count;
static unsigned char bonus200, bonus500;        /* increaseOn200/500 */
static unsigned char broken_side;

static unsigned int score;
static unsigned int rounds;                     /* gameCountForHiScore */
static unsigned int hiscore[2];

/* Время. game_timer — тик тика в 1/16 мс, остальное в миллисекундах. */
#define FRAME_MS      20u                       /* 50 Гц */
#define SPEED_SHIFT   4                         /* gameSpeed × 16 */
#define TICK_LIMIT    (1000u << SPEED_SHIFT)
#define RABBIT_MS     5000u
#define LOOSE_MS      2000u

static unsigned int speed16;
static unsigned int tick_inc;                   /* speed16 * FRAME_MS */
static unsigned int game_timer;
static unsigned int rabbit_timer;
static unsigned int loose_timer;
static unsigned char rabbit_visible;
static unsigned char factor5;                   /* gameCountFactor × 5 */

/* 5 + 5·N после N обнулений счёта. Выше FACTOR_MAX не пускаем: в
 * IncreaseScore перемножаем ratio(≤99) × delta(≤8) × factor5, и при 90
 * произведение переполнило бы 16 бит. */
#define FACTOR_MAX    80

/* ГПСЧ. Phaser.Math.Between(min,max) — равномерный целый; здесь старший байт
 * 16-битного LCG, умноженный на (n+1) и сдвинутый на 8 — 0..n без деления. */
static unsigned int rnd_state;
static unsigned int idle_frames;                /* счётчик кадров в меню */

static unsigned char between(unsigned char n)
{
    unsigned int v;

    rnd_state = rnd_state * 25173u + 13831u;
    v = (unsigned int)((rnd_state >> 8) & 0xFFu);
    return (unsigned char)((v * (unsigned int)(n + 1u)) >> 8);
}


/* ----------------------------------------------------------------------- */
/*  Таблицы логики                                                         */
/* ----------------------------------------------------------------------- */

/* Порядок перебора жёлобов одним GameTick(). Строка — lifeCount (для gameA)
 * или gameB; колонка — currentGroove. */
static const unsigned char turn_order[5][4] = {
    { POS_LU, POS_RU, POS_RD, POS_LU },   /* gameA, 6        */
    { POS_LU, POS_RU, POS_LD, POS_LU },   /* gameA, 5|4      */
    { POS_RU, POS_LD, POS_RD, POS_RU },   /* gameA, 3|2      */
    { POS_LU, POS_LD, POS_RD, POS_LU },   /* gameA, 1|0      */
    { POS_LU, POS_RU, POS_LD, POS_RD },   /* gameB           */
};
static const unsigned char turn_len[5] = { 3, 3, 3, 3, 4 };

/* Куда встанет новое яйцо по номеру currentNewEgg. Тот же порядок строк. */
static const unsigned char egg_choice[5][4] = {
    { POS_LU, POS_RU, POS_RD, POS_LU },   /* 6: LU RU RD     */
    { POS_LU, POS_LD, POS_RU, POS_LU },   /* 5|4: LU LD RU   */
    { POS_LD, POS_RU, POS_RD, POS_LD },   /* 3|2: LD RU RD   */
    { POS_LU, POS_LD, POS_RD, POS_LU },   /* 1|0: LU LD RD   */
    { POS_LU, POS_RU, POS_LD, POS_RD },   /* gameB           */
};

/* Строка таблицы по lifeCount: 6 → 0, 5|4 → 1, 3|2 → 2, 1|0 → 3. */
static unsigned char life_row(unsigned char n)
{
    if (n >= 6) return 0;
    if (n >= 4) return 1;
    if (n >= 2) return 2;
    return 3;
}

/* stagesStartSpeed / stagesFinishSpeed. */
static const unsigned char stage_start[10] = { 4, 4, 4, 5, 6, 7, 7, 8, 9, 12 };
static const unsigned char stage_finish[10] = { 7, 7, 8, 9, 9, 8, 8, 12, 12, 12 };

/* Таблица currentEggOnScreenNeeded из IncreaseScore: первые 26 диапазонов
 * счёта. Граница 999 в оригинале означает «при 999 не менять»; считаем 999
 * последним в диапазоне 815..999 — на игру не влияет, при 1000 счёт всё
 * равно обнуляется. */
static const unsigned int score_lim[26] = {
    5u, 10u, 50u, 100u, 140u, 200u, 230u, 280u, 300u, 320u, 360u, 400u, 410u,
    460u, 500u, 510u, 550u, 600u, 605u, 640u, 700u, 705u, 720u, 800u, 815u,
    1000u,
};
static const unsigned char score_need[26] = {
    1, 2, 3, 4, 3, 4, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 4,
    5,
};


/* ----------------------------------------------------------------------- */
/*  Прототипы (взаимные вызовы состояний и анимаций)                       */
/* ----------------------------------------------------------------------- */

static void clear_eggs_on_screen(void);
static void groove_draw(unsigned char position);
static void digits_show(unsigned int value);
static void show_lives(unsigned char n);
static void increase_score(unsigned char count);
static void decrease_life_count(unsigned char count);
static void start_chicken(void);
static void start_egg_broke(void);
static void start_add_lives(void);
static void anim_blink_start(unsigned char which);
static void anim_blink_stop(void);
static void save_hi_score(void);
static void to_menu(void);
static void draw_ui(void);            /* текст поверх фона, см. «Меню и панель» */


/* ----------------------------------------------------------------------- */
/*  Скорость                                                               */
/* ----------------------------------------------------------------------- */

/* CalcCurrentSpeed(): линейная интерполяция между стартом и финишем этапа
 * (этап = сотня очков) с множителем gameCountFactor. Результат — 1/16 мс. */
static void calc_current_speed(void)
{
    unsigned int s = score;
    unsigned char stage = (unsigned char)(s / 100u);
    unsigned char ratio = (unsigned char)(s - (unsigned int)stage * 100u);
    unsigned int t;

    t = (unsigned int)ratio;
    t = t * (unsigned int)(stage_finish[stage] - stage_start[stage]);
    t = t * (unsigned int)factor5 / 500u;       /* /100 и ×factor(×5) */

    speed16 = ((unsigned int)stage_start[stage] << SPEED_SHIFT) + t;
    tick_inc = speed16 * FRAME_MS;
}

/* gameSpeed = 4: старт игры и каждое прохождение тысячи. */
static void speed_reset(void)
{
    speed16 = 4u << SPEED_SHIFT;
    tick_inc = speed16 * FRAME_MS;
}


/* ----------------------------------------------------------------------- */
/*  Жёлобы и яйца                                                          */
/* ----------------------------------------------------------------------- */

/* drawGroove(position): переложить флаги жёлоба в плоскость сегментов. */
static void groove_draw(unsigned char position)
{
    unsigned char i;
    unsigned char base = position * EGGS_PER_GROOVE;

    for (i = 0; i < EGGS_PER_GROOVE; i++)
        slot_put(SLOT_EGGS + base + i,
                 groove[position][i] ? egg_blob[base + i] : HIDE);
}

static unsigned char count_eggs_on_stage(void)
{
    unsigned char p, i, n = 0;

    for (p = 0; p < 4; p++)
        for (i = 0; i < EGGS_PER_GROOVE; i++)
            n = (unsigned char)(n + groove[p][i]);
    return n;
}

static unsigned char count_eggs_on_first(void)
{
    unsigned char p, n = 0;

    for (p = 0; p < 4; p++)
        n = (unsigned char)(n + groove[p][0]);
    return n;
}

static void clear_new_eggs(void)
{
    new_egg[0] = 0; new_egg[1] = 0; new_egg[2] = 0; new_egg[3] = 0;
}

/* GenerateNewEgg(): не больше currentEggsOnScreenNeeded яиц на сцене и ни
 * одного у края — иначе новому яйцу некуда вставать. */
static void generate_new_egg(void)
{
    unsigned char row, c;

    if (count_eggs_on_stage() >= eggs_needed)
        return;
    if (count_eggs_on_first() != 0)
        return;

    row = game_type ? 4 : life_row(life_count);
    do {
        c = between(game_type ? 3 : 2);
    } while (c == previous_new_egg);

    /* Опечатка оригинала (this.reviousNewEgg) при lifeCount 1|0:
     * previousNewEgg остаётся от предыдущей ветки. Точь-в-точь. */
    if (row != 3)
        previous_new_egg = c;

    new_egg[egg_choice[row][c]] = 1;
}

/* GrooveTurn(position): сдвиг жёлоба на шаг к краю. Яйцо, сошедшее с края,
 * либо ловится (совпало с позицией волка), либо бьётся. */
static void groove_turn(unsigned char position)
{
    unsigned char *g = groove[position];

    if (g[GROOVE_LAST]) {
        if (wolf_position == position) {
            increase_score(1);
        } else {
            broken_side = (position == POS_LU || position == POS_LD)
                        ? SIDE_LEFT : SIDE_RIGHT;
            /* Разбитое яйцо видно только если заяц сейчас на месте; иначе
               скорлупу подбирает цыплёнок. */
            if (rabbit_visible) start_chicken();
            else start_egg_broke();
        }
    }

    g[4] = g[3]; g[3] = g[2]; g[2] = g[1]; g[1] = g[0];
    g[0] = new_egg[position];
    if (g[0])
        clear_new_eggs();

    groove_draw(position);
}

/* Turn(): один тик — один жёлоб, порядок жёлобов зависит от gameType и от
 * числа оставшихся жизней. */
static void turn(void)
{
    unsigned char row;

    generate_new_egg();
    row = game_type ? 4 : life_row(life_count);
    groove_turn(turn_order[row][groove_cursor]);

    groove_cursor++;
    if (groove_cursor >= turn_len[row])
        groove_cursor = 0;
}


/* ----------------------------------------------------------------------- */
/*  Счёт и жизни                                                           */
/* ----------------------------------------------------------------------- */

static void increase_score(unsigned char count)
{
    unsigned char i;

    /* Скорость пересчитывается по счёту ДО начисления — как в оригинале. */
    calc_current_speed();

    score += count;
    digits_show(score);

    for (i = 0; i < 26; i++)
        if (score < score_lim[i]) { eggs_needed = score_need[i]; break; }

    /* На 200 и 500 очках, если жизни потеряны, — одна возвращённая жизнь. */
    if (score == 200u && life_count != 6 && !bonus200) {
        bonus200 = 1;
        start_add_lives();
    }
    if (score == 500u && life_count != 6 && !bonus500) {
        bonus500 = 1;
        start_add_lives();
    }

    if (score >= 1000u) {
        bonus200 = 0;
        bonus500 = 0;
        if (factor5 < FACTOR_MAX)
            factor5++;                          /* gameCountFactor += 0.2 */
        speed_reset();
        rounds++;
        score = 0;
        /* ShowDigit(0) в оригинале не вызывается: до ближайшей ловли на
         * табло висит 1000. */
    }
}

/* DecreaseLifeCount(): цыплёнок уносит одно яйцо, разбитое яйцо стоит двух.
 * 0 жизней — конец игры, через 2 с возврат в меню. */
static void decrease_life_count(unsigned char count)
{
    life_count = (life_count > count)
               ? (unsigned char)(life_count - count) : 0;

    switch (life_count) {
    case 5: show_lives(5); break;
    case 4: show_lives(4); break;
    case 3: show_lives(3); break;
    case 2: show_lives(2); break;
    case 1: show_lives(1); break;
    default:
        if (life_count == 0) {
            show_lives(0);
            state = ST_LOOSE;
            loose_timer = 0;
        }
        break;
    }
}

/* ShowLives: на табло — ПОТЕРЯННЫЕ яйца, и не по прямой зависимости:
 * 0 → все три, 1 → два + мигает первым, 2 → два, 3 → одно + мигает вторым,
 * 4 → одно, 5 → мигает третьим, 6 → пусто. Всё как в оригинале. */
static void show_lives(unsigned char n)
{
    anim_blink_stop();

    life_put(0, 0); life_put(1, 0); life_put(2, 0);

    switch (n) {
    case 0: life_put(0, 1); life_put(1, 1); life_put(2, 1); break;
    case 1: life_put(1, 1); life_put(2, 1); anim_blink_start(0); break;
    case 2: life_put(1, 1); life_put(2, 1); break;
    case 3: life_put(2, 1); anim_blink_start(1); break;
    case 4: life_put(2, 1); break;
    case 5: anim_blink_start(2); break;
    default: break;
    }
}

/* ClearEggsOnScreen(): после разбитого яйца жёлобы пусты. */
static void clear_eggs_on_screen(void)
{
    unsigned char p, i;

    for (p = 0; p < 4; p++) {
        for (i = 0; i < EGGS_PER_GROOVE; i++)
            groove[p][i] = 0;
        groove_draw(p);
    }
}

/* setWolfPosition(): туловище по стороне, корзина по позиции. */
static void set_wolf_position(unsigned char position)
{
    wolf_position = position;
    wolf_put(position);
}


/* ----------------------------------------------------------------------- */
/*  Анимации                                                               */
/* ----------------------------------------------------------------------- */

/* Яйцо разбилось: у края сидит цыплёнок (кадр 0), 3 с, затем минус две
 * жизни. */
static unsigned char anim_broke, anim_broke_step;
static unsigned int anim_broke_timer;

/* Цыплёнок утащил яйцо: 5 кадров по 500 мс, минус одна жизнь. */
static unsigned char anim_chicken, chicken_frame;
static unsigned int anim_chicken_timer, chicken_next;

/* Возврат жизни: 14 миганий всеми тремя заставками по 500 мс. */
static unsigned char anim_addlives, addlives_k;
static unsigned int anim_addlives_timer, addlives_next;

/* Мигание потерянной жизни: видно 500 мс, скрыто 500 мс, до отмены. */
static unsigned char anim_blink[3], anim_blink_step[3];
static unsigned int anim_blink_timer[3];

#define ANIM_STEP_MS 500u
#define BROKE_MS     3000u
#define CHICKEN_FRAMES 5
#define ADDLIVES_STEPS 14


static void anim_blink_start(unsigned char which)
{
    if (!anim_blink[which]) {
        anim_blink_timer[which] = 0;
        anim_blink[which] = 1;
    }
}

/* Шаг 1 в EggBlinkingAnimation не сбрасывается — ShowLives гасит мигание,
 * оставив шаг включённым, и первый цикл после этого проходит «вхолостую».
 * Сохраняем и это. */
static void anim_blink_stop(void)
{
    anim_blink[0] = 0; anim_blink[1] = 0; anim_blink[2] = 0;
}

static void anim_blink_tick(unsigned char which)
{
    anim_blink_timer[which] += FRAME_MS;

    if (anim_blink_timer[which] > ANIM_STEP_MS && !anim_blink_step[which]) {
        life_put(which, 1);
        anim_blink_step[which] = 1;
    }
    if (anim_blink_timer[which] > 2u * ANIM_STEP_MS) {
        life_put(which, 0);
        anim_blink_step[which] = 0;
        anim_blink_timer[which] = 0;
    }
}

static void start_egg_broke(void)
{
    if (anim_broke) return;
    state = ST_ANIMATION;
    anim_broke_timer = 0;
    anim_broke_step = 0;
    anim_broke = 1;
}

static void anim_broke_tick(void)
{
    anim_broke_timer += FRAME_MS;

    if (!anim_broke_step) {
        anim_broke_step = 1;
        chicken_put_edge(broken_side, 1);
    }
    if (anim_broke_timer > BROKE_MS) {
        clear_eggs_on_screen();
        chicken_put_edge(broken_side, 0);
        decrease_life_count(2);
        anim_broke_timer = 0;
        anim_broke_step = 0;
        anim_broke = 0;
        if (state != ST_LOOSE) state = ST_PLAYING;
    }
}

static void start_chicken(void)
{
    if (anim_chicken) return;
    state = ST_ANIMATION;
    anim_chicken_timer = 0;
    chicken_next = 0;
    chicken_frame = 0;
    anim_chicken = 1;
}

static void anim_chicken_tick(void)
{
    anim_chicken_timer += FRAME_MS;
    if (anim_chicken_timer <= chicken_next)
        return;

    chicken_next += ANIM_STEP_MS;

    if (chicken_frame < CHICKEN_FRAMES) {
        if (chicken_frame == 0) chicken_put_edge(broken_side, 1);
        else chicken_put_run(broken_side, chicken_frame);
        chicken_frame++;
        return;
    }

    /* >2500 мс: цыплёнок утащил яйцо, минус одна жизнь. */
    slot_put(SLOT_CHICKEN, HIDE);
    chicken_put_edge(broken_side, 0);
    clear_eggs_on_screen();
    decrease_life_count(1);
    anim_chicken_timer = 0;
    anim_chicken = 0;
    if (state != ST_LOOSE) state = ST_PLAYING;
}

static void start_add_lives(void)
{
    if (anim_addlives) return;
    state = ST_ANIMATION;
    anim_addlives_timer = 0;
    addlives_next = 0;
    addlives_k = 0;
    anim_addlives = 1;
    show_lives(6);
}

static void anim_addlives_tick(void)
{
    anim_addlives_timer += FRAME_MS;
    if (anim_addlives_timer <= addlives_next)
        return;

    addlives_next += ANIM_STEP_MS;

    if (addlives_k < ADDLIVES_STEPS) {
        /* Чётные шаги гасят все три заставки, нечётные зажигают. */
        unsigned char on = (unsigned char)(addlives_k & 1);
        life_put(0, on); life_put(1, on); life_put(2, on);
        addlives_k++;
        return;
    }

    life_count = 6;
    show_lives(6);
    clear_eggs_on_screen();
    slot_put(SLOT_CHICKEN, HIDE);
    chicken_put_edge(SIDE_LEFT, 0);
    chicken_put_edge(SIDE_RIGHT, 0);
    anim_addlives_timer = 0;
    anim_addlives = 0;
    state = ST_PLAYING;
}

/* Animation(time, delta): тот же порядок проверки, что в JS. */
static void animation(void)
{
    if (anim_broke) anim_broke_tick();
    if (anim_blink[0]) anim_blink_tick(0);
    if (anim_blink[1]) anim_blink_tick(1);
    if (anim_blink[2]) anim_blink_tick(2);
    if (anim_chicken) anim_chicken_tick();
    if (anim_addlives) anim_addlives_tick();
}


/* ----------------------------------------------------------------------- */
/*  Ход игры                                                               */
/* ----------------------------------------------------------------------- */

/* UpdateTicks: таймер тика копит delta*gameSpeed, заяц мигает раз в 5 с. */
static void update_ticks(void)
{
    game_timer += tick_inc;
    if (game_timer > TICK_LIMIT) {
        game_timer = 0;
        /* GameTick(): Turn(); CalcCurrentSpeed(); — второй вызов в оригинале
         * бросает результат, скорость меняется только в IncreaseScore. */
        turn();
    }

    rabbit_timer += FRAME_MS;
    if (rabbit_timer > RABBIT_MS) {
        rabbit_timer = 0;
        rabbit_visible = (unsigned char)(!rabbit_visible);
        rabbit_put(rabbit_visible);
    }
}

static void update(void)
{
    if (state == ST_PLAYING)
        update_ticks();

    animation();

    if (state == ST_LOOSE) {
        loose_timer += FRAME_MS;
        if (loose_timer > LOOSE_MS) {
            save_hi_score();
            to_menu();
        }
    }
}

/* InitializeGame(): всё, что делает оригинал, кроме цветов текстовых меток
 * меню (их у нас нет). */
static void initialise_game(void)
{
    clear_eggs_on_screen();
    digits_show(0);
    show_lives(6);

    eggs_needed = 1;
    groove_cursor = 0;
    previous_new_egg = 0;
    clear_new_eggs();

    life_count = 6;
    score = 0;
    rounds = 0;
    bonus200 = 0;
    bonus500 = 0;
    factor5 = 5;
    speed_reset();

    game_timer = 0;
    rabbit_timer = 0;
    loose_timer = 0;

    anim_broke = 0;
    anim_chicken = 0;
    anim_addlives = 0;
    anim_blink_stop();

    rabbit_visible = 1;
    rabbit_put(1);
    wolf_put(wolf_position);
}

/* ----------------------------------------------------------------------- */
/*  Музыка заставки                                                        */
/* ----------------------------------------------------------------------- */

/* Мелодия title.mid играет по кругу, пока игра не началась (пока мы в меню).
 * Пауза между повторами заложена в самих партитурах (хвост из L-пауз), поэтому
 * зацикливаем штатно: music_set_loop(1) — движок сам переставляет потоки на
 * начало по достижении MUS_END, ручной рестарт и счётчик выдержки не нужны. */
static void menu_music_start(void)
{
    music_set_data(&title_music_song);
    music_set_loop(1);
    music_start();
}

static void menu_music_stop(void)
{
    music_stop();
}


/* ----------------------------------------------------------------------- */
/*  Старт игры                                                             */
/* ----------------------------------------------------------------------- */

static void start_game(unsigned char type)
{
    game_type = type;
    menu_music_stop();            /* заставка кончилась — мелодия долой */

    /* Фон не перерисовывается: за время игры он не меняется, а распаковка
     * 24 КБ заставила бы ждать. Сбрасываются только сегменты и слоты. */
    screen_reset();
    /* Семя — число кадров, проведённых в меню: у ГПСЧ нет своего источника
     * энтропии, но момент нажатия клавиши всегда разный. */
    rnd_state = (idle_frames | 1u) * 25173u + 13831u;

    initialise_game();
    state = ST_PLAYING;
    draw_ui();
}

static void save_hi_score(void)
{
    unsigned int total = score + rounds * 1000u;

    if (total > hiscore[game_type])
        hiscore[game_type] = total;
}


/* ----------------------------------------------------------------------- */
/*  Меню и панель                                                          */
/* ----------------------------------------------------------------------- */

/* Шрифт 8×8 — свой кириллический (src/font.asm, генерит tools/gen_font.py):
 * коды латинских букв A..Z рисуют русские буквы-транслит (R→Р, P→П, ...),
 * поэтому строки в тексте ROM пишутся латиницей-транслитом, а на экране
 * выходят по-русски: "IGRA" -> ИГРА, "PAUZA" -> ПАУЗА, "KLAV" -> КЛАВ.
 *
 * Фон (tools/gen_assets.py) рисует на экране поле 256x176, сдвинутое на 28
 * строк вниз, панель с четырьмя круглыми кнопками по углам и логотипом
 * «Ну, погоди!» в середине; всё остальное в фоне чёрное и отдано тексту:
 *
 *      0..11   строка Ф-клавиш
 *    28..203   поле
 *   204..255   панель: круглые кнопки (светлый обод, красная середина,
 *              рядом чёрная стрелка к своему углу поля) и логотип:
 *              левая пара x 8..32, правая x 224..248, ряды y 216 и 240;
 *              логотип x 84..171
 *
 * Подписи клавиш ROM рисует текстом у внутреннего края кнопки — в чёрной
 * полосе между кнопкой и логотипом: draw_char обнуляет под знаком все
 * активные плоскости, кроме своей, и текст, вставший на кнопку или логотип,
 * съел бы их. Координаты согласованы с build_panel() в gen_assets.py:
 * левые подписи в колонках 5..9 (x 40..79), правые в 22..26 (x 176..215),
 * строки y 212 и 236 (центр кнопок 216/240 минус половина знака). */
/* ---------------------------- панель ----------------------------------- */

#define UI_MENU_Y   0        /* строка Ф-клавиш */

/* Подпись каждого action — 5 колонок текста у внутреннего края кнопки:
 * левые подписи в колонках 5..9, правые в 22..26 (см. build_panel()).
 * Строка y — центр соответствующего ряда кнопок (216/240) минус 4. */
static const unsigned char ui_key_col[4] = { 5, 5, 22, 22 };
static const unsigned char ui_key_y[4] = { 212, 236, 212, 236 };
/* Левые подписи прижаты к левому краю поля (к левой кнопке), правые —
 * к правому краю (к правой кнопке), чтобы короткое имя не отъезжало
 * от своей кнопки к центру. */
static const unsigned char ui_key_right[4] = { 0, 0, 1, 1 };

/* Названия клавиш. Строки 2..7 матрицы — печатные символы (в латинской
 * раскладке они и есть буквы), строки 0 и 1 подписаны руками.
 * В font_chars (lib/gfx/pr.asm) нет глифов '^', 'v', '/', '\\', '~' — их
 * приходится писать словами, иначе подпись выйдет пустой. ↖ — это Home,
 * на клавиатуре Вектора он и подписан косой стрелкой. */
static const char key_names0[8][5] = {
    "TAB", "PS", "VK", "ZAB", "<-", "VERH", "->", "VNIZ"
};
static const char key_names1[8][5] = {
    "DOM", "STR", "AP2", "F1", "F2", "F3", "F4", "F5"
};
static const char key_chars[48] = {
    '0', '1', '2', '3', '4', '5', '6', '7',
    '8', '9', ':', ';', ',', '=', '.', '/',
    '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G',
    'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
    'X', 'Y', 'Z', '[', '\\', ']', '~', ' '
};

/* По умолчанию — клавиши, которые на Векторе стоят рядом и попадают под
 * две руки: ↖ ← СТР →. Хранится не код, а адрес в матрице (строка и бит
 * колонки): коды Ф-клавиш и стрелок kbd_scan() отдаёт неразличимо с
 * другими клавишами, а нам нужен именно произвольный ключ матрицы. */
static unsigned char key_row[4] = { 1, 0, 1, 0 };
static unsigned char key_bit[4] = { 0x01, 0x10, 0x02, 0x40 };

static unsigned char remap;          /* 0 = выкл, иначе action + 1 */
static unsigned char blink_t;        /* счётчик кадров мигания */
static unsigned char blink_on;

static unsigned char bit_index(unsigned char bit)
{
    unsigned char i = 0;

    while ((bit & 1u) == 0) {
        bit >>= 1;
        i++;
    }
    return i;
}

static const char *key_name(unsigned char row, unsigned char bit)
{
    static char buf[2];
    unsigned char i = bit_index(bit);
    char c;

    if (row == 0)
        return key_names0[i];
    if (row == 1)
        return key_names1[i];
    c = key_chars[(unsigned char)((row - 2) * 8u + i)];
    if (c == '/')
        return "DROB";
    if (c == '\\')
        return "KOSA";
    if (c == '~')
        return "TILDA";
    if (c == ' ')            /* ПРОБЕЛ не должен выглядеть пустяком */
        return "PUSTO";
    buf[0] = c;
    buf[1] = 0;
    return buf;
}

/* Одна подпись: ровно 5 колонок, остаток затирается. s = 0 — стереть.
 * Короткое имя ставится у края поля: левые — у левого, правые — у правого
 * (ui_key_right), иначе подпись уедет от своей кнопки к центру. */
static void put_label(unsigned char action, const char *s)
{
    unsigned char col = ui_key_col[action];
    unsigned char y = ui_key_y[action];
    unsigned char right = ui_key_right[action];
    unsigned char i;
    unsigned char len = 0;
    unsigned char pad;
    char c;

    if (s != 0)
        while (len < 5 && s[len] != 0)
            len++;
    pad = (unsigned char)(5 - len);

    for (i = 0; i < 5; i++) {
        c = ' ';
        if (s != 0) {
            if (right) {
                if (i >= pad)
                    c = s[i - pad];
            } else if (i < len)
                c = s[i];
        }
        gfx_put_char((unsigned char)(col + i), y, c, 8);
    }
}

static void draw_keys(void)
{
    unsigned char p;

    for (p = 0; p < 4; p++)
        put_label(p, key_name(key_row[p], key_bit[p]));
}

/* Все три строки равной длины: при смене контекста от предыдущей надписи
 * не должно оставаться хвоста. */
static void draw_top_line(void)
{
    if (remap)
        gfx_print(0, UI_MENU_Y, "SMENA KLAVYW           F3-OTMENA", 8);
    else if (state == ST_MENU)
        gfx_print(0, UI_MENU_Y, "F1-IGRA A  F2-IGRA B  F3-KLAVIWI", 8);
    else
        gfx_print(0, UI_MENU_Y, "            AR2-VYHOD           ", 8);
}

/* Всё, что ROM дописывает поверх фона: строку Ф-клавиш и подписи клавиш у
 * кнопок. Логотип и сами кнопки уже в фоне. Рекорды на экран не выводятся
 * (hiscore[] ведётся внутренне). */
static void draw_ui(void)
{
    draw_top_line();
    draw_keys();
}

static void to_menu(void)
{
    state = ST_MENU;
    wolf_position = POS_LU;
    screen_reset();
    initialise_game();
    draw_ui();
    menu_music_start();           /* в меню играет мелодия заставки */
}


/* ----------------------------------------------------------------------- */
/*  Ввод                                                                   */
/* ----------------------------------------------------------------------- */

/* Строка 1 матрицы: СТР (0x02) АП2 (0x04) Ф1 (0x08) Ф2 (0x10) Ф3 (0x20).
 * kbd_scan() отдаёт только первую нажатую клавишу, а играть нужно двумя
 * руками и переставлять волка, не отпуская предыдущую кнопку, — поэтому
 * смотрим на снимок всей матрицы и снимаем фронты сами. */
#define ROW_FUNCS   1
#define BIT_ESC     0x04
#define BIT_F1      0x08
#define BIT_F2      0x10
#define BIT_F3      0x20

static unsigned char prev_rows[8];

/* Первая клавиша, опущенная с прошлого кадра. */
static unsigned char scan_front(unsigned char *row, unsigned char *bit)
{
    unsigned char i, fresh, j;

    for (i = 0; i < 8; i++) {
        fresh = (unsigned char)(kbd_rows[i] & ~prev_rows[i]);
        prev_rows[i] = kbd_rows[i];
        if (fresh == 0)
            continue;
        for (j = 0; j < 8; j++)
            if (fresh & (unsigned char)(1u << j))
                break;
        *row = i;
        *bit = (unsigned char)(1u << j);
        return 1;
    }
    return 0;
}

/* Назначить клавишу действию. Если она уже занята — меняемся местами,
 * иначе у нас появилось бы действие без клавиши. */
static void assign_key(unsigned char action, unsigned char row, unsigned char bit)
{
    unsigned char other;

    for (other = 0; other < 4; other++) {
        if (other == action)
            continue;
        if (key_row[other] == row && key_bit[other] == bit) {
            key_row[other] = key_row[action];
            key_bit[other] = key_bit[action];
        }
    }
    key_row[action] = row;
    key_bit[action] = bit;
}

/* Мигание подписи назначаемого действия — каждые ~0,3 с. */
static void blink_label(void)
{
    unsigned char action = (unsigned char)(remap - 1);

    blink_t++;
    if (blink_t < 16)
        return;
    blink_t = 0;
    blink_on = (unsigned char)!blink_on;
    if (blink_on)
        put_label(action, key_name(key_row[action], key_bit[action]));
    else
        put_label(action, 0);
}

static void input(void)
{
    unsigned char row, bit, p;

    kbd_scan();

    if (state == ST_MENU && remap == 0)
        idle_frames++;

    if (!scan_front(&row, &bit)) {
        if (remap)
            blink_label();
        return;
    }

    /* Ф3 — переназначение: игра встаёт на паузу, мигает подпись первого
     * действия, дальше четыре нажатия раскладывают клавиши по местам.
     * Второе нажатие Ф3 раньше четвёртого — отмена. */
    if (row == ROW_FUNCS && bit == BIT_F3) {
        remap = (unsigned char)(remap ? 0 : 1);
        blink_t = 0;
        blink_on = 1;
        draw_top_line();
        draw_keys();
        return;
    }

    if (remap) {
        assign_key((unsigned char)(remap - 1), row, bit);
        remap++;
        if (remap > 4) {
            remap = 0;
            draw_top_line();
        }
        draw_keys();
        return;
    }

    if (state == ST_MENU) {
        if (row == ROW_FUNCS && bit == BIT_F1) { start_game(GAME_A); return; }
        if (row == ROW_FUNCS && bit == BIT_F2) { start_game(GAME_B); return; }
        /* В заставке волк ходит по позициям: игра не идёт, но пользователь
         * может проверить, какие клавиши за что отвечают. */
    } else {
        /* АП2 в игре — то же, что кнопка Pause в оригинале: сохранить
         * рекорд и уйти в меню. Выхода из игры нет: операционной системы на
         * Векторе нет, заставка крутится вечно. */
        if (row == ROW_FUNCS && bit == BIT_ESC) {
            save_hi_score();
            to_menu();
            return;
        }
        /* Во время анимации и после проигрыша клавиши не помогают, как в
         * оригинале. */
        if (state != ST_PLAYING)
            return;
    }

    for (p = 0; p < 4; p++)
        if (row == key_row[p] && bit == key_bit[p]) {
            set_wolf_position(p);
            break;
        }
}


/* ----------------------------------------------------------------------- */
/*  main                                                                   */
/* ----------------------------------------------------------------------- */

int main(void)
{
    unsigned char i;

    idle_frames = 0;
    remap = 0;
    hiscore[GAME_A] = 0;
    hiscore[GAME_B] = 0;

    /* Первый снимок матрицы — чтобы задать исходное состояние: иначе фронт
     * на любой клавише (или на наводке в момент включения) выглядит как
     * нажатие и игра стартует сама. */
    kbd_scan();
    for (i = 0; i < 8; i++)
        prev_rows[i] = kbd_rows[i];

    drum_init();
    to_menu();

    for (;;) {
        v06_wait_frame();
        music_tick();
        drum_tick();
        /* В меню мелодия идёт по кругу сама (music_set_loop(1)); при старте
         * игры menu_music_stop() её гасит — ручной рестарт не нужен. */
        input();
        if (remap == 0)          /* во время назначения игра стоит */
            update();
    }
}
