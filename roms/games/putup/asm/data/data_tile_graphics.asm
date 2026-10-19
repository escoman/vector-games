; Данные: data_tile_graphics
; Адрес: 0x2706
; Размер: 91 байт (22 записи x 4 + 3)
; Назначение: таблица графики тайлов карты. func_level_loader (0x197C) вычисляет
;             A = tile*4, HL = 0x2706 + A -> 4 символа тайла 2x2, рисует через
;             func_draw_tile_to_buf (0x1B87). Индексируется байтами из
;             data_level_maps. Внутрь таблицы также залезают спрайт-тайлы
;             (0x270A, 0x2756), используемые func_entity_state1.

data_tile_graphics:  ; byte-exact image slice 0x2706..0x2761 (91 bytes)
    DEFB 000h, 000h, 000h, 000h, 020h, 020h, 020h, 020h, 077h, 078h, 078h, 077h, 060h, 060h, 060h, 060h
    DEFB 07Eh, 080h, 081h, 082h, 07Dh, 078h, 078h, 077h, 075h, 075h, 076h, 076h, 020h, 020h, 072h, 06Dh
    DEFB 079h, 07Ah, 078h, 077h, 060h, 060h, 074h, 060h, 020h, 06Bh, 06Eh, 06Ch, 063h, 064h, 06Fh, 065h
    DEFB 066h, 067h, 070h, 068h, 020h, 069h, 071h, 06Ah, 061h, 020h, 073h, 062h, 084h, 085h, 086h, 087h
    DEFB 088h, 089h, 086h, 087h, 08Bh, 08Ch, 08Dh, 08Eh, 08Fh, 090h, 091h, 092h, 093h, 094h, 095h, 096h
    DEFB 097h, 098h, 099h, 09Ah, 000h, 000h, 000h, 000h, 000h, 000h, 000h
