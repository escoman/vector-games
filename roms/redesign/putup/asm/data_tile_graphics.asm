; Данные: data_tile_graphics
; Адрес: 0x2706
; Размер: 91 байт (22 записи x 4 + 3)
; Назначение: таблица графики тайлов карты. func_level_loader (0x197C) вычисляет
;             A = tile*4, HL = 0x2706 + A -> 4 символа тайла 2x2, рисует через
;             func_draw_tile_to_buf (0x1B87). Индексируется байтами из
;             data_level_maps. Внутрь таблицы также залезают спрайт-тайлы
;             (0x270A, 0x2756), используемые func_entity_state1.

data_tile_graphics:
    DEFB 00h, 00h, 00h, 00h   ; [+0x00] tile 0
    DEFB 20h, 20h, 20h, 20h   ; [+0x04] tile 1 (пол: пробелы)
    DEFB 77h, 78h, 78h, 77h   ; [+0x08] tile 2 (стена)
    DEFB 60h, 60h, 60h, 60h   ; [+0x0C] tile 3
    DEFB 7Eh, 80h, 81h, 82h   ; [+0x10] tile 4
    DEFB 7Dh, 78h, 78h, 77h   ; [+0x14] tile 5
    DEFB 75h, 75h, 76h, 76h   ; [+0x18] tile 6
    DEFB 20h, 20h, 72h, 6Dh   ; [+0x1C] tile 7
    DEFB 79h, 7Ah, 78h, 77h   ; [+0x20] tile 8
    DEFB 60h, 60h, 74h, 60h   ; [+0x24] tile 9
    DEFB 20h, 6Bh, 6Eh, 6Ch   ; [+0x28] tile 10
    DEFB 63h, 64h, 6Fh, 65h   ; [+0x2C] tile 11
    DEFB 66h, 70h, 68h, 20h   ; [+0x30] tile 12
    DEFB 69h, 71h, 6Ah, 61h   ; [+0x34] tile 13
    DEFB 20h, 73h, 62h, 84h   ; [+0x38] tile 14
    DEFB 85h, 86h, 87h, 88h   ; [+0x3C] tile 15
    DEFB 89h, 86h, 87h, 8Bh   ; [+0x40] tile 16
    DEFB 8Ch, 8Dh, 8Eh, 8Fh   ; [+0x44] tile 17
    DEFB 90h, 91h, 92h, 93h   ; [+0x48] tile 18
    DEFB 94h, 95h, 96h, 97h   ; [+0x4C] tile 19
    DEFB 98h, 99h, 9Ah, 00h   ; [+0x50] tile 20
    DEFB 00h, 00h, 00h, 00h   ; [+0x54] tile 21
    DEFB 00h, 00h, 00h        ; [+0x58] хвост (до 0x2761)
