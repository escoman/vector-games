/*
 * main.c — приложение "Композитор" для Вектора-06Ц.
 *
 * Музыкальный редактор с текстовым вводом партитур (.mus формат).
 * 3 тоновых голоса + ударные, проигрывание с подсветкой.
 * Экран 256x256x2, монохромный. Подсветка — инверсией символов.
 *
 * Ф1 — помощь, Ф2 — играть/стоп, Ф3 — ударные, Ф4 — соло-редактор
 * партитуры, Ф5 — о программе. Все они обрабатываются хуком
 * контроллера компонентов (ctrl.on_key), своего цикла клавиатуры у
 * главного экрана больше нет.
 *
 * SCORE 1..3 и DRUMS — компоненты textarea: текст правится на месте,
 * ТАБ переводит фокус между полями (СС+ТАБ — назад), внутри поля
 * работают ←/→/↑/↓. АП2 на главном экране — стоп проигрывания и
 * перерисовка.
 *
 * Соло-редактор — отдельный экран, он в solo.c.
 */

#include <string.h>
#include "v06.h"
#include "comps.h"
#include "parser.h"
#include "nes_drums.h"
#include "screens.h"

/* Инверсия символов в режиме 256x256x2 (плоскость 0xE000).
 * Инвертирует 9 строк: 1 выше + 8 глифа — целостная инверсия. */
void invert_chars(unsigned char col, unsigned char row,
                         unsigned char count)
{
    unsigned char c, r;
    volatile unsigned char *p;
    for (c = 0; c < count; c++) {
        p = (volatile unsigned char *)(0xE000 + (unsigned int)(col + c) * 256
                                       + (255 - row));
        for (r = 0; r < 9; r++) {
            *p ^= 0xFF;
            p--;
        }
    }
}

/* ------------------------------- Палитра ---------------------------- */

static const unsigned char composer_pal[2] = {
    V06_RGB(0, 0, 0),   /* 0: чёрный (фон) */
    V06_RGB(7, 7, 3),   /* 1: белый (текст) */
};


/* ------------------------------- Константы -------------------------- */

/* Раскладка главного экрана. Пиксели, строки — как в comps.h:
 * поле занимает от ta->y (верх метки) 25 + (lines-1)*10 строк, то есть
 * 45 при трёх видимых. Шаг 48 — 3 строки запаса: инверсия метки
 * задевает ряд на 1 выше неё, а нижняя линия рамки предыдущего поля
 * стоит на y+45. */
#define FOOT_Y      248              /* подвал (переключатель вывода)   */

/* Переключатель вывода звука в подвале: «VI53» и «AY» двумя кнопками,
 * горит та, куда сейчас идёт звук. Инвертируется слово вместе с
 * прилегающей колонкой запаса (« VI53 » и « AY »), так что кнопки
 * примыкают друг к другу и между ними остаётся чёрный зазор.
 * Колонки нужны и chrome_main() (красит подсветку на свежем экране), и
 * обработчику АП2 (тем же XOR переносит её на другую кнопку). */
#define OUT_VI_X    0                /* « VI53 » — 6 колонок             */
#define OUT_VI_N    6
#define OUT_AY_X    6                /* « AY »   — 4 колонки             */
#define OUT_AY_N    4

#define FIELD_X     0
#define FIELD_W     30               /* видимых колонок (рамка: 0..31)  */
#define FIELD_LINES 3                /* видимых строк в поле            */
#define FIELD_Y0    24
#define FIELD_PITCH 56

/* --------------------------- Память --------------------------------- */

/* Буферы партитур берутся из кучи (lib/mem/heap.c) — она стартует от
 * конца образа ROM, так что 4 КБ текстовых буферов не стоят образу ни
 * байта. Потолок кучи по умолчанию 0x8000 (выше — видеопамять); здесь
 * его поднимаем до 0xE000: экран 256x256x2, активна и заливается одна
 * плоскость 0xE000, остальное — обычная ОЗУ. */
#define SCORE_BUF   256            /* байт на канал, с терминатором */

/* --------------------------- Глобальные данные ---------------------- */

static char *score_text[4];

/* Поля главного экрана. Соло-редактор (Ф4) — отдельный экран (solo.c),
 * он сам создаёт своё поле на буфер выбранного канала. */
static textarea_t score_fields[4];
static controller_t ctrl;

static const char *field_label[4] = {
    "SCORE 1", "SCORE 2", "SCORE 3", "DRUMS"
};

