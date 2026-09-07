/*
 * editor.c — линейный текстовый редактор для .mus текста.
 *
 * Буфер строк фиксированной длины, навигация стрелками,
 * вставка/удаление символов, прокрутка, отрисовка graph_put_char().
 * Все введённые символы приводятся к верхнему регистру.
 */

#include "editor.h"
#include "v06.h"
#include <intrinsic.h>
#include "screens.h"
#include <string.h>

/* Инверсия символов — из main.c (256x256x2, плоскость 0xE000) */
extern void invert_chars(unsigned char col, unsigned char row,
                         unsigned char count);

/* ------------------------- Вспомогательные --------------------------- */

/* Длина строки (без \0) */
static unsigned char str_len(const char *s)
{
    unsigned char n = 0;
    while (*s++) n++;
    return n;
}

/* Приведение к верхнему регистру */
static char to_upper(char ch)
{
    if (ch >= 'a' && ch <= 'z')
        return ch - 32;
    return ch;
}

/* ------------------------- Публичные функции ------------------------- */

void editor_init(editor_t *ed)
{
    memset(ed, 0, sizeof(*ed));
    ed->num_lines = 1;
    ed->lines[0][0] = 0;
    ed->visible = 26;  /* по умолчанию (main.c может переопределить) */
}

void editor_load(editor_t *ed, const char *text)
{
    unsigned char i;

    memset(ed, 0, sizeof(*ed));
    ed->num_lines = 1;

    if (!text || !*text) {
        ed->lines[0][0] = 0;
        return;
    }

    ed->num_lines = 0;
    while (*text && ed->num_lines < EDITOR_MAX_LINES) {
        i = 0;
        while (*text && *text != '\n' && i < EDITOR_MAX_COLS - 1) {
            ed->lines[ed->num_lines][i] = to_upper(*text);
            i++;
            text++;
        }
        ed->lines[ed->num_lines][i] = 0;
        ed->num_lines++;
        if (*text == '\n')
            text++;
    }

    if (ed->num_lines == 0) {
        ed->num_lines = 1;
        ed->lines[0][0] = 0;
    }
}

void editor_save(editor_t *ed, char *buf, unsigned int buf_size)
{
    unsigned char i;
    unsigned int pos = 0;

    for (i = 0; i < ed->num_lines && pos < buf_size - 1; i++) {
        const char *s = ed->lines[i];
        while (*s && pos < buf_size - 1)
            buf[pos++] = *s++;
        if (i < ed->num_lines - 1 && pos < buf_size - 1)
            buf[pos++] = '\n';
    }
    buf[pos] = 0;
}

void editor_draw(editor_t *ed, unsigned char x, unsigned char y,
                 unsigned char color)
{
    unsigned char row;
    unsigned char slen;
    static unsigned char draw_buf[EDITOR_MAX_COLS + 1];
    unsigned char cursor_on;
    unsigned char i;
    unsigned char scr_row;
    unsigned char scr_col;
    unsigned char chunk;
    unsigned char chunk_len;

    /* Прокрутка: удерживать курсор в видимой области */
    if (ed->cur_line < ed->scroll)
        ed->scroll = ed->cur_line;
    if (ed->cur_line >= ed->scroll + ed->visible)
        ed->scroll = ed->cur_line - ed->visible + 1;

    /* Мигание курсора (~500мс при 50Гц) */
    cursor_on = ((frame_count >> 4) & 1) ? 0 : 1;

    scr_row = 0;

    for (row = 0; row < ed->visible; row++) {
        unsigned char line_idx = ed->scroll + row;

        if (line_idx >= ed->num_lines) {
            draw_buf[0] = ' ';
            draw_buf[1] = 0;
            graph_print(x, (unsigned char)(y + scr_row * 8),
                            (const char *)draw_buf, color);
            scr_row++;
            continue;
        }

        slen = str_len(ed->lines[line_idx]);

        /* Визуальный перенос: каждые 31 символ — на новую экранную строку */
        chunk = 0;
        while (scr_row < ed->visible) {
            unsigned char start = (unsigned char)(chunk * 31);
            if (start >= slen && chunk > 0) break;

            chunk_len = (slen > start)
                        ? (unsigned char)(slen - start) : 0;
            if (chunk_len > 31) chunk_len = 31;

            /* Заполнить буфер отрисовки */
            for (i = 0; i < 31; i++) {
                if (i < chunk_len)
                    draw_buf[i] = ed->lines[line_idx][start + i];
                else
                    draw_buf[i] = ' ';
            }
            draw_buf[31] = 0;

            /* Позиция курсора в экранных координатах */
            scr_col = 0xFF;
            if (cursor_on && line_idx == ed->cur_line) {
                if (ed->cur_col >= start &&
                    ed->cur_col < start + 31) {
                    scr_col = (unsigned char)(ed->cur_col - start);
                } else if (ed->cur_col == slen &&
                           slen >= start && slen < start + 31) {
                    scr_col = (unsigned char)(slen - start);
                }
            }

            if (scr_col != 0xFF) {
                if (draw_buf[scr_col] == ' ')
                    draw_buf[scr_col] = '#';
            }

            graph_print(x, (unsigned char)(y + scr_row * 8),
                            (const char *)draw_buf, color);

            if (scr_col != 0xFF) {
                invert_chars((unsigned char)(x + scr_col),
                    (unsigned char)(y + scr_row * 8 - 1), 1);
            }

            scr_row++;
            chunk++;
            if (start + 31 >= slen) break;
        }
    }
}

