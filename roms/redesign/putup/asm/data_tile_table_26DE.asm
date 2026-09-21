; Данные: data_tile_table_26DE
; Адрес: 0x26DE
; Размер: 40 байт (10 записей x 4)
; Назначение: таблица 2x2-символьных тайлов объектов/игрока. func_draw_game_objects
;             (0x130A) индексирует запись = var_090C*4 -> 4 символа, func_render_tile_vram
;             (0x1BA8) рисует их в VRAM. Записи 0..7 — глифы 0xA0..0xBF;
;             записи 8,9 (02 04 03 05 / 20 20 20 20) — спец-тайлы (выход/пусто).

data_tile_table_26DE:
    DEFB 0A0h, 0A2h, 0A1h, 0A3h   ; [0] запись 0x26DE
    DEFB 0A4h, 0A6h, 0A5h, 0A7h   ; [1] запись 0x26E2
    DEFB 0A8h, 0AAh, 0A9h, 0ABh   ; [2] запись 0x26E6
    DEFB 0ACh, 0AEh, 0ADh, 0AFh   ; [3] запись 0x26EA
    DEFB 0B0h, 0B2h, 0B1h, 0B3h   ; [4] запись 0x26EE
    DEFB 0B4h, 0B6h, 0B5h, 0B7h   ; [5] запись 0x26F2
    DEFB 0B8h, 0BAh, 0B9h, 0BBh   ; [6] запись 0x26F6
    DEFB 0BCh, 0BEh, 0BDh, 0BFh   ; [7] запись 0x26FA
    DEFB 02h, 04h, 03h, 05h       ; [8] запись 0x26FE (спец)
    DEFB 20h, 20h, 20h, 20h       ; [9] запись 0x2702 (пробелы)
