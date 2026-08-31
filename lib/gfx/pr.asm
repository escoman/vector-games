;
; graphpr.asm — быстрый вывод текста шрифтом 8x8 (Вектор-06Ц).
;
; Заменяет C-функции graph_put_char и graph_print (graph.c).
;
;   void graph_put_char(unsigned char x, unsigned char y, char ch,
;                       unsigned char color);
;   void graph_print(unsigned char x, unsigned char y, const char *s,
;                    unsigned char color);
;
; Соглашение вызова z88dk classic — по выводу компилятора этих функций
; (zcc -S): аргументы лежат в стеке в 16-битных слотах, значение в
; младшем байте. graph_put_char: color sp+2, ch sp+4, y sp+6, x sp+8;
; graph_print: color sp+2, s sp+4 (слово), y sp+6, x sp+8. Стек чистит
; вызывающий, поэтому функции НЕ трогают SP (никаких push/pop) и
; просто делают ret.
;
; Ячейка 8x8: пиксели глифа — цвет color (0-15), фон ячейки
; затирается. x должно быть кратно 8, y — верхняя строка ячейки.
; Неизвестный символ рисуется пробелом.
;
; Видеопамять: блок символа = (x/8)*256 байт внутри каждой плоскости
; (0x8000 + n*0x2000); строка y блока — по адресу (256-y)&0xFF, строки
; вниз — уменьшение адреса.
;
; Только 8080-инструкции: без jr/djnz и без префиксов CB/DD/ED/FD.
;

        SECTION code_clib
        PUBLIC  _graph_put_char
        PUBLIC  _graph_print

_graph_put_char:
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
        jp      draw_char

; ---------------------------------------------------------------
; Внутренняя отрисовка одного символа: берёт x/y/символ/цвет из
; tmp_x/tmp_y/tmp_ch/tmp_color. SP не трогает, регистры портит.
; ---------------------------------------------------------------
draw_char:
        ; --- поиск глифа: E = индекс; нет в таблице -> пробел ---
        ld      a, (tmp_ch)
        ld      c, a                    ; C = искомый символ
        ld      hl, font_chars
        ld      e, 0
find_loop:
        ld      a, (hl)
        or      a
        jp      z, char_not_found       ; терминатор: символа нет
        cp      c
        jp      z, glyph_found
        inc     hl
        inc     e
        jp      find_loop
char_not_found:
        ld      e, 0                    ; неизвестный символ -> пробел
glyph_found:
        ld      h, 0
        ld      l, e
        add     hl, hl
        add     hl, hl
        add     hl, hl                  ; индекс * 8
        ld      de, font8x8
        add     hl, de                  ; HL = указатель на 8 байт глифа
        ld      a, l
        ld      (tmp_glyph), a          ; глиф рисуется заново в каждой
        ld      a, h                    ; плоскости — указатель помним
        ld      (tmp_glyph + 1), a

        ; --- стартовый адрес: блок (x/8)*256, строка (256-y)&0xFF ---
        ld      a, (tmp_x)
        rrca
        rrca
        rrca
        and     31                      ; A = x/8 (0-31, x кратно 8)
        add     a, 0x80
        ld      h, a                    ; H = плоскость 0 + блок
        ld      a, (tmp_y)
        cpl
        inc     a                       ; A = (256 - y) & 0xFF
        jp      nz, y_ok               ; y=0: 0xFF+1 = 0x00, нужна коррекция
        dec     a                       ; 0x00 -> 0xFF
y_ok:
        ld      l, a                    ; L = смещение верхней строки

        ; --- 4 плоскости: бит цвета 1 -> байт глифа, 0 -> 0 ---
        ; B = маска плоскости: 8, 4, 2, 1; после rrca из 1 получается
        ; 0x80 — признак конца.
        ld      a, (tmp_color)
        ld      c, a                    ; C = цвет (жив до конца)
        ld      b, 8                    ; маска плоскости веса 8
