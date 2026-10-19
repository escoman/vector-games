; Функция: func_snd_enable_ch01
; Адрес: 0x02BA
; Размер: 6 байт
; Описание: Включить каналы 0 и 1: CALL func_snd_enable_ch0; JMP func_snd_enable_ch1.

func_snd_enable_ch01:
    CALL func_snd_enable_ch0    ; 0x02BA
    JMP func_snd_enable_ch1     ; 0x02BD