unsigned char editor_handle_key(editor_t *ed, unsigned char key)
{
    unsigned char slen;
    unsigned char i;

    if (key == 27)  /* АП2 — выход */
        return 1;

    if (key == 11) {  /* Стрелка вверх */
        if (ed->cur_line > 0) {
            ed->cur_line--;
            slen = str_len(ed->lines[ed->cur_line]);
            if (ed->cur_col > slen)
                ed->cur_col = slen;
        }
        return 0;
    }

    if (key == 10) {  /* Стрелка вниз */
        if (ed->cur_line < ed->num_lines - 1) {
            ed->cur_line++;
            slen = str_len(ed->lines[ed->cur_line]);
            if (ed->cur_col > slen)
                ed->cur_col = slen;
        }
        return 0;
    }

    if (key == 8) {  /* Стрелка влево */
        if (ed->cur_col > 0) {
            ed->cur_col--;
        } else if (ed->cur_line > 0) {
            ed->cur_line--;
            ed->cur_col = str_len(ed->lines[ed->cur_line]);
        }
        return 0;
    }

    if (key == 9) {  /* Стрелка вправо */
        slen = str_len(ed->lines[ed->cur_line]);
        if (ed->cur_col < slen) {
            ed->cur_col++;
        } else if (ed->cur_line < ed->num_lines - 1) {
            ed->cur_line++;
            ed->cur_col = 0;
        }
        return 0;
    }

    if (key == 13) {  /* ВК (Enter) — разрыв строки */
        if (ed->num_lines < EDITOR_MAX_LINES) {
            /* Вставить новую строку после текущей */
            unsigned char nl = ed->cur_line + 1;
            /* Сдвинуть строки вниз */
            for (i = ed->num_lines; i > nl; i--) {
                memcpy(ed->lines[i], ed->lines[i - 1], EDITOR_MAX_COLS);
            }
            /* Часть текущей строки после курсора — в новую */
            slen = str_len(ed->lines[ed->cur_line]);
            if (ed->cur_col < slen) {
                unsigned char tail = slen - ed->cur_col;
                memcpy(ed->lines[nl],
                       ed->lines[ed->cur_line] + ed->cur_col, tail);
                ed->lines[nl][tail] = 0;
                ed->lines[ed->cur_line][ed->cur_col] = 0;
            } else {
                ed->lines[nl][0] = 0;
            }
            ed->num_lines++;
            ed->cur_line = nl;
            ed->cur_col = 0;
        }
        return 0;
    }

    if (key == 12) {  /* ЗАБ (Backspace) — удаление слева */
        if (ed->cur_col > 0) {
            /* Удалить символ слева в текущей строке */
            slen = str_len(ed->lines[ed->cur_line]);
            for (i = ed->cur_col - 1; i < slen; i++) {
                ed->lines[ed->cur_line][i] = ed->lines[ed->cur_line][i + 1];
            }
            ed->cur_col--;
        } else if (ed->cur_line > 0) {
            /* Слить с предыдущей строкой */
            unsigned char prev = ed->cur_line - 1;
            unsigned char prev_len = str_len(ed->lines[prev]);
            slen = str_len(ed->lines[ed->cur_line]);
            /* Добавить текущую строку к предыдущей */
            for (i = 0; i <= slen; i++) {
                if (prev_len + i < EDITOR_MAX_COLS)
                    ed->lines[prev][prev_len + i] =
                        ed->lines[ed->cur_line][i];
            }
            /* Удалить текущую строку */
            for (i = ed->cur_line; i < ed->num_lines - 1; i++) {
                memcpy(ed->lines[i], ed->lines[i + 1], EDITOR_MAX_COLS);
            }
            ed->num_lines--;
            ed->cur_line = prev;
            ed->cur_col = prev_len;
        }
        return 0;
    }

    /* Обычный символ — вставка */
    if (key >= 32 && key < 127) {
        slen = str_len(ed->lines[ed->cur_line]);
        if (slen < EDITOR_MAX_COLS - 1) {
            /* Сдвинуть вправо */
            for (i = slen; i > ed->cur_col; i--) {
                ed->lines[ed->cur_line][i] =
                    ed->lines[ed->cur_line][i - 1];
            }
            ed->lines[ed->cur_line][ed->cur_col] = to_upper((char)key);
            ed->cur_col++;
        }
        return 0;
    }

    return 0;
}

