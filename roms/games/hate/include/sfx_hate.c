/*
 * sfx_hate.c — звук H.A.T.E.: 1-битный бипер на TapeOut (TZ §3.8).
 *
 * Уровень пишется в BSR ПИА1 (порт 00h, D7=0): A=01h — SET PC0,
 * A=00h — RESET PC0 (см. lib/snd/drums.asm, pc0_set). Режимная форма
 * (D7=1) сбросила бы и PC0, и регистр скролла, поэтому пишутся только 0/1.
 *
 * Этап 1 — только мелодия заставки: партитура include/title_music.asm
 * (снята с лога оригинала) и блокирующий плеер include/beep.asm.
 * Игровые SFX со своим планировщиком PC0 — Stage 10; этот файл станет
 * их домом, а beep.asm останется низкоуровневым выводом на PC0.
 */

#include "sfx_hate.h"

/* Блокирующий проигрыватель мелодии (include/beep.asm). */
extern void beep_play_title(void);

void sfx_title_play(void)
{
    beep_play_title();
}
