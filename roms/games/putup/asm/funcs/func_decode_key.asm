; Функция: func_decode_key
; Адрес: 0x0153
; Размер: 25 байт
; Описание: Декодер кода клавиши. Защита входа DCR A / JM (сканирует только при
;           A==0). Читает строку клавиатуры (CALL func_read_keybuf), RRC x4 +
;           ANI 0Fh (младший полубайт), индексирует 16-байтную таблицу
;           data_keycode_table (0x016C), возвращает код в A. Портит D/HL.

func_decode_key:
    DCR A                       ; 0x0153
    JM loc_0159                 ; 0x0154
    XRA A                       ; 0x0157
    RET                         ; 0x0158
loc_0159:
    XRA A                       ; 0x0159
    CALL func_read_keybuf       ; 0x015A
    RRC                         ; 0x015D
    RRC                         ; 0x015E
    RRC                         ; 0x015F
    RRC                         ; 0x0160
    ANI 0Fh                     ; 0x0161
    LXI H, data_keycode_table   ; 0x0163
    MOV E, A                    ; 0x0166
    MVI D, 00h                  ; 0x0167
    DAD D                       ; 0x0169
    MOV A, M                    ; 0x016A
    RET                         ; 0x016B
