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
extern unsigned char gfx_active_planes;  /* маска активных плоскостей текущего режима */

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

/* Плоскость сегментов (0xE000, вес 1). Реализация — lib/gfx/plane.asm.
   Фон занимает только чётные индексы палитры, поэтому бит 0 плоскости веса 1
   в фоне сброшен везде: OR выставляет сегмент, AND-NOT тем же массивом
   стирает его, возвращая ровно биты фона. Один массив данных служит и для
   рисования, и для стирания. Плоскость веса 1 должна быть активна
   (GFX_MODE_256_16 или GFX_MODE_256_2).

   Формат массива: [0] x0 (кратен 8), [1] y0, [2] wb (ширина в байтах),
   [3] h (строк), далее wb*h байт маски колонками сверху вниз.
   Требования: x0 кратно 8, y0 + h <= 256, x0 + wb*8 <= 256. */
extern void gfx_plane_or(const unsigned char *src);
extern void gfx_plane_andn(const unsigned char *src);


/* ----------------------------- Шрифты ------------------------------ */

/* Дескриптор шрифта. Все четыре поля читают pr.asm, pr512.asm и
 * pr512t.asm; режим задаётся полем chars.
 *
 * chars != 0 — таблица имён: chars перечисляет символы в том же
 * порядке, что глифы в glyphs, и заканчивается нулём; индекс глифа =
 * позиция символа в таблице, неизвестный символ рисуется глифом 0.
 * Годится для разреженных наборов (у PUTUP две разорванные группы
 * кодов) и стоит 1 байт индекса на символ.
 *
 * chars == 0 — прямой индекс по коду символа: глиф лежит по адресу
 * glyphs + (код - first_code) * шаг. Шаг известен из формата шрифта
 * (8 байт в pr.asm и pr512t.asm, 16 в pr512.asm) и в дескрипторе не
 * хранится. Коды вне [first_code..last_code] пропускаются: клетка
 * остаётся нетронутой, ничего не затирается. Индекс — два сравнения
 * вместо обхода таблицы, поэтому для плотных наборов (цифры,
 * латиница целиком) этот режим и компактнее, и быстрее.
 *
 * first_code <= last_code, в слове значим младший байт. */
typedef struct {
    const char *chars;            /* таблица имён, 0 = прямой индекс */
    const unsigned char *glyphs;  /* данные глифов                   */
    unsigned int first_code;      /* прямой индекс: первый код        */
    unsigned int last_code;       /* прямой индекс: последний код     */
} gfx_font_t;

/* Шрифты, собранные в ROM (данные — lib/gfx/fonts/default_*.inc).
 * В asm эти дескрипторы лежат под метками _gfx_font_8x8,
 * _gfx_font_16x8 и _gfx_font_thin. */
extern const gfx_font_t gfx_font_8x8;    /* 8x8   pr.asm     */
extern const gfx_font_t gfx_font_16x8;   /* 16x8  pr512.asm  */
extern const gfx_font_t gfx_font_thin;   /* 4x8   pr512t.asm */

/* Поставить текущий шрифт; действует на весь последующий вывод,
 * менять можно хоть между символами одной строки. 0 возвращает шрифт,
 * собранный в ROM. Пример своего шрифта (дескриптор + asm-модуль) —
 * roms/tests/fonts/putup_font.asm; шрифт, подменяемый на сборке, —
 * lib/gfx/fonts/default_8x8.inc. */
extern void gfx_select_font(const gfx_font_t *font) __z88dk_callee;
extern void gfx_select_font_512(const gfx_font_t *font) __z88dk_callee;
extern void gfx_select_font_512t(const gfx_font_t *font) __z88dk_callee;



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

/* Распаковщик ZX0 «standard» (lib/unpack/zx0.asm). src — сжатый поток,
 * dst — буфер размером не меньше исходных данных; длину результата
 * декодер не знает (конец — маркер EOF в потоке), её хранит вызывающий.
 * Пишет в dst линейно по возрастанию адреса, области не должны
 * пересекаться и src должен лежать ниже dst.
 * Стандартное соглашение: стек чистит вызывающий. */
