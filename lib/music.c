/*
 * music.c — партитурный синтезатор Вектора-06Ц (music_song_t).
 *
 * Собирается с -DMUSIC_ONLY. Символы music_* не конфликтуют с
 * шаговым плеером sound.c (sound_*), но в одном ROM собирайте
 * один плеер: оба пишут в одни каналы ВИ53.
 *
 * Архитектура (ТЗ «один music clock»): четыре потока байткода —
 * три тональных партитуры и ударные — идут относительно единого
 * музыкального времени. music_tick() вызывается из кадрового
 * прерывания 50 Гц и потребляет tempo_num/tempo_den тика за кадр
 * (аккумулятор Брешихэма); каждый тик все четыре потока продвигаются
 * синхронно, у каждого — своя позиция в своей партитуре.
 *
 * Тона — КР580ВИ53 (карта портов и режимы как в sound.c), ударные —
 * канал шума AY-3-8910 через проигрыватель семплов drums.asm
 * (drum_sample_play + drum_tick, вызывать рядом с music_tick).
 *
 * Байткод потока (константы MUS_* в v06.h, эмитит mus2inc.py):
 *   0x00        конец потока;
 *   0x01..0x5F  нота: абсолютный номер = байт - 1 (октава*12 +
 *               полутон), делитель ВИ53 берётся из таблицы;
 *   0x60        пауза на текущую длительность;
 *   0xE0..0xE7  длительность L1..L128 сетки PPQ = 32 — команда
 *               состояния: L = 1 << (байт - 0xE0), в тиках 128/L
 *               (четверть = 32 тика, без округлений и дрейфа; темп =
 *               tempo_num/tempo_den тика за кадр);
 *   0xE8        «[» — начало повторяемой секции: база повтора =
 *               следующий байт, счётчик проходов = 0;
 *   0xE9 n      «]n» — конец секции: счётчик + 1; пока счётчик < n,
 *               исполнение возвращается к базе (секция звучит ровно
 *               n раз, как $FB/$FE n движка Konami). Команда состояния
 *               ноту не запускает и время не продвигает; начальная
 *               длительность потока без команд — L4. Октава —
 *               compile-time состояние mus2inc.py, в байткоде команды
 *               нет (диапазон 0xD0..0xD7 свободен). Все высоты
 *               предвычислены mus2inc.py (ТЗ §26): в прерывании нет
 *               разбора строк и плавающей точки.
 */

#include "v06.h"

/* Прямые записи в порты ВИ53 (vi53out.asm): без самомодификации байта
 * порта и без di/ei, поэтому безопасны и в кадровом прерывании. */
extern void v06_vi53_ctrl(unsigned char v);
extern void v06_vi53_ch0(unsigned char v);
extern void v06_vi53_ch1(unsigned char v);
extern void v06_vi53_ch2(unsigned char v);

/* ------------------------------ ВИ53 ---------------------------------- */

/* Режим 3, чтение/запись 2 байта: каналы 0/1/2. Им же и выключаем:
 * только управляющее слово, счётчик не загружается (VECTOR.MD
 * §5.5.7, «самый распространённый способ в играх»). Проверено на
 * слух: режим 0 со счётом 0 даёт треск после остановки, режим 3 с
 * делителем 0xFFFF — постоянный фоновый гул; без загрузки счётчика
 * эмуляция молчит чисто (тест vi53sil.rom, методы 1/2/3). */
static const unsigned char vi53_m3[3] = { 0x36, 0x76, 0xB6 };

static void vi53_data(unsigned char channel, unsigned char v)
{
    if (channel == 0u)
        v06_vi53_ch0(v);
    else if (channel == 1u)
        v06_vi53_ch1(v);
    else
        v06_vi53_ch2(v);
}

/* Установка делителя канала (0 = выключить: управляющее слово
 * режима 3 без загрузки счётчика) */
