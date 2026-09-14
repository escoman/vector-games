; Функция: func_isr_palette_cycle
; Адрес: 0x0152
; Размер: 32 байта
; Описание: Palette cycling output. POP PSW loads palette color into A.
;           ORA M x3 — timing delay (reads [HL] where HL=0152h, [0152h]=F1h).
;           NOP — additional timing. Then 8x [OUT 0Ch + XOR arithmetic]:
;           outputs A to palette port 0Ch, then modifies A via XOR with
;           registers D(01h), C(03h), B(07h) in alternating pattern.
;           Final XRA A zeros A, last OUT 0Ch outputs 0. RET returns to
;           caller (func_isr_rearm_and_exit or self-loop).

    org 0152h

func_isr_palette_cycle:
    POP PSW                     ; 0x0152
    ORA M                       ; 0x0153
    ORA M                       ; 0x0154
    ORA M                       ; 0x0155
    NOP                         ; 0x0156
    OUT 0Ch                     ; 0x0157
    XRA D                       ; 0x0159
    OUT 0Ch                     ; 0x015A
    XRA C                       ; 0x015C
    OUT 0Ch                     ; 0x015D
    XRA D                       ; 0x015F
    OUT 0Ch                     ; 0x0160
    XRA B                       ; 0x0162
    OUT 0Ch                     ; 0x0163
    XRA D                       ; 0x0165
    OUT 0Ch                     ; 0x0166
    XRA C                       ; 0x0168
    OUT 0Ch                     ; 0x0169
    XRA D                       ; 0x016B
    OUT 0Ch                     ; 0x016C
    XRA A                       ; 0x016E
    OUT 0Ch                     ; 0x016F
    RET                         ; 0x0171
