/*
 * textarea.c — компонент поля ввода для Вектора-06Ц.
 *
 * Два режима в одном компоненте:
 *   lines == 1 → edit (однострочный, горизонтальная прокрутка)
 *   lines > 1  → textarea (многострочный, перенос по ширине)
 *
 * Внешний буфер, навигация стрелками, вставка/удаление символов.
 * Рамка и заголовок (label). Курсор — символ '_' без инверсии.
 */

#include "comps.h"
#include "v06.h"
#include <string.h>

/* Инверсия символов в режиме 256x256x2 (плоскость 0xE000).
 * Инвертирует 9 строк: 1 выше + 8 глифа — целостная инверсия. */
static void invert_chars(unsigned char col, unsigned char row,
                         unsigned char count)
{
    unsigned char c, r;
    volatile unsigned char *p;
    for (c = 0; c < count; c++) {
        p = (volatile unsigned char *)(0xE000 + (unsigned int)(col + c) * 256
                                       + (255 - row));
        for (r = 0; r < 9; r++) {
            *p ^= 0xFF;
            p--;
        }
    }
}

/* Длина строки (без \0) */
static unsigned char str_len(const char *s)
{
    unsigned char n = 0;
    while (*s++) n++;
    return n;
}

/* Приведение к верхнему регистру */
static char to_upper(char ch)
{
    if (ch >= 'a' && ch <= 'z')
        return ch - 32;
    return ch;
}

/* Длина label (для инверсии) */
static unsigned char label_len(const char *s)
{
    unsigned char n = 0;
    while (*s++) n++;
    return n;
}

/* Рисует маленький блок-курсор (2 нижних пикселя) в позиции col
 * относительно строки текста text_row. Блок на 1 пиксель ниже текста. */
static void draw_cursor(unsigned char col, unsigned char text_row)
{
    unsigned int addr = 0xE000 + (unsigned int)col * 256
                        + (255 - (text_row + 9));
    volatile unsigned char *p = (volatile unsigned char *)addr;
    p[0] = 0xFF;
    p[1] = 0xFF;
}

/* Очищает строку курсора (2 пикселя) по ширине контента */
static void clear_cursor_row(unsigned char x, unsigned char width,
                             unsigned char text_row)
{
    unsigned char c;
    for (c = 0; c <= width + 1; c++) {
        unsigned int addr = 0xE000 + (unsigned int)(x + c) * 256
                            + (255 - (text_row + 9));
        volatile unsigned char *p = (volatile unsigned char *)addr;
        p[0] = 0x00;
        p[1] = 0x00;
    }
}

/* Корректировка прокрутки: удерживать курсор в видимой области */
static void adjust_scroll(textarea_t *ta)
{
    if (ta->lines <= 1) {
        /* Edit: горизонтальная прокрутка */
        if (ta->cur_col < ta->scroll)
            ta->scroll = ta->cur_col;
        if (ta->cur_col >= ta->scroll + ta->width)
            ta->scroll = ta->cur_col - ta->width + 1;
    } else {
        /* Textarea: вертикальная прокрутка */
        unsigned char cur_line = ta->cur_col / ta->width;
        if (cur_line < ta->vscroll)
            ta->vscroll = cur_line;
        if (cur_line >= ta->vscroll + ta->lines)
            ta->vscroll = cur_line - ta->lines + 1;
    }
}

/* ------------------------- Публичные функции ------------------------- */

void edit_init(textarea_t *ta, char *buf, unsigned int max_len,
               unsigned char width, unsigned char x, unsigned char y,
               const char *label)
{
    textarea_init(ta, buf, max_len, width, 1, x, y, label);
}

void textarea_init(textarea_t *ta, char *buf, unsigned int max_len,
                   unsigned char width, unsigned char lines,
                   unsigned char x, unsigned char y,
                   const char *label)
{
    ta->base.draw = textarea_draw;
    ta->base.draw_content = textarea_draw_content;
    ta->base.handle_key = textarea_handle_key;
    ta->base.focus_toggle = textarea_focus_toggle;
    ta->buf = buf;
    ta->max_len = max_len;
    ta->cur_col = 0;
    ta->scroll = 0;
    ta->width = width;
    ta->lines = lines;
    ta->vscroll = 0;
    ta->x = x;
    ta->y = y;
    ta->label = label;
    if (buf && max_len > 0)
        buf[0] = 0;
}

