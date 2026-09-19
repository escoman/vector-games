/*
 * main.c — тестовый ROM разделения аудиомодулей Вектора-06Ц (ТЗ §24).
 *
 * В ОДНОМ образе линкуются оба независимых аппаратных модуля:
 *   vi53/ (КР580ВИ53, i8253) — vi53_set_channel / vi53_set_channel_m0;
 *   ay/   (AY-3-8910)        — ay_set_tone_period / ay_set_envelope / ay_mute_all;
 * плюс шаговый плеер sound.c (sound_*) и ударные drums.asm (drum_*).
 *
 * ROM собран БЕЗ -DMUSIC_ONLY, поэтому доступен шаговый плеер sound_*;
 * vi53_* / ay_* / drum_* объявлены в v06.h безусловно и не зависят от режима.
 *
 * Проверяемые сценарии:
 *   Test 1 (sound → ВИ53): короткая мелодия sound_step_t выводится
 *     плеером sound.c на три канала ВИ53, ударные — на Tape Out (PC0);
 *   Test 4 (ВИ53 + AY одновременно): прямые вызовы vi53_set_channel()
 *     и ay_set_tone_period() в одном образе — оба устройства звучат разом,
 *     без конфликта портов (ВИ53: 0x08-0x0B, AY: 0x14/0x15).
 *     Высоты нот берутся из v06_div_tab[]/v06_ay_period_tab[]
 *     через макросы DIV_OF()/AY_PER() — без 32-битного деления.
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

/* Делители ВИ53 (частота = 1500000 / делитель).
 * В static-инициализаторе массива struct нужна compile-time
 * константа, поэтому значения приведены буквально (те же, что
 * в v06_div_tab[N_*()]). Runtime-вызовы ниже идут через
 * DIV_OF()/AY_PER() — по таблице, без 32-битного деления. */
static const sound_step_t melody[] = {
    { 12u, 3409u,    0u,   0u,   0u },   /* A4 = 440 Гц */
    { 12u, 2867u,    0u,   0u,   2u },   /* C5 = 523 Гц */
    { 12u, 2554u,    0u,   0u,   0u },   /* D5 = 587 Гц */
    { 12u, 2275u,    0u,   0u,   1u },   /* E5 = 659 Гц */
    { 24u, 3409u, 2275u,   0u,   0u },   /* A4 + E5      */
    { 12u,    0u,    0u,   0u,   0u }    /* тишина        */
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
    show_status("READY");
    gfx_set_palette(test_pal);

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {
            if (key == '1') {            /* Test 1: sound_* → ВИ53 */
                all_silence();
                sound_set_data(melody,
                               (unsigned int)(sizeof(melody) / sizeof(melody[0])));
                sound_set_loop(0);
                sound_start();
                show_status("SOUND MELODY (VI53)");
            } else if (key == '2') {            /* прямой тон ВИ53 */
                all_silence();
                vi53_set_channel(0, DIV_OF(N_A(4)));
                show_status("VI53 CH0 440 HZ");
            } else if (key == '3') {            /* прямой тон AY + огибающая */
                all_silence();
                ay_set_envelope(AY_CH_A, AY_ENV_DECAY, 8000u);
                ay_set_tone_period(0, AY_PER(N_A(4)));
                show_status("AY CH A + ENVELOPE");
            } else if (key == '4') {            /* удар */
                drum_kick();
                show_status("DRUM KICK");
            } else if (key == '5') {            /* Test 4: ВИ53 + AY разом */
                all_silence();
                vi53_set_channel(0, DIV_OF(N_A(4)));    /* ВИ53 канал 0 */
                ay_set_fixed_volume(AY_CH_A, 15u);
                ay_set_tone_period(0, AY_PER(N_C(5)));  /* AY канал A   */
                ay_set_tone_period(1, AY_PER(N_E(5)));  /* AY канал B   */
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
