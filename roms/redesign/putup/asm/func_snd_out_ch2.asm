; Функция: func_snd_out_ch2
; Адрес: 0x024E
; Размер: 13 байт
; Описание: Вывод периода канала 2: LXI H, var_snd_period_ch2; CALL
;           func_snd_calc_period; OUT 09h (lo), OUT 09h (hi). Порт 09h = ch2 VI53.

func_snd_out_ch2:
    LXI H, var_snd_period_ch2   ; 0x024E
    CALL func_snd_calc_period   ; 0x0251
    MOV A, L                    ; 0x0254
    OUT 09h                     ; 0x0255
    MOV A, H                    ; 0x0257
    OUT 09h                     ; 0x0258
    RET                         ; 0x025A
