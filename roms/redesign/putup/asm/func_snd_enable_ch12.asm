; Функция: func_snd_enable_ch12
; Адрес: 0x02C6
; Размер: 6 байт
; Описание: Включить каналы 1 и 2: CALL func_snd_enable_ch1; JMP func_snd_enable_ch2.

func_snd_enable_ch12:
    CALL func_snd_enable_ch1    ; 0x02C6
    JMP func_snd_enable_ch2     ; 0x02C9
