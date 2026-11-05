/*
 * colors.c — тест цвета бордюра и экрана Вектора-06Ц.
 *
 * Назначение: проверка видеовыхода на ч/б телевизоре с осциллографом —
 * замер уровней сигнала на каждом пине RGB. Экран и бордюр становятся
 * ОДНИМ цветом (чёрный / красный / зелёный / синий, 100%), в середине
 * экрана две надписи с названием цвета: белым и чёрным — по ним видно
 * размах уровней (чёрный = гасящий/синхроимпульс, белый = максимальный).
 *
 * Управление цветом — ТОЛЬКО палитрой, никакой заливки «цветом»:
 *   - VRAM во всех состояниях залита нулями: каждый пиксель = индекс 0;
 *   - слот 0 палитры = текущий цвет фона;
 *   - бордюр — индекс палитры в битах 0-3 порта 0x02 (PB); индекс 0
 *     стоит в ПИА после сброса и запись управляющего слова (его делает
 *     kbd_scan) тоже сбрасывает PB в 0 — бордюр всегда смотрит в слот 0,
 *     порт 0x02 не трогаем вовсе;
 *   - смена цвета = одна перезагрузка палитры (порт 0x0C).
 * В 16-цветном режиме байт VRAM = 8 пикселей (бит = пиксель), индекс
 * собирается по одноимённым битам 4 плоскостей, поэтому заливка экран
 * «числом цвета» (gfx_clear(1)) дала бы не сплошной цвет, а полосаты
 * узор — заливаем только нули.
 *
 * Палитра: слот 0 = фон (меняется), слот 1 = чёрный (текст),
 * слот 15 = белый (текст). Режим 256x256, 16 цветов.
 *
 * Управление: любая клавиша — следующий цвет (0 → 1 → 2 → 3 → 0).
 */

#include <string.h>
#include "v06.h"

#define SLOT_BG      0u    /* фон экрана и бордюр: индекс 0 всегда     */
#define SLOT_BLACK   1u    /* чёрный текст                             */
#define SLOT_WHITE  15u    /* белый текст                              */

/* Цвета состояний в палитровом формате RRRGGGBB (макрос V06_RGB).
 * 100% канал = максимум разрядов своего цвета: R/G — 7, B — 3. */
#define RGB_BLACK V06_RGB(0, 0, 0)
#define RGB_RED   V06_RGB(7, 0, 0)
#define RGB_GREEN V06_RGB(0, 7, 0)
#define RGB_BLUE  V06_RGB(0, 0, 3)
#define RGB_WHITE V06_RGB(7, 7, 3)

/* Рабочая палитра: слот 0 перезаписывается под текущий цвет. */
static unsigned char palette[16] = {
    /* 0 */ RGB_BLACK,   /* фон — меняется show_color() */
    /* 1 */ RGB_BLACK,   /* чёрный текст                */
    /* 2 */ RGB_BLACK,
    /* 3 */ RGB_BLACK,
    /* 4 */ RGB_BLACK,
    /* 5 */ RGB_BLACK,
    /* 6 */ RGB_BLACK,
    /* 7 */ RGB_BLACK,
    /* 8 */ RGB_BLACK,
    /* 9 */ RGB_BLACK,
    /*10 */ RGB_BLACK,
    /*11 */ RGB_BLACK,
    /*12 */ RGB_BLACK,
    /*13 */ RGB_BLACK,
    /*14 */ RGB_BLACK,
    /*15 */ RGB_WHITE,   /* белый текст */
};

/* Состояния теста: цвет слота 0 + надпись. */
static const unsigned char bg_color[4] =
    { RGB_BLACK, RGB_RED, RGB_GREEN, RGB_BLUE };
static const char *color_name[4] =
    { "BLACK", "RED", "GREEN", "BLUE" };

/* y-координаты двух центральных надписей (пиксели, шрифт 8x8):
 * блок из двух строк с межстрочным шагом 24 пикселя по центру 256. */
#define LABEL_Y_WHITE  112u
#define LABEL_Y_BLACK  136u
#define FOOTER_Y       240u

/* Печать строки по центру экрана: x — столбец VRAM (0..31). */
static void print_centered(unsigned char y, const char *s,
                           unsigned char color)
{
    unsigned char x = (unsigned char)((32u - (unsigned char)strlen(s)) / 2u);
    gfx_print(x, y, s, color);
}

/* Показать состояние: фон только палитрой, поверх — текст. */
static void show_color(unsigned char state)
{
    palette[SLOT_BG] = bg_color[state];

    gfx_set_palette(palette);  /* слот 0 = новый цвет фона/бордюра */
    gfx_clear(0);              /* VRAM = индекс 0 → везде слот 0   */

    print_centered(LABEL_Y_WHITE, color_name[state], SLOT_WHITE);
    print_centered(LABEL_Y_BLACK, color_name[state], SLOT_BLACK);

    print_centered(FOOTER_Y, "PRESS ANY KEY - NEXT COLOR", SLOT_WHITE);
}

/* Ожидание нажатия любой клавиши (фронт, как в тесте cls). */
static void wait_key_press(void)
{
    unsigned char prev = kbd_scan();
    for (;;) {
        unsigned char key;
        v06_wait_frame();
        key = kbd_scan();
        if (key != 0 && key != prev)
            return;
        prev = key;
    }
}

int main(void)
{
    unsigned char state = 0;

    gfx_set_mode(GFX_MODE_256_16);
    /* Бордюр не ставим: PB=0 после сброса ПИА → индекс 0 = слот фона. */

    for (;;) {
        show_color(state);
        wait_key_press();
        state = (unsigned char)((state + 1u) & 3u);
    }
}
