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
;
; Только 8080-инструкции: без jr/djnz и без префиксов CB/DD/ED/FD.
;

        SECTION code_clib
        PUBLIC  _graph_put_char_512
        PUBLIC  _graph_print_512

_graph_put_char_512:
        ; --- читаем аргументы со стека, не меняя SP ---
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)
        ld      (tmp_color), a          ; цвет
        ld      hl, 4
        add     hl, sp
        ld      a, (hl)
        ld      (tmp_ch), a             ; символ
        ld      hl, 6
        add     hl, sp
        ld      a, (hl)
        ld      (tmp_y), a              ; y
        ld      hl, 8
        add     hl, sp
        ld      a, (hl)
        ld      (tmp_x), a              ; x
        jp      draw_char_512

; ---------------------------------------------------------------
; Внутренняя отрисовка одного символа 16x8.
; ---------------------------------------------------------------
draw_char_512:
        ; --- поиск глифа: E = индекс; нет в таблице -> пробел ---
        ld      a, (tmp_ch)
        ld      c, a                    ; C = искомый символ
        ld      hl, font_chars_512
        ld      e, 0
find_loop_512:
        ld      a, (hl)
        or      a
        jp      z, char_not_found_512   ; терминатор: символа нет
        cp      c
        jp      z, glyph_found_512
        inc     hl
        inc     e
        jp      find_loop_512
char_not_found_512:
        ld      e, 0                    ; неизвестный символ -> пробел
glyph_found_512:
        ld      h, 0
        ld      l, e
        ; индекс * 16 (16 байт на глиф)
        add     hl, hl                  ; *2
        add     hl, hl                  ; *4
        add     hl, hl                  ; *8
        add     hl, hl                  ; *16
        ld      de, font16x8
        add     hl, de                  ; HL = указатель на 16 байт глифа
        ld      a, l
        ld      (tmp_glyph), a
        ld      a, h
        ld      (tmp_glyph + 1), a

        ; --- стартовый адрес для чётных пикселей (E000h) ---
        ; Адрес: 0xE000 + char_x * 0x100 + (255 - y)
        ld      a, (tmp_x)
        add     a, 0xE0                 ; A = 0xE0 + char_x
        ld      h, a                    ; H = 0xE0 + char_x
        ld      a, (tmp_y)
        ld      e, a                    ; E = y
        ld      a, 255
        sub     e                       ; A = 255 - y
        ld      l, a                    ; L = смещение строки
        ; HL = базовый адрес для чётных пикселей (E000h)

        ; --- отрисовка 8 строк чётных пикселей в E000h ---
        ld      a, (tmp_color)
        ld      c, a                    ; C = цвет
        ld      a, c
        and     1                       ; проверяем bit0 цвета
        jp      z, skip_even            ; если bit0=0, пропускаем чётные

        push    hl
        ld      a, (tmp_glyph)          ; указатель глифа
        ld      e, a
        ld      a, (tmp_glyph + 1)
        ld      d, a
        ; --- рисуем 8 строк чётных пикселей (байты 0,2,4,6,8,10,12,14) ---
        ld      a, (de)                 ; байт 0 (чётные, строка 0)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de                      ; пропускаем нечётный байт
        ld      a, (de)                 ; байт 2 (чётные, строка 1)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 4 (чётные, строка 2)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 6 (чётные, строка 3)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 8 (чётные, строка 4)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 10 (чётные, строка 5)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 12 (чётные, строка 6)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 14 (чётные, строка 7)
        ld      (hl), a
        pop     hl

skip_even:
        ; --- переход к нечётным пикселям (A000h) ---
        ; Меняем H с 0xE0+char_x на 0xA0+char_x
        ld      a, h
        sub     0x40                    ; 0xE0 - 0x40 = 0xA0
        ld      h, a
        ; HL = базовый адрес для нечётных пикселей (A000h)

        ; --- отрисовка 8 строк нечётных пикселей в A000h ---
        ld      a, c
        and     1                       ; проверяем bit0 цвета
        jp      z, skip_odd             ; если bit0=0, пропускаем нечётные

        push    hl
        ld      a, (tmp_glyph)          ; указатель глифа
        ld      e, a
        ld      a, (tmp_glyph + 1)
        ld      d, a
        inc     de                      ; пропускаем чётный байт
        ; --- рисуем 8 строк нечётных пикселей (байты 1,3,5,7,9,11,13,15) ---
        ld      a, (de)                 ; байт 1 (нечётные, строка 0)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 3 (нечётные, строка 1)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 5 (нечётные, строка 2)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 7 (нечётные, строка 3)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 9 (нечётные, строка 4)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 11 (нечётные, строка 5)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 13 (нечётные, строка 6)
        ld      (hl), a
        dec     hl
        inc     de
        inc     de
        ld      a, (de)                 ; байт 15 (нечётные, строка 7)
        ld      (hl), a
        pop     hl

skip_odd:
        ret

; ---------------------------------------------------------------
; void graph_print_512(x, y, s, color)
; ---------------------------------------------------------------
_graph_print_512:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)
        ld      (tmp_color), a          ; цвет
        ld      hl, 4
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        ld      a, e                    ; DE = указатель строки
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
print_loop_512:
        ld      a, (de)
        or      a
        jp      z, print_done_512       ; конец строки
        inc     de
        ld      c, a                    ; символ
        ld      a, e
        ld      (tmp_s), a
        ld      a, d
        ld      (tmp_s + 1), a
        ld      a, c
        ld      (tmp_ch), a
        call    draw_char_512
        ld      a, (tmp_x)
        inc     a                       ; следующий символ: x += 1
        ld      (tmp_x), a
        ld      a, (tmp_s)
        ld      e, a
        ld      a, (tmp_s + 1)
        ld      d, a
        jp      print_loop_512
print_done_512:
        ret

tmp_x:          defb    0
tmp_y:          defb    0
tmp_ch:         defb    0
tmp_color:      defb    0
tmp_glyph:      defw    0
tmp_s:          defw    0

; ---------------------------------------------------------------
; Шрифт font16x8: 46 глифов по 16 байт.
; Каждая строка: 2 байта (чётные пиксели E000h, нечётные пиксели A000h).
; ---------------------------------------------------------------
font_chars_512:
        defm    " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().,?!@"
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
