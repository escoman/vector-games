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

; ---------------------------------------------------------------
; void graph_put_char(unsigned char x, unsigned char y,
;                     char ch, unsigned char color)
;   __z88dk_callee
;
; Аргументы на входе:
;
;   fill? Нет.
;
; После CALL стек:
;
;   SP -> return address
;          color
;          ch
;          y
;          x
;
; Забираем всё через POP и возвращаем return address обратно.
;
; x:
;   0..31, номер столбца (каждый столбец = 8 пикселей).
;
; y:
;   0..248, верхняя строка символа.
;
; color:
;   bit 3 -> плоскость E000-FFFF
;   bit 2 -> плоскость C000-DFFF
;   bit 1 -> плоскость A000-BFFF
;   bit 0 -> плоскость 8000-9FFF
;
; Неизвестный символ = пробел.
; ---------------------------------------------------------------

_graph_put_char:

        ; Снимаем return address.
        pop     de

        ; color
        pop     hl
        ld      a, l
        ld      (tmp_color), a

        ; ch
        pop     hl
        ld      a, l
        ld      (tmp_ch), a

        ; y
        pop     hl
        ld      a, l
        ld      (tmp_y), a

        ; x
        pop     hl
        ld      a, l
        ld      (tmp_x), a

        ; Возвращаем return address.
        push    de

        jp      draw_char


; ---------------------------------------------------------------
; draw_char
;
; Внутренняя отрисовка одного символа.
;
; Входные данные:
;
;   tmp_x
;   tmp_y
;   tmp_ch
;   tmp_color
;
; Стек не изменяется.
;
; Регистры:
;
;   HL = адрес текущего байта VRAM
;   DE = указатель текущего глифа
;   C  = color
;   B  = маска плоскости
; ---------------------------------------------------------------

draw_char:

        ; =======================================================
        ; Ищем символ в font_chars.
        ;
        ; E = индекс глифа.
        ; Если символ не найден -> E=0 (пробел).
        ; =======================================================

        ld      a, (tmp_ch)
        ld      c, a

        ld      hl, font_chars
        ld      e, 0

dc_find:
        ld      a, (hl)
        or      a
        jp      z, dc_not_found

        cp      c
        jp      z, dc_found

        inc     hl
        inc     e
        jp      dc_find

dc_not_found:
        ld      e, 0

dc_found:

        ; =======================================================
        ; HL = font8x8 + index * 8
        ; =======================================================

        ld      h, 0
        ld      l, e

        add     hl, hl
        add     hl, hl
        add     hl, hl

        ld      de, font8x8
        add     hl, de

        ; Сохраняем адрес глифа.
        ld      (tmp_glyph), hl

        ; =======================================================
        ; Вычисляем начальный адрес VRAM.
        ;
        ; Плоскость 8000:
        ;
        ;   8000 + x*256 + (255-y)
        ;
        ; Например:
        ;
        ;   x=0,  y=0   -> 80FF
        ;   x=1,  y=0   -> 81FF
        ;   x=0,  y=8   -> 80F7
        ;   x=31, y=248 -> 9F07
        ;
        ; Внутри символа адрес уменьшается на 1.
        ; =======================================================

        ; x (столбец 0-31)
        ld      a, (tmp_x)
        and     31

        ; 80h + номер блока
        add     a, 80h
        ld      h, a

        ; 255 - y
        ld      a, (tmp_y)
        cpl
        ld      l, a

        ; =======================================================
        ; C = color
        ; B = маска текущей плоскости.
        ;
        ; Порядок:
        ;
        ;   B=08 -> E000
        ;   B=04 -> C000
        ;   B=02 -> A000
        ;   B=01 -> 8000
        ; =======================================================

        ld      a, (tmp_color)
        ld      c, a

        ld      b, 08h


; ===============================================================
; Следующая плоскость
; ===============================================================

dc_plane:

        ; -------------------------------------------------------
        ; DE = начало текущего глифа.
        ; -------------------------------------------------------

        ld      de, (tmp_glyph)

        ; -------------------------------------------------------
        ; Проверяем цветовой бит.
        ; -------------------------------------------------------

        ld      a, c
        and     b
        jp      z, dc_clear


        ; =======================================================
        ; Цветной глиф.
        ; Записываем 8 строк.
        ;
        ; После каждой строки:
        ;
        ;   DE++
        ;   HL--
        ; =======================================================

        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl

        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl

        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl

        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl

        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl

        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl

        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl

        ld      a, (de)
        ld      (hl), a
        dec     hl

        jp      dc_plane_next


