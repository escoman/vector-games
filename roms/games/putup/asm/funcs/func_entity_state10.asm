; Функция: func_entity_state10
; Адрес: 0x191B
; Размер: 97 байт
; Описание: Обработчик сущности в состоянии 10 (ожидание/цель). Если
;           координата 0923h (data_entity_ycoords+1) >= 17h -> loc_1958.
;           Иначе рисует тайл: 090Ch=08h, сравнение текущей позиции 08E7h с
;           (0920h,0923h); если отличается -> стереть старую (func_draw_tile_at_ptr),
;           сохранить новую в 08E7h и отрисовать тайл из data_tile_table_26DE
;           (func_render_tile_vram). Затем вычисление |dx|,|dy| между
;           var_player_col/var_player_row и сущностью (0920h/0923h); если обе
;           разности >= 2 -> RNC (возврат), иначе JMP 13AAh (обработчик потери
;           жизни, вне RDB). Вспомогательная loc_1979: A = -A (CMA/INR A).

func_entity_state10:
    LDA 0923h                   ; 0x191B
    CPI 17h                     ; 0x191E
    JNC loc_1958                ; 0x1920
    MVI A, 08h                  ; 0x1923
    STA 090Ch                   ; 0x1925
    LXI H, 08E7h                ; 0x1928
    LDA 0923h                   ; 0x192B
    CMP M                       ; 0x192E
    JNZ loc_193B                ; 0x192F
    INX H                       ; 0x1932
    LDA 0920h                   ; 0x1933
    CMP M                       ; 0x1936
    DCX H                       ; 0x1937
    JZ loc_193E                 ; 0x1938
loc_193B:
    CALL func_draw_tile_at_ptr  ; 0x193B
loc_193E:
    LDA 0923h                   ; 0x193E
    MOV L, A                    ; 0x1941
    LDA 0920h                   ; 0x1942
    MOV H, A                    ; 0x1945
    SHLD 08E7h                  ; 0x1946
    XCHG                        ; 0x1949
    LDA 090Ch                   ; 0x194A
    ADD A                       ; 0x194D
    ADD A                       ; 0x194E
    LXI H, data_tile_table_26DE ; 0x194F
    CALL func_hl_add_a          ; 0x1952
    CALL func_render_tile_vram  ; 0x1955
loc_1958:
    LDA 0920h                   ; 0x1958
    MOV B, A                    ; 0x195B
    LDA var_player_col          ; 0x195C
    SUB B                       ; 0x195F
    CC loc_1979                 ; 0x1960
    MOV D, A                    ; 0x1963
    LDA 0923h                   ; 0x1964
    MOV B, A                    ; 0x1967
    LDA var_player_row          ; 0x1968
    SUB B                       ; 0x196B
    CC loc_1979                 ; 0x196C
    CPI 02h                     ; 0x196F
    RNC                         ; 0x1971
    MOV A, D                    ; 0x1972
    CPI 02h                     ; 0x1973
    RNC                         ; 0x1975
    JMP 13AAh                   ; 0x1976
loc_1979:
    CMA                         ; 0x1979
    INR A                       ; 0x197A
    RET                         ; 0x197B
