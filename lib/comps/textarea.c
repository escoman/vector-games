/*
 * textarea.c — компонент поля ввода для Вектора-06Ц.
 *
 * Два режима в одном компоненте:
 *   lines == 1 → edit (однострочный, горизонтальная прокрутка)
 *   lines > 1  → textarea (многострочный, перенос по ширине)
 *
 * Внешний буфер, навигация стрелками, вставка/удаление символов.
 * Рамка рисуется линиями через gfx_fill_stride, заголовок (label).
 * Курсор — линия 1 пиксель высотой в пустом ряду под глифом (не глиф).
 * Высота строки текста — TA_ROW_H пикселей, а не 8: ряду курсора нужно
 * своё место, иначе он затирает нижние пиксели глифов.
 * Перерисовка минимальная: сдвинутый «хвост» строки, а не вся область
 * (см. redraw_range).
 */

#include "comps.h"
#include "v06.h"
#include <string.h>

/* Плоскость монохромного режима 256x256 (бит 0 цвета → 0xE000). */
#define FRAME_PLANE 0xE000u

/* Вертикальная раскладка текста поля.
 *
 * Глиф 8x8, шаг строки — TA_ROW_H = 10: 8 рядов глифа, ряд под ним —
 * курсор (сплошная линия шириной в ячейку), ещё один ряд остаётся пустым
 * до следующей строки. При шаге 8 строки шли вплотную, и курсор ложился
 * на нижний ряд собственного глифа — у '_' и ',' там нарисованные пиксели,
 * они затирались.
 *
 * Отсчёт от ta->y (верх метки): ta->y+10 — верхняя линия рамки, ta->y+14 —
 * первая строка текста, нижняя линия — на 3 ряда ниже последнего глифа
 * (тот же отступ, что сверху). Однострочный edit от шага строки не
 * зависит: его рамка осталась прежней (ta->y+10 .. ta->y+25), курсор лишь
 * переехал на ряд под глиф. */
#define TA_ROW_H 10         /* шаг строки текста, пикселей                  */
#define TA_TEXT_Y0 14       /* 1-я строка текста относительно ta->y         */
#define TA_CURSOR_ROW 8     /* ряд курсора внутри строки (под рядом глифа) */
#define TA_FRAME_PAD 11     /* 7 (низ глифа) + 3 пустых ряда + линия рамки */

/* Верхняя строка глифа видимой строки vrow (0 — первая в окне). */
#define TA_TEXT_ROW(ta, vrow) \
    ((unsigned char)((ta)->y + TA_TEXT_Y0 + (unsigned char)(vrow) * TA_ROW_H))

/* Нижняя линия рамки поля. */
#define TA_FRAME_BOT(ta) \
    ((unsigned char)((ta)->y + TA_TEXT_Y0 \
                     + (unsigned char)((ta)->lines - 1) * TA_ROW_H + TA_FRAME_PAD))

/* Буфер одной выводимой строки: максимум 32 колонки + терминатор. */
static unsigned char draw_buf[34];

/* Отладочные счётчики (показываются в отладочной панели контроллера):
 *  textarea_draw_count   — сколько раз перерисовывали область целиком;
 *  textarea_redraw_chars — сколько символов нарисовала последняя
 *                          перерисовка (т.е. цена одного нажатия). */
unsigned int textarea_draw_count = 0;
unsigned int textarea_redraw_chars = 0;

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

/* Длина строки (без \0). Возвращает unsigned int: буфер поля ввода может
 * быть длиннее 255 символов, байтовый счётчик давал бы длину по модулю
 * 256 (256 символов — «пусто»), и правка такого текста затирала начало. */
