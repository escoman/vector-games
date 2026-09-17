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

/* Формат байта палитры: RRRGGGBB (D0-D2 красный, D3-D5 зелёный, D6-D7 синий). */
#define V06_RGB(r, g, b)  (((b) << 6) | ((g) << 3) | (r))
#define V06_AY_SEL      0x15    /* AY-3-8910: выбор регистра (нечётный)  */
#define V06_AY_DAT      0x14    /* AY-3-8910: запись данных (чётный)     */

/* Управляющие слова ПИА */
#define V06_CW_NORMAL   0x88    /* PA вход, PB выход (обычный режим)      */
#define V06_CW_KEYSCAN  0x8A    /* чтение клавиатуры через порт B (2)     */

/* --------------------------- Порты (v06io.asm) ------------------------ */

extern void v06_out(unsigned char port, unsigned char val);
extern unsigned char v06_in(unsigned char port);

/* ------------------------------- Графика ------------------------------- */

#define V06_VRAM        ((unsigned char *)0x8000)

/* Видеорежимы */
#define GFX_MODE_256_16  0   /* 256x256, 16 цветов, все плоскости      */
#define GFX_MODE_256_2   1   /* 256x256, 2 цвета, плоскость 0xE000     */
#define GFX_MODE_512_4   2   /* 512x256, 4 цвета                       */
#define GFX_MODE_512_2   3   /* 512x256, 2 цвета, 0xE000+0xA000        */

typedef struct {
    unsigned char width_div8;   /* 32 (256) или 64 (512); >32 = 512    */
    unsigned char plane_mask;   /* маска активных плоскостей            */
    unsigned char num_colors;   /* 2, 4 или 16                          */
} gfx_mode_t;

extern const gfx_mode_t gfx_modes[];
extern unsigned char gfx_current_mode;

/* Переключение режима. 256x256 — аппаратный по умолчанию, не трогает
 * ПИА. 512x256 — настраивает ПИА и скролл. */
extern void gfx_set_mode(unsigned char mode);

/* Очистка экрана цветом 0-15. Заполняет только активные плоскости
 * текущего режима (через gfx_fill_planes). */
extern void gfx_clear(unsigned char color);

/* Загрузка палитры из num_colors цветов. Автоматически расширяет
 * до 16 слотов, маскируя неиспользуемые плоскости. */
extern void gfx_set_palette(const unsigned char *colors);

/* RLE-поток bmp2inc.py: прямоугольник картинки — заголовок (ширина
 * в 8-пиксельных блоках, высота; 0 = 256), пары (количество, байт),
 * терминатор — 0. Вывод в точку (x, y) — левый верхний угол картинки;
 * x должно быть кратно 8, картинка должна помещаться в экран 256x256.
 * Область вне картинки не меняется (для чистого экрана — gfx_clear). */
extern void gfx_rle_expand(const unsigned char *src, unsigned char x,
                             unsigned char y);

/* Заливка плоскостей VRAM цветом 0-15 (gfx_fill_planes в clr.asm).
 * mask определяет, какие плоскости заполнять; fill: 0x00 или 0xFF. */
extern void gfx_fill_planes(unsigned char mask, unsigned char fill) __z88dk_callee;

/* Заливка с шагом: записывает val по адресу addr, затем
 * addr+step, addr+2*step и т.д., всего count байт (fstride.asm). */
extern void gfx_fill_stride(unsigned int addr, unsigned char val,
                              unsigned int step, unsigned char count) __z88dk_callee;

/* Загрузка 16 цветов палитры. Формат байта: 0bRRRGGGBB.
 * Палитра Вектора адресуется «цветом под лучом», поэтому запись идёт
 * в кадровый гасящий интервал через регистр бордюра (см. v06pal.asm). */
extern void gfx_set_bmp_palette(const unsigned char *pal);

/* Все 16 цветов чёрные (скрыть экран/процесс отрисовки). */
extern void gfx_set_black_palette(void);

/* Регистр строки (скролл); значение запоминается — keyboard.c
 * восстанавливает его после сканирования клавиатуры. */
