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
 * Плеер: данные sound_step_t задаются sound_set_data(); sound_tick()
 * вызывается из кадрового прерывания (startup.asm, 50 Гц) и потребляет
 * g_tempo_num/g_tempo_den тика за кадр (аккумулятор Брешихэма):
 * 1/1 = один тик на кадр. Темп меняется через sound_set_tempo().
 * Символы sound_* не конфликтуют с партитурным плеером music.c
 * (music_*) — в одном ROM допустимо линковать оба.
 * Поле noise шага — ударные на канале шума AY-3-8910 (drums.asm):
 * 1 = снейр/том, 2 = бочка. Триггер вызывается один раз на входе в
 * шаг; огибающую ведёт drum_tick() из того же прерывания. ВИ53 при
 * этом не трогается — все три тональных канала остаются мелодии,
 * бас на канале 2 звучит непрерывно.
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

static const sound_step_t *g_steps;     /* таблица мелодии              */
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

void sound_set_data(const sound_step_t *steps, unsigned int len)
{
    g_steps = steps;
    g_len = len;
}

/* Темп = num/den тика на кадровое прерывание (1/1 — номинал 50 Гц).
 * num > den — быстрее, num < den — медленнее. */
void sound_set_tempo(unsigned char num, unsigned char den)
{
    if (num != 0u && den != 0u) {
        g_tempo_num = num;
        g_tempo_den = den;
    }
}

void sound_set_loop(unsigned char loop)
{
    g_loop = loop;
}

void sound_start(void)
{
    g_pos = 0u;
    g_left = 0u;
    g_tempo_acc = 0u;
    g_playing = 1u;
}

void sound_stop(void)
{
    g_playing = 0u;
    vi53_set_channel(0, 0);
    vi53_set_channel(1, 0);
    vi53_set_channel(2, 0);
    g_cur1 = g_cur2 = g_cur3 = 0u;
    drum_mute();
}

unsigned char sound_is_playing(void)
{
    return g_playing;
}

static void sound_advance(void);

/* Вызов из кадрового прерывания: потребляет num/den тика плеера */
void sound_tick(void)
{
    unsigned char n;

    if (!g_playing)
        return;

    g_tempo_acc += g_tempo_num;
    n = (unsigned char)(g_tempo_acc / g_tempo_den);
    g_tempo_acc %= g_tempo_den;
    while (n-- > 0u)
        sound_advance();
}

/* Продвижение на один тик плеера */
static void sound_advance(void)
{
    const sound_step_t *s;

    if (g_left == 0u) {
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
        if (s->ch3 != g_cur3) {
            g_cur3 = s->ch3;
            vi53_set_channel(2, g_cur3);
        }
        /* ударные — на канал шума AY-3-8910 (drums.asm), один
         * триггер на вход в шаг; ВИ53 не трогается */
        if (s->noise == 1u)
            drum_snare();
        else if (s->noise == 2u)
            drum_kick();

        g_left = s->duration;
        ++g_pos;
    }
    --g_left;
}

/* Полная остановка звука (включая незавершённый шум) */
void sound_silence(void)
{
    sound_stop();
}
