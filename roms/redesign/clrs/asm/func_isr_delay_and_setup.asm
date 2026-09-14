; Функция: func_isr_delay_and_setup
; Адрес: 0x013F
; Размер: 19 байт
; Описание: VBlank ISR entry (RST 7 vector target). (1) Delay loop:
;           LXI B,00ECh / DCX B / MOV A,B / ORA C / JNZ — counts down BC.
;           (2) NOP NOP — timing padding (8 T-states).
;           (3) LXI B,0703h / MVI D,01h — set up registers for palette cycling.
;           (4) LXI SP,0177h — reposition SP for palette stack consumption.
;           Falls through to func_isr_palette_cycle at 0x0152.

    org 013Fh

func_isr_delay_and_setup:
    LXI B, 00ECh                ; 0x013F
.loc_0142:
    DCX B                       ; 0x0142
    MOV A, B                    ; 0x0143
    ORA C                       ; 0x0144
    JNZ .loc_0142               ; 0x0145
    NOP                         ; 0x0148
    NOP                         ; 0x0149
    LXI B, 0703h                ; 0x014A
    MVI D, 01h                  ; 0x014D
    LXI SP, 0177h               ; 0x014F
