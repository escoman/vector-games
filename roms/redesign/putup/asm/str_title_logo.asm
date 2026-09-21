; Данные: str_title_logo
; Адрес: 0x0A06
; Размер: 193 байта (192 симв. + терминатор 0FFh @0x0AC6)
; Назначение: графика логотипа заставки — ASCII-арт из символа блочной иконки 9Bh
;             (глиф 0x9B из data_glyph_block) и пробелов 20h. Печатается по курсору
;             0x50A0 через func_print_string (0x0321). Нечитаемый текст -> DEFB-дамп.

str_title_logo:  ; byte-exact image slice 0x0A06..0x0AC7 (193 bytes)
    INCBIN "bin/str_title_logo.bin"
