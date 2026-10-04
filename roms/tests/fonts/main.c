/*
 * fonts/main.c — тест подключаемых шрифтов lib/gfx.
 *
 * Фаза 1. Режим экрана 256x256, 2 цвета (GFX_MODE_256_2, плоскость 0xE000).
 * На одном экране печатаем двумя шрифтами 8x8:
 *
 *   1. шрифт библиотеки по умолчанию (lib/gfx/fonts/default_8x8.inc,
 *      дескриптор gfx_font_8x8 из pr.asm);
 *   2. шрифт игры PUTUP ("Ну, погоди!"), putup_font.asm — глифы
 *      выгружены из блока глифов ROM (RUNTIME RAM 0x6000), кодировка
 *      источника KOI8-R.
 *
 * У PUTUP-цифр есть второй дескриптор, putup_digits: тот же шрифт, но в
 * режиме прямого индекса (chars = 0, диапазон 0x30..0x39). Он занимает
 * 80 байт без таблицы имён и проверяет границы двумя сравнениями, а коды
 * вне диапазона пропускает, ничего в клетку не пишет — на экране это
 * строка "123 ABC 456" поверх подложки из X.
 *
 * gfx_select_font() меняет текущий шрифт, дальше gfx_print/gfx_put_char
 * рисуют им. До первого вызова работает шрифт из ROM. Строчных букв в
 * шрифте PUTUP нет, поэтому везде верхний регистр; букв 'Ё' и 'Ч' в
 * выгруженном блоке тоже нет (их коды содержат другие данные), в
 * кириллических строках на их месте пробел.
 *
 * Фаза 2 (клавиша 5). Режим 512x256, 4 цвета: те же два режима шрифтов
 * для pr512.asm (16x8) и pr512t.asm (тонкий 4x8) — таблица имён и
 * прямой индекс. Данные цифр для него вырезаны из библиотечных шрифтов
 * (range_fonts.asm), так что строки «таблица» и «прямой индекс» обязаны
 * совпадать символ в символ там, где код внутри диапазона.
 *
 * ТАБ — переключать шрифт живой строки (фаза 1), 5 — режим 512x256,
 * АП2 (ESC) — выход.
 */

#include "v06.h"

/* Дескриптор шрифта PUTUP — метка _putup_font в putup_font.asm. */
extern const gfx_font_t putup_font;

/* Те же цифры 0x30..0x39 прямым индексом — метка _putup_digits. */
extern const gfx_font_t putup_digits;

/* Цифры прямым индексом для 512-рендеров — метки из range_fonts.asm. */
extern const gfx_font_t digits_16x8;
extern const gfx_font_t digits_thin;

/* 2 цвета: слот 0 — фон, слот 1 — передний план (плоскость E000). */
static const unsigned char pal2[2] = {
    V06_RGB(0, 0, 0),   /* 0: чёрный фон */
    V06_RGB(7, 7, 3),   /* 1: белый      */
};

/* В 256x256x2 черни = бит 0 цвета, он выбирает плоскость 0xE000. */
#define INK         1u

/* В 512x256x4 черни = оба бита цвета (E000/A000 + C000/8000). */
#define INK4        3u

/* 4 цвета: 0 — фон, дальше красный, зелёный и белый (как в scr_modes). */
static const unsigned char pal4[4] = {
    V06_RGB(0, 0, 0),   /* 0 */
    V06_RGB(7, 0, 0),   /* 1 */
    V06_RGB(0, 7, 0),   /* 2 */
    V06_RGB(7, 7, 3),   /* 3 */
};

/* Левая половина экрана — шрифт по умолчанию, правая — PUTUP. */
#define COL_LEFT    0
#define COL_RIGHT   16

#define ROWS        8           /* шаг строки в пикселях (глиф 8x8) */

/* ---------------------------------------------------------------
 * Строки в KOI8-R: sccz80 берёт байты литерала как есть, поэтому
 * кириллица записана восьмеричными экранизациями.
 * --------------------------------------------------------------- */

static const char koi_abv[]     = "\341\342\367\347\344\345\366\372\351"
                                  "\352\353\354\355\356\357\360";
                                  /* "АБВГДЕЖЗИЙКЛМНОП" */
static const char koi_rst[]     = "\362\363\364\365\346\350\343\040\373"
                                  "\375\377\371\370\374\340\361";
                                  /* "РСТУФХЦ ШЩЪЫЬЭЮЯ" (без 'Ч') */
static const char koi_nu[]      = "\056\356\365\054\040\360\357\347\357"
                                  "\344\351\041\056";
                                  /* ".НУ, ПОГОДИ!." */
static const char koi_vector[]  = "\367\345\353\364\357\362\040\060\066\343";
                                  /* "ВЕКТОР 06Ц" */
static const char koi_schrift[] = "\373\362\351\346\364\040\360\365\364"
                                  "\341\360";
                                  /* "ШРИФТ ПУТАП" */

