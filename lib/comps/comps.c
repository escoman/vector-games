/*
 * comps.c — контроллер UI-компонентов для Вектора-06Ц.
 *
 * Управляет набором компонентов: первичная отрисовка, навигация
 * TAB между компонентами, передача клавиш активному.
 */

#include "comps.h"
#include "v06.h"
#include <intrinsic.h>

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
            } else if (key == 27) {  /* ESC — выход */
                return 27;
            } else if (ctrl->on_key && ctrl->on_key(key)) {
                return key;  /* внешний обработчик перехватил */
            } else {
                /* Передать активному компоненту */
                if (ctrl->items[ctrl->active]->handle_key(
                        ctrl->items[ctrl->active], key))
                    return key;
                /* Перерисовать только содержимое (текст изменился) */
                ctrl->items[ctrl->active]->draw_content(
                    ctrl->items[ctrl->active]);
            }
        }
        key_prev = key;
    }
}
