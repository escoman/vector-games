; Функция: func_delay
; Адрес: 0x0EF7
; Размер: 18 байт
; Описание: Программная пауза. Внешний счётчик B; внутренний цикл HL=1000h,
;           DCX H до нуля (loc_0EFC). DCR B; JNZ loc_0EF9 повторяет внешний цикл.
;           Сохраняет H и PSW. Длительность ~ B * 4096 итераций.

func_delay:
    PUSH H                      ; 0x0EF7
    PUSH PSW                    ; 0x0EF8
loc_0EF9:
    LXI H, 1000h                ; 0x0EF9
loc_0EFC:
    DCX H                       ; 0x0EFC
    MOV A, L                    ; 0x0EFD
    ORA H                       ; 0x0EFE
    JNZ loc_0EFC                ; 0x0EFF
    DCR B                       ; 0x0F02
    JNZ loc_0EF9                ; 0x0F03
    POP PSW                     ; 0x0F06
    POP H                       ; 0x0F07
    RET                         ; 0x0F08
