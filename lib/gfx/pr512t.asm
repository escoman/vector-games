;
; graphpr512t.asm — вывод тонкого текста (символы 4x8) в режиме 512x256.
;
;   void graph_put_char_512t(unsigned char x, unsigned char y, const char *s,
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
; Только 8080-инструкции: без jr/djnz и без префиксов CB/DD/ED/FD.
;

        SECTION code_clib
        PUBLIC  _graph_put_char_512t
        PUBLIC  _graph_print_512t

; ---------------------------------------------------------------
; void graph_put_char_512t(x, y, ch, color)
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
_graph_put_char_512t:
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
; void graph_print_512t(x, y, s, color)
; ---------------------------------------------------------------
_graph_print_512t:
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
; Внутренняя отрисовка одного тонкого символа 4x8.
; ---------------------------------------------------------------
draw_char_512t:
        ; --- поиск глифа: E = индекс; нет в таблице -> пробел ---
        ld      a, (tmp_ch)
        ld      c, a                    ; C = искомый символ
        ld      hl, font_chars_512t
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
glyph_found_512t:
        ld      h, 0
        ld      l, e
        add     hl, hl
        add     hl, hl
        add     hl, hl                  ; индекс * 8
        ; tmp_fp = font_thin + index*8
        ld      de, font_thin
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
; Символы шрифта.
; ---------------------------------------------------------------
font_chars_512t:
        defm    " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().,?!@<>=&$#*+%;[]_"
        defb    0

; ---------------------------------------------------------------
; font_thin: 55 глифов по 8 байт.
; Старшая тетрада = чётные пиксели, младшая = нечётные.
; ---------------------------------------------------------------
font_thin:
        ; ' '
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ; 'A'
        defb    0x44, 0x6C, 0xAA, 0xAA, 0xEE, 0xAA, 0xAA, 0x00
        ; 'B'
        defb    0xEE, 0x5A, 0x5A, 0x6E, 0x5A, 0x5A, 0xEE, 0x00
        ; 'C'
        defb    0x66, 0x5A, 0x88, 0x88, 0x88, 0x5A, 0x66, 0x00
        ; 'D'
        defb    0xEC, 0x6A, 0x5A, 0x5A, 0x5A, 0x6A, 0xEC, 0x00
        ; 'E'
        defb    0xFE, 0x58, 0x68, 0x6C, 0x68, 0x58, 0xFE, 0x00
        ; 'F'
        defb    0xFE, 0x58, 0x68, 0x6C, 0x68, 0x48, 0xCC, 0x00
        ; 'G'
        defb    0x66, 0x5A, 0x88, 0x88, 0xBA, 0x5A, 0x76, 0x00
        ; 'H'
        defb    0xAA, 0xAA, 0xAA, 0xEE, 0xAA, 0xAA, 0xAA, 0x00
        ; 'I'
        defb    0x6C, 0x44, 0x44, 0x44, 0x44, 0x44, 0x6C, 0x00
        ; 'J'
        defb    0x36, 0x22, 0x22, 0x22, 0xAA, 0xAA, 0x6C, 0x00
        ; 'K'
        defb    0xDA, 0x5A, 0x6A, 0x6C, 0x6A, 0x5A, 0xDA, 0x00
        ; 'L'
        defb    0xCC, 0x48, 0x48, 0x48, 0x58, 0x5A, 0xFE, 0x00
        ; 'M'
        defb    0x9A, 0xFA, 0xFE, 0xFE, 0x9E, 0x9A, 0x9A, 0x00
        ; 'N'
        defb    0x9A, 0xDA, 0xDE, 0xBE, 0xBA, 0x9A, 0x9A, 0x00
        ; 'O'
        defb    0x64, 0x6A, 0x9A, 0x9A, 0x9A, 0x6A, 0x64, 0x00
        ; 'P'
        defb    0xEE, 0x5A, 0x5A, 0x6E, 0x48, 0x48, 0xCC, 0x00
        ; 'Q'
        defb    0x6C, 0xAA, 0xAA, 0xAA, 0xAE, 0x6C, 0x26, 0x00
        ; 'R'
        defb    0xEE, 0x5A, 0x5A, 0x6E, 0x6A, 0x5A, 0xDA, 0x00
        ; 'S'
        defb    0x6C, 0xAA, 0xC8, 0x4C, 0x26, 0xAA, 0x6C, 0x00
        ; 'T'
        defb    0xEE, 0xC6, 0x44, 0x44, 0x44, 0x44, 0x6C, 0x00
        ; 'U'
        defb    0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xEE, 0x00
        ; 'V'
        defb    0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0x6C, 0x44, 0x00
        ; 'W'
        defb    0x9A, 0x9A, 0x9A, 0x9E, 0xFE, 0xFA, 0x9A, 0x00
        ; 'X'
        defb    0x9A, 0x9A, 0x6A, 0x64, 0x64, 0x6A, 0x9A, 0x00
        ; 'Y'
        defb    0xAA, 0xAA, 0xAA, 0x6C, 0x44, 0x44, 0x6C, 0x00
        ; 'Z'
        defb    0xFE, 0x9A, 0xA2, 0x24, 0x54, 0x5A, 0xFE, 0x00
        ; '0'
        defb    0x6E, 0x9A, 0xBA, 0xBE, 0xDE, 0xDA, 0x6E, 0x00
        ; '1'
        defb    0x44, 0x4C, 0x44, 0x44, 0x44, 0x44, 0xEE, 0x00
        ; '2'
        defb    0x6C, 0xAA, 0x22, 0x64, 0x48, 0xAA, 0xEE, 0x00
        ; '3'
        defb    0x6C, 0xAA, 0x22, 0x64, 0x22, 0xAA, 0x6C, 0x00
        ; '4'
        defb    0x26, 0x66, 0x6A, 0xAA, 0xFE, 0x22, 0x36, 0x00
        ; '5'
        defb    0xEE, 0x88, 0xEC, 0x22, 0x22, 0xAA, 0x6C, 0x00
        ; '6'
        defb    0x64, 0x48, 0x88, 0xEC, 0xAA, 0xAA, 0x6C, 0x00
        ; '7'
        defb    0xEE, 0xAA, 0x22, 0x24, 0x44, 0x44, 0x44, 0x00
        ; '8'
        defb    0x6C, 0xAA, 0xAA, 0x6C, 0xAA, 0xAA, 0x6C, 0x00
        ; '9'
        defb    0x6C, 0xAA, 0xAA, 0x6E, 0x22, 0x24, 0x4C, 0x00
        ; '-'
        defb    0x00, 0x00, 0x00, 0xEE, 0x00, 0x00, 0x00, 0x00
        ; ':'
        defb    0x00, 0x44, 0x44, 0x00, 0x00, 0x44, 0x44, 0x00
        ; '('
        defb    0x24, 0x44, 0x48, 0x48, 0x48, 0x44, 0x24, 0x00
        ; ')'
        defb    0x48, 0x44, 0x24, 0x24, 0x24, 0x44, 0x48, 0x00
        ; '.'
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x44, 0x44, 0x00
        ; ','
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x44, 0x44, 0x48
        ; '?'
        defb    0x6C, 0xAA, 0x22, 0x24, 0x44, 0x00, 0x44, 0x00
        ; '!'
        defb    0x44, 0x44, 0x44, 0x44, 0x44, 0x00, 0x44, 0x00
        ; '@'
        defb    0x6E, 0x90, 0xB6, 0x94, 0xB6, 0x80, 0x6E, 0x00
        ; '<'
        defb    0x12, 0x24, 0x48, 0x80, 0x48, 0x24, 0x12, 0x00
        ; '>'
        defb    0x88, 0x44, 0x22, 0x10, 0x22, 0x44, 0x88, 0x00
        ; '='
        defb    0x00, 0x00, 0xEE, 0x00, 0xEE, 0x00, 0x00, 0x00
        ; '&'
        defb    0x44, 0x28, 0x44, 0x70, 0x0A, 0xA2, 0x5C, 0x00
        ; '$'
        defb    0x04, 0x7E, 0x8C, 0x6E, 0x16, 0xEE, 0x04, 0x00
        ; '#'
        defb    0x60, 0x60, 0xFE, 0x60, 0xFE, 0x60, 0x60, 0x00
        ; '*'
        defb    0x04, 0x0E, 0x64, 0xFE, 0x64, 0x0E, 0x04, 0x00
        ; '+'
        defb    0x04, 0x04, 0x04, 0xFE, 0x04, 0x04, 0x04, 0x00
        ; '%'
        defb    0xD8, 0xC2, 0xE8, 0x04, 0x72, 0x38, 0xB2, 0x00
        ; ';'
        defb    0x00, 0x00, 0x44, 0x44, 0x00, 0x44, 0x44, 0x48
        ; '['
        defb    0x66, 0x44, 0x44, 0x44, 0x44, 0x44, 0x66, 0x00
        ; ']'
        defb    0x66, 0x22, 0x22, 0x22, 0x22, 0x22, 0x66, 0x00
        ; '_'
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF
