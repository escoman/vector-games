; Данные: data_level_maps
; Адрес: 0x1C8E
; Размер: 2640 байт (15 карт уровня x 176)
; Назначение: таблица тайл-карт уровней. Карта N лежит по адресу 0x1C8E+(N-1)*176
;   (func_level_loader @0x19AA в цикле прибавляет 0xB0=176).
; ФОРМАТ: 176 байт тайл-индексов, row-major 16 колонок x 11 рядов; каждый байт
;   рисуется как тайл 2x2 через data_tile_graphics(0x2706) + tile*4 (цикл @0x19BE).
;   Тайл-индексы: 1=пол, 2=стена/граница (row0, row10, col0, col15 все =2),
;   3..14=спец-тайлы (предметы/враги/выход). Выход закодирован тайлом (по коллизии).
; ВЫГРУЗКА: крупные бинарные блоки (TZ Stage 10 п.7) выгружены директивой INCBIN
;   из bin/*.bin. Бинарники — прямая по-байтовая копия образа putup.rom (SHA256
;   совпадает с ROM в MCP), см. отчёт Stage10.md. Каждая карта помечена глобальной
;   меткой data_level_NN для Stage 11 (data_level_01 = база таблицы, объекта в RDB нет).

; --- Уровень 01 (0x1C8E, объект data_level_maps) ---
data_level_maps:          ; base alias (func_level_loader LXI H,data_level_maps)
data_level_01:
    INCBIN "bin/data_level_01.bin"
; --- Уровень 02 (0x1D3E, объект data_level_02) ---
data_level_02:
    INCBIN "bin/data_level_02.bin"
; --- Уровень 03 (0x1DEE, объект data_level_03) ---
data_level_03:
    INCBIN "bin/data_level_03.bin"
; --- Уровень 04 (0x1E9E, объект data_level_04) ---
data_level_04:
    INCBIN "bin/data_level_04.bin"
; --- Уровень 05 (0x1F4E, объект data_level_05) ---
data_level_05:
    INCBIN "bin/data_level_05.bin"
; --- Уровень 06 (0x1FFE, объект data_level_06) ---
data_level_06:
    INCBIN "bin/data_level_06.bin"
; --- Уровень 07 (0x20AE, объект data_level_07) ---
data_level_07:
    INCBIN "bin/data_level_07.bin"
; --- Уровень 08 (0x215E, объект data_level_08) ---
data_level_08:
    INCBIN "bin/data_level_08.bin"
; --- Уровень 09 (0x220E, объект data_level_09) ---
data_level_09:
    INCBIN "bin/data_level_09.bin"
; --- Уровень 10 (0x22BE, объект data_level_10) ---
data_level_10:
    INCBIN "bin/data_level_10.bin"
; --- Уровень 11 (0x236E, объект data_level_11) ---
data_level_11:
    INCBIN "bin/data_level_11.bin"
; --- Уровень 12 (0x241E, объект data_level_12) ---
data_level_12:
    INCBIN "bin/data_level_12.bin"
; --- Уровень 13 (0x24CE, объект data_level_13) ---
data_level_13:
    INCBIN "bin/data_level_13.bin"
; --- Уровень 14 (0x257E, объект data_level_14) ---
data_level_14:
    INCBIN "bin/data_level_14.bin"
; --- Уровень 15 (0x262E, объект data_level_15) ---
data_level_15:
    INCBIN "bin/data_level_15.bin"
