; Данные: data_note_param_table_43F9
; Адрес: 0x43F9
; Размер: 100 байт (до data_note_freq_table_ch0 @0x445D)
; Назначение: таблица 14-байтных блоков параметров нот. func_music_set_note_params
;             (0x3B0F) индексирует её по значению ноты (маска 7Fh, шаг 8 в цикле)
;             и копирует 14 байт выбранного блока в data_voice_param_buf (0x3845).
;             Блоки ниже показаны по 14 байт для читаемости; последний — хвост.

data_note_param_table_43F9:
    DEFB 0EEh, 0Eh, 15h, 10h, 00h, 0Ah, 01h, 00h, 0F6h, 9h, 0Ah, 10h, 00h, 0Ah   ; блок 0
    DEFB 01h, 00h, 64h, 00h, 00h, 10h, 00h, 0Ch, 01h, 00h, 00h, 2h, 00h, 10h      ; блок 1
    DEFB 00h, 9h, 01h, 00h, 00h, 3h, 00h, 10h, 00h, 9h, 01h, 00h, 00h, 0Ah        ; блок 2
    DEFB 11h, 00h, 0Ah, 00h, 00h, 0Ah, 00h, 00h, 10h, 00h, 19h, 01h, 00h, 80h     ; блок 3
    DEFB 00h, 5h, 10h, 00h, 3h, 01h, 00h, 40h, 00h, 2h, 10h, 00h, 3h, 01h         ; блок 4
    DEFB 00h, 80h, 00h, 5h, 10h, 00h, 3h, 01h, 00h, 40h, 00h, 2h, 10h, 00h        ; блок 5
    DEFB 3h, 01h, 00h, 40h, 00h, 00h, 10h, 00h, 3h, 4h, 00h, 7Bh, 0D0h, 3Eh       ; блок 6
    DEFB 0Ah                                                                       ; хвост (до 0x445D)
