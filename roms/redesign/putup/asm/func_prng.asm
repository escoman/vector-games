; Функция: func_prng
; Адрес: 0x1123
; Размер: 50 байт
; Описание: 16-битный ГПСЧ (LFSR/сдвиг с умножением). Состояние хранится в слове
;           1155h. HL=seed; BC=0383h (константа-множитель); DE=0; 16 итераций
;           (loc_1132): сдвиг BC вправо через RAR, если перенос (JC пропущен) ->
;           DE+=HL (XCHG; DAD D; XCHG); HL<<=1 (DAD H). Результат: HL&=7Fh,
;           seed=HL, A=L+L. Возвращает A=псевдослучайный байт. Сохраняет H,D,B,PSW.
;           Примечание: 1155h — переменная состояния ГПСЧ (не объект RDB), hex.
;           0383h — числовая константа, не ссылка на func_hw_init.

func_prng:
    PUSH H                      ; 0x1123
    PUSH D                      ; 0x1124
    PUSH B                      ; 0x1125
    PUSH PSW                    ; 0x1126
    LHLD 1155h                  ; 0x1127
    LXI B, 0383h                ; 0x112A
    LXI D, 0000h                ; 0x112D
    MVI A, 10h                  ; 0x1130
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
    ANI 7Fh                     ; 0x1147
    MOV H, A                    ; 0x1149
    SHLD 1155h                  ; 0x114A
    ADD L                       ; 0x114D
    MOV L, A                    ; 0x114E
    POP PSW                     ; 0x114F
    MOV A, L                    ; 0x1150
    POP B                       ; 0x1151
    POP D                       ; 0x1152
    POP H                       ; 0x1153
    RET                         ; 0x1154
