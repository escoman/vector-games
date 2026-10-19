; Функция: func_level_loader
; Адрес: 0x197C
; Размер: 523 байта
; Описание: Загрузка следующего уровня. var_level++; если var_level >= 10h
;           (16) -> ветка победы/бонуса (loc_1A3B). Иначе: обнуление 090Fh,
;           копирование 8 байт параметров уровня из data_level_params[level*8]
;           в data_level_param_buf (func_memcpy), сброс стека, очистка
;           текстового буфера (func_clear_textbuf), вычисление указателя карты
;           уровня в data_level_maps (карта = 0B0h байт = 16x11 тайлов),
;           отрисовка всех тайлов карты в буфер (func_draw_tile_to_buf),
;           отрисовка HUD (счёт/жизни/статус), инициализация координат игрока и
;           сущностей из буфера параметров, затем JMP lbl_main_game_loop.
;           Ветка победы: рисует рамку, поздравление (str_congratulation) и
;           бонус (str_bonus), начисляет 5000 (1388h) очков, JMP 1447h
;           (обработчик вне RDB).

func_level_loader:
    LXI H, var_level            ; 0x197C
    INR M                       ; 0x197F
    MOV A, M                    ; 0x1980
    CPI 10h                     ; 0x1981
    JNC loc_1A3B                ; 0x1983
    XRA A                       ; 0x1986
    STA 090Fh                   ; 0x1987
    LXI H, data_level_params    ; 0x198A
    LDA var_level               ; 0x198D
    RLC                         ; 0x1990
    RLC                         ; 0x1991
    RLC                         ; 0x1992
    MOV E, A                    ; 0x1993
    MVI D, 00h                  ; 0x1994
    DAD D                       ; 0x1996
    LXI D, data_level_param_buf ; 0x1997
    LXI B, 0008h                ; 0x199A
    CALL func_memcpy            ; 0x199D
    LXI SP, 0100h               ; 0x19A0
    CALL func_clear_textbuf     ; 0x19A3
    LDA var_level               ; 0x19A6
    DCR A                       ; 0x19A9
    LXI H, data_level_maps      ; 0x19AA
    JZ loc_19B8                 ; 0x19AD
    LXI D, 00B0h                ; 0x19B0
loc_19B3:
    DAD D                       ; 0x19B3
    DCR A                       ; 0x19B4
    JNZ loc_19B3                ; 0x19B5
loc_19B8:
    LXI D, 0000h                ; 0x19B8
    LXI B, 00B0h                ; 0x19BB
loc_19BE:
    PUSH B                      ; 0x19BE
    PUSH H                      ; 0x19BF
    MOV A, M                    ; 0x19C0
    ADD A                       ; 0x19C1
    ADD A                       ; 0x19C2
    LXI H, data_tile_graphics   ; 0x19C3
    CALL func_hl_add_a          ; 0x19C6
    PUSH D                      ; 0x19C9
    CALL func_draw_tile_to_buf  ; 0x19CA
    POP D                       ; 0x19CD
    INR D                       ; 0x19CE
    INR D                       ; 0x19CF
    MOV A, D                    ; 0x19D0
    CPI 20h                     ; 0x19D1
    JNZ loc_19DA                ; 0x19D3
    MVI D, 00h                  ; 0x19D6
    INR E                       ; 0x19D8
    INR E                       ; 0x19D9
