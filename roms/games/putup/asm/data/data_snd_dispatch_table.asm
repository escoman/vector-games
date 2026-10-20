; Данные: data_snd_dispatch_table
; Адрес: 0x01CD
; Размер: 32 байта (16 слов)
; Назначение: 16-позиционная таблица переходов PCHL для func_sound_op (0x01BC).
;             Индекс = A&00Fh, слово = адрес обработчика операции VI53.
;             Все 16 целей — symbolic (DEFW на метки обработчиков/эпилога).
;             Обработчики [0..5] влились из гэпов (func_snd_set_period_chN),
;             холостые [6],[11..15] и [7] — func_snd_dispatch_nops / эпилог.

data_snd_dispatch_table:  ; byte-exact image slice 0x01CD..0x01ED (32 bytes)
    DEFW func_snd_set_period_ch0    ; [0]  0x01ED период ch0 lo
    DEFW snd_set_ch0_hi             ; [1]  0x01F7 период ch0 hi
    DEFW func_snd_set_period_ch1    ; [2]  0x0219 период ch1 lo
    DEFW snd_set_ch1_hi             ; [3]  0x0223 период ch1 hi
    DEFW func_snd_set_period_ch2    ; [4]  0x023A период ch2 lo
    DEFW snd_set_ch2_hi             ; [5]  0x0244 период ch2 hi
    DEFW snd_dispatch_nop           ; [6]  0x025B nop
    DEFW snd_dispatch_toggle        ; [7]  0x0267 CALL toggle
    DEFW func_snd_gate_ch0          ; [8]  0x02D2 гейт ch0
    DEFW func_snd_gate_ch1          ; [9]  0x02EA гейт ch1
    DEFW func_snd_gate_ch2          ; [10] 0x0302 гейт ch2
    DEFW snd_dispatch_nop11         ; [11] 0x025E nop
    DEFW snd_dispatch_nop12         ; [12] 0x0261 nop
    DEFW snd_dispatch_nop13         ; [13] 0x0264 nop
    DEFW func_snd_op_epilogue       ; [14] 0x026A nop→возврат
    DEFW func_snd_op_epilogue       ; [15] 0x026A nop→возврат
