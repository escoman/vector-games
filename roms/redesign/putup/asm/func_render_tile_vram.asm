; Функция: func_render_tile_vram
; Адрес: 0x1BA8
; Размер: 33 байта
; Описание: Рисует тайл 2x2 непосредственно в VRAM (в обход текстового буфера).
;           Вход: HL = указатель графики тайла (4 байта-глифа), D = колонка,
;           E = строка. Аналогична func_draw_tile_to_buf, но вместо
;           func_draw_char_at_hl вызывает func_render_glyph для каждого из 4
;           глифов.

func_render_tile_vram:
    PUSH B                      ; 0x1BA8
    PUSH H                      ; 0x1BA9
    CALL func_coords_to_textbuf ; 0x1BAA
    POP D                       ; 0x1BAD
    LDAX D                      ; 0x1BAE
    CALL func_render_glyph      ; 0x1BAF
    INX D                       ; 0x1BB2
    INX H                       ; 0x1BB3
    LDAX D                      ; 0x1BB4
    CALL func_render_glyph      ; 0x1BB5
    INX D                       ; 0x1BB8
    LXI B, 001Fh                ; 0x1BB9
    DAD B                       ; 0x1BBC
    LDAX D                      ; 0x1BBD
    CALL func_render_glyph      ; 0x1BBE
    INX D                       ; 0x1BC1
    INX H                       ; 0x1BC2
    LDAX D                      ; 0x1BC3
    CALL func_render_glyph      ; 0x1BC4
    POP B                       ; 0x1BC7
    RET                         ; 0x1BC8
