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
    char *err_text;             /* указатель на result->err_text: фрагмент
                                 * партитуры пишем сразу туда. Хранить здесь
                                 * копию нельзя — pstate_t лежит на стеке,
                                 * а стек (STACK_TOP=0x100) глуби чем на ~200
                                 * байтов затирает вектор 0x0038. */

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

/* Фрагмент исходника от ошибочного токена: до 4 операндов (токенов)
 * или до конца партитуры / комментария «;» — что ближе. Переводы
 * строк и табуляции заменяются пробелами, хвостовые пробелы срезаются;
 * всего до PERR_MSG_SIZE-1 символов (32-колоночный экран). */
static void grab_excerpt(const char *p, char *out)
{
    unsigned char i = 0u;
    unsigned char toks = 0u;
    unsigned char in_tok = 0u;

    while (*p == ' ' || *p == '\t' || *p == '\n')
        p++;
    while (i < PERR_MSG_SIZE - 1u) {
        unsigned char c = (unsigned char)*p;
        if (c == 0u || c == ';')
            break;                      /* конец партитуры / комментарий */
        if (c == ' ' || c == '\t' || c == '\n') {
            if (in_tok) {
                ++toks;
                if (toks >= 4u)
                    break;              /* нескольких операндов хватает */
            }
            in_tok = 0u;
            c = ' ';                    /* переводы строк — в пробелы */
        } else {
            in_tok = 1u;
        }
        out[i++] = (char)c;
        p++;
    }
    while (i > 0u && out[i - 1u] == ' ')
        --i;
    out[i] = 0;
}

