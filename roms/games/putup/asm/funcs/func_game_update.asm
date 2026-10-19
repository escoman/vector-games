; Функция: func_game_update
; Адрес: 0x0CE0
; Размер: 421 байт (0x0CE0-0x0E84, непрерывное тело)
; Описание: Кадровое обновление игры (управление/движение/коллизии игрока).
;           Вызывается из lbl_main_game_loop (0x0ED6). XRA A; CALL
;           func_check_start_key; если нажата клавиша: LDA var_game_state,
;           ==1 -> JZ 12B3h, ==2 -> JZ 12F6h (обработчики вне тела, в gap-зоне).
;           Обычный путь loc_0CF5: var_player_row++ (INR M); E=row; D=var_player_col;
;           CALL func_coords_to_textbuf; SHLD var_player_bufaddr. Сканирование
;           коллизий: var_collision_flag=0; HL+=0020h (ячейка ниже); 2x [MOV A,M;
;           CPI 76h('v'); JC/JZ skip; CMA; STA var_collision_flag]. При коллизии:
;           var_player_row--; var_game_state=1; 0906h=0. Далее CALL func_decode_key;
;           диспетчер кода клавиши: 1,2->loc_0D68; 3,4->0FD4h; 5->1042h; 6,7->1017h
;           (внешние gap-обработчики). loc_0D68: var_work_const=3; 0909h=col;
;           090Ah=row; 090Ch=tile; перерисовка пред.позиции 08E3h через
;           func_draw_tile_at_ptr; SHLD 08E3h; рендер тайла из data_tile_table_26DE
;           через func_render_tile_vram; скан текстового буфера 0300h байт (loc_0DBE).
;           Затем второй проход коллизий по 't'(74h); при nonzero -> JNZ 13Ah (gap).
;           Обновление 08E9h, CALL func_erase_char_08E9, проверка 08EAh==2 -> 1252h.
;           Финал: char ниже игрока; если <6Eh -> RC; иначе CALL func_sound_init и
;           диспетчер (A-6Dh): 1..4 -> func_score_and_redraw; 5->0F39h; 6->0F63h;
;           7->0F6Dh (gap-обработчики). Fall-through в lbl_main_game_loop.
;           Примечание: ветви на 0FD4h/1017h/1042h/12B3h/12F6h/13AAh/1252h/
;           0F39h/0F63h/0F6Dh ведут в gap-зоны (не объекты RDB) — оставлены как hex.

func_game_update:
    XRA A                       ; 0x0CE0
    CALL func_check_start_key   ; 0x0CE1
    ORA A                       ; 0x0CE4
    JZ loc_0CF5                 ; 0x0CE5
    LDA var_game_state          ; 0x0CE8
    CPI 01h                     ; 0x0CEB
    JZ 12B3h                    ; 0x0CED
    CPI 02h                     ; 0x0CF0
    JZ 12F6h                    ; 0x0CF2
loc_0CF5:
    LXI H, var_player_row       ; 0x0CF5
    INR M                       ; 0x0CF8
    MOV E, M                    ; 0x0CF9
    LDA var_player_col          ; 0x0CFA
    MOV D, A                    ; 0x0CFD
    CALL func_coords_to_textbuf ; 0x0CFE
    SHLD var_player_bufaddr     ; 0x0D01
    XRA A                       ; 0x0D04
    STA var_collision_flag      ; 0x0D05
    LXI B, 0020h                ; 0x0D08
    DAD B                       ; 0x0D0B
    MOV A, M                    ; 0x0D0C
    CPI 76h                     ; 0x0D0D
    JC loc_0D19                 ; 0x0D0F
    JZ loc_0D19                 ; 0x0D12
    CMA                         ; 0x0D15
    STA var_collision_flag      ; 0x0D16
loc_0D19:
    INX H                       ; 0x0D19
    MOV A, M                    ; 0x0D1A
    CPI 76h                     ; 0x0D1B
    JC loc_0D27                 ; 0x0D1D
    JZ loc_0D27                 ; 0x0D20
    CMA                         ; 0x0D23
    STA var_collision_flag      ; 0x0D24
