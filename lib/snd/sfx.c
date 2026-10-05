/*
 * sfx.c — трёхголосный смеситель звуковых эффектов (КР580ВИ53 или AY-3-8910).
 *
 * Отличия от прежних плееров библиотеки:
 *   - music.c играет одну партитуру (байткод), sound.c — одну шаговую
 *     мелодию: оба занимают все три канала и не дают наложить один короткий
 *     сигнал на другой. Игре («Ну, погоди!») нужно ровно обратное: писк
 *     пойманного яйца, кряканье цыплёнка и переключение волка могут звучать
 *     одновременно.
 *   - здесь эффект — маленькая таблица шагов, а аллокатор выдаёт под него
 *     один свободный канал; если каналов нет, эффект с бо́льшим prio вытесняет
 *     самый низкоприоритетный, иначе эффект отбрасывается (игра не должна
 *     «взрывать» звуком каждый кадр).
 *
 * Один голос = один эффект: шаги идут последовательно, каждый шаг задаёт
 * ноту (абсолютный номер из v06_div_tab, 0 = тишина), длительность в кадрах
 * 50 Гц и глайссандо (прибавку к ДЕЛИТЕЛЮ каждый кадр — так же удобно делать
 * и подъёмы, и падения тона).
 *
 * Шумовых эффектов здесь нет сознательно: шум в библиотеке один на всех и
 * живёт в drums.asm (Tape Out / AY Noise C), а играм довольно трёх тональных
 * каналов — «разбитое яйцо» и «конец игры» делаются гудком с падением на том
 * же vi53_set_channel(). Если шум всё-таки нужен, зовите drum_sample_play()
 * напрямую, прослойка sfx_hit() убрана как неиспользуемая.
 *
 * Запись в чип — тем же способом, что и music.c: устройство выбирается
 * ФЛАГОМ СБОРКИ (-DMUSIC_AY_DRUMS_AY собирает ROM на AY, иначе — на ВИ53),
 * никаких runtime-переключателей. Та же логика внутри:
 *   - нота берётся из своей таблицы (v06_div_tab / v06_ay_period_tab), обе
 *     вычислены друг из друга в notes.c, так что номер ноты один и тот же;
 *   - глайссандо в шагах таблиц задано в ДЕЛИТЕЛЯХ ВИ53 (там и придумано), для
 *     AY шаг пересчитывается тем же отношением 887/12000 — наклон в процентах
 *     за кадр остаётся тем же, иначе 12-битный период кончался бы за пару кадров;
 *   - верхняя граница тона: у ВИ53 65535 (переполнение 16 бит), у AY 4095
 *     (R0/R2/R4 — 12-битные, старше бита просто не помещается);
 *   - у AY тон без громкости молчит, поэтому на атаке канала ставится
 *     фиксированная SFX_AY_VOLUME (режим огибающей со станции снимается).
 *
 * Вызов: sfx_tick() из главного цикла сразу после v06_wait_frame() (50 Гц),
 * как music_tick()/drum_tick(). Пока играет музыка, каналы делят два движка:
 * атакующая нота партитуры перепишет голос эффекта — в меню это осознанно
 * допустимо (щелчки коротки), в игре музыка стоит и конфликта нет.
 */

#include "v06.h"

#define SFX_VOICES   3u           /* канала чипа: 0, 1, 2                      */
#define SFX_NOTES    95u          /* размер v06_div_tab / v06_ay_period_tab    */

#ifdef MUSIC_AY_DRUMS_AY
#define SFX_TONE_MAX   4095u      /* период AY — 12 бит                        */
#define SFX_AY_VOLUME  12u         /* фиксированная громкость эффекта на AY    */
#else
#define SFX_TONE_MAX   65535u     /* делитель ВИ53 — 16 бит                     */
#endif

static struct {
    const sfx_step_t *steps;      /* 0 = голос свободен                       */
    unsigned char idx;            /* текущий шаг                              */
    unsigned char len;            /* шагов в эффекте                          */
    unsigned char left;           /* кадров до конца текущего шага            */
    unsigned char prio;           /* приоритет запустившего эффекта           */
    unsigned int  tone;           /* текущий тон: делитель ВИ53 или период AY */
} g_voice[SFX_VOICES];

/* Записать тон в канал и запомнить его. */
static void voice_write(unsigned char ch, unsigned int tone)
{
    g_voice[ch].tone = tone;
#ifdef MUSIC_AY_DRUMS_AY
    ay_set_fixed_volume((unsigned char)(1u << ch), SFX_AY_VOLUME);
    ay_set_tone_period(ch, tone);
#else
    vi53_set_channel(ch, tone);
#endif
}

/* Нота -> тон текущего чипа. */
static unsigned int voice_tone(unsigned char note)
{
#ifdef MUSIC_AY_DRUMS_AY
    return (note < SFX_NOTES) ? v06_ay_period_tab[note] : 0u;
#else
    return (note < SFX_NOTES) ? v06_div_tab[note] : 0u;
#endif
}

