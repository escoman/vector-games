/*
 * ay.c — низкоуровневый API AY-3-8910, Вектор-06Ц.
 *
 * Единственный владелец записи в регистры AY из C (ТЗ §17). Порты:
 * выбор регистра — НЕЧЁТНЫЙ 0x15, данные — 0x14 (эмулятор декодирует
 * ay.write(port & 1, v): addr==1 — выбор, addr==0 — данные).
 *
 * Три тональных канала A/B/C: период R0/R1, R2/R3, R4/R5; громкость
 * R8/R9/R10. Огибающая в AY ОДНА ОБЩАЯ на все каналы: R11/R12
 * (период) и R13 (форма) физически единственные, поэтому shape/period
 * — скаляры, а ay_env_mode — битовая маска подключаемых каналов
 * (AY_CH_A/B/C). Независимых огибающих на канал нет (ТЗ §8).
 *
 * Зеркало микшера g_ay_r7 определено в drums.asm (единственный автор
 * бит шума/тона C); здесь объявлено extern. Поэтому ROM, линкующий
 * ay.c, обязан линковать и drums.asm.
 *
 * Конверсия «делитель ВИ53 → период AY» из модуля УБРАНА: высоты нот
 * берутся из v06_ay_period_tab[] (lib/snd/notes.c) по абсолютному
 * номеру ноты — без 32-битного умножения/деления.
 */

#include "v06.h"

/* Запись регистра AY-3-8910. Аргументы через volatile locals
 * (гарантия доступа по стеку из asm), OUT — в едином asm-блоке.
 *
 * БЕЗ di/ei: функция вызывается из кадрового прерывания
 * (music_tick → ay_set_tone_period → ay_write), где прерывания уже
 * замаскированы (8080 сам сбрасывает IFF при подтверждении, а
 * isr_frame делает ei только в самом конце). Лишний ei здесь
 * разрешил бы прерывания посреди ISR. Пара out(0x15)/out(0x14)
 * атомарна в ISR и без di. */
static volatile unsigned char ay_r_, ay_v_;
void ay_write(unsigned char reg, unsigned char val)
{
    ay_r_ = reg;
    ay_v_ = val;
#asm
    ld  a, (_ay_r_)
    out (0x15), a
    ld  a, (_ay_v_)
    out (0x14), a
#endasm
}

/* Зеркало R7 (определено в drums.asm): хранит текущее значение
 * микшера AY, чтобы ударные могли включить/выключить Noise C, не трогая
 * биты тонов. Обновляется при каждом ay_set_r7(...). */
extern unsigned char g_ay_r7;

/* "Желаемая" громкость канала C (R10) со стороны мелодии. Значение,
 * которое ay_set_tone_period() записала бы в R10, если бы ударные сейчас
 * его не трогали. Обновляется на каждой атаке/релизе канала C и
 * читается из drums.asm: чтобы в конце удара вернуть R10 к мелодии,
 * а не к 0, и чтобы drum_live() брала max(drum_vol, мелодия).
 * Определение — в drums.asm (там же, где g_ay_r7), чтобы модуль
 * линковался и в VI53-only сборке без ay.c. */
extern unsigned char g_ay_r10_melody;

/* Состояние пост-релиза R10 в drums.asm. Когда ay.c пишет R10 мелодии
 * напрямую (атака/релиз/мьют), надо синхронизировать "последнее
 * записанное значение" и снять флаг пост-релиза — иначе drum_tick
 * продолжит писать R10 по своей траектории и перекроет свежую
 * мелодийную громкость (нота «сядет» на несколько кадров). */
extern unsigned char drum_r10_current;
extern unsigned char drum_r10_release;

void ay_set_r7(unsigned char val)
{
    g_ay_r7 = val;
    ay_write(7, val);
}

/* Состояние огибающей/громкости. Огибающая в AY ОДНА ОБЩАЯ на все три
 * канала (R11/R12/R13), поэтому shape/period — скаляры, а ay_env_mode —
 * битовая маска подключаемых каналов (бит0=A, бит1=B, бит2=C; макросы
 * AY_CH_A/B/C). Всё применяется в ay_set_tone_period на атаке ноты (см.
 * ay_set_envelope / ay_set_fixed_volume ниже) — сами эти функции в
 * регистры AY не пишут, чтобы не дать непрерывный тон.
 * ay_fixed_vol — фиксированная громкость канала (0..15) для атаки вне
 * огибающей; R8/R9/R10 независимы, поэтому это массив; по умолч. 15
 * (выставляется в ay_mixer_init). */
static unsigned char ay_env_mode;      /* маска каналов на огибающей */
static unsigned char ay_env_shape;     /* форма R13 (общая)          */
static unsigned int  ay_env_period;    /* период R11/R12 (общий)     */
static unsigned char ay_fixed_vol[3];

/* Базовая конфигурация микшера AY для вывода музыки на AY:
 * тоны A/B/C включены, шум C выключен (его включают ударные drums.asm
 * при триггере), шум A/B выключен. При выводе на ВИ53 шум ударных идёт
 * на Tape Out, поэтому ударные в AY-регистры не пишут вовсе.
 * drum_init() вызывается ДО привязки вывода, R7 перезаписываем здесь. */
