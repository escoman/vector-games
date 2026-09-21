; Данные: data_tile_graphics
; Адрес: 0x2706
; Размер: 91 байт (22 записи x 4 + 3)
; Назначение: таблица графики тайлов карты. func_level_loader (0x197C) вычисляет
;             A = tile*4, HL = 0x2706 + A -> 4 символа тайла 2x2, рисует через
;             func_draw_tile_to_buf (0x1B87). Индексируется байтами из
;             data_level_maps. Внутрь таблицы также залезают спрайт-тайлы
;             (0x270A, 0x2756), используемые func_entity_state1.

data_tile_graphics:  ; byte-exact image slice 0x2706..0x2761 (91 bytes)
    INCBIN "bin/data_tile_graphics.bin"