static unsigned int str_len(const char *s)
{
    unsigned int n = 0;
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

/* Рисует/стирает курсор — горизонтальную линию высотой 1 пиксель (на всю
 * ширину ячейки) в колонке col строки текста text_row. Курсор занимает
 * пустой ряд под глифом (text_row+TA_CURSOR_ROW), до следующей строки
 * остаётся ещё ряд — ни нижний ряд своего глифа, ни соседняя строка не
 * затираются. val=0xFF — нарисовать, val=0x00 — стереть. */
static void put_cursor_block(unsigned char col, unsigned char text_row,
                             unsigned char val)
{
    unsigned int addr = 0xE000 + (unsigned int)col * 256
                        + (255 - (text_row + TA_CURSOR_ROW));
    *((volatile unsigned char *)addr) = val;
}

/* Рисует курсор (1 пиксель) в позиции col строки текста text_row. */
static void draw_cursor(unsigned char col, unsigned char text_row)
{
    put_cursor_block(col, text_row, 0xFF);
}

/* Печатает n ячеек, начиная с плоской позиции src, в экранную позицию
 * (col, row): символы строки, а всё, что за концом строки — пробелы.
 * Пробелы затирают прежний хвост строки; ряд курсора чистится отдельно
 * (gfx_fill_stride ниже). Один gfx_print на непрерывный участок строки —
 * дешевле, по символу на ячейку. */
static void draw_cells(const textarea_t *ta, unsigned int src,
                       unsigned char col, unsigned char row,
                       unsigned char n)
{
    const char *p = ta->buf + src;
    unsigned int slen = str_len(ta->buf);
    unsigned int rem;
    unsigned char nch, i;

    /* Символов строки в участке не больше n (ячейки ≤ 32), поэтому дальше
     * всё считается байтом: два простых цикла вместо 16-битного сравнения
     * на каждый символ. */
    rem = (src < slen) ? slen - src : 0;
    nch = (rem > n) ? n : (unsigned char)rem;

    for (i = 0; i < nch; i++)
        draw_buf[i] = p[i];
    for (; i < n; i++)
        draw_buf[i] = ' ';
    draw_buf[n] = 0;
    gfx_print(col, row, (const char *)draw_buf, 1);
    /* Курсор живёт в ряду под глифом — до шага строки 10 он попадал в
     * нижний ряд ячейки и стирался вместе с перерисовкой ячейки gfx_print.
     * Теперь ряд курсора ячейке не принадлежит, поэтому любая перерисовка
     * обязана стереть курсор, который на этих колонках мог лежать, иначе
     * подчёркивания накапливаются при движении курсора по тексту. Живой
     * курсор рисуется после перерисовки (см. textarea_draw_content). */
    gfx_fill_stride((unsigned int)(FRAME_PLANE + (unsigned int)col * 256
                                   + (255 - (unsigned char)(row + TA_CURSOR_ROW))),
                    0x00, 0x0100u, n);
    textarea_redraw_chars += n;
}

/* Перерисовка изменённых ячеек [from, to) плоских позиций — только
 * попавших в видимое окно, участками до конца строки (со следующим
 * участком — уже на новой строке). Ячейки левее from не трогаются, так
 * что вставка/удаление в конце строки стоит 1-2 символа вместо всей
 * области; при вставке в середине — только сдвинутый хвост. */
static void redraw_range(const textarea_t *ta, unsigned int from,
                         unsigned int to)
{
    unsigned int vis_start, vis_end;
    unsigned int pos;

    if (ta->lines <= 1) {
        vis_start = ta->scroll;
        vis_end = ta->scroll + ta->width;
    } else {
        vis_start = (unsigned int)ta->vscroll * ta->width;
        vis_end = vis_start + (unsigned int)ta->width * ta->lines;
    }
    if (from < vis_start) from = vis_start;
    if (to > vis_end) to = vis_end;

    pos = from;
    while (pos < to) {
        unsigned char vcol, row, n;

        if (ta->lines <= 1) {
            vcol = (unsigned char)(pos - ta->scroll);
            row = TA_TEXT_ROW(ta, 0);
        } else {
            unsigned int line = pos / ta->width;
            vcol = (unsigned char)(pos - line * ta->width);
            row = TA_TEXT_ROW(ta, line - ta->vscroll);
        }
        n = (unsigned char)(ta->width - vcol);        /* до конца строки */
        if (to - pos < n)
            n = (unsigned char)(to - pos);
        draw_cells(ta, pos, (unsigned char)(ta->x + 1 + vcol), row, n);
        pos = pos + n;
    }
}

/* Перерисовывает один символ контента по плоской позиции pos — восстанавливает
 * ячейку, под которой был курсор (и сам курсор: draw_cells чистит его ряд).
 * Рисует только видимые позиции; невидимые (за прокруткой) пропускает. */
static void redraw_char_at(const textarea_t *ta, unsigned int pos)
{
    redraw_range(ta, pos, pos + 1);
}

/* Кэш последнего нарисованного индикатора прокрутки (см. draw_scrollbar):
 * колонка правой границы, её верхний ряд и границы бегунка [sb_t0, sb_t1).
 * 0xFF — «на экране просто граница», перерисовать обязательно. */
static unsigned char sb_col = 0xFF;
static unsigned char sb_top;
static unsigned char sb_t0, sb_t1;

/* Вход/выход расчёта бегунка — тоже в статиках (см. комментарий у
 * textarea_handle_key: на кадре с десятком побайтовых локальных sccz80
 * путается в смещениях). */
static unsigned char gs_top, gs_bot;          /* ряды рамки            */
static unsigned char gs_lines;                /* видимых строк         */
static unsigned int  gs_vscroll;              /* первая видимая строка */
static unsigned int  gs_total;                /* строк текста всего    */
static unsigned char gs_t0, gs_t1;            /* бегунок [t0, t1)      */

/* Рисует прямоугольную рамку, ограничивающую поле ввода, линиями
 * через gfx_fill_stride (вместо символов '_' и '|'). Рамка охватывает
 * столбцы ta->x .. ta->x+width+1 и строки (ta->y+10) .. TA_FRAME_BOT.
 * Сначала вертикальные линии, затем горизонтальные — так углы
 * перекрываются сплошным байтом 0xFF. */
static void draw_frame(const textarea_t *ta)
{
    unsigned char cx0 = ta->x;
    unsigned char cx1 = (unsigned char)(ta->x + ta->width + 1);
    unsigned char ncols = (unsigned char)(ta->width + 2);
    unsigned char ytop = (unsigned char)(ta->y + 10);
    unsigned char ybot = TA_FRAME_BOT(ta);
    unsigned char vcount = (unsigned char)(ybot - ytop + 1);

    /* Правая граница теперь «принадлежит» индикатору прокрутки. */
    sb_col = 0xFF;

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

/* Индикатор положения видимого окна внутри всего текста — «скроллбар»
 * на правой ограничивающей полосе рамки.
 *
 * Колонка cx1 — служебный столбец между последним знаком текста и
 * границей, поверх текста индикатор не попадает. Граница поля занимает
 * бит 0 байта (пиксель X = cx1*8+7), и чтобы бегунок не лежал вплотную
 * к ограничивающему прямоугольнику, вокруг него оставлен зазор в 1 пиксель:
 *   бит 0    — линия правой границы (её индикатор не трогает);
 *   бит 1    — зазор до границы;
 *   биты 2..4 — сам бегунок (3 пикселя шириной);
 *   ряды ytop+1 и ybot-1 — зазор до верхней и нижней линий рамки,
 *                  бегунок ходит в пределах ytop+2 .. ybot-2.
 *   трек    — 1 пиксель (0x01) на всю высоту между линиями рамки;
 *   бегунок — 3 пикселя (биты 2..4) вместе с пикселем границы:
 *             высота = доля видимых строк,
 *             положение = насколько окно прокручено вниз.
 * Когда текст целиком влезает в поле, бегунок занимает весь трек.
 * У однострочного edit прокрутка горизонтальная — индикатор не рисуется.
 *
 * Дешевле, чем кажется: если бегунок никуда не сдвинулся, VRAM не трогается
 * вовсе, иначе нажатие, не изменившее окно, стоило бы ~48 записей вместо
 * 1-2 перерисованных символов.
 *
 * Кэш предполагает, что между перерисовками индикатора в эти пиксели больше
 * никто не пишет; любая перерисовка рамки (draw_frame) кэш сбрасывает. */

/* Зазоры индикатора: 1 пиксель до линий рамки сверху/снизу и 1 пиксель
 * (бит 1) до линии границы справа. */
#define SB_ROW0 2                 /* первый ряд бегунка: ytop + SB_ROW0  */
#define SB_THUMB 0x1C             /* биты 2..4                            */
#define SB_TRACK 0x01             /* бит 0 — он же граница, им и чистим   */
/* Что реально пишем в ряд бегунка: gfx_fill_stride заменяет байт целиком,
 * поэтому пиксель границы (бит 0) приходится дописывать, иначе бегунок её
 * сотрёт. Бит 1 при этом остаётся нулевым — тот самый зазор до границы. */
#define SB_ON   (unsigned char)(SB_TRACK | SB_THUMB)

/* Считает границы бегунка в gs_t0/gs_t1 (ряды пикселей, gs_t1 исключая). */
static void scrollbar_thumb(void)
{
    /* Рядов доступно: между ytop+1 и ybot-1 (зазоры) — на 2 меньше,
     * чем расстояние между линиями минус их собственные ряды. */
    unsigned int h = (unsigned int)(gs_bot - gs_top - 1 - SB_ROW0);
    unsigned int vis = gs_lines;
    unsigned int total = gs_total;
    unsigned int thumb, p, d, v;

    if (total <= vis) {
        gs_t0 = (unsigned char)(gs_top + SB_ROW0);
        gs_t1 = (unsigned char)(gs_bot - 1);
        return;
    }
    /* Высота бегунка пропорциональна доле видимого текста. Округление
     * вверх — как и было, но без «+ total - 1»: та сумма переполнила бы
     * 16 бит на длинном тексте. Здесь h*vis ≤ 252*255 заведомо влезает,
     * а thumb*total ≤ h*vis, значит и проверка остатка безопасна. */
    p = h * vis;
    thumb = p / total;
    if (thumb * total < p)
        thumb++;
    if (thumb < 3) thumb = 3;
    if (thumb > h) thumb = h;

    /* Позиция: (h - thumb) * vscroll / (total - vis). Произведение
     * переполняет 16 бит, когда строк текста больше нескольких сотен,
     * а 32-битная арифметика на Z80 слишком дорога. Дробь нормализуем
     * сдвигом: знаменатель ≤ 255, тогда произведение влезает, а
     * монотонность и оба крайних положения бегунка сохраняются. */
    d = total - vis;
    v = gs_vscroll;
    while (d > 255) { d >>= 1; v >>= 1; }
    gs_t0 = (unsigned char)(gs_top + SB_ROW0 + ((h - thumb) * v) / d);
    gs_t1 = (unsigned char)(gs_t0 + (unsigned char)thumb);
}

static void draw_scrollbar(const textarea_t *ta)
{
    unsigned char cx1 = (unsigned char)(ta->x + ta->width + 1);
    unsigned char ytop = (unsigned char)(ta->y + 10);
    unsigned char ybot = TA_FRAME_BOT(ta);

    if (ta->lines <= 1) return;

    gs_top = ytop;
    gs_bot = ybot;
    gs_lines = ta->lines;
    gs_vscroll = ta->vscroll;
    /* Строк всего, включая ту, где встанет курсор после конца текста. */
    gs_total = str_len(ta->buf) / ta->width + 1;
    scrollbar_thumb();

    if (sb_col == cx1 && sb_top == ytop &&
        sb_t0 == gs_t0 && sb_t1 == gs_t1)
        return;
    sb_col = cx1;
    sb_top = ytop;
    sb_t0 = gs_t0;
    sb_t1 = gs_t1;

    /* Шаг 0xFFFF = -1: строки идут вниз экрана по убыванию адреса.
     * Сначала трек значением SB_TRACK: оно же восстанавливает пиксель
     * границы (бит 0) и стирает прежний бегунок ниже/выше нового. */
    gfx_fill_stride((unsigned int)(FRAME_PLANE + (unsigned int)cx1 * 256
                                   + (255 - (unsigned char)(ytop + SB_ROW0))),
                    SB_TRACK, 0xFFFFu,
                    (unsigned char)(ybot - ytop - 1 - SB_ROW0));
    gfx_fill_stride((unsigned int)(FRAME_PLANE + (unsigned int)cx1 * 256
                                   + (255 - gs_t0)),
                    SB_ON, 0xFFFFu, (unsigned char)(gs_t1 - gs_t0));
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
        unsigned int cur_line = ta->cur_col / ta->width;
        if (cur_line < ta->vscroll)
            ta->vscroll = cur_line;
        if (cur_line >= ta->vscroll + ta->lines)
            ta->vscroll = cur_line - ta->lines + 1;
    }
}

/* Отрисовка всего видимого окна контента (без курсора): один gfx_print на
 * строку. Позиции за концом строки — пробелы. */
static void draw_visible(const textarea_t *ta)
{
    unsigned char row;

    if (ta->lines <= 1) {
        /* ---- Edit: одна строка ---- */
        draw_cells(ta, ta->scroll, (unsigned char)(ta->x + 1),
                   TA_TEXT_ROW(ta, 0), ta->width);
    } else {
        /* ---- Textarea: все видимые строки ---- */
        for (row = 0; row < ta->lines; row++)
            draw_cells(ta, (unsigned int)(ta->vscroll + row) * ta->width,
                       (unsigned char)(ta->x + 1),
                       TA_TEXT_ROW(ta, row), ta->width);
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
    unsigned char i;
    unsigned char llen;

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

    /* Содержимое; курсор — только у активного компонента */
    adjust_scroll(ta);
    draw_visible(ta);
    draw_scrollbar(ta);

    if (active)
        textarea_draw_cursor(c);
}

/* Полная перерисовка видимого окна. Нужна, когда сдвинулось само окно
 * (прокрутка) или когда изменён почти весь текст. */
void textarea_draw_content(component_t *c)
{
    textarea_t *ta = (textarea_t *)c;

    textarea_draw_count++;
    adjust_scroll(ta);
    draw_visible(ta);
    draw_scrollbar(ta);

    /* Курсор — ПОСЛЕ текста (иначе следующая строка его затирает) */
    textarea_draw_cursor(c);
}

/* Рисует только курсор в текущей позиции (без перерисовки контента).
 * Используется при получении фокуса, когда текст уже на экране. */
void textarea_draw_cursor(component_t *c)
{
    textarea_t *ta = (textarea_t *)c;

    if (ta->lines <= 1) {
        /* ---- Edit: одна строка ---- */
        unsigned char scr_col = (unsigned char)(ta->cur_col - ta->scroll);
        draw_cursor((unsigned char)(ta->x + scr_col + 1), TA_TEXT_ROW(ta, 0));
    } else {
        /* ---- Textarea: курсор только в видимой строке ---- */
        unsigned int cur_line = ta->cur_col / ta->width;
        unsigned char cur_vcol = (unsigned char)(ta->cur_col % ta->width);
        if (cur_line >= ta->vscroll &&
            cur_line < ta->vscroll + ta->lines) {
            unsigned char vrow = (unsigned char)(cur_line - ta->vscroll);
            draw_cursor((unsigned char)(ta->x + cur_vcol + 1),
                        TA_TEXT_ROW(ta, vrow));
        }
    }
}

void textarea_focus_toggle(component_t *c)
{
    textarea_t *ta = (textarea_t *)c;
    unsigned char llen = label_len(ta->label);

    /* Скрыть курсор: восстановить ячейку, поверх которой он был
     * (курсор живёт в пределах своей ячейки, следующую строку не трогает). */
    textarea_redraw_chars = 0;   /* переключение фокуса стоит 1 ячейку */
    redraw_char_at(ta, ta->cur_col);

    /* Инверсия label */
    invert_chars(ta->x, (unsigned char)(ta->y - 1), llen);
}

/* Снимок последнего редактирования — в статиках, а не в локальных:
 * у textarea_handle_key их набиралось с десяток, и на таком кадре
 * sccz80 путается в смещениях (читает old_cur из ячейки указателя ta,
 * отчего правая граница участка получается мусорной). */
static unsigned int ed_slen;           /* длина строки ДО правки      */
static unsigned int ed_to;             /* длина строки ПОСЛЕ правки   */
static unsigned int ed_old_cur;        /* позиция курсора ДО правки   */
static unsigned int ed_old_scroll;
static unsigned int ed_old_vscroll;
static unsigned int ed_from;           /* первая изменённая ячейка    */

unsigned char textarea_handle_key(component_t *c, unsigned char key)
{
    textarea_t *ta = (textarea_t *)c;
    unsigned int i;
    unsigned char content_changed = 0;

    if (key == 27)  /* АП2 — выход */
        return 1;

    ed_slen = str_len(ta->buf);
    ed_to = ed_slen;                   /* правка, не меняющая длину */
    ed_old_cur = ta->cur_col;
    ed_old_scroll = ta->scroll;
    ed_old_vscroll = ta->vscroll;
    ed_from = ed_old_cur;              /* вставка — в позицию курсора */

    if (key == 8) {  /* ← */
        if (ta->cur_col > 0)
            ta->cur_col--;
    } else if (key == 9) {  /* → */
        if (ta->cur_col < ed_slen)
            ta->cur_col++;
    } else if (key == 11 && ta->lines > 1) {  /* ↑ (textarea only) */
        if (ta->cur_col >= ta->width)
            ta->cur_col -= ta->width;
    } else if (key == 10 && ta->lines > 1) {  /* ↓ (textarea only) */
        if (ta->cur_col + ta->width <= ed_slen)
            ta->cur_col += ta->width;
        else if (ta->cur_col < ed_slen)
            ta->cur_col = ed_slen;
    } else if (key == 12) {  /* ЗАБ (Backspace) */
        if (ta->cur_col > 0) {
            for (i = ta->cur_col - 1; i < ed_slen; i++)
                ta->buf[i] = ta->buf[i + 1];
            ta->cur_col--;
            ed_from = ta->cur_col;     /* удалён символ левее курсора */
            content_changed = 1;
        }
    } else if (key >= 32 && key < 127) {  /* Обычный символ — вставка */
        if (ed_slen < ta->max_len) {
            for (i = ed_slen; i > ta->cur_col; i--)
                ta->buf[i] = ta->buf[i - 1];
            ta->buf[ta->cur_col] = to_upper((char)key);
            ta->cur_col++;
            ed_to = ed_slen + 1;
            content_changed = 1;
        }
    }

    /* Минимальная перерисовка:
     *  - сдвинулось окно (прокрутка) → перерисовать всё видимое;
     *  - текст изменился в пределах окна → только сдвинутый хвост от
     *    ed_from до конца строки, плюс ячейка под старым курсором
     *    (восстановленный символ затирает его); всё левее не трогаем;
     *  - сдвинулся только курсор → стереть старый, нарисовать новый. */
    adjust_scroll(ta);
    textarea_redraw_chars = 0;

    /* Правая (исключительная) граница — самый дальний из:
     *  - ed_to: старый/новый конец строки (стереть хвост после удаления,
     *    дорисовать вставленный символ);
     *  - ячейки за старым курсором (стереть сам курсор). */
    if (ed_old_cur >= ed_to)
        ed_to = ed_old_cur + 1;

    if (content_changed && ta->scroll == ed_old_scroll &&
        ta->vscroll == ed_old_vscroll) {
        redraw_range(ta, ed_from, ed_to);
        /* Длина текста могла измениться и без сдвига окна — у индикатора
         * прокрутки изменилась бы только высота бегунка. */
        draw_scrollbar(ta);
        textarea_draw_cursor(c);
    } else if (content_changed || ta->scroll != ed_old_scroll ||
               ta->vscroll != ed_old_vscroll) {
        textarea_draw_content(c);
    } else if (ta->cur_col != ed_old_cur) {
        /* Движение только курсора: восстановить ячейку под старым курсором
         * (она же его стирает) и нарисовать курсор на новом месте. */
        redraw_char_at(ta, ed_old_cur);
        textarea_draw_cursor(c);
    }

    return 0;
}
