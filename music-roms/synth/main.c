/*
 * main.c — тестовый ROM партитурного синтезатора Вектора-06Ц
 *          (lib/music.c, сборка с -DMUSIC_ONLY вместо sound.c).
 *
 * Пять тестов из ТЗ, скомпилированы utils/mus2inc.py из music/*.mus:
 *   1 - SCALE      гамма, один тональный канал;
 *   2 - VOICES     три одновременных голоса;
 *   3 - DRUMS      только ударные (семплы .smp);
 *   4 - RHYTHM     смесь L4/L8/L16 + паузы, ударные вдвое чаще;
 *   5 - SYNC       удар точно на начало каждой ноты.
 *
 * Управление:
 *   1..5    — выбрать тест и запустить (music_start, с начала);
 *   ВК/ПРБЛ — пауза / продолжить (music_pause / music_resume);
 *   0       — остановить (music_stop);
 *   СТОП    — выход из ROM.
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

static const unsigned char synth_pal[16] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xFF, 0x24, 0x12, 0x03, 0x00, 0x00, 0x00, 0x00
};

static const struct {
    const char *title;
    const music_song_t *song;
} songs[] = {
    { "SCALE",  &scale_song },
    { "VOICES", &voices_song },
    { "DRUMS",  &drums01_song },
    { "RHYTHM", &rhythm_song },
    { "SYNC",   &sync_song },
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

static void show_status(const char *state, const char *title)
{
    /* ячейка 8x8 непрозрачная — перепечатываем строку целиком,
     * хвост затираем пробелами */
    graph_print(16u, 224u, state, 8u);
    graph_print(128u, 224u, title, 9u);
    //graph_print(200u, 224u, "        ", 8u);
}

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;
    unsigned char paused = 0;
    unsigned char cur = 0;

    frame_handler = isr_music;
    drum_init();                /* микшер AY: тон C выкл, шум C вкл */
    music_set_loop(1);          /* тесты крутятся по кругу */

    graph_set_black_palette();
    graph_clear(0);
    graph_print(16u, 16u, "SYNTH TESTS (MUSIC.C):", 8u);
    graph_print(16u, 40u, "1 - SCALE (ONE VOICE)", 8u);
    graph_print(16u, 56u, "2 - VOICES (THREE)", 8u);
    graph_print(16u, 72u, "3 - DRUMS (SMP)", 8u);
    graph_print(16u, 88u, "4 - RHYTHM (L4-L16)", 8u);
    graph_print(16u, 104u, "5 - SYNC (DRUM + NOTE)", 8u);
    graph_print(16u, 136u, "VK/PBL - PAUSE/RESUME", 8u);
    graph_print(16u, 152u, "0 - STOP", 8u);
    graph_print(16u, 168u, "ESC - EXIT", 8u);
    show_status("STOPPED", "-");
    graph_set_palette(synth_pal);

    for (;;) {
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {
            if (key >= '1' && key <= '5') {
                cur = (unsigned char)(key - '1');
                music_set_data(songs[cur].song);
                music_start();
                paused = 0;
                show_status("PLAYING", songs[cur].title);
            } else if (key == 13 || key == ' ') {   /* ВК / пробел */
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
            } else if (key == '0') {
                music_stop();
                paused = 0;
                show_status("STOPPED", songs[cur].title);
            } else if (key == 27) {                 /* СТОП (ESC) */
                break;
            }
        }
        prev_key = key;
    }

    music_stop();
    return 0;
}
