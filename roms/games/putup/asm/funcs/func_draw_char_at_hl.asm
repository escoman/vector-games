; Функция: func_draw_char_at_hl
; Адрес: 0x0145
; Размер: 10 байт
; Описание: Рисует символ A в позиции HL: PUSH H; CALL func_put_char; INX H;
;           SHLD var_text_ptr (сдвиг курсора); POP H; RET. В отличие от
;           func_print_char_at_ptr использует входящий HL как позицию.

func_draw_char_at_hl:
    PUSH H                      ; 0x0145
    CALL func_put_char          ; 0x0146
    INX H                       ; 0x0149
    SHLD var_text_ptr           ; 0x014A
    POP H                       ; 0x014D
    RET                         ; 0x014E
