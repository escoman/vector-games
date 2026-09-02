/*
 * editor.h — линейный текстовый редактор для .mus текста.
 *
 * Предоставляет буфер строк фиксированной длины, навигацию,
 * вставку/удаление символов и отрисовку через graph_print().
 * Строки до 127 символов; на экране (32 столбца) — визуальный перенос.
 * Используется в редакторе партитур композитора.
 */

#ifndef EDITOR_H
#define EDITOR_H

/* Максимальные размеры буфера редактора */
#define EDITOR_MAX_LINES  32
#define EDITOR_MAX_COLS   128    /* длинная строка; на экране 31 символ,
                                   остальное — визуальный перенос */

/* Состояние текстового редактора */
typedef struct {
    char lines[EDITOR_MAX_LINES][EDITOR_MAX_COLS];
    unsigned char num_lines;      /* число строк (минимум 1) */
    unsigned char cur_line;       /* курсор: строка (0..num_lines-1) */
    unsigned char cur_col;        /* курсор: столбец (0..strlen) */
    unsigned char scroll;         /* первая видимая строка */
    unsigned char visible;        /* видимых строк на экране */
} editor_t;

/* Инициализация редактора (пустой буфер, 1 пустая строка) */
void editor_init(editor_t *ed);

/* Загрузка текста из строки с \n-разделителями */
void editor_load(editor_t *ed, const char *text);

/* Сохранение текста в буфер (с \n, 0-терминатор). buf_size — размер. */
void editor_save(editor_t *ed, char *buf, unsigned int buf_size);

/* Отрисовка видимой области. x,y — знаковые координаты (0..31, 0..31).
 * color — цвет текста; курсор — инвертированный. */
void editor_draw(editor_t *ed, unsigned char x, unsigned char y,
                 unsigned char color);

/* Обработка нажатия клавиши (код kbd_scan).
 * Возвращает: 0 — продолжить работу, 1 — выход (ESC). */
unsigned char editor_handle_key(editor_t *ed, unsigned char key);

#endif /* EDITOR_H */