plane_loop:
        push    hl
        ld      a, (tmp_glyph)          ; указатель глифа для плоскости
        ld      e, a
        ld      a, (tmp_glyph + 1)
        ld      d, a
        ld      a, c
        and     b
        jp      z, plane_clear
        ld      a, (de)                 ; строка 0
        ld      (hl), a
        dec     hl
        inc     de
        ld      a, (de)                 ; строка 1
        ld      (hl), a
        dec     hl
        inc     de
        ld      a, (de)                 ; строка 2
        ld      (hl), a
        dec     hl
        inc     de
        ld      a, (de)                 ; строка 3
        ld      (hl), a
        dec     hl
        inc     de
        ld      a, (de)                 ; строка 4
        ld      (hl), a
        dec     hl
        inc     de
        ld      a, (de)                 ; строка 5
        ld      (hl), a
        dec     hl
        inc     de
        ld      a, (de)                 ; строка 6
        ld      (hl), a
        dec     hl
        inc     de
        ld      a, (de)                 ; строка 7
        ld      (hl), a
        pop     hl
        jp      plane_next
plane_clear:
        xor     a
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        pop     hl
plane_next:
        ld      a, l                    ; HL = база следующей плоскости:
        ;add     a, 8                    ; HL уже сдвинут на -8, добавляем
        ld      l, a                    ; +0x2008
        ld      a, h
        adc     a, 0x20
        ld      h, a
        ld      a, b                    ; следующая маска: 8->4->2->1->0x80
        rrca
        ld      b, a
        cp      0x80                    ; прошли плоскость веса 1?
        jp      nz, plane_loop
        ret

; ---------------------------------------------------------------
; void graph_print(x, y, s, color)
; Аргументы читаются один раз; указатель строки живёт в tmp_s
; (draw_char портит DE). SP не трогаем.
; ---------------------------------------------------------------
_graph_print:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)
        ld      (tmp_color), a          ; цвет
        ld      hl, 4
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        ld      a, e                    ; DE = указатель строки;
        ld      (tmp_s), a              ; сразу сохраним в tmp_s
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
print_loop:
        ld      a, (de)
        or      a
        jp      z, print_done           ; конец строки
        inc     de
        ld      c, a                    ; символ (спасаем от перезаписи)
        ld      a, e                    ; сохранить указатель строки
        ld      (tmp_s), a
        ld      a, d
        ld      (tmp_s + 1), a
        ld      a, c
        ld      (tmp_ch), a
        call    draw_char
        ld      a, (tmp_x)
        add     a, 8
        ld      (tmp_x), a              ; следующий символ: x += 8
        ld      a, (tmp_s)              ; восстановить указатель строки
        ld      e, a
        ld      a, (tmp_s + 1)
        ld      d, a
        jp      print_loop
print_done:
        ret

tmp_x:          defb    0
tmp_y:          defb    0
tmp_ch:         defb    0
tmp_color:      defb    0
tmp_glyph:      defw    0
tmp_s:          defw    0

; ---------------------------------------------------------------
; Шрифт font8x8 (IBM VGA, public domain): 46 глифов по 8 байт,
; старший бит байта — левый пиксель. font_chars — строка соответствия.
; ---------------------------------------------------------------
font_chars:
        defm    " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().,?!@"
        defb    0

