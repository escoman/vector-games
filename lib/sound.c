/*
 * sound.c — звук Вектора-06Ц: КР580ВИ53 и плеер шаговой мелодии.
 *
 * КР580ВИ53 (аналог i8253), тактовая 1.5 МГц:
 *   - порт управляющего слова:          0x08
 *   - порт канала 0 (звуковой канал 1): 0x0B
 *   - порт канала 1 (звуковой канал 2): 0x0A
 *   - порт канала 2 (звуковой канал 3): 0x09
 *   - режим 3 (квадрат): управляющие слова 0x36/0x76/0xB6;
 *     частота на выходе = 1500000 / делитель (в режиме 3 счётчик
 *     уменьшается на 2 за такт, поэтому множителя 2 в формуле нет);
 *   - «канал выключен»: режим 0 (OUT=0, тишина), управляющие 0x30/0x70/0xB0.
 *
 * Плеер: данные music_step_t задаются music_set_data(); music_tick()
 * вызывается из кадрового прерывания (startup.asm, 50 Гц) и потребляет
 * g_tempo_num/g_tempo_den тика за кадр (аккумулятор Брешихэма):
 * 1/1 = один тик на кадр. Темп меняется через music_set_tempo().
 * Поле noise шага — ударные (короткий всплеск в начале шага):
 * 1 = снейр/том (шумовой треск), 2 = бочка (низкий стук).
 */

#include "v06.h"

/* Прямые записи в порты ВИ53 (vi53out.asm): без самомодификации байта
 * порта и без di/ei, поэтому безопасны и в кадровом прерывании. */
extern void v06_vi53_ctrl(unsigned char v);
extern void v06_vi53_ch0(unsigned char v);
extern void v06_vi53_ch1(unsigned char v);
extern void v06_vi53_ch2(unsigned char v);

/* ------------------------------ ВИ53 ---------------------------------- */

/* Режим 3, чтение/запись 2 байта: каналы 0/1/2 */
static const unsigned char vi53_m3[3] = { 0x36, 0x76, 0xB6 };
/* Режим 0 (OUT = 0, тишина): каналы 0/1/2 */
static const unsigned char vi53_m0[3] = { 0x30, 0x70, 0xB0 };

/* Запись одного байта в порт данных канала */
static void vi53_data(unsigned char channel, unsigned char v)
{
    if (channel == 0u)
        v06_vi53_ch0(v);
    else if (channel == 1u)
        v06_vi53_ch1(v);
    else
        v06_vi53_ch2(v);
}

/* Установка делителя канала (0 = выключить, режим 0 -> тишина) */
static void vi53_set_channel(unsigned char channel, unsigned int divisor)
{
    if (divisor == 0u) {
        v06_vi53_ctrl(vi53_m0[channel]);
        vi53_data(channel, 0x00);
        vi53_data(channel, 0x00);
        return;
    }
    v06_vi53_ctrl(vi53_m3[channel]);
    vi53_data(channel, (unsigned char)(divisor & 0xFFu));
    vi53_data(channel, (unsigned char)(divisor >> 8));
}

void sound_init(void)
{
    vi53_set_channel(0, 0);
    vi53_set_channel(1, 0);
    vi53_set_channel(2, 0);
}

/* ------------------------------ Плеер --------------------------------- */

static const music_step_t *g_steps;     /* таблица мелодии              */
static unsigned int g_len;              /* её длина в шагах             */

static unsigned int g_pos;              /* текущий шаг мелодии          */
static unsigned char g_left;            /* тиков до конца текущего шага */
static unsigned char g_playing;
static unsigned char g_loop;            /* 1 — крутить мелодию по кругу */

/* Темп: тиков плеера на одно кадровое прерывание (num/den) */
static unsigned char g_tempo_num = 1u;
static unsigned char g_tempo_den = 1u;
static unsigned char g_tempo_acc;       /* остаток в аккумуляторе       */

/* делители, записанные в каналы в данный момент (0 = выключен) */
static unsigned int g_cur1, g_cur2, g_cur3;
static unsigned char g_ch2_busy;        /* канал 2 перехвачен ударом    */

/* простой ГПСЧ для программного шума */
static unsigned int g_lfsr = 0xACE1u;

static unsigned char noise_rand(void)
{
    /* бит 0 ^ бит 2 ^ бит 3 ^ бит 5 */
    unsigned int bit = (g_lfsr ^ (g_lfsr >> 2) ^ (g_lfsr >> 3) ^ (g_lfsr >> 5)) & 1u;
    g_lfsr = (g_lfsr >> 1) | (bit << 15);
    return (unsigned char)(g_lfsr & 0x7Fu);
}

