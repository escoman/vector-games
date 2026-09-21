; Данные: data_level_05
; Адрес: 0xF4E
; Размер: 176 байт (16 колонок x 11 рядов тайл-индексов)
; Назначение: тайл-карта уровня 05. Формат/тайл-индексы/выход: см. data_level_maps
;   (0x1C8E). Это 1-я..15-я карта = data_level_maps + 4*176.
; ВЫГРУЗКА: INCBIN из bin/data_level_05.bin (по-байтовая копия putup.rom, Stage 10 п.7).

data_level_05:
    INCBIN "bin/data_level_05.bin"
