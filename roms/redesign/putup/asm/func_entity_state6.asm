; Функция: func_entity_state6
; Адрес: 0x16FC
; Размер: 172 байта
; Описание: Обработчик сущности в состоянии 6 (движение влево с поворотом).
;           data_entity_xcoords[idx]-- -> D; data_entity_ycoords[idx] -> E;
;           CALL func_coords_to_textbuf. Проверка текущей клетки и клетки ниже
;           (HL+0020h) на пустоту (0x20). Если не пусто -> loc_1723 (откат x++,
;           перерисовка клетки тайлом data_tile_graphics со смещением от
;           var_page_flip: A=(var_page_flip+0Eh)*4, HL=2706h+BC). Затем
;           сравнение data_entity_ycoords[idx] с var_player_row: если y>=row
;           состояние=07h, иначе 08h. Если путь свободен (loc_176A): стереть
;           старую позицию тайлом 270Ah и нарисовать новую.

func_entity_state6:
    LDA var_entity_index        ; 0x16FC
    PUSH PSW                    ; 0x16FF
    LXI H, data_entity_xcoords  ; 0x1700
    CALL func_hl_add_a          ; 0x1703
    DCR M                       ; 0x1706
    MOV D, M                    ; 0x1707
    POP PSW                     ; 0x1708
    LXI H, data_entity_ycoords  ; 0x1709
    CALL func_hl_add_a          ; 0x170C
    MOV E, M                    ; 0x170F
    CALL func_coords_to_textbuf ; 0x1710
    MOV A, M                    ; 0x1713
    CPI 20h                     ; 0x1714
    JNZ loc_1723                ; 0x1716
    LXI B, 0020h                ; 0x1719
    DAD B                       ; 0x171C
    MOV A, M                    ; 0x171D
    CPI 20h                     ; 0x171E
    JZ loc_176A                 ; 0x1720
loc_1723:
    LDA var_entity_index        ; 0x1723
    LXI H, data_entity_xcoords  ; 0x1726
    PUSH PSW                    ; 0x1729
    CALL func_hl_add_a          ; 0x172A
    INR M                       ; 0x172D
    POP PSW                     ; 0x172E
    MOV D, M                    ; 0x172F
    LXI H, data_entity_ycoords  ; 0x1730
    PUSH PSW                    ; 0x1733
    CALL func_hl_add_a          ; 0x1734
    MOV E, M                    ; 0x1737
    LDA var_page_flip           ; 0x1738
    ADI 0Eh                     ; 0x173B
    ADD A                       ; 0x173D
    ADD A                       ; 0x173E
    MOV C, A                    ; 0x173F
    MVI B, 00h                  ; 0x1740
    LXI H, data_tile_graphics   ; 0x1742
    DAD B                       ; 0x1745
    CALL func_draw_tile_to_buf  ; 0x1746
    POP PSW                     ; 0x1749
    LXI H, data_entity_ycoords  ; 0x174A
    CALL func_hl_add_a          ; 0x174D
    LDA var_player_row          ; 0x1750
    MOV B, A                    ; 0x1753
    MOV A, M                    ; 0x1754
    CMP B                       ; 0x1755
    PUSH PSW                    ; 0x1756
    LDA var_entity_index        ; 0x1757
    LXI H, 0919h                ; 0x175A
    CALL func_hl_add_a          ; 0x175D
    POP PSW                     ; 0x1760
    JC loc_1767                 ; 0x1761
    MVI M, 07h                  ; 0x1764
    RET                         ; 0x1766
loc_1767:
    MVI M, 08h                  ; 0x1767
    RET                         ; 0x1769
loc_176A:
    LDA var_entity_index        ; 0x176A
    LXI H, data_entity_xcoords  ; 0x176D
    PUSH PSW                    ; 0x1770
    CALL func_hl_add_a          ; 0x1771
    POP PSW                     ; 0x1774
    MOV D, M                    ; 0x1775
    INR D                       ; 0x1776
    LXI H, data_entity_ycoords  ; 0x1777
    PUSH PSW                    ; 0x177A
    CALL func_hl_add_a          ; 0x177B
    MOV E, M                    ; 0x177E
    LXI H, 270Ah                ; 0x177F
    CALL func_draw_tile_to_buf  ; 0x1782
    POP PSW                     ; 0x1785
    LXI H, data_entity_xcoords  ; 0x1786
    PUSH PSW                    ; 0x1789
    CALL func_hl_add_a          ; 0x178A
    POP PSW                     ; 0x178D
    MOV D, M                    ; 0x178E
    LXI H, data_entity_ycoords  ; 0x178F
    CALL func_hl_add_a          ; 0x1792
    MOV E, M                    ; 0x1795
    LXI H, data_tile_graphics   ; 0x1796
    LDA var_page_flip           ; 0x1799
    ADI 0Eh                     ; 0x179C
    ADD A                       ; 0x179E
    ADD A                       ; 0x179F
    MOV C, A                    ; 0x17A0
    MVI B, 00h                  ; 0x17A1
    DAD B                       ; 0x17A3
    CALL func_draw_tile_to_buf  ; 0x17A4
    RET                         ; 0x17A7
