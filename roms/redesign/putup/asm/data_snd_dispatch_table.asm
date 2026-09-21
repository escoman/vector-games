; Данные: data_snd_dispatch_table
; Адрес: 0x01CD
; Размер: 32 байта (16 слов)
; Назначение: 16-позиционная таблица переходов PCHL для func_sound_op (0x01BC).
;             Индекс = A&0Fh, слово = адрес обработчика операции VI53.
;             Цели [0..5],[7],[11..15] — точки входа обработчиков ВНУТРИ крупных
;             функций (не начало RDB-объекта), оставлены как hex (Stage 10 п.5).
;             Цели [6],[8],[9],[10] совпадают с началами объектов -> символические.

data_snd_dispatch_table:
    DEFW 01EDh                  ; [0]  ch0 период lo        (внутри func_snd_out_ch0)
    DEFW 01F7h                  ; [1]  ch0 период hi + play (внутри func_snd_out_ch0)
    DEFW 0219h                  ; [2]  ch1 период lo        (внутри func_snd_out_ch1)
    DEFW 0223h                  ; [3]  ch1 период hi + play (внутри func_snd_out_ch1)
    DEFW 023Ah                  ; [4]  ch2 период lo        (внутри func_snd_out_ch2)
    DEFW 0244h                  ; [5]  ch2 период hi + play (внутри func_snd_out_ch2)
    DEFW func_snd_out_ch2       ; [6]  0x025B nop / общий эпилог (начало func_snd_out_ch2)
    DEFW 0267h                  ; [7]  переключение состояния (внутри func_snd_toggle)
    DEFW func_snd_gate_ch0      ; [8]  0x02D2 gate ch0
    DEFW func_snd_gate_ch1      ; [9]  0x02EA gate ch1
    DEFW func_snd_gate_ch2      ; [10] 0x0302 gate ch2
    DEFW 025Eh                  ; [11] nop
    DEFW 0261h                  ; [12] nop
    DEFW 0264h                  ; [13] nop
    DEFW 026Ah                  ; [14] nop
    DEFW 026Ah                  ; [15] nop
