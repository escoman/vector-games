; Данные: data_level_04
; Адрес: 0xE9E
; Размер: 176 байт (16 колонок x 11 рядов тайл-индексов)
; Назначение: тайл-карта уровня 04. Формат/тайл-индексы/выход: см. data_level_maps
;   (0x1C8E). Это 1-я..15-я карта = data_level_maps + 3*176.
; ВЫГРУЗКА: INCBIN из bin/data_level_04.bin (по-байтовая копия putup.rom, Stage 10 п.7).

data_level_04:
    INCBIN "bin/data_level_04.bin"
