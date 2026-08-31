;
; graphpr512t.asm — вывод тонкого текста (символы 4x8) в режиме 512x256.
;
;   void graph_print_512t(unsigned char x, unsigned char y, const char *s,
;                         unsigned char color);
;
; Каждый символ занимает 4 пикселя по горизонтали (одна тетрада байта).
; Два символа размещаются в одном байте: чётный — в левой тетраде (0xF0),
; нечётный — в правой (0x0F).
;
; Шрифт взят из graphpr.asm (8x8), каждая строка разбита на две
; полуплоскости: чётные пиксели (bits 7,5,3,1) и нечётные (bits 6,4,2,0),
; упакованные в левую тетраду (0xF0).
;
; Два символа рисуются в одном столбце:
;   1-й (phase 0,2) — запись напрямую (левая тетрада).
;   2-й (phase 1,3) — сдвиг на 4 вправо + OR (правая тетрада).
; После каждой пары символов колонка сдвигается на 1.
;
; x — колонка (0-63), y — строка (0-255).
; Цвет 0-3: bit0 -> E000h/A000h, bit1 -> C000h/8000h.
;
; Только 8080-инструкции: без jr/djnz и без префиксов CB/DD/ED/FD.
;

; ---------------------------------------------------------------
; pr512t.asm
;
; Тонкий шрифт 4x8 в режиме 512x256.
;
; x    = tetrad-column 0..63
; y    = верхняя строка 0..248
; ch   = ASCII
; color:
;   bit 0 -> E000/A000
;   bit 1 -> C000/8000
;
; Два символа занимают один байт:
;
;   even x -> high nibble
;   odd  x -> low nibble
;
; __z88dk_callee
;
; Только Intel 8080.
; ---------------------------------------------------------------

        SECTION code_clib

        PUBLIC  _graph_put_char_512t
        PUBLIC  _graph_print_512t


; ===============================================================
; graph_put_char_512t(x,y,ch,color)
; ===============================================================

_graph_put_char_512t:

        pop     de              ; return

        pop     hl              ; color
        mov     a, l
        sta     tmp_color_512t

        pop     hl              ; ch
        mov     a, l
        sta     tmp_ch_512t

        pop     hl              ; y
        mov     a, l
        sta     tmp_y_512t

        pop     hl              ; x
        mov     a, l
        sta     tmp_x_512t

        push    de

        call    draw_char_512t
        ret


; ===============================================================
; draw_char_512t
; ===============================================================

draw_char_512t:

        ; -------------------------------------------------------
        ; Проверка координат.
        ; -------------------------------------------------------

        lda     tmp_x_512t
        cpi     64
        jnc     dct512_done

        lda     tmp_y_512t
        cpi     249
        jnc     dct512_done


        ; -------------------------------------------------------
        ; Ищем глиф.
        ; E = index.
        ; -------------------------------------------------------

        lda     tmp_ch_512t
        mov     c, a

        lxi     h, font_chars_512t
        mvi     e, 0

dct512_find:

        mov     a, m
        ora     a
        jz      dct512_not_found

        cmp     c
        jz      dct512_found

        inx     h
        inr     e
        jmp     dct512_find


dct512_not_found:

        mvi     e, 0


dct512_found:

        ; -------------------------------------------------------
        ; DE = font_even_thin + index*8
        ; -------------------------------------------------------

        mvi     d, 0
        mov     l, e
        mvi     h, 0

        dad     h
        dad     h
        dad     h

        lxi     d, font_even_thin
        dad     d

        shld    tmp_fp_512t

        ; -------------------------------------------------------
        ; DE = font_odd_thin + index*8
        ; -------------------------------------------------------

        mov     a, l
        sta     tmp_index_lo_512t

        mov     a, h
        sta     tmp_index_hi_512t

        lhld    tmp_index_lo_512t
        lxi     d, font_odd_thin
        dad     d

        shld    tmp_fp2_512t


        ; =======================================================
        ; Вычисляем физический байт.
        ;
        ; byte column = x / 2
        ;
        ; x=0..31  -> left
        ; x=32..63 -> right
        ; =======================================================

        lda     tmp_x_512t
        mov     c, a

        ; x / 2
        rar
        ani     127
        mov     e, a

        ; -------------------------------------------------------
        ; x < 32 ?
        ; -------------------------------------------------------

        mov     a, c
        cpi     32
        jc      dct512_left

        ; -------------------------------------------------------
        ; RIGHT
        ;
        ; local byte column = x/2 - 16
        ; base:
        ;   bit0 = A000
        ;   bit1 = 8000
        ; -------------------------------------------------------

        mov     a, e
        sui     16
        adi     0A0h
        mov     h, a

        jmp     dct512_addr_done


