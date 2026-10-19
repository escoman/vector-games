; Функция: func_draw_score_hud
; Адрес: 0x1197
; Размер: 82 байта
; Описание: Отрисовка счёта в HUD и проверка бонуса. Устанавливает текстовый
;           курсор 52E1h, печатает str_score ("SCORE"), курсор 52E7h, печатает
;           var_score через func_print_uint16 + завершающий '0'. Далее сравнение
;           var_score с var_bonus_threshold-1: если счёт не превысил порог ->
;           loc_11D1 (пропуск); иначе var_score &= 0BFh (маска). Сохраняет флаг
;           переноса в 0B3Dh; RNC -> выход. При переходе порога: var_bonus_counter++,
;           CALL func_play_sfx, var_bonus_threshold += 07D0h (следующий порог).

func_draw_score_hud:
    LXI H, 52E1h                ; 0x1197
    CALL func_set_text_ptr      ; 0x119A
    LXI H, str_score            ; 0x119D
    CALL func_print_string      ; 0x11A0
    LXI H, 52E7h                ; 0x11A3
    CALL func_set_text_ptr      ; 0x11A6
    LXI H, var_score            ; 0x11A9
    CALL func_print_uint16      ; 0x11AC
    MVI A, 30h                  ; 0x11AF
    CALL func_print_char_at_ptr ; 0x11B1
    LHLD var_score              ; 0x11B4
    XCHG                        ; 0x11B7
    LHLD var_bonus_threshold    ; 0x11B8
    DCX H                       ; 0x11BB
    STA 0B3Dh                   ; 0x11BC
    MOV A, L                    ; 0x11BF
    SBB E                       ; 0x11C0
    MOV L, A                    ; 0x11C1
    MOV A, H                    ; 0x11C2
    SBB D                       ; 0x11C3
    MOV H, A                    ; 0x11C4
    PUSH H                      ; 0x11C5
    PUSH PSW                    ; 0x11C6
    ORA L                       ; 0x11C7
    JZ loc_11D1                 ; 0x11C8
    POP H                       ; 0x11CB
    MVI A, 0BFh                 ; 0x11CC
    ANA L                       ; 0x11CE
    MOV L, A                    ; 0x11CF
    PUSH H                      ; 0x11D0
loc_11D1:
    POP PSW                     ; 0x11D1
    POP H                       ; 0x11D2
    LDA 0B3Dh                   ; 0x11D3
    RNC                         ; 0x11D6
    LXI H, var_bonus_counter    ; 0x11D7
    INR M                       ; 0x11DA
    CALL func_play_sfx          ; 0x11DB
    LHLD var_bonus_threshold    ; 0x11DE
    LXI B, 07D0h                ; 0x11E1
    DAD B                       ; 0x11E4
    SHLD var_bonus_threshold    ; 0x11E5
    RET                         ; 0x11E8
