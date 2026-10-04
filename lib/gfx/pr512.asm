;
; graphpr512.asm — вывод текста шрифтом 16x8 в режиме 512x256
; Вектор-06Ц / Intel 8080.
;
;   void gfx_put_char_512(unsigned char x, unsigned char y, char ch,
;                           unsigned char color);
;   void gfx_print_512(unsigned char x, unsigned char y, const char *s,
;                        unsigned char color);
;
; __z88dk_callee.
;
; VRAM:
;   E000-FFFF
;   C000-DFFF
;   A000-BFFF
;   8000-9FFF
;
; color:
;   bit 0 -> E000/A000
;   bit 1 -> C000/8000
;
; Шрифт подключается во время работы: gfx_select_font_512() меняет
; текущий дескриптор (gfx_font_t в v06.h), поэтому gfx_print_512 можно
; напечатать разными шрифтами. До первого вызова работает шрифт из
; ROM (_gfx_font_16x8).
;
; Дескриптор с chars = 0 вместо таблицы имён задаёт прямой индекс по
; коду символа в диапазоне first_code..last_code; коды вне диапазона
; не рисуются совсем (клетка остаётся нетронутой).
;
; Только реальные инструкции Intel 8080.
;

        SECTION code_clib
        PUBLIC  _gfx_put_char_512
        PUBLIC  _gfx_print_512
        PUBLIC  _gfx_select_font_512
        PUBLIC  _gfx_font_16x8


; ---------------------------------------------------------------
; gfx_put_char_512(x,y,ch,color)
;
; __z88dk_callee
;
; На входе:
;
;   SP -> return address
;         color
;         ch
;         y
;         x
;
; ---------------------------------------------------------------

_gfx_put_char_512:

        pop     h
        pop     d
        mov     a,e
        sta     tmp_color

        pop     d
        mov     a,e
        sta     tmp_ch

        pop     d
        mov     a,e
        sta     tmp_y

        pop     d
        mov     a,e
        sta     tmp_x

        push    h

        jmp     draw_char_512


; ---------------------------------------------------------------
; draw_char_512
; ---------------------------------------------------------------

draw_char_512:

        ; x = 0..31

        lda     tmp_x
        cpi     32
        jnc     draw_done_512

        ; y = 0..248

        lda     tmp_y
        cpi     249
        jnc     draw_done_512


        ; -------------------------------------------------------
        ; Текущий шрифт: из дескриптора tmp_font берём адреса
        ; таблицы имён и данных глифов. Один раз на символ.
        ; -------------------------------------------------------

        lhld    tmp_font
        mov     a,m
        sta     tmp_chars
        inx     h
        mov     a,m
        sta     tmp_chars+1
        inx     h
        mov     a,m
        sta     tmp_glyphs
        inx     h
        mov     a,m
        sta     tmp_glyphs+1

        ; -------------------------------------------------------
        ; Поиск индекса глифа.
        ;
        ; chars = 0  -> прямой индекс: E = код - first_code, код вне
        ;               [first_code..last_code] пропускаем без записи
        ;               в VRAM.
        ; chars != 0 -> линейный поиск в таблице имён, неизвестный
        ;               символ = глиф 0 (пробел).
        ; -------------------------------------------------------

        lda     tmp_ch
        mov     c,a

        lhld    tmp_chars
        mov     a,h
        ora     l
        jz      direct_index_512

        mvi     e,0


find_loop_512:

        mov     a,m
        ora     a
        jz      char_not_found_512

        cmp     c
        jz      glyph_found_512

        inx     h
        inr     e

        jmp     find_loop_512


char_not_found_512:

        mvi     e,0
        jmp     glyph_found_512


        ; -------------------------------------------------------
        ; Прямой индекс: границы в словах дескриптора +4 (first_code)
        ; и +6 (last_code), значим младшие байты. Шаг глифа в
        ; дескрипторе не нужен: он известен из формата и равен 16.
        ;
        ; Выход за пределы диапазона – draw_done_512: в VRAM не
        ; пишется ничего, клетка остаётся такой, какой была.
        ; -------------------------------------------------------

