; Данные: data_level_15
; Адрес: 0x262E
; Размер: 176 байт (16 колонок x 11 рядов тайл-индексов)
; Назначение: тайл-карта уровня 15. Формат/тайл-индексы/выход: см. data_level_maps
;   (0x1C8E). Это 1-я..15-я карта = data_level_maps + 14*176.
; ВЫГРУЗКА: INCBIN из bin/data_level_15.bin (по-байтовая копия putup.rom, Stage 10 п.7).

data_level_15:
    INCBIN "bin/data_level_15.bin"
