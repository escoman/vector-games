; Функция: func_snd_out_ch0
; Адрес: 0x0201
; Размер: 13 байт
; Описание: Вывод периода канала 0: LXI H, var_snd_period_ch0; CALL
;           func_snd_calc_period (HL = 12*значение); OUT 0Bh (lo), OUT 0Bh (hi).
;           Порт 0Bh = счётчик ch0 KR580VI53.

func_snd_out_ch0:
    LXI H, var_snd_period_ch0   ; 0x0201
    CALL func_snd_calc_period   ; 0x0204
    MOV A, L                    ; 0x0207
    OUT 0Bh                     ; 0x0208
    MOV A, H                    ; 0x020A
    OUT 0Bh                     ; 0x020B
    RET                         ; 0x020D
