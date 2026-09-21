; Данные: data_gfx_2761
; Адрес: 0x2761
; Размер: 2048 байт (0x2761..0x2F60; следующий объект data_sprites_2F61@0x2F61)
; Назначение: графические данные ROM, копируемые в back-буфер 0x6000 функцией
;   func_load_gfx_2761 (0x04CD). Инициализирует глиф 0 блока глифов.
; ВЫГРУЗКА: крупный бинарный блок (TZ Stage 10 п.7) — INCBIN из bin/data_gfx_2761.bin,
;   по-байтовая копия putup.rom (SHA256 совпадает с ROM в MCP). Начало сверено с
;   debug_read_memory_range(0x2761,16).

data_gfx_2761:
    INCBIN "bin/data_gfx_2761.bin"
