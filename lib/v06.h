/*
 * v06.h — Vector-06C library (vector-games/lib).
 *
 * See lib/README.md for detailed documentation.
 */

#ifndef V06_H
#define V06_H


/* ----------------------------------------------------------------------- */
/*                                 COMMON                                  */
/* ----------------------------------------------------------------------- */

/* ПИА (КР580ВВ55) */
#define V06_PIA_CW      0x00    /* управляющее слово                       */
#define V06_PIA_PC      0x01    /* порт C: модификаторы, Tape Out         */
#define V06_PIA_PB      0x02    /* порт B: бордюр/режим                   */
#define V06_PIA_PA      0x03    /* порт A: регистр строки / клавиатура    */

/* КР580ВИ53 */
#define V06_VI53_CTRL   0x08    /* управляющее слово                       */
#define V06_VI53_CH2    0x09    /* канал 2                                 */
#define V06_VI53_CH1    0x0A    /* канал 1                                 */
#define V06_VI53_CH0    0x0B    /* канал 0                                 */

/* Палитра */
#define V06_PALETTE     0x0C    /* запись байта палитры                   */
#define V06_RGB(r, g, b) (((b) << 6) | ((g) << 3) | (r))  /* RRRGGGBB    */

/* AY-3-8910 */
#define V06_AY_SEL      0x15    /* выбор регистра (нечётный)              */
#define V06_AY_DAT      0x14    /* запись данных (чётный)                 */

/* Управляющие слова ПИА */
#define V06_CW_NORMAL   0x88    /* PA вход, PB выход                      */
#define V06_CW_KEYSCAN  0x8A    /* чтение клавиатуры через порт B         */

/* Видеопамять */
#define V06_VRAM        ((unsigned char *)0x8000)



/* ----------------------------------------------------------------------- */
/*                                  SYS                                    */
/* ----------------------------------------------------------------------- */

extern void v06_out(unsigned char port, unsigned char val);
extern unsigned char v06_in(unsigned char port);

/* Лёгкий сон до ближайшего прерывания (кадрового, 50 Гц). asm("halt")
 * sccz80 встраивает в код без вызова функции — тот же opcode, что и
 * у брошенного intrinsic_halt() из <intrinsic.h>. */
#define HALT()  asm("halt")

extern volatile unsigned int frame_count;       /* счётчик кадров 50 Гц  */
extern volatile unsigned char irq_active;       /* 1 = в обработчике ПР  */
extern void (*frame_handler)(void);             /* функц. из ISR, 0=нет  */

/* Ждать начала следующего кадра (сон HALT до изменения frame_count).
 * Реализация — в startup.asm, атомарные di/ei-чтения счётчика. */
extern void v06_wait_frame(void);



/* ----------------------------------------------------------------------- */
/*                                  GFX                                    */
/* ----------------------------------------------------------------------- */

/* Видеорежимы */
#define GFX_MODE_256_16  0   /* 256x256, 16 цв.                          */
#define GFX_MODE_256_2   1   /* 256x256, 2 цв., пл. 0xE000              */
#define GFX_MODE_512_4   2   /* 512x256, 4 цв.                           */
#define GFX_MODE_512_2   3   /* 512x256, 2 цв., 0xE000+0xA000           */

typedef struct {
    unsigned char width_div8;   /* 32 (256) или 64 (512)                 */
    unsigned char plane_mask;   /* маска активных плоскостей             */
    unsigned char num_colors;   /* 2, 4 или 16                           */
} gfx_mode_t;

extern const gfx_mode_t gfx_modes[];
extern unsigned char gfx_current_mode;

/* Режимы и очистка */
extern void gfx_set_mode(unsigned char mode);
extern void gfx_clear(unsigned char color);
extern void gfx_fill_planes(unsigned char mask, unsigned char fill) __z88dk_callee;
extern void gfx_fill_stride(unsigned int addr, unsigned char val,
                            unsigned int step, unsigned char count) __z88dk_callee;

