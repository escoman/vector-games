; Функция: func_blit_plane_mask20
; Адрес: 0x0483
; Размер: 37 байт
; Описание: Копирует 8 байт из (DE) в (HL) с побитовой маской 20h/02h (плоскость 1).
;           Структура идентична func_blit_plane_mask80, но маски ANI 20h и ANI 02h.
;           C=08h; loc_0485: LDAX D, DCX D, C=A; A=(HL), CMA, B=A; маска 20h ->
;           loc_0495; маска 02h -> loc_049F (ORA M); MOV M,A; INX H; DCR C; JNZ loc_0485.

func_blit_plane_mask20:
    MVI C, 08h                  ; 0x0483
loc_0485:
    PUSH B                      ; 0x0485
    LDAX D                      ; 0x0486
    DCX D                       ; 0x0487
    MOV C, A                    ; 0x0488
    MOV A, M                    ; 0x0489
    CMA                         ; 0x048A
    MOV B, A                    ; 0x048B
    MOV A, C                    ; 0x048C
    ANI 20h                     ; 0x048D
    MVI A, 00h                  ; 0x048F
    JZ loc_0495                 ; 0x0491
    MOV A, M                    ; 0x0494
loc_0495:
    MOV M, A                    ; 0x0495
    MOV A, C                    ; 0x0496
    ANI 02h                     ; 0x0497
    MVI A, 00h                  ; 0x0499
    JZ loc_049F                 ; 0x049B
    MOV A, B                    ; 0x049E
loc_049F:
    ORA M                       ; 0x049F
    MOV M, A                    ; 0x04A0
    INX H                       ; 0x04A1
    POP B                       ; 0x04A2
    DCR C                       ; 0x04A3
    JNZ loc_0485                ; 0x04A4
    RET                         ; 0x04A7
