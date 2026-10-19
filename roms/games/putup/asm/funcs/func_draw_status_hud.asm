; Функция: func_draw_status_hud
; Адрес: 0x121A
; Размер: 57 байт
; Описание: Отрисовка строки состояния HUD. Курсор 52F2h -> печатает var_level
;           через func_print_uint16; курсор 52EFh -> str_round ("ROUND");
;           курсор 5302h -> str_time ("TIME"); курсор 5307h -> печатает
;           var_lives_icons раз символ 9Bh (значок жизни) через
;           func_print_char_at_ptr (цикл loc_124A).

func_draw_status_hud:
    LXI H, 52F2h                ; 0x121A
    CALL func_set_text_ptr      ; 0x121D
    LXI H, var_level            ; 0x1220
    CALL func_print_uint16      ; 0x1223
    LXI H, 52EFh                ; 0x1226
    CALL func_set_text_ptr      ; 0x1229
    LXI H, str_round            ; 0x122C
    CALL func_print_string      ; 0x122F
    LXI H, 5302h                ; 0x1232
    CALL func_set_text_ptr      ; 0x1235
    LXI H, str_time             ; 0x1238
    CALL func_print_string      ; 0x123B
    LXI H, 5307h                ; 0x123E
    CALL func_set_text_ptr      ; 0x1241
    LDA var_lives_icons         ; 0x1244
    MOV B, A                    ; 0x1247
    MVI A, 9Bh                  ; 0x1248
loc_124A:
    CALL func_print_char_at_ptr ; 0x124A
    DCR B                       ; 0x124D
    JNZ loc_124A                ; 0x124E
    RET                         ; 0x1251
