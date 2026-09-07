/*
 * screens.h — общие объявления экранных модулей.
 */
#ifndef SCREENS_H
#define SCREENS_H

#include "v06.h"

/* Инициализация экрана: режим 256x256x2, палитра, очистка. */
void init_screen(void);

/* Ожидание следующего кадра 50 Гц. */
void wait_frame(void);

/* Горизонтальный разделитель из '-' на строке y (в пикселях). */
void draw_separator(unsigned char y);

/* Инверсия символов в режиме 256x256x2 (плоскость 0xE000). */
void invert_chars(unsigned char col, unsigned char row,
                  unsigned char count);

/* Проигрывание: старт/стоп/соло. */
void playback_start(void);
void playback_stop(void);
void playback_solo(unsigned char ch);

/* Экраны — каждый содержит свой главный цикл. */
void screen_about(void);
void screen_help(void);
void screen_drums(void);
void screen_editor(unsigned char channel, char *score_text[4]);

#endif