dct512_left:

        ; -------------------------------------------------------
        ; LEFT
        ;
        ; base:
        ;   bit0 = E000
        ;   bit1 = C000
        ; -------------------------------------------------------

        mov     a, e
        adi     0E0h
        mov     h, a


dct512_addr_done:

        ; L = 255-y
        lda     tmp_y_512t
        cma
        mov     l, a

        shld    tmp_vram_512t


        ; =======================================================
        ; Выбираем тетраду.
        ;
        ; x even -> high nibble
        ; x odd  -> low nibble
        ; =======================================================

        lda     tmp_x_512t
        ani     1
        jnz     dct512_right_nibble

        jmp     dct512_left_nibble


; ===============================================================
; LEFT NIBBLE
; ===============================================================

dct512_left_nibble:

        ; -------------------------------------------------------
        ; color bit0 -> E000/A000
        ; -------------------------------------------------------

        lda     tmp_color_512t
        ani     01h
        jz      dct512_ln_skip0

        lhld    tmp_vram_512t
        xchg
        lhld    tmp_fp_512t
        call    draw_thin_left


dct512_ln_skip0:

        ; -------------------------------------------------------
        ; color bit1 -> C000/8000
        ; -------------------------------------------------------

        lda     tmp_color_512t
        ani     02h
        jz      dct512_done

        lhld    tmp_vram_512t

        lda     tmp_x_512t
        cpi     32
        jc      dct512_ln_c_left

        ; right: A000 -> 8000
        mov     a, h
        sui     20h
        mov     h, a
        jmp     dct512_ln_c_draw


dct512_ln_c_left:

        ; left: E000 -> C000
        mov     a, h
        adi     20h
        mov     h, a


dct512_ln_c_draw:

        xchg
        lhld    tmp_fp_512t
        call    draw_thin_left

        ret


; ===============================================================
; RIGHT NIBBLE
; ===============================================================

dct512_right_nibble:

        ; -------------------------------------------------------
        ; color bit0
        ; -------------------------------------------------------

        lda     tmp_color_512t
        ani     01h
        jz      dct512_rn_skip0

        lhld    tmp_vram_512t
        xchg
        lhld    tmp_fp_512t
        call    draw_thin_right


dct512_rn_skip0:

        ; -------------------------------------------------------
        ; color bit1
        ; -------------------------------------------------------

        lda     tmp_color_512t
        ani     02h
        jz      dct512_done

        lhld    tmp_vram_512t

        lda     tmp_x_512t
        cpi     32
        jc      dct512_rn_c_left

        ; right A000 -> 8000
        mov     a, h
        sui     20h
        mov     h, a
        jmp     dct512_rn_c_draw


dct512_rn_c_left:

        ; left E000 -> C000
        mov     a, h
        adi     20h
        mov     h, a


dct512_rn_c_draw:

        xchg
        lhld    tmp_fp_512t
        call    draw_thin_right

        ret


; ===============================================================
; draw_thin_left
;
; HL = glyph
; DE = VRAM
;
; Заменяем HIGH nibble, LOW сохраняем.
;
;   old = xxxx yyyy
;   new = AAAA yyyy
;
; результат:
;   AAAA yyyy
; ===============================================================

draw_thin_left:

        mvi     b, 8

dtl_loop:

        mov     a, m
        ani     0Fh
        mov     c, a

        ldax    d
        ani     0F0h
        ora     c

        stax    d

        inx     h
        inx     d

        dcr     b
        jnz     dtl_loop

        ret


; ===============================================================
; draw_thin_right
;
; HL = glyph
; DE = VRAM
;
; Заменяем LOW nibble, HIGH сохраняем.
; ===============================================================

draw_thin_right:

        mvi     b, 8

