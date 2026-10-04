;
; graphpr512t.asm — вывод тонкого текста (символы 4x8) в режиме 512x256.
;
;   void gfx_put_char_512t(unsigned char x, unsigned char y, const char *s,
;                         unsigned char color);
;
; Каждый символ занимает 4 пикселя по горизонтали (одна тетрада байта).
; Данные объединены: старшая тетрада — чётные пиксели,
; младшая тетрада — нечётные пиксели.
;
; Шрифт: одна таблица font_thin, 8 байт на символ.
; Старшая тетрада каждого байта — чётные пиксели,
; младшая — нечётные.
;
; Отрисовка:
;   Чётная плоскость (E000h/C000h): AND 0xF0, прямая запись.
;   Нечётная плоскость при чётном x: AND 0x0F, сдвиг влево на 4, OR.
;   Нечётная плоскость при нечётном x: AND 0x0F, прямая запись.
;
; x — колонка (0-63), y — строка (0-255).
; Цвет 0-3: bit0 -> E000h/A000h, bit1 -> C000h/8000h.
;
; Шрифт подключается во время работы: gfx_select_font_512t() меняет
; текущий дескриптор (gfx_font_t в v06.h), поэтому gfx_print_512t можно
; напечатать разными шрифтами. До первого вызова работает шрифт из
; ROM (_gfx_font_thin).
;
; Дескриптор с chars = 0 вместо таблицы имён задаёт прямой индекс по
; коду символа в диапазоне first_code..last_code; коды вне диапазона
; не рисуются совсем (клетка остаётся нетронутой).
;
; Только 8080-инструкции: без jr/djnz и без префиксов CB/DD/ED/FD.
;

        SECTION code_clib
        PUBLIC  _gfx_put_char_512t
        PUBLIC  _gfx_print_512t
        PUBLIC  _gfx_select_font_512t
        PUBLIC  _gfx_font_thin

; ---------------------------------------------------------------
; void gfx_put_char_512t(x, y, ch, color)
;
; __z88dk_callee
;
; x = позиция тонкого символа, 0..63.
;   x even -> левая тетрада
;   x odd  -> правая тетрада
;
; y = 0..248 (символ имеет высоту 8 строк).
;
; Стек после CALL:
;   SP+0  = return address
;   SP+2  = x
;   SP+4  = y
;   SP+6  = ch
;   SP+8  = color
;
; Параметры снимаются POP-ами. SP после PUSH адреса возврата
; полностью соответствует __z88dk_callee.
; ---------------------------------------------------------------
_gfx_put_char_512t:
        pop     h                       ; HL = адрес возврата
        pop     d                       ; DE = x
        mov     a, e
        sta     tmp_x_input_512t
        pop     d                       ; DE = y
        mov     a, e
        sta     tmp_y
        pop     d                       ; DE = ch
        mov     a, e
        sta     tmp_ch
        pop     d                       ; DE = color
        mov     a, e
        sta     tmp_color
        push    h                       ; восстановить адрес возврата

        ; Проверка границ.
        lda     tmp_x_input_512t
        cpi     64
        jnc     put_char_done_512t
        lda     tmp_y
        cpi     249
        jnc     put_char_done_512t

        ; parity = x & 1
        lda     tmp_x_input_512t
        ani     1
        sta     tmp_parity

        ; tmp_x = x / 2 = номер байта VRAM (0..31)
        lda     tmp_x_input_512t
        rrca
        ani     31
        sta     tmp_x

        jmp     draw_char_512t

put_char_done_512t:
        ret

; ---------------------------------------------------------------
; void gfx_print_512t(x, y, s, color)
; ---------------------------------------------------------------
_gfx_print_512t:
        ; __z88dk_callee: компилятор пушит x, y, s, color.
        ; На стеке (после CALL):
        ;   SP+0  return address
        ;   SP+2  color      (последний push)
        ;   SP+3  s_low
        ;   SP+4  s_high
        ;   SP+5  y
        ;   SP+6  x          (первый push)
        ;
        ; Снимаем в обратном порядке: color → s → y → x.

        pop     h                       ; HL = адрес возврата

        pop     d                       ; color
        mov     a, e
        sta     tmp_color

        pop     d                       ; s (указатель строки)
        xchg
        shld    tmp_s
        xchg

        pop     d                       ; y
        mov     a, e
        sta     tmp_y

        pop     d                       ; x
        mov     a, e
        sta     tmp_x

        push    h                       ; вернуть адрес возврата

        mvi     a, 0
        sta     tmp_parity

        lhld    tmp_s
        xchg                    ; DE = указатель строки
