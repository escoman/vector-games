/*
 * debug_sound.c — диагностика партитурного синтезатора music.c.
 *
 * Счётчики продвижения тональных каналов и ударных для определения
 * рассинхронизации (ТЗ §4-17). Только наблюдение — не влияют на звук.
 *
 * Определения переменных живут здесь; music.c инкрементирует их
 * через extern (tone_event, drum_event, clock_tick, music_tick).
 *
 * Экран диагностики обновляется из основного цикла (не из IRQ —
 * чтобы не портить timing).
 */

#include "v06.h"
#include "debug_sound.h"

/* ----------------------- Счётчики (ТЗ §4-12) ------------------------- */

volatile unsigned long diag_irq_count;
volatile unsigned long diag_music_tick_count;
volatile unsigned long diag_score0_steps;
volatile unsigned long diag_drums_steps;
volatile unsigned long diag_music_time;
volatile unsigned long diag_score0_time;
volatile unsigned long diag_drums_time;
volatile unsigned long diag_score0_finish_irq;
volatile unsigned long diag_drums_finish_irq;
volatile unsigned long diag_score0_finish_time;
volatile unsigned long diag_drums_finish_time;
volatile unsigned long diag_score0_finish_steps;
volatile unsigned long diag_drums_finish_steps;
volatile unsigned char diag_score0_finished;
volatile unsigned char diag_drums_finished;

void diag_reset(void)
{
    diag_irq_count          = 0;
    diag_music_tick_count   = 0;
    diag_score0_steps       = 0;
    diag_drums_steps        = 0;
    diag_music_time         = 0;
    diag_score0_time        = 0;
    diag_drums_time         = 0;
    diag_score0_finish_irq  = 0;
    diag_drums_finish_irq   = 0;
    diag_score0_finish_time = 0;
    diag_drums_finish_time  = 0;
    diag_score0_finish_steps = 0;
    diag_drums_finish_steps = 0;
    diag_score0_finished    = 0;
    diag_drums_finished     = 0;
}

/* ----------------------- Форматирование ------------------------------ */

/* Преобразовать unsigned long в десятичную строку.
 * Буфер buf — минимум 12 байт. */
static void ulong_to_str(unsigned long val, char *buf)
{
    char digits[11];
    int i, j;
    unsigned long p;

    /* Извлекаем 10 цифр: от младшей (10^0) к старшей (10^9). */
    for (i = 9; i >= 0; --i) {
        int d = 0;
        p = 1;
        for (j = 0; j < i; ++j)
            p *= 10;
        while (val >= p) {
            val -= p;
            d++;
        }
        digits[9 - i] = (char)('0' + d);
    }
    digits[10] = '\0';

    /* Убираем лидирующие нули. */
    j = 0;
    while (j < 9 && digits[j] == '0')
        j++;
    for (i = j; digits[i]; ++i)
        *buf++ = digits[i];
    *buf = '\0';
}

/* ------------------- Диагностический экран (ТЗ §13-17) --------------- */

void draw_diag_screen(void)
{
    char num[12];
    unsigned long s0_pos, dr_pos, pos_diff;

    s0_pos   = diag_score0_steps;
    dr_pos   = diag_drums_steps;
    pos_diff = (s0_pos > dr_pos) ? (s0_pos - dr_pos) : (dr_pos - s0_pos);

    /* --- Заголовок --- */
    graph_print(24, 0, "MUSIC DIAGNOSTIC", 8);

    /* --- IRQ / MUSIC --- */
    ulong_to_str(diag_irq_count, num);
    graph_print(24, 16, "IRQ:", 8);
    graph_print(80, 16, num, 8);

    ulong_to_str(diag_music_tick_count, num);
    graph_print(24, 24, "MUSIC:", 8);
    graph_print(80, 24, num, 8);

    ulong_to_str(diag_music_time, num);
    graph_print(152, 24, "TIME:", 8);
    graph_print(200, 24, num, 8);

    /* --- SCORE0 --- */
    graph_print(0, 40, "SCORE0", 8);

    ulong_to_str(diag_score0_steps, num);
    graph_print(8, 48, "STEPS:", 8);
    graph_print(80, 48, num, 8);

    ulong_to_str(diag_score0_time, num);
    graph_print(8, 56, "TIME:",  8);
    graph_print(80, 56, num, 8);

    graph_print(8, 64, "FINISH:", 8);
    graph_print(80, 64,
                diag_score0_finished ? "YES" : "NO ", 8);

    ulong_to_str(diag_score0_finish_irq, num);
    graph_print(8, 72, "F-IRQ:", 8);
    graph_print(80, 72, num, 8);

    ulong_to_str(diag_score0_finish_time, num);
    graph_print(8, 80, "F-TIME:", 8);
    graph_print(80, 80, num, 8);

    /* --- DRUMS --- */
    graph_print(0, 96, "DRUMS", 8);

    ulong_to_str(diag_drums_steps, num);
    graph_print(8, 104, "STEPS:", 8);
    graph_print(80, 104, num, 8);

    ulong_to_str(diag_drums_time, num);
    graph_print(8, 112, "TIME:",  8);
    graph_print(80, 112, num, 8);

    graph_print(8, 120, "FINISH:", 8);
    graph_print(80, 120,
                diag_drums_finished ? "YES" : "NO ", 8);

    ulong_to_str(diag_drums_finish_irq, num);
    graph_print(8, 128, "F-IRQ:", 8);
    graph_print(80, 128, num, 8);

    ulong_to_str(diag_drums_finish_time, num);
    graph_print(8, 136, "F-TIME:", 8);
    graph_print(80, 136, num, 8);

    /* --- DIFF (ТЗ §14-15) --- */
    graph_print(0, 152, "DIFF", 8);

    ulong_to_str(pos_diff, num);
    graph_print(8, 160, "STEPS:", 8);
    graph_print(80, 160, num, 8);

    /* time diff */
    if (diag_score0_time > diag_drums_time) {
        ulong_to_str(diag_score0_time - diag_drums_time, num);
        graph_print(8, 168, "TIME:-", 8);
    } else {
        ulong_to_str(diag_drums_time - diag_score0_time, num);
        graph_print(8, 168, "TIME: ", 8);
    }
    graph_print(80, 168, num, 8);

    /* IRQ diff */
    if (diag_score0_finish_irq > diag_drums_finish_irq) {
        ulong_to_str(diag_score0_finish_irq - diag_drums_finish_irq, num);
        graph_print(8, 176, "IRQ: -", 8);
    } else {
        ulong_to_str(diag_drums_finish_irq - diag_score0_finish_irq, num);
        graph_print(8, 176, "IRQ:  ", 8);
    }
    graph_print(80, 176, num, 8);

    /* --- POS DIFF (ТЗ §16-17) --- */
    ulong_to_str(s0_pos, num);
    graph_print(8, 192, "S0 POS:", 8);
    graph_print(80, 192, num, 8);

    ulong_to_str(dr_pos, num);
    graph_print(8, 200, "DR POS:", 8);
    graph_print(80, 200, num, 8);

    ulong_to_str(pos_diff, num);
    graph_print(8, 208, "PDIFF:", 8);
    graph_print(80, 208, num, 8);
}
