; Функция: func_snd_enable_ch02
; Адрес: 0x02C0
; Размер: 6 байт
; Описание: Включить каналы 0 и 2: CALL func_snd_enable_ch0; JMP func_snd_enable_ch2.

func_snd_enable_ch02:
    CALL func_snd_enable_ch0    ; 0x02C0
    JMP func_snd_enable_ch2     ; 0x02C3
