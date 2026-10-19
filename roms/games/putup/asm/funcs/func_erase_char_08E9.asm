; Функция: func_erase_char_08E9
; Адрес: 0x0CA3
; Размер: 61 байт
; Описание: Стирание ячейки символа: HL = слово по 08E9h; 5 поворотов 16-бит
;           вправо (HL>>=5) через RAR H/L; A = L AND 1Fh; 08FEh = 17h - A;
;           08FFh = 18h; CALL func_restore_cursor; печать пробела (20h) через
;           func_print_char_at_ptr. Стирает объект в предыдущей позиции
;           (колонка выводится из var_08E9).

func_erase_char_08E9:
    LHLD 08E9h                  ; 0x0CA3
    ORA A                       ; 0x0CA6
    MOV A, H                    ; 0x0CA7
    RAR                         ; 0x0CA8
    MOV H, A                    ; 0x0CA9
    MOV A, L                    ; 0x0CAA
    RAR                         ; 0x0CAB
    MOV L, A                    ; 0x0CAC
    ORA A                       ; 0x0CAD
    MOV A, H                    ; 0x0CAE
    RAR                         ; 0x0CAF
    MOV H, A                    ; 0x0CB0
    MOV A, L                    ; 0x0CB1
    RAR                         ; 0x0CB2
    MOV L, A                    ; 0x0CB3
    ORA A                       ; 0x0CB4
    MOV A, H                    ; 0x0CB5
    RAR                         ; 0x0CB6
    MOV H, A                    ; 0x0CB7
    MOV A, L                    ; 0x0CB8
    RAR                         ; 0x0CB9
    MOV L, A                    ; 0x0CBA
    ORA A                       ; 0x0CBB
    MOV A, H                    ; 0x0CBC
    RAR                         ; 0x0CBD
    MOV H, A                    ; 0x0CBE
    MOV A, L                    ; 0x0CBF
    RAR                         ; 0x0CC0
    MOV L, A                    ; 0x0CC1
    ORA A                       ; 0x0CC2
    MOV A, H                    ; 0x0CC3
    RAR                         ; 0x0CC4
    MOV H, A                    ; 0x0CC5
    MOV A, L                    ; 0x0CC6
    RAR                         ; 0x0CC7
    MOV L, A                    ; 0x0CC8
    ANI 1Fh                     ; 0x0CC9
    MOV B, A                    ; 0x0CCB
    MVI A, 17h                  ; 0x0CCC
    SUB B                       ; 0x0CCE
    STA 08FEh                   ; 0x0CCF
    MVI A, 18h                  ; 0x0CD2
    STA 08FFh                   ; 0x0CD4
    CALL func_restore_cursor    ; 0x0CD7
    MVI A, 20h                  ; 0x0CDA
    CALL func_print_char_at_ptr ; 0x0CDC
    RET                         ; 0x0CDF
