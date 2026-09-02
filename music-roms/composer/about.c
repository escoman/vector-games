/*
 * about.c — экран "О программе" (F5).
 */
#include "v06.h"
#include "screens.h"

void draw_about(void)
{
    init_screen();
    graph_print(0, 0,  "COMPOSER", 3);
    graph_print(0, 24, "MUSIC EDITOR FOR VECTOR-06C", 3);
    graph_print(0, 40, "VERSION 1.0", 3);
    graph_print(0, 64, "AP2-RETURN", 3);
}