/* Установка ошибки */
static void set_error(pstate_t *s, unsigned char code, const char *pos)
{
    if (s->err == 0) {
        s->err = code;
        s->col = (unsigned char)(pos - s->line_start);
        /* err_text == 0 у build_line_map: там фрагмент не нужен, а
         * писать некуда — на стеке запаса под него больше нет. */
        if (s->err_text)
            grab_excerpt(pos, s->err_text);
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

    /* V<n> — громкость канала V1..V15 (байт 0xF1..0xFF, вся команда
     * — 1 байт). Команда состояния: время не продвигает. На AY
     * применяется на следующей атаке ноты, на ВИ53 рантайм её
     * игнорирует. В канале ударных не эмитится (рантайм игнорирует
     * V в drum-потоке — не тратить байткод). */
    if ((ch == 'V' || ch == 'v') && p[1] >= '0' && p[1] <= '9') {
        unsigned int v;
        p++;
        v = parse_number(&p);
        if (v < 1 || v > 15) {
            set_error(s, PERR_BAD_VOL, start);
        } else if (!s->drums) {
            emit(s, (unsigned char)(MUS_VOL_BASE + v));
        }
        *endp = p;
        return;
    }

    /* S<n> <period> — огибающая S0..S15 (байт 0xC0+n) + период WORD
     * little-endian (R11/R12). Команда состояния: время не продвигает,
     * канал подключается к огибающей на следующей атаке. Генератор AY
     * один — параметры общие для всех подключённых каналов; на ВИ53
     * рантайм команду игнорирует. В канале ударных операнды только
     * разбираются, байткод не эмитится (рантайм их пропускает). */
    if ((ch == 'S' || ch == 's') && p[1] >= '0' && p[1] <= '9') {
        unsigned int n, per;
        unsigned char over;
        p++;
        n = parse_number(&p);
        if (n > 15) {
            set_error(s, PERR_BAD_SHAPE, start);
            *endp = p;
            return;
        }
        /* период — следующее число через пробелы (табуляцию),
         * accumulate с точной проверкой переполнения 16 бит:
         * per*10+d <= 65535 <=> per < 6553 или (per == 6553 и d <= 5) */
        while (*p == ' ' || *p == '\t')
            p++;
        if (*p < '0' || *p > '9') {
            set_error(s, PERR_BAD_PERIOD, start);
            *endp = p;
            return;
        }
        per = 0u;
        over = 0u;
        while (*p >= '0' && *p <= '9') {
            unsigned int d = (unsigned int)(*p - '0');
            if (over || per > 6553u || (per == 6553u && d > 5u))
                over = 1u;
            else
                per = per * 10u + d;
            p++;
        }
        if (over) {
            set_error(s, PERR_BAD_PERIOD, start);
            *endp = p;
            return;
        }
        if (!s->drums) {
            emit(s, (unsigned char)(MUS_ENV_BASE + n));
            emit(s, (unsigned char)(per & 0xFFu));
            emit(s, (unsigned char)(per >> 8));
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
    st.err_text = result->err_text;
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
    /* номер тонового канала parse_score не знает (4 = не заявлен),
     * ударные определяются флагом; parse_song переставляет точно */
    result->err_chan = drums ? 3u : 4u;
    if (!st.err)
        result->err_text[0] = 0;  /* при ошибке фрагмент уже записан
                                   * set_error прямо в result */
}

/* ---------------------- Парсинг полной песни ------------------------- */

void parse_song(parse_result_t *result,
                const char *score_text[4],
                unsigned char bytecode_buf[4][PARSER_BC_SIZE],
                unsigned char tempo,
                const unsigned char * const *samples,
                music_song_t *song)
{
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
        /* Локальной копии результата нет — parse_score пишет прямо в
         * result: каждый parse_result_t на стеке этого вызова стоил бы
         * лишние ~37 байт, а стек упирается в векторную страницу. */
        parse_score(result, score_text[ch], bytecode_buf[ch],
                    PARSER_BC_SIZE, is_drums);
        if (!result->ok) {
            result->err_chan = ch; /* точный номер партитуры */
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
                } else if (b >= MUS_VOL_BASE + 1) {
                    /* V1..V15: состояние, время не продвигает */
                } else if (b == MUS_LPSTART) {
                    /* пропуск */
                } else if (b == MUS_LPEND) {
                    pc++;  /* пропуск n */
                } else if (b == MUS_JMP) {
                    pc += 2;
                } else if (b >= MUS_ENV_BASE && b <= MUS_ENV_BASE + 15) {
                    pc += 2;  /* S0..S15: пропуск периода, время стоит */
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

    result->ok = 1;
    result->err_line = 0;
    result->err_col = 0;
    result->err_code = PERR_OK;
    result->err_chan = 4u;
    result->err_text[0] = 0;
}

/* ------------------------- Имена ошибок ------------------------------ */

/* Текст для экрана: что за ошибка (код PERR_*). Строки короче
 * 32 колонок — печатаются gfx_print целиком. */
const char *parse_error_name(unsigned char code)
{
    static const char *names[] = {
        "NO ERROR",                /* PERR_OK            */
        "UNKNOWN TOKEN",           /* PERR_UNKNOWN_TOK   */
        "END WITHOUT BEGIN",       /* PERR_NO_END_BEGIN  */
        "BEGIN WITHOUT END",       /* PERR_NO_BEGIN_END  */
        "UNCLOSED SECTION [",      /* PERR_NO_BRACKET    */
        "NOTE TOO HIGH",           /* PERR_NOTE_HIGH     */
        "BAD LENGTH L",            /* PERR_BAD_LEN       */
        "OCTAVE O MUST BE 0-7",    /* PERR_BAD_OCT       */
        "TEMPO T MUST BE 32-255",  /* PERR_BAD_TEMPO     */
        "REPEAT N MUST BE 2-255",  /* PERR_BRACKET_N     */
        "VOLUME V MUST BE 1-15",   /* PERR_BAD_VOL       */
        "SHAPE S MUST BE 0-15",    /* PERR_BAD_SHAPE     */
        "PERIOD MUST BE 0-65535"   /* PERR_BAD_PERIOD    */
    };
    if (code > PERR_BAD_PERIOD)
        return "UNKNOWN ERROR";
    return names[code];
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
