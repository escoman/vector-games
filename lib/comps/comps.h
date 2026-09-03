/*
 * comps.h — UI-компоненты для Вектора-06Ц.
 *
 * Базовый интерфейс компонента, контроллер с навигацией TAB,
 * переиспользуемые элементы управления (edit, textarea).
 * Режим 256x256x2, монохромный, графический шрифт 8x8.
 */

#ifndef COMPS_H
#define COMPS_H

/* -------------------- Базовый интерфейс компонента ----------------- */

/* Таблица виртуальных методов. Каждый компонент встраивает
 * component_t первым полем своей структуры ("наследование"). */
typedef struct component_s {
    void (*draw)(struct component_s *c, unsigned char active);
    void (*draw_content)(struct component_s *c);
    unsigned char (*handle_key)(struct component_s *c, unsigned char key);
    void (*focus_toggle)(struct component_s *c);  /* инверсия label */
} component_t;

/* -------------------- Контроллер компонентов ----------------------- */

typedef unsigned char (*key_handler_t)(unsigned char key);
/* Внешний обработчик клавиш. Возвращает:
 *   0 — не наш ключ, передать компоненту;
 *   1 — обработан, продолжаем цикл;
 *  >1 — код выхода (controller_run возвращает это значение). */

#define COMPS_MAX 8

typedef struct {
    component_t *items[COMPS_MAX];
    unsigned char count;
    unsigned char active;
    key_handler_t on_key;   /* 0 = нет внешнего обработчика */
} controller_t;

void controller_init(controller_t *ctrl);
void controller_add(controller_t *ctrl, component_t *comp);

/* Главный цикл: TAB — переключение, ESC — выход (возврат 27),
 * on_key — перехват спецклавиш, остальное — активному компоненту.
 * Возвращает код клавиши, вызвавшей выход. */
unsigned char controller_run(controller_t *ctrl);

/* ----------------------- Edit / Textarea --------------------------- */

/* Поле ввода с рамкой и заголовком.
 * Два режима:
 *   lines == 1 → edit (однострочный, горизонтальная прокрутка)
 *   lines > 1  → textarea (многострочный, перенос по ширине)
 * Данные хранятся во внешнем буфере (caller owns memory). */
typedef struct {
    component_t base;           /* MUST BE FIRST */
    char *buf;                  /* внешний буфер (0-термин.) */
    unsigned int max_len;       /* макс. длина строки (без \0) */
    unsigned char cur_col;      /* плоская позиция курсора (0..strlen) */
    unsigned char scroll;       /* edit: первый видимый столбец */
    unsigned char width;        /* ширина области (символов, без рамки) */
    unsigned char lines;        /* 1 = edit, >1 = textarea */
    unsigned char vscroll;      /* textarea: первая видимая строка */
    unsigned char x, y;         /* позиция label (col, pixel row) */
    const char *label;          /* заголовок поля */
} textarea_t;

/* Edit — однострочное поле ввода (lines=1).
 * Горизонтальная прокрутка, стрелки ←/→. */
void edit_init(textarea_t *ta, char *buf, unsigned int max_len,
               unsigned char width, unsigned char x, unsigned char y,
               const char *label);

/* Textarea — многострочное поле ввода с переносом по ширине.
 * lines — количество видимых строк. Стрелки ←/→/↑/↓. */
void textarea_init(textarea_t *ta, char *buf, unsigned int max_len,
                   unsigned char width, unsigned char lines,
                   unsigned char x, unsigned char y,
                   const char *label);

/* Реализации интерфейса component_t (вызываются через контроллер). */
void textarea_draw(component_t *c, unsigned char active);
void textarea_draw_content(component_t *c);
unsigned char textarea_handle_key(component_t *c, unsigned char key);
void textarea_focus_toggle(component_t *c);

#endif /* COMPS_H */
