; Данные: data_note_table_ch1
; Адрес: 0x42F9
; Размер: 256 байт (0x42F9..0x43F8; следующий объект data_note_param_table_43F9@0x43F9)
; Назначение: таблица частот/параметров нот для музыкального канала 1, шаг 10 байт
;   на ноту. Индексируется селектором ноты в func_music_play_note_ch1(0x3C7D).
;   Точная раскладка записи (10 байт) не расшифрована -> выгружена сырым блоком.
; ВЫГРУЗКА: бинарный блок — INCBIN из bin/data_note_table_ch1.bin, по-байтовая копия
;   putup.rom (SHA256 = ROM в MCP). Начало сверено с debug_read_memory_range(0x42F9,16).

data_note_table_ch1:
    INCBIN "bin/data_note_table_ch1.bin"