dtr_loop:

        ldax    d
        mov     c, a

        mov     a, c
        ani     0F0h
        mov     c, a

        mov     a, m

        ; source F0 -> 0F
        rrc
        rrc
        rrc
        rrc
        ani     0Fh

        ora     c
        stax    d

        inx     h
        inx     d

        dcr     b
        jnz     dtr_loop

        ret


; ===============================================================
; graph_print_512t
;
; x += 1 после каждого символа.
;
; x = 0..63.
; После x=63 следующий символ уже не выводится.
; ===============================================================

_graph_print_512t:

        pop     de              ; return

        pop     hl              ; color
        mov     a, l
        sta     tmp_color_512t

        pop     hl              ; string
        shld    tmp_s_512t

        pop     hl              ; y
        mov     a, l
        sta     tmp_y_512t

        pop     hl              ; x
        mov     a, l
        sta     tmp_x_512t

        push    de


gp512t_loop:

        lda     tmp_x_512t
        cpi     64
        jnc     gp512t_done

        lhld    tmp_s_512t

        mov     a, m
        ora     a
        jz      gp512t_done

        sta     tmp_ch_512t

        inx     h
        shld    tmp_s_512t

        call    draw_char_512t

        lda     tmp_x_512t
        inr     a
        sta     tmp_x_512t

        jmp     gp512t_loop


gp512t_done:
        ret


; ===============================================================
; Конец draw_char_512t / выход при недопустимых координатах
; ===============================================================

dct512_done:
        ret


; ===============================================================
; Таблица ASCII-символов
; ===============================================================

font_chars_512t:
        defm    " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().,?!@<>=&$#*+%"
        defb    0


; ===============================================================
; Рабочие переменные
; ===============================================================

tmp_x_512t:
        defb    0

tmp_y_512t:
        defb    0

tmp_ch_512t:
        defb    0

tmp_color_512t:
        defb    0

tmp_fp_512t:
        defw    0

tmp_fp2_512t:
        defw    0

tmp_vram_512t:
        defw    0

tmp_s_512t:
        defw    0

tmp_index_lo_512t:
        defb    0

tmp_index_hi_512t:
        defb    0

; ---------------------------------------------------------------
; Символы шрифта (те же, что в graphpr.asm).
; ---------------------------------------------------------------
font_chars_512:
        defm    " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().,?!@<>=&$#*+%"
        defb    0

