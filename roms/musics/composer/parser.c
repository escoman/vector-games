/*
 * parser.c — runtime-парсер .mus текста в байткод music.c.
 *
 * Работает на Z80 (через z88dk), аналог utils/mus2inc.py.
 * Токенизирует текст партитуры, эмитит байткод, валидирует.
 * Все длительности — сетка PPQ = 32 (четверть = 32 тика).
 */

#include "parser.h"
#include <string.h>

/* --------------------------- Вспомогательные -------------------------- */

/* Полутоны нот (C=0, D=2, E=4, F=5, G=7, A=9, B=11) */
static unsigned char note_semi(unsigned char ch)
{
    switch (ch) {
    case 'C': return 0;
    case 'D': return 2;
    case 'E': return 4;
    case 'F': return 5;
    case 'G': return 7;
    case 'A': return 9;
    case 'B': return 11;
    }
    return 0;
}

/* Является ли символ нотой */
static unsigned char is_note(unsigned char ch)
{
    return ch >= 'A' && ch <= 'G';
}

/* L-значение в индекс байткода: L1=0, L2=1, L4=2, ..., L128=7 */
static unsigned char l_index(unsigned int l_val)
{
    unsigned char i;
    unsigned int v;

    for (i = 0, v = 1; i < 8; i++, v <<= 1)
        if (v == l_val)
            return i;
    return 0xFF;  /* недопустимое */
}

/* Тики длительности: L_n = 128/n */
static unsigned int len_ticks(unsigned int l_val)
{
    return 128 / l_val;
}

/* Пропуск пробелов и табуляций. Возвращает новую позицию. */
static const char *skip_ws(const char *p)
{
    while (*p == ' ' || *p == '\t')
        p++;
    return p;
}

/* Переход на начало следующей строки. Возвращает новую позицию. */
static const char *next_line(const char *p)
{
    while (*p && *p != '\n')
        p++;
    if (*p == '\n')
        p++;
    return p;
}

/* Парсинг натурального числа. Возвращает значение, advancing *pp. */
static unsigned int parse_number(const char **pp)
{
    unsigned int n = 0;
    const char *p = *pp;

    while (*p >= '0' && *p <= '9') {
        n = n * 10 + (unsigned char)(*p - '0');
        p++;
    }
    *pp = p;
    return n;
}

/* Сравнение с шаблоном (case-insensitive для первой буквы).
 * Возвращает 1, если *p начинается с word (и далее не буква/цифра). */
static unsigned char match_word(const char *p, const char *word)
{
    while (*word) {
        unsigned char a = *p, b = *word;
        /* to upper */
        if (a >= 'a' && a <= 'z') a -= 32;
        if (b >= 'a' && b <= 'z') b -= 32;
        if (a != b)
            return 0;
        p++;
        word++;
    }
    /* после слова не должно быть буквы/цифры */
    if ((*p >= 'A' && *p <= 'Z') || (*p >= '0' && *p <= '9'))
        return 0;
    return 1;
}

/* ----------------------- Состояние парсера --------------------------- */

typedef struct {
    unsigned char *bc;          /* буфер байткода */
    unsigned int bc_size;       /* размер буфера */
    unsigned int bc_pos;        /* текущая позиция записи */
    unsigned char drums;        /* 1 = канал ударных */

    unsigned char oct;          /* текущая октава (4 по умолчанию) */
    unsigned int l_val;         /* текущая длительность (4 по умолчанию) */
    unsigned int ticks;         /* накопленные тики */

    unsigned int loop_pos;      /* позиция байткода после BEGIN (0xFFFF = нет) */
    unsigned int mark_stack[4]; /* стек позиций '[' */
    unsigned char mark_top;     /* вершина стека */

    unsigned char line;         /* текущая строка (0-based) */
    unsigned char col;          /* текущий столбец */
    const char *line_start;     /* начало текущей строки */

    unsigned char err;          /* код ошибки (0 = нет) */

    /* Таблица строк для подсветки */
    unsigned int *line_ticks;   /* line_ticks[i] = тик на начало строки i */
    unsigned char num_lines;    /* число строк в таблице */
    unsigned char max_lines;    /* максимум строк */
    unsigned int cur_line_tick; /* тик на начало текущей строки */
} pstate_t;

/* Эмит одного байта */
static void emit(pstate_t *s, unsigned char b)
{
    if (s->bc_pos < s->bc_size)
        s->bc[s->bc_pos] = b;
    s->bc_pos++;
}

/* Эмит команды длины L */
static void emit_len(pstate_t *s, unsigned int l_val)
{
    unsigned char idx = l_index(l_val);
    if (idx < 8)
        emit(s, MUS_LEN + idx);
}

