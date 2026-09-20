; Функция: func_print_char_at_ptr
; Адрес: 0x01A1
; Размер: 13 байт
; Описание: Вывод символа по курсору: LHLD var_text_ptr; CALL func_put_char;
;           INX H; SHLD var_text_ptr. Печатает символ A и сдвигает курсор.

func_print_char_at_ptr:
    PUSH H                      ; 0x01A1
    LHLD var_text_ptr           ; 0x01A2
    CALL func_put_char          ; 0x01A5
    INX H                       ; 0x01A8
    SHLD var_text_ptr           ; 0x01A9
    POP H                       ; 0x01AC
    RET                         ; 0x01AD