/* Палитра */
extern void gfx_set_palette(const unsigned char *colors);
extern void gfx_set_bmp_palette(const unsigned char *pal);
extern void gfx_set_black_palette(void);

/* Скролл (отложенная запись в PIA PA) */
extern void gfx_set_scroll(unsigned char row);
extern unsigned char gfx_scroll_row;

/* Синхронизация кадров */
extern void gfx_next_frame(void);

/* Текст 8x8 (256x256) */
extern void gfx_put_char(unsigned char x, unsigned char y, char ch,
                         unsigned char color) __z88dk_callee;
extern void gfx_print(unsigned char x, unsigned char y, const char *s,
                      unsigned char color) __z88dk_callee;

/* Текст 16x8 (512x256) */
extern void gfx_put_char_512(unsigned char x, unsigned char y, char ch,
                             unsigned char color) __z88dk_callee;
extern void gfx_print_512(unsigned char x, unsigned char y, const char *s,
                          unsigned char color) __z88dk_callee;

/* Текст 4x8 тонкий (512x256) */
extern void gfx_print_512t(unsigned char x, unsigned char y, const char *s,
                           unsigned char color) __z88dk_callee;



/* ----------------------------------------------------------------------- */
/*                                UNPACK                                   */
/* ----------------------------------------------------------------------- */

/* RLE 256x256 (bmp2inc.py format) */
extern void gfx_rle_expand(const unsigned char *src, unsigned char x,
                           unsigned char y);

/* RLE 512x256 (bmp2inc512.py format) */
extern void gfx_rle_expand_512(const unsigned char *src);

/* LZ-тайловая распаковка (bmp2inc_lz.py format) */
extern void gfx_lz_expand(const unsigned char *src);



/* ----------------------------------------------------------------------- */
/*                                  SND                                    */
/* ----------------------------------------------------------------------- */

/* - - - - - - - - - - - - Ноты (notes.c) - - - - - - - - - - - - - - - - - */

/* Абсолютный номер ноты = октава*12 + полутон, 0..94 (то же, что в
 * байткоде music.c: 0x01..0x5F → 0..94). Мнемоники: N_<нота>(<октава>). */
#define N_C(n)    ((n)*12 + 0)
#define N_Cs(n)   ((n)*12 + 1)
#define N_Db(n)   N_Cs(n)
#define N_D(n)    ((n)*12 + 2)
#define N_Ds(n)   ((n)*12 + 3)
#define N_Eb(n)   N_Ds(n)
#define N_E(n)    ((n)*12 + 4)
#define N_F(n)    ((n)*12 + 5)
#define N_Fs(n)   ((n)*12 + 6)
#define N_Gb(n)   N_Fs(n)
#define N_G(n)    ((n)*12 + 7)
#define N_Gs(n)   ((n)*12 + 8)
#define N_Ab(n)   N_Gs(n)
#define N_A(n)    ((n)*12 + 9)   /* N_A(4) = 57 = 440 Гц */
#define N_As(n)   ((n)*12 + 10)
#define N_Bb(n)   N_As(n)
#define N_B(n)    ((n)*12 + 11)

/* Предвычисленные таблицы высот (lib/snd/notes.c). */
extern const unsigned int v06_div_tab[95];        /* ВИ53: 1500000/f   */
extern const unsigned int v06_ay_period_tab[95];  /* AY:   12 бит      */

/* Быстрый доступ к частотам нот — только индексация массива, без
 * 32-битного умножения/деления. В static-инициализаторах массивов
 * не используются (SDCC требует compile-time константу). */
#define DIV_OF(note)   (v06_div_tab[(note)])
#define AY_PER(note)   (v06_ay_period_tab[(note)])

/* - - - - - - - - - - - - KR580VI53 (vi53.c) - - - - - - - - - - - - - - */

extern void vi53_set_channel(unsigned char channel, unsigned int divisor);
extern void vi53_set_channel_m0(unsigned char channel, unsigned int divisor);

/* - - - - - - - - - - - - AY-3-8910 (ay.c) - - - - - - - - - - - - - - - */

