; Данные: str_title_logo
; Адрес: 0x0A06
; Размер: 193 байта (192 симв. + терминатор 0FFh @0x0AC6)
; Назначение: графика логотипа заставки — ASCII-арт из символа блочной иконки 9Bh
;             (глиф 0x9B из data_glyph_block) и пробелов 20h. Печатается по курсору
;             0x50A0 через func_print_string (0x0321). Нечитаемый текст -> DEFB-дамп.

str_title_logo:
    DEFB 20h, 9Bh, 9Bh, 9Bh, 9Bh, 20h, 20h, 9Bh   ; 0x0A06
    DEFB 9Bh, 20h, 20h, 9Bh, 20h, 9Bh, 9Bh, 9Bh   ; 0x0A0E
    DEFB 9Bh, 9Bh, 9Bh, 20h, 9Bh, 9Bh, 20h, 20h   ; 0x0A16
    DEFB 9Bh, 20h, 9Bh, 9Bh, 9Bh, 9Bh, 20h, 20h   ; 0x0A1E
    DEFB 20h, 9Bh, 9Bh, 20h, 20h, 9Bh, 20h, 9Bh   ; 0x0A26
    DEFB 9Bh, 20h, 20h, 9Bh, 20h, 20h, 20h, 9Bh   ; 0x0A2E
    DEFB 9Bh, 20h, 20h, 20h, 9Bh, 9Bh, 20h, 20h   ; 0x0A36
    DEFB 9Bh, 20h, 9Bh, 9Bh, 20h, 20h, 9Bh, 20h   ; 0x0A3E
    DEFB 20h, 9Bh, 9Bh, 20h, 20h, 9Bh, 20h, 9Bh   ; 0x0A46
    DEFB 9Bh, 20h, 20h, 9Bh, 20h, 20h, 9Bh, 9Bh   ; 0x0A4E
    DEFB 9Bh, 9Bh, 20h, 20h, 9Bh, 9Bh, 20h, 20h   ; 0x0A56
    DEFB 9Bh, 20h, 20h, 20h, 9Bh, 9Bh, 20h, 20h   ; 0x0A5E
    DEFB 20h, 9Bh, 9Bh, 20h, 20h, 9Bh, 20h, 9Bh   ; 0x0A66
    DEFB 9Bh, 9Bh, 9Bh, 9Bh, 20h, 20h, 9Bh, 9Bh   ; 0x0A6E
    DEFB 20h, 20h, 9Bh, 20h, 20h, 20h, 9Bh, 9Bh   ; 0x0A76
    DEFB 20h, 20h, 20h, 9Bh, 9Bh, 20h, 20h, 9Bh   ; 0x0A7E
    DEFB 20h, 9Bh, 9Bh, 9Bh, 9Bh, 20h, 20h, 20h   ; 0x0A86
    DEFB 9Bh, 9Bh, 20h, 20h, 20h, 20h, 9Bh, 9Bh   ; 0x0A8E
    DEFB 20h, 20h, 9Bh, 20h, 20h, 20h, 9Bh, 9Bh   ; 0x0A96
    DEFB 20h, 20h, 20h, 9Bh, 9Bh, 20h, 20h, 9Bh   ; 0x0A9E
    DEFB 20h, 9Bh, 9Bh, 20h, 20h, 20h, 20h, 20h   ; 0x0AA6
    DEFB 9Bh, 9Bh, 20h, 20h, 20h, 20h, 20h, 9Bh   ; 0x0AAE
    DEFB 9Bh, 9Bh, 20h, 20h, 20h, 20h, 9Bh, 9Bh   ; 0x0AB6
    DEFB 20h, 20h, 20h, 20h, 9Bh, 9Bh, 9Bh, 20h   ; 0x0ABE
    DEFB 0FFh                                       ; 0x0AC6 терминатор
