/*
 * main.c — тестовый ROM партитурного синтезатора Вектора-06Ц
 *          (lib/music.c, сборка с -DMUSIC_ONLY вместо sound.c).
 *
 * Пять тестов из ТЗ, скомпилированы utils/mus2inc.py из music/*.mus:
 *   1 - SCALE      гамма, один тональный канал;
 *   2 - VOICES     три одновременных голоса;
 *   3 - DRUMS      только ударные (семплы .smp);
 *   4 - RHYTHM     смесь L4/L8/L16 + паузы, ударные вдвое чаще;
 *   5 - SYNC       удар точно на начало каждой ноты;
 *   6 - FLIGHT     «Полёт шмеля» (Римский-Корсаков), одноголосая;
 *   7 - GAMMA      гамма вверх-вниз, 0.5 сек на ноту.
 *
 * Управление:
 *   1..7 — выбрать тест и запустить (music_start, с начала);
 *   F1   — пауза / продолжить (music_pause / music_resume);
 *   F2   — остановить (music_stop);
 *   F3   — переключить backend: ВИ53 (i8253) ↔ AY-3-8910.
 *
 * Один music clock ведёт все четыре потока (music_tick), огибающие
 * семплов ударных — drum_tick; обе функции вызываются из кадрового
 * прерывания 50 Гц через frame_handler.
 */

#include <intrinsic.h>

#include "v06.h"

#include "rom_data/scale.inc"
#include "rom_data/voices.inc"
#include "rom_data/drums01.inc"
#include "rom_data/rhythm.inc"
#include "rom_data/sync.inc"
#include "rom_data/flight.inc"
#include "rom_data/gamma.inc"

static const unsigned char synth_pal[16] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xFF, 0x24, 0x12, 0x03, 0x00, 0x00, 0x00, 0x00
};

static const struct {
    const char *title;
    const music_song_t *song;
} songs[] = {
    { "SCALE ",  &scale_song },
    { "VOICES", &voices_song },
    { "DRUMS ",  &drums01_song },
    { "RHYTHM", &rhythm_song },
    { "SYNC  ",   &sync_song },
    { "FLIGHT", &flight_song },
    { "GAMMA ",  &gamma_song },
};

/* Оба потребителя кадрового прерывания: единый music clock и
 * огибающие семплов ударных. */
static void isr_music(void)
{
    music_tick();
    drum_tick();
}

static void wait_one_frame(void)
{
    unsigned int start;

    start = frame_count;
    while (frame_count == start)
        intrinsic_halt();
}

static unsigned char cur_mode = MUSIC_MODE_VI53;

static void show_status(const char *state, const char *title)
{
    /* ячейка 8x8 непрозрачная — перепечатываем строку целиком,
     * хвост затираем пробелами */
    gfx_print(16u, 224u, state, 8u);
    gfx_print(80u, 234u,
              cur_mode == MUSIC_MODE_AY ? "AY      " : "VI53    ", 8u);
    gfx_print(128u, 224u, title, 9u);
}

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;
    unsigned char paused = 0;
    unsigned char cur = 0;

    frame_handler = isr_music;
    drum_init();                /* микшер AY: тон C выкл, шум C вкл */
    music_set_loop(0);          /* без зацикливания */

    gfx_set_black_palette();
    gfx_clear(0);
    gfx_print(2u, 16u, "SYNTH TESTS", 8u);
    gfx_print(2u, 40u, "1 - SCALE (ONE VOICE)", 8u);
    gfx_print(2u, 56u, "2 - VOICES (THREE)", 8u);
    gfx_print(2u, 72u, "3 - DRUMS (SMP)", 8u);
    gfx_print(2u, 88u, "4 - RHYTHM (L4-L16)", 8u);
    gfx_print(2u, 104u, "5 - SYNC (DRUM + NOTE)", 8u);
    gfx_print(2u, 120u, "6 - FLIGHT (BUMBLEBEE)", 8u);
    gfx_print(2u, 136u, "7 - GAMMA (0.5S/NOTE)", 8u);
    gfx_print(2u, 168u, "F1 - PAUSE/RESUME", 8u);
    gfx_print(2u, 184u, "F2 - STOP", 8u);
    gfx_print(2u, 200u, "F3 - BACKEND (VI53/AY)", 8u);
    show_status("STOPPED", "-");
    gfx_set_palette(synth_pal);

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {
            if (key >= '1' && key <= '7') {
                cur = (unsigned char)(key - '1');
                music_set_data(songs[cur].song);
                music_start();
                paused = 0;
                show_status("PLAYING", songs[cur].title);
            } else if (key == 128) {                    /* F1 */
                if (music_is_playing()) {
                    if (!paused) {
                        music_pause();
                        paused = 1;
                        show_status("PAUSED", songs[cur].title);
                    } else {
                        music_resume();
                        paused = 0;
                        show_status("PLAYING", songs[cur].title);
                    }
                }
            } else if (key == 129) {                    /* F2 */
                music_stop();
                paused = 0;
                show_status("STOPPED", songs[cur].title);
            } else if (key == 130) {                    /* F3 */
                cur_mode = (cur_mode == MUSIC_MODE_VI53)
                           ? MUSIC_MODE_AY : MUSIC_MODE_VI53;
                music_mode(cur_mode);
                /* Demo: канал A на AY-огибающую (повторный треугольник, ~144ms/фаза) */
                if (cur_mode == MUSIC_MODE_AY) {
                    ay_set_envelope(AY_CH_A, AY_ENV_7, 500);
                    ay_set_fixed_volume(AY_CH_B, 11);
                }

                show_status(paused ? "PAUSED" :
                            (music_is_playing() ? "PLAYING" : "STOPPED"),
                            songs[cur].title);
            }
        }
        prev_key = key;
    }
}
