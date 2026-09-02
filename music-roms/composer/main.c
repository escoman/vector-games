/*
 * main.c — приложение "Композитор" для Вектора-06Ц.
 *
 * Музыкальный редактор с текстовым вводом партитур (.mus формат).
 * 3 тоновых голоса + ударные, проигрывание с подсветкой.
 * Экран 256x256x2, монохромный. Подсветка — инверсией символов.
 *
 * Ф1 — помощь, Ф2 — играть/стоп, Ф3 — ударные, Ф4 — библиотека, Ф5 — о программе.
 * Стрелки + ВК — навигация, выбор SCORE/DRUMS, вход в редактор.
 * ESC — возврат на главный экран.
 */

#include <intrinsic.h>
#include <string.h>
#include "v06.h"
#include "parser.h"
#include "editor.h"
#include "nes_drums.h"
#include "screens.h"

/* Инверсия символов в режиме 256x256x2 (плоскость 0xE000).
 * Инвертирует 9 строк: 1 выше + 8 глифа — целостная инверсия. */
void invert_chars(unsigned char col, unsigned char row,
                         unsigned char count)
{
    unsigned char c, r;
    volatile unsigned char *p;
    for (c = 0; c < count; c++) {
        p = (volatile unsigned char *)(0xE000 + (unsigned int)(col + c) * 256
                                       + (255 - row));
        for (r = 0; r < 9; r++) {
            *p ^= 0xFF;
            p--;
        }
    }
}

/* ------------------------------- Палитра ---------------------------- */

static const unsigned char composer_pal[2] = {
    V06_RGB(0, 0, 0),   /* 0: чёрный (фон) */
    V06_RGB(7, 7, 3),   /* 1: белый (текст) */
};

/* ------------------------------- Константы -------------------------- */

#define SCR_ROWS   32
#define TEXT_X     0
#define TEXT_W     32
#define PREVIEW_H  5
#define EDIT_VISIBLE 27

/* --------------------------- Пул-аллокатор -------------------------- */

/* Простой bump-аллокатор в статическом пуле.
 * Контролируем, чтобы выделенная память не залезала в VRAM (0x8000). */
#define POOL_SIZE 1024   /* 4 канала × 256 байт */
static unsigned char mem_pool[POOL_SIZE];
static unsigned int pool_used = 0;

static char *pool_alloc(unsigned int size)
{
    char *p;
    if (pool_used + size > POOL_SIZE) return (char *)0;
    p = (char *)(mem_pool + pool_used);
    pool_used += size;
    return p;
}

/* Общая свободная память: от конца BSS до VRAM (0xE000).
 * pool_end — адрес конца пула (он в конце BSS). */
extern unsigned char _bss_compiler_tail;

static unsigned int free_ram(void)
{
    unsigned int bss_end = (unsigned int)&_bss_compiler_tail;
    if (bss_end >= 0xE000) return 0;
    return 0xE000 - bss_end;
}

/* --------------------------- Глобальные данные ---------------------- */

static char *score_text[4];

static unsigned char bc_buf[4][PARSER_BC_SIZE];
static music_song_t song;

static unsigned int line_map[4][PARSER_MAX_LINES];
static unsigned char line_count[4];
static unsigned int play_ticks;
static unsigned char cur_line_ch[4];
static unsigned char playing;

static unsigned char sel_item;

static unsigned char key_prev;

/* ------------------------- Встроенный пример ------------------------ */

static const char default_s0[] = "O4 L4 C D E F G A B O5 C";
static const char default_s1[] = "O3 L4 C E G C E G O4 C E";
static const char default_s2[] = "O2 L2 C G C G";
static const char default_dr[] = "L4 0 P 2 P 0 P 4 P\nL4 8 P 10 P 8 P 10 P";

/* ------------------------- Прототипы ------------------------------- */

void wait_frame(void);
static void draw_main(void);
void playback_start(void);
void playback_stop(void);

/* ------------------------- Кадровый обработчик --------------------- */

static void on_frame(void)
{
    unsigned char ch;

    music_tick();
    drum_tick();

    if (!playing) return;

    play_ticks++;
    for (ch = 0; ch < 4; ch++) {
        unsigned char ln;
        cur_line_ch[ch] = 0;
        for (ln = 0; ln < line_count[ch]; ln++) {
            if (line_map[ch][ln] <= play_ticks)
                cur_line_ch[ch] = ln;
        }
    }
}

