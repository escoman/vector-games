; Функция: func_blit_plane_mask40
; Адрес: 0x045E
; Размер: 37 байт
; Описание: Копирует 8 байт из (DE) в (HL) с побитовой маской 40h/04h (плоскость 2).
;           Структура идентична func_blit_plane_mask80, но маски ANI 40h и ANI 04h.
;           C=08h; loc_0460: LDAX D, DCX D, C=A; A=(HL), CMA, B=A; маска 40h ->
;           loc_0470; маска 04h -> loc_047A (ORA M); MOV M,A; INX H; DCR C; JNZ loc_0460.

func_blit_plane_mask40:
    MVI C, 08h                  ; 0x045E
loc_0460:
    PUSH B                      ; 0x0460
    LDAX D                      ; 0x0461
    DCX D                       ; 0x0462
    MOV C, A                    ; 0x0463
    MOV A, M                    ; 0x0464
    CMA                         ; 0x0465
    MOV B, A                    ; 0x0466
    MOV A, C                    ; 0x0467
    ANI 40h                     ; 0x0468
    MVI A, 00h                  ; 0x046A
    JZ loc_0470                 ; 0x046C
    MOV A, M                    ; 0x046F
loc_0470:
    MOV M, A                    ; 0x0470
    MOV A, C                    ; 0x0471
    ANI 04h                     ; 0x0472
    MVI A, 00h                  ; 0x0474
    JZ loc_047A                 ; 0x0476
    MOV A, B                    ; 0x0479
loc_047A:
    ORA M                       ; 0x047A
    MOV M, A                    ; 0x047B
    INX H                       ; 0x047C
    POP B                       ; 0x047D
    DCR C                       ; 0x047E
    JNZ loc_0460                ; 0x047F
    RET                         ; 0x0482