static void vi53_set_channel(unsigned char channel, unsigned int divisor)
{
    v06_vi53_ctrl(vi53_m3[channel]);
    if (divisor == 0u)
        return;
    vi53_data(channel, (unsigned char)(divisor & 0xFFu));
    vi53_data(channel, (unsigned char)(divisor >> 8));
}

/* Делители ВИ53 по абсолютному номеру ноты (октава*12 + полутон):
 * делитель = 1500000 / частота, ля 4-й октавы (57) = 440 Гц = 3409.
 * Номера 0..11 ниже рабочей зоны — тишина (делитель > 65535). */
static const unsigned int div_tab[95] = {
        0u,     0u,     0u,     0u,     0u,     0u,     0u,     0u,
        0u,     0u,     0u,     0u, 45867u, 43293u, 40863u, 38569u,
    36405u, 34361u, 32433u, 30613u, 28894u, 27273u, 25742u, 24297u,
    22934u, 21646u, 20431u, 19285u, 18202u, 17181u, 16216u, 15306u,
    14447u, 13636u, 12871u, 12149u, 11467u, 10823u, 10216u,  9642u,
     9101u,  8590u,  8108u,  7653u,  7224u,  6818u,  6436u,  6074u,
     5733u,  5412u,  5108u,  4821u,  4551u,  4295u,  4054u,  3827u,
     3612u,  3409u,  3218u,  3037u,  2867u,  2706u,  2554u,  2411u,
     2275u,  2148u,  2027u,  1913u,  1806u,  1705u,  1609u,  1519u,
     1433u,  1353u,  1277u,  1205u,  1138u,  1074u,  1014u,   957u,
      903u,   852u,   804u,   759u,   717u,   676u,   638u,   603u,
      569u,   537u,   507u,   478u,   451u,   426u,   402u
};

/* --------------------------- Состояние -------------------------------- */

/* Один поток партитуры: позиция в байткоде и текущее состояние */
typedef struct {
    const unsigned char *pc;    /* 0 = поток закончился               */
    const unsigned char *start; /* начало — для перезапуска (loop)    */
    const unsigned char *loop_pc;  /* база повтора (MUS_LPSTART)      */
    unsigned char loop_cnt;     /* пройдено раз в текущей секции      */
    unsigned char cnt;          /* тиков до конца текущего события    */
    unsigned char len;          /* текущая длительность (MUS_LEN)     */
    unsigned char gate;         /* тиков тишины до вступления ноты    */
    unsigned int div;           /* делитель отложенной ноты           */
} mus_ch_t;

static const music_song_t *g_song;
static mus_ch_t g_ch[3];        /* тоновые партитуры                  */
static mus_ch_t g_dr;           /* партитура ударных                  */

static unsigned char g_playing;
static unsigned char g_paused;
static unsigned char g_loop;
static unsigned int g_acc;      /* остаток в аккумуляторе темпа       */

/* Диагностика: переменные и diag_reset() определены в debug_sound.c;
 * инкременты счётчиков остались здесь (tone_event, drum_event,
 * clock_tick, music_tick). */
extern void diag_reset(void);

/* ------------------------------ Помощники ----------------------------- */

static void silence_tones(void)
{
    vi53_set_channel(0, 0);
    vi53_set_channel(1, 0);
    vi53_set_channel(2, 0);
}

static void reset_stream(mus_ch_t *c, const unsigned char *pc)
{
    c->pc = pc;
    c->start = pc;
    c->loop_pc = pc;
    c->loop_cnt = 0u;
    c->cnt = 0u;
    c->gate = 0u;
    c->len = 32u;               /* до первой команды MUS_LEN — L4     */
}

/* ------------------------------- API ---------------------------------- */

void music_set_data(const music_song_t *song)
{
    g_song = song;
    music_stop();
}