extern void gfx_set_scroll(unsigned char row);
extern unsigned char gfx_scroll_row;

/* Текст шрифтом 8x8 (глифы " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().").
 * Ячейка непрозрачная: пиксели глифа — цвет color (0-15), фон затирается.
 * x должно быть кратно 8, y — верхняя строка ячейки. */
extern void gfx_put_char(unsigned char x, unsigned char y, char ch,
                           unsigned char color) __z88dk_callee;
extern void gfx_print(unsigned char x, unsigned char y, const char *s,
                        unsigned char color) __z88dk_callee;

/* Текст шрифтом 16x8 в режиме 512x256 (pr512.asm). */
extern void gfx_put_char_512(unsigned char x, unsigned char y, char ch,
                               unsigned char color) __z88dk_callee;
extern void gfx_print_512(unsigned char x, unsigned char y, const char *s,
                            unsigned char color) __z88dk_callee;

/* Тонкий текст 4x8 в режиме 512x256 (pr512t.asm). */
extern void gfx_print_512t(unsigned char x, unsigned char y, const char *s,
                             unsigned char color) __z88dk_callee;

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

/* Режимы вывода: MUSIC_MODE_VI53 — тоны на КР580ВИ53, шум ударных на
 * Tape Out (PC0); MUSIC_MODE_AY — тоны и шум на AY-3-8910.
 * Флаги общие для music_mode() и drum_mode(), поэтому константы живут
 * вне #ifdef MUSIC_ONLY (drums.asm линкуется и без music.c). */
#define MUSIC_MODE_VI53 0
#define MUSIC_MODE_AY   1

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
 *   0xE8        начало повторяемой секции «[»: запоминает адрес
 *               возврата, счётчик повторов = 0;
 *   0xE9 n      конец секции «]n»: пока счётчик < n, исполнение
 *               возвращается к адресу возврата (секция звучит n раз).
 *   0xEA <lo> <hi> — JMP назад на (lo | hi<<8) байт: бесконечный
 *               цикл основной части мелодии (intro + loop).
 * Команды состояния (0xE0-0xE9) время не продвигают; начальная
 * длительность потока без команд — L4. Октава — compile-time состояние
 * mus2inc.py, в байткоде команды нет (диапазон 0xD0..0xD7 свободен). */
#define MUS_END         0x00
#define MUS_REST        0x60
#define MUS_LEN         0xE0    /* ..0xE7: тики = 0x80 >> (байт-MUS_LEN) */
#define MUS_LPSTART     0xE8    /* «[»: база повтора = следующий байт   */
#define MUS_LPEND       0xE9    /* «]n»: операнд n — всего n проходов   */
#define MUS_JMP         0xEA    /* <lo> <hi>: JMP назад на (lo|hi<<8)  */

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
    const unsigned char * const *samples; /* таблица <имя>_samples[16] */
} music_song_t;

extern void music_set_data(const music_song_t *song);
extern void music_start(void);
extern void music_pause(void);
extern void music_resume(void);
extern void music_stop(void);
extern unsigned char music_is_playing(void);
extern void music_set_loop(unsigned char loop);
/* Маскировка каналов в runtime: биты 0-2 — тон 0-2, бит 3 — ударные.
 * 0x0F — все включены, 0x00 — все выключены. */
extern void music_set_channel_mask(unsigned char mask);
/* Один шаг music clock — из кадрового прерывания (startup.asm);
 * рядом должен вызываться drum_tick() (огибающие сэмплов). */
extern void music_tick(void);

/* Backend: ВИ53 (0, по умолчанию) или AY-3-8910 (1). Переключение
 * во время воспроизведения — без сброса позиции и состояния.
 * Три мелодических канала: 0→VI53 CH0/AY A, 1→CH1/AY B, 2→CH2/AY C.
 * Ударные (шум) следуют тому же флагу: VI53 → Tape Out PC0 (LFSR в
 * drums.asm), AY → шумовой канал AY (см. также drum_mode). */