static unsigned char bc_buf[4][PARSER_BC_SIZE];
static music_song_t song;

static unsigned char modal_screen; /* на экране модалка со своим заголовком */

/* Режим проигрывания — он же признак «играет»: PLAY_NONE / PLAY_ALL /
 * PLAY_ONE (см. screens.h). */
unsigned char play_mode;

/* Колонка и ширина той подписи, что горит сейчас. Нужны только чтобы
 * снять подсветку на естественном конце партитуры — вызвать
 * play_label() с правильными аргументами прерыванию негде. Обновляет их
 * сам play_label(); ширина 0 — подписать нечего. */
static unsigned char lit_col;
static unsigned char lit_count;

/* Вывод звука: 0 = КР580ВИ53 (ударные на Tape Out), 1 = AY-3-8910
 * (ударные на шумовом канале C). Флаг локальный: «режима звука» в
 * движке нет, есть привязка вывода (music_use_vi53/music_use_ay), а её
 * спросить негде. Значение 0 — то, с чем движок и стартует. */
static unsigned char out_ay;

/* ------------------------- Встроенный пример ------------------------ */

static const char default_s0[] = "O4 L4 S10 1500 C D E F G A B O5 C";
static const char default_s1[] = "O3 L4 V2 C V4 D V6 E V8 F V10 G V12 A V14 B V15 O4 C";
static const char default_s2[] = "O2 L2 C G C G";
static const char default_dr[] = "L4 0 P 2 P 0 P 4 P\nL4 8 P 10 P 8 P 10 P";

/* ------------------------- Прототипы ------------------------------- */

void playback_start(void);
void playback_stop(void);

/* Поле главного экрана открывает соло-редактор, а хук контроллера нужен
 * fields_init() раньше, чем определён. */
static unsigned char on_key(unsigned char key);

/* ------------------------- Кадровый обработчик --------------------- */

static void on_frame(void)
{
    music_tick();
    drum_tick();

    if (play_mode == PLAY_NONE) return;

    /* Партитура доиграла. Узнать об этом больше негде: цикла клавиатуры
     * у главного экрана нет, он у контроллера компонентов. Стоп так же,
     * как по нажатию Ф2/Ф3 — playback_stop() и маску каналов сбрасывает
     * (music_stop), чтобы следующая Ф2 снова играла всё; гасим
     * подсветку и выключаем себя — на следующем прерывании
     * frame_handler уже не вызовит on_frame (trampoline прочитал адрес
     * заранее, так что выход из прерывания не ломается). */
    if (!music_is_playing()) {
        playback_stop();
        /* На модалке ряд 8 занят её собственным заголовком — тушить
         * там нечего, а после возврата всё перерисуется заново. */
        if (!modal_screen)
            play_label_off();
    }
}

/* ------------------------- Утилиты --------------------------------- */

/* Экран: чёрная палитра и очистка. Режим ставить не нужно — его
 * выставили один раз в main(), и сменить его может только то, что
 * пишет в порты видеочасти, а экраны нашего ROM-а только красят
 * плоскость. */
void begin_init_screen(void)
{
    gfx_set_black_palette();
    gfx_clear(0);
}

/* Отрисовка кончена — показать результат. */
void end_init_screen(void)
{
    gfx_set_palette(composer_pal);
}

/* Подсветка подписи проигрывания: инвертировать count символов от
 * колонки col на строке заголовка, либо снять инверсию (on = 0).
 * Экран печатает свой заголовок сам — здесь только XOR.
 * Перепечатывать текст вместо этого нельзя: инвертируется 9 строк
 * (ряд над глифами тоже), а рисуется 8, так что от перепечати над
 * подписью оставалась бы белая полоска. */
void play_label(unsigned char col, unsigned char count, unsigned char on)
{
    invert_chars(col, (unsigned char)(HDR_Y - 1), count);
    if (on) {
        lit_col = col;
        lit_count = count;
    } else {
        lit_count = 0;
    }
}

/* Погасить ту подпись, что горит. */
void play_label_off(void)
{
    if (lit_count)
        play_label(lit_col, lit_count, 0);
}

/* Подсветка активного слова переключателя вывода. Один и тот же вызов
 * ставит и снимает её (XOR по тем же клеткам), поэтому при переключении
 * достаточно тушить старое слово и зажечь новое. Перепечатью тут не
 * обойтись: инверсия захватывает ряд над глифами, а печать — только
 * сами глифы. */
