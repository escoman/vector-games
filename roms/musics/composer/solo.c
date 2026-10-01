/*
 * solo.c — экран соло-редактора партитуры одного канала (Ф4).
 *
 * Отдельный экран в духе help.c и drums.c: сам рисует свой заголовок,
 * сам создаёт поле и контроллер компонентов, сам крутит свой цикл.
 * АП2 — выход, управление возвращается главному экрану.
 *
 * Партитура передаётся указателем: textarea навешивается прямо на буфер
 * канала (содержимое буфера инициализация не трогает), так что
 * редактирование идёт на месте и никакого копирования текста нет.
 */

#include "v06.h"
#include "comps.h"
#include "screens.h"

/* Раскладка: метка канала в строке 20, поле 30 колонок на 9 строк —
 * 270 позиций, весь буфер канала (255 символов) виден целиком,
 * прокрутки нет. Нижняя рамка на 20+25+8*10 = 125, выше подвала. */
#define SOLO_X      0
#define SOLO_Y      24
#define SOLO_W      30
#define SOLO_LINES  20

static textarea_t solo_field;
static controller_t solo_ctrl;
static unsigned char solo_ch;

/* Заголовок соло-экрана. Вызывается с чёрной палитрой (begin_init_screen),
 * палитру обратно возвращает paint_solo() — когда дорисовано поле. */
static void chrome_solo(void)
{
    begin_init_screen();
    gfx_print(0, HDR_Y, "F2-PLAY F3-SOLO AP2-RETURN", 1);

    /* Экран свежий — подписи чистые, остаётся подсветить ту, что
     * соответствует играющему режиму. */
    if (play_mode == PLAY_ONE)
        play_label(8, PLAY_LBL_N, 1);
    else if (play_mode == PLAY_ALL)
        play_label(0, PLAY_LBL_N, 1);
}

static void paint_solo(void)
{
    chrome_solo();
    solo_field.base.draw((component_t *)&solo_field, 1);
    end_init_screen();
}

/* Результат переключения проигрывания: подсветить подпись включившегося
 * режима, погасить прежнюю при остановке; а если парсер залил экран под
 * своё сообщение — держать его до АП2. */
static void show_result(unsigned char r)
{
    if (r == PLAY_ERROR) {
        kbd_wait_key(KBD_KEY_ESC);
        paint_solo();
        return;
    }
    if (r == PLAY_NONE) {
        play_label_off();
        return;
    }
    if (r == PLAY_ONE)
        play_label(8, PLAY_LBL_N, 1);
    else
        play_label(0, PLAY_LBL_N, 1);
}

static unsigned char solo_key(unsigned char key)
{
    if (key == KBD_KEY_F2) {                  /* играть/стоп все каналы */
        show_result(playback_toggle(PLAY_ALL, 0));
        return 1;
    }
    if (key == KBD_KEY_F3) {                  /* играть только этот голос */
        /* Маску сбрасывает music_stop, поэтому следующая Ф2 снова
         * играет всё. */
        show_result(playback_toggle(PLAY_ONE, solo_ch));
        return 1;
    }
    return 0;
}

unsigned int screen_solo(unsigned char ch, char *buf, unsigned int max_len,
                         const char *label)
{
    solo_ch = ch;

    /* Компонент на буфер канала: текст редактор видит и правит на месте.
     * Курсор начинается с нуля — так он гарантированно внутри строки,
     * даже если в главном поле он остался за конец укоротившегося текста. */
    textarea_init(&solo_field, buf, max_len, SOLO_W, SOLO_LINES,
                  SOLO_X, SOLO_Y, label);

    /* Экран рисуем целиком сами: поле дорисовывается до возврата
     * рабочей палитры, чтобы процесс отрисовки не был виден. Контроллер
     * при входе нарисует то же поле ещё раз — теми же символами. */
    paint_solo();

    controller_init(&solo_ctrl);
    controller_add(&solo_ctrl, (component_t *)&solo_field);
    solo_ctrl.on_key = solo_key;
    controller_run(&solo_ctrl);              /* АП2 — выход */

    return solo_field.cur_col;
}
