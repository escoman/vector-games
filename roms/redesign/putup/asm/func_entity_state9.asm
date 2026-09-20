; Функция: func_entity_state9
; Адрес: 0x18FE
; Размер: 29 байт
; Описание: Обработчик сущности в состоянии 9 (сближение с игроком).
;           Шаг второй координаты сущности 0920h (data_entity_xcoords+1) к
;           var_player_col: если col >= x -> x++, иначе x--. Затем шаг
;           координаты 0923h (data_entity_ycoords+1) к var_player_row:
;           если row >= y -> y++, иначе y--.

func_entity_state9:
    LXI H, 0920h                ; 0x18FE
    LDA var_player_col          ; 0x1901
    CMP M                       ; 0x1904
    JNC loc_190C                ; 0x1905
    DCR M                       ; 0x1908
    JMP loc_190D                ; 0x1909
loc_190C:
    INR M                       ; 0x190C
loc_190D:
    LXI H, 0923h                ; 0x190D
    LDA var_player_row          ; 0x1910
    CMP M                       ; 0x1913
    JNC loc_1919                ; 0x1914
    DCR M                       ; 0x1917
    RET                         ; 0x1918
loc_1919:
    INR M                       ; 0x1919
    RET                         ; 0x191A