/* Установка ошибки */
static void set_error(pstate_t *s, unsigned char code, const char *pos)
{
    if (s->err == 0) {
        s->err = code;
        s->col = (unsigned char)(pos - s->line_start);
    }
}

/* -------------------------- Основной парсер -------------------------- */

/* Парсинг одного токена. Возвращает 0 при ошибке. */
static void parse_token(pstate_t *s, const char *p, const char **endp)
{
    unsigned char ch;
    const char *start = p;

    ch = *p;

    /* Пропуск пробелов */
    p = skip_ws(p);
    ch = *p;
    if (ch == 0 || ch == '\n') {
        *endp = p;
        return;
    }

    /* BEGIN */
    if (match_word(p, "BEGIN")) {
        if (s->loop_pos != 0xFFFFu) {
            set_error(s, PERR_NO_END_BEGIN, p);
            *endp = p + 5;
            return;
        }
        s->loop_pos = s->bc_pos;
        *endp = p + 5;
        return;
    }

    /* END */
    if (match_word(p, "END")) {
        unsigned int target, current, back;
        if (s->loop_pos == 0xFFFFu) {
            set_error(s, PERR_NO_END_BEGIN, p);
            *endp = p + 3;
            return;
        }
        target = s->loop_pos;
        current = s->bc_pos + 3;  /* позиция после 0xEA + 2 байт */
        back = current - target;
        emit(s, MUS_JMP);
        emit(s, (unsigned char)(back & 0xFF));
        emit(s, (unsigned char)((back >> 8) & 0xFF));
        s->loop_pos = 0xFFFFu;
        *endp = p + 3;
        return;
    }

    /* [ */
    if (ch == '[') {
        if (s->mark_top < 4) {
            s->mark_stack[s->mark_top] = s->ticks;
            s->mark_top++;
        }
        emit(s, MUS_LPSTART);
        *endp = p + 1;
        return;
    }

    /* ]n */
    if (ch == ']') {
        unsigned int n, section;
        p++;
        n = parse_number(&p);
        if (n < 2 || n > 255) {
            set_error(s, PERR_BRACKET_N, start);
            *endp = p;
            return;
        }
        if (s->mark_top > 0) {
            s->mark_top--;
            section = s->ticks - s->mark_stack[s->mark_top];
        } else {
            section = s->ticks;
        }
        s->ticks += section * (n - 1);
        emit(s, MUS_LPEND);
        emit(s, (unsigned char)n);
        *endp = p;
        return;
    }

    /* ! (разрешение разной длины) */
    if (ch == '!') {
        *endp = p + 1;
        return;
    }

    /* T<n> — темп */
    if ((ch == 'T' || ch == 't') && p[1] >= '0' && p[1] <= '9') {
        unsigned int t;
        p++;
        t = parse_number(&p);
        if (t < 32 || t > 255)
            set_error(s, PERR_BAD_TEMPO, start);
        *endp = p;
        return;
    }

    /* O<n> — октава */
    if ((ch == 'O' || ch == 'o') && p[1] >= '0' && p[1] <= '9') {
        unsigned int o;
        p++;
        o = parse_number(&p);
        if (o > 7) {
            set_error(s, PERR_BAD_OCT, start);
        } else {
            s->oct = (unsigned char)o;
        }
        *endp = p;
        return;
    }

    /* L<n> — длительность */
    if ((ch == 'L' || ch == 'l') && p[1] >= '0' && p[1] <= '9') {
        unsigned int lv;
        p++;
        lv = parse_number(&p);
        if (l_index(lv) == 0xFF) {
            set_error(s, PERR_BAD_LEN, start);
        } else {
            s->l_val = lv;
            emit_len(s, lv);
        }
        *endp = p;
        return;
    }

    /* P — пауза */
    if (ch == 'P' || ch == 'p') {
        unsigned int l_ov = 0;
        p++;
        /* явная длительность P<n> */
        if (*p >= '0' && *p <= '9') {
            l_ov = parse_number(&p);
            if (l_index(l_ov) == 0xFF) {
                set_error(s, PERR_BAD_LEN, start);
                l_ov = 0;
            }
        }
        if (l_ov && l_ov != s->l_val) {
            emit_len(s, l_ov);
            emit(s, MUS_REST);
            emit_len(s, s->l_val);
            s->ticks += len_ticks(l_ov);
        } else {
            emit(s, MUS_REST);
            s->ticks += len_ticks(s->l_val);
        }
        *endp = p;
        return;
    }

    /* Нота: A-G с акцидентом (#, +, -) и/или явной длительностью */
    if (is_note(ch) && !s->drums) {
        unsigned char semi;
        unsigned int abs_note, l_ov = 0;
        unsigned char note_ch = ch;
        if (note_ch >= 'a' && note_ch <= 'z')
            note_ch -= 32;
        semi = note_semi(note_ch);
        p++;
        /* акцидент */
        if (*p == '#' || *p == '+') {
            semi++;
            p++;
        } else if (*p == '-') {
            /* бемоль: только если далее не цифра (иначе это не нота) */
            if (p[1] < '0' || p[1] > '9') {
                semi--;
                p++;
            }
        }
        /* явная длительность */
        if (*p >= '0' && *p <= '9') {
            l_ov = parse_number(&p);
            if (l_index(l_ov) == 0xFF) {
                set_error(s, PERR_BAD_LEN, start);
                l_ov = 0;
            }
        }
        abs_note = (unsigned int)s->oct * 12 + semi;
        if (abs_note > 94) {
            set_error(s, PERR_NOTE_HIGH, start);
        }
        /* эмит ноты */
        if (l_ov && l_ov != s->l_val) {
            emit_len(s, l_ov);
            emit(s, (unsigned char)(abs_note + 1));
            emit_len(s, s->l_val);
            s->ticks += len_ticks(l_ov);
        } else {
            emit(s, (unsigned char)(abs_note + 1));
            s->ticks += len_ticks(s->l_val);
        }
        *endp = p;
        return;
    }

    /* Drum hit: цифра (0..15) */
    if (ch >= '0' && ch <= '9' && s->drums) {
        unsigned int drum_id;
        unsigned int l_ov = 0;
        drum_id = parse_number(&p);
        if (drum_id > 15)
            drum_id = 15;
        /* явная длительность */
        if (*p >= '0' && *p <= '9') {
            l_ov = parse_number(&p);
        }
        if (l_ov && l_ov != s->l_val) {
            emit_len(s, l_ov);
            emit(s, (unsigned char)(drum_id + 1));
            emit_len(s, s->l_val);
            s->ticks += len_ticks(l_ov);
        } else {
            emit(s, (unsigned char)(drum_id + 1));
            s->ticks += len_ticks(s->l_val);
        }
        *endp = p;
        return;
    }

    /* Непонятный токен */
    set_error(s, PERR_UNKNOWN_TOK, p);
    *endp = p + 1;
}

