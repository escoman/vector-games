; Функция: func_load_gfx_2761
; Адрес: 0x04CD
; Размер: 78 байт
; Описание: Копирует графику из data_gfx_2761@0x2761 в data_glyph_block@0x6000.
;           HL=2761h (источник, читается в обратном порядке DCX H), BC=6000h
;           (приёмник, INX B), DE=0008h. Внешний цикл loc_04D6 по D (8 строк);
;           4 внутренних блока по 8 байт (loc_04D6/04E6/04F6/0506) с шагом HL
;           через PUSH B / LXI B,0008h / DAD B; в конце DCR D, HL += 0010h,
;           JNZ loc_04D6. Заполняет блок глифов упакованной графикой.

func_load_gfx_2761:
    LXI H, data_gfx_2761        ; 0x04CD
    LXI B, data_glyph_block     ; 0x04D0
    LXI D, 0008h                ; 0x04D3
loc_04D6:
    MOV A, M                    ; 0x04D6
    STAX B                      ; 0x04D7
    DCX H                       ; 0x04D8
    INX B                       ; 0x04D9
    DCR E                       ; 0x04DA
    JNZ loc_04D6                ; 0x04DB
    PUSH B                      ; 0x04DE
    LXI B, 0008h                ; 0x04DF
    DAD B                       ; 0x04E2
    POP B                       ; 0x04E3
    MVI E, 08h                  ; 0x04E4
loc_04E6:
    MOV A, M                    ; 0x04E6
    STAX B                      ; 0x04E7
    DCX H                       ; 0x04E8
    INX B                       ; 0x04E9
    DCR E                       ; 0x04EA
    JNZ loc_04E6                ; 0x04EB
    PUSH B                      ; 0x04EE
    LXI B, 0008h                ; 0x04EF
    DAD B                       ; 0x04F2
    POP B                       ; 0x04F3
    MVI E, 08h                  ; 0x04F4
loc_04F6:
    MOV A, M                    ; 0x04F6
    STAX B                      ; 0x04F7
    DCX H                       ; 0x04F8
    INX B                       ; 0x04F9
    DCR E                       ; 0x04FA
    JNZ loc_04F6                ; 0x04FB
    PUSH B                      ; 0x04FE
    LXI B, 0008h                ; 0x04FF
    DAD B                       ; 0x0502
    POP B                       ; 0x0503
    MVI E, 08h                  ; 0x0504
loc_0506:
    MOV A, M                    ; 0x0506
    STAX B                      ; 0x0507
    DCX H                       ; 0x0508
    INX B                       ; 0x0509
    DCR E                       ; 0x050A
    JNZ loc_0506                ; 0x050B
    DCR D                       ; 0x050E
    MVI E, 08h                  ; 0x050F
    PUSH B                      ; 0x0511
    LXI B, 0010h                ; 0x0512
    DAD B                       ; 0x0515
    POP B                       ; 0x0516
    JNZ loc_04D6                ; 0x0517
    RET                         ; 0x051A
