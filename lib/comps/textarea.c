/*
 * textarea.c — компонент поля ввода для Вектора-06Ц.
 *
 * Два режима в одном компоненте:
 *   lines == 1 → edit (однострочный, горизонтальная прокрутка)
 *   lines > 1  → textarea (многострочный, перенос по ширине)
 *
 * Внешний буфер, навигация стрелками, вставка/удаление символов.
 * Рамка рисуется линиями через gfx_fill_stride, заголовок (label).
 * Курсор — тонкая линия 1 пиксель в межстрочном промежутке (не глиф).
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

/* Рисует/стирает курсор — тонкую горизонтальную линию высотой 1 пиксель
 * в колонке col строки text_row. Курсор занимает нижнюю строку ячейки
 * (text_row+7) — межстрочный промежуток, поэтому следующую строку текста
 * он не задевает. val=0xFF — нарисовать, val=0x00 — стереть. */
static void put_cursor_block(unsigned char col, unsigned char text_row,
                             unsigned char val)
{
    unsigned int addr = 0xE000 + (unsigned int)col * 256
                        + (255 - (text_row + 7));
    *((volatile unsigned char *)addr) = val;
}

/* Рисует курсор (1 пиксель) в позиции col строки текста text_row. */
static void draw_cursor(unsigned char col, unsigned char text_row)
{
    put_cursor_block(col, text_row, 0xFF);
}

/* Перерисовывает один символ контента по плоской позиции pos — тем самым
 * восстанавливает ячейку, поверх которой был курсор (фактически стирает
 * его). Рисует только видимые позиции; невидимые (за прокруткой) пропускает. */
static void redraw_char_at(const textarea_t *ta, unsigned char pos)
{
    unsigned char slen = str_len(ta->buf);
    unsigned char col, row;
    char ch;

    if (ta->lines <= 1) {
        unsigned char vc = (unsigned char)(pos - ta->scroll);
        if (vc >= ta->width) return;
        col = (unsigned char)(ta->x + 1 + vc);
        row = (unsigned char)(ta->y + 14);
    } else {
        unsigned char line = (unsigned char)(pos / ta->width);
        unsigned char vcol = (unsigned char)(pos % ta->width);
        if (line < ta->vscroll || line >= ta->vscroll + ta->lines) return;
        col = (unsigned char)(ta->x + 1 + vcol);
        row = (unsigned char)(ta->y + 14 + (line - ta->vscroll) * 8);
    }
    ch = (pos < slen) ? ta->buf[pos] : ' ';
    gfx_put_char(col, row, ch, 1);
}

/* Плоскость монохромного режима 256x256 (бит 0 цвета → 0xE000). */
#define FRAME_PLANE 0xE000u

/* Рисует прямоугольную рамку, ограничивающую поле ввода, линиями
 * через gfx_fill_stride (вместо символов '_' и '|'). Рамка охватывает
 * столбцы ta->x .. ta->x+width+1 и строки (ta->y+10) .. (ta->y+17+lines*8).
 * Сначала вертикальные линии, затем горизонтальные — так углы
 * перекрываются сплошным байтом 0xFF. */