/* Шаг глайссандо кадра в тон-единицах чипа. В таблицах он написан в
 * делителях ВИ53; период AY = (div*887+6000)/12000, и 887*127 в 16 бит не
 * влезает, поэтому берется приближение 27/365 = 0,07397 (ошибка 0,07 %).
 * Знак сохраняется, округление — к нулю. */
static int voice_detune(int detune)
{
#ifdef MUSIC_AY_DRUMS_AY
    unsigned int mag;

    if (detune == 0)
        return 0;
    mag = (unsigned int)((detune < 0) ? -detune : detune);
    mag = (mag * 27u + 182u) / 365u;
    return (detune < 0) ? -(int)mag : (int)mag;
#else
    return detune;
#endif
}

/* Начать шаг голосу: нота -> тон, загрузка длительности, сразу в чип. */
static void voice_load(unsigned char ch)
{
    const sfx_step_t *s;

    s = &g_voice[ch].steps[g_voice[ch].idx];
    voice_write(ch, voice_tone(s->note));
    g_voice[ch].left = (s->ticks != 0u) ? s->ticks : 1u;
}

static void voice_stop(unsigned char ch)
{
    g_voice[ch].steps = 0;
    g_voice[ch].left = 0u;
    g_voice[ch].idx = 0u;
#ifdef MUSIC_AY_DRUMS_AY
    ay_note_off(ch);
#else
    vi53_set_channel(ch, 0u);
#endif
}

static void voice_start(unsigned char ch, const sfx_t *fx)
{
    g_voice[ch].steps = fx->steps;
    g_voice[ch].len = fx->len;
    g_voice[ch].idx = 0u;
    g_voice[ch].prio = fx->prio;
    voice_load(ch);
}

void sfx_init(void)
{
    unsigned char i;

#ifdef MUSIC_AY_DRUMS_AY
    ay_mixer_init();              /* Tone ABC, фиксированная громкость        */
#endif
    for (i = 0u; i < SFX_VOICES; ++i) {
        g_voice[i].steps = 0;
        g_voice[i].left = 0u;
        g_voice[i].idx = 0u;
        g_voice[i].len = 0u;
        g_voice[i].prio = 0u;
        g_voice[i].tone = 0u;
#ifdef MUSIC_AY_DRUMS_AY
        ay_note_off(i);
#else
        vi53_set_channel(i, 0u);
#endif
    }
}

/* 1 — эффект запущен, 0 — каналов не хватило и вытеснять нечего. */
unsigned char sfx_play(const sfx_t *fx)
{
    unsigned char i, worst;

    if (fx->steps == 0 || fx->len == 0u)
        return 0u;

    for (i = 0u; i < SFX_VOICES; ++i) {
        if (g_voice[i].steps == 0) {
            voice_start(i, fx);
            return 1u;
        }
    }

    /* Все три заняты: берём самый низкоприоритетный, но только если
     * новичок действительно важнее (равный приоритет НЕ вытесняет — иначе
     * частые одинаковые сигналы будут обрывать друг друга). */
    worst = 0u;
    for (i = 1u; i < SFX_VOICES; ++i) {
        if (g_voice[i].prio < g_voice[worst].prio)
            worst = i;
    }
    if (fx->prio <= g_voice[worst].prio)
        return 0u;

    voice_start(worst, fx);
    return 1u;
}

void sfx_stop_all(void)
{
    unsigned char i;

    for (i = 0u; i < SFX_VOICES; ++i) {
        if (g_voice[i].steps != 0)
            voice_stop(i);
    }
}

unsigned char sfx_busy(void)
{
    unsigned char i;

    for (i = 0u; i < SFX_VOICES; ++i)
        if (g_voice[i].steps != 0)
            return 1u;
    return 0u;
}

/* Каждый кадр 50 Гц: досчитать шаги, сдвинуть делитель глайссандо. */
void sfx_tick(void)
{
    unsigned char i;
    const sfx_step_t *s;
    unsigned int d;

    for (i = 0u; i < SFX_VOICES; ++i) {
        if (g_voice[i].steps == 0)
            continue;

        s = &g_voice[i].steps[g_voice[i].idx];
        if (g_voice[i].left > 1u) {
            --g_voice[i].left;
            if (s->detune == 0)
                continue;
            /* знаковое смещение тона; 0 — это «тишина», пропускаем */
            d = g_voice[i].tone + (unsigned int)voice_detune((int)s->detune);
            if (d == 0u || (s->detune < 0 && d > g_voice[i].tone))
                d = 1u;              /* свип вверх дошёл до границы частот   */
            else if (s->detune > 0 && d < g_voice[i].tone)
                d = SFX_TONE_MAX;    /* свип вниз упёрся в разрядность тона */
            voice_write(i, d);
            continue;
        }

        /* шаг доиграл */
        ++g_voice[i].idx;
        if (g_voice[i].idx >= g_voice[i].len)
            voice_stop(i);
        else
            voice_load(i);
    }
}
