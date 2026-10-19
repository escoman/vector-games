; Функция: func_check_start_key
; Адрес: 0x017C
; Размер: 27 байт
; Описание: Возвращает 0xFF если нажат SPACE или SHIFT, иначе 0. Читает строку 7
;           матрицы (CALL func_read_keybuf, A=07h), проверяет bit7 (SPACE,
;           активный низкий); иначе IN 01h проверяет bit5 (Shift). Защита входа
;           DCR A / JM — сканирует только при A==0. Используется опросом заставки.

func_check_start_key:
    DCR A                       ; 0x017C
    JM loc_0182                 ; 0x017D
    XRA A                       ; 0x0180
    RET                         ; 0x0181
loc_0182:
    MVI A, 07h                  ; 0x0182
    CALL func_read_keybuf       ; 0x0184
    ANI 80h                     ; 0x0187
    JZ loc_0195                 ; 0x0189
    IN 01h                      ; 0x018C
    ANI 20h                     ; 0x018E
    JZ loc_0195                 ; 0x0190
    XRA A                       ; 0x0193
    RET                         ; 0x0194
loc_0195:
    CMA                         ; 0x0195
    RET                         ; 0x0196