static void draw_frame(const textarea_t *ta)
{
    unsigned char cx0 = ta->x;
    unsigned char cx1 = (unsigned char)(ta->x + ta->width + 1);
    unsigned char ncols = (unsigned char)(ta->width + 2);
    unsigned char ytop = (unsigned char)(ta->y + 10);
    unsigned char ybot = (unsigned char)(ta->y + 17 + ta->lines * 8);
    unsigned char vcount = (unsigned char)(ybot - ytop + 1);

    /* Левая граница: пиксель X = cx0*8 (бит 7), шаг -1 по строкам. */
    gfx_fill_stride((unsigned int)(FRAME_PLANE + (unsigned int)cx0 * 256
                                   + (255 - ytop)), 0x80, 0xFFFFu, vcount);
    /* Правая граница: пиксель X = cx1*8+7 (бит 0), шаг -1 по строкам. */
    gfx_fill_stride((unsigned int)(FRAME_PLANE + (unsigned int)cx1 * 256
                                   + (255 - ytop)), 0x01, 0xFFFFu, vcount);

    /* Верхняя и нижняя границы: сплошные строки, шаг 256 по столбцам. */
    gfx_fill_stride((unsigned int)(FRAME_PLANE + (unsigned int)cx0 * 256
                                   + (255 - ytop)), 0xFF, 0x100u, ncols);
    gfx_fill_stride((unsigned int)(FRAME_PLANE + (unsigned int)cx0 * 256
                                   + (255 - ybot)), 0xFF, 0x100u, ncols);
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
    ta->base.draw_cursor = textarea_draw_cursor;
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
    unsigned char llen;

    slen = str_len(ta->buf);

    /* Рамка — линиями через gfx_fill_stride */
    draw_frame(ta);

    /* Label */
    llen = label_len(ta->label);
    for (i = 0; i < llen; i++)
        draw_buf[i] = ta->label[i];
    draw_buf[llen] = 0;
    gfx_print(ta->x, ta->y, (const char *)draw_buf, 1);

    /* Инверсия label если активен */
    if (active)
        invert_chars(ta->x, (unsigned char)(ta->y - 1), llen);

    /* Содержимое */
    adjust_scroll(ta);

    if (ta->lines <= 1) {
        /* ---- Edit: одна строка ---- */
        for (i = 0; i < ta->width; i++) {
            unsigned char src = ta->scroll + i;
            draw_buf[i] = (src < slen) ? ta->buf[src] : ' ';
        }
        draw_buf[ta->width] = 0;
        gfx_print((unsigned char)(ta->x + 1), (unsigned char)(ta->y + 14),
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

        for (row = 0; row < ta->lines; row++) {
            for (i = 0; i < ta->width; i++) {
                unsigned char src = start + row * ta->width + i;
                draw_buf[i] = (src < slen) ? ta->buf[src] : ' ';
            }
            draw_buf[ta->width] = 0;
            gfx_print((unsigned char)(ta->x + 1),
                        (unsigned char)(ta->y + 14 + row * 8),
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
        for (i = 0; i < ta->width; i++) {
            unsigned char src = ta->scroll + i;
            draw_buf[i] = (src < slen) ? ta->buf[src] : ' ';
        }
        draw_buf[ta->width] = 0;
        gfx_print((unsigned char)(ta->x + 1), (unsigned char)(ta->y + 14),
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

        for (row = 0; row < ta->lines; row++) {
            for (i = 0; i < ta->width; i++) {
                unsigned char src = start + row * ta->width + i;
                draw_buf[i] = (src < slen) ? ta->buf[src] : ' ';
            }
            draw_buf[ta->width] = 0;
            gfx_print((unsigned char)(ta->x + 1),
                        (unsigned char)(ta->y + 14 + row * 8),
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

/* Рисует только курсор в текущей позиции (без перерисовки контента).
 * Используется при получении фокуса, когда текст уже на экране. */
void textarea_draw_cursor(component_t *c)
{
    textarea_t *ta = (textarea_t *)c;

    if (ta->lines <= 1) {
        /* ---- Edit: одна строка ---- */
        unsigned char scr_col = (unsigned char)(ta->cur_col - ta->scroll);
        draw_cursor((unsigned char)(ta->x + scr_col + 1),
                    (unsigned char)(ta->y + 14));
    } else {
        /* ---- Textarea: курсор только в видимой строке ---- */
        unsigned char cur_line = ta->cur_col / ta->width;
        unsigned char cur_vcol = (unsigned char)(ta->cur_col % ta->width);
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

    /* Скрыть курсор: восстановить ячейку, поверх которой он был
     * (курсор живёт в пределах своей ячейки, следующую строку не трогает). */
    redraw_char_at(ta, ta->cur_col);

    /* Инверсия label */
    invert_chars(ta->x, (unsigned char)(ta->y - 1), llen);
}

unsigned char textarea_handle_key(component_t *c, unsigned char key)
{
    textarea_t *ta = (textarea_t *)c;
    unsigned char slen;
    unsigned char i;
    unsigned char old_cur, old_scroll, old_vscroll;
    unsigned char content_changed = 0;

    if (key == 27)  /* АП2 — выход */
        return 1;

    slen = str_len(ta->buf);
    old_cur = ta->cur_col;
    old_scroll = ta->scroll;
    old_vscroll = ta->vscroll;

    if (key == 8) {  /* ← */
        if (ta->cur_col > 0)
            ta->cur_col--;
    } else if (key == 9) {  /* → */
        if (ta->cur_col < slen)
            ta->cur_col++;
    } else if (key == 11 && ta->lines > 1) {  /* ↑ (textarea only) */
        if (ta->cur_col >= ta->width)
            ta->cur_col -= ta->width;
    } else if (key == 10 && ta->lines > 1) {  /* ↓ (textarea only) */
        if (ta->cur_col + ta->width <= slen)
            ta->cur_col += ta->width;
        else if (ta->cur_col < slen)
            ta->cur_col = slen;
    } else if (key == 12) {  /* ЗАБ (Backspace) */
        if (ta->cur_col > 0) {
            for (i = ta->cur_col - 1; i < slen; i++)
                ta->buf[i] = ta->buf[i + 1];
            ta->cur_col--;
            content_changed = 1;
        }
    } else if (key >= 32 && key < 127) {  /* Обычный символ — вставка */
        if (slen < ta->max_len) {
            for (i = slen; i > ta->cur_col; i--)
                ta->buf[i] = ta->buf[i - 1];
            ta->buf[ta->cur_col] = to_upper((char)key);
            ta->cur_col++;
            content_changed = 1;
        }
    }

    /* Минимальная перерисовка:
     *  - текст изменился или сдвинулась прокрутка → весь контент;
     *  - иначе сдвинулся только курсор → стереть старый, нарисовать новый. */
    adjust_scroll(ta);
    if (content_changed || ta->scroll != old_scroll ||
        ta->vscroll != old_vscroll) {
        textarea_draw_content(c);
    } else if (ta->cur_col != old_cur) {
        /* Движение только курсора: восстановить ячейку под старым курсором
         * (она же его стирает) и нарисовать курсор на новом месте. */
        redraw_char_at(ta, old_cur);
        textarea_draw_cursor(c);
    }

    return 0;
}
