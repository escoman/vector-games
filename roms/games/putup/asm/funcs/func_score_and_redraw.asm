; Функция: func_score_and_redraw
; Адрес: 0x0F09
; Размер: 48 байт
; Описание: Начисление очков за собранный предмет и перерисовка. A=var_collision_flag;
;           A-=6Dh (тип предмета); HL=08EDh+A (таблица стоимости предмета);
;           CALL func_hl_add_a; L=(HL); H=0; вычисляет DE=HL, HL=HL*8+DE (умножение
;           на 9); var_score += DE; CALL func_draw_score_hud (обновление HUD счёта);
;           затем D=var_player_col, E=var_player_row; HL=270Ah (тайл пустой клетки);
;           CALL func_draw_tile_to_buf (стереть предмет в текстовом буфере);
;           JMP func_game_update (продолжить кадр).

func_score_and_redraw:
    LDA var_collision_flag      ; 0x0F09
    SUI 6Dh                     ; 0x0F0C
    LXI H, 08EDh                ; 0x0F0E
    CALL func_hl_add_a          ; 0x0F11
    MOV L, M                    ; 0x0F14
    MVI H, 00h                  ; 0x0F15
    DAD H                       ; 0x0F17
    MOV D, H                    ; 0x0F18
    MOV E, L                    ; 0x0F19
    DAD H                       ; 0x0F1A
    DAD H                       ; 0x0F1B
    DAD D                       ; 0x0F1C
    XCHG                        ; 0x0F1D
    LHLD var_score              ; 0x0F1E
    DAD D                       ; 0x0F21
    SHLD var_score              ; 0x0F22
    CALL func_draw_score_hud    ; 0x0F25
    LDA var_player_col          ; 0x0F28
    MOV D, A                    ; 0x0F2B
    LDA var_player_row          ; 0x0F2C
    MOV E, A                    ; 0x0F2F
    LXI H, 270Ah                ; 0x0F30
    CALL func_draw_tile_to_buf  ; 0x0F33
    JMP func_game_update        ; 0x0F36
