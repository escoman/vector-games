/*
 * help.c — экран помощи (Ф1).
 */
#include "v06.h"
#include "screens.h"

/* Строки справки. Печатаются в цикле с шагом HELP_DY = 10 пикселей:
 * глиф занимает все 8 строк без нижнего пробела, так что строки
 * впритык (шаг 8) наезжают друг на друга. 10 — как в полях textarea.
 * Пустая строка — просто пропуск рядом ниже.
 * Длиннее 32 колонок ни одна строка: за краем экрана адрес следующего
 * символа переходит в соседнюю строку, и хвост затирает её начало. */
#define HELP_DY 10

static const char *help_lines[] = {
    "HELP",
    "",
    "______________________________",
    "NOTES:   C D E F G A B (+ -)",
    "",
    "OCTAVE:  O0-O7",
    "",
    "LENGTH:  L1 L2 L4 L8 L16",
    "         L32 L64 L128",
    "VOLUME:  V1-V15 (AY)",
    "",
    "PAUSE:   P",
    "",
    "TEMPO:   T32-T255",
    "",
    "REPEAT:  [ ... ]N",
    "",
    "LOOP:    BEGIN ... END",
    "",
    "DRUMS:   0-15 (SAMPLE INDEX)",
    "______________________________",
    "",
    "EDIT:    TAB-FIELDS, TYPE TEXT",
    "ARROWS:  MOVE CURSOR IN FIELD",
    "AP2:     SOUND OUT VI53/AY",
};

#define HELP_COUNT (sizeof(help_lines) / sizeof(help_lines[0]))

void draw_help(void)
{
    unsigned char i;

    begin_init_screen();
    for (i = 0; i < HELP_COUNT; i++)
        gfx_print(0, (unsigned char)(i * HELP_DY), help_lines[i], 1);
    end_init_screen();
}

void screen_help(void)
{
    draw_help();
    kbd_wait_key(KBD_KEY_ESC);
}
