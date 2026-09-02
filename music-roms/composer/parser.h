/*
 * parser.h — runtime-парсер .mus текста в байткод music.c.
 *
 * Преобразует текстовый формат партитур (.mus) в байткод для
 * music_song_t. Аналог mus2inc.py, но работает на Z80 при проигрывании.
 * Также выполняет валидацию и строит таблицу строк для подсветки.
 */

#ifndef PARSER_H
#define PARSER_H

#include "v06.h"

/* Максимальные размеры буферов */
#define PARSER_BC_SIZE   256     /* байткод на один канал */
#define PARSER_MAX_LINES  32     /* строк в таблице подсветки */

/* Коды ошибок парсера */
#define PERR_OK            0
#define PERR_UNKNOWN_TOK   1     /* непонятный токен */
#define PERR_NO_END_BEGIN  2     /* END без BEGIN */
#define PERR_NO_BEGIN_END  3     /* BEGIN без END */
#define PERR_NO_BRACKET    4     /* '[' без ']' */
#define PERR_NOTE_HIGH     5     /* нота выше O7 */
#define PERR_BAD_LEN       6     /* недопустимая L */
#define PERR_BAD_OCT       7     /* O вне 0..7 */
#define PERR_BAD_TEMPO     8     /* T вне 32..255 */
#define PERR_BRACKET_N     9     /* ]n: n вне 2..255 */

/* Результат парсинга */
typedef struct {
    unsigned char ok;             /* 1 = нет ошибок */
    unsigned char err_line;       /* строка ошибки (0-based, если ok) */
    unsigned char err_col;        /* столбец ошибки */
    unsigned char err_code;       /* код ошибки (PERR_*) */
} parse_result_t;

/* Парсинг текста одного канала в буфер байткода.
 * drums=1 для канала ударных. Записывает bytecode (до bc_size байт),
 * завершает MUS_END. Результат записывается в *result. */
void parse_score(parse_result_t *result,
                 const char *text, unsigned char *bytecode,
                 unsigned int bc_size, unsigned char drums);

/* Парсинг всех 4 каналов + темп. Заполняет song->s0..s2, song->dr,
 * song->samples, song->tempo_num/den.
 * score_text[0..2] — тексты тоновых партитур, score_text[3] — ударные.
 * samples — таблица указателей на семплы (nes_drums_samples). */
void parse_song(parse_result_t *result,
                const char *score_text[4],
                unsigned char bytecode_buf[4][PARSER_BC_SIZE],
                unsigned char tempo,
                const unsigned char * const *samples,
                music_song_t *song);

/* Построение таблицы тиков по строкам для подсветки.
 * Заполняет line_ticks[0..return-1]: тик на начало каждой строки.
 * Возвращает число строк. */
unsigned char build_line_map(const char *text, unsigned int *line_ticks,
                             unsigned char max_lines, unsigned char drums);

#endif /* PARSER_H */
