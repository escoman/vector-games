; Функция: func_draw_tile_at_ptr
; Адрес: 0x0104
; Размер: 29 байт
; Описание: Рисует тайл 2x2 символа по координатам из памяти: DE = слово по (HL)
;           (координаты x/y); CALL func_coords_to_textbuf для адреса буфера;
;           рисует (HL),(HL+1) через func_render_glyph; HL += 001Fh (следующая
;           строка буфера); рисует ещё 2 символа. Используется
;           func_draw_game_objects для вывода тайлов объектов.

func_draw_tile_at_ptr:
    MOV E, M                    ; 0x0104
    INX H                       ; 0x0105
    MOV D, M                    ; 0x0106
    CALL func_coords_to_textbuf ; 0x0107
    MOV A, M                    ; 0x010A
    CALL func_render_glyph      ; 0x010B
    INX H                       ; 0x010E
    MOV A, M                    ; 0x010F
    CALL func_render_glyph      ; 0x0110
    LXI B, 001Fh                ; 0x0113
    DAD B                       ; 0x0116
    MOV A, M                    ; 0x0117
    CALL func_render_glyph      ; 0x0118
    INX H                       ; 0x011B
    MOV A, M                    ; 0x011C
    CALL func_render_glyph      ; 0x011D
    RET                         ; 0x0120