void ay_mixer_init(void)
{
    /* Фиксированная громкость по умолчанию на каждый канал. */
    ay_fixed_vol[0] = ay_fixed_vol[1] = ay_fixed_vol[2] = 15u;
    g_ay_r10_melody = 0u;
    drum_r10_current = 0u;
    drum_r10_release = 0u;
    /* Tone ABC on, Noise ABC off. Noise C включают ударные
     * (drums.asm) при триггере и выключают при завершении. */
    ay_set_r7(0xF8);
}

/* Установка тона AY по ГОТОВОМУ периоду (12 бит) + громкость.
 * period = 0 — тишина (громкость в 0, период не трогаем — ТЗ §10).
 * Это аппаратный уровень: ROM передаёт сюда период из готовой таблицы
 * v06_ay_period_tab[] (см. макрос AY_PER(N_A(4)) в v06.h), поэтому
 * в вызове нет 32-битного умножения/деления — погодно и для кадрового
 * ISR. Канал C (R10) — общий с drums.asm: огибающая удара перезаписывает
 * громкость мелодии, это штатное поведение (ТЗ §6-7).
 *
 * Режим envelope: если для канала выставлен бит в ay_env_mode, то на
 * каждой атаке ноты (сразу после 1-тикового гейта) генератор
 * перезапускается записью R13 и канал подключается битом 4 в
 * R8/R9/R10 (0x1F). На ay_note_off() громкость обнуляется → бит 4
 * спадает аппаратно, огибающая «отпускает» канал до следующей атаки.
 * Это тот же приём, что в движе Konami/NES, и согласуется с 1-тиковым
 * гейтом тональных событий в music.c. */
void ay_set_tone_period(unsigned char ch, unsigned int period)
{
    static const unsigned char preg[3] = { 0, 2, 4 };  /* R0, R2, R4 */
    static const unsigned char vreg[3] = { 8, 9, 10 }; /* R8, R9, R10 */
    unsigned char vol;

    ay_write(preg[ch], (unsigned char)(period & 0xFFu));
    ay_write(preg[ch] + 1u, (unsigned char)(period >> 8));
    if (period == 0u) {
        vol = 0u;                          /* note OFF: volume = 0 */
    } else if (ay_env_mode & (unsigned char)(1u << ch)) {
        /* Атака на envelope: перезапустить общий генератор и
         * подключить канал. Порядок R11 → R12 → R13 → R8/9/10
         * (ТЗ §6), запись R13 сбрасывает счётчик формы. */
        ay_write(11, (unsigned char)(ay_env_period & 0xFFu));
        ay_write(12, (unsigned char)(ay_env_period >> 8));
        ay_write(13, ay_env_shape);
        vol = 0x1Fu;
    } else {
        /* note ON: фиксированная громкость канала (по умолч. 15) */
        vol = ay_fixed_vol[ch];
    }
    ay_write(vreg[ch], vol);
    if (ch == 2u) {
        g_ay_r10_melody = vol;
        drum_r10_current = vol;
        drum_r10_release = 0u;
    }
}

/* Выключение тонального канала (громкость в 0, период не трогаем). */
void ay_note_off(unsigned char ch)
{
    static const unsigned char vreg[3] = { 8, 9, 10 }; /* R8, R9, R10 */
    ay_write(vreg[ch], 0u);
    if (ch == 2u) {
        g_ay_r10_melody = 0u;
        drum_r10_current = 0u;
        drum_r10_release = 0u;
    }
}

/* Тишина на всех трёх тональных каналах. */
void ay_mute_all(void)
{
    ay_write(8, 0);
    ay_write(9, 0);
    ay_write(10, 0);
    g_ay_r10_melody = 0u;
    drum_r10_current = 0u;
    drum_r10_release = 0u;
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
 * ay_set_tone_period() запрограммирует R11/R12/R13 и поднимет бит 4 в
 * R8/R9/R10. На ay_note_off() громкость обнуляется → бит 4 спадает,
 * огибающая «отпускает» канал до следующей атаки. */
void ay_set_envelope(unsigned char chan_mask,
                     unsigned char shape,
                     unsigned int period)
{
    chan_mask &= 0x07u;         /* только A/B/C */
    if (chan_mask == 0u)
        return;

    /* Одно определение общей огибающей: форма/период глобальные,
     * ay_env_mode = какие каналы к ней подключены. Регистры не трогаем —
     * применит ay_set_tone_period на атаке. */
    ay_env_shape = (unsigned char)(shape & 0x0Fu);
    ay_env_period = period;
    ay_env_mode = chan_mask;
}

/* Вернуть каналы на фиксированную громкость (снять бит 4 в R8/R9/R10).
 * chan_mask — биты AY_CH_A/B/C; volume применяется ко всем каналам маски.
 * Снимает флаг envelope у этих каналов и запоминает громкость в
 * ay_fixed_vol[]; в регистры НЕ пишет (иначе — фоновый тон). Следующая
 * атака ay_set_tone_period() отработает по обычной ветке с volume для
 * канала. */
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