loc_19DA:
    POP H                       ; 0x19DA
    INX H                       ; 0x19DB
    POP B                       ; 0x19DC
    DCX B                       ; 0x19DD
    MOV A, B                    ; 0x19DE
    ORA C                       ; 0x19DF
    JNZ loc_19BE                ; 0x19E0
    CALL func_draw_score_hud    ; 0x19E3
    CALL func_play_sfx          ; 0x19E6
    MVI A, 10h                  ; 0x19E9
    STA var_lives_icons         ; 0x19EB
    CALL func_draw_status_hud   ; 0x19EE
    MVI A, 01h                  ; 0x19F1
    STA var_player_row          ; 0x19F3
    INR A                       ; 0x19F6
    STA var_player_col          ; 0x19F7
    XRA A                       ; 0x19FA
    STA var_game_state          ; 0x19FB
    LDA 0913h                   ; 0x19FE
    STA var_entity1_state       ; 0x1A01
    LDA 0916h                   ; 0x1A04
    STA var_entity2_state       ; 0x1A07
    LDA 0914h                   ; 0x1A0A
    STA 0920h                   ; 0x1A0D
    LDA 0915h                   ; 0x1A10
    STA 0923h                   ; 0x1A13
    LDA 0917h                   ; 0x1A16
    STA 0921h                   ; 0x1A19
    LDA 0918h                   ; 0x1A1C
    STA 0924h                   ; 0x1A1F
    XRA A                       ; 0x1A22
    STA 0910h                   ; 0x1A23
    LXI H, 0000h                ; 0x1A26
    SHLD 08E9h                  ; 0x1A29
    CALL func_draw_game_objects ; 0x1A2C
    XRA A                       ; 0x1A2F
    STA 090Dh                   ; 0x1A30
    MVI A, 03h                  ; 0x1A33
    STA var_work_const          ; 0x1A35
    JMP lbl_main_game_loop      ; 0x1A38
loc_1A3B:
    CALL func_draw_game_objects ; 0x1A3B
    CALL func_clear_textbuf     ; 0x1A3E
    LXI H, 5100h                ; 0x1A41
    CALL func_set_text_ptr      ; 0x1A44
    LXI B, 0180h                ; 0x1A47
loc_1A4A:
    MVI A, 9Ch                  ; 0x1A4A
    CALL func_print_char_at_ptr ; 0x1A4C
    DCX B                       ; 0x1A4F
    MOV A, C                    ; 0x1A50
    ORA B                       ; 0x1A51
    JNZ loc_1A4A                ; 0x1A52
loc_1A55:
    PUSH B                      ; 0x1A55
    MOV A, B                    ; 0x1A56
    ADD A                       ; 0x1A57
    MOV D, A                    ; 0x1A58
    MVI E, 14h                  ; 0x1A59
    LXI H, 270Eh                ; 0x1A5B
    CALL func_draw_tile_to_buf  ; 0x1A5E
    POP B                       ; 0x1A61
    INR B                       ; 0x1A62
    MOV A, B                    ; 0x1A63
    CPI 10h                     ; 0x1A64
    JNZ loc_1A55                ; 0x1A66
    XRA A                       ; 0x1A69
    STA var_player_col          ; 0x1A6A
    CALL func_draw_score_hud    ; 0x1A6D
    CALL func_draw_level_hud    ; 0x1A70
    CALL func_draw_status_hud   ; 0x1A73
    LXI H, 5250h                ; 0x1A76
    CALL func_set_text_ptr      ; 0x1A79
    MVI A, 9Dh                  ; 0x1A7C
    CALL func_print_char_at_ptr ; 0x1A7E
    LXI H, 5270h                ; 0x1A81
    CALL func_set_text_ptr      ; 0x1A84
    MVI A, 9Eh                  ; 0x1A87
    CALL func_print_char_at_ptr ; 0x1A89
loc_1A8C:
    LDA 08F7h                   ; 0x1A8C
    MOV B, A                    ; 0x1A8F
    LDA 08F8h                   ; 0x1A90
    STA 08F7h                   ; 0x1A93
    MOV A, B                    ; 0x1A96
    STA 08F8h                   ; 0x1A97
    LXI H, var_player_col       ; 0x1A9A
    INR M                       ; 0x1A9D
    LDA 08F7h                   ; 0x1A9E
    CPI 01h                     ; 0x1AA1
    JZ loc_1ABD                 ; 0x1AA3
    LDA var_page_flip           ; 0x1AA6
    MOV B, A                    ; 0x1AA9
    LDA 08FAh                   ; 0x1AAA
    STA var_page_flip           ; 0x1AAD
    MOV A, B                    ; 0x1AB0
    STA 08FAh                   ; 0x1AB1
    LDA var_page_flip           ; 0x1AB4
    STA var_collision_flag      ; 0x1AB7
    JMP loc_1AC2                ; 0x1ABA
loc_1ABD:
    MVI A, 03h                  ; 0x1ABD
    STA var_collision_flag      ; 0x1ABF
