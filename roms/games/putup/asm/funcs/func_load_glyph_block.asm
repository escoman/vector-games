; Функция: func_load_glyph_block
; Адрес: 0x0401
; Размер: 56 байт
; Описание: Распаковка блока глифов. Сохраняет H/D/B/PSW; CALL func_load_gfx_2761
;           (копирует графику в data_glyph_block@0x6000). HL=data_glyph_block,
;           DE=data_packed_font_3041, B=00h (256 итераций). Цикл loc_0410: для
;           каждого байта шрифта вызывает 4 blit-функции по битовым плоскостям
;           (mask80/40/20/10), сохраняя DE. DCR B; JNZ loc_042F (переход к
;           следующему байту: DE += 0008h); иначе выход и восстановление регистров.

func_load_glyph_block:
    PUSH H                      ; 0x0401
    PUSH D                      ; 0x0402
    PUSH B                      ; 0x0403
    PUSH PSW                    ; 0x0404
    CALL func_load_gfx_2761     ; 0x0405
    LXI H, data_glyph_block     ; 0x0408
    LXI D, data_packed_font_3041 ; 0x040B
    MVI B, 00h                  ; 0x040E
loc_0410:
    PUSH B                      ; 0x0410
    PUSH D                      ; 0x0411
    CALL func_blit_plane_mask80 ; 0x0412
    POP D                       ; 0x0415
    PUSH D                      ; 0x0416
    CALL func_blit_plane_mask40 ; 0x0417
    POP D                       ; 0x041A
    PUSH D                      ; 0x041B
    CALL func_blit_plane_mask20 ; 0x041C
    POP D                       ; 0x041F
    PUSH D                      ; 0x0420
    CALL func_blit_plane_mask10 ; 0x0421
    POP D                       ; 0x0424
    POP B                       ; 0x0425
    DCR B                       ; 0x0426
    JNZ loc_042F                ; 0x0427
    POP PSW                     ; 0x042A
    POP B                       ; 0x042B
    POP D                       ; 0x042C
    POP H                       ; 0x042D
    RET                         ; 0x042E
loc_042F:
    PUSH H                      ; 0x042F
    LXI H, 0008h                ; 0x0430
    DAD D                       ; 0x0433
    XCHG                        ; 0x0434
    POP H                       ; 0x0435
    JMP loc_0410                ; 0x0436
