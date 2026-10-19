; Функция: func_entity_state8
; Адрес: 0x1851
; Размер: 173 байта
; Описание: Обработчик сущности в состоянии 8 (движение вниз с поворотом).
;           data_entity_xcoords[idx] -> D; data_entity_ycoords[idx]++ -> E;
;           CALL func_coords_to_textbuf; HL+=0020h (клетка ниже). Проверка
;           клетки ниже и справа (HL+1) на пустоту (0x20). Если не пусто ->
;           loc_1879 (откат y--, перерисовка тайлом data_tile_graphics со
;           смещением от var_page_flip: A=(var_page_flip+0Eh)*4, HL=2706h+BC).
;           Затем сравнение data_entity_xcoords[idx] с var_player_col: если
;           x>=col состояние=06h, иначе 05h. Если путь свободен (loc_18C0):
;           стереть старую позицию тайлом 270Ah и нарисовать новую.

func_entity_state8:
    LDA var_entity_index        ; 0x1851
    PUSH PSW                    ; 0x1854
    LXI H, data_entity_xcoords  ; 0x1855
    CALL func_hl_add_a          ; 0x1858
    MOV D, M                    ; 0x185B
    POP PSW                     ; 0x185C
    LXI H, data_entity_ycoords  ; 0x185D
    CALL func_hl_add_a          ; 0x1860
    INR M                       ; 0x1863
    MOV E, M                    ; 0x1864
    CALL func_coords_to_textbuf ; 0x1865
    LXI B, 0020h                ; 0x1868
    DAD B                       ; 0x186B
    MOV A, M                    ; 0x186C
    CPI 20h                     ; 0x186D
    JNZ loc_1879                ; 0x186F
    INX H                       ; 0x1872
    MOV A, M                    ; 0x1873
    CPI 20h                     ; 0x1874
    JZ loc_18C0                 ; 0x1876
loc_1879:
    LDA var_entity_index        ; 0x1879
    LXI H, data_entity_xcoords  ; 0x187C
    PUSH PSW                    ; 0x187F
    CALL func_hl_add_a          ; 0x1880
    POP PSW                     ; 0x1883
    MOV D, M                    ; 0x1884
    LXI H, data_entity_ycoords  ; 0x1885
    PUSH PSW                    ; 0x1888
    CALL func_hl_add_a          ; 0x1889
    DCR M                       ; 0x188C
    MOV E, M                    ; 0x188D
    LDA var_page_flip           ; 0x188E
    ADI 0Eh                     ; 0x1891
    ADD A                       ; 0x1893
    ADD A                       ; 0x1894
    MOV C, A                    ; 0x1895
    MVI B, 00h                  ; 0x1896
    LXI H, data_tile_graphics   ; 0x1898
    DAD B                       ; 0x189B
    CALL func_draw_tile_to_buf  ; 0x189C
    POP PSW                     ; 0x189F
    LXI H, data_entity_xcoords  ; 0x18A0
    CALL func_hl_add_a          ; 0x18A3
    LDA var_player_col          ; 0x18A6
    MOV B, A                    ; 0x18A9
    MOV A, M                    ; 0x18AA
    CMP B                       ; 0x18AB
    PUSH PSW                    ; 0x18AC
    LDA var_entity_index        ; 0x18AD
    LXI H, 0919h                ; 0x18B0
    CALL func_hl_add_a          ; 0x18B3
    POP PSW                     ; 0x18B6
    JC loc_18BD                 ; 0x18B7
    MVI M, 06h                  ; 0x18BA
    RET                         ; 0x18BC
loc_18BD:
    MVI M, 05h                  ; 0x18BD
    RET                         ; 0x18BF
loc_18C0:
    LDA var_entity_index        ; 0x18C0
    LXI H, data_entity_xcoords  ; 0x18C3
    PUSH PSW                    ; 0x18C6
    CALL func_hl_add_a          ; 0x18C7
    POP PSW                     ; 0x18CA
    MOV D, M                    ; 0x18CB
    LXI H, data_entity_ycoords  ; 0x18CC
    PUSH PSW                    ; 0x18CF
    CALL func_hl_add_a          ; 0x18D0
    MOV E, M                    ; 0x18D3
    DCR E                       ; 0x18D4
    LXI H, 270Ah                ; 0x18D5
    CALL func_draw_tile_to_buf  ; 0x18D8
    POP PSW                     ; 0x18DB
    LXI H, data_entity_xcoords  ; 0x18DC
    PUSH PSW                    ; 0x18DF
    CALL func_hl_add_a          ; 0x18E0
    POP PSW                     ; 0x18E3
    MOV D, M                    ; 0x18E4
    LXI H, data_entity_ycoords  ; 0x18E5
    CALL func_hl_add_a          ; 0x18E8
    MOV E, M                    ; 0x18EB
    LXI H, data_tile_graphics   ; 0x18EC
    LDA var_page_flip           ; 0x18EF
    ADI 0Eh                     ; 0x18F2
    ADD A                       ; 0x18F4
    ADD A                       ; 0x18F5
    MOV C, A                    ; 0x18F6
    MVI B, 00h                  ; 0x18F7
    DAD B                       ; 0x18F9
    CALL func_draw_tile_to_buf  ; 0x18FA
    RET                         ; 0x18FD
