/*
 * comps.c — контроллер UI-компонентов для Вектора-06Ц.
 *
 * Управляет набором компонентов: первичная отрисовка, навигация
 * TAB (вперёд) и СС+TAB (назад) между компонентами, передача клавиш
 * активному. Из цикла есть ровно один выход — когда on_key вернёт
 * код >1: контроллер не знает ни про какие клавиши, кроме TAB,
 * решение о выходе принимает приложение.
 */

#include "comps.h"
#include "v06.h"

/* Состояние модификатора СС: по нему TAB с СС переключает фокус назад
 * (см. controller_run). Заполняется в kbdscan.asm при опросе матрицы. */
extern unsigned char kbd_shift_state;

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

/* Отрисовать все компоненты контроллера: активный — с фокусом
 * (у textarea это инверсия метки), остальные — без. Экран, который сам
 * красит свою подложку, зовёт это из своего paint() — до возврата
 * рабочей палитры, чтобы процесс отрисовки не мелькал. controller_run
 * делает тот же вызов при входе, поэтому экрану, который рисовать себя
 * сам не хочет, достаточно просто запустить цикл. */
void controller_draw(controller_t *ctrl)
{
    unsigned char i;

    for (i = 0; i < ctrl->count; i++)
        ctrl->items[i]->draw(ctrl->items[i],
                             (unsigned char)(i == ctrl->active));
}

unsigned char controller_run(controller_t *ctrl)
{
    unsigned char key, key_prev = 0;

    if (ctrl->count == 0) return 0;

    for (;;) {
        v06_wait_frame();
        key = kbd_scan();

        if (key != key_prev && key != 0) {
            if (key == KBD_KEY_TAB) {  /* ТАБ — переключение (СС+ТАБ — назад) */
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
                     * текста/прокрутки, либо только курсор при навигации.
                     * Выбраться из цикла он оттуда не может. */
                    ctrl->items[ctrl->active]->handle_key(
                        ctrl->items[ctrl->active], key);
                }
            }
        }
        key_prev = key;
    }
}
