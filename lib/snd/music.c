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
 * Тона — КР580ВИ53 (карта портов и режимы как в sound.c) в режиме
 * MUSIC_MODE_VI53 или тоновые каналы AY-3-8910 в режиме MUSIC_MODE_AY.
 * Ударные (шум) — drums.asm: в AY-режиме это шумовой канал AY (R6/R10,
 * микшер R7), в VI53-режиме — программный 1-битный LFSR-шум на Tape Out
 * (PIA1 Port C bit 0, порт 01h/BSR 00h). Вызывать drum_tick() рядом с
 * music_tick().
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

/* ------------------------- AY-3-8910 backend ------------------------- */

/* Запись регистра AY-3-8910. Аргументы через volatile locals
 * (гарантия доступа по стеку из asm), OUT — в едином asm-блоке,
 * что исключает проблему порядка аргументов sccz80 и гонок
 * с прерываниями между двумя OUT. */
static volatile unsigned char ay_r_, ay_v_;
static void ay_write(unsigned char reg, unsigned char val)
{
    ay_r_ = reg;
    ay_v_ = val;
#asm
    di
    ld  a, (_ay_r_)
    out (0x15), a
    ld  a, (_ay_v_)
    out (0x14), a
    ei
#endasm
}

/* Зеркало R7 (определено в drums.asm): хранит текущее значение
 * микшера AY, чтобы ударные могли включить/выключить Noise C, не трогая
 * биты тонов. Обновляется при каждом ay_write(7, ...). */
extern unsigned char g_ay_r7;

void ay_set_r7(unsigned char val)
{
    g_ay_r7 = val;
    ay_write(7, val);
}

/* Состояние огибающей/громкости. Огибающая в AY ОДНА ОБЩАЯ на все три
 * канала (R11/R12/R13), поэтому shape/period — скаляры, а ay_env_mode —
 * битовая маска подключаемых каналов (бит0=A, бит1=B, бит2=C; макросы
 * AY_CH_A/B/C). Всё применяется в ay_set_tone на атаке ноты (см.
 * ay_set_envelope / ay_set_fixed_volume ниже) — сами эти функции в
 * регистры AY не пишут, чтобы не дать непрерывный тон.
 * ay_fixed_vol — фиксированная громкость канала (0..15) для атаки вне
 * огибающей; R8/R9/R10 независимы, поэтому это массив; по умолч. 15
 * (выставляется в ay_mixer_init). */
static unsigned char ay_env_mode;      /* маска каналов на огибающей */
static unsigned char ay_env_shape;     /* форма R13 (общая)          */
static unsigned int  ay_env_period;    /* период R11/R12 (общий)     */
static unsigned char ay_fixed_vol[3];

/* Базовая конфигурация микшера AY для режима MUSIC_MODE_AY:
 * тоны A/B/C включены, шум C выключен (его включают ударные drums.asm
 * при триггере), шум A/B выключен. В MUSIC_MODE_VI53 шум ударных идёт
 * на Tape Out, поэтому ударные в AY-регистры не пишут вовсе.
 * drum_init() вызывается ДО music_mode(), R7 перезаписываем здесь. */
static void ay_mixer_init(void)
{
    /* Фиксированная громкость по умолчанию на каждый канал. */
    ay_fixed_vol[0] = ay_fixed_vol[1] = ay_fixed_vol[2] = 15u;
    /* Tone ABC on, Noise ABC off. Noise C включают ударные
     * (drums.asm) при триггере и выключают при завершении. */
    ay_set_r7(0xF8);
}

/* Конвертация делителя ВИ53 в период AY-3-8910.
 * Формула: period_AY = round(AY_CLOCK * div_VI53 / (16 * 1500000)),
 * AY_CLOCK = 1774000 Гц.  Целочисленная форма:
 *   period_AY = (div * 887 + 6000) / 12000
 * (коэффициент 1774000/(16*1500000) = 887/12000, GCD = 125).
 * Максимальный промежуточный: 65535 * 887 = 58 129 545 < 2^32.
 * Результат ограничен 12-битным диапазоном AY: 1..4095.
 * При div == 0 — тишина (возврат 0). */
static unsigned int vi53_to_ay_period(unsigned int div)
{
    unsigned long p;
    if (div == 0u)
        return 0u;
    p = ((unsigned long)div * 887UL + 6000UL) / 12000UL;
    if (p > 4095UL) p = 4095UL;
    if (p < 1UL)    p = 1UL;
    return (unsigned int)p;
}

/* Установка тона AY (период + громкость). div_VI53 — делитель из
 * div_tab[], конвертируется в период AY целочисленной формулой
 * (vi53_to_ay_period). divisor = 0 — тишина (громкость в 0,
 * период не трогаем — ТЗ §10). Канал C (R10) — общий с drums.asm:
 * огибающая удара перезаписывает громкость мелодии, это штатное
 * поведение (ТЗ §6-7).
 *
 * Режим envelope: если для канала выставлен бит в ay_env_mode, то на
 * каждой атаке ноты (music_note_on, сразу после 1-тикового гейта)
 * генератор перезапускается записью R13 и канал подключается битом 4 в
 * R8/R9/R10 (0x1F). На music_note_off() громкость обнуляется → бит 4
 * спадает аппаратно, огибающая «отпускает» канал до следующей атаки.
 * Это тот же приём, что в движе Konami/NES, и согласуется с 1-тиковым
 * гейтом тональных событий в tone_event(). */