static void out_invert(unsigned char ay)
{
    if (ay)
        invert_chars(OUT_AY_X, (unsigned char)(FOOT_Y - 1), OUT_AY_N);
    else
        invert_chars(OUT_VI_X, (unsigned char)(FOOT_Y - 1), OUT_VI_N);
}

/* ------------------------- Проигрывание ---------------------------- */

/* Собираем строки сообщения об ошибке парсинга в 32-колоночный
 * буфер: префикс + числа + фрагмент партитуры. Простого хелпера
 * форматирования в lib нет — здесь нужен только dec-ввод. */
static char msg_buf[33];

static void msg_cat(const char *s)
{
    unsigned char i = 0;
    while (msg_buf[i])
        i++;
    while (*s && i < 31) {
        msg_buf[i++] = *s++;
    }
    msg_buf[i] = 0;
}

static void msg_dec(unsigned int v)
{
    char tmp[8];
    char t;
    unsigned char n = 0, i;

    do {
        tmp[n++] = (char)('0' + (unsigned char)(v % 10u));
        v /= 10u;
    } while (v && n < 7u);
    tmp[n] = 0;
    for (i = 0u; i < n / 2u; ++i) {   /* цифры в обратном порядке */
        t = tmp[i];
        tmp[i] = tmp[n - 1u - i];
        tmp[n - 1u - i] = t;
    }
    msg_cat(tmp);
}

/* Экран ошибки парсинга: код, партитура (SCORE 0..2 / DRUMS),
 * строка/столбец (1-based), что за ошибка и фрагмент партитуры от
 * ошибочного токена. Вызывается из playback_start; держится до AP2
 * (см. playback_toggle/show_result). */
static void show_parse_error(const parse_result_t *res, unsigned char ch)
{
    static const char *chan_names[4] = {
        "SCORE 0", "SCORE 1", "SCORE 2", "DRUMS"
    };

    begin_init_screen();
    gfx_print(0, 40, "PARSE ERROR", 1);
    gfx_print(0, 56, ch < 4u ? chan_names[ch] : "PARTITURE ?", 1);
    msg_buf[0] = 0;
    msg_cat("LINE ");
    msg_dec((unsigned int)res->err_line + 1u);
    msg_cat(" COL ");
    msg_dec((unsigned int)res->err_col + 1u);
    gfx_print(0, 72, msg_buf, 1);
    gfx_print(0, 88, parse_error_name(res->err_code), 1);
    if (res->err_text[0]) {           /* фрагмент не пуст — есть что */
        msg_buf[0] = 0;               /* показать: ошибочный токен и   */
        msg_cat("> ");                /* следующие операнды партитуры  */
        msg_cat(res->err_text);
        gfx_print(0, 104, msg_buf, 1);
    }
    gfx_print(0, 136, "AP2-RETURN", 1);
    end_init_screen();
}

void playback_stop(void)
{
    play_mode = PLAY_NONE;
    music_stop();
    drum_mute();
    frame_handler = 0;
}

/* Ф2/Ф3 на любом экране: одно нажатие — старт, следующее — стоп.
 * mode: PLAY_ALL (Ф2, играет всё) или PLAY_ONE (Ф3 на соло-экране,
 * играет только канал ch).
 * Результат возвращается вызывающему, чтобы тот восстанавливал СВОЙ
 * экран: у сообщения об ошибке парсинга весь экран свой, и перерисовка
 * главного поля отсюда вытеснила бы его. */
unsigned char playback_toggle(unsigned char mode, unsigned char ch)
{
    if (play_mode != PLAY_NONE) {
        playback_stop();
        return PLAY_NONE;
    }
    playback_start();
    if (play_mode == PLAY_NONE)
        return PLAY_ERROR;
    if (mode == PLAY_ONE) {
        /* Включить только выбранный канал, остальные выключить */
        music_set_channel_mask((unsigned char)(1u << ch));
        play_mode = PLAY_ONE;
    }
    return play_mode;
}

