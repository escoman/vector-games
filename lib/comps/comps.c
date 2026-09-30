/*
 * comps.c — контроллер UI-компонентов для Вектора-06Ц.
 *
 * Управляет набором компонентов: первичная отрисовка, навигация
 * TAB (вперёд) и СС+TAB (назад) между компонентами, передача клавиш
 * активному.
 */

#include "comps.h"
#include "v06.h"

extern unsigned int textarea_draw_count;
extern unsigned int textarea_redraw_chars;
extern unsigned char kbd_rows[8];
extern unsigned char kbd_shift_state;
extern unsigned char kbd_port_c_raw;

/* Отладка: число в фиксированной позиции, 4 цифры с ведущими нулями.
 * Столбец 25..30 — вместе с тегом влезает в 32 колонки экрана. */
static void dbg_num(unsigned char x, unsigned char y, char tag,
                    unsigned int n)
{
    char db[8];

    db[0] = tag;
    db[1] = ':';
    db[2] = (char)('0' + (n / 1000) % 10);
    db[3] = (char)('0' + (n / 100) % 10);
    db[4] = (char)('0' + (n / 10) % 10);
    db[5] = (char)('0' + n % 10);
    db[6] = 0;
    gfx_print(x, y, db, 1);
}

void controller_init(controller_t *ctrl)
{
    ctrl->count = 0;
    ctrl->active = 0;
    ctrl->on_key = 0;
}

void controller_add(controller_t *ctrl, component_t *comp)
{
    if (ctrl->count < COMPS_MAX)
        ctrl->items[ctrl->count++] = comp;
}

unsigned char controller_run(controller_t *ctrl)
{
    unsigned char key, key_prev = 0;

    if (ctrl->count == 0) return 0;

    /* Первичная отрисовка всех компонентов */
    {
        unsigned char i;
        for (i = 0; i < ctrl->count; i++)
            ctrl->items[i]->draw(ctrl->items[i], i == ctrl->active ? 1 : 0);
    }

    for (;;) {
        v06_wait_frame();
        key = kbd_scan();

        /* Отладка: key, draw_count и активные строки матрицы */
        {
            static unsigned char dbg_key_prev = 0xFF;
            static unsigned int dbg_dc_prev = 0xFFFF;
            static unsigned int dbg_rc_prev = 0xFFFF;
            static unsigned char dbg_rows_prev[8];
            unsigned char rows_changed = 0;
            {
                unsigned char r;
                for (r = 0; r < 8; r++) {
                    if (kbd_rows[r] != dbg_rows_prev[r]) {
                        rows_changed = 1;
                        dbg_rows_prev[r] = kbd_rows[r];
                    }
                }
            }
            if (key != dbg_key_prev) {
                dbg_num(25, 248, 'K', key);
                dbg_key_prev = key;
                rows_changed = 1;
            }
            if (rows_changed) {
                char rb[12];
                unsigned char rp = 0;
                unsigned char r;
                for (r = 0; r < 8; r++) {
                    if (kbd_rows[r]) {
                        rb[rp++] = '0' + r;
                        rb[rp++] = ' ';
                    }
                }
                if (rp == 0) { rb[0] = '-'; rb[1] = ' '; rp = 2; }
                rb[rp] = 0;
                gfx_print(0, 240, rb, 1);
            }
            if (textarea_draw_count != dbg_dc_prev) {
                dbg_num(25, 232, 'D', textarea_draw_count);
                dbg_dc_prev = textarea_draw_count;
            }
            /* Сколько символов стоила последняя перерисовка активного поля:
             * 1-2 при вводе/удалении в конце строки, вся область — при
             * сдвиге прокрутки. */
            if (textarea_redraw_chars != dbg_rc_prev) {
                dbg_num(25, 216, 'N', textarea_redraw_chars);
                dbg_rc_prev = textarea_redraw_chars;
            }
            /* Отладка: сырой порт C (01h) — поиск бита СС */
            {
                static unsigned char dbg_pc_prev = 0xFF;
                if (kbd_port_c_raw != dbg_pc_prev) {
                    char sb[6];
                    unsigned char v = kbd_port_c_raw;
                    sb[0] = 'C';
                    sb[1] = ':';
                    sb[2] = "0123456789ABCDEF"[(v >> 4) & 0xF];
                    sb[3] = "0123456789ABCDEF"[v & 0xF];
                    sb[4] = 0;
                    gfx_print(25, 224, sb, 1);
                    dbg_pc_prev = kbd_port_c_raw;
                }
            }
        }

        if (key != key_prev && key != 0) {
            if (key == 7) {  /* TAB — переключение (СС+TAB — назад) */
                /* Переключить фокус (инверсия label) */
                ctrl->items[ctrl->active]->focus_toggle(
                    ctrl->items[ctrl->active]);
                /* СС+ТАБ — на предыдущий, иначе на следующий.
                 * СС читается из порта C (бит 5) отдельно от матрицы,
                 * поэтому kbd_shift_state валиден в момент опроса TAB. */
                if (kbd_shift_state) {
                    if (ctrl->active == 0)
                        ctrl->active = ctrl->count - 1;
                    else
                        ctrl->active--;
                } else {
                    ctrl->active++;
                    if (ctrl->active >= ctrl->count)
                        ctrl->active = 0;
                }
                /* Переключить фокус на новый */
                ctrl->items[ctrl->active]->focus_toggle(
                    ctrl->items[ctrl->active]);
                /* Отобразить курсор нового активного (контент уже на экране) */
                ctrl->items[ctrl->active]->draw_cursor(
                    ctrl->items[ctrl->active]);
            } else if (key == 27) {  /* ESC — выход */
                return 27;
            } else {
                unsigned char handled = 0;
                if (ctrl->on_key) {
                    unsigned char res = ctrl->on_key(key);
                    if (res > 1) return res;  /* >1 — код выхода */
                    if (res == 1) handled = 1; /* обработано */
                }
                if (!handled) {
                    /* Передать активному компоненту. Он сам выполняет
                     * минимальную перерисовку: весь контент при изменении
                     * текста/прокрутки, либо только курсор при навигации. */
                    if (ctrl->items[ctrl->active]->handle_key(
                            ctrl->items[ctrl->active], key))
                        return key;
                }
            }
        }
        key_prev = key;
    }
}