extern void zx0_decompress(const unsigned char *src, unsigned char *dst);



/* ----------------------------------------------------------------------- */
/*                                  MEM                                    */
/* ----------------------------------------------------------------------- */

/* Bump-аллокатор свободной ОЗУ (mem/heap.c). Куча начинается от конца
 * образа ROM (символ линкера __tail, в него попадает и BSS) и растёт
 * вверх; освобождения нет. Статический буфер в BSS стоит образу ROM
 * ровно столько байт, сколько весит в памяти, — куча вместо него не
 * стоит ничего. */
#define HEAP_TOP_DEFAULT  0x8000

/* Потолок кучи. По умолчанию 0x8000 — куча не заходит в видеопамять,
 * и этого значения достаточно всем режимам, где активны плоскости
 * 0x8000..0xFFFF.
 * Поднимать потолок можно только проекту, который гарантированно не
 * трогает верхние плоскости: в GFX_MODE_256_2 отображается и заливается
 * одна плоскость 0xE000, значит 0x8000..0xDFFF — обычная ОЗУ. Присвой
 * heap_top до первой выдачи, иначе уже выделенное окажется под
 * содержимым экрана.
 * Опускать потолок ниже вершины кучи поздно, но и не поднимать его,
 * когда образ перелез через 0x8000, тоже нельзя: выдача тогда просто
 * вернёт 0 — возвращённое значение всегда проверяй.
 *
 * Сам образ ROM может дорасти только до 0xBFFF: начальный загрузчик
 * во время загрузки рисует свою таблицу в плоскости 0xC000, так что
 * 0xC000..0xDFFF доступны только уже запущенной программе, то есть
 * куче. */
extern unsigned int heap_top;

extern void *heap_alloc(unsigned int size);   /* 0 — не хватило места  */
extern unsigned int heap_avail(void);         /* свободных байт в куче */



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
#define MUS_VOL_BASE    0xF0    /* 0xF1..0xFF: V1..V15 громкость канала, */
                                /* вся команда — 1 байт (байт = 0xF0 + V, */
                                /* громкость = байт & 0x0F); AY R8/R9/R10  */
                                /* на атаке; ВИ53 — игнор                 */

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

/* Сжатая песня (MUSIC_COMPRESSED): четыре потока байткода (s0|s1|s2|dr)
 * лежат в ROM одним ZX0-блобом и распаковываются в ОЗУ перед игрой.
 * music_load_compressed() распаковывает blob в буфер и собирает из него
 * обычную music_song_t, потоки которой указывают внутрь буфера:
 *   s0 = buf, s1 = buf+stream_len[0], s2 = +stream_len[1], dr = +stream_len[2].
 * Байткод позиционно-независим (MUS_JMP — относительный прыжок назад),
 * поэтому распакованные потоки играются напрямую, без правки адресов.
 * Семплы ударных остаются в ROM (samples) — dr лишь ссылается на них. */
typedef struct {
    unsigned int tempo_num;
    unsigned int tempo_den;
    unsigned int  length;              /* длина в тиках (справочно)      */
    unsigned int  unpack_size;         /* байт после распаковки (s0+..+dr)*/
    const unsigned int *stream_len;    /* [4]: длины s0,s1,s2,dr несжатые */
    const unsigned char *blob;         /* ZX0-поток (без заголовка)       */
    const unsigned char * const *samples;
} music_csong_t;

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

/* Распаковать сжатую песню в буфер и вернуть готовую music_song_t
 * (RAM-копия внутри music.c). buf должен вмещать cs->unpack_size байт;
 * обычно его берут из кучи (heap_alloc) — она стартует сразу за концом
 * образа ROM (__tail). Одновременно играет одна песня, поэтому буфер
 * переиспользуют: выделяют один раз под самый длинный трек. Результат
 * передают в music_set_data()/play_song(). */
extern const music_song_t *music_load_compressed(const music_csong_t *cs,
                                                 unsigned char *buf);

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

/* - - - - - - - - - SFX: 3-голосный смеситель эффектов - - - - - - - - - - - */

