/*
 * help.c — экран помощи (F1).
 */
#include "v06.h"
#include "screens.h"

void draw_help(void)
{
    init_screen();
    graph_print(0, 0,  "HELP", 1);
    graph_print(0, 16, "NOTES: C D E F G A B (+ -)", 1);
    graph_print(0, 24, "OCTAVE: O0-O7", 1);
    graph_print(0, 32, "LENGTH: L1 L2 L4 L8 L16 L32 L64 L128", 1);
    graph_print(0, 40, "PAUSE: P", 1);
    graph_print(0, 48, "TEMPO: T32-T255", 1);
    graph_print(0, 56, "REPEAT: [ ... ]N", 1);
    graph_print(0, 64, "LOOP: BEGIN ... END", 1);
    graph_print(0, 72, "DRUMS: 0-15 (SAMPLE INDEX)", 1);
    graph_print(0, 96, "AP2-RETURN", 1);
}

void screen_help(void)
{
    draw_help();
    kbd_wait_key(27);
}