/* ------------------------- Утилиты --------------------------------- */

void wait_frame(void)
{
    unsigned int s = frame_count;
    while (frame_count == s)
        intrinsic_halt();
}

void init_screen(void)
{
    gfx_set_mode(GFX_MODE_256_2);
    gfx_set_palette(composer_pal);
    gfx_clear(0);
}

void draw_separator(unsigned char y)
{
    graph_print(0, y,
        "--------------------------------", 1);
}

/* Инвертировать метку F2-PLAY в заголовке (XOR-тоггл). */
static void invert_play_label(void)
{
    invert_chars(8, 7, 7);
}

/* Инвертировать/деинвертировать метку [EDIT] для секции.
 * XOR-свойство: повторный вызов возвращает текст в исходное состояние. */
static void invert_section(unsigned char sec)
{
    unsigned char row = sec * 7 + 3;
    unsigned char y = (unsigned char)(row * 8);

    /* Инвертируем только [EDIT] (6 символов начиная с col 9) */
    invert_chars(9, (unsigned char)(y - 1), 6);
}

/* ------------------------- Проигрывание ---------------------------- */

void playback_stop(void)
{
    playing = 0;
    music_stop();
    drum_mute();
    frame_handler = 0;
}

void playback_solo(unsigned char ch)
{
    if (!playing) return;
    if (ch == 0) song.s0 = 0;
    else if (ch == 1) song.s1 = 0;
    else if (ch == 2) song.s2 = 0;
    else song.dr = 0;
}

void playback_start(void)
{
    parse_result_t res;
    unsigned char ch;
    unsigned char tempo = 120;

    /* Парсинг всех 4 каналов */
    for (ch = 0; ch < 4; ch++) {
        if (score_text[ch][0] == 0) {
            bc_buf[ch][0] = MUS_END;
            line_count[ch] = 0;
            continue;
        }
        parse_score(&res, score_text[ch], bc_buf[ch],
                    PARSER_BC_SIZE, (ch == 3) ? 1 : 0);
        if (!res.ok) {
            /* Ошибка парсинга — мигнём красным */
            gfx_clear(0);
            graph_print(0, 64, "PARSE ERROR", 1);
            return;
        }
    }

    /* Заполнение song */
    {
        const char *texts[4];
        for (ch = 0; ch < 4; ch++)
            texts[ch] = score_text[ch][0] ? score_text[ch] : (const char *)0;
        parse_song(&res, texts, bc_buf, tempo, nes_drums_samples, &song);
        if (!res.ok) return;
    }

    /* Построение таблицы строк для подсветки */
    for (ch = 0; ch < 4; ch++) {
        if (score_text[ch][0])
            line_count[ch] = build_line_map(score_text[ch],
                line_map[ch], PARSER_MAX_LINES, (ch == 3) ? 1 : 0);
        else
            line_count[ch] = 0;
    }

    /* Запуск */
    play_ticks = 0;
    memset(cur_line_ch, 0, sizeof(cur_line_ch));
    playing = 1;
    frame_handler = on_frame;
    drum_init();
    music_set_data(&song);
    music_set_loop(0);
    music_start();
}

/* ------------------------- Главный экран --------------------------- */