void playback_start(void)
{
    /* Результат парсинга — не на стеке: цепочка
     * controller_run → on_key → playback_toggle → playback_start →
     * parse_song → parse_score и так близка к векторной странице
     * (стек растёт из-под 0x0100, а RST 0x38 живёт на 0x0038). */
    static parse_result_t res;
    unsigned char ch;
    unsigned char tempo = 120;

    /* Парсинг всех 4 каналов */
    for (ch = 0; ch < 4; ch++) {
        if (score_text[ch][0] == 0) {
            bc_buf[ch][0] = MUS_END;
            continue;
        }
        parse_score(&res, score_text[ch], bc_buf[ch],
                    PARSER_BC_SIZE, (ch == 3) ? 1 : 0);
        if (!res.ok) {
            /* Ошибка парсинга — весь экран под сообщение. Интерфейс
             * восстановит вызывающий (on_key), когда увидят текст. */
            show_parse_error(&res, ch);
            return;
        }
    }

    /* Заполнение song */
    {
        const char *texts[4];
        for (ch = 0; ch < 4; ch++)
            texts[ch] = score_text[ch][0] ? score_text[ch] : (const char *)0;
        parse_song(&res, texts, bc_buf, tempo, nes_drums_samples, &song);
        if (!res.ok) {
            show_parse_error(&res, res.err_chan);
            return;
        }
    }

    /* Запуск. Сначала стартуем транспорт (music_start_* ставит
     * g_playing = 1), и только потом взводим play_mode и кадровый
     * обработчик. Иначе прерывание 50 Гц, пришедшее в окно между
     * frame_handler = on_frame и фактическим стартом, увидит
     * play_mode != PLAY_NONE при music_is_playing() == 0 и ложно
     * примет его за конец партитуры: playback_stop() сбросит
     * play_mode и обнулит frame_handler — звук не пойдёт, а
     * playback_toggle() вернёт PLAY_ERROR (экран зависнет в ожидании
     * АП2 без всякого сообщения об ошибке). */
    drum_init();
    music_set_data(&song);
    music_set_loop(0);

    /* Старт на ТОМ выводе, который выбран переключателем: music_start()
     * из ROM-а с обоими выводами не спрашивает текущий, а привязывает
     * КР580ВИ53 (он же возвращает и ударные на Tape Out) — после АП2
     * первая же Ф2 молча сбила бы режим обратно. */
    if (out_ay)
        music_start_ay();
    else
        music_start_vi53();

    play_mode = PLAY_ALL;
    frame_handler = on_frame;
}

/* ------------------------- Главный экран --------------------------- */

/* Заголовок и подвал. Сами поля рисует контроллер компонентов. */
static void chrome_main(void)
{
    gfx_print(0, HDR_Y, "F1-HELP F2-PLAY F3-DRUMS F4-SOLO", 1);
    /* На главном экране подпись проигрывания одна: F3 здесь — это
     * библиотека ударных, а не режим проигрывания. */
    if (play_mode != PLAY_NONE)
        play_label(8, PLAY_LBL_N, 1);

    /* Подвал: две кнопки переключателя вывода (АП2) в начале строки и
     * экран «о программе» (Ф5) в конце. Между ними запас — иначе
     * инверсия активной кнопки задевала бы соседнюю подсказку. */
    gfx_print(0, FOOT_Y, " VI53  AY ", 1);
    gfx_print(24, FOOT_Y, "F5-ABOUT", 1);

    /* Из двух кнопок горит одна — та, куда сейчас идёт звук. */
    out_invert(out_ay);
}

static void paint_main(void)
{
    begin_init_screen();
    chrome_main();
    /* Четыре поля — компоненты, их рисует контроллер. Здесь, а не
     * только при входе в цикл: после модального экрана и после сообщения
     * парсера подложка чистая, а controller_run в цикл уже не заходит. */
    controller_draw(&ctrl);
    end_init_screen();
}

/* Компоненты главного экрана. Соло-редактор (Ф4) своего поля не имеет:
 * он в solo.c и навешивает компонент на буфер канала сам, при входе. */
static void fields_init(void)
{
    unsigned char i;

    for (i = 0; i < 4; i++)
        textarea_init(&score_fields[i], score_text[i], SCORE_BUF - 1,
                      FIELD_W, FIELD_LINES, FIELD_X,
                      (unsigned char)(FIELD_Y0 + i * FIELD_PITCH),
                      field_label[i]);

    controller_init(&ctrl);
    for (i = 0; i < 4; i++)
        controller_add(&ctrl, (component_t *)&score_fields[i]);
    ctrl.on_key = on_key;
}

/* Модальный экран: свои клавиши и свой заголовок. */
static void modal(void (*screen)(void))
{
    modal_screen = 1;
    screen();
    modal_screen = 0;
    paint_main();
}

