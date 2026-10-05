/*
 * sfx.c — трёхголосный смеситель звуковых эффектов на КР580ВИ53.
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
 * Запись в чип — тем же способом, что и music.c: vi53_set_channel() (0 =
 * только управляющее слово, без загрузки счётчика — проверено на слух).
 *
 * Вызов: sfx_tick() из главного цикла сразу после v06_wait_frame() (50 Гц),
 * как music_tick()/drum_tick(). Пока играет музыка, каналы делят два движка:
 * атакующая нота партитуры перепишет голос эффекта — в меню это осознанно
 * допустимо (щелчки коротки), в игре музыка стоит и конфликта нет.
 */

#include "v06.h"

#define SFX_VOICES   3u           /* канала ВИ53: 0, 1, 2                     */
#define SFX_NOTES    95u          /* размер v06_div_tab                       */

static struct {
    const sfx_step_t *steps;      /* 0 = голос свободен                       */
    unsigned char idx;            /* текущий шаг                              */
    unsigned char len;            /* шагов в эффекте                          */
    unsigned char left;           /* кадров до конца текущего шага            */
    unsigned char prio;           /* приоритет запустившего эффекта           */
    unsigned int  div;            /* текущий делитель (глайссандо меняет его) */
} g_voice[SFX_VOICES];

/* Записать делитель в канал и запомнить его. */
static void voice_write(unsigned char ch, unsigned int div)
{
    g_voice[ch].div = div;
    vi53_set_channel(ch, div);
}

/* Начать шаг голосу: нота -> делитель, загрузка длительности, сразу в чип. */
static void voice_load(unsigned char ch)
{
    const sfx_step_t *s;
    unsigned char n;

    s = &g_voice[ch].steps[g_voice[ch].idx];
    n = s->note;
    voice_write(ch, (n < SFX_NOTES) ? v06_div_tab[n] : 0u);
    g_voice[ch].left = (s->ticks != 0u) ? s->ticks : 1u;
}

static void voice_stop(unsigned char ch)
{
    g_voice[ch].steps = 0;
    g_voice[ch].left = 0u;
    g_voice[ch].idx = 0u;
    vi53_set_channel(ch, 0u);
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

    for (i = 0u; i < SFX_VOICES; ++i) {
        g_voice[i].steps = 0;
        g_voice[i].left = 0u;
        g_voice[i].idx = 0u;
        g_voice[i].len = 0u;
        g_voice[i].prio = 0u;
        g_voice[i].div = 0u;
        vi53_set_channel(i, 0u);
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
            /* знаковое смещение делителя; 0 — это «тишина», пропускаем */
            d = g_voice[i].div + (unsigned int)(int)s->detune;
            if (d == 0u || (s->detune < 0 && d > g_voice[i].div))
                d = 1u;              /* свип вверх дошёл до границы частот   */
            else if (s->detune > 0 && d < g_voice[i].div)
                d = 65535u;          /* свип вниз переполнил 16 бит         */
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