; ---------------------------------------------------------------
; font_even_thin: 55 глифов по 8 байт.
; Чётные пиксели (bits 7,5,3,1 оригинала) в левой тетраде.
; ---------------------------------------------------------------
font_even_thin:
        ; ' '
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ; 'A'
        defb    0x40, 0x60, 0xA0, 0xA0, 0xE0, 0xA0, 0xA0, 0x00
        ; 'B'
        defb    0xE0, 0x50, 0x50, 0x60, 0x50, 0x50, 0xE0, 0x00
        ; 'C'
        defb    0x60, 0x50, 0x80, 0x80, 0x80, 0x50, 0x60, 0x00
        ; 'D'
        defb    0xE0, 0x60, 0x50, 0x50, 0x50, 0x60, 0xE0, 0x00
        ; 'E'
        defb    0xF0, 0x50, 0x60, 0x60, 0x60, 0x50, 0xF0, 0x00
        ; 'F'
        defb    0xF0, 0x50, 0x60, 0x60, 0x60, 0x40, 0xC0, 0x00
        ; 'G'
        defb    0x60, 0x50, 0x80, 0x80, 0xB0, 0x50, 0x70, 0x00
        ; 'H'
        defb    0xA0, 0xA0, 0xA0, 0xE0, 0xA0, 0xA0, 0xA0, 0x00
        ; 'I'
        defb    0x60, 0x40, 0x40, 0x40, 0x40, 0x40, 0x60, 0x00
        ; 'J'
        defb    0x30, 0x20, 0x20, 0x20, 0xA0, 0xA0, 0x60, 0x00
        ; 'K'
        defb    0xD0, 0x50, 0x60, 0x60, 0x60, 0x50, 0xD0, 0x00
        ; 'L'
        defb    0xC0, 0x40, 0x40, 0x40, 0x50, 0x50, 0xF0, 0x00
        ; 'M'
        defb    0x90, 0xF0, 0xF0, 0xF0, 0x90, 0x90, 0x90, 0x00
        ; 'N'
        defb    0x90, 0xD0, 0xD0, 0xB0, 0xB0, 0x90, 0x90, 0x00
        ; 'O'
        defb    0x60, 0x60, 0x90, 0x90, 0x90, 0x60, 0x60, 0x00
        ; 'P'
        defb    0xE0, 0x50, 0x50, 0x60, 0x40, 0x40, 0xC0, 0x00
        ; 'Q'
        defb    0x60, 0xA0, 0xA0, 0xA0, 0xA0, 0x60, 0x20, 0x00
        ; 'R'
        defb    0xE0, 0x50, 0x50, 0x60, 0x60, 0x50, 0xD0, 0x00
        ; 'S'
        defb    0x60, 0xA0, 0xC0, 0x40, 0x20, 0xA0, 0x60, 0x00
        ; 'T'
        defb    0xE0, 0xC0, 0x40, 0x40, 0x40, 0x40, 0x60, 0x00
        ; 'U'
        defb    0xA0, 0xA0, 0xA0, 0xA0, 0xA0, 0xA0, 0xE0, 0x00
        ; 'V'
        defb    0xA0, 0xA0, 0xA0, 0xA0, 0xA0, 0x60, 0x40, 0x00
        ; 'W'
        defb    0x90, 0x90, 0x90, 0x90, 0xF0, 0xF0, 0x90, 0x00
        ; 'X'
        defb    0x90, 0x90, 0x60, 0x60, 0x60, 0x60, 0x90, 0x00
        ; 'Y'
        defb    0xA0, 0xA0, 0xA0, 0x60, 0x40, 0x40, 0x60, 0x00
        ; 'Z'
        defb    0xF0, 0x90, 0xA0, 0x20, 0x50, 0x50, 0xF0, 0x00
        ; '0'
        defb    0x60, 0x90, 0xB0, 0xB0, 0xD0, 0xD0, 0x60, 0x00
        ; '1'
        defb    0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0xE0, 0x00
        ; '2'
        defb    0x60, 0xA0, 0x20, 0x60, 0x40, 0xA0, 0xE0, 0x00
        ; '3'
        defb    0x60, 0xA0, 0x20, 0x60, 0x20, 0xA0, 0x60, 0x00
        ; '4'
        defb    0x20, 0x60, 0x60, 0xA0, 0xF0, 0x20, 0x30, 0x00
        ; '5'
        defb    0xE0, 0x80, 0xE0, 0x20, 0x20, 0xA0, 0x60, 0x00
        ; '6'
        defb    0x60, 0x40, 0x80, 0xE0, 0xA0, 0xA0, 0x60, 0x00
        ; '7'
        defb    0xE0, 0xA0, 0x20, 0x20, 0x40, 0x40, 0x40, 0x00
        ; '8'
        defb    0x60, 0xA0, 0xA0, 0x60, 0xA0, 0xA0, 0x60, 0x00
        ; '9'
        defb    0x60, 0xA0, 0xA0, 0x60, 0x20, 0x20, 0x40, 0x00
        ; '-'
        defb    0x00, 0x00, 0x00, 0xE0, 0x00, 0x00, 0x00, 0x00
        ; ':'
        defb    0x00, 0x40, 0x40, 0x00, 0x00, 0x40, 0x40, 0x00
        ; '('
        defb    0x20, 0x40, 0x40, 0x40, 0x40, 0x40, 0x20, 0x00
        ; ')'
        defb    0x40, 0x40, 0x20, 0x20, 0x20, 0x40, 0x40, 0x00
        ; '.'
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x40, 0x00
        ; ','
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x40, 0x40
        ; '?'
        defb    0x60, 0xA0, 0x20, 0x20, 0x40, 0x00, 0x40, 0x00
        ; '!'
        defb    0x40, 0x40, 0x40, 0x40, 0x40, 0x00, 0x40, 0x00
        ; '@'
        defb    0x00, 0x60, 0x10, 0x30, 0x10, 0x30, 0x00, 0x60
        ; '<'
        defb    0x60, 0xC0, 0xC0, 0xC0, 0x60, 0x60, 0x30, 0x00
        ; '>'
        defb    0xC0, 0x60, 0x60, 0x30, 0x30, 0x60, 0xC0, 0x00
        ; '='
        defb    0x00, 0x00, 0xE0, 0x00, 0xE0, 0x00, 0x00, 0x00
        ; '&'
        defb    0x40, 0x40, 0x40, 0x60, 0x90, 0x40, 0x40, 0x00
        ; '$'
        defb    0x40, 0x60, 0x80, 0x60, 0x20, 0xE0, 0x40, 0x00
        ; '#'
        defb    0x60, 0x60, 0xE0, 0x60, 0xE0, 0x60, 0x60, 0x00
        ; '*'
        defb    0x00, 0x40, 0x60, 0xE0, 0x60, 0x40, 0x00, 0x00
        ; '+'
        defb    0x00, 0x40, 0x40, 0x40, 0x40, 0x40, 0x00, 0x00
        ; '%'
        defb    0xC0, 0xC0, 0x20, 0x20, 0x40, 0xC0, 0xC0, 0x00