/* Запись строки в таблицу подсветки */
static void record_line(pstate_t *s)
{
    if (s->num_lines < s->max_lines) {
        s->line_ticks[s->num_lines] = s->cur_line_tick;
        s->num_lines++;
    }
    s->cur_line_tick = s->ticks;
}

/* -------------------------- Публичный API ---------------------------- */

void parse_score(parse_result_t *result,
                 const char *text, unsigned char *bytecode,
                 unsigned int bc_size, unsigned char drums)
{
    pstate_t st;
    const char *p;

    memset(&st, 0, sizeof(st));
    st.bc = bytecode;
    st.bc_size = bc_size;
    st.bc_pos = 0;
    st.drums = drums;
    st.oct = 4;
    st.l_val = 4;
    st.loop_pos = 0xFFFFu;
    st.mark_top = 0;
    st.line = 0;
    st.err = 0;
    st.ticks = 0;
    st.line_ticks = 0;
    st.num_lines = 0;
    st.max_lines = 0;
    st.cur_line_tick = 0;

    p = text;
    st.line_start = p;

    while (*p) {
        /* Пропуск пустых строк и комментариев */
        const char *lp = skip_ws(p);
        if (*lp == ';' || *lp == 0) {
            if (*lp == 0) break;
            p = next_line(p);
            st.line++;
            st.line_start = p;
            continue;
        }
        if (*lp == '\n') {
            p++;
            st.line++;
            st.line_start = p;
            continue;
        }

        /* Записать строку в таблицу подсветки */
        if (st.line_ticks)
            record_line(&st);

        /* Разбор токенов в строке */
        p = lp;
        while (*p && *p != '\n' && *p != ';') {
            const char *end;
            p = skip_ws(p);
            if (*p == 0 || *p == '\n' || *p == ';')
                break;
            parse_token(&st, p, &end);
            if (st.err)
                goto done;
            if (end == p)
                break;  /* защита от зацикливания */
            p = end;
        }

        /* Переход на следующую строку */
        p = next_line(p);
        st.line++;
        st.line_start = p;
    }

done:
    /* Финальная проверка */
    if (!st.err && st.loop_pos != 0xFFFFu)
        st.err = PERR_NO_BEGIN_END;
    if (!st.err && st.mark_top > 0)
        st.err = PERR_NO_BRACKET;

    /* Завершение байткода */
    emit(&st, MUS_END);

    result->ok = (st.err == 0) ? 1 : 0;
    result->err_line = st.line;
    result->err_col = st.col;
    result->err_code = st.err ? st.err : PERR_OK;
}