void textarea_draw(component_t *c, unsigned char active)
{
    textarea_t *ta = (textarea_t *)c;
    static unsigned char draw_buf[34];
    unsigned char slen;
    unsigned char i, row;
    unsigned char frame_w;
    unsigned char llen;

    slen = str_len(ta->buf);
    frame_w = ta->width + 2;  /* рамка: | + content + | */

    /* Верхняя рамка */
    for (i = 0; i < frame_w; i++)
        draw_buf[i] = '_';
    draw_buf[frame_w] = 0;
    graph_print(ta->x, (unsigned char)(ta->y + 1), (const char *)draw_buf, 1);

    /* Нижняя рамка */
    graph_print(ta->x, (unsigned char)(ta->y + 10 + ta->lines * 8),
                (const char *)draw_buf, 1);

    /* Label */
    llen = label_len(ta->label);
    for (i = 0; i < llen; i++)
        draw_buf[i] = ta->label[i];
    draw_buf[llen] = 0;
    graph_print(ta->x, ta->y, (const char *)draw_buf, 1);

    /* Инверсия label если активен */
    if (active)
        invert_chars(ta->x, (unsigned char)(ta->y - 1), llen);

    /* Содержимое */
    adjust_scroll(ta);

    if (ta->lines <= 1) {
        /* ---- Edit: одна строка ---- */
        clear_cursor_row(ta->x, ta->width, (unsigned char)(ta->y + 14));

        draw_buf[0] = '|';
        for (i = 0; i < ta->width; i++) {
            unsigned char src = ta->scroll + i;
            draw_buf[i + 1] = (src < slen) ? ta->buf[src] : ' ';
        }
        draw_buf[ta->width + 1] = '|';
        draw_buf[ta->width + 2] = 0;
        graph_print(ta->x, (unsigned char)(ta->y + 14),
                    (const char *)draw_buf, 1);

        /* Курсор — ПОСЛЕ текста */
        if (active) {
            unsigned char scr_col = (unsigned char)(ta->cur_col - ta->scroll);
            draw_cursor((unsigned char)(ta->x + scr_col + 1),
                        (unsigned char)(ta->y + 14));
        }
    } else {
        /* ---- Textarea: несколько строк ---- */
        unsigned char start = ta->vscroll * ta->width;
        unsigned char cur_line = ta->cur_col / ta->width;
        unsigned char cur_vcol = (unsigned char)(ta->cur_col % ta->width);

        /* Очищаем строки курсора */
        for (row = 0; row < ta->lines; row++)
            clear_cursor_row(ta->x, ta->width,
                             (unsigned char)(ta->y + 14 + row * 8));

        for (row = 0; row < ta->lines; row++) {
            draw_buf[0] = '|';
            for (i = 0; i < ta->width; i++) {
                unsigned char src = start + row * ta->width + i;
                draw_buf[i + 1] = (src < slen) ? ta->buf[src] : ' ';
            }
            draw_buf[ta->width + 1] = '|';
            draw_buf[ta->width + 2] = 0;
            graph_print(ta->x, (unsigned char)(ta->y + 14 + row * 8),
                        (const char *)draw_buf, 1);
        }

        /* Курсор — ПОСЛЕ текста (иначе след. строка затирает) */
        if (active && cur_line >= ta->vscroll &&
            cur_line < ta->vscroll + ta->lines) {
            unsigned char vrow = (unsigned char)(cur_line - ta->vscroll);
            draw_cursor((unsigned char)(ta->x + cur_vcol + 1),
                        (unsigned char)(ta->y + 14 + vrow * 8));
        }
    }
}

unsigned int textarea_draw_count = 0;

