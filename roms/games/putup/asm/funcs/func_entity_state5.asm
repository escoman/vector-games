; Функция: func_entity_state5
; Адрес: 0x164F
; Размер: 173 байта
; Описание: Обработчик сущности в состоянии 5 (движение вправо с поворотом).
;           data_entity_xcoords[idx]++ -> D; data_entity_ycoords[idx] -> E;
;           CALL func_coords_to_textbuf. Проверка клетки справа (HL+1) и ниже
;           (HL+0020h) на пустоту (0x20). Если не пусто -> loc_1677 (откат x--,
;           перерисовка клетки тайлом data_tile_graphics со смещением от
;           var_page_flip: A=(var_page_flip+0Eh)*4, HL=2706h+BC). Затем
;           сравнение data_entity_ycoords[idx] с var_player_row: если y>=row
;           состояние=07h, иначе 08h. Если путь свободен (loc_16BE): стереть
;           старую позицию тайлом 270Ah и нарисовать новую.

func_entity_state5:
    LDA var_entity_index        ; 0x164F
    PUSH PSW                    ; 0x1652
    LXI H, data_entity_xcoords  ; 0x1653
    CALL func_hl_add_a          ; 0x1656
    INR M                       ; 0x1659
    MOV D, M                    ; 0x165A
    POP PSW                     ; 0x165B
    LXI H, data_entity_ycoords  ; 0x165C
    CALL func_hl_add_a          ; 0x165F
    MOV E, M                    ; 0x1662
    CALL func_coords_to_textbuf ; 0x1663
    INX H                       ; 0x1666
    MOV A, M                    ; 0x1667
    CPI 20h                     ; 0x1668
    JNZ loc_1677                ; 0x166A
    LXI B, 0020h                ; 0x166D
    DAD B                       ; 0x1670
    MOV A, M                    ; 0x1671
    CPI 20h                     ; 0x1672
    JZ loc_16BE                 ; 0x1674
loc_1677:
    LDA var_entity_index        ; 0x1677
    LXI H, data_entity_xcoords  ; 0x167A
    PUSH PSW                    ; 0x167D
    CALL func_hl_add_a          ; 0x167E
    DCR M                       ; 0x1681
    POP PSW                     ; 0x1682
    MOV D, M                    ; 0x1683
    LXI H, data_entity_ycoords  ; 0x1684
    PUSH PSW                    ; 0x1687
    CALL func_hl_add_a          ; 0x1688
    MOV E, M                    ; 0x168B
    LDA var_page_flip           ; 0x168C
    ADI 0Eh                     ; 0x168F
    ADD A                       ; 0x1691
    ADD A                       ; 0x1692
    MOV C, A                    ; 0x1693
    MVI B, 00h                  ; 0x1694
    LXI H, data_tile_graphics   ; 0x1696
    DAD B                       ; 0x1699
    CALL func_draw_tile_to_buf  ; 0x169A
    POP PSW                     ; 0x169D
    LXI H, data_entity_ycoords  ; 0x169E
    CALL func_hl_add_a          ; 0x16A1
    LDA var_player_row          ; 0x16A4
    MOV B, A                    ; 0x16A7
    MOV A, M                    ; 0x16A8
    CMP B                       ; 0x16A9
    PUSH PSW                    ; 0x16AA
    LDA var_entity_index        ; 0x16AB
    LXI H, 0919h                ; 0x16AE
    CALL func_hl_add_a          ; 0x16B1
    POP PSW                     ; 0x16B4
    JC loc_16BB                 ; 0x16B5
    MVI M, 07h                  ; 0x16B8
    RET                         ; 0x16BA
loc_16BB:
    MVI M, 08h                  ; 0x16BB
    RET                         ; 0x16BD
loc_16BE:
    LDA var_entity_index        ; 0x16BE
    LXI H, data_entity_xcoords  ; 0x16C1
    PUSH PSW                    ; 0x16C4
    CALL func_hl_add_a          ; 0x16C5
    POP PSW                     ; 0x16C8
    MOV D, M                    ; 0x16C9
    DCR D                       ; 0x16CA
    LXI H, data_entity_ycoords  ; 0x16CB
    PUSH PSW                    ; 0x16CE
    CALL func_hl_add_a          ; 0x16CF
    MOV E, M                    ; 0x16D2
    LXI H, 270Ah                ; 0x16D3
    CALL func_draw_tile_to_buf  ; 0x16D6
    POP PSW                     ; 0x16D9
    LXI H, data_entity_xcoords  ; 0x16DA
    PUSH PSW                    ; 0x16DD
    CALL func_hl_add_a          ; 0x16DE
    POP PSW                     ; 0x16E1
    MOV D, M                    ; 0x16E2
    LXI H, data_entity_ycoords  ; 0x16E3
    CALL func_hl_add_a          ; 0x16E6
    MOV E, M                    ; 0x16E9
    LXI H, data_tile_graphics   ; 0x16EA
    LDA var_page_flip           ; 0x16ED
    ADI 0Eh                     ; 0x16F0
    ADD A                       ; 0x16F2
    ADD A                       ; 0x16F3
    MOV C, A                    ; 0x16F4
    MVI B, 00h                  ; 0x16F5
    DAD B                       ; 0x16F7
    CALL func_draw_tile_to_buf  ; 0x16F8
    RET                         ; 0x16FB
