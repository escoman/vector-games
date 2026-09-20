; Функция: func_snd_out_ch1
; Адрес: 0x022D
; Размер: 13 байт
; Описание: Вывод периода канала 1: LXI H, var_snd_period_ch1; CALL
;           func_snd_calc_period; OUT 0Ah (lo), OUT 0Ah (hi). Порт 0Ah = ch1 VI53.

func_snd_out_ch1:
    LXI H, var_snd_period_ch1   ; 0x022D
    CALL func_snd_calc_period   ; 0x0230
    MOV A, L                    ; 0x0233
    OUT 0Ah                     ; 0x0234
    MOV A, H                    ; 0x0236
    OUT 0Ah                     ; 0x0237
    RET                         ; 0x0239
