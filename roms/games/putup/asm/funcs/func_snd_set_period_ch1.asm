; Функция: func_snd_set_period_ch1
; Адрес: 0x0219
; Размер: 20 байт
; Описание: Обработчики диспетчера VI53 [2]/[3] — установка периода канала 1.
;           [2]@0x0219 (lo), [3]@0x0223 (hi): A=E; STA var_snd_period_ch1(+1);
;           CALL func_snd_out_ch1; JMP func_snd_op_epilogue.

func_snd_set_period_ch1:        ; dispatch [2] @0x0219 — период ch1 (lo)
    MOV A, E                    ; 0x0219
    STA var_snd_period_ch1      ; 0x021A
    CALL func_snd_out_ch1       ; 0x021D
    JMP func_snd_op_epilogue    ; 0x0220
snd_set_ch1_hi:                 ; dispatch [3] @0x0223 — период ch1 (hi)
    MOV A, E                    ; 0x0223
    STA var_snd_period_ch1+1    ; 0x0224
    CALL func_snd_out_ch1       ; 0x0227
    JMP func_snd_op_epilogue    ; 0x022A
