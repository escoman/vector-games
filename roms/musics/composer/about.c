/*
 * about.c — экран "О программе" (Ф5).
 */
#include "v06.h"
#include "screens.h"

void draw_about(void)
{
    begin_init_screen();
    gfx_print(0, 0,  "COMPOSER", 1);
    gfx_print(0, 24, "MUSIC EDITOR FOR VECTOR-06C", 1);
    gfx_print(0, 40, "VERSION 1.0", 1);

    gfx_print(0, 88, "AP2-RETURN", 1);
    end_init_screen();
}

void screen_about(void)
{
    draw_about();
    kbd_wait_key(KBD_KEY_ESC);
}
