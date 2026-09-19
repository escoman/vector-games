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
 * Тона — КР580ВИ53 (vi53/vi53.c) или тоновые каналы AY-3-8910
 * (ay/ay.c): устройство выбирается ЯВНО привязкой вывода
 * (music_start_vi53/music_start_ay, music_use_vi53/music_use_ay),
 * а не глобальным режимом. Вывод идёт через драйвер music_out_t
 * (набор функций note_on/note_off/silence_all), поэтому в тональном
 * горячем пути нет ветвления по режиму (ТЗ §6).
 * Ударные (шум) — drums.asm: при выводе на AY это шумовой канал AY
 * (R6/R10, микшер R7), при выводе на ВИ53 — программный 1-битный
 * LFSR-шум на Tape Out (PIA1 Port C bit 0, порт 01h/BSR 00h). Выбор
 * выхода ударных drum_route_tape()/drum_route_ay() делается при
 * привязке вывода. Вызывать drum_tick() рядом с music_tick().
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
 *   0xEA <lo> <hi> — JMP назад на (lo | hi<<8) байт: бесконечный
 *               цикл основной части мелодии (intro + loop). Выход
 *               только из game code (music_stop()).
 */

#include "v06.h"

#ifndef MUSIC_AY_DRUMS_AY   /* таблица ВИ53 нужна, пока не собран AY-only ROM */
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
#endif

#ifndef MUSIC_VI53_DRUMS_TAPE   /* таблица AY нужна, пока не собран VI53-only ROM */
/* Таблица периодов AY-3-8910, предвычисленная из div_tab[] по формуле
 * (div*887 + 6000)/12000 с ограничением 1..4095 (0 = тишина). Плеер
 * берёт отсюда готовый период по индексу ноты, поэтому в кадровом ISR
 * нет 32-битного умножения/деления — music_tick быстрый и не теряет
 * кадры (иначе темп «плывёт»). Индексы 0-11 — паузы (div=0 → 0). */
static const unsigned int ay_period_tab[95] = {
        0u,     0u,     0u,     0u,     0u,     0u,     0u,     0u,
        0u,     0u,     0u,     0u,  3390u,  3200u,  3020u,  2851u,
     2691u,  2540u,  2397u,  2263u,  2136u,  2016u,  1903u,  1796u,
     1695u,  1600u,  1510u,  1425u,  1345u,  1270u,  1199u,  1131u,
     1068u,  1008u,   951u,   898u,   848u,   800u,   755u,   713u,
      673u,   635u,   599u,   566u,   534u,   504u,   476u,   449u,
      424u,   400u,   378u,   356u,   336u,   317u,   300u,   283u,
      267u,   252u,   238u,   224u,   212u,   200u,   189u,   178u,
      168u,   159u,   150u,   141u,   133u,   126u,   119u,   112u,
      106u,   100u,    94u,    89u,    84u,    79u,    75u,    71u,
       67u,    63u,    59u,    56u,    53u,    50u,    47u,    45u,
       42u,    40u,    37u,    35u,    33u,    31u,    30u
};
#endif

/* --------------------------- Драйверы вывода ------------------------- */

/* Привязка вывода: тоновые каналы направляют события на явно выбранное
 * физическое устройство — КР580ВИ53 (vi53/vi53.c) или AY-3-8910
 * (ay/ay.c). Никакого глобального «режима звука»: music.c хранит
 * указатель на драйвер (g_out), выбор делается вызовом
 * music_start_vi53/music_start_ay или music_use_vi53/music_use_ay.
 * note_on принимает индекс ноты 0-94; каждый драйвер берёт готовое
 * значение из своей таблицы: ВИ53 — делитель div_tab[], AY — период
 * ay_period_tab[] (без 32-битной математики в ISR). */
typedef struct {
    void (*note_on)(unsigned char ch, unsigned char note_idx);
    void (*note_off)(unsigned char ch);
    void (*silence_all)(void);
} music_out_t;

