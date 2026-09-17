/*
 * vi53.c — низкоуровневый API КР580ВИ53 (аналог i8253), Вектор-06Ц.
 *
 * Тактовая 1.5 МГц; карта портов:
 *   - управляющее слово:                   0x08
 *   - канал 0 (звуковой канал 1):          0x0B
 *   - канал 1 (звуковой канал 2):          0x0A
 *   - канал 2 (звуковой канал 3):          0x09
 *   - режим 3 (квадрат): частота = 1500000 / делитель (в режиме 3
 *     счётчик уменьшается на 2 за такт, поэтому множителя 2 нет).
 * Маппинг портов подтверждён двумя независимыми источниками: исходниками
 * эмулятора (vio.h: addr = ~port & 3) и рабочей игрой OldTower.
 *
 * Это единственный владелец записи в порты ВИ53: music.c и sound.c
 * не должны содержать собственных реализаций (ТЗ §16).
 *
 * Прямые записи портов — инлайн-asm тем же приёмом, что и ay_write() в
 * ay.c: байт передаётся через volatile-переменную, OUT — 8080-инструкция
 * out (n),a с НЕМЕДЛЕННЫМ адресом порта (без самомодификации байта порта,
 * как в v06_out из v06io.asm). БЕЗ di/ei: эти функции вызываются из
 * кадрового ISR, где прерывания уже замаскированы (8080 сам сбрасывает
 * IFF, а isr_frame делает ei только перед ret), а лишний ei разрешил бы
 * их посреди ISR → повторный вход в прерывание → рекурсия → переполнение
 * стека. Каждый out (n),a атомарен сам по себе.
 *
 * Два варианта установки канала сохраняют РАЗНОЕ существующее
 * поведение выключения (ТЗ §22 — не менять аппаратные протоколы):
 *   vi53_set_channel()    — режим 3, делитель 0 = только управляющее
 *                           слово, счётчик НЕ загружается (способ music.c:
 *                           без треска после остановки);
 *   vi53_set_channel_m0() — режим 3, делитель 0 = режим 0 (OUT=0) +
 *                           два нулевых байта (способ sound.c).
 */

#include "v06.h"

/* Байт для записи в порт. Как и в ay.c, значение передаётся в asm через
 * volatile-переменную; out (n),a с немедленным адресом — без di/ei (см.
 * шапку: функции вызываются из ISR, где прерывания уже замаскированы).
 * Каждый порт имеет свой немедленный адрес, поэтому четыре отдельных
 * helper'а (аналог четырёх PUBLIC-функций прежнего vi53out.asm). */
static volatile unsigned char vi53_v_;

static void vi53_out_ctrl(unsigned char v)   /* 0x08 — управляющее слово */
{
    vi53_v_ = v;
#asm
    ld  a, (_vi53_v_)
    out (0x08), a
#endasm
}

static void vi53_out_ch0(unsigned char v)    /* 0x0B — данные канала 0 */
{
    vi53_v_ = v;
#asm
    ld  a, (_vi53_v_)
    out (0x0B), a
#endasm
}

static void vi53_out_ch1(unsigned char v)    /* 0x0A — данные канала 1 */
{
    vi53_v_ = v;
#asm
    ld  a, (_vi53_v_)
    out (0x0A), a
#endasm
}

static void vi53_out_ch2(unsigned char v)    /* 0x09 — данные канала 2 */
{
    vi53_v_ = v;
#asm
    ld  a, (_vi53_v_)
    out (0x09), a
#endasm
}

/* Режим 3, чтение/запись 2 байта: каналы 0/1/2. */
static const unsigned char vi53_m3[3] = { 0x36, 0x76, 0xB6 };
/* Режим 0 (OUT = 0, тишина): каналы 0/1/2. */
static const unsigned char vi53_m0[3] = { 0x30, 0x70, 0xB0 };

/* Запись одного байта в порт данных канала. */
static void vi53_data(unsigned char channel, unsigned char v)
{
    if (channel == 0u)
        vi53_out_ch0(v);
    else if (channel == 1u)
        vi53_out_ch1(v);
    else
        vi53_out_ch2(v);
}

/* Установка делителя канала (способ music.c): 0 = выключить — только
 * управляющее слово режима 3, счётчик не загружается (VECTOR.MD
 * §5.5.7). Проверено на слух: без загрузки счётчика эмуляция молчит
 * чисто, тогда как режим 0 со счётом 0 даёт треск после остановки. */
void vi53_set_channel(unsigned char channel, unsigned int divisor)
{
    vi53_out_ctrl(vi53_m3[channel]);
    if (divisor == 0u)
        return;
    vi53_data(channel, (unsigned char)(divisor & 0xFFu));
    vi53_data(channel, (unsigned char)(divisor >> 8));
}

/* Установка делителя канала (способ sound.c): тон — режим 3, а
 * 0 = выключить — режим 0 (OUT=0) + два нулевых байта. Сохраняет
 * существующее поведение шагового плеера sound.c без изменений. */
void vi53_set_channel_m0(unsigned char channel, unsigned int divisor)
{
    if (divisor == 0u) {
        vi53_out_ctrl(vi53_m0[channel]);
        vi53_data(channel, 0x00);
        vi53_data(channel, 0x00);
        return;
    }
    vi53_out_ctrl(vi53_m3[channel]);
    vi53_data(channel, (unsigned char)(divisor & 0xFFu));
    vi53_data(channel, (unsigned char)(divisor >> 8));
}
