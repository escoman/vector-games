; Данные: data_note_param_table_43F9
; Адрес: 0x43F9
; Размер: 100 байт (до data_note_freq_table_ch0 @0x445D)
; Назначение: таблица 14-байтных блоков параметров нот. func_music_set_note_params
;             (0x3B0F) индексирует её по значению ноты (маска 7Fh, шаг 8 в цикле)
;             и копирует 14 байт выбранного блока в data_voice_param_buf (0x3845).
;             Блоки ниже показаны по 14 байт для читаемости; последний — хвост.

data_note_param_table_43F9:  ; byte-exact image slice 0x43F9..0x445C (99 bytes)
    INCBIN "bin/data_note_param_table_43F9.bin"