void textarea_draw_content(component_t *c)
{
    textarea_draw_count++;

    textarea_t *ta = (textarea_t *)c;
    static unsigned char draw_buf[34];
    unsigned char slen;
    unsigned char i, row;

    slen = str_len(ta->buf);
    adjust_scroll(ta);

    if (ta->lines <= 1) {
        /* ---- Edit: одна строка ---- */
        clear_cursor_row(ta->x, ta->width, (unsigned char)(ta->y + 14));

        draw_buf[0] = '|';
        for (i = 0; i < ta->width; i++) {
            unsigned char src = ta->scroll + i;
            draw_buf[i + 1] = (src < slen) ? ta->buf[src] : ' ';
        }
        draw_buf[ta->width + 1] = '|';
        draw_buf[ta->width + 2] = 0;
        graph_print(ta->x, (unsigned char)(ta->y + 14),
                    (const char *)draw_buf, 1);

        /* Курсор — ПОСЛЕ текста */
        {
            unsigned char scr_col = (unsigned char)(ta->cur_col - ta->scroll);
            draw_cursor((unsigned char)(ta->x + scr_col + 1),
                        (unsigned char)(ta->y + 14));
        }
    } else {
        /* ---- Textarea: несколько строк ---- */
        unsigned char start = ta->vscroll * ta->width;
        unsigned char cur_line = ta->cur_col / ta->width;
        unsigned char cur_vcol = (unsigned char)(ta->cur_col % ta->width);

        /* Очищаем строки курсора */
        for (row = 0; row < ta->lines; row++)
            clear_cursor_row(ta->x, ta->width,
                             (unsigned char)(ta->y + 14 + row * 8));

        for (row = 0; row < ta->lines; row++) {
            draw_buf[0] = '|';
            for (i = 0; i < ta->width; i++) {
                unsigned char src = start + row * ta->width + i;
                draw_buf[i + 1] = (src < slen) ? ta->buf[src] : ' ';
            }
            draw_buf[ta->width + 1] = '|';
            draw_buf[ta->width + 2] = 0;
            graph_print(ta->x, (unsigned char)(ta->y + 14 + row * 8),
                        (const char *)draw_buf, 1);
        }

        /* Курсор — ПОСЛЕ текста */
        if (cur_line >= ta->vscroll &&
            cur_line < ta->vscroll + ta->lines) {
            unsigned char vrow = (unsigned char)(cur_line - ta->vscroll);
            draw_cursor((unsigned char)(ta->x + cur_vcol + 1),
                        (unsigned char)(ta->y + 14 + vrow * 8));
        }
    }
}

void textarea_focus_toggle(component_t *c)
{
    textarea_t *ta = (textarea_t *)c;
    unsigned char llen = label_len(ta->label);

    /* Стираем курсор при потере/получении фокуса */
    if (ta->lines <= 1) {
        clear_cursor_row(ta->x, ta->width, (unsigned char)(ta->y + 14));
    } else {
        unsigned char row;
        for (row = 0; row < ta->lines; row++)
            clear_cursor_row(ta->x, ta->width,
                             (unsigned char)(ta->y + 14 + row * 8));
    }

    /* Инверсия label */
    invert_chars(ta->x, (unsigned char)(ta->y - 1), llen);
}

unsigned char textarea_handle_key(component_t *c, unsigned char key)
{
    textarea_t *ta = (textarea_t *)c;
    unsigned char slen;
    unsigned char i;

    if (key == 27)  /* АП2 — выход */
        return 1;

    slen = str_len(ta->buf);

    if (key == 8) {  /* ← */
        if (ta->cur_col > 0)
            ta->cur_col--;
        return 0;
    }

    if (key == 9) {  /* → */
        if (ta->cur_col < slen)
            ta->cur_col++;
        return 0;
    }

    if (key == 11 && ta->lines > 1) {  /* ↑ (textarea only) */
        if (ta->cur_col >= ta->width)
            ta->cur_col -= ta->width;
        return 0;
    }

    if (key == 10 && ta->lines > 1) {  /* ↓ (textarea only) */
        if (ta->cur_col + ta->width <= slen)
            ta->cur_col += ta->width;
        else if (ta->cur_col < slen)
            ta->cur_col = slen;
        return 0;
    }

    if (key == 12) {  /* ЗАБ (Backspace) */
        if (ta->cur_col > 0) {
            for (i = ta->cur_col - 1; i < slen; i++)
                ta->buf[i] = ta->buf[i + 1];
            ta->cur_col--;
        }
        return 0;
    }

    /* Обычный символ — вставка */
    if (key >= 32 && key < 127) {
        if (slen < ta->max_len) {
            for (i = slen; i > ta->cur_col; i--)
                ta->buf[i] = ta->buf[i - 1];
            ta->buf[ta->cur_col] = to_upper((char)key);
            ta->cur_col++;
        }
        return 0;
    }

    return 0;
}
