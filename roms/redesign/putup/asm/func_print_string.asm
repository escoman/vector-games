; Функция: func_print_string
; Адрес: 0x0321
; Размер: 11 байт
; Описание: Печать KOI8-R строки по (HL). Читает байт; INR A проверяет
;           терминатор 0xFF (INR 0xFF -> 00 -> Z); RZ — выход; DCR A
;           восстанавливает код символа; CALL func_print_char_at_ptr;
;           INX H; JMP func_print_string — цикл по строке до 0xFF.

func_print_string:
    MOV A, M                    ; 0x0321
    INR A                       ; 0x0322
    RZ                          ; 0x0323
    DCR A                       ; 0x0324
    CALL func_print_char_at_ptr ; 0x0325
    INX H                       ; 0x0328
    JMP func_print_string       ; 0x0329