#ifndef MUSIC_AY_DRUMS_AY   /* ВИ53-драйвер: не собирается в AY-only ROM */
static void vi53_on(unsigned char ch, unsigned char note_idx)
{
    vi53_set_channel(ch, div_tab[note_idx]);
}
static void vi53_off(unsigned char ch)
{
    vi53_set_channel(ch, 0u);
}
static void vi53_silence_all(void)
{
    vi53_set_channel(0, 0u);
    vi53_set_channel(1, 0u);
    vi53_set_channel(2, 0u);
}
#endif

#ifndef MUSIC_VI53_DRUMS_TAPE   /* AY-драйвер: не собирается в VI53-only ROM */
static void ay_on(unsigned char ch, unsigned char note_idx)
{
    ay_set_tone_period(ch, ay_period_tab[note_idx]);
}
static void ay_off(unsigned char ch)
{
    ay_note_off(ch);
}
static void ay_silence_all(void)
{
    ay_mute_all();
}
#endif

#ifndef MUSIC_AY_DRUMS_AY
static const music_out_t music_out_vi53 = { vi53_on, vi53_off, vi53_silence_all };
#endif
#ifndef MUSIC_VI53_DRUMS_TAPE
static const music_out_t music_out_ay   = { ay_on,   ay_off,   ay_silence_all };
#endif

/* Текущий драйвер вывода (по умолчанию ВИ53; в AY-only ROM — AY). Локальное
 * состояние плеера, а не глобальный переключатель всей звуковой системы. */
#ifndef MUSIC_AY_DRUMS_AY
static const music_out_t *g_out = &music_out_vi53;
#else
static const music_out_t *g_out = &music_out_ay;
#endif

/* Включение ноты на привязанном устройстве. note_idx — индекс ноты
 * 0-94 (как в div_tab[]/ay_period_tab[]). */
static void music_note_on(unsigned char ch, unsigned char note_idx)
{
    g_out->note_on(ch, note_idx);
}

/* Выключение ноты (тишина) на привязанном устройстве. */
static void music_note_off(unsigned char ch)
{
    g_out->note_off(ch);
}

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
    unsigned char note;         /* индекс ноты 0-94 (div_tab/ay_period) */
} mus_ch_t;

static const music_song_t *g_song;
static mus_ch_t g_ch[3];        /* тоновые партитуры                  */
static mus_ch_t g_dr;           /* партитура ударных                  */

static unsigned char g_playing;
static unsigned char g_paused;
static unsigned char g_loop;
static unsigned char g_ch_mask = 0x0F; /* биты 0-2: тон 0-2, бит 3: ударные */
static unsigned int g_acc;      /* остаток в аккумуляторе темпа       */

/* ------------------------------ Помощники ----------------------------- */

static void silence_tones(void)
{
    g_out->silence_all();
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

/* Общий запуск транспорта: сброс всех четырёх потоков на позицию 0.
 * Устройство вывода должно быть привязано ДО вызова (g_out). */
static void music_start_common(void)
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
    silence_tones();
    drum_mute();                /* старт всех потоков с позиции 0 */
}

/* ------------------------------- API ---------------------------------- */

void music_set_data(const music_song_t *song)
{
    g_song = song;
    music_stop();
}

/* Совместимость: запуск на «своём» устройстве вывода, выбранном флагом
 * сборки. В AY-only ROM мелодия идёт на AY, иначе — на КР580ВИ53
 * (ударные на Tape Out), как прежний режим по умолчанию. */
void music_start(void)
{
#ifdef MUSIC_AY_DRUMS_AY
    music_start_ay();
#else
    music_start_vi53();
#endif
}

#ifndef MUSIC_AY_DRUMS_AY   /* не нужен в AY-only ROM */
/* Запуск с явной привязкой вывода к КР580ВИ53: мелодия на трёх каналах
 * ВИ53, ударные на Tape Out (PC0). */
void music_start_vi53(void)
{
    g_out = &music_out_vi53;
    drum_route_tape();
    music_start_common();
}
#endif

