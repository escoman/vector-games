/*
 * screens.h — общие объявления экранных модулей (about, help, drums).
 */
#ifndef SCREENS_H
#define SCREENS_H

typedef enum {
    SCREEN_MAIN,
    SCREEN_EDIT,
    SCREEN_HELP,
    SCREEN_DRUMS,
    SCREEN_ABOUT
} screen_t;

/* Инициализация экрана: режим 256x256x2, палитра, очистка. */
void init_screen(void);

/* Отрисовка экранов. */
void draw_about(void);
void draw_help(void);
void draw_drums(void);

/* Обработка клавиш на экране ударных.
 * Возвращает 1 — вернуться на главный экран, 0 — остаться. */
unsigned char drums_handle_key(unsigned char key);

#endif