/* Маски каналов */
#define AY_CH_A   0x01    /* канал A (R8)                                */
#define AY_CH_B   0x02    /* канал B (R9)                                */
#define AY_CH_C   0x04    /* канал C (R10); общий с drums                 */

/* Формы огибающей R13 */
#define AY_ENV_0    0x00  /* \_____  спад → удержание 0                  */
#define AY_ENV_1    0x01  /* \_____  то же что AY_ENV_0                  */
#define AY_ENV_2    0x02  /* \_____  то же что AY_ENV_0                  */
#define AY_ENV_3    0x03  /* \_____  то же что AY_ENV_0                  */
#define AY_ENV_4    0x04  /* /^^^^^  рост → удержание макс.              */
#define AY_ENV_5    0x05  /* /^^^^^  то же что AY_ENV_4                  */
#define AY_ENV_6    0x06  /* /^^^^^  то же что AY_ENV_4                  */
#define AY_ENV_7    0x07  /* /^^^^^  то же что AY_ENV_4                  */
#define AY_ENV_8    0x08  /* \\\\    repeating saw-down                  */
#define AY_ENV_9    0x09  /* \_____  спад → удержание 0                  */
#define AY_ENV_10   0x0A  /* \/\/\/  triangle, старт со спада           */
#define AY_ENV_11   0x0B  /* \_____  спад → удержание 0                  */
#define AY_ENV_12   0x0C  /* //////  repeating saw-up                    */
#define AY_ENV_13   0x0D  /* /^^^^^  рост → удержание 15                 */
#define AY_ENV_14   0x0E  /* /\/\/\  triangle, старт с роста             */
#define AY_ENV_15   0x0F  /* /^^^^^  рост → удержание 15                 */

/* Алиасы огибающих */
#define AY_ENV_DECAY          AY_ENV_0
#define AY_ENV_HOLD_LOW       AY_ENV_0
#define AY_ENV_ATTACK         AY_ENV_4
#define AY_ENV_HOLD_HIGH      AY_ENV_4
#define AY_ENV_TRIANGLE       AY_ENV_14
#define AY_ENV_TRIANGLE_DOWN  AY_ENV_10

/* Запись регистров и инициализация */
extern void ay_write(unsigned char reg, unsigned char val);
extern void ay_set_r7(unsigned char val);
extern void ay_mixer_init(void);

/* Тональные каналы */
extern void ay_set_tone_period(unsigned char ch, unsigned int period);
extern void ay_note_off(unsigned char ch);
extern void ay_mute_all(void);

/* Огибающая и громкость */
extern void ay_set_envelope(unsigned char chan_mask,
                            unsigned char shape, unsigned int period);
extern void ay_set_fixed_volume(unsigned char chan_mask,
                                unsigned char volume);

/* - - - - - - - - - - Плееры мелодий - - - - - - - - - - - - - - - - - - */

/* sound.c: шаговая мелодия */
typedef struct {
    unsigned char duration;     /* тики 50 Гц                             */
    unsigned int  ch1;          /* делитель ВИ53 (0=тишина)              */
    unsigned int  ch2;
    unsigned int  ch3;
    unsigned char noise;        /* 0=нет, 1=снейр/том, 2=бочка          */
} sound_step_t;

extern void sound_init(void);
extern void sound_silence(void);

#ifdef MUSIC_ONLY

/* music.c: партитурный синтезатор (bytecode from mus2inc.py) */
#define MUS_END         0x00
#define MUS_REST        0x60
#define MUS_LEN         0xE0    /* ..0xE7                                */
#define MUS_LPSTART     0xE8    /* «[»                                   */
#define MUS_LPEND       0xE9    /* «]n»                                  */
#define MUS_JMP         0xEA    /* <lo> <hi>                             */

typedef struct {
    unsigned int tempo_num;
    unsigned int tempo_den;
    unsigned int  length;
    const unsigned char *s0;
    const unsigned char *s1;
    const unsigned char *s2;
    const unsigned char *dr;
    const unsigned char * const *samples;
} music_song_t;

