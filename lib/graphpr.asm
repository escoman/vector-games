;
; graphpr.asm — быстрый вывод одного символа шрифтом 8x8 (Вектор-06Ц).
;
; Шаг 2 инкрементальной оптимизации: на ассемблере только
; graph_put_char; graph_print пока остаётся в C (graph.c) и вызывает
; эту функцию для каждого символа строки.
;
;   void graph_put_char(unsigned char x, unsigned char y, char ch,
;                       unsigned char color);
;
; Ячейка 8x8: пиксели глифа — цвет color (0-15), фон ячейки
; затирается. x должно быть кратно 8, y — верхняя строка ячейки.
; Неизвестный символ рисуется пробелом.
;
; Видеопамять: блок символа = (x/8)*256 байт внутри каждой плоскости
; (0x8000 + n*0x2000); строка y блока — по адресу (256-y)&0xFF, строки
; вниз — уменьшение адреса.
;
; Соглашение вызова z88dk classic (проверено по дизассемблеру кода из
; C): аргументы кладутся в стек в порядке объявления — первый глубже
; всех, последний сразу под адресом возврата; каждый занимает 2 байта
; (младший байт значения — по младшему адресу); стек чистит вызывающий,
; поэтому перед ret SP обязан указывать ровно на адрес возврата.
; Только 8080-инструкции (никаких jr/djnz, никаких rlc r).
;

        SECTION code_clib
        PUBLIC  _graph_put_char

; ---------------------------------------------------------------
; Внутренняя отрисовка одного символа. Аргументы в регистрах:
;   C = x (кратно 8), B = y, E = символ, D = цвет.
; Регистры не портит: AF, BC, DE, HL сохраняются в стек.
; ---------------------------------------------------------------
draw_char:
        push    af                      ; сохранить регистры вызывающего
        push    bc
        push    de
        push    hl
        ld      (tmp_xy), bc            ; C = x, B = y
        ld      a, d
        ld      (tmp_color), a          ; цвет

        ; --- поиск глифа в font_chars: DE := индекс, иначе пробел ---
        ld      a, e                    ; A = искомый символ
        ld      hl, font_chars
        ld      de, 0                   ; DE := индекс
find_loop:
        cp      (hl)                    ; cp не портит A
        jp      z, glyph_ok
        inc     hl
        inc     de
        ld      b, a                    ; сохранить символ (B временно)
        ld      a, (hl)                 ; конец таблицы?
        or      a
        jp      z, not_found
        ld      a, b
        jp      find_loop
not_found:
        ld      de, 0                   ; неизвестный символ -> пробел
glyph_ok:
        ex      de, hl                  ; HL = индекс
        add     hl, hl
        add     hl, hl
        add     hl, hl                  ; индекс * 8
        ld      de, font8x8
        add     hl, de
        ex      de, hl                  ; DE = указатель на 8 байт глифа

        ; --- стартовый адрес: блок (x/8)*256, строка (256-y)&0xFF ---
        ld      bc, (tmp_xy)            ; C = x, B = y
        ld      a, c
        rrca
        rrca
        rrca                            ; A = x/8 (0-31, x кратно 8)
        add     a, 0x80
        ld      h, a                    ; H = плоскость 0 + блок
        ld      a, b
        cpl
        inc     a                       ; A = (256 - y) & 0xFF
        ld      l, a                    ; L = смещение верхней строки

        ; --- 4 плоскости: бит цвета 1 -> байт глифа, 0 -> 0 ---
        ; B = маска плоскости: 8, 4, 2, 1; после rrca из 1 получается
        ; 0x80 — признак конца.
        ld      a, (tmp_color)
        ld      c, a                    ; C = цвет (жив до конца)
        ld      b, 8                    ; маска плоскости веса 8
plane_loop:
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
plane_next:
        ld      a, l                    ; HL = база следующей плоскости:
        add     a, 8                    ; HL уже сдвинут на -8, добавляем
        ld      l, a                    ; +0x2008
        ld      a, h
        adc     a, 0x20
        ld      h, a
        ld      a, b                    ; следующая маска: 8->4->2->1->0x80
        rrca
        ld      b, a
        cp      0x80                    ; прошли плоскость веса 1?
        jp      nz, plane_loop
        pop     hl                      ; восстановить регистры вызывающего
        pop     de
        pop     bc
        pop     af
        ret

; ---------------------------------------------------------------
; void graph_put_char(x, y, ch, color)
; Стек при входе (сверху вниз): ret, color, ch, y, x.
; ---------------------------------------------------------------
_graph_put_char:
        pop     hl              ; адрес возврата
        pop     de              ; e = цвет
        ld      a, e
        ld      d, a            ; D = цвет
        pop     bc              ; c = символ
        pop     hl              ; l = y
        ld      b, l            ; B = y
        pop     hl              ; l = x
        ld      a, c
        ld      c, l            ; C = x
        ld      e, a            ; E = символ
        ; --- вернуть SP на адрес возврата (значения не важны) ---
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        call    draw_char
        ret

tmp_xy:         defw    0
tmp_color:      defb    0

; ---------------------------------------------------------------
; Шрифт font8x8 (IBM VGA, public domain): 42 глифа по 8 байт,
; старший бит байта — левый пиксель. font_chars — строка соответствия.
; ---------------------------------------------------------------
font_chars:
        defm    " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:()."
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
