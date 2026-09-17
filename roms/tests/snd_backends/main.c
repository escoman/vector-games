/*
 * main.c — тестовый ROM разделения аудиомодулей Вектора-06Ц (ТЗ §24).
 *
 * В ОДНОМ образе линкуются оба независимых аппаратных модуля:
 *   vi53/ (КР580ВИ53, i8253) — vi53_set_channel / vi53_set_channel_m0;
 *   ay/   (AY-3-8910)        — ay_set_tone / ay_set_envelope / ay_mute_all;
 * плюс шаговый плеер sound.c (sound_*) и ударные drums.asm (drum_*).
 *
 * ROM собран БЕЗ -DMUSIC_ONLY, поэтому доступен шаговый плеер sound_*;
 * vi53_* / ay_* / drum_* объявлены в v06.h безусловно и не зависят от режима.
 *
 * Проверяемые сценарии:
 *   Test 1 (sound → ВИ53): короткая мелодия sound_step_t выводится
 *     плеером sound.c на три канала ВИ53, ударные — на Tape Out (PC0);
 *   Test 4 (ВИ53 + AY одновременно): прямые вызовы vi53_set_channel()
 *     и ay_set_tone() в одном образе — оба устройства звучат разом,
 *     без конфликта портов (ВИ53: 0x08-0x0B, AY: 0x14/0x15).
 *
 * Управление:
 *   1 — мелодия sound_* на ВИ53 (Test 1);
 *   2 — прямой тон ВИ53 (канал 0, 440 Гц);
 *   3 — прямой тон AY (канал A) с огибающей;
 *   4 — удар drum_kick() (маршрут — текущий, см. F1);
 *   5 — ВИ53 + AY одновременно + удар (Test 4);
 *   F1 — маршрут ударных: Tape Out (PC0) ↔ AY Noise C;
 *   F2 — тишина (остановить всё);
 *   СТОП (ESC) — выход из ROM.
 *
 * sound_tick() и drum_tick() вызываются из кадрового прерывания 50 Гц
 * через frame_handler.
 */

#include <intrinsic.h>

#include "v06.h"

static const unsigned char test_pal[16] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xFF, 0x24, 0x12, 0x03, 0x00, 0x00, 0x00, 0x00
};

/* Делители ВИ53 (частота = 1500000 / делитель):
 *   3409 ≈ 440 Гц (ля 1-й октавы), 2867 ≈ 523 Гц (до),
 *   2554 ≈ 587 Гц (ре), 2275 ≈ 659 Гц (ми). */
#define DIV_A4   3409u
#define DIV_C5   2867u
#define DIV_D5   2554u
#define DIV_E5   2275u

/* Короткая шаговая мелодия для sound.c (Test 1). noise: 1 = снейр/том,
 * 2 = бочка (drums.asm, на текущем маршруте). */
static const sound_step_t melody[] = {
    { 12u, DIV_A4, 0u,     0u,     0u },
    { 12u, DIV_C5, 0u,     0u,     2u },
    { 12u, DIV_D5, 0u,     0u,     0u },
    { 12u, DIV_E5, 0u,     0u,     1u },
    { 24u, DIV_A4, DIV_E5, 0u,     0u },
    { 12u, 0u,     0u,     0u,     0u }
};

/* Оба потребителя кадрового прерывания: шаговый плеер и огибающие
 * ударных. */
static void isr_audio(void)
{
    sound_tick();
    drum_tick();
}

static void wait_one_frame(void)
{
    unsigned int start;

    start = frame_count;
    while (frame_count == start)
        intrinsic_halt();
}

/* Локальный флаг маршрута ударных — только для отображения:
 * 0 = Tape Out (PC0, по умолчанию), 1 = AY Noise C. */
static unsigned char route_ay = 0;

static void show_status(const char *msg)
{
    gfx_print(8u, 208u, "STATUS:", 8u);
    /* строка статуса непрозрачная — затираем хвост пробелами */
    gfx_print(64u, 208u, "                    ", 8u);
    gfx_print(64u, 208u, msg, 11u);
    gfx_print(8u, 224u, "DRUM ROUTE: ", 8u);
    gfx_print(104u, 224u, route_ay ? "AY NOISE C" : "TAPE OUT  ", 8u);
}

/* Тишина на всех устройствах. */
static void all_silence(void)
{
    sound_stop();               /* ВИ53 (режим 0) + drum_mute()      */
    vi53_set_channel(0, 0u);
    vi53_set_channel(1, 0u);
    vi53_set_channel(2, 0u);
    ay_mute_all();
}

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;

    frame_handler = isr_audio;
    sound_init();               /* все каналы ВИ53 в тишину          */
    drum_route_tape();          /* маршрут по умолчанию — Tape Out   */
    drum_init();                /* микшер AY: тон C выкл, шум C вкл   */
    ay_mixer_init();            /* тоны A/B/C вкл, R7 = 0xF8          */

    gfx_set_black_palette();
    gfx_clear(0);
    gfx_print(4u, 8u,   "SND BACKENDS TEST", 8u);
    gfx_print(4u, 32u,  "1 - SOUND MELODY (VI53)", 8u);
    gfx_print(4u, 48u,  "2 - VI53 TONE (CH0 440)", 8u);
    gfx_print(4u, 64u,  "3 - AY TONE (CH A + ENV)", 8u);
    gfx_print(4u, 80u,  "4 - DRUM KICK", 8u);
    gfx_print(4u, 96u,  "5 - VI53 + AY TOGETHER", 8u);
    gfx_print(4u, 120u, "F1 - DRUM ROUTE (TAPE/AY)", 8u);
    gfx_print(4u, 136u, "F2 - SILENCE", 8u);
    gfx_print(4u, 152u, "ESC - EXIT", 8u);
    show_status("READY");
    gfx_set_palette(test_pal);

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {
            if (key == 27) {                    /* ESC — выход */
                all_silence();
                break;
            } else if (key == '1') {            /* Test 1: sound_* → ВИ53 */
                all_silence();
                sound_set_data(melody,
                               (unsigned int)(sizeof(melody) / sizeof(melody[0])));
                sound_set_loop(0);
                sound_start();
                show_status("SOUND MELODY (VI53)");
            } else if (key == '2') {            /* прямой тон ВИ53 */
                all_silence();
                vi53_set_channel(0, DIV_A4);
                show_status("VI53 CH0 440 HZ");
            } else if (key == '3') {            /* прямой тон AY + огибающая */
                all_silence();
                ay_set_envelope(AY_CH_A, AY_ENV_DECAY, 8000u);
                ay_set_tone(0, DIV_A4);
                show_status("AY CH A + ENVELOPE");
            } else if (key == '4') {            /* удар */
                drum_kick();
                show_status("DRUM KICK");
            } else if (key == '5') {            /* Test 4: ВИ53 + AY разом */
                all_silence();
                vi53_set_channel(0, DIV_A4);    /* ВИ53 канал 0 */
                ay_set_fixed_volume(AY_CH_A, 15u);
                ay_set_tone(0, DIV_C5);         /* AY канал A   */
                ay_set_tone(1, DIV_E5);         /* AY канал B   */
                drum_kick();
                show_status("VI53 + AY TOGETHER");
            } else if (key == 128) {            /* F1 — маршрут ударных */
                route_ay = (unsigned char)(!route_ay);
                if (route_ay)
                    drum_route_ay();
                else
                    drum_route_tape();
                show_status("DRUM ROUTE SWITCHED");
            } else if (key == 129) {            /* F2 — тишина */
                all_silence();
                show_status("SILENCE");
            }
        }
        prev_key = key;
    }

    return 0;
}
