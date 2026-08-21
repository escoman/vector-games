/*
 * v06.h — общая библиотека Вектора-06Ц (vector-games/lib).
 *
 * Всё аппаратное взаимодействие — своими силами, без clib z88dk:
 *   v06io.asm  — запись/чтение портов 8080 (самоmodификация операнда);
 *   graph.c    — видеопамять, RLE-распаковка, палитра (v06pal.asm);
 *   sound.c    — КР580ВИ53 и плеер шаговой мелодии;
 *   keyboard.c — опрос клавиатурной матрицы портами (без прерываний).
 */

#ifndef V06_H
#define V06_H

/* ------------------------------- Порты -------------------------------- */

#define V06_PIA_CW      0x00    /* управляющее слово ПИА (КР580ВВ55)      */
#define V06_PIA_PC      0x01    /* порт C: модификаторы клавиатуры и пр.  */
#define V06_PIA_PB      0x02    /* порт B: биты 0-3 бордюр, бит 4 режим   */
#define V06_PIA_PA      0x03    /* порт A: регистр строки / строка кл-ры  */
#define V06_VI53_CTRL   0x08    /* ВИ53: управляющее слово                */
#define V06_VI53_CH2    0x09    /* ВИ53: канал 2                          */
#define V06_VI53_CH1    0x0A    /* ВИ53: канал 1                          */
#define V06_VI53_CH0    0x0B    /* ВИ53: канал 0                          */
#define V06_PALETTE     0x0C    /* запись байта палитры                   */
#define V06_AY_SEL      0x15    /* AY-3-8910: выбор регистра (нечётный)  */
#define V06_AY_DAT      0x14    /* AY-3-8910: запись данных (чётный)     */

/* Управляющие слова ПИА */
#define V06_CW_NORMAL   0x88    /* PA вход, PB выход (обычный режим)      */
#define V06_CW_KEYSCAN  0x8A    /* чтение клавиатуры через порт B (2)     */

/* --------------------------- Порты (v06io.asm) ------------------------ */

extern void v06_out(unsigned char port, unsigned char val);
extern unsigned char v06_in(unsigned char port);

/* ------------------------------ Графика ------------------------------- */

#define V06_VRAM        ((unsigned char *)0x8000)

/* RLE-поток bmp2inc.py: прямоугольник картинки — заголовок (ширина
 * в 8-пиксельных блоках, высота; 0 = 256), пары (количество, байт),
 * терминатор — 0. Вывод в точку (x, y) — левый верхний угол картинки;
 * x должно быть кратно 8, картинка должна помещаться в экран 256x256.
 * Область вне картинки не меняется (для чистого экрана — graph_clear). */
extern void graph_rle_expand(const unsigned char *src, unsigned char x,
                             unsigned char y);

/* Заливка экрана цветом 0-15 (плоскостная видеопамять). */
extern void graph_clear(unsigned char color);

/* Загрузка 16 цветов палитры. Формат байта: 0bBBGGGRRR.
 * Палитра Вектора адресуется «цветом под лучом», поэтому запись идёт
 * в кадровый гасящий интервал через регистр бордюра (см. v06pal.asm). */
extern void graph_set_palette(const unsigned char *pal);

/* Все 16 цветов чёрные (скрыть экран/процесс отрисовки). */
extern void graph_set_black_palette(void);

/* Регистр строки (скролл); значение запоминается — keyboard.c
 * восстанавливает его после сканирования клавиатуры. */
extern void graph_set_scroll(unsigned char row);
extern unsigned char graph_scroll_row;

/* Текст шрифтом 8x8 (глифы " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().").
 * Ячейка непрозрачная: пиксели глифа — цвет color (0-15), фон затирается.
 * x должно быть кратно 8, y — верхняя строка ячейки. */
extern void graph_put_char(unsigned char x, unsigned char y, char ch,
                           unsigned char color);
extern void graph_print(unsigned char x, unsigned char y, const char *s,
                        unsigned char color);

/* ------------------------------- Звук --------------------------------- */

/* Один шаг мелодии плеера sound.c: длительность в тиках 50 Гц и
 * делители ВИ53 (частота = 1500000 / делитель; 0 = тишина),
 * noise — ударные в начале шага на канале шума AY-3-8910 (drums.asm):
 * 0 = нет, 1 = снейр/том, 2 = бочка. */
typedef struct {
    unsigned char duration;
    unsigned int  ch1;
    unsigned int  ch2;
    unsigned int  ch3;
    unsigned char noise;
} sound_step_t;

extern void sound_init(void);               /* все каналы в тишину      */
extern void sound_silence(void);            /* тишина + сброс состояния */

/* Плееры мелодий: sound.c (шаговая мелодия, символы sound_*) и
 * music.c (партитурный синтезатор, -DMUSIC_ONLY, символы music_*).
 * Префиксы разные — символы не конфликтуют; в одном ROM всё равно
 * собирайте один плеер: оба пишут в одни каналы ВИ53. */
#ifdef MUSIC_ONLY

