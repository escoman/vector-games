; Функция: func_entity_state2
; Адрес: 0x14F9
; Размер: 111 байт
; Описание: Обработчик сущности в состоянии 2 (движение влево). Зеркален
;           func_entity_state1: data_entity_xcoords[idx]-- -> D; координата Y -> E;
;           CALL func_coords_to_textbuf. Проверка текущей клетки и клетки ниже
;           (HL+0020h) на пустоту (0x20): если не пусто -> loc_1520 (откат x++,
;           состояние=1). Если свободно (loc_1535): стереть старую позицию тайлом
;           270Ah и нарисовать сущность тайлом 2752h.

func_entity_state2:
    LDA var_entity_index        ; 0x14F9
    PUSH PSW                    ; 0x14FC
    LXI H, data_entity_xcoords  ; 0x14FD
    CALL func_hl_add_a          ; 0x1500
    DCR M                       ; 0x1503
    MOV D, M                    ; 0x1504
    POP PSW                     ; 0x1505
    LXI H, data_entity_ycoords  ; 0x1506
    CALL func_hl_add_a          ; 0x1509
    MOV E, M                    ; 0x150C
    CALL func_coords_to_textbuf ; 0x150D
    MOV A, M                    ; 0x1510
    CPI 20h                     ; 0x1511
    JNZ loc_1520                ; 0x1513
    LXI B, 0020h                ; 0x1516
    DAD B                       ; 0x1519
    MOV A, M                    ; 0x151A
    CPI 20h                     ; 0x151B
    JZ loc_1535                 ; 0x151D
loc_1520:
    LDA var_entity_index        ; 0x1520
    LXI H, data_entity_xcoords  ; 0x1523
    PUSH PSW                    ; 0x1526
    CALL func_hl_add_a          ; 0x1527
    INR M                       ; 0x152A
    POP PSW                     ; 0x152B
    LXI H, 0919h                ; 0x152C
    CALL func_hl_add_a          ; 0x152F
    MVI M, 01h                  ; 0x1532
    RET                         ; 0x1534
loc_1535:
    LDA var_entity_index        ; 0x1535
    LXI H, data_entity_xcoords  ; 0x1538
    PUSH PSW                    ; 0x153B
    CALL func_hl_add_a          ; 0x153C
    POP PSW                     ; 0x153F
    MOV D, M                    ; 0x1540
    INR D                       ; 0x1541
    LXI H, data_entity_ycoords  ; 0x1542
    PUSH PSW                    ; 0x1545
    CALL func_hl_add_a          ; 0x1546
    MOV E, M                    ; 0x1549
    LXI H, 270Ah                ; 0x154A
    CALL func_draw_tile_to_buf  ; 0x154D
    POP PSW                     ; 0x1550
    LXI H, data_entity_xcoords  ; 0x1551
    PUSH PSW                    ; 0x1554
    CALL func_hl_add_a          ; 0x1555
    POP PSW                     ; 0x1558
    MOV D, M                    ; 0x1559
    LXI H, data_entity_ycoords  ; 0x155A
    CALL func_hl_add_a          ; 0x155D
    MOV E, M                    ; 0x1560
    LXI H, 2752h                ; 0x1561
    CALL func_draw_tile_to_buf  ; 0x1564
    RET                         ; 0x1567