/* Инвертировать метку F2-PLAY или F3-SOLO в заголовке редактора. */
static void invert_label(unsigned char which)
{
    /* which: 0 = F2-PLAY (col 14, 7 симв.), 1 = F3-SOLO (col 22, 7 симв.) */
    invert_chars((unsigned char)(16 + which * 8), 7, 7);
}

/* Запуск проигрывания из редактора: solo=0 — все каналы, solo=1 — только текущий. */
static void editor_play(editor_t *ed, char *st[], unsigned char channel,
                        unsigned char solo)
{
    unsigned char k;
    editor_save(ed, st[channel], 256);
    playback_start();
    if (solo)
        playback_solo(channel);
    if (!music_is_playing()) return;
    invert_label(solo);
    while (music_is_playing()) {
        wait_frame();
        editor_draw(ed, 0, 24, 1);
        k = kbd_scan();
        if (k == 27 || k == 129 || k == 130) {
            playback_stop();
            break;
        }
    }
    invert_label(solo);
}

void screen_editor(unsigned char channel, char *st[4])
{
    unsigned char key;
    unsigned char key_prev = 0;
    static editor_t ed;
    static char hdr[33];

    editor_init(&ed);
    ed.visible = 27;
    editor_load(&ed, st[channel]);

    init_screen();
    /* Заголовок */
    {
        const char *src = (channel < 3)
            ? "EDIT SCORE X    F2-PLAY F3-SOLO"
            : "EDIT DRUMS      F2-PLAY F3-SOLO";
        unsigned char i = 0;
        while (*src && i < 32) {
            hdr[i] = (*src == 'X')
                ? (char)('1' + channel) : *src;
            i++; src++;
        }
        hdr[i] = 0;
        graph_print(0, 8, hdr, 1);
    }
    draw_separator(16);

    for (;;) {
        wait_frame();
        key = kbd_scan();

        if (key != key_prev && key != 0) {
            if (key == 129) {  /* F2 — play all */
                editor_play(&ed, st, channel, 0);
                key_prev = 0;
                continue;
            }
            if (key == 130) {  /* F3 — solo */
                editor_play(&ed, st, channel, 1);
                key_prev = 0;
                continue;
            }
            if (editor_handle_key(&ed, key)) {
                editor_save(&ed, st[channel], 256);
                break;
            }
        }
        key_prev = key;

        editor_draw(&ed, 0, 24, 1);

        /* Статус */
        {
            char status[33];
            unsigned char sl = ed.cur_line + 1;
            unsigned char sc = ed.cur_col;
            unsigned char nl = ed.num_lines;
            unsigned char fc = ed.lines[0][0];
            status[0] = 'L';
            status[1] = (char)('0' + (sl / 10));
            status[2] = (char)('0' + (sl % 10));
            status[3] = ' ';
            status[4] = 'C';
            status[5] = (char)('0' + (sc / 10));
            status[6] = (char)('0' + (sc % 10));
            status[7] = ' ';
            status[8] = 'N';
            status[9] = (char)('0' + nl);
            status[10] = ' ';
            status[11] = 'F';
            status[12] = fc ? fc : '.';
            status[13] = 0;
            graph_print(0, 248, status, 1);
        }
    }
}