/* music.c — партитурный синтезатор: 3 тона ВИ53 + шумовые ударные
 * AY-3-8910 (сэмлы .smp, drums.asm). Данные — music_song_t, их
 * компилирует utils/mus2inc.py из .mus/.smp в .inc: четыре потока
 * байткода (3 тона + ударные) и таблица сэмплов; все длительности
 * предвычислены в кадрах 50 Гц, в прерывании нет деления времени.
 * Байткод (общие константы с mus2inc.py):
 *   0x00        конец потока;
 *   0x01..0x5F  нота, абсолютный номер = байт - 1 (октава*12 +
 *               полутон; ля 4-й октавы = 57, делитель ВИ53 3409);
 *   0x60        пауза на текущую длительность;
 *   0xE0..0xE7  длительность L1..L128 сетки PPQ = 32: L = 1 << (байт -
 *               0xE0), в тиках 128/L (четверть = 32 тика); темп
 *               применяется в runtime: tempo_num/tempo_den тика за кадр.
 * Команда состояния (0xE0-0xE7) время не продвигает; начальная
 * длительность потока без команд — L4. Октава — compile-time состояние
 * mus2inc.py, в байткоде команды нет (диапазон 0xD0..0xD7 свободен). */
#define MUS_END         0x00
#define MUS_REST        0x60
#define MUS_LEN         0xE0    /* ..0xE7: тики = 0x80 >> (байт-MUS_LEN) */

typedef struct {
    unsigned int tempo_num;             /* тиков clock на кадр: num/den */
    unsigned int tempo_den;             /* (4T/375, ТЗ — четвертей/мин) */
    unsigned int  length;               /* длина композиции в тиках     */
    /* Потоки байткода (sdcc не умеет инициализировать массивы внутри
     * структур — отдельные поля): s0-s2 — тона, dr — ударные. */
    const unsigned char *s0;
    const unsigned char *s1;
    const unsigned char *s2;
    const unsigned char *dr;
    const unsigned char * const *samples; /* таблица <имя>_samples[10] */
} music_song_t;

extern void music_set_data(const music_song_t *song);
extern void music_start(void);
extern void music_pause(void);
extern void music_resume(void);
extern void music_stop(void);
extern unsigned char music_is_playing(void);
extern void music_set_loop(unsigned char loop);
/* Один шаг music clock — из кадрового прерывания (startup.asm);
 * рядом должен вызываться drum_tick() (огибающие сэмплов). */
extern void music_tick(void);

#else /* обычная сборка: плеер sound.c */

extern void sound_set_data(const sound_step_t *steps, unsigned int len);
/* Темп = num/den тика плеера на кадровое прерывание 50 Гц.
 * 1/1 — номинал (длительности шагов как есть); num < den — медленнее,
 * num > den — быстрее. Например, sound_set_tempo(4, 5) — темп 80%. */
extern void sound_set_tempo(unsigned char num, unsigned char den);
/* Зацикливание: 0 (по умолчанию) — по окончании мелодии тишина и
 * остановка; 1 — играть по кругу. */
extern void sound_set_loop(unsigned char loop);
extern void sound_start(void);
extern void sound_stop(void);
extern unsigned char sound_is_playing(void);
/* Один тик плеера — вызывается из кадрового прерывания (startup.asm). */
extern void sound_tick(void);

#endif /* MUSIC_ONLY */

/* ------------------------- Ударные (drums.asm) ----------------------- */

/* Синтезатор ударных на AY-3-8910, только канал шума: канал C в режиме
 * «tone off, noise on». Тоновые каналы не трогает: в R0-R5 не пишет,
 * R7 пишет один раз (drum_init), звук управляется R6 (период шума) и
 * R10 (громкость канала C, программная огибающая в drum_tick).
 * noise в sound_step_t — моментальное событие: каждый drum_*() всегда
 * перезапускает звучащий удар, приоритеты ничего не блокируют.
 * Параметры инструментов — таблица в начале drums.asm. */
extern void drum_init(void);            /* микшер и тишина             */
extern void drum_kick(void);
extern void drum_snare(void);
extern void drum_hat_c(void);           /* закрытый хэт                */
extern void drum_hat_o(void);           /* открытый хэт                */
extern void drum_tom(void);
extern void drum_clap(void);
extern void drum_rim(void);
extern void drum_tick(void);            /* раз в кадр, 50 Гц           */
extern void drum_mute(void);            /* оборвать звучащий удар      */
/* Проиграть семпл .smp (mus2inc.py): байт N — число кадров, затем
 * N пар (R6, R10) по одному кадру в тик 50 Гц; первый кадр сразу.
 * Нулевой указатель и N = 0 — тишина. Звучащий семпл вытесняет
 * табличный удар и наоборот; ведёт его drum_tick(). */
extern void drum_sample_play(const unsigned char *smp);

/* ----------------------------- Клавиатура ----------------------------- */

/* Однократный опрос матрицы. Возвращает код первой нажатой клавиши
 * (ASCII / 27 = АПС=ESC, 13 = ВК) или 0, если ничего не нажато. */
extern unsigned char kbd_scan(void);

/* ------------------------------ Прочее -------------------------------- */

/* Счётчик кадров 50 Гц; увеличивается кадровым прерыванием (startup.asm). */
extern volatile unsigned int frame_count;

/* Обработчик кадрового прерывания 50 Гц (startup.asm): назначьте
 * функцию — она будет вызываться каждый кадр из прерывания.
 * 0 (по умолчанию) — обработчика нет. Пример: frame_handler = music_tick; */
extern void (*frame_handler)(void);

#endif /* V06_H */
