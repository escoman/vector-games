; Функция: func_draw_level_hud
; Адрес: 0x11EE
; Размер: 44 байта
; Описание: Отрисовка индикатора бонуса/жизней в HUD. A=var_bonus_counter;
;           если A>=6 (JC/JZ пропуск) -> ограничивает значение до 6, иначе
;           использует A как есть; сохраняет в 091Dh. Курсор 52F9h
;           (func_set_text_ptr); B=091Dh; если B==0 -> RZ (ничего не рисовать);
;           иначе печатает B раз символ 8Ah (значок жизни) через
;           func_print_char_at_ptr (цикл loc_1212).

func_draw_level_hud:
    LDA var_bonus_counter       ; 0x11EE
    CPI 06h                     ; 0x11F1
    JC loc_1201                 ; 0x11F3
    JZ loc_1201                 ; 0x11F6
    MVI A, 06h                  ; 0x11F9
    STA 091Dh                   ; 0x11FB
    JMP loc_1204                ; 0x11FE
loc_1201:
    STA 091Dh                   ; 0x1201
loc_1204:
    LXI H, 52F9h                ; 0x1204
    CALL func_set_text_ptr      ; 0x1207
    LDA 091Dh                   ; 0x120A
    MOV B, A                    ; 0x120D
    ORA A                       ; 0x120E
    RZ                          ; 0x120F
    MVI A, 8Ah                  ; 0x1210
loc_1212:
    CALL func_print_char_at_ptr ; 0x1212
    DCR B                       ; 0x1215
    JNZ loc_1212                ; 0x1216
    RET                         ; 0x1219
