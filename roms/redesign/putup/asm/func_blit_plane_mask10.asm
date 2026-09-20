; Функция: func_blit_plane_mask10
; Адрес: 0x04A8
; Размер: 37 байт
; Описание: Копирует 8 байт из (DE) в (HL) с побитовой маской 10h/01h (плоскость 0).
;           Структура идентична func_blit_plane_mask80, но маски ANI 10h и ANI 01h.
;           C=08h; loc_04AA: LDAX D, DCX D, C=A; A=(HL), CMA, B=A; маска 10h ->
;           loc_04BA; маска 01h -> loc_04C4 (ORA M); MOV M,A; INX H; DCR C; JNZ loc_04AA.

func_blit_plane_mask10:
    MVI C, 08h                  ; 0x04A8
loc_04AA:
    PUSH B                      ; 0x04AA
    LDAX D                      ; 0x04AB
    DCX D                       ; 0x04AC
    MOV C, A                    ; 0x04AD
    MOV A, M                    ; 0x04AE
    CMA                         ; 0x04AF
    MOV B, A                    ; 0x04B0
    MOV A, C                    ; 0x04B1
    ANI 10h                     ; 0x04B2
    MVI A, 00h                  ; 0x04B4
    JZ loc_04BA                 ; 0x04B6
    MOV A, M                    ; 0x04B9
loc_04BA:
    MOV M, A                    ; 0x04BA
    MOV A, C                    ; 0x04BB
    ANI 01h                     ; 0x04BC
    MVI A, 00h                  ; 0x04BE
    JZ loc_04C4                 ; 0x04C0
    MOV A, B                    ; 0x04C3
loc_04C4:
    ORA M                       ; 0x04C4
    MOV M, A                    ; 0x04C5
    INX H                       ; 0x04C6
    POP B                       ; 0x04C7
    DCR C                       ; 0x04C8
    JNZ loc_04AA                ; 0x04C9
    RET                         ; 0x04CC