direct_index_512:

        lhld    tmp_font
        mov     a,l
        adi     4
        mov     l,a
        mov     a,h
        aci     0
        mov     h,a                     ; HL = first_code

        mov     b,m                     ; B = first_code
        inx     h
        inx     h                       ; HL = last_code
        mov     a,m
        sub     b                       ; макс. индекс = last - first
        jc      draw_done_512           ; first > last: шрифт неверный
        mov     d,a

        lda     tmp_ch
        sub     b                       ; индекс = код - first_code
        jc      draw_done_512           ; код < first_code
        cmp     d
        jz      direct_ok_512           ; код == last_code
        jnc     draw_done_512           ; код > last_code

        ; E = индекс глифа
direct_ok_512:
        mov     e,a


glyph_found_512:

        ; -------------------------------------------------------
        ; HL = font16x8 + index * 16
        ; -------------------------------------------------------

        mvi     d,0
        mov     l,e
        mvi     h,0

        dad     h
        dad     h
        dad     h
        dad     h                       ; HL = индекс * 16

        xchg                            ; DE = смещение
        lhld    tmp_glyphs              ; HL = данные глифов
        xchg                            ; DE = данные, HL = смещение
        dad     d

        shld    tmp_glyph


        ; -------------------------------------------------------
        ; Базовый адрес E000:
        ;
        ; H = E0 + x
        ; L = 255 - y
        ; -------------------------------------------------------

        lda     tmp_x
        adi     0E0h
        mov     h,a

        lda     tmp_y
        mov     e,a

        mvi     a,255
        sub     e
        mov     l,a


        lda     tmp_color
        mov     c,a


        ; =======================================================
        ; bit 0 -> E000
        ; =======================================================

        mov     a,c
        ani     01h
        jz      skip_b0_even

        push    h

        lda     tmp_glyph
        mov     e,a

        lda     tmp_glyph + 1
        mov     d,a

        call    draw_8_even_bytes

        pop     h


skip_b0_even:


        ; =======================================================
        ; bit 0 -> A000
        ; =======================================================

        mov     a,c
        ani     01h
        jz      skip_b0_odd

        push    h

        mov     a,h
        sui     040h
        mov     h,a

        lda     tmp_glyph
        mov     e,a

        lda     tmp_glyph + 1
        mov     d,a

        inx     d

        call    draw_8_even_bytes

        pop     h


skip_b0_odd:


        ; =======================================================
        ; bit 1 -> C000
        ;
        ; ВАЖНО:
        ; E000 -> C000 = -2000h
        ; поэтому H уменьшается на 20h.
        ; =======================================================

        mov     a,c
        ani     02h
        jz      skip_b1_even

        push    h

        mov     a,h
        sui     020h
        mov     h,a

        lda     tmp_glyph
        mov     e,a

        lda     tmp_glyph + 1
        mov     d,a

        call    draw_8_even_bytes

        pop     h


skip_b1_even:


        ; =======================================================
        ; bit 1 -> 8000
        ; =======================================================

        mov     a,c
        ani     02h
        jz      skip_b1_odd

        push    h

        mov     a,h
        sui     060h
        mov     h,a

        lda     tmp_glyph
        mov     e,a

        lda     tmp_glyph + 1
        mov     d,a

        inx     d

        call    draw_8_even_bytes

        pop     h


skip_b1_odd:

        ret


draw_done_512:

        ret


; ---------------------------------------------------------------
; HL = VRAM address
; DE = glyph address
;
; Записываются байты:
;
;   0
;   2
;   4
;   6
;   8
;   10
;   12
;   14
;
; После каждой строки HL уменьшается на 1.
; ---------------------------------------------------------------

draw_8_even_bytes:

        ldax    d
        mov     m,a
        dcx     h
        inx     d
        inx     d

        ldax    d
        mov     m,a
        dcx     h
        inx     d
        inx     d

        ldax    d
        mov     m,a
        dcx     h
        inx     d
        inx     d

        ldax    d
        mov     m,a
        dcx     h
        inx     d
        inx     d

        ldax    d
        mov     m,a
        dcx     h
        inx     d
        inx     d

        ldax    d
        mov     m,a
        dcx     h
        inx     d
        inx     d

        ldax    d
        mov     m,a
        dcx     h
        inx     d
        inx     d

        ldax    d
        mov     m,a
        dcx     h

        ret


