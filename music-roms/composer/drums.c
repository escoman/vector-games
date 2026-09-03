/*
 * drums.c — экран ударных (F3) и воспроизведение семплов.
 */
#include "v06.h"
#include <intrinsic.h>
#include "nes_drums.h"
#include "screens.h"

/* Общая функция из main.c */
extern void draw_separator(unsigned char y);

static const char *drum_names[16] = {
    "CLOSED HI-HAT", "OPEN HI-HAT", "SNARE ATTACK",
    "SNARE BODY",    "SNARE STD",   "CYMBAL CRASH",
    "SNARE LOW",     "DIST EXPLOS",  "TOM LOW",
    "TOM RUMBLE",    "HEAVY KICK",  "TIGHT KICK",
    "RUMBLE SUB",    "ULTRA-LO ROAR","SUB-BASS DROP",
    "CRACKLE"
};

void draw_drums(void)
{
    unsigned char i;

    init_screen();
    draw_separator(4);
    graph_print(0, 0,
        "DRUM LIBRARY (0-F TO PLAY)", 1);

    for (i = 0; i < 16; i++) {
        char buf[33];
        unsigned char col = (i < 8) ? 0 : 17;
        unsigned char row = (i < 8) ? i : (unsigned char)(i - 8);
        unsigned char y = (unsigned char)((row + 2) * 10);
        unsigned char hi = (unsigned char)(i < 10 ? '0' + i : 'A' + i - 10);

        buf[0] = (char)hi;
        buf[1] = '-';
        {
            const char *name = drum_names[i];
            unsigned char j = 0;
            while (name[j] && j < 14) {
                buf[j + 2] = name[j];
                j++;
            }
            buf[j + 2] = 0;
        }
        graph_print(col, y, buf, 1);
    }

    graph_print(0, 152, "AP2-RETURN", 1);
}

unsigned char drums_handle_key(unsigned char key)
{
    unsigned char idx = 0xFF;

    if (key == 27)  /* АП2 — возврат */
        return 1;

    if (key >= '0' && key <= '9')
        idx = (unsigned char)(key - '0');
    else if (key >= 'a' && key <= 'f')
        idx = (unsigned char)(key - 'a' + 10);

    if (idx < 16)
        drum_sample_play(nes_drums_samples[idx]);

    return 0;
}

void screen_drums(void)
{
    unsigned char key, prev = 0;
    draw_drums();
    for (;;) {
        wait_frame();
        drum_tick();
        key = kbd_scan();
        if (key != prev && key != 0) {
            if (drums_handle_key(key)) break;
        }
        prev = key;
    }
}