print_loop_512t:
        ld      a, (de)
        or      a
        jp      z, print_done_512t      ; конец строки
        inc     de
        ld      c, a                    ; символ
        ld      a, e
        ld      (tmp_s), a
        ld      a, d
        ld      (tmp_s + 1), a
        ld      a, c
        ld      (tmp_ch), a
        call    draw_char_512t
        ; если индекс символа нечётный — сдвигаем колонку
        ld      a, (tmp_parity)
        and     1
        jp      z, no_col_advance
        ld      a, (tmp_x)
        inc     a                       ; x += 1 (новая колонка)
        ld      (tmp_x), a
no_col_advance:
        ld      a, (tmp_parity)
        inc     a
        ld      (tmp_parity), a
        ld      a, (tmp_s)
        ld      e, a
        ld      a, (tmp_s + 1)
        ld      d, a
        jp      print_loop_512t
print_done_512t:
        ret

; ---------------------------------------------------------------
; void gfx_select_font_512t(const gfx_font_t *font)
;
; __z88dk_callee
;
; Меняет текущий шрифт: аргумент — адрес дескриптора gfx_font_t
; (v06.h). font = 0 возвращает шрифт, собранный в ROM.
; ---------------------------------------------------------------
_gfx_select_font_512t:
        pop     h                       ; HL = адрес возврата
        pop     d                       ; DE = адрес дескриптора

        mov     a, e
        or      d
        jnz     sel_user_512t
        ld      de, _gfx_font_thin       ; 0 -> шрифт из ROM

sel_user_512t:
        xchg                            ; HL = дескриптор, DE = адрес возврата
        shld    tmp_font
        xchg                            ; HL = адрес возврата обратно
        push    h

        ret

; ---------------------------------------------------------------
; Внутренняя отрисовка одного тонкого символа 4x8.
; ---------------------------------------------------------------
draw_char_512t:
        ; --- текущий шрифт: из дескриптора tmp_font берём адреса
        ;     таблиц; один раз на символ ---
        ld      hl, (tmp_font)
        ld      a, (hl)
        ld      (tmp_chars), a
        inc     hl
        ld      a, (hl)
        ld      (tmp_chars + 1), a
        inc     hl
        ld      a, (hl)
        ld      (tmp_glyphs), a
        inc     hl
        ld      a, (hl)
        ld      (tmp_glyphs + 1), a

        ; --- поиск индекса глифа ------------------------------
        ;
        ; chars = 0  -> прямой индекс: E = код - first_code; код вне
        ;               [first_code..last_code] пропускаем, клетку не
        ;               затираем.
        ; chars != 0 -> линейный поиск в таблице имён, неизвестный
        ;               символ = глиф 0 (пробел).
        ld      a, (tmp_ch)
        ld      c, a                    ; C = искомый символ
        ld      hl, (tmp_chars)
        ld      a, h
        or      l
        jp      z, direct_index_512t
        ld      e, 0
find_loop_512t:
        ld      a, (hl)
        or      a
        jp      z, char_not_found_512t
        cp      c
        jp      z, glyph_found_512t
        inc     hl
        inc     e
        jp      find_loop_512t
char_not_found_512t:
        ld      e, 0                    ; неизвестный -> пробел
        jp      glyph_found_512t

        ; Прямой индекс: границы в словах дескриптора +4 (first_code)
        ; и +6 (last_code), значим младшие байты. Шаг глифа известен
        ; из формата (8 байт) и в дескрипторе не хранится.
direct_index_512t:
        ld      hl, (tmp_font)
        ld      a, l
        adi     4
        ld      l, a
        ld      a, h
        aci     0
        ld      h, a                    ; HL = first_code
        ld      b, (hl)                 ; B = first_code
        inc     hl
        inc     hl                      ; HL = last_code
        ld      a, (hl)
        sub     b                       ; макс. индекс = last - first
        jp      c, put_char_done_512t   ; first > last: шрифт неверный
        ld      d, a
        ld      a, (tmp_ch)
        sub     b                       ; индекс = код - first_code
        jp      c, put_char_done_512t   ; код < first_code: клетка цела
        cp      d
        jp      z, direct_ok_512t       ; код == last_code
        jp      nc, put_char_done_512t  ; код > last_code
direct_ok_512t:
        ld      e, a                    ; E = индекс глифа

