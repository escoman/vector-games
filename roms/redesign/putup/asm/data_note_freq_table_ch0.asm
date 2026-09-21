; Данные: data_note_freq_table_ch0
; Адрес: 0x445D
; Размер: 419 байт (0x445D..0x45FE; это последний блок данных ROM, образ заканчивается 0x45FF)
; Назначение: таблица частот/параметров нот для музыкального канала 0, шаг 20 байт
;   на ноту. Индексируется селектором ноты в func_music_play_note_ch0(0x3BCA).
;   Начинается с слов 0x0001 (LE 01 00). Точная раскладка записи (20 байт) не
;   расшифрована -> выгружена сырым блоком.
; ВЫГРУЗКА: бинарный блок — INCBIN из bin/data_note_freq_table_ch0.bin, по-байтовая
;   копия putup.rom (SHA256 = ROM в MCP). Начало сверено с debug_read_memory_range(0x445D,16).

data_note_freq_table_ch0:
    INCBIN "bin/data_note_freq_table_ch0.bin"
