; Функция: func_entity_state4
; Адрес: 0x15DF
; Размер: 112 байт
; Описание: Обработчик сущности в состоянии 4 (движение вниз). data_entity_ycoords[idx]++
;           -> E; data_entity_xcoords[idx] -> D; CALL func_coords_to_textbuf;
;           HL+=0020h (клетка ниже). Проверка клетки ниже и справа (HL+1) на пустоту
;           (0x20): если не пусто -> loc_1607 (откат y--, состояние=3). Если свободно
;           (loc_161C): стереть старую позицию тайлом 270Ah, нарисовать сущность
;           тайлом 274Ah.

func_entity_state4:
    LDA var_entity_index        ; 0x15DF
    PUSH PSW                    ; 0x15E2
    LXI H, data_entity_ycoords  ; 0x15E3
    CALL func_hl_add_a          ; 0x15E6
    INR M                       ; 0x15E9
    MOV E, M                    ; 0x15EA
    POP PSW                     ; 0x15EB
    LXI H, data_entity_xcoords  ; 0x15EC
    CALL func_hl_add_a          ; 0x15EF
    MOV D, M                    ; 0x15F2
    CALL func_coords_to_textbuf ; 0x15F3
    LXI B, 0020h                ; 0x15F6
    DAD B                       ; 0x15F9
    MOV A, M                    ; 0x15FA
    CPI 20h                     ; 0x15FB
    JNZ loc_1607                ; 0x15FD
    INX H                       ; 0x1600
    MOV A, M                    ; 0x1601
    CPI 20h                     ; 0x1602
    JZ loc_161C                 ; 0x1604
loc_1607:
    LDA var_entity_index        ; 0x1607
    LXI H, data_entity_ycoords  ; 0x160A
    PUSH PSW                    ; 0x160D
    CALL func_hl_add_a          ; 0x160E
    DCR M                       ; 0x1611
    POP PSW                     ; 0x1612
    LXI H, 0919h                ; 0x1613
    CALL func_hl_add_a          ; 0x1616
    MVI M, 03h                  ; 0x1619
    RET                         ; 0x161B
loc_161C:
    LDA var_entity_index        ; 0x161C
    LXI H, data_entity_xcoords  ; 0x161F
    PUSH PSW                    ; 0x1622
    CALL func_hl_add_a          ; 0x1623
    POP PSW                     ; 0x1626
    MOV D, M                    ; 0x1627
    LXI H, data_entity_ycoords  ; 0x1628
    PUSH PSW                    ; 0x162B
    CALL func_hl_add_a          ; 0x162C
    MOV E, M                    ; 0x162F
    DCR E                       ; 0x1630
    LXI H, 270Ah                ; 0x1631
    CALL func_draw_tile_to_buf  ; 0x1634
    POP PSW                     ; 0x1637
    LXI H, data_entity_xcoords  ; 0x1638
    PUSH PSW                    ; 0x163B
    CALL func_hl_add_a          ; 0x163C
    POP PSW                     ; 0x163F
    MOV D, M                    ; 0x1640
    LXI H, data_entity_ycoords  ; 0x1641
    CALL func_hl_add_a          ; 0x1644
    MOV E, M                    ; 0x1647
    LXI H, 274Ah                ; 0x1648
    CALL func_draw_tile_to_buf  ; 0x164B
    RET                         ; 0x164E
