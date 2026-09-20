; Функция: func_blit_plane_mask80
; Адрес: 0x0439
; Размер: 37 байт
; Описание: Копирует 8 байт из (DE) в (HL) с побитовой маской 80h/08h (плоскость 3).
;           C=08h (счётчик). loc_043B: LDAX D (байт источника), DCX D, C=A;
;           A=(HL), CMA (инверсия приёмника), B=A. Проверка маски 80h: если бит
;           установлен — берёт (HL), иначе 00h; MOV M,A. Проверка маски 08h: если
;           бит установлен — A=B (инверсный), ORA M (наложение); MOV M,A; INX H;
;           DCR C; JNZ loc_043B. Одна из 4 функций побитовой распаковки шрифта.

func_blit_plane_mask80:
    MVI C, 08h                  ; 0x0439
loc_043B:
    PUSH B                      ; 0x043B
    LDAX D                      ; 0x043C
    DCX D                       ; 0x043D
    MOV C, A                    ; 0x043E
    MOV A, M                    ; 0x043F
    CMA                         ; 0x0440
    MOV B, A                    ; 0x0441
    MOV A, C                    ; 0x0442
    ANI 80h                     ; 0x0443
    MVI A, 00h                  ; 0x0445
    JZ loc_044B                 ; 0x0447
    MOV A, M                    ; 0x044A
loc_044B:
    MOV M, A                    ; 0x044B
    MOV A, C                    ; 0x044C
    ANI 08h                     ; 0x044D
    MVI A, 00h                  ; 0x044F
    JZ loc_0455                 ; 0x0451
    MOV A, B                    ; 0x0454
loc_0455:
    ORA M                       ; 0x0455
    MOV M, A                    ; 0x0456
    INX H                       ; 0x0457
    POP B                       ; 0x0458
    DCR C                       ; 0x0459
    JNZ loc_043B                ; 0x045A
    RET                         ; 0x045D