#ifndef MUSIC_VI53_DRUMS_TAPE   /* не нужен в VI53-only ROM */
/* Запуск с явной привязкой вывода к AY-3-8910: мелодия на каналах
 * A/B/C, ударные на шумовом генераторе AY (Noise C). */
void music_start_ay(void)
{
    g_out = &music_out_ay;
    drum_route_ay();
    ay_mixer_init();
    music_start_common();
}
#endif

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
    g_ch_mask = 0x0Fu;
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

/* ---------------------- Явная привязка вывода ------------------------ */

#if !defined(MUSIC_AY_DRUMS_AY) && !defined(MUSIC_VI53_DRUMS_TAPE)   /* live-перепривязка нужна только ROM с обоими выводами */
/* Перепривязка вывода к КР580ВИ53 БЕЗ сброса транспорта: позиция, pc,
 * cnt, gate, состояние g_ch[] и ударных сохраняются (ТЗ §14). Меняется
 * только устройство; текущие ноты восстанавливаются на нём. Ударные
 * переводятся на Tape Out; звучащий удар глушится на старом выходе.
 * Замена прежнего глобального переключателя режима: устройство выбирается
 * именем функции, а не значением общего флага. */
void music_use_vi53(void)
{
    unsigned char i;

    if (g_out == &music_out_vi53)
        return;

    /* Смена выхода шума: drum_route_tape переводит маршрут и глушит
     * удар на старом выходе (R10 AY + PC0 ленты — см. drums.asm). */
    drum_route_tape();

    /* ---- AY → ВИ53 ---- */
    /* 1. Заглушить AY tone channels */
    ay_mute_all();
    /* 2. Вернуть микшер AY в состояние «тоны выкл, шум C не мешает» */
    ay_set_r7(0xDF);
    /* 3. Переключить драйвер вывода */
    g_out = &music_out_vi53;
    /* 4. Восстановить текущие ноты на ВИ53 (если играет) */
    if (g_playing && !g_paused) {
        for (i = 0u; i < 3u; ++i) {
            if (g_ch[i].gate == 0u && g_ch[i].note < 95u &&
                g_ch[i].pc != 0 && (g_ch_mask & (1u << i)))
                vi53_set_channel(i, div_tab[g_ch[i].note]);
        }
    }
}

/* Перепривязка вывода к AY-3-8910 БЕЗ сброса транспорта (см. выше).
 * Ударные переводятся на шумовой генератор AY (Noise C). */
void music_use_ay(void)
{
    unsigned char i;

    if (g_out == &music_out_ay)
        return;

    /* Смена выхода шума: drum_route_ay переводит маршрут и глушит удар. */
    drum_route_ay();

    /* ---- ВИ53 → AY ---- */
    /* 1. Заглушить активные VI53-каналы */
    vi53_set_channel(0, 0u);
    vi53_set_channel(1, 0u);
    vi53_set_channel(2, 0u);
    /* 2. Настроить AY: микшер (R7) + громкости */
    ay_mixer_init();
    ay_mute_all();
    /* 3. Переключить драйвер вывода */
    g_out = &music_out_ay;
    /* 4. Восстановить текущие ноты на AY (если играет) */
    if (g_playing && !g_paused) {
        for (i = 0u; i < 3u; ++i) {
            if (g_ch[i].gate == 0u && g_ch[i].note < 95u &&
                g_ch[i].pc != 0 && (g_ch_mask & (1u << i)))
                ay_set_tone_period(i, ay_period_tab[g_ch[i].note]);
        }
    }
}
#endif

/* Маскировка каналов: биты 0-2 — тональные 0-2, бит 3 — ударные.
 * 0x0F (по умолчанию) — все каналы включены. */