/* ---------------------- Парсинг полной песни ------------------------- */

void parse_song(parse_result_t *result,
                const char *score_text[4],
                unsigned char bytecode_buf[4][PARSER_BC_SIZE],
                unsigned char tempo,
                const unsigned char * const *samples,
                music_song_t *song)
{
    parse_result_t res;
    unsigned char ch;
    unsigned int g;

    /* Инициализация song */
    memset(song, 0, sizeof(*song));

    /* Темп: tempo_num/tempo_den = 4*T/gcd(4*T,375) / 375/gcd(4*T,375) */
    {
        unsigned int t4 = (unsigned int)tempo * 4;
        unsigned int a = t4, b = 375;
        while (b) { unsigned int t = b; b = a % b; a = t; }
        g = a;
        song->tempo_num = t4 / g;
        song->tempo_den = 375 / g;
    }

    /* Парсинг каждого канала */
    for (ch = 0; ch < 4; ch++) {
        unsigned char is_drums = (ch == 3) ? 1 : 0;
        if (score_text[ch] == 0 || score_text[ch][0] == 0) {
            /* Пустой канал */
            bytecode_buf[ch][0] = MUS_END;
            continue;
        }
        parse_score(&res, score_text[ch], bytecode_buf[ch],
                    PARSER_BC_SIZE, is_drums);
        if (!res.ok) {
            *result = res;
            return;
        }
    }

    /* Заполнение song */
    song->s0 = bytecode_buf[0];
    song->s1 = bytecode_buf[1];
    song->s2 = bytecode_buf[2];
    song->dr = bytecode_buf[3];
    song->samples = samples;

    /* Длина = максимум тиков по каналам */
    {
        unsigned int max_t = 0;
        /* Пересчитаем тики из каждого канала */
        for (ch = 0; ch < 4; ch++) {
            unsigned int t = 0;
            const unsigned char *pc = bytecode_buf[ch];
            unsigned int l_val = 4;
            while (*pc != MUS_END) {
                unsigned char b = *pc++;
                if (b == MUS_REST) {
                    t += len_ticks(l_val);
                } else if (b >= MUS_LEN && b <= MUS_LEN + 7) {
                    l_val = (unsigned int)(0x80 >> (b - MUS_LEN));
                } else if (b == MUS_LPSTART) {
                    /* пропуск */
                } else if (b == MUS_LPEND) {
                    pc++;  /* пропуск n */
                } else if (b == MUS_JMP) {
                    pc += 2;
                } else if (b >= 1 && b <= 0x5F) {
                    t += len_ticks(l_val);
                } else if (b >= 0x61 && b <= 0x7F) {
                    /* drum hit: 1..15 -> байт код */
                    t += len_ticks(l_val);
                }
            }
            if (t > max_t) max_t = t;
        }
        song->length = max_t;
    }

    res.ok = 1;
    res.err_line = 0;
    res.err_col = 0;
    res.err_code = PERR_OK;
    *result = res;
}

/* ------------------- Таблица строк для подсветки --------------------- */

unsigned char build_line_map(const char *text, unsigned int *line_ticks,
                             unsigned char max_lines, unsigned char drums)
{
    pstate_t st;
    const char *p;

    memset(&st, 0, sizeof(st));
    st.bc = 0;            /* байткод не пишем */
    st.bc_size = 0;
    st.bc_pos = 0;
    st.drums = drums;
    st.oct = 4;
    st.l_val = 4;
    st.loop_pos = 0xFFFFu;
    st.mark_top = 0;
    st.line = 0;
    st.err = 0;
    st.ticks = 0;
    st.line_ticks = line_ticks;
    st.num_lines = 0;
    st.max_lines = max_lines;
    st.cur_line_tick = 0;

    p = text;
    st.line_start = p;

    while (*p) {
        const char *lp = skip_ws(p);
        if (*lp == ';' || *lp == 0) {
            if (*lp == 0) break;
            p = next_line(p);
            st.line++;
            st.line_start = p;
            continue;
        }
        if (*lp == '\n') {
            p++;
            st.line++;
            st.line_start = p;
            continue;
        }

        record_line(&st);

        p = lp;
        while (*p && *p != '\n' && *p != ';') {
            const char *end;
            p = skip_ws(p);
            if (*p == 0 || *p == '\n' || *p == ';')
                break;
            parse_token(&st, p, &end);
            if (st.err)
                goto map_done;
            if (end == p)
                break;
            p = end;
        }
        p = next_line(p);
        st.line++;
        st.line_start = p;
    }

map_done:
    return st.num_lines;
}