glyph_found_512t:
        ld      h, 0
        ld      l, e
        add     hl, hl
        add     hl, hl
        add     hl, hl                  ; индекс * 8
        ; tmp_fp = font_thin + index*8
        ld      de, (tmp_glyphs)
        add     hl, de
        ld      a, l
        ld      (tmp_fp), a
        ld      a, h
        ld      (tmp_fp + 1), a

        ; --- стартовый адрес: 0xE000 + col * 0x100 + (255 - y) ---
        ld      a, (tmp_x)
        add     a, 0xE0
        ld      h, a                    ; H = 0xE0 + col
        ld      a, (tmp_y)
        ld      e, a
        ld      a, 255
        sub     e                       ; A = 255 - y
        ld      l, a                    ; HL = адрес в E000h

        ; --- проверка чётности колонки ---
        ld      a, (tmp_parity)
        and     1
        jp      nz, odd_column

        ; ====== ЧЁТНАЯ КОЛОНКА ======
        ld      a, (tmp_color)
        ld      c, a                    ; C = цвет

        ; -- bit0 -> E000h: even-thin (старшая тетрада) --
        ld      a, c
        and     1
        jp      z, ce_skip0
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a                    ; DE = font_thin + index*8
        call    draw_even_plane
ce_skip0:
        ; -- переход на A000h --
        ld      a, h
        sub     0x40
        ld      h, a

        ; -- bit0 -> A000h: odd-plane (младшая тетрада) --
        ld      a, c
        and     1
        jp      z, ce_skip0b
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_odd_plane_low
ce_skip0b:
        ; -- переход на C000h --
        ld      a, h
        add     a, 0x20
        ld      h, a

        ; -- bit1 -> C000h: even-plane --
        ld      a, c
        and     2
        jp      z, ce_skip1
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_even_plane
ce_skip1:
        ; -- переход на 8000h --
        ld      a, h
        sub     0x40
        ld      h, a

        ; -- bit1 -> 8000h: odd-plane --
        ld      a, c
        and     2
        jp      z, ce_done
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_odd_plane_low
ce_done:
        ret

odd_column:
        ; ====== НЕЧЁТНАЯ КОЛОНКА ======
        ld      a, (tmp_color)
        ld      c, a                    ; C = цвет

        ; -- bit0 -> E000h: even-plane (AND 0xF0, >>4, write) --
        ld      a, c
        and     1
        jp      z, co_skip0
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_even_plane_high
co_skip0:
        ; -- переход на A000h --
        ld      a, h
        sub     0x40
        ld      h, a

        ; -- bit0 -> A000h: odd-plane (AND 0x0F, write) --
        ld      a, c
        and     1
        jp      z, co_skip0b
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_odd_plane_direct
co_skip0b:
        ; -- переход на C000h --
        ld      a, h
        add     a, 0x20
        ld      h, a

        ; -- bit1 -> C000h: even-plane (AND 0xF0, >>4, write) --
        ld      a, c
        and     2
        jp      z, co_skip1
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_even_plane_high
co_skip1:
        ; -- переход на 8000h --
        ld      a, h
        sub     0x40
        ld      h, a

        ; -- bit1 -> 8000h: odd-plane (AND 0x0F, write) --
        ld      a, c
        and     2
        jp      z, co_done
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_odd_plane_direct
co_done:
        ret

; ---------------------------------------------------------------
; Вспомогательные: 8 строк, HL = адрес экрана, DE = шрифт.
; Все сохраняют HL (база экрана) через push/pop.
; Данные в комбинированном формате: старшая тетрада = even,
; младшая тетрада = odd.
; ---------------------------------------------------------------

; Чётная плоскость при чётном x: старшая тетрада (even_data) →
; read-modify-write: сохраняем младшую тетраду через OR.
draw_even_plane:
        push    bc
        push    hl
        ld      b, 8
dep_loop:
        ld      a, (de)
        and     0xF0                    ; новая старшая тетрада
        ld      c, a                    ; C = новая старшая тетрада
        ld      a, (hl)                 ; читаем текущий байт
        and     0x0F                    ; сохраняем младшую тетраду
        or      c                       ; объединяем со старшей
        ld      (hl), a
        dec     hl
        inc     de
        dec     b
        ld      a, b
        or      a
        jp      nz, dep_loop
        pop     hl
        pop     bc
        ret

; Нечётная плоскость при чётном x: младшая тетрада (odd_data) →
; сдвиг влево на 4 бита (rlc ×4) → старшая тетрада → OR.
draw_odd_plane_low:
        push    bc
        push    hl
        ld      b, 8