font8x8:
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 ; ' '
        defb    0x30, 0x78, 0xCC, 0xCC, 0xFC, 0xCC, 0xCC, 0x00 ; 'A'
        defb    0xFC, 0x66, 0x66, 0x7C, 0x66, 0x66, 0xFC, 0x00 ; 'B'
        defb    0x3C, 0x66, 0xC0, 0xC0, 0xC0, 0x66, 0x3C, 0x00 ; 'C'
        defb    0xF8, 0x6C, 0x66, 0x66, 0x66, 0x6C, 0xF8, 0x00 ; 'D'
        defb    0xFE, 0x62, 0x68, 0x78, 0x68, 0x62, 0xFE, 0x00 ; 'E'
        defb    0xFE, 0x62, 0x68, 0x78, 0x68, 0x60, 0xF0, 0x00 ; 'F'
        defb    0x3C, 0x66, 0xC0, 0xC0, 0xCE, 0x66, 0x3E, 0x00 ; 'G'
        defb    0xCC, 0xCC, 0xCC, 0xFC, 0xCC, 0xCC, 0xCC, 0x00 ; 'H'
        defb    0x78, 0x30, 0x30, 0x30, 0x30, 0x30, 0x78, 0x00 ; 'I'
        defb    0x1E, 0x0C, 0x0C, 0x0C, 0xCC, 0xCC, 0x78, 0x00 ; 'J'
        defb    0xE6, 0x66, 0x6C, 0x78, 0x6C, 0x66, 0xE6, 0x00 ; 'K'
        defb    0xF0, 0x60, 0x60, 0x60, 0x62, 0x66, 0xFE, 0x00 ; 'L'
        defb    0xC6, 0xEE, 0xFE, 0xFE, 0xD6, 0xC6, 0xC6, 0x00 ; 'M'
        defb    0xC6, 0xE6, 0xF6, 0xDE, 0xCE, 0xC6, 0xC6, 0x00 ; 'N'
        defb    0x38, 0x6C, 0xC6, 0xC6, 0xC6, 0x6C, 0x38, 0x00 ; 'O'
        defb    0xFC, 0x66, 0x66, 0x7C, 0x60, 0x60, 0xF0, 0x00 ; 'P'
        defb    0x78, 0xCC, 0xCC, 0xCC, 0xDC, 0x78, 0x1C, 0x00 ; 'Q'
        defb    0xFC, 0x66, 0x66, 0x7C, 0x6C, 0x66, 0xE6, 0x00 ; 'R'
        defb    0x78, 0xCC, 0xE0, 0x70, 0x1C, 0xCC, 0x78, 0x00 ; 'S'
        defb    0xFC, 0xB4, 0x30, 0x30, 0x30, 0x30, 0x78, 0x00 ; 'T'
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xFC, 0x00 ; 'U'
        defb    0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0x78, 0x30, 0x00 ; 'V'
        defb    0xC6, 0xC6, 0xC6, 0xD6, 0xFE, 0xEE, 0xC6, 0x00 ; 'W'
        defb    0xC6, 0xC6, 0x6C, 0x38, 0x38, 0x6C, 0xC6, 0x00 ; 'X'
        defb    0xCC, 0xCC, 0xCC, 0x78, 0x30, 0x30, 0x78, 0x00 ; 'Y'
        defb    0xFE, 0xC6, 0x8C, 0x18, 0x32, 0x66, 0xFE, 0x00 ; 'Z'
        defb    0x7C, 0xC6, 0xCE, 0xDE, 0xF6, 0xE6, 0x7C, 0x00 ; '0'
        defb    0x30, 0x70, 0x30, 0x30, 0x30, 0x30, 0xFC, 0x00 ; '1'
        defb    0x78, 0xCC, 0x0C, 0x38, 0x60, 0xCC, 0xFC, 0x00 ; '2'
        defb    0x78, 0xCC, 0x0C, 0x38, 0x0C, 0xCC, 0x78, 0x00 ; '3'
        defb    0x1C, 0x3C, 0x6C, 0xCC, 0xFE, 0x0C, 0x1E, 0x00 ; '4'
        defb    0xFC, 0xC0, 0xF8, 0x0C, 0x0C, 0xCC, 0x78, 0x00 ; '5'
        defb    0x38, 0x60, 0xC0, 0xF8, 0xCC, 0xCC, 0x78, 0x00 ; '6'
        defb    0xFC, 0xCC, 0x0C, 0x18, 0x30, 0x30, 0x30, 0x00 ; '7'
        defb    0x78, 0xCC, 0xCC, 0x78, 0xCC, 0xCC, 0x78, 0x00 ; '8'
        defb    0x78, 0xCC, 0xCC, 0x7C, 0x0C, 0x18, 0x70, 0x00 ; '9'
        defb    0x00, 0x00, 0x00, 0xFC, 0x00, 0x00, 0x00, 0x00 ; '-'
        defb    0x00, 0x30, 0x30, 0x00, 0x00, 0x30, 0x30, 0x00 ; ':'
        defb    0x18, 0x30, 0x60, 0x60, 0x60, 0x30, 0x18, 0x00 ; '('
        defb    0x60, 0x30, 0x18, 0x18, 0x18, 0x30, 0x60, 0x00 ; ')'
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x30, 0x30, 0x00 ; '.'
        defb    0x00, 0x00, 0x00, 0x00, 0x00, 0x30, 0x30, 0x60 ; ','
        defb    0x78, 0xCC, 0x0C, 0x18, 0x30, 0x00, 0x30, 0x00 ; '?'
        defb    0x30, 0x30, 0x30, 0x30, 0x30, 0x00, 0x30, 0x00 ; '!'
        defb    0x00, 0x3C, 0x42, 0x5E, 0x52, 0x5E, 0x40, 0x3C ; '@'
