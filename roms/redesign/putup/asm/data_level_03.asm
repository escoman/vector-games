; Данные: data_level_03
; Адрес: 0xDEE
; Размер: 176 байт (16 колонок x 11 рядов тайл-индексов)
; Назначение: тайл-карта уровня 03. Формат/тайл-индексы/выход: см. data_level_maps
;   (0x1C8E). Это 1-я..15-я карта = data_level_maps + 2*176.
; ВЫГРУЗКА: INCBIN из bin/data_level_03.bin (по-байтовая копия putup.rom, Stage 10 п.7).

data_level_03:
    INCBIN "bin/data_level_03.bin"
