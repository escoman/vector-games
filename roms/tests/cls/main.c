/*
 * scr_cls.c — тест скорости очистки экрана Вектора-06Ц.
 *
 * Замеряем два алгоритма очистки видеопамяти (32 КБ, 8000h-FFFFh)
 * аппаратным таймером КР580ВИ53 (канал 0, тактирование 1.5 МГц).
 *
 * Алгоритм 1 — «классический» (копия graphclr.asm из lib/):
 *   4 плоскости × 32 страницы × 256 байт = 32 КБ записей,
 *   по 8 байт на итерацию с развёрнутым циклом.
 *
 * Алгоритм 2 — «оптимизированный» (PUSH):
 *   SP = 0000h, PUSH HL (HL=0) заполняет 32 КБ (8000h-FFFFh) нулями.
 *   64 × 32 × 8 = 16384 PUSH × 2 байта = 32 КБ.
 *
 * Управление: любая клавиша — запуск следующего теста, ESC — выход.
 */

#include <intrinsic.h>
#include "v06.h"

/* Палитра: 0 — чёрный, 1 — тёмно-серый, 3 — средне-серый,
 * 7 — светло-серый, 15 — белый. Остальные — плавный градиент.
 * Формат байта: 0bBB_GGG_RRR (D0-D2 R, D3-D5 G, D6-D7 B). */
static const unsigned char default_palette[16] = {
    0x00, 0x4A, 0x4A, 0x94, 0x94, 0xB6, 0xB6, 0xDE,
    0xDE, 0xE7, 0xE7, 0xF0, 0xF0, 0xF8, 0xF8, 0xFF
};

/* ================================================================
 *  Ассемблерные вспомогательные функции (8080, только базовый набор).
 *
 *  Определены в #asm-блоках на уровне файла; линкер z88dk делает их
 *  доступными для C через PUBLIC-метки. Вызываются как обычные
 *  C-функции; возвращаемое значение — в HL (16 бит) или L (8 бит).
 * ================================================================ */

#asm
        SECTION code_clib

; ---------------------------------------------------------------
; void init_timer_ffff(void)
;
; Инициализация ВИ53 канал 0: режим 0, 16-битный двоичный,
; счётчик = 0xFFFF. Записывает 3 байта: CW (0x30) в порт 08h,
; затем LSB (0xFF) и MSB (0xFF) в порт 0Bh.
;
; Без аргументов — нет проблем со стеком и calling convention.
; Регистры: портит A.
; ---------------------------------------------------------------
        PUBLIC  _init_timer_ffff

_init_timer_ffff:
        ld      a, 0x30
        out     (0x08), a       ; control: ch0, mode 0, 16-bit binary
        ld      a, 0xFF
        out     (0x0B), a       ; LSB = FF
        out     (0x0B), a       ; MSB = FF (итого 0xFFFF)
        ret

; ---------------------------------------------------------------
; unsigned int read_timer(void)
;
; Защёлкивает текущее значение счётчика канала 0 ВИ53 и считывает
; 16-битный результат. Порядок:
;   1) OUT 08h, 0x20  — latch channel 0 (заморозить значение)
;   2) IN  0Bh         — младший байт (сохраняется в A)
;   3) IN  0Bh         — старший байт (в L)
;   4) A -> H          — результат в HL
;
; Возврат: HL = 16-битный остаток счётчика.
; Тиков потрачено = 0xFFFF - остаток (без учёта переполнения).
; Регистры: портит A, HL.
; ---------------------------------------------------------------
        PUBLIC  _read_timer

_read_timer:
        ld      a, 0x20
        out     (0x08), a       ; latch channel 0
        in      a, (0x0B)       ; младший байт -> A
        ld      l, a
        in      a, (0x0B)       ; старший байт -> A
        ld      h, a            ; HL = результат
        ret

; ---------------------------------------------------------------
; void garbage_fill(void)
;
; Заполняет экран «мусором» для визуализации процесса очистки.
; Заполняет все 32 КБ (4 плоскости по 8 КБ).
; Паттерн: значение = младший байт адреса.
; Регистры: портит A, HL.
; ---------------------------------------------------------------
        PUBLIC  _garbage_fill

_garbage_fill:
        ld      h, 0x80
        ld      l, 0            ; HL = 8000h
gf_loop:
        ld      a, l
        ld      (hl), a         ; паттерн = младший байт адреса
        inc     l
        jp      nz, gf_loop     ; L не обнулился — страница не кончилась
        inc     h               ; следующая страница
        ld      a, h
        cp      0x00            ; дошли до 10000h (= 0000h)?
        jp      nz, gf_loop     ; нет — продолжаем
        ret

