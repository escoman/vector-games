; Функция: func_entity_state7
; Адрес: 0x17A8
; Размер: 169 байт
; Описание: Обработчик сущности в состоянии 7 (движение вверх с поворотом).
;           data_entity_xcoords[idx] -> D; data_entity_ycoords[idx]-- -> E;
;           CALL func_coords_to_textbuf. Проверка текущей клетки и клетки справа
;           (HL+1) на пустоту (0x20). Если не пусто -> loc_17CC (откат y++,
;           перерисовка клетки тайлом data_tile_graphics со смещением от
;           var_page_flip: A=(var_page_flip+0Eh)*4, HL=2706h+BC). Затем
;           сравнение data_entity_xcoords[idx] с var_player_col: если x>=col
;           состояние=06h, иначе 05h. Если путь свободен (loc_1813): стереть
;           старую позицию тайлом 270Ah и нарисовать новую.

func_entity_state7:
    LDA var_entity_index        ; 0x17A8
    PUSH PSW                    ; 0x17AB
    LXI H, data_entity_xcoords  ; 0x17AC
    CALL func_hl_add_a          ; 0x17AF
    MOV D, M                    ; 0x17B2
    POP PSW                     ; 0x17B3
    LXI H, data_entity_ycoords  ; 0x17B4
    CALL func_hl_add_a          ; 0x17B7
    DCR M                       ; 0x17BA
    MOV E, M                    ; 0x17BB
    CALL func_coords_to_textbuf ; 0x17BC
    MOV A, M                    ; 0x17BF
    CPI 20h                     ; 0x17C0
    JNZ loc_17CC                ; 0x17C2
    INX H                       ; 0x17C5
    MOV A, M                    ; 0x17C6
    CPI 20h                     ; 0x17C7
    JZ loc_1813                 ; 0x17C9
loc_17CC:
    LDA var_entity_index        ; 0x17CC
    LXI H, data_entity_xcoords  ; 0x17CF
    PUSH PSW                    ; 0x17D2
    CALL func_hl_add_a          ; 0x17D3
    POP PSW                     ; 0x17D6
    MOV D, M                    ; 0x17D7
    LXI H, data_entity_ycoords  ; 0x17D8
    PUSH PSW                    ; 0x17DB
    CALL func_hl_add_a          ; 0x17DC
    INR M                       ; 0x17DF
    MOV E, M                    ; 0x17E0
    LDA var_page_flip           ; 0x17E1
    ADI 0Eh                     ; 0x17E4
    ADD A                       ; 0x17E6
    ADD A                       ; 0x17E7
    MOV C, A                    ; 0x17E8
    MVI B, 00h                  ; 0x17E9
    LXI H, data_tile_graphics   ; 0x17EB
    DAD B                       ; 0x17EE
    CALL func_draw_tile_to_buf  ; 0x17EF
    POP PSW                     ; 0x17F2
    LXI H, data_entity_xcoords  ; 0x17F3
    CALL func_hl_add_a          ; 0x17F6
    LDA var_player_col          ; 0x17F9
    MOV B, A                    ; 0x17FC
    MOV A, M                    ; 0x17FD
    CMP B                       ; 0x17FE
    PUSH PSW                    ; 0x17FF
    LDA var_entity_index        ; 0x1800
    LXI H, 0919h                ; 0x1803
    CALL func_hl_add_a          ; 0x1806
    POP PSW                     ; 0x1809
    JC loc_1810                 ; 0x180A
    MVI M, 06h                  ; 0x180D
    RET                         ; 0x180F
loc_1810:
    MVI M, 05h                  ; 0x1810
    RET                         ; 0x1812
loc_1813:
    LDA var_entity_index        ; 0x1813
    LXI H, data_entity_xcoords  ; 0x1816
    PUSH PSW                    ; 0x1819
    CALL func_hl_add_a          ; 0x181A
    POP PSW                     ; 0x181D
    MOV D, M                    ; 0x181E
    LXI H, data_entity_ycoords  ; 0x181F
    PUSH PSW                    ; 0x1822
    CALL func_hl_add_a          ; 0x1823
    MOV E, M                    ; 0x1826
    INR E                       ; 0x1827
    LXI H, 270Ah                ; 0x1828
    CALL func_draw_tile_to_buf  ; 0x182B
    POP PSW                     ; 0x182E
    LXI H, data_entity_xcoords  ; 0x182F
    PUSH PSW                    ; 0x1832
    CALL func_hl_add_a          ; 0x1833
    POP PSW                     ; 0x1836
    MOV D, M                    ; 0x1837
    LXI H, data_entity_ycoords  ; 0x1838
    CALL func_hl_add_a          ; 0x183B
    MOV E, M                    ; 0x183E
    LXI H, data_tile_graphics   ; 0x183F
    LDA var_page_flip           ; 0x1842
    ADI 0Eh                     ; 0x1845
    ADD A                       ; 0x1847
    ADD A                       ; 0x1848
    MOV C, A                    ; 0x1849
    MVI B, 00h                  ; 0x184A
    DAD B                       ; 0x184C
    CALL func_draw_tile_to_buf  ; 0x184D
    RET                         ; 0x1850