static void draw_main(void)
{
    unsigned char sec;
    unsigned char y;

    init_screen();

    /* Заголовок (строка 1, y=8) */
    graph_print(0, 8,
        "F1-HELP F2-PLAY F3-DRUMS F4-LIB", 1);
    if (playing)
        invert_play_label();

    for (sec = 0; sec < 4; sec++) {
        unsigned char row = sec * 7 + 3;
        y = (unsigned char)(row * 8);

        /* Метка секции */
        if (sec < 3) {
            char label[16];
            label[0] = 'S'; label[1] = 'C'; label[2] = 'O';
            label[3] = 'R'; label[4] = 'E'; label[5] = ' ';
            label[6] = (char)('1' + sec);
            label[7] = ':'; label[8] = ' ';
            label[9] = '['; label[10] = 'E'; label[11] = 'D';
            label[12] = 'I'; label[13] = 'T'; label[14] = ']';
            label[15] = 0;
            graph_print(0, y, label, 1);
            if (sel_item == sec && !playing)
                invert_section(sec);
        } else {
            graph_print(0, y, "DRUMS:   [EDIT]", 1);
            if (sel_item == sec && !playing)
                invert_section(sec);
        }

        /* Разделитель */
        draw_separator((unsigned char)(y + 8));

        /* Превью текста (3 строки) */
        {
            unsigned char ln;
            const char *p = score_text[sec];
            for (ln = 0; ln < PREVIEW_H; ln++) {
                unsigned char cy = (unsigned char)((row + 2 + ln) * 8);

                if (*p) {
                    char buf[33];
                    unsigned char i = 0;
                    while (*p && *p != '\n' && i < 32) {
                        buf[i] = (*p >= 'a' && *p <= 'z')
                                 ? (char)(*p - 32) : *p;
                        i++;
                        p++;
                    }
                    buf[i] = 0;
                    if (*p == '\n') p++;
                    graph_print(0, cy, buf, 1);
                }
            }
        }
    }

    /* Свободная память RAM + F5-ABOUT (внизу экрана) */
    {
        unsigned int fr = free_ram();
        char mem[33];
        unsigned char pos = 0;
        const char *label = "FREE:";
        while (*label) { mem[pos++] = *label++; }
        if (fr >= 10000) mem[pos++] = (char)('0' + (unsigned char)(fr / 10000));
        if (fr >= 1000)  mem[pos++] = (char)('0' + (unsigned char)((fr / 1000) % 10));
        if (fr >= 100)   mem[pos++] = (char)('0' + (unsigned char)((fr / 100) % 10));
        if (fr >= 10)    mem[pos++] = (char)('0' + (unsigned char)((fr / 10) % 10));
        mem[pos++] = (char)('0' + (unsigned char)(fr % 10));
        mem[pos++] = 'B';
        while (pos < 24) mem[pos++] = ' ';
        mem[24] = 'F'; mem[25] = '5'; mem[26] = '-'; mem[27] = 'A';
        mem[28] = 'B'; mem[29] = 'O'; mem[30] = 'U'; mem[31] = 'T';
        mem[32] = 0;
        graph_print(0, 248, mem, 1);
    }
}

/* ------------------------- main ------------------------------------ */

int main(void)
{
    unsigned char key;

    /* Инициализация данных — динамическое выделение из пула */
    for (key = 0; key < 4; key++) {
        score_text[key] = pool_alloc(256);
        if (score_text[key])
            memset(score_text[key], 0, 256);
    }
    memcpy(score_text[0], default_s0, sizeof(default_s0));
    memcpy(score_text[1], default_s1, sizeof(default_s1));
    memcpy(score_text[2], default_s2, sizeof(default_s2));
    memcpy(score_text[3], default_dr, sizeof(default_dr));

    playing = 0;
    sel_item = 0;
    key_prev = 0;

    /* Начальная отрисовка */
    drum_init();
    draw_main();

    for (;;) {
        wait_frame();

        if (playing && !music_is_playing()) {
            playing = 0;
            drum_mute();
            frame_handler = 0;
        }

        key = kbd_scan();

        if (key != key_prev && key != 0) {
            if (key == 128) {          /* F1 — Help */
                screen_help();
                draw_main();
            } else if (key == 129) {   /* F2 — Play/Stop */
                if (playing) {
                    playback_stop();
                } else {
                    playback_start();
                }
                draw_main();
            } else if (key == 130) {   /* F3 — Drums */
                screen_drums();
                draw_main();
            } else if (key == 131) {   /* F4 — Lib (placeholder) */
            } else if (key == 132) {   /* F5 — About */
                screen_about();
                draw_main();
            } else if (key == 11) {    /* Up */
                if (sel_item > 0) sel_item--;
            } else if (key == 10) {    /* Down */
                if (sel_item < 3) sel_item++;
            } else if (key == 13) {    /* Enter — Edit */
                screen_editor(sel_item, score_text);
                draw_main();
            }
        }
        key_prev = key;
    }
}