static void ay_set_tone(unsigned char ch, unsigned int div_VI53)
{
    unsigned int period;
    static const unsigned char preg[3] = { 0, 2, 4 };  /* R0, R2, R4 */
    static const unsigned char vreg[3] = { 8, 9, 10 }; /* R8, R9, R10 */

    period = vi53_to_ay_period(div_VI53);
    ay_write(preg[ch], (unsigned char)(period & 0xFFu));
    ay_write(preg[ch] + 1u, (unsigned char)(period >> 8));
    if (period == 0u) {
        ay_write(vreg[ch], 0u);    /* note OFF: volume = 0 */
    } else if (ay_env_mode & (unsigned char)(1u << ch)) {
        /* Атака на envelope: перезапустить общий генератор и
         * подключить канал. Порядок R11 → R12 → R13 → R8/9/10
         * (ТЗ §6), запись R13 сбрасывает счётчик формы. */
        ay_write(11, (unsigned char)(ay_env_period & 0xFFu));
        ay_write(12, (unsigned char)(ay_env_period >> 8));
        ay_write(13, ay_env_shape);
        ay_write(vreg[ch], 0x1Fu);
    } else {
        /* note ON: фиксированная громкость канала (по умолч. 15) */
        ay_write(vreg[ch], ay_fixed_vol[ch]);
    }
}

static void ay_mute_all(void)
{
    ay_write(8, 0);
    ay_write(9, 0);
    ay_write(10, 0);
}

/* ------------------ AY: аппаратная огибающая (R11..R13) --------------- */

/* Штатный envelope generator AY-3-8910: ОДИН ОБЩИЙ на все три канала.
 * R11 (период lo) / R12 (период hi) / R13 (форма) — физически единственный
 * комплект регистров; R8/R9/R10 только подключают/отключают конкретный
 * канал к генерируемой огибающей (бит 4).
 *
 * СЛЕДСТВИЕ: форма/период глобальные. Вызов ay_set_envelope(mask, ...)
 * МЕНЯЕТ их для ВСЕХ каналов, подключённых к огибающей. Например, был
 * ay_set_envelope(AY_CH_A, DECAY, 1000), затем
 * ay_set_envelope(AY_CH_A | AY_CH_B, TRIANGLE, 4000) — и A, и B теперь на
 * TRIANGLE/4000, и общий генератор перезапустится на ближайшей атаке
 * (запись R13). Независимых огибающих на канал в AY-3-8910 нет.
 *
 * chan_mask — битовая маска каналов (бит0=A/бит1=B/бит2=C; макросы
 * AY_CH_A/B/C). Модель плеера — «применение на атаке ноты»: вызов только
 * сохраняет глобальные shape/period и выставляет ay_env_mode = chan_mask;
 * в регистры AY НЕ пишет (иначе огибающая подключилась бы к уже звучащему
 * тону и дала непрерывный сигнал). На следующей атаке подключённого канала
 * ay_set_tone() запрограммирует R11/R12/R13 и поднимет бит 4 в R8/R9/R10.
 * На music_note_off() громкость обнуляется → бит 4 спадает, огибающая
 * «отпускает» канал до следующей атаки. */
void ay_set_envelope(unsigned char chan_mask,
                     unsigned char shape,
                     unsigned int period)
{
    chan_mask &= 0x07u;         /* только A/B/C */
    if (chan_mask == 0u)
        return;

    /* Одно определение общей огибающей: форма/период глобальные,
     * ay_env_mode = какие каналы к ней подключены. Регистры не трогаем —
     * применит ay_set_tone на атаке. */
    ay_env_shape = (unsigned char)(shape & 0x0Fu);
    ay_env_period = period;
    ay_env_mode = chan_mask;
}

/* Вернуть каналы на фиксированную громкость (снять бит 4 в R8/R9/R10).
 * chan_mask — биты AY_CH_A/B/C; volume применяется ко всем каналам маски.
 * Снимает флаг envelope у этих каналов и запоминает громкость в
 * ay_fixed_vol[]; в регистры НЕ пишет (иначе — фоновый тон). Следующая
 * атака ay_set_tone() отработает по обычной ветке с volume для канала. */
