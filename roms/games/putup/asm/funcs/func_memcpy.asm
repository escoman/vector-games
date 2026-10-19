; Функция: func_memcpy
; Адрес: 0x1BC9
; Размер: 11 байт
; Описание: Копирование блока памяти. Вход: HL = источник, DE = приёмник,
;           BC = количество байт. Копирует по одному байту (MOV A,M / STAX D),
;           инкрементируя HL и DE и декрементируя BC, пока BC != 0.
;           Примечание: в RDB размер указан как 12, фактически функция занимает
;           11 байт (0x1BC9-0x1BD3); следующий объект func_coords_to_textbuf
;           начинается с 0x1BD4.

func_memcpy:
    MOV A, M                    ; 0x1BC9
    STAX D                      ; 0x1BCA
    INX H                       ; 0x1BCB
    INX D                       ; 0x1BCC
    DCX B                       ; 0x1BCD
    MOV A, B                    ; 0x1BCE
    ORA C                       ; 0x1BCF
    JNZ func_memcpy             ; 0x1BD0
    RET                         ; 0x1BD3