; ---------------------------------------------------------------
; void classic_clear(unsigned char color)
;
; Эталонный алгоритм очистки экрана — копия graphclr.asm из lib/.
;
; Четыре плоскости по 8 КБ (веса цвета 8, 4, 2, 1; базы 0x8000,
; 0xA000, 0xC000, 0xE000): плоскость получает 0xFF, если её бит в
; цвете установлен, и 0x00 иначе. Заливка идёт страницами по 256 байт:
; L пробегает страницу и обнуляется на её границе (флаг Z после
; inc l — признак конца страницы), а H после 32 страниц сам выходит
; на базу следующей плоскости (+0x20). Запись 8 байт за итерацию
; разворачивает цикл и гасит накладные расходы переходов.
;
; Регистры: E — цвет, C — маска текущей плоскости (8, 4, 2, 1),
; B — счётчик страниц, HL — текущий адрес, A — байт заливки.
;
; Соглашение вызова z88dk classic: color на sp+2 (16-битный слот,
; значение в младшем байте). Стек чистит вызывающий.
;
; Только 8080-инструкции: без jr/djnz и без префиксов CB/DD/ED/FD.
; ---------------------------------------------------------------
        PUBLIC  _classic_clear

_classic_clear:
        ld      hl, 2
        add     hl, sp
        ld      e, (hl)         ; E = цвет 0-15 (жив до конца заливки)
        ld      c, 8            ; маска плоскости веса 8
        ld      h, 0x80
        ld      l, 0            ; HL = 0x8000, база первой плоскости
cc_plane:
        ld      a, e
        and     c               ; бит цвета текущей плоскости
        ld      a, 0xFF
        jp      nz, cc_fill
        xor     a               ; бит 0 — плоскость заливаем 0x00
cc_fill:
        ld      b, 0x20         ; 32 страницы по 256 байт = 8 КБ
cc_page:
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        jp      nz, cc_page     ; L не обнулился — страница не кончилась
        inc     h               ; следующая страница
        dec     b
        jp      nz, cc_page
        ; плоскость залита; HL уже на базе следующей плоскости
        ld      a, c
        rrca                    ; маска: 8 -> 4 -> 2 -> 1 -> 0x80
        ld      c, a
        cp      0x80            ; из маски 1 получилось 0x80 — всё
        jp      nz, cc_plane
        ret

; ---------------------------------------------------------------
; void optimized_clear(void)
;
; Быстрая очистка экрана через PUSH.
;
; SP = 0000h: PUSH пишет от FFFFh вниз до 8000h (32 КБ).
; HL = 0 — содержимое PUSH (нули).
; 64 × 32 × 8 = 16384 PUSH × 2 байта = 32 КБ.
;
; Важно: PUSH-цикл затирает VRAM (8000h-FFFFh).
; Стек расположен ниже 8000h (startup.asm: SP = 8000h, растёт вниз),
; поэтому адрес возврата и _saved_sp в кодовой секции не страдают.
; После цикла восстанавливаем SP из _saved_sp для корректного ret.
; ---------------------------------------------------------------
        PUBLIC  _optimized_clear

_optimized_clear:
        di                      ; запрет прерываний

        ld      (_saved_sp), sp ; сохранить SP вызывающего (7FFEh)
        ld      sp, 0x0000      ; SP = 0000h, PUSH пишет от FFFFh вниз до 8000h
        ld      hl, 0           ; HL = 0000h — содержимое PUSH
        ld      b, 0x40         ; B = 64 (внешний счётчик)
        ld      c, 0x20         ; C = 0 (внутренний счётчик: 32 по 8 push)
opt_loop:
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        dcr     c               ; C-- (Z=1 при переходе через 0)
        jp      nz, opt_loop    ; 32 × 8 = 256 PUSH-ей за проход
        dcr     b               ; B--
        ld      c, 0x20
        jp      nz, opt_loop    ; 64 прохода × 32 × 8 = 16384 PUSH = 32 КБ

        ld      hl, (_saved_sp) ; восстановить SP вызывающего (7FFEh)
        ld      sp, hl
        ei                      ; разрешение прерываний
        ret

_saved_sp:
        defw    0

#endasm


/* Объявления ассемблерных функций для C. */
extern void         garbage_fill(void);
extern void         classic_clear(unsigned char color);
extern void         optimized_clear(void);
extern void         init_timer_ffff(void);
extern unsigned int read_timer(void);

/* ================================================================
 *  Вспомогательные C-функции
 * ================================================================ */

/* Ожидание кадра через счётчик кадров (startup.asm, 50 Гц). */
static void wait_one_frame(void)
{
    unsigned int start = frame_count;
    while (frame_count == start)
        intrinsic_halt();
}