/* Общий набор символов обеих гарнитур: не больше 16 колонок на строку. */
static const char alnum1[]      = "ABCDEFGHIJKLMNOP";
static const char alnum2[]      = "QRSTUVWXYZ012345";
static const char alnum3[]      = "6789-:().,?!@<>=";
static const char alnum4[]      = "&#*$+%;[]_";

/* Живая строка: одинаковые символы в двух гарнитурах видно рядом. */
static const char live_text[]   = "VECTOR-06C 12345";

/* 16 пробелов: очистить строку перед перерисовкой. В шрифте из ROM
 * пробел есть, поэтому глиф 0 затирает клетку на месте прежнего символа. */
static const char blanks16[]    = "                ";

/* Подложка под строку прямого индекса: где шрифт символ пропустит,
 * останется X. */
static const char xs11[]        = "XXXXXXXXXXX";

/* Строка для шрифта цифр: '1'-'9' внутри диапазона 0x30..0x39,
 * буквы и пробелы — вне. */
static const char range_text[]  = "123 ABC 456";

/* То же для 512-фазы: 21 символ — цифры в диапазоне, остальное вне. */
static const char range_512[]   = "0123456789 ABCDEFGHIJ";
static const char xs21[]        = "XXXXXXXXXXXXXXXXXXXXX";

/* Тонкий шрифт 4x8: тот же приём, но колонок вдвое больше. */
static const char range_thin[]  = "0123456789 ABCDEFGHIJKLMNOPQRSTUV";
static const char xs32[]        = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX";

/* ---------------------------------------------------------------
 *  Вспомогательные функции
 * --------------------------------------------------------------- */

/* Одна строка заданным шрифтом. col — номер столбца 0..31,
 * row — номер строки, y = row * 8. */
static void line(unsigned char col, unsigned char row, const char *s,
                 const gfx_font_t *font)
{
    gfx_select_font(font);
    gfx_print(col, row * ROWS, s, INK);
}

/* Строка, где шрифты чередуются посимвольно: чётные символы — из ROM,
 * нечётные — PUTUP. Показывает, что выбор шрифта читается на каждый
 * символ, а не один раз на строку. */
static void line_mixed(unsigned char col, unsigned char row, const char *s)
{
    unsigned char i;

    for (i = 0; s[i] != '\0'; i++) {
        gfx_select_font((i & 1) ? &putup_font : &gfx_font_8x8);
        gfx_put_char(col + i, row * ROWS, s[i], INK);
    }
}

/* Живая строка + подпись текущего шрифта. */
static void draw_live(const gfx_font_t *font)
{
    if (font == &putup_font)
        line(0, 24, "FONT: PUTUP  ", &gfx_font_8x8);
    else if (font == &putup_digits)
        line(0, 24, "FONT: DIGITS ", &gfx_font_8x8);
    else
        line(0, 24, "FONT: DEFAULT", &gfx_font_8x8);

    /* Шрифт прямого индекса пропущенные клетки не затирает, так что
     * строку подчищаем заранее — иначе осталась бы прежняя гарнитура. */
    line(0, 25, blanks16, &gfx_font_8x8);
    line(0, 25, live_text, font);
}

/* ---------------------------------------------------------------
 *  Статическая часть экрана
 * --------------------------------------------------------------- */

static void draw_screen(void)
{
    /* Заголовок. */
    line(0,  0, "VECTOR-06C FONT TEST",     &gfx_font_8x8);
    line(0,  1, "MODE 256X256 2 COLORS",    &gfx_font_8x8);
    line(0,  2, "--------------------------------", &gfx_font_8x8);

    /* Две колонки: слева шрифт из ROM, справа PUTUP. */
    line(COL_LEFT,  3, "DEFAULT FONT", &gfx_font_8x8);
    line(COL_RIGHT, 3, "PUTUP FONT",   &putup_font);

    line(COL_LEFT,  4, alnum1, &gfx_font_8x8);
    line(COL_RIGHT, 4, alnum1, &putup_font);
    line(COL_LEFT,  5, alnum2, &gfx_font_8x8);
    line(COL_RIGHT, 5, alnum2, &putup_font);
    line(COL_LEFT,  6, alnum3, &gfx_font_8x8);
    line(COL_RIGHT, 6, alnum3, &putup_font);
    line(COL_LEFT,  7, alnum4, &gfx_font_8x8);
    line(COL_RIGHT, 7, alnum4, &putup_font);

    /* Кириллица есть только в PUTUP (источник — KOI8-R). */
    line(0,  9,  "PUTUP CYRILLIC, KOI8-R", &gfx_font_8x8);
    line(0,  10, koi_abv,                  &putup_font);
    line(0,  11, koi_rst,                  &putup_font);
    line(0,  12, koi_nu,                   &putup_font);
    line(0,  13, koi_vector,               &putup_font);
    line(0,  14, koi_schrift,              &putup_font);

    /* Смешение шрифтов внутри одной строки. */
    line(0,  16, "MIXED FONTS, ONE LINE",  &gfx_font_8x8);
    line_mixed(0, 17, "VECTOR-06C PUTUP");

    /* Неизвестный символ рисуется глифом 0 (пробел): в шрифте из ROM
     * кириллицы нет, от строки остаются только точки по краям. */
    line(0,  19, "DEFAULT: NO CYRILLIC, GLYPH 0", &gfx_font_8x8);
    line(0,  20, koi_nu,                          &gfx_font_8x8);
    line(0,  21, "PUTUP: SAME LINE",              &gfx_font_8x8);
    line(0,  22, koi_nu,                          &putup_font);

    /* Интерактивная часть. */
    line(0,  18, "5 - MODE 512X256  ESC - EXIT", &gfx_font_8x8);
    line(0,  23, "TAB - CHANGE FONT BELOW", &gfx_font_8x8);

    /* Шрифт прямого индекса: цифры 0x30..0x39, коды вне диапазона
     * пропускаются без записи в VRAM, поэтому под ними видны X
     * подложки. */
    line(0,  26, "DIRECT INDEX 0X30-0X39", &gfx_font_8x8);
    line(0,  27, xs11,                     &putup_font);
    line(0,  27, range_text,               &putup_digits);
}