dopl_loop:
        ld      a, (de)
        rlc
        rlc
        rlc
        rlc
        and     0xF0
        or      (hl)
        ld      (hl), a
        dec     hl
        inc     de
        dec     b
        ld      a, b
        or      a
        jp      nz, dopl_loop
        pop     hl
        pop     bc
        ret

; Чётная плоскость при нечётном x: старшая тетрада → сдвиг вправо
; на 4 (rrca×4, AND 0x0F) → младшая тетрада → read-modify-write.
; C используется как scratch-регистр.
draw_even_plane_high:
        push    bc
        push    hl
        ld      b, 8
deph_loop:
        ld      a, (de)
        rrca
        rrca
        rrca
        rrca
        and     0x0F                    ; новая младшая тетрада
        ld      c, a                    ; C = новая младшая тетрада
        ld      a, (hl)                 ; читаем текущий байт
        and     0xF0                    ; сохраняем старшую тетраду
        or      c                       ; объединяем
        ld      (hl), a
        dec     hl
        inc     de
        dec     b
        ld      a, b
        or      a
        jp      nz, deph_loop
        pop     hl
        pop     bc
        ret

; Нечётная плоскость при нечётном x: младшая тетрада (odd_data) →
; read-modify-write: сохраняем старшую тетраду через OR.
; C используется как scratch-регистр.
draw_odd_plane_direct:
        push    bc
        push    hl
        ld      b, 8
dopd_loop:
        ld      a, (de)
        and     0x0F                    ; новая младшая тетрада
        ld      c, a                    ; C = новая младшая тетрада
        ld      a, (hl)                 ; читаем текущий байт
        and     0xF0                    ; сохраняем старшую тетраду
        or      c                       ; объединяем
        ld      (hl), a
        dec     hl
        inc     de
        dec     b
        ld      a, b
        or      a
        jp      nz, dopd_loop
        pop     hl
        pop     bc
        ret

tmp_x:          defb    0
tmp_x_input_512t: defb    0
tmp_y:          defb    0
tmp_ch:         defb    0
tmp_color:      defb    0
tmp_fp:         defw    0
tmp_s:          defw    0
tmp_parity:     defb    0

; ---------------------------------------------------------------
; Текущий шрифт.
;
; tmp_font   — адрес дескриптора (gfx_font_t); инициализируется
;              при сборке шрифтом из ROM, меняется на ходу.
; tmp_chars, tmp_glyphs — два слова дескриптора, разобранные
;              один раз на символ (см. draw_char_512t).
; ---------------------------------------------------------------

tmp_font:       defw    _gfx_font_thin
tmp_chars:      defw    0
tmp_glyphs:     defw    0

; ---------------------------------------------------------------
; Тонкий шрифт 4x8 (режим 512x256).
;
; Данные по умолчанию — fonts/default_thin.inc. Путь разрешается
; относительно каталога этого файла, передавать -I не нужно.
;
; Игра со своим шрифтом добавляет в SRCS модуль вида
;
;         SECTION code_clib
;         PUBLIC  font_chars_512t
;         PUBLIC  font_thin
;
;   font_chars_512t:
;         defm    " ..."
;         defb    0
;   font_thin:
;         defb    ...
;
; и собирается с -Ca-DFONT_EXTERNAL_512T: тогда вместо INCLUDE обе
; метки объявляются как EXTERN и линкуются из того модуля.
;
; Второй вариант — не заменять шрифт по умолчанию, а добавить
; в ROM ещё один дескриптор и переключать его gfx_select_font_512t.
; ---------------------------------------------------------------

        ifdef   FONT_EXTERNAL_512T
        EXTERN  font_chars_512t
        EXTERN  font_thin
        else
        INCLUDE "fonts/default_thin.inc"
        endif


; ---------------------------------------------------------------
; Дескриптор шрифта по умолчанию. Структура gfx_font_t (v06.h):
;
;   word 0  адрес таблицы имён   (font_chars_512t, 0 = конец)
;   word 1  адрес данных глифов  (font_thin)
;   word 2  первый код символа   (first_code, младший байт)
;   word 3  последний код        (last_code, младший байт)
;
; Слова 2 и 3 работают только при chars = 0 (прямой индекс), поэтому у
; шрифта по умолчанию они заполнены нулём.
;
; ---------------------------------------------------------------

_gfx_font_thin:
        defw    font_chars_512t
        defw    font_thin
        defw    0
        defw    0