; ---------------------------------------------------------------
; gfx_print_512(x,y,s,color)
;
; __z88dk_callee
; ---------------------------------------------------------------

_gfx_print_512:

        pop     h               ; return address

        pop     d               ; color
        mov     a,e
        sta     tmp_color

        pop     d               ; string
        xchg
        shld    tmp_s
        xchg

        pop     d               ; y
        mov     a,e
        sta     tmp_y

        pop     d               ; x
        mov     a,e
        sta     tmp_x

        push    h               ; return address


print_loop_512:

        lda     tmp_x
        cpi     32
        jnc     print_done_512

        lhld    tmp_s
        xchg                    ; DE = pointer

        ldax    d
        ora     a
        jz      print_done_512

        sta     tmp_ch

        inx     d
        xchg
        shld    tmp_s
        xchg

        call    draw_char_512

        lda     tmp_x
        inr     a
        sta     tmp_x

        jmp     print_loop_512


print_done_512:

        ret


; ---------------------------------------------------------------
; gfx_select_font_512(font)
;
; __z88dk_callee
;
; Меняет текущий шрифт: аргумент — адрес дескриптора gfx_font_t
; (v06.h). font = 0 возвращает шрифт, собранный в ROM.
; ---------------------------------------------------------------

_gfx_select_font_512:

        pop     h                       ; return address
        pop     d                       ; DE = адрес дескриптора

        mov     a,e
        ora     d
        jnz     sel_user_512
        lxi     d,_gfx_font_16x8         ; 0 -> шрифт из ROM

sel_user_512:
        xchg                            ; HL = дескриптор, DE = return address
        shld    tmp_font
        xchg                            ; HL = return address обратно
        push    h

        ret


; ---------------------------------------------------------------
; Рабочие переменные
; ---------------------------------------------------------------

tmp_x:
        defb    0

tmp_y:
        defb    0

tmp_ch:
        defb    0

tmp_color:
        defb    0

tmp_glyph:
        defw    0

tmp_s:
        defw    0

; ---------------------------------------------------------------
; Текущий шрифт.
;
; tmp_font   — адрес дескриптора (gfx_font_t); инициализируется
;              при сборке шрифтом из ROM, меняется на ходу.
; tmp_chars, tmp_glyphs — два слова дескриптора, разобранные
;              один раз на символ (см. draw_char_512).
; ---------------------------------------------------------------

tmp_font:
        defw    _gfx_font_16x8

tmp_chars:
        defw    0

tmp_glyphs:
        defw    0


; ---------------------------------------------------------------
; Шрифт 16x8 (режим 512x256).
;
; Данные по умолчанию — fonts/default_16x8.inc. Путь разрешается
; относительно каталога этого файла, передавать -I не нужно.
;
; Игра со своим шрифтом добавляет в SRCS модуль вида
;
;         SECTION code_clib
;         PUBLIC  font_chars_512
;         PUBLIC  font16x8
;
;   font_chars_512:
;         defm    " ..."
;         defb    0
;   font16x8:
;         defb    ...
;
; и собирается с -Ca-DFONT_EXTERNAL_512: тогда вместо INCLUDE обе
; метки объявляются как EXTERN и линкуются из того модуля.
;
; Второй вариант — не заменять шрифт по умолчанию, а добавить
; в ROM ещё один дескриптор и переключать его gfx_select_font_512.
; ---------------------------------------------------------------

        ifdef   FONT_EXTERNAL_512
        EXTERN  font_chars_512
        EXTERN  font16x8
        else
        INCLUDE "fonts/default_16x8.inc"
        endif


; ---------------------------------------------------------------
; Дескриптор шрифта по умолчанию. Структура gfx_font_t (v06.h):
;
;   word 0  адрес таблицы имён   (font_chars_512, 0 = конец)
;   word 1  адрес данных глифов  (font16x8)
;   word 2  первый код символа   (first_code, младший байт)
;   word 3  последний код        (last_code, младший байт)
;
; Слова 2 и 3 работают только при chars = 0 (прямой индекс), поэтому у
; шрифта по умолчанию они заполнены нулём.
;
; ---------------------------------------------------------------

_gfx_font_16x8:
        defw    font_chars_512
        defw    font16x8
        defw    0
        defw    0
