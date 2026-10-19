; Функция: func_delay_long
; Адрес: 0x1477
; Размер: 18 байт
; Описание: Длинная программная пауза (аналог func_delay, но внутренний счётчик
;           HL=0000h -> 65536 итераций). Внешний счётчик B: DCR B; JNZ loc_1479.
;           Внутренний цикл loc_147C: DCX H до нуля. Сохраняет H и PSW.

func_delay_long:
    PUSH H                      ; 0x1477
    PUSH PSW                    ; 0x1478
loc_1479:
    LXI H, 0000h                ; 0x1479
loc_147C:
    DCX H                       ; 0x147C
    MOV A, L                    ; 0x147D
    ORA H                       ; 0x147E
    JNZ loc_147C                ; 0x147F
    DCR B                       ; 0x1482
    JNZ loc_1479                ; 0x1483
    POP PSW                     ; 0x1486
    POP H                       ; 0x1487
    RET                         ; 0x1488