/* lib/snd/sfx.c: короткий сигнал на одном канале ВИ53, несколько сигналов
 * могут звучать одновременно (по числу каналов). Только тональные каналы:
 * шума здесь нет (он один на всех в drums.asm), эффекты вида «разбилось»
 * делаются гудком с падением — detune по кадрам. */
typedef struct {
    unsigned char note;         /* абсолютный номер ноты 0..94 (0 = тишина),
                                   см. v06_div_tab и макросы N_<нота>(<окт.>)  */
    signed char   detune;       /* прибавка к ДЕЛИТЕЛЮ каждый кадр (свип),
                                   только -128..127: 127 = ~полтона на ноте
                                   средней октавы; положительный = вниз     */
    unsigned char ticks;        /* кадров 50 Гц на этот шаг (0 = 1)            */
} sfx_step_t;

typedef struct {
    const sfx_step_t *steps;    /* последовательность шагов                    */
    unsigned char len;          /* их число                                  */
    unsigned char prio;         /* 0..255: выше — вытесняет занятой канал     */
} sfx_t;

extern void sfx_init(void);                      /* тишина, сброс голосов     */
extern unsigned char sfx_play(const sfx_t *fx);   /* 1 — запущен, 0 — нечего   */
extern void sfx_stop_all(void);                  /* заглушить все голоса      */
extern unsigned char sfx_busy(void);             /* есть звучащий эффект      */
extern void sfx_tick(void);                       /* из main loop, 50 Гц       */



/* ----------------------------------------------------------------------- */
/*                                  KBD                                    */
/* ----------------------------------------------------------------------- */

extern unsigned char kbd_scan(void);            /* опрос матрицы         */
extern void kbd_scan_now(void);                 /* снимок в ISR          */
extern unsigned char kbd_read(void);            /* декод. последний снимок*/
extern void kbd_wait_key(unsigned char key);    /* ждать нажатия         */

/* Снимок матрицы после kbd_scan()/kbd_scan_now(): 8 байт, строки, бит 1 =
 * клавиша нажата (колонка = номер бита). kbd_scan()/kbd_read() отдают только
 * ПЕРВУЮ нажатую клавишу, а игре нужно следить за несколькими
 * одновременно: тогда читаем kbd_rows[] и снимаем фронты сами. */
extern unsigned char kbd_rows[8];

/* Коды служебных и специальных клавиш, возвращаемые kbd_scan()/kbd_read().
 * Числовые значения соответствуют матричной таблице kbd_codes в
 * lib/kbd/keyboard.c (строка*8 + колонка). */
#define KBD_KEY_TAB    7    /* ТАБ — переключение фокуса (СС+ТАБ — назад) */
#define KBD_KEY_LEFT   8    /* ← */
#define KBD_KEY_RIGHT  9    /* → */
#define KBD_KEY_DOWN   10   /* ↓ */
#define KBD_KEY_UP     11   /* ↑ */
#define KBD_KEY_BACK   12   /* ЗАБ (backspace) */
#define KBD_KEY_ESC    27   /* АП2 (ESC) — возврат, выход из цикла   */
#define KBD_KEY_F1     128  /* Ф1 */
#define KBD_KEY_F2     129  /* Ф2 */
#define KBD_KEY_F3     130  /* Ф3 */
#define KBD_KEY_F4     131  /* Ф4 */
#define KBD_KEY_F5     132  /* Ф5 */
/* ↖ и СТР — строка 1 матрицы (колонки 0 и 1); z88dk оставил их без кода,
 * поэтому назначаем свои выше ASCII и Ф1-Ф5 (коллизий нет). */
#define KBD_KEY_HOME   133  /* «влево-вверх» (↖) — курсор в начало строки */
#define KBD_KEY_END    134  /* «СТР» — курсор в конец строки             */

/* Печатные символы матрицы: коды лежат в ASCII-диапазоне, пробел (32)
 * первый, DEL (127) уже не печатный. */
#define KBD_IS_PRINT(c)  ((c) >= 32 && (c) < 127)



/* ----------------------------------------------------------------------- */
/*                                 COMPS                                   */
/* ----------------------------------------------------------------------- */

/* UI-компоненты (controller, edit, textarea) — см. comps/comps.h */



#endif /* V06_H */
