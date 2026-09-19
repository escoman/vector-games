/*
 * main.c — тестовый ROM гибкой генерации шума Tape Out (ТЗ §15/§16).
 *
 * Проверяет разделение drum engine / output route / scheduler для Tape Out
 * (PIA1 Port C bit 0, бипер) при СОХРАНЁННОМ разделении VI53/AY и
 * неизменённом LFSR (маска 0xB400). Маршрут AY-Noise (§13) не трогается.
 *
 *   drum_tape_step()     — один шаг LFSR + запись PC0 (дешёвый примитив);
 *   drum_tape_generate(n) — пакет из n шагов из main loop (муз. ROM);
 *   drum_tape_mode_frame()/drum_tape_mode_manual() — планировщик Tape Out;
 *   drum_tape_set_steps_per_tick(n) — число шагов за кадр в FRAME-режиме.
 *
 * Тесты (ТЗ §16):
 *   1 Test A  FRAME-режим: лента из interrupt (табличные барабаны);
 *   2 Test B  MANUAL, авто-генерация ОТКЛ — тишина (шагов нет);
 *   3 Test C  MANUAL + drum_tape_step() из main loop (tight loop);
 *   4 Test D  MANUAL + drum_tape_generate(n), n=50/100/200/400 (7/8/9/0);
 *   6         FRAME + drum_tape_set_steps_per_tick(n) — фикс. порог/кадр;
 *   5 Test F  маршрут AY-Noise: удар из interrupt (§13 не сломан);
 *   Test E    ввод (клавиатура) обрабатывается и при высокой нагрузке:
 *             в режимах 3/4 основной цикл генерирует шум пачками, а клавиши
 *             опрашиваются на границе кадра — отклик сохраняется;
 *   R         измерение: 1 секунда барабанного шума из interrupt (Test A/F
 *             на слух), затем 1 секунда ручного drum_tape_generate(400).
 *   ESC       выход.
 *
 * sound_tick()/drum_tick() ведутся из кадрового прерывания 50 Гц (frame_handler).
 * Точные steps/sec, PC0 writes/sec и CPU% снимаются отладчиком (вектор-debugger)
 * по IO-трассе порта 0x00 и T-состояниям; ROM дополнительно показывает свою
 * программную оценку steps/sec для режимов main loop.
 */


#include "v06.h"

static const unsigned char test_pal[16] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xFF, 0x24, 0x12, 0x03, 0x00, 0x00, 0x00, 0x00
};

/* Режимы основной петли. */
#define M_OFF         0u   /* меню, генерации нет                        */
#define M_FRAME       1u   /* Test A: лента из interrupt, табличные удары */
#define M_MANUAL_OFF  2u   /* Test B: MANUAL, шагов нет → тишина         */
#define M_STEP        3u   /* Test C: drum_tape_step() из main loop      */
#define M_BATCH       4u   /* Test D: drum_tape_generate(n) из main loop */
#define M_FRAME_N     6u   /* FRAME + фикс. порог шагов/кадр (§6)        */
#define M_AY          5u   /* Test F: маршрут AY-Noise из interrupt      */

static volatile unsigned long g_steps;    /* суммарно шагов Tape Out     */
static unsigned char mode = M_OFF;        /* текущий режим               */
static unsigned char route_ay;            /* 0 = Tape Out, 1 = AY (Test F)*/
static unsigned int  batch_n = 200u;      /* размер пакета для M_BATCH   */
static unsigned char steps_per_tick = 16u;/* порог для M_FRAME_N         */

/* ------------------------------ вывод --------------------------------- */

static void print_dec(unsigned char x, unsigned char y,
                      unsigned long v, unsigned char color)
{
    unsigned char buf[11];
    unsigned char i = 0u;
    unsigned char j;
    char ch;

    /* цифры кладём в обратном порядке: buf[0] = младший разряд */
    do {
        buf[i++] = (unsigned char)('0' + (unsigned char)(v % 10u));
        v /= 10u;
    } while (v != 0u);

    /* печатаем старший разряд первым: читаем buf с конца */
    for (j = 0u; j < i; ++j) {
        ch = (char)buf[i - 1u - j];
        gfx_put_char(x, y, ch, color);
        x = x+1;
    }
}

static void set_line(unsigned char y, const char *s)
{
    static char line[41];
    unsigned char i;

    /* сначала затираем всю строку пробелами, затем копируем в неё текст:
     * короткое сообщение перекрывает остатки предыдущей (более длинной) */
    for (i = 0u; i < 32u; ++i) line[i] = ' ';
    line[40] = '\0';

    for (i = 0u; i < 40u && s[i] != '\0'; ++i) line[i] = s[i];

    gfx_print(0u, y, line, 10u);
}

static void update_hud(void)
{
    unsigned long rate = g_steps;   /* показываем и накопленные шаги, и /сек */

    switch (mode) {
        case M_OFF:        set_line(96u,  "MODE: OFF (menu)"); break;
        case M_FRAME:      set_line(96u,  "MODE: A FRAME (interrupt)"); break;
        case M_MANUAL_OFF: set_line(96u,  "MODE: B MANUAL-OFF (silent)"); break;
        case M_STEP:       set_line(96u,  "MODE: C STEP (main loop)"); break;
        case M_BATCH:      set_line(96u,  "MODE: D GENERATE n (main loop)"); break;
        case M_FRAME_N:    set_line(96u,  "MODE: FRAME + steps/tick"); break;
        case M_AY:         set_line(96u,  "MODE: F AY NOISE (interrupt)"); break;
        default: break;
    }

    set_line(112u, route_ay ? "ROUTE: AY NOISE C" : "ROUTE: TAPE OUT (PC0)");

    gfx_print(0u, 128u, "STEPS TOTAL:", 8u);
    print_dec(13u, 128u, rate, 11u);
    gfx_print(0u, 144u, "STEPS /SEC  :", 8u);
    print_dec(13u, 144u, g_steps * 2u / 25u, 11u); /* обновление раз в 25 кадр*/
}