; ===============================================================
; Нулевая плоскость.
;
; Если соответствующий бит color = 0, фон символа должен
; быть очищен.
; ===============================================================

dc_clear:

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
        dec     hl


; ===============================================================
; Переход к следующей плоскости.
;
; После 8 × DEC HL:
;
;   HL = исходный адрес - 8
;
; Нужно получить:
;
;   исходный адрес + 2000h
;
; поэтому добавляем 2008h.
;
; Используем полноценную 16-битную арифметику с переносом.
; ===============================================================

dc_plane_next:

        ld      a, l
        adi     08h
        ld      l, a

        ld      a, h
        aci     20h
        ld      h, a

        ; -------------------------------------------------------
        ; Следующая маска:
        ;
        ; 08 -> 04
        ; 04 -> 02
        ; 02 -> 01
        ; 01 -> 80
        ;
        ; После обработки плоскости 01 завершаем.
        ; -------------------------------------------------------

        ld      a, b
        rrca
        ld      b, a

        cp      80h
        jp      nz, dc_plane

        ret


; ---------------------------------------------------------------
; void graph_print(unsigned char x, unsigned char y,
;                  const char *s, unsigned char color)
;   __z88dk_callee
;
; Выводит строку символов с шагом 8 пикселей.
;
; DE = указатель строки во время цикла.
; draw_char может портить DE, поэтому указатель сохраняется
; обычным PUSH/POP вокруг CALL.
; ---------------------------------------------------------------

_graph_print:

        ; return address
        pop     de

        ; color
        pop     hl
        ld      a, l
        ld      (tmp_color), a

        ; s
        pop     hl
        ld      (tmp_s), hl

        ; y
        pop     hl
        ld      a, l
        ld      (tmp_y), a

        ; x
        pop     hl
        ld      a, l
        ld      (tmp_x), a

        ; return address обратно
        push    de

        ; DE = строка
        ld      de, (tmp_s)


; ===============================================================
; Цикл вывода строки
; ===============================================================

dp_loop:

        ld      a, (de)
        or      a
        jp      z, dp_done

        ; DE указывает на следующий символ после INC.
        inc     de

        ; Сохраняем указатель строки.
        push    de

        ; Текущий символ.
        ld      (tmp_ch), a

        ; Рисуем.
        call    draw_char

        ; Восстанавливаем указатель строки.
        pop     de

        ; x += 1 (следующий столбец)
        ld      a, (tmp_x)
        inc     a
        ld      (tmp_x), a

        jp      dp_loop


dp_done:
        ret


; ---------------------------------------------------------------
; Временные переменные.
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
; ВАЖНО:
;
; В исходном коде здесь отсутствовал '$'.
; В font8x8 глифы идут в порядке:
;
;   ...
;   &
;   $
;   #
;   *
;   +
;   %
;
; Поэтому font_chars должен содержать '$'.
; ---------------------------------------------------------------

font_chars:
        defm    " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:().,?!@<>=&#$*+%"
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
        defb    0x30, 0x60, 0xC0, 0xC0, 0x60, 0x60, 0x30, 0x00 ; '<'
        defb    0xC0, 0x60, 0x60, 0x30, 0x30, 0x60, 0xC0, 0x00 ; '>'
        defb    0x00, 0x00, 0xFC, 0x00, 0xFC, 0x00, 0x00, 0x00 ; '='
        defb    0x30, 0x48, 0x30, 0x56, 0x99, 0x42, 0x3C, 0x00 ; '&'
        defb    0x30, 0x7C, 0xC0, 0x78, 0x06, 0xF8, 0x30, 0x00 ; '$'
        defb    0x6C, 0x6C, 0xFE, 0x6C, 0xFE, 0x6C, 0x6C, 0x00 ; '#'
        defb    0x18, 0x5A, 0x3C, 0xFF, 0x3C, 0x5A, 0x18, 0x00 ; '*'
        defb    0x18, 0x30, 0x60, 0x60, 0x30, 0x18, 0x00, 0x00 ; '+'
        defb    0xC6, 0xC6, 0x0C, 0x18, 0x30, 0x66, 0x66, 0x00 ; '%'
