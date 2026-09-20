; Функция: func_snd_enable_ch012
; Адрес: 0x02CC
; Размер: 6 байт
; Описание: Включить каналы 0, 1 и 2: CALL func_snd_enable_ch0; JMP func_snd_enable_ch12.

func_snd_enable_ch012:
    CALL func_snd_enable_ch0    ; 0x02CC
    JMP func_snd_enable_ch12    ; 0x02CF