void ay_set_fixed_volume(unsigned char chan_mask,
                         unsigned char volume)
{
    unsigned char ch;

    chan_mask &= 0x07u;         /* только A/B/C */
    if (chan_mask == 0u)
        return;
    volume &= 0x0Fu;
    ay_env_mode &= (unsigned char)~chan_mask;   /* снять огибающую с маски */
    for (ch = 0u; ch < 3u; ++ch)
        if (chan_mask & (unsigned char)(1u << ch))
            ay_fixed_vol[ch] = volume;
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

/* --------------------------- Абстракция вывода ----------------------- */

/* Абстракция вывода: тоновые каналы. Общий флаг режима g_music_mode
 * определён в snd.c (единственный экземпляр, разделяют music.c и
 * drums.asm); объявлен extern в v06.h. */

/* Включение ноты на текущем backend. note_idx — индекс ноты 0-94
 * (как в div_tab[]). VI53 получает делитель напрямую; AY — через
 * конвертацию vi53_to_ay_period() (ТЗ: конвертация параметров). */
static void music_note_on(unsigned char ch, unsigned char note_idx)
{
    if (g_music_mode == MUSIC_MODE_AY) {
        ay_set_tone(ch, div_tab[note_idx]);
    } else {
        vi53_set_channel(ch, div_tab[note_idx]);
    }
}

/* Выключение ноты (тишина). Для AY: volume = 0, период не трогаем
 * (ТЗ §10). Для VI53: режим 3 без загрузки счётчика. */
static void music_note_off(unsigned char ch)
{
    if (g_music_mode == MUSIC_MODE_AY) {
        static const unsigned char vreg[3] = { 8, 9, 10 };
        ay_write(vreg[ch], 0u);
    } else {
        vi53_set_channel(ch, 0u);
    }
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
    if (g_music_mode == MUSIC_MODE_AY) {
        ay_mute_all();
    } else {
        vi53_set_channel(0, 0);
        vi53_set_channel(1, 0);
        vi53_set_channel(2, 0);
    }
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

/* ---------------------- Переключение backend ------------------------ */

/* Глобальное переключение вывода мелодических каналов: ВИ53 ↔ AY.
 * Переключение во время воспроизведения — без сброса позиции, pc,
 * cnt, gate, состояния g_ch[] и drums (ТЗ §14). Меняется только
 * аппаратный backend; текущие ноты восстанавливаются на новом
 * устройстве. Ударные переключаются тем же флагом: AY Noise ↔
 * Tape Out (PC0); звучащий удар глушится на старом выходе. */
void music_mode(unsigned char mode)
{
    unsigned char i;

    if (mode == g_music_mode)
        return;

    /* Смена выхода шума: drum_mode переводит общий флаг и глушит
     * удар на старом выходе (R10 AY + PC0 ленты — см. drums.asm) */
    drum_mode(mode);

    if (mode == MUSIC_MODE_AY) {
        /* ---- VI53 → AY ---- */
        /* 1. Заглушить активные VI53-каналы */
        vi53_set_channel(0, 0u);
        vi53_set_channel(1, 0u);
        vi53_set_channel(2, 0u);
        /* 2. Настроить AY: микшер (R7) + громкости */
        ay_mixer_init();
        ay_mute_all();
        /* 3. Переключить режим */
        g_music_mode = MUSIC_MODE_AY;
        /* 4. Восстановить текущие ноты на AY (если играет) */
        if (g_playing && !g_paused) {
            for (i = 0u; i < 3u; ++i) {
                if (g_ch[i].gate == 0u && g_ch[i].note < 95u &&
                    g_ch[i].pc != 0 && (g_ch_mask & (1u << i)))
                    ay_set_tone(i, div_tab[g_ch[i].note]);
            }
        }
    } else {
        /* ---- AY → VI53 ---- */
        /* 1. Заглушить AY tone channels */
        ay_mute_all();
        /* 2. Вернуть микшер AY в состояние «тоны выкл, шум C не
         * мешает» (как drum_init); шаги sound.c в VI53-каналах */
        ay_set_r7(0xDF);
        /* 3. Переключить режим */
        g_music_mode = MUSIC_MODE_VI53;
        /* 4. Восстановить текущие ноты на VI53 (если играет) */
        if (g_playing && !g_paused) {
            for (i = 0u; i < 3u; ++i) {
                if (g_ch[i].gate == 0u && g_ch[i].note < 95u &&
                    g_ch[i].pc != 0 && (g_ch_mask & (1u << i)))
                    vi53_set_channel(i, div_tab[g_ch[i].note]);
            }
        }
    }
}

/* Маскировка каналов: биты 0-2 — тональные 0-2, бит 3 — ударные.
 * 0x0F (по умолчанию) — все каналы включены. */
void music_set_channel_mask(unsigned char mask)
{
    g_ch_mask = mask;
    /* При выключении тональных каналов — сразу тишина */
    if (g_music_mode == MUSIC_MODE_AY) {
        if (!(mask & 1u)) ay_set_tone(0, 0u);
        if (!(mask & 2u)) ay_set_tone(1, 0u);
        if (!(mask & 4u)) ay_set_tone(2, 0u);
    } else {
        if (!(mask & 1u)) vi53_set_channel(0, 0u);
        if (!(mask & 2u)) vi53_set_channel(1, 0u);
        if (!(mask & 4u)) vi53_set_channel(2, 0u);
    }
    if (!(mask & 8u)) drum_mute();
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
         * тик = len), дрейфа нет. Делитель отложен, запись в ВИ53 — в
         * clock_tick(). */
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
