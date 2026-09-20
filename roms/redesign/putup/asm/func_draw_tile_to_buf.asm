; Функция: func_draw_tile_to_buf
; Адрес: 0x1B87
; Размер: 33 байта
; Описание: Рисует тайл 2x2 в текстовый буфер. Вход: HL = указатель графики
;           тайла (4 байта-глифа), D = колонка, E = строка. Сохраняет BC и HL,
;           через func_coords_to_textbuf получает адрес клетки в буфере (HL),
;           восстанавливает указатель тайла в DE и копирует 4 глифа
;           (func_draw_char_at_hl), перемещаясь по строке (INX D/INX H) и на
;           следующую строку (LXI B,001Fh; DAD B).

func_draw_tile_to_buf:
    PUSH B                      ; 0x1B87
    PUSH H                      ; 0x1B88
    CALL func_coords_to_textbuf ; 0x1B89
    POP D                       ; 0x1B8C
    LDAX D                      ; 0x1B8D
    CALL func_draw_char_at_hl   ; 0x1B8E
    INX D                       ; 0x1B91
    INX H                       ; 0x1B92
    LDAX D                      ; 0x1B93
    CALL func_draw_char_at_hl   ; 0x1B94
    INX D                       ; 0x1B97
    LXI B, 001Fh                ; 0x1B98
    DAD B                       ; 0x1B9B
    LDAX D                      ; 0x1B9C
    CALL func_draw_char_at_hl   ; 0x1B9D
    INX D                       ; 0x1BA0
    INX H                       ; 0x1BA1
    LDAX D                      ; 0x1BA2
    CALL func_draw_char_at_hl   ; 0x1BA3
    POP B                       ; 0x1BA6
    RET                         ; 0x1BA7