extern void music_mode(unsigned char mode);

/* ---------------- AY-3-8910: аппаратная огибающая -------------------- */

/* Штатный envelope generator AY-3-8910. Генератор в чипе ОДИН ОБЩИЙ
 * на все три тональных канала: R11/R12 (16-битный период) и R13 (форма)
 * физически единственные. Параметр channel в ay_set_envelope() выбирает
 * только ТОТ канал, который подключается к огибающей (ставит бит 4 в
 * R8/R9/R10), а не создаёт независимую огибающую. Два последовательных
 * вызова с разными channel используют один и тот же R11/R12/R13 — у
 * последнего вызова форму/период. Каналы, которым бит 4 не выставлен,
 * остаются на фиксированной громкости. */

/* Формы R13 (4 бита). Перечислены все 16 значений; часть из них даёт
 * идентичную наблюдаемую форму — дубликаты сохранены намеренно, см.
 * примечание у каждого. Обозначения: / — рост, \ — спад, ‾ — удержание
 * максимума (R13=15), _ — удержание нуля.
 * Биты R13 у AY-3-8910 трактуются так: бит 3 = «первый цикл спадом /
 * ростом» и «разрешить продолжение», бит 2 = выбор стартового
 * направления, бит 1 = альтернировать цикл, бит 0 = удерживать итог
 * после ПЕРВОГО цикла. Из-за этого 8 и 9 (10 и 11, 12 и 13, 14 и 15)
 * дают РАЗНОЕ наблюдаемое поведение: без продолжения (нечётные) —
 * одиночный проход с удержанием, с продолжением (чётные) —
 * периодическая форма. */
#define AY_ENV_0    0x00 /* \_____    спад → удержание 0                   */
#define AY_ENV_1    0x01 /* \_____    то же, что AY_ENV_0 (HOLD игнор.)    */
#define AY_ENV_2    0x02 /* \_____    то же, что AY_ENV_0                  */
#define AY_ENV_3    0x03 /* \_____    то же, что AY_ENV_0                  */
#define AY_ENV_4    0x04 /* /‾‾‾‾‾    линейный рост → удержание максимума  */
#define AY_ENV_5    0x05 /* /‾‾‾‾‾    то же, что AY_ENV_4 (HOLD игнор.)    */
#define AY_ENV_6    0x06 /* /‾‾‾‾‾    то же, что AY_ENV_4                  */
#define AY_ENV_7    0x07 /* /‾‾‾‾‾    то же, что AY_ENV_4                  */
#define AY_ENV_8    0x08 /* \\\\      repeating saw-down (спад, повтор)     */
#define AY_ENV_9    0x09 /* \_____    спад → удержание 0 (одиночный)       */
#define AY_ENV_10   0x0A /* \/\/\/    repeating triangle (старт со спада)  */
#define AY_ENV_11   0x0B /* \_____    спад → удержание 0 (одиночный)       */
#define AY_ENV_12   0x0C /* //////    repeating saw-up (рост, повтор)       */
#define AY_ENV_13   0x0D /* /‾‾‾‾‾    рост → удержание 15 (одиночный)      */
#define AY_ENV_14   0x0E /* /\/\/\/   repeating triangle (старт с роста)    */
#define AY_ENV_15   0x0F /* /‾‾‾‾‾    рост → удержание 15 (одиночный)      */

/* Практические алиасы (указывают на эквивалентные коды из списка). */
#define AY_ENV_DECAY          AY_ENV_0    /* одиночный спад → тишина       */
#define AY_ENV_HOLD_LOW       AY_ENV_0    /* то же: после спада держит 0   */
#define AY_ENV_ATTACK         AY_ENV_4    /* рост → удержание максимума    */
#define AY_ENV_HOLD_HIGH      AY_ENV_4    /* то же: после роста держит max */
#define AY_ENV_TRIANGLE       AY_ENV_14   /* плавный вверх-вниз, старт вверх*/
#define AY_ENV_TRIANGLE_DOWN  AY_ENV_10   /* то же, но старт со спада      */