/* Ожидание нажатия любой клавиши (фронт). */
static void wait_any_key(void)
{
    unsigned char prev = kbd_scan();
    for (;;) {
        wait_one_frame();
        unsigned char key = kbd_scan();
        if (key != 0 && key != prev)
            return;
        prev = key;
    }
}

/* Преобразование 16-битного числа в 4 HEX-символа. */
static void word_to_hex(unsigned int val, char *out)
{
    unsigned char c;
    
    c = (val >> 12) & 0x0F;
    out[0] = (c < 10) ? ('0' + c) : ('A' + c - 10);
    
    c = (val >>  8) & 0x0F;
    out[1] = (c < 10) ? ('0' + c) : ('A' + c - 10);
    
    c = (val >>  4) & 0x0F;
    out[2] = (c < 10) ? ('0' + c) : ('A' + c - 10);
    
    c =  val        & 0x0F;
    out[3] = (c < 10) ? ('0' + c) : ('A' + c - 10);
}

/* Отрисовка экрана результатов. */
static void show_results(unsigned int classic, unsigned int optimized)
{
    static char buf[8];

    graph_set_black_palette();
    gfx_clear(0);
    graph_set_palette(default_palette);

    graph_print(8,   0, "SCREEN CLEAR SPEED TEST", 15u);
    graph_print(8,  16, "------------------------",  7u);

    graph_print(8,  48, "TIMER: VI53 CH0 1.5MHZ", 11u);
    graph_print(8,  64, "MODE: 256X256 16 COL",   11u);
    graph_print(8,  80, "VRAM: 32KB 4 PLANES",    11u);

    graph_print(8, 112, "CLASSIC x100:",       11u);
    word_to_hex(classic, buf);
    buf[4] = '\0';
    graph_print(8, 128, buf, 8u);
    graph_print(56, 128, " TICKS ", 7u);

    graph_print(8, 160, "OPTIMIZED x100:",        11u);
    word_to_hex(optimized, buf);
    buf[4] = '\0';
    graph_print(8, 176, buf, 8u);
    graph_print(56, 176, " TICKS ", 7u);

    graph_print(8, 232, "ESC - EXIT",               7u);
}


/* ================================================================
 *  main
 * ================================================================ */

int main(void)
{
    unsigned int result_classic = 0;
    unsigned int result_optimized = 0;
    unsigned int remainder = 0;

    unsigned int g_result_classic = 0;
    unsigned int g_result_optimized = 0;

    /* Начальная инициализация: чёрный экран, текст-приветствие. */
    graph_set_black_palette();
    gfx_clear(0);
    graph_set_palette(default_palette);

    graph_print(8,   0, "SCREEN CLEAR SPEED TEST", 15u);
    graph_print(8,  16, "------------------------",  7u);
    graph_print(8,  48, "CLASSIC: 4 PLANES",        11u);
    graph_print(8,  64, "  8 BYTES/ITER  32KB",     11u);
    graph_print(8,  96, "OPTIMIZED: PUSH",          11u);
    graph_print(8, 112, "  8 PUSH/ITER  32KB",      11u);
    graph_print(8, 160, "PRESS ANY KEY",            14u);
    graph_print(8, 232, "ESC - EXIT",                7u);

    wait_any_key();

    /* ============================================================
     *  Тест 1: классический алгоритм (копия graphclr.asm).
     * ============================================================ */

    /* Заполняем экран мусором (все 32 КБ VRAM). */
    garbage_fill();

    /* Замер: запускаем алгоритм 100 раз, таймер ВИ53. */
    {
        unsigned int i;
        init_timer_ffff();                  /* счётчик = 0xFFFF */
        for (i = 0; i < 100; i++) {
            classic_clear(0);
        }
        g_result_classic = 0xFFFF - read_timer();
    }

    /* Экран-пауза перед вторым тестом. */
    graph_set_black_palette();
    gfx_clear(0);
    graph_set_palette(default_palette);
    graph_print(8,  80, "TEST 1 DONE",         14u);
    graph_print(8, 128, "PRESS ANY KEY",       14u);
    graph_print(8, 160, "FOR TEST 2 (PUSH)",   11u);

    wait_any_key();

    /* ============================================================
     *  Тест 2: оптимизированный алгоритм (PUSH).
     * ============================================================ */                /* счётчик = 0xFFFF */

    /* Снова заполняем экран мусором. */
    garbage_fill();

    /* Замер: запускаем алгоритм 100 раз, таймер ВИ53. */
    {
        unsigned int i;
        init_timer_ffff();                  /* счётчик = 0xFFFF */
        for (i = 0; i < 100; i++) {
            optimized_clear();
        }
        g_result_optimized = 0xFFFF - read_timer();
    }

    /* ============================================================
     *  Вывод результатов.
     * ============================================================ */

    show_results(g_result_classic, g_result_optimized);

    wait_any_key();

    return 0;
}
