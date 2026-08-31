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

        SECTION code_clib
        PUBLIC  _graph_print_512t

; ---------------------------------------------------------------
; void graph_print_512t(x, y, s, color)
; ---------------------------------------------------------------
_graph_print_512t:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)
        ld      (tmp_color), a          ; цвет
        ld      hl, 4
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        ld      a, e
        ld      (tmp_s), a
        ld      a, d
        ld      (tmp_s + 1), a
        ld      hl, 6
        add     hl, sp
        ld      a, (hl)
        ld      (tmp_y), a              ; y
        ld      hl, 8
        add     hl, sp
        ld      a, (hl)
        ld      (tmp_x), a              ; x
        ld      a, 0                    ; счётчик символов
        ld      (tmp_parity), a
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
        ; tmp_fp = font_even_thin + index*8
        ld      de, font_even_thin
        push    hl
        add     hl, de
        ld      a, l
        ld      (tmp_fp), a
        ld      a, h
        ld      (tmp_fp + 1), a
        pop     hl
        ; tmp_fp2 = font_odd_thin + index*8
        ld      de, font_odd_thin
        add     hl, de
        ld      a, l
        ld      (tmp_fp2), a
        ld      a, h
        ld      (tmp_fp2 + 1), a

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

        ; ====== ЧЁТНАЯ КОЛОНКА: запись напрямую (левая тетрада) ======
        ld      a, (tmp_color)
        ld      c, a                    ; C = цвет

        ; -- bit0 -> E000h (even-plane шрифт) --
        ld      a, c
        and     1
        jp      z, ce_skip0
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a                    ; DE = even-глиф
        call    draw_even_direct
ce_skip0:
        ; -- переход на A000h (odd-plane) --
        ld      a, h
        sub     0x40
        ld      h, a

        ; -- bit0 -> A000h (odd-plane шрифт) --
        ld      a, c
        and     1
        jp      z, ce_skip0b
        ld      a, (tmp_fp2)
        ld      e, a
        ld      a, (tmp_fp2 + 1)
        ld      d, a                    ; DE = odd-глиф
        call    draw_even_direct
ce_skip0b:
        ; -- переход на C000h (bit1, even-plane) --
        ld      a, h
        add     a, 0x20
        ld      h, a

        ; -- bit1 -> C000h (even-plane шрифт) --
        ld      a, c
        and     2
        jp      z, ce_skip1
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_even_direct
ce_skip1:
        ; -- переход на 8000h (bit1, odd-plane) --
        ld      a, h
        sub     0x40
        ld      h, a

        ; -- bit1 -> 8000h (odd-plane шрифт) --
        ld      a, c
        and     2
        jp      z, ce_done
        ld      a, (tmp_fp2)
        ld      e, a
        ld      a, (tmp_fp2 + 1)
        ld      d, a
        call    draw_even_direct
ce_done:
        ret

odd_column:
        ; ====== НЕЧЁТНАЯ КОЛОНКА: сдвиг >> 4 + OR (правая тетрада) ======
        ld      a, (tmp_color)
        ld      c, a                    ; C = цвет

        ; -- bit0 -> E000h (even-plane, shift+OR) --
        ld      a, c
        and     1
        jp      z, co_skip0
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_odd_shift_or
co_skip0:
        ; -- переход на A000h --
        ld      a, h
        sub     0x40
        ld      h, a

        ; -- bit0 -> A000h (odd-plane, shift+OR) --
        ld      a, c
        and     1
        jp      z, co_skip0b
        ld      a, (tmp_fp2)
        ld      e, a
        ld      a, (tmp_fp2 + 1)
        ld      d, a
        call    draw_odd_shift_or
co_skip0b:
        ; -- переход на C000h --
        ld      a, h
        add     a, 0x20
        ld      h, a

        ; -- bit1 -> C000h (even-plane, shift+OR) --
        ld      a, c
        and     2
        jp      z, co_skip1
        ld      a, (tmp_fp)
        ld      e, a
        ld      a, (tmp_fp + 1)
        ld      d, a
        call    draw_odd_shift_or
co_skip1:
        ; -- переход на 8000h --
        ld      a, h
        sub     0x40
        ld      h, a

        ; -- bit1 -> 8000h (odd-plane, shift+OR) --
        ld      a, c
        and     2
        jp      z, co_done
        ld      a, (tmp_fp2)
        ld      e, a
        ld      a, (tmp_fp2 + 1)
        ld      d, a
        call    draw_odd_shift_or
co_done:
        ret

; ---------------------------------------------------------------
; Вспомогательные: 8 строк, HL = адрес экрана, DE = шрифт.
; Все сохраняют HL (база экрана) через push/pop.
; ---------------------------------------------------------------

; Чётная колонка, прямая запись. Данные в левой тетраде (0xF0).
draw_even_direct:
        push    hl
        ld      b, 8
ded_loop:
        ld      a, (de)
        ld      (hl), a
        dec     hl
        inc     de
        dec     b
        ld      a, b
        or      a
        jp      nz, ded_loop
        pop     hl
        ret

; Нечётная колонка: сдвиг на 4 вправо + OR.
draw_odd_shift_or:
        push    hl
        ld      b, 8
doso_loop:
        ld      a, (de)
        rrca
        rrca
        rrca
        rrca
        and     0x0F
        or      (hl)
        ld      (hl), a
        dec     hl
        inc     de
        dec     b
        ld      a, b
        or      a
        jp      nz, doso_loop
        pop     hl
        ret

tmp_x:          defb    0
tmp_y:          defb    0
tmp_ch:         defb    0
tmp_color:      defb    0
tmp_fp:         defw    0
tmp_fp2:        defw    0
tmp_s:          defw    0
tmp_parity:     defb    0

; ---------------------------------------------------------------
; Символы шрифта (те же, что в graphpr.asm).
; ---------------------------------------------------------------
font_chars_512t:
        defm    " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().,?!@<>=&#*+%"
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
