; Функция: func_snd_set_period_ch0
; Адрес: 0x01ED
; Размер: 20 байт
; Описание: Обработчики диспетчера VI53 [0]/[1] — установка периода канала 0.
;           [0]@0x01ED: A=E; STA var_snd_period_ch0 (lo); CALL func_snd_out_ch0;
;           JMP func_snd_op_epilogue. [1]@0x01F7: то же для старшего байта
;           (STA var_snd_period_ch0+1). Вход: E = значение периода.

func_snd_set_period_ch0:        ; dispatch [0] @0x01ED — период ch0 (lo)
    MOV A, E                    ; 0x01ED
    STA var_snd_period_ch0      ; 0x01EE
    CALL func_snd_out_ch0       ; 0x01F1
    JMP func_snd_op_epilogue    ; 0x01F4
snd_set_ch0_hi:                 ; dispatch [1] @0x01F7 — период ch0 (hi)
    MOV A, E                    ; 0x01F7
    STA var_snd_period_ch0+1    ; 0x01F8
    CALL func_snd_out_ch0       ; 0x01FB
    JMP func_snd_op_epilogue    ; 0x01FE
