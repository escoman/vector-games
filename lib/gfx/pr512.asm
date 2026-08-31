;
; graphpr512.asm — вывод текста шрифтом 16x8 в режиме 512x256 (Вектор-06Ц).
;
;   void graph_put_char_512(unsigned char x, unsigned char y, char ch,
;                           unsigned char color);
;   void graph_print_512(unsigned char x, unsigned char y, const char *s,
;                        unsigned char color);
;
; Шрифт 16x8: каждая буква — 16 байт (8 строк по 2 байта).
; Первый байт строки — чётные пиксели (plane 0xE000),
; второй байт — нечётные пиксели (plane 0xA000).
;
; x — позиция символа (0-31), y — строка (0-31).
; Цвет 0-3: bit0 -> E000h/A000h, bit1 -> C000h/8000h.
; Цвет 1 — только первая плоскость, цвет 2 — только вторая,
; цвет 3 — обе плоскости.
;
; Только 8080-инструкции: без jr/djnz и без префиксов CB/DD/ED/FD.
;

; ---------------------------------------------------------------
; pr512.asm
;
; Вывод текста 16x8 в режиме 512x256.
;
; x    = номер символа, 0..31
; y    = верхняя строка символа, 0..248
; ch   = ASCII
; color:
;   bit 0 -> цветовая пара E000/A000
;   bit 1 -> цветовая пара C000/8000
;
; __z88dk_callee
;
; Только Intel 8080.
; ---------------------------------------------------------------

        SECTION code_clib

        PUBLIC  _graph_put_char_512
        PUBLIC  _graph_print_512


; ===============================================================
; graph_put_char_512(x, y, ch, color)
;
; __z88dk_callee
;
; При входе:
;
;   SP -> return
;         color
;         ch
;         y
;         x
;
; POP полностью снимает параметры.
; После этого на стеке остаётся только return address.
; ===============================================================

_graph_put_char_512:

        pop     de              ; return address

        pop     hl              ; color
        mov     a, l
        sta     tmp_color_512

        pop     hl              ; ch
        mov     a, l
        sta     tmp_ch_512

        pop     hl              ; y
        mov     a, l
        sta     tmp_y_512

        pop     hl              ; x
        mov     a, l
        sta     tmp_x_512

        push    de              ; return address

        call    draw_char_512
        ret


; ===============================================================
; draw_char_512
; ===============================================================

draw_char_512:

        ; -------------------------------------------------------
        ; Ищем символ.
        ; E = индекс глифа.
        ; Не найден -> 0 = пробел.
        ; -------------------------------------------------------

        lda     tmp_ch_512
        mov     c, a

        lxi     h, font_chars_512
        mvi     e, 0

dc512_find:

        mov     a, m
        ora     a
        jz      dc512_not_found

        cmp     c
        jz      dc512_found

        inx     h
        inr     e
        jmp     dc512_find


dc512_not_found:

        mvi     e, 0


dc512_found:

        ; -------------------------------------------------------
        ; HL = font16x8 + index * 16
        ; -------------------------------------------------------

        mvi     d, 0
        mov     l, e
        mvi     h, 0

        dad     h              ; *2
        dad     h              ; *4
        dad     h              ; *8
        dad     h              ; *16

        lxi     d, font16x8
        dad     d

        shld    tmp_glyph_512


        ; -------------------------------------------------------
        ; Проверка координат.
        ;
        ; x должен быть 0..31
        ; y должен быть 0..248
        ;
        ; Это одновременно защищает VRAM от выхода за границы.
        ; -------------------------------------------------------

        lda     tmp_x_512
        cpi     32
        jnc     dc512_done

        lda     tmp_y_512
        cpi     249
        jnc     dc512_done


        ; -------------------------------------------------------
        ; Определяем половину экрана.
        ;
        ; x < 16:
        ;   левая половина
        ;
        ; x >= 16:
        ;   правая половина
        ; -------------------------------------------------------

        lda     tmp_x_512
        cpi     16
        jc      dc512_left


        ; =======================================================
        ; ПРАВАЯ ПОЛОВИНА
        ;
        ; local_x = x - 16
        ;
        ; bit0 -> A000
        ; bit1 -> 8000
        ; =======================================================

        sui     16
        adi     0A0h
        mov     h, a

        jmp     dc512_right_addr