loc_1AC2:
    MVI A, 12h                  ; 0x1AC2
    STA 090Ah                   ; 0x1AC4
    LDA var_player_col          ; 0x1AC7
    STA 0909h                   ; 0x1ACA
    LDA var_collision_flag      ; 0x1ACD
    DCR A                       ; 0x1AD0
    STA 090Ch                   ; 0x1AD1
    LXI H, 08E3h                ; 0x1AD4
    LDA 090Ah                   ; 0x1AD7
    CMP M                       ; 0x1ADA
    JNZ loc_1AE7                ; 0x1ADB
    INX H                       ; 0x1ADE
    LDA 0909h                   ; 0x1ADF
    CMP M                       ; 0x1AE2
    DCX H                       ; 0x1AE3
    JZ loc_1AEA                 ; 0x1AE4
loc_1AE7:
    CALL func_draw_tile_at_ptr  ; 0x1AE7
loc_1AEA:
    LDA 090Ah                   ; 0x1AEA
    MOV L, A                    ; 0x1AED
    LDA 0909h                   ; 0x1AEE
    MOV H, A                    ; 0x1AF1
    SHLD 08E3h                  ; 0x1AF2
    XCHG                        ; 0x1AF5
    LDA 090Ch                   ; 0x1AF6
    ADD A                       ; 0x1AF9
    ADD A                       ; 0x1AFA
    LXI H, data_tile_table_26DE ; 0x1AFB
    CALL func_hl_add_a          ; 0x1AFE
    CALL func_render_tile_vram  ; 0x1B01
    MVI B, 05h                  ; 0x1B04
    CALL func_delay             ; 0x1B06
    LDA var_player_col          ; 0x1B09
    CPI 1Ch                     ; 0x1B0C
    JC loc_1A8C                 ; 0x1B0E
    LDA var_player_col          ; 0x1B11
    STA 0909h                   ; 0x1B14
    MVI A, 12h                  ; 0x1B17
    STA 090Ah                   ; 0x1B19
    MVI A, 06h                  ; 0x1B1C
    STA 090Ch                   ; 0x1B1E
    LXI H, 08E3h                ; 0x1B21
    LDA 090Ah                   ; 0x1B24
    CMP M                       ; 0x1B27
    JNZ loc_1B34                ; 0x1B28
    INX H                       ; 0x1B2B
    LDA 0909h                   ; 0x1B2C
    CMP M                       ; 0x1B2F
    DCX H                       ; 0x1B30
    JZ loc_1B37                 ; 0x1B31
loc_1B34:
    CALL func_draw_tile_at_ptr  ; 0x1B34
loc_1B37:
    LDA 090Ah                   ; 0x1B37
    MOV L, A                    ; 0x1B3A
    LDA 0909h                   ; 0x1B3B
    MOV H, A                    ; 0x1B3E
    SHLD 08E3h                  ; 0x1B3F
    XCHG                        ; 0x1B42
    LDA 090Ch                   ; 0x1B43
    ADD A                       ; 0x1B46
    ADD A                       ; 0x1B47
    LXI H, data_tile_table_26DE ; 0x1B48
    CALL func_hl_add_a          ; 0x1B4B
    CALL func_render_tile_vram  ; 0x1B4E
    LXI H, 5250h                ; 0x1B51
    CALL func_set_text_ptr      ; 0x1B54
    MVI A, 9Ch                  ; 0x1B57
    CALL func_print_char_at_ptr ; 0x1B59
    LXI H, 5087h                ; 0x1B5C
    CALL func_set_text_ptr      ; 0x1B5F
    LXI H, str_congratulation   ; 0x1B62
    CALL func_print_string      ; 0x1B65
    LXI H, 50C6h                ; 0x1B68
    CALL func_set_text_ptr      ; 0x1B6B
    LXI H, str_bonus            ; 0x1B6E
    CALL func_print_string      ; 0x1B71
    LHLD var_score              ; 0x1B74
    LXI D, 1388h                ; 0x1B77
    DAD D                       ; 0x1B7A
    SHLD var_score              ; 0x1B7B
    CALL func_draw_score_hud    ; 0x1B7E
    CALL func_draw_game_objects ; 0x1B81
    JMP 1447h                   ; 0x1B84
