; Функция: func_snd_set_period_ch2
; Адрес: 0x023A
; Размер: 20 байт
; Описание: Обработчики диспетчера VI53 [4]/[5] — установка периода канала 2.
;           [4]@0x023A (lo), [5]@0x0244 (hi): A=E; STA var_snd_period_ch2(+1);
;           CALL func_snd_out_ch2; JMP func_snd_op_epilogue.

func_snd_set_period_ch2:        ; dispatch [4] @0x023A — период ch2 (lo)
    MOV A, E                    ; 0x023A
    STA var_snd_period_ch2      ; 0x023B
    CALL func_snd_out_ch2       ; 0x023E
    JMP func_snd_op_epilogue    ; 0x0241
snd_set_ch2_hi:                 ; dispatch [5] @0x0244 — период ch2 (hi)
    MOV A, E                    ; 0x0244
    STA var_snd_period_ch2+1    ; 0x0245
    CALL func_snd_out_ch2       ; 0x0248
    JMP func_snd_op_epilogue    ; 0x024B
