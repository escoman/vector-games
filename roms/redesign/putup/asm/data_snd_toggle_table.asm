; Данные: data_snd_toggle_table
; Адрес: 0x0280
; Размер: 16 байт (8 слов)
; Назначение: 8-словная таблица повторного входа в диспетчер func_sound_op,
;             используемая func_snd_toggle (0x026E). Индекс = (var_snd_state ^ E)&7.
;             Цели [1..7] совпадают с началами функций включения каналов ->
;             символические имена; [0]=0x026D — метка внутри func_snd_toggle (hex).

data_snd_toggle_table:
    DEFW 026Dh                  ; [0]  нет каналов (внутри func_snd_toggle)
    DEFW func_snd_enable_ch0    ; [1]  0x0290 вкл ch0
    DEFW func_snd_enable_ch1    ; [2]  0x029E вкл ch1
    DEFW func_snd_enable_ch01   ; [3]  0x02BA вкл ch0+ch1
    DEFW func_snd_enable_ch2    ; [4]  0x02AC вкл ch2
    DEFW func_snd_enable_ch02   ; [5]  0x02C0 вкл ch0+ch2
    DEFW func_snd_enable_ch12   ; [6]  0x02C6 вкл ch1+ch2
    DEFW func_snd_enable_ch012  ; [7]  0x02CC вкл ch0+ch1+ch2