/* Снейр/том: серия случайных делителей в слышимом диапазоне
 * (примерно 2.4–6 кГц) — широкополосный треск. Басовый канал на
 * время всплеска «перехватывается» шумом. */
static void play_snare(void)
{
    unsigned char i;
    unsigned int d;

    for (i = 0u; i < 6u; ++i) {
        d = 240u + (unsigned int)noise_rand() * 3u;
        v06_vi53_ctrl(0xB6);            /* режим 3, два байта, канал 2 */
        v06_vi53_ch2((unsigned char)(d & 0xFFu));
        v06_vi53_ch2((unsigned char)(d >> 8));
    }
}

/* Бочка: короткий низкий «стук» с падением тона по тикам всплеска. */
static void play_kick(void)
{
    static unsigned char kick_phase;
    unsigned int d;

    if (!g_ch2_busy)
        kick_phase = 0u;
    d = (kick_phase == 0u) ? 8000u : 16000u;   /* 187 Гц -> 94 Гц */
    kick_phase ^= 1u;
    v06_vi53_ctrl(0xB6);
    v06_vi53_ch2((unsigned char)(d & 0xFFu));
    v06_vi53_ch2((unsigned char)(d >> 8));
}

void music_set_data(const music_step_t *steps, unsigned int len)
{
    g_steps = steps;
    g_len = len;
}

/* Темп = num/den тика на кадровое прерывание (1/1 — номинал 50 Гц).
 * num > den — быстрее, num < den — медленнее. */
void music_set_tempo(unsigned char num, unsigned char den)
{
    if (num != 0u && den != 0u) {
        g_tempo_num = num;
        g_tempo_den = den;
    }
}

void music_set_loop(unsigned char loop)
{
    g_loop = loop;
}

void music_start(void)
{
    g_pos = 0u;
    g_left = 0u;
    g_lfsr = 0xACE1u;
    g_tempo_acc = 0u;
    g_playing = 1u;
}

void music_stop(void)
{
    g_playing = 0u;
    g_ch2_busy = 0u;
    vi53_set_channel(0, 0);
    vi53_set_channel(1, 0);
    vi53_set_channel(2, 0);
    g_cur1 = g_cur2 = g_cur3 = 0u;
}

unsigned char music_is_playing(void)
{
    return g_playing;
}

static void music_advance(void);

/* Вызов из кадрового прерывания: потребляет num/den тика плеера */
void music_tick(void)
{
    unsigned char n;

    if (!g_playing)
        return;

    g_tempo_acc += g_tempo_num;
    n = (unsigned char)(g_tempo_acc / g_tempo_den);
    g_tempo_acc %= g_tempo_den;
    while (n-- > 0u)
        music_advance();
}

/* Продвижение на один тик плеера */
static void music_advance(void)
{
    const music_step_t *s;

    if (g_left == 0u) {
        if (g_ch2_busy) {
            /* закончился шаг с ударом — вернуть бас (или тишину) */
            g_ch2_busy = 0u;
            vi53_set_channel(2, g_cur3);
        }
        if (g_pos >= g_len) {
            if (!g_loop) {
                /* мелодия отзвучала: тишина и остановка */
                g_playing = 0u;
                vi53_set_channel(0, 0);
                vi53_set_channel(1, 0);
                vi53_set_channel(2, 0);
                g_cur1 = g_cur2 = g_cur3 = 0u;
                return;
            }
            g_pos = 0u;
        }
        s = &g_steps[g_pos];

        if (s->ch1 != g_cur1) {
            g_cur1 = s->ch1;
            vi53_set_channel(0, g_cur1);
        }
        if (s->ch2 != g_cur2) {
            g_cur2 = s->ch2;
            vi53_set_channel(1, g_cur2);
        }
        if (s->noise == 0u) {
            if (s->ch3 != g_cur3) {
                g_cur3 = s->ch3;
                vi53_set_channel(2, g_cur3);
            }
        } else {
            g_cur3 = s->ch3;            /* бас запомнен, вернётся после */
            g_ch2_busy = 1u;
        }

        g_left = s->duration;
        ++g_pos;
    }
    --g_left;

    s = &g_steps[(g_pos == 0u) ? (g_len - 1u) : (g_pos - 1u)];
    if (s->noise == 1u)
        play_snare();
    else if (s->noise == 2u)
        play_kick();
}

/* Полная остановка звука (включая незавершённый шум) */
void sound_silence(void)
{
    music_stop();
}
