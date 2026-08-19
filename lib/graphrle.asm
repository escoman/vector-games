;
; graphrle.asm — быстрая RLE-распаковка заставки (Вектор-06Ц).
;
; Заменяет C-функцию graph_rle_expand (graph.c).
;
;   void graph_rle_expand(const unsigned char *src, unsigned char *dst);
;
; Поток: пары (количество, байт) в порядке адресов видеопамяти,
; терминатор — количество 0 (utils/bmp2inc.py).
;
; Соглашение вызова z88dk classic — по выводу компилятора (zcc -S):
; src на sp+4, dst на sp+2 (16-битные слоты). Стек чистит вызывающий,
; поэтому функция НЕ трогает SP (никаких push/pop) и просто делает ret.
;
; Только 8080-инструкции.
;

        SECTION code_clib
        PUBLIC  _graph_rle_expand

_graph_rle_expand:
        ; --- src (sp+4) -> DE ---
        ld      hl, 4
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        ; --- dst (sp+2) -> HL ---
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)
        inc     hl
        ld      h, (hl)
        ld      l, a                    ; HL = dst
rle_next:
        ld      a, (de)                 ; количество повторов
        inc     de
        or      a
        ret     z                       ; 0 = конец потока
        ld      b, a                    ; B = счётчик повторов
        ld      a, (de)                 ; байт-значение
        inc     de
rle_fill:
        ld      (hl), a
        inc     hl
        dec     b
        jp      nz, rle_fill
        jp      rle_next
