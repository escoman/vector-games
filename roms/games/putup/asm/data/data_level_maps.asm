; Данные: data_level_maps
; Адрес: 0x1C8E
; Размер: 2640 байт (15 карт уровня x 176)
; Назначение: таблица тайл-карт уровней. Карта N лежит по адресу 0x1C8E+(N-1)*176
;   (func_level_loader @0x19AA в цикле прибавляет 0xB0=176).
; ФОРМАТ: 176 байт тайл-индексов, row-major 16 колонок x 11 рядов; каждый байт
;   рисуется как тайл 2x2 через data_tile_graphics(0x2706) + tile*4 (цикл @0x19BE).
;   Тайл-индексы: 1=пол, 2=стена/граница (row0, row10, col0, col15 все =2),
;   3..14=спец-тайлы (предметы/враги/выход). Выход закодирован тайлом (по коллизии).
; РАЗБИВКА: каждая карта — отдельный файл data_level_01.asm..data_level_15.asm;
;   карты включаются сюда последовательно и идут побайтово подряд, как и должен
;   читать их func_level_loader. data_level_01 = база таблицы (объекта level_01
;   в RDB нет); метка-алиас data_level_maps — для LXI H,data_level_maps.

; base alias (func_level_loader LXI H,data_level_maps)
data_level_maps:

; --- Уровень 01 (0x1C8E, объект data_level_maps) ---
    include "data/data_level_01.asm"
; --- Уровень 02 (0x1D3E, объект data_level_02) ---
    include "data/data_level_02.asm"
; --- Уровень 03 (0x1DEE, объект data_level_03) ---
    include "data/data_level_03.asm"
; --- Уровень 04 (0x1E9E, объект data_level_04) ---
    include "data/data_level_04.asm"
; --- Уровень 05 (0x1F4E, объект data_level_05) ---
    include "data/data_level_05.asm"
; --- Уровень 06 (0x1FFE, объект data_level_06) ---
    include "data/data_level_06.asm"
; --- Уровень 07 (0x20AE, объект data_level_07) ---
    include "data/data_level_07.asm"
; --- Уровень 08 (0x215E, объект data_level_08) ---
    include "data/data_level_08.asm"
; --- Уровень 09 (0x220E, объект data_level_09) ---
    include "data/data_level_09.asm"
; --- Уровень 10 (0x22BE, объект data_level_10) ---
    include "data/data_level_10.asm"
; --- Уровень 11 (0x236E, объект data_level_11) ---
    include "data/data_level_11.asm"
; --- Уровень 12 (0x241E, объект data_level_12) ---
    include "data/data_level_12.asm"
; --- Уровень 13 (0x24CE, объект data_level_13) ---
    include "data/data_level_13.asm"
; --- Уровень 14 (0x257E, объект data_level_14) ---
    include "data/data_level_14.asm"
; --- Уровень 15 (0x262E, объект data_level_15) ---
    include "data/data_level_15.asm"
