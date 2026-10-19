; Функция: func_entity_state1
; Адрес: 0x1489
; Размер: 112 байт
; Описание: Обработчик сущности в состоянии 1 (движение вправо). A=var_entity_index;
;           data_entity_xcoords[idx]++ -> D; data_entity_ycoords[idx] -> E;
;           CALL func_coords_to_textbuf (HL=адрес клетки). Проверка клетки справа
;           (HL+1) и ниже (HL+0020h) на пустоту (0x20): если не пусто -> loc_14B1
;           (откат x--, состояние=2). Если путь свободен (loc_14C6): стереть старую
;           позицию тайлом 270Ah и нарисовать сущность тайлом 2756h
;           (func_draw_tile_to_buf).

func_entity_state1:
    LDA var_entity_index        ; 0x1489
    PUSH PSW                    ; 0x148C
    LXI H, data_entity_xcoords  ; 0x148D
    CALL func_hl_add_a          ; 0x1490
    INR M                       ; 0x1493
    MOV D, M                    ; 0x1494
    POP PSW                     ; 0x1495
    LXI H, data_entity_ycoords  ; 0x1496
    CALL func_hl_add_a          ; 0x1499
    MOV E, M                    ; 0x149C
    CALL func_coords_to_textbuf ; 0x149D
    INX H                       ; 0x14A0
    MOV A, M                    ; 0x14A1
    CPI 20h                     ; 0x14A2
    JNZ loc_14B1                ; 0x14A4
    LXI B, 0020h                ; 0x14A7
    DAD B                       ; 0x14AA
    MOV A, M                    ; 0x14AB
    CPI 20h                     ; 0x14AC
    JZ loc_14C6                 ; 0x14AE
loc_14B1:
    LDA var_entity_index        ; 0x14B1
    LXI H, data_entity_xcoords  ; 0x14B4
    PUSH PSW                    ; 0x14B7
    CALL func_hl_add_a          ; 0x14B8
    DCR M                       ; 0x14BB
    POP PSW                     ; 0x14BC
    LXI H, 0919h                ; 0x14BD
    CALL func_hl_add_a          ; 0x14C0
    MVI M, 02h                  ; 0x14C3
    RET                         ; 0x14C5
loc_14C6:
    LDA var_entity_index        ; 0x14C6
    LXI H, data_entity_xcoords  ; 0x14C9
    PUSH PSW                    ; 0x14CC
    CALL func_hl_add_a          ; 0x14CD
    POP PSW                     ; 0x14D0
    MOV D, M                    ; 0x14D1
    DCR D                       ; 0x14D2
    LXI H, data_entity_ycoords  ; 0x14D3
    PUSH PSW                    ; 0x14D6
    CALL func_hl_add_a          ; 0x14D7
    MOV E, M                    ; 0x14DA
    LXI H, 270Ah                ; 0x14DB
    CALL func_draw_tile_to_buf  ; 0x14DE
    POP PSW                     ; 0x14E1
    LXI H, data_entity_xcoords  ; 0x14E2
    PUSH PSW                    ; 0x14E5
    CALL func_hl_add_a          ; 0x14E6
    POP PSW                     ; 0x14E9
    MOV D, M                    ; 0x14EA
    LXI H, data_entity_ycoords  ; 0x14EB
    CALL func_hl_add_a          ; 0x14EE
    MOV E, M                    ; 0x14F1
    LXI H, 2756h                ; 0x14F2
    CALL func_draw_tile_to_buf  ; 0x14F5
    RET                         ; 0x14F8