void music_start(void)
{
    if (g_song == 0)
        return;
    reset_stream(&g_ch[0], g_song->s0);
    reset_stream(&g_ch[1], g_song->s1);
    reset_stream(&g_ch[2], g_song->s2);
    reset_stream(&g_dr, g_song->dr);
    g_acc = 0u;
    g_paused = 0u;
    g_playing = 1u;
    diag_reset();
    silence_tones();
    drum_mute();                /* старт всех потоков с позиции 0 */
}

void music_pause(void)
{
    if (!g_playing)
        return;
    g_paused = 1u;
    silence_tones();            /* позиции и clock сохранены */
}

void music_resume(void)
{
    if (g_playing)
        g_paused = 0u;
}

void music_stop(void)
{
    g_playing = 0u;
    g_paused = 0u;
    g_acc = 0u;
    g_ch[0].pc = g_ch[1].pc = g_ch[2].pc = 0;
    g_dr.pc = 0;
    silence_tones();
    drum_mute();
}

unsigned char music_is_playing(void)
{
    return g_playing;
}

void music_set_loop(unsigned char loop)
{
    g_loop = loop;
}

/* ------------------------------ Рантайм ------------------------------- */

/* Тоновый поток: события читаются до ноты/паузы/конца (управляющие
 * команды исполняются на месте). Запись в ВИ53 — на событии и в
 * clock_tick() по истечении гейта. */
static void tone_event(unsigned char ch)
{
    mus_ch_t *c = &g_ch[ch];
    unsigned char b, n;

    for (;;) {
        b = *c->pc++;
        if (b == MUS_END) {
            c->pc = 0;                  /* поток закончился */
            vi53_set_channel(ch, 0u);
            if (ch == 0u) {
                diag_score0_steps++;
                diag_score0_time = diag_music_time;
                if (!diag_score0_finished) {
                    diag_score0_finished = 1;
                    diag_score0_finish_irq = diag_irq_count;
                    diag_score0_finish_time = diag_music_time;
                    diag_score0_finish_steps = diag_score0_steps;
                }
            }
            return;
        }
        if (b == MUS_REST) {
            vi53_set_channel(ch, 0u);
            /* Текущий тик — первый тик паузы (как и в drum_event),
             * поэтому cnt = len - 1. */
            if (c->len > 1u)
                c->cnt = c->len - 1u;
            else
                c->cnt = 0u;
            if (ch == 0u) {
                diag_score0_steps++;
                diag_score0_time = diag_music_time;
            }
            return;
        }
        if (b >= MUS_LEN && b <= MUS_LEN + 7u) {  /* E0..E7: длит-ть */
            c->len = (unsigned char)(0x80u >> (b - MUS_LEN));
            continue;
        }
        if (b == MUS_LPSTART) {         /* «[»: база повтора */
            c->loop_pc = c->pc;
            c->loop_cnt = 0u;
            continue;
        }
        if (b == MUS_LPEND) {           /* «]n»: n проходов секции */
            n = *c->pc++;
            if (++c->loop_cnt < n)
                c->pc = c->loop_pc;
            continue;
        }
        /* Гейт: первый тик ноты — тишина (разделяет повторы той же
         * ноты — ВИ53 иначе тянет звук без разрыва; даёт каждой ноте
         * атаку). Гейт И текущий тик — оба внутри длительности:
         * событие длится ровно len тиков (gate=1 + cnt=len-2 + текущий
         * тик = len), дрейфа нет. Делитель отложен, запись в ВИ53 — в
         * clock_tick(). */
        vi53_set_channel(ch, 0u);
        c->gate = 1u;
        c->div = div_tab[b - 1u];
        if (c->len >= 2u)
            c->cnt = c->len - 2u;   /* 1 тик — текущий, 1 тик — гейт */
        else
            c->cnt = 0u;            /* L1: только текущий тик (гейт) */
        if (ch == 0u) {
            diag_score0_steps++;
            diag_score0_time = diag_music_time;
        }
        return;
    }
}

