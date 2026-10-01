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
    void (*draw_cursor)(struct component_s *c);  /* только курсор */
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

/* Главный цикл: ТАБ (KBD_KEY_TAB) — переключение, АП2 (KBD_KEY_ESC) —
 * выход (возвращает KBD_KEY_ESC), on_key — перехват спецклавиш
 * (KBD_KEY_F1.. из v06.h), остальное — активному компоненту.
 * Возвращает код клавиши, вызвавшей выход. */
unsigned char controller_run(controller_t *ctrl);

/* ----------------------- Edit / Textarea --------------------------- */

/* Поле ввода с рамкой и заголовком.
 * Два режима:
 *   lines == 1 → edit (однострочный, горизонтальная прокрутка)
 *   lines > 1  → textarea (многострочный, перенос по ширине)
 * Данные хранятся во внешнем буфере (caller owns memory).
 *
 * Позиции и длины — 16 битами: буфер может быть длиннее 255 символов.
 * Байтовые счётчики раньше давали длину по модулю 256 (256 символов —
 * «пустое» поле), курсор не доставал за 255-ю позицию, а охранка
 * `len < max_len` переставала работать и затирала терминатор. Геометрия
 * (width, lines, x, y) остаётся байтовой — она ограничена экраном.
 *
 * Строки текста идут с шагом 10 пикселей (не 8): 8 рядов глифа, ряд
 * курсора под ним и пустой ряд до следующей строки — см. textarea_init. */
typedef struct {
    component_t base;           /* MUST BE FIRST */
    char *buf;                  /* внешний буфер (0-термин.) */
    unsigned int max_len;       /* макс. длина строки (без \0) */
    unsigned int cur_col;       /* плоская позиция курсора (0..strlen) */
    unsigned int scroll;        /* edit: первый видимый столбец */
    unsigned char width;        /* ширина области (символов, без рамки) */
    unsigned char lines;        /* 1 = edit, >1 = textarea */
    unsigned int vscroll;       /* textarea: первая видимая строка */
    unsigned char x, y;         /* позиция label (col, pixel row) */
    const char *label;          /* заголовок поля */
} textarea_t;

/* Edit — однострочное поле ввода (lines=1).
 * Горизонтальная прокрутка, стрелки ←/→. */
void edit_init(textarea_t *ta, char *buf, unsigned int max_len,
               unsigned char width, unsigned char x, unsigned char y,
               const char *label);

/* Textarea — многострочное поле ввода с переносом по ширине.
 * lines — количество видимых строк. Стрелки ←/→/↑/↓.
 *
 * Раскладка по высоте (от ta->y — верх строки метки, всё в пикселях):
 *   ta->y            метка (её инверсия захватывает ряд на 1 выше)
 *   ta->y+10         верхняя линия рамки
 *   ta->y+14+k*10    k-я строка текста: её глиф занимает ряды +0..+7,
 *                    +8 — курсор, +9 пустой, +10 — следующая строка
 *   ta->y+25+(lines-1)*10   нижняя линия рамки
 * То есть поле занимает 25 + (lines-1)*10 строк: у edit (lines=1) это 25,
 * как и раньше; у textarea раньше было 17+lines*8 — при шаге 10 поле
 * вырастает на 2 ряда на каждую лишнюю строку, при расстановке
 * компонентов по экрану это учитывай.
 *
 * Содержимое буфера init не трогает: буфер принадлежит вызывающему и
 * может содержать готовый текст — компонент навешивается на него как на
 * данные (повторная инициализация тем же буфером тоже законна). Но
 * буфер обязан быть законченной 0-строкой: с мусором в памяти компонент
 * начнёт печатать и править мусор. Курсор после init — в начале текста.
 */
void textarea_init(textarea_t *ta, char *buf, unsigned int max_len,
                   unsigned char width, unsigned char lines,
                   unsigned char x, unsigned char y,
                   const char *label);

/* Реализации интерфейса component_t (вызываются через контроллер). */
void textarea_draw(component_t *c, unsigned char active);
void textarea_draw_content(component_t *c);
void textarea_draw_cursor(component_t *c);
unsigned char textarea_handle_key(component_t *c, unsigned char key);
void textarea_focus_toggle(component_t *c);

#endif /* COMPS_H */
