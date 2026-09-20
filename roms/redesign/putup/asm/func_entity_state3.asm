; Функция: func_entity_state3
; Адрес: 0x1568
; Размер: 119 байт
; Описание: Обработчик сущности в состоянии 3 (движение вверх). data_entity_ycoords[idx]--
;           -> E; data_entity_xcoords[idx] -> D; CALL func_coords_to_textbuf.
;           Проверка текущей клетки и клетки справа (HL+1) на пустоту (0x20):
;           если не пусто -> loc_158C (откат y++, состояние=4). Если свободно
;           (loc_15A1): стереть старую позицию тайлом 270Ah, затем нарисовать
;           сущность тайлом из data_tile_graphics со смещением, зависящим от
;           var_page_flip (A=(var_page_flip+10h)*4; HL=2706h+BC).

func_entity_state3:
    LDA var_entity_index        ; 0x1568
    PUSH PSW                    ; 0x156B
    LXI H, data_entity_ycoords  ; 0x156C
    CALL func_hl_add_a          ; 0x156F
    DCR M                       ; 0x1572
    MOV E, M                    ; 0x1573
    POP PSW                     ; 0x1574
    LXI H, data_entity_xcoords  ; 0x1575
    CALL func_hl_add_a          ; 0x1578
    MOV D, M                    ; 0x157B
    CALL func_coords_to_textbuf ; 0x157C
    MOV A, M                    ; 0x157F
    CPI 20h                     ; 0x1580
    JNZ loc_158C                ; 0x1582
    INX H                       ; 0x1585
    MOV A, M                    ; 0x1586
    CPI 20h                     ; 0x1587
    JZ loc_15A1                 ; 0x1589
loc_158C:
    LDA var_entity_index        ; 0x158C
    LXI H, data_entity_ycoords  ; 0x158F
    PUSH PSW                    ; 0x1592
    CALL func_hl_add_a          ; 0x1593
    INR M                       ; 0x1596
    POP PSW                     ; 0x1597
    LXI H, 0919h                ; 0x1598
    CALL func_hl_add_a          ; 0x159B
    MVI M, 04h                  ; 0x159E
    RET                         ; 0x15A0
loc_15A1:
    LDA var_entity_index        ; 0x15A1
    LXI H, data_entity_xcoords  ; 0x15A4
    PUSH PSW                    ; 0x15A7
    CALL func_hl_add_a          ; 0x15A8
    POP PSW                     ; 0x15AB
    MOV D, M                    ; 0x15AC
    LXI H, data_entity_ycoords  ; 0x15AD
    PUSH PSW                    ; 0x15B0
    CALL func_hl_add_a          ; 0x15B1
    MOV E, M                    ; 0x15B4
    INR E                       ; 0x15B5
    LXI H, 270Ah                ; 0x15B6
    CALL func_draw_tile_to_buf  ; 0x15B9
    POP PSW                     ; 0x15BC
    LXI H, data_entity_xcoords  ; 0x15BD
    PUSH PSW                    ; 0x15C0
    CALL func_hl_add_a          ; 0x15C1
    POP PSW                     ; 0x15C4
    MOV D, M                    ; 0x15C5
    LXI H, data_entity_ycoords  ; 0x15C6
    CALL func_hl_add_a          ; 0x15C9
    MOV E, M                    ; 0x15CC
    LDA var_page_flip           ; 0x15CD
    ADI 10h                     ; 0x15D0
    ADD A                       ; 0x15D2
    ADD A                       ; 0x15D3
    MOV C, A                    ; 0x15D4
    MVI B, 00h                  ; 0x15D5
    LXI H, data_tile_graphics   ; 0x15D7
    DAD B                       ; 0x15DA
    CALL func_draw_tile_to_buf  ; 0x15DB
    RET                         ; 0x15DE
