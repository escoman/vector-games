; Функция: func_vblank_isr
; Адрес: 0x03A4
; Размер: 93 байт
; Описание: Обработчик прерывания RST7 (кадровый). Сохраняет H/D/B/PSW;
;           INR var_frame_counter. Если var_palette_timer != 0: DCR M и цикл
;           вывода палитры (DE=100Fh итераций): OUT 02h (регистр E), OUT 0Ch
;           (данные по (HL)), DCX H, JNZ loc_03BB. Затем скан клавиатуры:
;           OUT 00h=8Ah; HL=data_kbd_matrix; A=0FEh; цикл loc_03DA: OUT 03h
;           (строка), IN 02h (столбцы), MOV M,A, INX H, RLC, JC loc_03DA (8 строк).
;           OUT 00h=88h; OUT 01h=02h; OUT 03h=var_scroll; OUT 02h=var_portb_mode;
;           CALL func_music_tick; восстанавливает регистры; EI; RET.

func_vblank_isr:
    PUSH H                      ; 0x03A4
    PUSH D                      ; 0x03A5
    PUSH B                      ; 0x03A6
    PUSH PSW                    ; 0x03A7
    LXI H, var_frame_counter    ; 0x03A8
    INR M                       ; 0x03AB
    LXI H, var_palette_timer    ; 0x03AC
    XRA A                       ; 0x03AF
    CMP M                       ; 0x03B0
    JZ loc_03D1                 ; 0x03B1
    DCR M                       ; 0x03B4
    LXI D, 100Fh                ; 0x03B5
    LHLD var_palette_ptr        ; 0x03B8
loc_03BB:
    MOV A, E                    ; 0x03BB
    OUT 02h                     ; 0x03BC
    MOV A, M                    ; 0x03BE
    OUT 0Ch                     ; 0x03BF
    DCR C                       ; 0x03C1
    OUT 0Ch                     ; 0x03C2
    NOP                         ; 0x03C4
    NOP                         ; 0x03C5
    NOP                         ; 0x03C6
    DCX H                       ; 0x03C7
    OUT 0Ch                     ; 0x03C8
    DCR E                       ; 0x03CA
    DCR D                       ; 0x03CB
    OUT 0Ch                     ; 0x03CC
    JNZ loc_03BB                ; 0x03CE
loc_03D1:
    MVI A, 8Ah                  ; 0x03D1
    OUT 00h                     ; 0x03D3
    LXI H, data_kbd_matrix      ; 0x03D5
    MVI A, 0FEh                 ; 0x03D8
loc_03DA:
    PUSH PSW                    ; 0x03DA
    OUT 03h                     ; 0x03DB
    IN 02h                      ; 0x03DD
    MOV M, A                    ; 0x03DF
    POP PSW                     ; 0x03E0
    INX H                       ; 0x03E1
    RLC                         ; 0x03E2
    JC loc_03DA                 ; 0x03E3
    MVI A, 88h                  ; 0x03E6
    OUT 00h                     ; 0x03E8
    MVI A, 02h                  ; 0x03EA
    OUT 01h                     ; 0x03EC
    LDA var_scroll              ; 0x03EE
    OUT 03h                     ; 0x03F1
    LDA var_portb_mode          ; 0x03F3
    OUT 02h                     ; 0x03F6
    CALL func_music_tick        ; 0x03F8
    POP PSW                     ; 0x03FB
    POP B                       ; 0x03FC
    POP D                       ; 0x03FD
    POP H                       ; 0x03FE
    EI                          ; 0x03FF
    RET                         ; 0x0400
