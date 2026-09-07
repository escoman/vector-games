/*
 * debug_sound.h — диагностика партитурного синтезатора music.c.
 *
 * Счётчики продвижения тональных каналов и ударных для определения
 * рассинхронизации. Только наблюдение — не влияют на звук.
 * Подключается к music.c через extern-переменные; инкременты
 * остаются в tone_event / drum_event / clock_tick / music_tick.
 */

#ifndef DEBUG_SOUND_H
#define DEBUG_SOUND_H

/* ------ Счётчики (определены в debug_sound.c) ------ */

extern volatile unsigned long diag_irq_count;
extern volatile unsigned long diag_music_tick_count;
extern volatile unsigned long diag_score0_steps;
extern volatile unsigned long diag_drums_steps;
extern volatile unsigned long diag_music_time;
extern volatile unsigned long diag_score0_time;
extern volatile unsigned long diag_drums_time;
extern volatile unsigned long diag_score0_finish_irq;
extern volatile unsigned long diag_drums_finish_irq;
extern volatile unsigned long diag_score0_finish_time;
extern volatile unsigned long diag_drums_finish_time;
extern volatile unsigned long diag_score0_finish_steps;
extern volatile unsigned long diag_drums_finish_steps;
extern volatile unsigned char diag_score0_finished;
extern volatile unsigned char diag_drums_finished;

/* ------ API ------ */

/* Сброс всех счётчиков (вызывается из music_start). */
extern void diag_reset(void);

/* Отрисовка диагностического экрана (graph_print). */
extern void draw_diag_screen(void);

#endif /* DEBUG_SOUND_H */