loc_0D27:
    LDA var_collision_flag      ; 0x0D27
    ORA A                       ; 0x0D2A
    JZ loc_0D3E                 ; 0x0D2B
    LXI H, var_player_row       ; 0x0D2E
    DCR M                       ; 0x0D31
    MVI A, 01h                  ; 0x0D32
    STA var_game_state          ; 0x0D34
    XRA A                       ; 0x0D37
    STA 0906h                   ; 0x0D38
    JMP loc_0D41                ; 0x0D3B
loc_0D3E:
    STA var_game_state          ; 0x0D3E
loc_0D41:
    XRA A                       ; 0x0D41
    CALL func_decode_key        ; 0x0D42
    CPI 01h                     ; 0x0D45
    JZ loc_0D68                 ; 0x0D47
    CPI 02h                     ; 0x0D4A
    JZ loc_0D68                 ; 0x0D4C
    CPI 03h                     ; 0x0D4F
    JZ 0FD4h                    ; 0x0D51
    CPI 04h                     ; 0x0D54
    JZ 0FD4h                    ; 0x0D56
    CPI 05h                     ; 0x0D59
    JZ 1042h                    ; 0x0D5B
    CPI 06h                     ; 0x0D5E
    JZ 1017h                    ; 0x0D60
    CPI 07h                     ; 0x0D63
    JZ 1017h                    ; 0x0D65
loc_0D68:
    MVI A, 03h                  ; 0x0D68
    STA var_work_const          ; 0x0D6A
    LDA var_player_col          ; 0x0D6D
    STA 0909h                   ; 0x0D70
    LDA var_player_row          ; 0x0D73
    STA 090Ah                   ; 0x0D76
    LDA 090Dh                   ; 0x0D79
    MOV B, A                    ; 0x0D7C
    RLC                         ; 0x0D7D
    ADD B                       ; 0x0D7E
    MOV B, A                    ; 0x0D7F
    LDA var_work_const          ; 0x0D80
    ADD B                       ; 0x0D83
    DCR A                       ; 0x0D84
    STA 090Ch                   ; 0x0D85
    LXI H, 08E3h                ; 0x0D88
    LDA 090Ah                   ; 0x0D8B
    CMP M                       ; 0x0D8E
    JNZ loc_0D9B                ; 0x0D8F
    INX H                       ; 0x0D92
    LDA 0909h                   ; 0x0D93
    CMP M                       ; 0x0D96
    DCX H                       ; 0x0D97
    JZ loc_0D9E                 ; 0x0D98
loc_0D9B:
    CALL func_draw_tile_at_ptr  ; 0x0D9B
loc_0D9E:
    LDA 090Ah                   ; 0x0D9E
    MOV L, A                    ; 0x0DA1
    LDA 0909h                   ; 0x0DA2
    MOV H, A                    ; 0x0DA5
    SHLD 08E3h                  ; 0x0DA6
    XCHG                        ; 0x0DA9
    LDA 090Ch                   ; 0x0DAA
    ADD A                       ; 0x0DAD
    ADD A                       ; 0x0DAE
    LXI H, data_tile_table_26DE ; 0x0DAF
    CALL func_hl_add_a          ; 0x0DB2
    CALL func_render_tile_vram  ; 0x0DB5
    LXI H, data_ram_buffer_5000 ; 0x0DB8
    LXI B, 0300h                ; 0x0DBB
loc_0DBE:
    MOV A, M                    ; 0x0DBE
    CPI 75h                     ; 0x0DBF
    JZ loc_0DD1                 ; 0x0DC1
    CPI 0FEh                    ; 0x0DC4
    JNZ loc_0DD6                ; 0x0DC6
    MVI A, 75h                  ; 0x0DC9
    CALL func_draw_char_at_hl   ; 0x0DCB
    JMP loc_0DD6                ; 0x0DCE
loc_0DD1:
    MVI A, 0FEh                 ; 0x0DD1
    CALL func_draw_char_at_hl   ; 0x0DD3