dc512_left:

        ; =======================================================
        ; ЛЕВАЯ ПОЛОВИНА
        ;
        ; H = E0 + x
        ;
        ; bit0 -> E000
        ; bit1 -> C000
        ; =======================================================

        adi     0E0h
        mov     h, a


dc512_left_addr:
dc512_right_addr:

        ; -------------------------------------------------------
        ; L = 255 - y
        ; -------------------------------------------------------

        lda     tmp_y_512
        cma
        mov     l, a

        ; -------------------------------------------------------
        ; Сохраняем базовый адрес.
        ; -------------------------------------------------------

        shld    tmp_vram_512

        ; =======================================================
        ; COLOR BIT 0
        ; =======================================================

        lda     tmp_color_512
        ani     01h
        jz      dc512_skip_bit0

        ; -------------------------------------------------------
        ; В зависимости от половины:
        ;
        ; left  -> E000
        ; right -> A000
        ;
        ; Адрес уже подготовлен.
        ; -------------------------------------------------------

        lhld    tmp_vram_512

        ; x >= 16 ?
        lda     tmp_x_512
        cpi     16
        jc      dc512_bit0_left

        ; right -> A000
        lhld    tmp_glyph_512
        xchg
        lhld    tmp_vram_512
        call    draw16_even
        jmp     dc512_skip_bit0


dc512_bit0_left:

        ; left -> E000
        lhld    tmp_glyph_512
        xchg
        lhld    tmp_vram_512
        call    draw16_even


dc512_skip_bit0:

        ; =======================================================
        ; COLOR BIT 1
        ; =======================================================

        lda     tmp_color_512
        ani     02h
        jz      dc512_done

        ; -------------------------------------------------------
        ; Повторно вычисляем базовый адрес.
        ; -------------------------------------------------------

        lda     tmp_x_512
        cpi     16
        jc      dc512_bit1_left

        ; right:
        ; A000 -> 8000
        sui     16
        adi     0A0h
        mov     h, a
        jmp     dc512_bit1_addr


dc512_bit1_left:

        ; left:
        ; E000 -> C000
        lda     tmp_x_512
        adi     0E0h
        mov     h, a


dc512_bit1_addr:

        lda     tmp_y_512
        cma
        mov     l, a

        lhld    tmp_glyph_512
        xchg
        ; HL = VRAM
        lhld    tmp_vram_512

        ; Исправляем H для bit1.
        lda     tmp_x_512
        cpi     16
        jc      dc512_bit1_left_c

        ; right A000 -> 8000
        mov     a, h
        sui     20h
        mov     h, a
        jmp     dc512_bit1_draw


dc512_bit1_left_c:

        ; left E000 -> C000
        mov     a, h
        adi     20h
        mov     h, a


dc512_bit1_draw:

        call    draw16_odd


dc512_done:
        ret


; ===============================================================
; draw16_even
;
; HL = VRAM address
; DE = начало глифа
;
; Используются байты:
;
;   0, 2, 4, 6, 8, 10, 12, 14
;
; После каждой строки:
;
;   VRAM--
;   glyph += 2
; ===============================================================

draw16_even:

        mvi     b, 8

d16_even_loop:

        ldax    d
        mov     m, a

        dcx     h

        inx     d
        inx     d

        dcr     b
        jnz     d16_even_loop

        ret


; ===============================================================
; draw16_odd
;
; HL = VRAM
; DE = начало глифа
;
; Используются байты:
;
;   1, 3, 5, 7, 9, 11, 13, 15
; ===============================================================

draw16_odd:

        inx     d

        mvi     b, 8

d16_odd_loop:

        ldax    d
        mov     m, a

        dcx     h

        inx     d
        inx     d

        dcr     b
        jnz     d16_odd_loop

        ret


; ===============================================================
; graph_print_512(x, y, s, color)
;
; __z88dk_callee
;
; x += 1 после каждого символа.
;
; Если x достигает 32 — прекращаем вывод.
; ===============================================================

_graph_print_512:

        pop     de              ; return
        pop     hl              ; color
        mov     a, l
        sta     tmp_color_512

        pop     hl              ; string
        shld    tmp_s_512

        pop     hl              ; y
        mov     a, l
        sta     tmp_y_512

        pop     hl              ; x
        mov     a, l
        sta     tmp_x_512

        push    de              ; return