; ---------------------------------------------------------------
; font_odd_thin: 55 глифов по 8 байт.
; Нечётные пиксели (bits 6,4,2,0 оригинала) в левой тетраде.
; ---------------------------------------------------------------
font_odd_thin:
        ; ' '
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ; 'A'
        defb    0x40, 0xC0, 0xA0, 0xA0, 0xE0, 0xA0, 0xA0, 0x00
        ; 'B'
        defb    0xE0, 0xA0, 0xA0, 0xE0, 0xA0, 0xA0, 0xE0, 0x00
        ; 'C'
        defb    0x60, 0xA0, 0x80, 0x80, 0x80, 0xA0, 0x60, 0x00
        ; 'D'
        defb    0xC0, 0xA0, 0xA0, 0xA0, 0xA0, 0xA0, 0xC0, 0x00
        ; 'E'
        defb    0xE0, 0x80, 0x80, 0xC0, 0x80, 0x80, 0xE0, 0x00
        ; 'F'
        defb    0xE0, 0x80, 0x80, 0xC0, 0x80, 0x80, 0xC0, 0x00
        ; 'G'
        defb    0x60, 0xA0, 0x80, 0x80, 0xA0, 0xA0, 0x60, 0x00
        ; 'H'
        defb    0xA0, 0xA0, 0xA0, 0xE0, 0xA0, 0xA0, 0xA0, 0x00
        ; 'I'
        defb    0xC0, 0x40, 0x40, 0x40, 0x40, 0x40, 0xC0, 0x00
        ; 'J'
        defb    0x60, 0x20, 0x20, 0x20, 0xA0, 0xA0, 0xC0, 0x00
        ; 'K'
        defb    0xA0, 0xA0, 0xA0, 0xC0, 0xA0, 0xA0, 0xA0, 0x00
        ; 'L'
        defb    0xC0, 0x80, 0x80, 0x80, 0x80, 0xA0, 0xE0, 0x00
        ; 'M'
        defb    0xA0, 0xA0, 0xE0, 0xE0, 0xE0, 0xA0, 0xA0, 0x00
        ; 'N'
        defb    0xA0, 0xA0, 0xE0, 0xE0, 0xA0, 0xA0, 0xA0, 0x00
        ; 'O'
        defb    0x40, 0xA0, 0xA0, 0xA0, 0xA0, 0xA0, 0x40, 0x00
        ; 'P'
        defb    0xE0, 0xA0, 0xA0, 0xE0, 0x80, 0x80, 0xC0, 0x00
        ; 'Q'
        defb    0xC0, 0xA0, 0xA0, 0xA0, 0xE0, 0xC0, 0x60, 0x00
        ; 'R'
        defb    0xE0, 0xA0, 0xA0, 0xE0, 0xA0, 0xA0, 0xA0, 0x00
        ; 'S'
        defb    0xC0, 0xA0, 0x80, 0xC0, 0x60, 0xA0, 0xC0, 0x00
        ; 'T'
        defb    0xE0, 0x60, 0x40, 0x40, 0x40, 0x40, 0xC0, 0x00
        ; 'U'
        defb    0xA0, 0xA0, 0xA0, 0xA0, 0xA0, 0xA0, 0xE0, 0x00
        ; 'V'
        defb    0xA0, 0xA0, 0xA0, 0xA0, 0xA0, 0xC0, 0x40, 0x00
        ; 'W'
        defb    0xA0, 0xA0, 0xA0, 0xE0, 0xE0, 0xA0, 0xA0, 0x00
        ; 'X'
        defb    0xA0, 0xA0, 0xA0, 0x40, 0x40, 0xA0, 0xA0, 0x00
        ; 'Y'
        defb    0xA0, 0xA0, 0xA0, 0xC0, 0x40, 0x40, 0xC0, 0x00
        ; 'Z'
        defb    0xE0, 0xA0, 0x20, 0x40, 0x40, 0xA0, 0xE0, 0x00
        ; '0'
        defb    0xE0, 0xA0, 0xA0, 0xE0, 0xE0, 0xA0, 0xE0, 0x00
        ; '1'
        defb    0x40, 0xC0, 0x40, 0x40, 0x40, 0x40, 0xE0, 0x00
        ; '2'
        defb    0xC0, 0xA0, 0x20, 0x40, 0x80, 0xA0, 0xE0, 0x00
        ; '3'
        defb    0xC0, 0xA0, 0x20, 0x40, 0x20, 0xA0, 0xC0, 0x00
        ; '4'
        defb    0x60, 0x60, 0xA0, 0xA0, 0xE0, 0x20, 0x60, 0x00
        ; '5'
        defb    0xE0, 0x80, 0xC0, 0x20, 0x20, 0xA0, 0xC0, 0x00
        ; '6'
        defb    0x40, 0x80, 0x80, 0xC0, 0xA0, 0xA0, 0xC0, 0x00
        ; '7'
        defb    0xE0, 0xA0, 0x20, 0x40, 0x40, 0x40, 0x40, 0x00
        ; '8'
        defb    0xC0, 0xA0, 0xA0, 0xC0, 0xA0, 0xA0, 0xC0, 0x00
        ; '9'
        defb    0xC0, 0xA0, 0xA0, 0xE0, 0x20, 0x40, 0xC0, 0x00
        ; '-'
        defb    0x00, 0x00, 0x00, 0xE0, 0x00, 0x00, 0x00, 0x00
        ; ':'
        defb    0x00, 0x40, 0x40, 0x00, 0x00, 0x40, 0x40, 0x00
        ; '('
        defb    0x40, 0x40, 0x80, 0x80, 0x80, 0x40, 0x40, 0x00
        ; ')'
        defb    0x80, 0x40, 0x40, 0x40, 0x40, 0x40, 0x80, 0x00
        ; '.'
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x40, 0x00
        ; ','
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x40, 0x80
        ; '?'
        defb    0xC0, 0xA0, 0x20, 0x40, 0x40, 0x00, 0x40, 0x00
        ; '!'
        defb    0x40, 0x40, 0x40, 0x40, 0x40, 0x00, 0x40, 0x00
        ; '@'
        defb    0x00, 0x60, 0x80, 0xE0, 0xC0, 0xE0, 0x80, 0x60
        ; '<'
        defb    0x60, 0xC0, 0xC0, 0xC0, 0x60, 0x60, 0x30, 0x00
        ; '>'
        defb    0xC0, 0x60, 0x60, 0x30, 0x30, 0x60, 0xC0, 0x00
        ; '='
        defb    0x00, 0x00, 0xE0, 0x00, 0xE0, 0x00, 0x00, 0x00
        ; '&'
        defb    0x40, 0x80, 0x40, 0x60, 0x90, 0x80, 0x40, 0x00
        ; '$'
        defb    0x40, 0xE0, 0xC0, 0xE0, 0x60, 0xE0, 0x40, 0x00
        ; '#'
        defb    0x60, 0x60, 0xE0, 0x60, 0xE0, 0x60, 0x60, 0x00
        ; '*'
        defb    0x40, 0x60, 0x40, 0xE0, 0x40, 0x60, 0x40, 0x00
        ; '+'
        defb    0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x00, 0x00
        ; '%'
        defb    0xC0, 0xC0, 0x40, 0x20, 0x20, 0xC0, 0xC0, 0x00
