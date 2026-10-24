; Функция: func_prng
; Адрес: 0x1123
; Размер: 50 байт
; Описание: 16-битный ГПСЧ — мультипликативный конгруентный (Лемер):
;           state = (state × PRNG_MULTIPLIER) mod 2^15. Реализован побитовым
;           умножением «русского крестьянина». Состояние в var_prng_state.
;           HL=state; BC=PRNG_MULTIPLIER(0383h); DE=0; PRNG_ITERATIONS(16)
;           итераций (loc_1132): сдвиг BC вправо через RAR, если перенос (JC пропущен) ->
;           DE+=HL (XCHG; DAD D; XCHG); HL<<=1 (DAD H). Результат: HL&=PRNG_MODULUS_MASK,
;           state=HL, A=hi+lo. Возвращает A=псевдослучайный байт. Сохраняет H,D,B,PSW.
;           ЭНТРОПИЯ: сид НЕ сбрасывается; разнообразие даёт число вызовов —
;           func_prng дёргается в цикле опроса заставки и каждый кадр игры,
;           так что состояние уже прокручивается, пока игрок жмёт старт/играет.

func_prng:
    PUSH H                      ; 0x1123
    PUSH D                      ; 0x1124
    PUSH B                      ; 0x1125
    PUSH PSW                    ; 0x1126
    LHLD var_prng_state         ; 0x1127
    LXI B, PRNG_MULTIPLIER      ; 0x112A
    LXI D, 0000h                ; 0x112D
    MVI A, PRNG_ITERATIONS      ; 0x1130
loc_1132:
    PUSH PSW                    ; 0x1132
    MOV A, B                    ; 0x1133
    RAR                         ; 0x1134
    MOV B, A                    ; 0x1135
    MOV A, C                    ; 0x1136
    RAR                         ; 0x1137
    MOV C, A                    ; 0x1138
    JNC loc_113F                ; 0x1139
    XCHG                        ; 0x113C
    DAD D                       ; 0x113D
    XCHG                        ; 0x113E
loc_113F:
    DAD H                       ; 0x113F
    POP PSW                     ; 0x1140
    DCR A                       ; 0x1141
    JNZ loc_1132                ; 0x1142
    XCHG                        ; 0x1145
    MOV A, H                    ; 0x1146
    ANI PRNG_MODULUS_MASK       ; 0x1147
    MOV H, A                    ; 0x1149
    SHLD var_prng_state         ; 0x114A
    ADD L                       ; 0x114D
    MOV L, A                    ; 0x114E
    POP PSW                     ; 0x114F
    MOV A, L                    ; 0x1150
    POP B                       ; 0x1151
    POP D                       ; 0x1152
    POP H                       ; 0x1153
    RET                         ; 0x1154