gp512_loop:

        ; x >= 32 -> конец строки экрана
        lda     tmp_x_512
        cpi     32
        jnc     gp512_done

        ; s
        lhld    tmp_s_512

        mov     a, m
        ora     a
        jz      gp512_done

        sta     tmp_ch_512

        inx     h
        shld    tmp_s_512

        call    draw_char_512

        lda     tmp_x_512
        inr     a
        sta     tmp_x_512

        jmp     gp512_loop


gp512_done:
        ret


; ---------------------------------------------------------------
; Рабочие переменные
; ---------------------------------------------------------------

tmp_x_512:
        defb    0

tmp_y_512:
        defb    0

tmp_ch_512:
        defb    0

tmp_color_512:
        defb    0

tmp_glyph_512:
        defw    0

tmp_vram_512:
        defw    0

tmp_s_512:
        defw    0

; ---------------------------------------------------------------
; Шрифт font16x8: 55 глифов по 16 байт.
; Каждая строка: 2 байта (чётные пиксели E000h, нечётные пиксели A000h).
; ---------------------------------------------------------------
font_chars_512:
        defm    " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().,?!@<>=&$#*+%"
        defb    0

font16x8:
        ; ' ' (пробел)
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ; 'A'
        defb    0x30, 0x30, 0x78, 0x78, 0xCC, 0xCC, 0xCC, 0xCC
        defb    0xFC, 0xFC, 0xCC, 0xCC, 0xCC, 0xCC, 0x00, 0x00
        ; 'B'
        defb    0xFC, 0xFC, 0x66, 0x66, 0x66, 0x66, 0x7C, 0x7C
        defb    0x66, 0x66, 0x66, 0x66, 0xFC, 0xFC, 0x00, 0x00
        ; 'C'
        defb    0x3C, 0x3C, 0x66, 0x66, 0xC0, 0xC0, 0xC0, 0xC0
        defb    0xC0, 0xC0, 0x66, 0x66, 0x3C, 0x3C, 0x00, 0x00
        ; 'D'
        defb    0xF8, 0xF8, 0x6C, 0x6C, 0x66, 0x66, 0x66, 0x66
        defb    0x66, 0x66, 0x6C, 0x6C, 0xF8, 0xF8, 0x00, 0x00
        ; 'E'
        defb    0xFE, 0xFE, 0x62, 0x62, 0x68, 0x68, 0x78, 0x78
        defb    0x68, 0x68, 0x62, 0x62, 0xFE, 0xFE, 0x00, 0x00
        ; 'F'
        defb    0xFE, 0xFE, 0x62, 0x62, 0x68, 0x68, 0x78, 0x78
        defb    0x68, 0x68, 0x60, 0x60, 0xF0, 0xF0, 0x00, 0x00
        ; 'G'
        defb    0x3C, 0x3C, 0x66, 0x66, 0xC0, 0xC0, 0xC0, 0xC0
        defb    0xCE, 0xCE, 0x66, 0x66, 0x3E, 0x3E, 0x00, 0x00
        ; 'H'
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xFC, 0xFC
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0x00, 0x00
        ; 'I'
        defb    0x78, 0x78, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30
        defb    0x30, 0x30, 0x30, 0x30, 0x78, 0x78, 0x00, 0x00
        ; 'J'
        defb    0x1E, 0x1E, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0x78, 0x78, 0x00, 0x00
        ; 'K'
        defb    0xE6, 0xE6, 0x66, 0x66, 0x6C, 0x6C, 0x78, 0x78
        defb    0x6C, 0x6C, 0x66, 0x66, 0xE6, 0xE6, 0x00, 0x00
        ; 'L'
        defb    0xF0, 0xF0, 0x60, 0x60, 0x60, 0x60, 0x60, 0x60
        defb    0x62, 0x62, 0x66, 0x66, 0xFE, 0xFE, 0x00, 0x00
        ; 'M'
        defb    0xC6, 0xC6, 0xEE, 0xEE, 0xFE, 0xFE, 0xFE, 0xFE
        defb    0xD6, 0xD6, 0xC6, 0xC6, 0xC6, 0xC6, 0x00, 0x00
        ; 'N'
        defb    0xC6, 0xC6, 0xE6, 0xE6, 0xF6, 0xF6, 0xDE, 0xDE
        defb    0xCE, 0xCE, 0xC6, 0xC6, 0xC6, 0xC6, 0x00, 0x00
        ; 'O'
        defb    0x38, 0x38, 0x6C, 0x6C, 0xC6, 0xC6, 0xC6, 0xC6
        defb    0xC6, 0xC6, 0x6C, 0x6C, 0x38, 0x38, 0x00, 0x00
        ; 'P'
        defb    0xFC, 0xFC, 0x66, 0x66, 0x66, 0x66, 0x7C, 0x7C
        defb    0x60, 0x60, 0x60, 0x60, 0xF0, 0xF0, 0x00, 0x00
        ; 'Q'
        defb    0x78, 0x78, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC
        defb    0xDC, 0xDC, 0x78, 0x78, 0x1C, 0x1C, 0x00, 0x00
        ; 'R'
        defb    0xFC, 0xFC, 0x66, 0x66, 0x66, 0x66, 0x7C, 0x7C
        defb    0x6C, 0x6C, 0x66, 0x66, 0xE6, 0xE6, 0x00, 0x00
        ; 'S'
        defb    0x78, 0x78, 0xCC, 0xCC, 0xE0, 0xE0, 0x70, 0x70
        defb    0x1C, 0x1C, 0xCC, 0xCC, 0x78, 0x78, 0x00, 0x00
        ; 'T'
        defb    0xFC, 0xFC, 0xB4, 0xB4, 0x30, 0x30, 0x30, 0x30
        defb    0x30, 0x30, 0x30, 0x30, 0x78, 0x78, 0x00, 0x00
        ; 'U'
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0xFC, 0xFC, 0x00, 0x00
        ; 'V'
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC
        defb    0xCC, 0xCC, 0x78, 0x78, 0x30, 0x30, 0x00, 0x00
        ; 'W'
        defb    0xC6, 0xC6, 0xC6, 0xC6, 0xC6, 0xC6, 0xD6, 0xD6
        defb    0xFE, 0xFE, 0xEE, 0xEE, 0xC6, 0xC6, 0x00, 0x00
        ; 'X'
        defb    0xC6, 0xC6, 0x6C, 0x6C, 0x38, 0x38, 0x38, 0x38
        defb    0x6C, 0x6C, 0xC6, 0xC6, 0xC6, 0xC6, 0x00, 0x00
        ; 'Y'
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0x78, 0x78
        defb    0x30, 0x30, 0x30, 0x30, 0x78, 0x78, 0x00, 0x00
        ; 'Z'
        defb    0xFE, 0xFE, 0xC6, 0xC6, 0x8C, 0x8C, 0x18, 0x18
        defb    0x32, 0x32, 0x66, 0x66, 0xFE, 0xFE, 0x00, 0x00
        ; '0'
        defb    0x7C, 0x7C, 0xC6, 0xC6, 0xCE, 0xCE, 0xDE, 0xDE
        defb    0xF6, 0xF6, 0xE6, 0xE6, 0x7C, 0x7C, 0x00, 0x00
        ; '1'
        defb    0x30, 0x30, 0x70, 0x70, 0x30, 0x30, 0x30, 0x30
        defb    0x30, 0x30, 0x30, 0x30, 0xFC, 0xFC, 0x00, 0x00
        ; '2'
        defb    0x78, 0x78, 0xCC, 0xCC, 0x0C, 0x0C, 0x38, 0x38
        defb    0x60, 0x60, 0xCC, 0xCC, 0xFC, 0xFC, 0x00, 0x00
        ; '3'
        defb    0x78, 0x78, 0xCC, 0xCC, 0x0C, 0x0C, 0x38, 0x38
        defb    0x0C, 0x0C, 0xCC, 0xCC, 0x78, 0x78, 0x00, 0x00
        ; '4'
        defb    0x1C, 0x1C, 0x3C, 0x3C, 0x6C, 0x6C, 0xCC, 0xCC
        defb    0xFE, 0xFE, 0x0C, 0x0C, 0x1E, 0x1E, 0x00, 0x00
        ; '5'
        defb    0xFC, 0xFC, 0xC0, 0xC0, 0xF8, 0xF8, 0x0C, 0x0C
        defb    0x0C, 0x0C, 0xCC, 0xCC, 0x78, 0x78, 0x00, 0x00
        ; '6'
        defb    0x38, 0x38, 0x60, 0x60, 0xC0, 0xC0, 0xF8, 0xF8
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0x78, 0x78, 0x00, 0x00
        ; '7'
        defb    0xFC, 0xFC, 0xCC, 0xCC, 0x0C, 0x0C, 0x18, 0x18
        defb    0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x00, 0x00
        ; '8'
        defb    0x78, 0x78, 0xCC, 0xCC, 0xCC, 0xCC, 0x78, 0x78
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0x78, 0x78, 0x00, 0x00
        ; '9'
        defb    0x78, 0x78, 0xCC, 0xCC, 0xCC, 0xCC, 0x7C, 0x7C
        defb    0x0C, 0x0C, 0x18, 0x18, 0x70, 0x70, 0x00, 0x00
        ; '-'
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFC, 0xFC
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ; ':'
        defb    0x00, 0x00, 0x30, 0x30, 0x30, 0x30, 0x00, 0x00
        defb    0x00, 0x00, 0x30, 0x30, 0x30, 0x30, 0x00, 0x00
        ; '('
        defb    0x18, 0x18, 0x30, 0x30, 0x60, 0x60, 0x60, 0x60
        defb    0x60, 0x60, 0x30, 0x30, 0x18, 0x18, 0x00, 0x00
        ; ')'
        defb    0x60, 0x60, 0x30, 0x30, 0x18, 0x18, 0x18, 0x18
        defb    0x18, 0x18, 0x30, 0x30, 0x60, 0x60, 0x00, 0x00
        ; '.'
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        defb    0x00, 0x00, 0x30, 0x30, 0x30, 0x30, 0x00, 0x00
        ; ','
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        defb    0x00, 0x00, 0x30, 0x30, 0x30, 0x60, 0x00, 0x00
        ; '?'
        defb    0x78, 0x78, 0xCC, 0xCC, 0x0C, 0x0C, 0x18, 0x18
        defb    0x30, 0x30, 0x00, 0x00, 0x30, 0x30, 0x00, 0x00
        ; '!'
        defb    0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30
        defb    0x30, 0x30, 0x00, 0x00, 0x30, 0x30, 0x00, 0x00
        ; '@'
        defb    0x00, 0x00, 0x3C, 0x3C, 0x42, 0x42, 0x5E, 0x5E
        defb    0x52, 0x52, 0x5E, 0x5E, 0x40, 0x40, 0x3C, 0x3C
        ; '<'
        defb    0x30, 0x30, 0x60, 0x60, 0xC0, 0xC0, 0xC0, 0xC0
        defb    0x60, 0x60, 0x60, 0x60, 0x30, 0x30, 0x00, 0x00
        ; '>'
        defb    0xC0, 0xC0, 0x60, 0x60, 0x60, 0x60, 0x30, 0x30
        defb    0x30, 0x30, 0x60, 0x60, 0xC0, 0xC0, 0x00, 0x00
        ; '='
        defb    0x00, 0x00, 0x00, 0x00, 0xFC, 0xFC, 0x00, 0x00
        defb    0xFC, 0xFC, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ; '&'
        defb    0x30, 0x30, 0x48, 0x48, 0x30, 0x30, 0x56, 0x56
        defb    0x99, 0x99, 0x42, 0x42, 0x3C, 0x3C, 0x00, 0x00
        ; '$'
        defb    0x30, 0x30, 0x7C, 0x7C, 0xC0, 0xC0, 0x78, 0x78
        defb    0x06, 0x06, 0xF8, 0xF8, 0x30, 0x30, 0x00, 0x00
        ; '#'
        defb    0x6C, 0x6C, 0x6C, 0x6C, 0xFE, 0xFE, 0x6C, 0x6C
        defb    0xFE, 0xFE, 0x6C, 0x6C, 0x6C, 0x6C, 0x00, 0x00
        ; '*'
        defb    0x18, 0x18, 0x5A, 0x5A, 0x3C, 0x3C, 0xFF, 0xFF
        defb    0x3C, 0x3C, 0x5A, 0x5A, 0x18, 0x18, 0x00, 0x00
        ; '+'
        defb    0x18, 0x18, 0x30, 0x30, 0x60, 0x60, 0x60, 0x60
        defb    0x30, 0x30, 0x18, 0x18, 0x00, 0x00, 0x00, 0x00
        ; '%'
        defb    0xC6, 0xC6, 0xC6, 0xC6, 0x0C, 0x0C, 0x18, 0x18
        defb    0x30, 0x30, 0x66, 0x66, 0x66, 0x66, 0x00, 0x00