/* Подключить канал к аппаратной огибающей: period → R11/R12, shape →
 * R13 (запись R13 перезапускает генератор), в R8/R9/R10 выставить бит 4.
 * channel: 0=A (R8), 1=B (R9), 2=C (R10). Возврат — ничего; при
 * channel > 2 вызов игнорируется.
 *
 * ВНИМАНИЕ: R11/R12/R13 — общие регистры AY-3-8910 на все три канала.
 * Вызов для одного канала МЕНЯЕТ форму/период envelope для ВСЕХ каналов,
 * которые сейчас подключены к огибающей (у которых бит 4 в R8/R9/R10 = 1),
 * и перезапускает общий генератор (из-за записи R13). Если A уже на
 * огибающей и вызвать ay_set_envelope(2, ...) с другой формой/периодом —
 * канал A тоже услышит новую форму. */
extern void ay_set_envelope(unsigned char channel,
                            unsigned char shape,
                            unsigned int period);

/* Вернуть канал на фиксированную громкость: сбросить бит 4 в
 * R8/R9/R10 и записать volume (обрезается до 0..15). volume = 0 —
 * канал выключен. При channel > 2 вызов игнорируется. */
extern void ay_set_fixed_volume(unsigned char channel,
                                unsigned char volume);

/* Диагностика (ТЗ §4-12): счётчики для определения рассинхронизации
 * тональных каналов и ударных. Только наблюдение, не влияют на звук. */
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

/* Синтезатор шума: в режиме MUSIC_MODE_AY — канал C AY-3-8910 в
 * «tone off, noise on» (R6 период, R10 громкость, микшер R7);
 * в режиме MUSIC_MODE_VI53 — программный 1-битный LFSR-шум на
 * Tape Out (PIA1 Port C bit 0): R6 задаёт число сдвигов за тик,
 * R10 — duty-окно переключений PC0. Выход выбирается по g_music_mode
 * (общий флаг с мелодией, см. music_mode / drum_mode).
 * Тоновые регистры не трогает: в R0-R5 не пишет, R8/R9 не пишет вовсе,
 * в R7 меняет только биты шума/тона C (по зеркалу g_ay_r7).
 * noise в sound_step_t — моментальное событие: каждый drum_*() всегда
 * перезапускает звучащий удар, приоритеты ничего не блокируют.
 * Параметры инструментов — таблица в начале drums.asm. */
extern unsigned char g_music_mode;    /* MUSIC_MODE_* (в music.c)     */
extern void drum_mode(unsigned char mode); /* выход шума: 0=PC0, 1=AY */
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

/* Опрос матрицы без ожидания кадра — для вызова в самом начале
 * кадрового прерывания: луч на VSync в гашении, маски строк (порт 03h
 * = скролл) не задевают видимую часть. Парная с kbd_read(). */
extern void kbd_scan_now(void);

/* Декодировать последний снимок матрицы без повторного опроса портов. */
extern unsigned char kbd_read(void);

/* Ждёт нажатия указанной клавиши (код как у kbd_scan: ASCII,
 * 27 = ESC, 13 = ВК, ' ' = пробел). Синхронизация 50 Гц,
 * фронт-детектор: реагирует только на нажатие. */
extern void kbd_wait_key(unsigned char key);

/* ------------------------------ Прочее -------------------------------- */

/* Счётчик кадров 50 Гц; увеличивается кадровым прерыванием (startup.asm). */
extern volatile unsigned int frame_count;

/* Ожидание следующего кадра (синхронизация с VBlank 50 Гц).
 * HLT до прерывания, затем проверка frame_count. Возвращает
 * управление, когда счётчик изменился (прошёл новый кадр). */
extern void gfx_next_frame(void);

/* Обработчик кадрового прерывания 50 Гц (startup.asm): назначьте
 * функцию — она будет вызываться каждый кадр из прерывания.
 * 0 (по умолчанию) — обработчика нет. Пример: frame_handler = music_tick; */
extern void (*frame_handler)(void);

#endif /* V06_H */