loc_0DD6:
    INX H                       ; 0x0DD6
    DCX B                       ; 0x0DD7
    MOV A, B                    ; 0x0DD8
    ORA C                       ; 0x0DD9
    JNZ loc_0DBE                ; 0x0DDA
    LDA var_player_col          ; 0x0DDD
    MOV D, A                    ; 0x0DE0
    LDA var_player_row          ; 0x0DE1
    MOV E, A                    ; 0x0DE4
    CALL func_coords_to_textbuf ; 0x0DE5
    SHLD var_player_bufaddr     ; 0x0DE8
    XRA A                       ; 0x0DEB
    STA var_collision_flag      ; 0x0DEC
    MOV A, M                    ; 0x0DEF
    CPI 74h                     ; 0x0DF0
    JC loc_0DFC                 ; 0x0DF2
    JZ loc_0DFC                 ; 0x0DF5
    CMA                         ; 0x0DF8
    STA var_collision_flag      ; 0x0DF9
loc_0DFC:
    INX H                       ; 0x0DFC
    MOV A, M                    ; 0x0DFD
    CPI 74h                     ; 0x0DFE
    JC loc_0E0A                 ; 0x0E00
    JZ loc_0E0A                 ; 0x0E03
    CMA                         ; 0x0E06
    STA var_collision_flag      ; 0x0E07
loc_0E0A:
    LXI B, 001Fh                ; 0x0E0A
    DAD B                       ; 0x0E0D
    MOV A, M                    ; 0x0E0E
    CPI 74h                     ; 0x0E0F
    JC loc_0E1B                 ; 0x0E11
    JZ loc_0E1B                 ; 0x0E14
    CMA                         ; 0x0E17
    STA var_collision_flag      ; 0x0E18
loc_0E1B:
    INX H                       ; 0x0E1B
    MOV A, M                    ; 0x0E1C
    CPI 74h                     ; 0x0E1D
    JC loc_0E29                 ; 0x0E1F
    JZ loc_0E29                 ; 0x0E22
    CMA                         ; 0x0E25
    STA var_collision_flag      ; 0x0E26
loc_0E29:
    LDA var_collision_flag      ; 0x0E29
    ORA A                       ; 0x0E2C
    JNZ 13AAh                   ; 0x0E2D
    LHLD 08E9h                  ; 0x0E30
    INX H                       ; 0x0E33
    SHLD 08E9h                  ; 0x0E34
    LDA 08E9h                   ; 0x0E37
    ANI 1Fh                     ; 0x0E3A
    JNZ loc_0E4A                ; 0x0E3C
    CALL func_erase_char_08E9   ; 0x0E3F
    LDA 08EAh                   ; 0x0E42
    CPI 02h                     ; 0x0E45
    JZ 1252h                    ; 0x0E47
loc_0E4A:
    LHLD var_player_bufaddr     ; 0x0E4A
    LXI B, 0020h                ; 0x0E4D
    DAD B                       ; 0x0E50
    MOV A, M                    ; 0x0E51
    STA var_collision_flag      ; 0x0E52
    CPI 6Eh                     ; 0x0E55
    RC                          ; 0x0E57
    MVI B, 02h                  ; 0x0E58
    CALL func_sound_init        ; 0x0E5A
    LDA var_collision_flag      ; 0x0E5D
    SUI 6Dh                     ; 0x0E60
    CPI 01h                     ; 0x0E62
    JZ func_score_and_redraw    ; 0x0E64
    CPI 02h                     ; 0x0E67
    JZ func_score_and_redraw    ; 0x0E69
    CPI 03h                     ; 0x0E6C
    JZ func_score_and_redraw    ; 0x0E6E
    CPI 04h                     ; 0x0E71
    JZ func_score_and_redraw    ; 0x0E73
    CPI 05h                     ; 0x0E76
    JZ 0F39h                    ; 0x0E78
    CPI 06h                     ; 0x0E7B
    JZ 0F63h                    ; 0x0E7D
    CPI 07h                     ; 0x0E80
    JZ 0F6Dh                    ; 0x0E82
    ; fall-through в lbl_main_game_loop (0x0E85)
