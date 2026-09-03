/*
 * comps.c — контроллер UI-компонентов для Вектора-06Ц.
 *
 * Управляет набором компонентов: первичная отрисовка, навигация
 * TAB между компонентами, передача клавиш активному.
 */

#include "comps.h"
#include "v06.h"
#include <intrinsic.h>

extern unsigned int textarea_draw_count;
extern unsigned char kbd_rows[8];
extern unsigned char kbd_shift_state;
extern unsigned char kbd_port_c_raw;

static void wait_frame(void)
{
    unsigned int s = frame_count;
    while (frame_count == s)
        intrinsic_halt();
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
        wait_frame();
        key = kbd_scan();

        /* Отладка: key, draw_count и активные строки матрицы */
        {
            static unsigned char dbg_key_prev = 0xFF;
            static unsigned int dbg_dc_prev = 0xFFFF;
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
                char db[6];
                unsigned char dp = 0;
                db[dp++] = 'K';
                db[dp++] = ':';
                if (key >= 100) db[dp++] = '0' + (key / 100);
                if (key >= 10)  db[dp++] = '0' + ((key / 10) % 10);
                db[dp++] = '0' + (key % 10);
                db[dp] = 0;
                graph_print(27, 248, db, 1);
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
                graph_print(0, 240, rb, 1);
            }
            if (textarea_draw_count != dbg_dc_prev) {
                char db[8];
                unsigned char dp = 0;
                unsigned int n = textarea_draw_count;
                db[dp++] = 'D';
                db[dp++] = ':';
                if (n >= 1000) db[dp++] = '0' + (n / 1000);
                if (n >= 100)  db[dp++] = '0' + ((n / 100) % 10);
                if (n >= 10)   db[dp++] = '0' + ((n / 10) % 10);
                db[dp++] = '0' + (n % 10);
                db[dp] = 0;
                graph_print(27, 232, db, 1);
                dbg_dc_prev = textarea_draw_count;
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
                    graph_print(27, 224, sb, 1);
                    dbg_pc_prev = kbd_port_c_raw;
                }
            }
        }

        if (key != key_prev && key != 0) {
            if (key == 7) {  /* TAB — переключение */
                /* Переключить фокус (инверсия label) */
                ctrl->items[ctrl->active]->focus_toggle(
                    ctrl->items[ctrl->active]);
                /* Следующий */
                ctrl->active++;
                if (ctrl->active >= ctrl->count)
                    ctrl->active = 0;
                /* Переключить фокус на новый */
                ctrl->items[ctrl->active]->focus_toggle(
                    ctrl->items[ctrl->active]);
                /* Отобразить курсор нового активного */
                ctrl->items[ctrl->active]->draw_content(
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
                    /* Передать активному компоненту */
                    if (ctrl->items[ctrl->active]->handle_key(
                            ctrl->items[ctrl->active], key))
                        return key;
                    /* Перерисовать только содержимое */
                    ctrl->items[ctrl->active]->draw_content(
                        ctrl->items[ctrl->active]);
                }
            }
        }
        key_prev = key;
    }
}