void music_set_channel_mask(unsigned char mask)
{
    g_ch_mask = mask;
    /* При выключении тональных каналов — сразу тишина на текущем выводе */
    if (!(mask & 1u)) g_out->note_off(0);
    if (!(mask & 2u)) g_out->note_off(1);
    if (!(mask & 4u)) g_out->note_off(2);
    if (!(mask & 8u)) drum_mute();
}

/* ------------------------------ Рантайм ------------------------------- */

/* Тоновый поток: события читаются до ноты/паузы/конца (управляющие
 * команды исполняются на месте). Запись в устройство вывода — на
 * событии и в clock_tick() по истечении гейта. */
static void tone_event(unsigned char ch)
{
    mus_ch_t *c = &g_ch[ch];
    unsigned char b, n;

    for (;;) {
        b = *c->pc++;
        if (b == MUS_END) {
            c->pc = 0;                  /* поток закончился */
            music_note_off(ch);
            return;
        }
        if (b == MUS_REST) {
            music_note_off(ch);
            /* Текущий тик — первый тик паузы (как и в drum_event),
             * поэтому cnt = len - 1. */
            if (c->len > 1u)
                c->cnt = c->len - 1u;
            else
                c->cnt = 0u;
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
        if (b == MUS_JMP) {             /* <lo> <hi>: JMP назад */
            unsigned int back = (unsigned int)c->pc[0] |
                                ((unsigned int)c->pc[1] << 8);
            c->pc += 2;
            c->pc -= back;
            continue;
        }
        /* Гейт: первый тик ноты — тишина (разделяет повторы той же
         * ноты — ВИ53 иначе тянет звук без разрыва; даёт каждой ноте
         * атаку). Гейт И текущий тик — оба внутри длительности:
         * событие длится ровно len тиков (gate=1 + cnt=len-2 + текущий
         * тик = len), дрейфа нет. Делитель отложен, запись в устройство
         * вывода — в clock_tick(). */
        music_note_off(ch);
        c->gate = 1u;
        c->note = (unsigned char)(b - 1u);
        if (c->len >= 2u)
            c->cnt = c->len - 2u;   /* 1 тик — текущий, 1 тик — гейт */
        else
            c->cnt = 0u;            /* L1: только текущий тик (гейт) */
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
            return;
        }
        if (b == MUS_REST) {
            drum_set_counter();
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
        if (b == MUS_JMP) {             /* <lo> <hi>: JMP назад */
            unsigned int back = (unsigned int)g_dr.pc[0] |
                                ((unsigned int)g_dr.pc[1] << 8);
            g_dr.pc += 2;
            g_dr.pc -= back;
            continue;
        }
        if (b <= 16u)                   /* новый удар — перезапуск */
            drum_sample_play(g_song->samples[b - 1u]);
        drum_set_counter();
        return;
    }
}

/* Один тик music clock: продвижение всех четырёх потоков */
static void clock_tick(void)
{
    unsigned char i;

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
        if (!(g_ch_mask & (1u << i))) {
            /* Канал выключен — пропускаем ноты, но читаем байткод */
            if (g_ch[i].cnt > 0u)
                --g_ch[i].cnt;
            else {
                g_ch[i].gate = 0u;
                tone_event(i);
            }
            continue;
        }
        if (g_ch[i].gate > 0u) {
            --g_ch[i].gate;
            if (g_ch[i].gate == 0u)     /* гейт отзвучал — нота */
                music_note_on(i, g_ch[i].note);
        } else if (g_ch[i].cnt > 0u) {
            --g_ch[i].cnt;
        } else {
            tone_event(i);
        }
    }
    if (g_dr.pc != 0) {
        if (!(g_ch_mask & 8u)) {
            /* Ударные выключены — пропускаем атаки */
            if (g_dr.cnt > 0u)
                --g_dr.cnt;
            else {
                drum_event();
                drum_mute();
            }
        } else if (g_dr.cnt > 0u)
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

    g_acc += g_song->tempo_num;
    n = (unsigned char)(g_acc / g_song->tempo_den);
    g_acc %= g_song->tempo_den;
    while (n-- > 0u)
        clock_tick();
}
