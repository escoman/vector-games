/*
 * main.c — тест UI-компонентов для Вектора-06Ц.
 *
 * Два edit-поля и один textarea (многострочный), навигация TAB,
 * внешний обработчик F1 (счётчик нажатий внизу экрана).
 * ESC — выход.
 */

#include <intrinsic.h>
#include <string.h>
#include "v06.h"
#include "comps.h"

static const unsigned char pal[2] = {
    V06_RGB(0, 0, 0),   /* 0: чёрный */
    V06_RGB(7, 7, 3),   /* 1: белый */
};

static char name_buf[32];
static char score_buf[64];
static char note_buf[128];

static textarea_t name_field;
static textarea_t score_field;
static textarea_t note_area;
static controller_t ctrl;

static unsigned char f1_count;

/* Внешний обработчик клавиш */
static unsigned char on_key(unsigned char key)
{
    if (key == 128) {  /* F1 — счётчик */
        char buf[16];

        f1_count++;
        unsigned char pos = 0;
        buf[pos++] = 'F';
        buf[pos++] = '1';
        buf[pos++] = ':';
        buf[pos++] = ' ';
        if (f1_count >= 10)
            buf[pos++] = '0' + (f1_count / 10);
        buf[pos++] = '0' + (f1_count % 10);
        buf[pos] = 0;
        graph_print(0, 248, buf, 1);
        return 1;
    }
    return 0;
}

int main(void)
{
    /* Инициализация экрана */
    gfx_set_mode(GFX_MODE_256_2);
    gfx_set_palette(pal);
    gfx_clear(0);

    /* Заголовок */
    graph_print(0, 0, "EDIT / TEXTAREA TEST", 1);
    graph_print(0, 8, "______________________", 1);

    /* Edit-поля (однострочные) */
    edit_init(&name_field, name_buf, sizeof(name_buf) - 1,
              20, 1, 20, "NAME");
    edit_init(&score_field, score_buf, sizeof(score_buf) - 1,
              20, 1, 60, "SCORE");

    /* Textarea (многострочное, 3 видимые строки) */
    textarea_init(&note_area, note_buf, sizeof(note_buf) - 1,
                  20, 5, 1, 100, "NOTES");

    /* Контроллер */
    controller_init(&ctrl);
    controller_add(&ctrl, (component_t *)&name_field);
    controller_add(&ctrl, (component_t *)&score_field);
    controller_add(&ctrl, (component_t *)&note_area);
    ctrl.on_key = on_key;

    /* Запуск — TAB переключение, ESC выход */
    controller_run(&ctrl);

    return 0;
}
