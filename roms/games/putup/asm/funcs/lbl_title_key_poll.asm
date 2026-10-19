; Метка: lbl_title_key_poll
; Адрес: 0x0C65
; Размер: 62 байта (0x0C65-0x0CA2)
; Описание: Цикл ожидания нажатия пробела на заставке (Stage 6 step 2).
;           LXI B,0C00h (таймаут=3072). Цикл опроса loc_0C68: XRA A; PUSH B;
;           CALL func_check_start_key; POP B; ORA A; JNZ loc_0C9D (пробел/SHIFT
;           нажат). Иначе DCX B; MOV A,C; ORA B; JNZ loc_0C68 (отсчёт таймаута).
;           По таймауту: бегущая строка в буфере 5180h (32 символа, переключение
;           'u'(75h)<->0FEh через func_draw_char_at_hl), затем JMP lbl_title_key_poll.
;           При нажатии (loc_0C9D): CALL func_music_start_track; JMP func_level_loader.

lbl_title_key_poll:
    LXI B, 0C00h                ; 0x0C65
loc_0C68:
    XRA A                       ; 0x0C68
    PUSH B                      ; 0x0C69
    CALL func_check_start_key   ; 0x0C6A
    POP B                       ; 0x0C6D
    ORA A                       ; 0x0C6E
    JNZ loc_0C9D                ; 0x0C6F
    DCX B                       ; 0x0C72
    MOV A, C                    ; 0x0C73
    ORA B                       ; 0x0C74
    JNZ loc_0C68                ; 0x0C75
    LXI H, 5180h                ; 0x0C78
    MVI B, 20h                  ; 0x0C7B
loc_0C7D:
    MOV A, M                    ; 0x0C7D
    CPI 75h                     ; 0x0C7E
    JZ loc_0C90                 ; 0x0C80
    CPI 0FEh                    ; 0x0C83
    JNZ loc_0C95                ; 0x0C85
    MVI A, 75h                  ; 0x0C88
    CALL func_draw_char_at_hl   ; 0x0C8A
    JMP loc_0C95                ; 0x0C8D
loc_0C90:
    MVI A, 0FEh                 ; 0x0C90
    CALL func_draw_char_at_hl   ; 0x0C92
loc_0C95:
    INX H                       ; 0x0C95
    DCR B                       ; 0x0C96
    JNZ loc_0C7D                ; 0x0C97
    JMP lbl_title_key_poll      ; 0x0C9A
loc_0C9D:
    CALL func_music_start_track ; 0x0C9D
    JMP func_level_loader       ; 0x0CA0
