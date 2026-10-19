; Функция: func_snd_calc_period
; Адрес: 0x020E
; Размер: 11 байт
; Описание: Вычисляет значение счётчика VI53 из слова ноты по (HL): HL = слово;
;           DAD H; DE = HL; DAD H; DAD D; DAD H -> HL = 12*значение. Возвращает
;           период в HL для OUT в порт счётчика. Портит DE.

func_snd_calc_period:
    MOV A, M                    ; 0x020E
    INX H                       ; 0x020F
    MOV H, M                    ; 0x0210
    MOV L, A                    ; 0x0211
    DAD H                       ; 0x0212
    MOV E, L                    ; 0x0213
    MOV D, H                    ; 0x0214
    DAD H                       ; 0x0215
    DAD D                       ; 0x0216
    DAD H                       ; 0x0217
    RET                         ; 0x0218