/* ---------------------------------------------------------------
 *  Фаза 2: режим 512x256, шрифты 16x8 (pr512.asm) и 4x8 (pr512t.asm)
 * --------------------------------------------------------------- */

/* Строка 16x8: col — колонка 0..31, row — строка (y = row * 8). */
static void line512(unsigned char col, unsigned char row, const char *s,
                    const gfx_font_t *font)
{
    gfx_select_font_512(font);
    gfx_print_512(col, row * ROWS, s, INK4);
}

/* Строка тонким 4x8: col — колонка 0..63. */
static void line512t(unsigned char col, unsigned char row, const char *s,
                     const gfx_font_t *font)
{
    gfx_select_font_512t(font);
    gfx_print_512t(col, row * ROWS, s, INK4);
}

static void draw_screen_512(void)
{
    gfx_set_mode(GFX_MODE_512_4);
    gfx_set_palette(pal4);
    gfx_clear(0);

    /* 16x8: сначала таблица имён (шрифт из ROM), потом те же символы
     * шрифтом прямого индекса поверх подложки из X: цифры встанут на
     * место X, буквы и пробелы вне диапазона оставят их нетронутыми. */
    line512(1, 0, "MODE 512X256 4 COLORS", &gfx_font_16x8);

    line512(1, 2,  "16X8, TABLE NAMES",  &gfx_font_16x8);
    line512(1, 3,  range_512,            &gfx_font_16x8);

    line512(1, 5,  "16X8, DIRECT INDEX", &gfx_font_16x8);
    line512(1, 6,  xs21,                 &gfx_font_16x8);
    line512(1, 6,  range_512,            &digits_16x8);

    /* Тонкий 4x8 тем же приёмом. */
    line512t(1, 9,  "THIN 4X8, TABLE NAMES",  &gfx_font_thin);
    line512t(1, 10, range_thin,               &gfx_font_thin);

    line512t(1, 12, "THIN 4X8, DIRECT INDEX", &gfx_font_thin);
    line512t(1, 13, xs32,                     &gfx_font_thin);
    line512t(1, 13, range_thin,               &digits_thin);

    line512(1, 16, "ESC - EXIT",           &gfx_font_16x8);
}

/* ---------------------------------------------------------------
 *  main
 * --------------------------------------------------------------- */

int main(void)
{
    const gfx_font_t *live_font;
    unsigned char prev;
    unsigned char key;
    unsigned char phase;        /* 0 — экран 256x256, 1 — 512x256 */

    live_font = &putup_font;
    phase = 0;

    gfx_set_mode(GFX_MODE_256_2);
    gfx_set_palette(pal2);
    gfx_clear(0);

    draw_screen();
    draw_live(live_font);

    prev = kbd_scan();

    for (;;) {
        v06_wait_frame();

        key = kbd_scan();
        if (key == 0) {
            prev = 0;
            continue;
        }
        if (key == prev)
            continue;

        prev = key;

        if (key == KBD_KEY_ESC)
            break;

        /* Клавиша 5 переводит в режим 512x256: там те же два режима
         * шрифтов, но другими рендерами. */
        if (phase == 0 && key == '5') {
            phase = 1;
            draw_screen_512();
            continue;
        }

        if (key == KBD_KEY_TAB) {
            /* Три шрифта по кругу: ROM -> PUTUP -> цифры прямым индексом. */
            if (live_font == &gfx_font_8x8)
                live_font = &putup_font;
            else if (live_font == &putup_font)
                live_font = &putup_digits;
            else
                live_font = &gfx_font_8x8;

            draw_live(live_font);
        }
    }

    gfx_select_font(0);
    gfx_select_font_512(0);
    gfx_select_font_512t(0);
    gfx_clear(0);

    return 0;
}