/* Кадровый обработчик: огибающие ударных (frame/AY-режимы). В MANUAL-ленте
 * drum_tick на Tape Out не трогает PC0 (ТЗ §7), но ведёт AY-шум. */
static void isr_audio(void)
{
    drum_tick();
}

static void apply_mode(void)
{
    /* Маршрут и планировщик раздельны (ТЗ §3). Tape-режимы — маршрут
     * лента; AY-режим — маршрут AY. FRAME/MANUAL — планировщик Tape. */
    if (mode == M_AY) {
        drum_route_ay();
        drum_tape_mode_frame();     /* планировщик ленты не важен для AY */
        route_ay = 1u;
    } else {
        drum_route_tape();
        route_ay = 0u;
        if (mode == M_FRAME || mode == M_FRAME_N)
            drum_tape_mode_frame();
        else
            drum_tape_mode_manual(); /* B/C/D: авто-генерация из interrupt off */
    }
    /* Порог шагов/кадр: только для FRAME-фикс режима, иначе авторежим. */
    drum_tape_set_steps_per_tick(mode == M_FRAME_N ? steps_per_tick : 0u);
    drum_init();
}

static void handle_key(unsigned char key)
{
    switch (key) {
        case '1': mode = M_FRAME;      apply_mode(); break;
        case '2': mode = M_MANUAL_OFF; apply_mode(); break;
        case '3': mode = M_STEP;       apply_mode(); break;
        case '4': mode = M_BATCH;      apply_mode(); break;
        case '5': mode = M_AY;         apply_mode(); break;
        case '6': mode = M_FRAME_N;    apply_mode(); break;
        case '7': batch_n = 50u;  if (mode != M_BATCH) { mode = M_BATCH; apply_mode(); } break;
        case '8': batch_n = 100u; if (mode != M_BATCH) { mode = M_BATCH; apply_mode(); } break;
        case '9': batch_n = 200u; if (mode != M_BATCH) { mode = M_BATCH; apply_mode(); } break;
        case '0': batch_n = 400u; if (mode != M_BATCH) { mode = M_BATCH; apply_mode(); } break;
        default: break;
    }
}

/* ------------------------------- main --------------------------------- */

int main(void)
{
    unsigned char key;
    unsigned char prev_key = 0;
    unsigned int  last_frame;
    unsigned int  stat_frame;
    unsigned int  trig_frame;
    unsigned long stat_steps;

    frame_handler = isr_audio;
    drum_tape_mode_frame();         /* планировщик по умолчанию (ТЗ §12)  */
    drum_route_tape();              /* маршрут по умолчанию — Tape Out    */
    drum_init();
    ay_mixer_init();                /* R7 = 0xF8 (Test F: AY-шум)          */

    gfx_set_black_palette();
    gfx_clear(0);
    gfx_print(0u, 8u,  "TAPE OUT GEN TEST", 8u);
    gfx_print(0u, 32u, "1-FRAME   2-OFF    3-STEP", 8u);
    gfx_print(0u, 48u, "4-GEN     5-AY     6-FRAME+N", 8u);
    gfx_print(0u, 64u, "7,8,9,0   N=50,100,200,400", 8u);
    gfx_print(0u, 80u, "R MEASURE", 8u);
    update_hud();
    gfx_set_palette(test_pal);

    last_frame = stat_frame = trig_frame = frame_count;
    stat_steps = 0u;

    for (;;) {
        /* Генерация Tape Out согласно режиму. В M_STEP/M_BATCH основной
         * цикл расходует заметную долю CPU на шум (ТЗ §8); клавиатура всё
         * равно опрашивается раз в кадр (Test E). */
        if (mode == M_STEP) {
            drum_tape_step();
            ++g_steps;
        } else if (mode == M_BATCH) {
            drum_tape_generate(batch_n);
            g_steps += batch_n;
        }

        if (frame_count == last_frame) {
            if (mode == M_STEP)
                continue;           /* плотный tight-loop drum_tape_step   */
            /* M_BATCH: дать кадру пройти, но и так вернёмся в generate. */
        }
        last_frame = frame_count;

        /* --- раз в кадр: ввод + триггеры + статистика --- */
        key = kbd_scan();
        if (key != prev_key) {
            if (key == 'r' || key == 'R') {
                /* грубая проверка: 1 с FRAME-шума, затем 1 с generate(400) */
                mode = M_FRAME; apply_mode();
                trig_frame = frame_count;
                while (frame_count - trig_frame < 50u)
                    drum_kick();
                mode = M_BATCH; batch_n = 400u; apply_mode();
                trig_frame = frame_count;
                while (frame_count - trig_frame < 50u)
                    drum_tape_generate(400u);
                mode = M_OFF; apply_mode();
            } else {
                handle_key(key);
            }
        }
        prev_key = key;

        /* периодический табличный удар для FRAME/AY-режимов (слышимость) */
        if (mode == M_FRAME || mode == M_AY || mode == M_FRAME_N) {
            if (frame_count - trig_frame >= 8u) {
                trig_frame = frame_count;
                drum_snare();
            }
        }

        /* обновление оценки steps/sec раз в 25 кадров (~0.5 с) */
        if (frame_count - stat_frame >= 25u) {
            stat_frame = frame_count;
            stat_steps = g_steps;
            update_hud();
        }
    }

    return 0;
}