/* Функциональные клавиши главного экрана — хук контроллера. Возврат 1:
 * клавиша наша, 0 — отдать активному полю, >1 — код выхода из цикла
 * контроллера. Сейчас выходящих нет: АП2 в главном окне отдана
 * переключателю вывода, а из программы у ROM-аппарата выходить некуда
 * (на контроллере висит только ТАБ, см. controller_run). */
static unsigned char on_key(unsigned char key)
{
    unsigned char ch = ctrl.active;
    unsigned char r;

    if (key == KBD_KEY_ESC) {           /* АП2 — КР580ВИ53 <-> AY-3-8910 */
        /* Перепривязка живая: транспорт не сбрасывается, играющая
         * партитура продолжает звучать на новом выводе (текущие ноты
         * движок восстановит сам, ударные уйдут с Tape Out на шум AY).
         * Подсветка переносится на другое слово тем же XOR. */
        out_invert(out_ay);
        out_ay = (unsigned char)(!out_ay);
        if (out_ay)
            music_use_ay();
        else
            music_use_vi53();
        out_invert(out_ay);
        return 1;
    }
    if (key == KBD_KEY_F1) { modal(screen_help); return 1; }
    if (key == KBD_KEY_F2) {
        r = playback_toggle(PLAY_ALL, 0);
        if (r == PLAY_ERROR) {   /* парсер залил экран — держать до АП2 */
            kbd_wait_key(KBD_KEY_ESC);
            paint_main();
        } else if (r == PLAY_NONE) {
            play_label_off();
        } else {
            play_label(8, PLAY_LBL_N, 1);
        }
        return 1;
    }
    if (key == KBD_KEY_F3) { modal(screen_drums); return 1; }
    /* Ф4 — отдельный экран соло-редактора канала в фокусе. Он сам рисует
     * свой заголовок, сам заводит поле и контроллер и сам крутит свой
     * цикл; обратно приходит по АП2. Поле того же канала переносит
     * курсор, на котором вышли. */
    if (key == KBD_KEY_F4) {
        score_fields[ch].cur_col = screen_solo(ch, score_text[ch],
                                              SCORE_BUF - 1, field_label[ch]);
        paint_main();
        return 1;
    }
    if (key == KBD_KEY_F5) { modal(screen_about); return 1; }
    return 0;
}

/* ------------------------- main ------------------------------------ */

int main(void)
{
    unsigned char i;

    /* Режим ставится один раз и больше не трогается: экран за ROM
     * не меняется, а перестановка режима — это очистка видеочасти.
     * Экраны только красят плоскость: begin_init_screen() ставит
     * чёрную палитру и чистит, end_init_screen() возвращает рабочую. */
    gfx_set_mode(GFX_MODE_256_2);

    /* Потолок кучи поднимается до первой выдачи — ниже вершины кучи
     * его опускать уже некуда (см. lib/mem/heap.c). */
    heap_top = 0xE000;

    /* Инициализация данных — буферы партитур из кучи.
     * Отказ проверки оставил бы null-указатели в score_text: memcpy в
     * адрес 0 — это запись в векторы прерываний, а не тихий мусор. */
    for (i = 0; i < 4; i++) {
        score_text[i] = (char *)heap_alloc(SCORE_BUF);
        if (!score_text[i])
            return 1;               /* куча кончилась — играть нечего */
        memset(score_text[i], 0, SCORE_BUF);
    }

    play_mode = PLAY_NONE;

    /* Компоненты, затем примеры партитур: textarea навешивается на буфер,
     * содержимое его не трогает, так что порядок любой. */
    fields_init();
    memcpy(score_text[0], default_s0, sizeof(default_s0));
    memcpy(score_text[1], default_s1, sizeof(default_s1));
    memcpy(score_text[2], default_s2, sizeof(default_s2));
    memcpy(score_text[3], default_dr, sizeof(default_dr));

    /* Своего цикла клавиатуры у главного экрана больше нет: управление
     * полностью у контроллера компонентов — ТАБ между полями, правку
     * делает активное поле, Ф1..Ф5 и АП2 — нашему хуку. Из цикла
     * контроллера выход не объявлен ни по какой клавише: у ROM-аппарата
     * возврата некуда (нажал по привычке АП2 — и сиди перезагружай),
     * поэтому АП2 здесь крутит вывод звука, а останавливается
     * проигрывание той же Ф2. */
    drum_init();
    paint_main();
    controller_run(&ctrl);
}
