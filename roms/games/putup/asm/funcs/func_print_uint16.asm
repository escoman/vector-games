; Функция: func_print_uint16
; Адрес: 0x0331
; Размер: 36 байт
; Описание: Печать 16-битного беззнакового числа из (HL) как 5 десятичных цифр.
;           Читает слово в DE; XRA A; STA var_num_leading_zero_flag (сброс флага
;           ведущих нулей); XCHG (значение в HL); 4 раза CALL func_divmod_u16 с
;           дополнительными кодами делителей: 0D8F0h(-10000), 0FC18h(-1000),
;           0FF9Ch(-100), 0FFF6h(-10) — извлекает цифры тысяч/сотен/десятков;
;           MOV A,L (единицы); JMP 0364h — хвост печати цифры (вне RDB).

func_print_uint16:
    MOV E, M                    ; 0x0331
    INX H                       ; 0x0332
    MOV D, M                    ; 0x0333
    XRA A                       ; 0x0334
    STA var_num_leading_zero_flag ; 0x0335
    XCHG                        ; 0x0338
    LXI D, 0D8F0h               ; 0x0339
    CALL func_divmod_u16        ; 0x033C
    LXI D, 0FC18h               ; 0x033F
    CALL func_divmod_u16        ; 0x0342
    LXI D, 0FF9Ch               ; 0x0345
    CALL func_divmod_u16        ; 0x0348
    LXI D, 0FFF6h               ; 0x034B
    CALL func_divmod_u16        ; 0x034E
    MOV A, L                    ; 0x0351
    JMP 0364h                   ; 0x0352 — хвост печати цифры (вне RDB)