extern void music_set_data(const music_song_t *song);
extern void music_start(void);
extern void music_pause(void);
extern void music_resume(void);
extern void music_stop(void);
extern unsigned char music_is_playing(void);
extern void music_set_loop(unsigned char loop);
extern void music_set_channel_mask(unsigned char mask);
extern void music_tick(void);

/* Привязка устройства вывода */
extern void music_start_vi53(void);
extern void music_start_ay(void);
extern void music_use_vi53(void);
extern void music_use_ay(void);

/* Диагностика */
extern volatile unsigned long diag_irq_count;
extern volatile unsigned long diag_music_tick_count;
extern volatile unsigned long diag_score0_steps;
extern volatile unsigned long diag_drums_steps;
extern volatile unsigned long diag_music_time;
extern volatile unsigned long diag_score0_time;
extern volatile unsigned long diag_drums_time;
extern volatile unsigned long diag_score0_finish_irq;
extern volatile unsigned long diag_drums_finish_irq;
extern volatile unsigned long diag_score0_finish_time;
extern volatile unsigned long diag_drums_finish_time;
extern volatile unsigned long diag_score0_finish_steps;
extern volatile unsigned long diag_drums_finish_steps;
extern volatile unsigned char diag_score0_finished;
extern volatile unsigned char diag_drums_finished;
extern void diag_reset(void);

#else /* обычная сборка: плеер sound.c */

extern void sound_set_data(const sound_step_t *steps, unsigned int len);
extern void sound_set_tempo(unsigned char num, unsigned char den);
extern void sound_set_loop(unsigned char loop);
extern void sound_start(void);
extern void sound_stop(void);
extern unsigned char sound_is_playing(void);
extern void sound_tick(void);

#endif /* MUSIC_ONLY */

/* - - - - - - - - Drums: routing & control - - - - - - - - - - - - - - - */

extern void drum_route_tape(void);      /* шум на Tape Out (PC0)         */
extern void drum_route_ay(void);        /* шум на AY Noise C             */
extern void drum_init(void);            /* микшер и тишина               */
extern void drum_tick(void);            /* раз в кадр, 50 Гц            */
extern void drum_mute(void);            /* оборвать звучащий удар        */

/* - - - - - - - - Drums: sound triggers - - - - - - - - - - - - - - - - - */

extern void drum_kick(void);
extern void drum_snare(void);
extern void drum_hat_c(void);           /* закрытый хэт                  */
extern void drum_hat_o(void);           /* открытый хэт                  */
extern void drum_tom(void);
extern void drum_clap(void);
extern void drum_rim(void);

/* - - - - - - - - Drums: samples - - - - - - - - - - - - - - - - - - - - */

extern void drum_sample_play(const unsigned char *smp);

/* - - - - - - - - Drums: Tape Out LFSR engine - - - - - - - - - - - - - */

extern void drum_tape_step(void);                       /* 1 шаг LFSR    */
extern void drum_tape_generate(unsigned int count);     /* пакет шагов   */
extern void drum_tape_mode_frame(void);                 /* из interrupt  */
extern void drum_tape_mode_manual(void);                /* вручную       */
extern void drum_tape_mode_manual_env(void);            /* вручную+огиб. */
extern unsigned char drum_tape_running(void);           /* гейт кадра    */
extern void drum_tape_set_steps_per_tick(unsigned int n);



/* ----------------------------------------------------------------------- */
/*                                  KBD                                    */
/* ----------------------------------------------------------------------- */

extern unsigned char kbd_scan(void);            /* опрос матрицы         */
extern void kbd_scan_now(void);                 /* снимок в ISR          */
extern unsigned char kbd_read(void);            /* декод. последний снимок*/
extern void kbd_wait_key(unsigned char key);    /* ждать нажатия         */



/* ----------------------------------------------------------------------- */
/*                                 COMPS                                   */
/* ----------------------------------------------------------------------- */

/* UI-компоненты (controller, edit, textarea) — см. comps/comps.h */



#endif /* V06_H */