/* Длительность drum-события: текущий тик уже учтён (как и в tone_event),
 * поэтому cnt = len - 1. Без этого каждое drum-событие занимало бы
 * len + 1 тиков и дорожка ударных отстаёт от тональных каналов. */
static void drum_set_counter(void)
{
    if (g_dr.len > 1u)
        g_dr.cnt = g_dr.len - 1u;
    else
        g_dr.cnt = 0u;
}

/* Поток ударных: нота (байт 1..10) запускает семпл 0..9 с таблицы
 * песни; пауза новые атаки не даёт, звучащий семпл не обрывает. */
static void drum_event(void)
{
    unsigned char b, n;

    for (;;) {
        b = *g_dr.pc++;
        if (b == MUS_END) {
            g_dr.pc = 0;
            diag_drums_steps++;
            diag_drums_time = diag_music_time;
            if (!diag_drums_finished) {
                diag_drums_finished = 1;
                diag_drums_finish_irq = diag_irq_count;
                diag_drums_finish_time = diag_music_time;
                diag_drums_finish_steps = diag_drums_steps;
            }
            return;
        }
        if (b == MUS_REST) {
            drum_set_counter();
            diag_drums_steps++;
            diag_drums_time = diag_music_time;
            return;
        }
        if (b >= MUS_LEN && b <= MUS_LEN + 7u) {
            g_dr.len = (unsigned char)(0x80u >> (b - MUS_LEN));
            continue;
        }
        if (b == MUS_LPSTART) {         /* «[»: база повтора */
            g_dr.loop_pc = g_dr.pc;
            g_dr.loop_cnt = 0u;
            continue;
        }
        if (b == MUS_LPEND) {           /* «]n»: n проходов секции */
            n = *g_dr.pc++;
            if (++g_dr.loop_cnt < n)
                g_dr.pc = g_dr.loop_pc;
            continue;
        }
        if (b <= 10u)                   /* новый удар — перезапуск */
            drum_sample_play(g_song->samples[b - 1u]);
        drum_set_counter();
        diag_drums_steps++;
        diag_drums_time = diag_music_time;
        return;
    }
}

/* Один тик music clock: продвижение всех четырёх потоков */
static void clock_tick(void)
{
    unsigned char i;

    diag_music_time++;

    if (g_ch[0].pc == 0 && g_ch[1].pc == 0 &&
        g_ch[2].pc == 0 && g_dr.pc == 0) {
        /* композиция отзвучала */
        if (!g_loop) {
            g_playing = 0u;
            silence_tones();
            return;
        }
        for (i = 0u; i < 3u; ++i) {
            g_ch[i].pc = g_ch[i].start;
            g_ch[i].cnt = 0u;
        }
        g_dr.pc = g_dr.start;
        g_dr.cnt = 0u;
    }

    for (i = 0u; i < 3u; ++i) {
        if (g_ch[i].pc == 0)
            continue;
        if (g_ch[i].gate > 0u) {
            --g_ch[i].gate;
            if (g_ch[i].gate == 0u)     /* гейт отзвучал — нота */
                vi53_set_channel(i, g_ch[i].div);
        } else if (g_ch[i].cnt > 0u) {
            --g_ch[i].cnt;
        } else {
            tone_event(i);
        }
    }
    if (g_dr.pc != 0) {
        if (g_dr.cnt > 0u)
            --g_dr.cnt;
        else
            drum_event();
    }
}

/* Вызов из кадрового прерывания: потребляет num/den тика clock.
 * drum_tick() вызывается рядом (огибающие семплов — каждый кадр). */
void music_tick(void)
{
    unsigned char n;

    if (!g_playing || g_paused || g_song == 0)
        return;

    diag_music_tick_count++;

    g_acc += g_song->tempo_num;
    n = (unsigned char)(g_acc / g_song->tempo_den);
    g_acc %= g_song->tempo_den;
    while (n-- > 0u)
        clock_tick();
}
