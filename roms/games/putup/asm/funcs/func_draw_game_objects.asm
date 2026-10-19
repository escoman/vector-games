; Функция: func_draw_game_objects
; Адрес: 0x130A
; Размер: 160 байт (0x130A-0x13A9)
; Описание: Отрисовка игровых объектов (мяч/платформа/предметы). Устанавливает
;           090Ch=9 (индекс тайла), 0909h=0 (колонка), 090Ah=19h (строка).
;           Трижды повторяет блок: если пара координат 090Ah/0909h не совпадает с
;           сохранённой позицией в 08E3h/08E5h/08E7h -> CALL func_draw_tile_at_ptr
;           (стереть старую позицию); затем записывает новые координаты в
;           08E3h/08E5h/08E7h, XCHG, A=090Ch*4, HL=data_tile_table_26DE+A
;           (func_hl_add_a), CALL func_render_tile_vram (нарисовать тайл в VRAM).
;           Примечание: блок 0x13AA-0x1476 (обработчик потери жизни/game over,
;           цель JNZ 13AAh из func_game_update) — отдельная gap-зона, не тело
;           этой функции.

func_draw_game_objects:
    MVI A, 09h                  ; 0x130A
    STA 090Ch                   ; 0x130C
    MVI A, 00h                  ; 0x130F
    STA 0909h                   ; 0x1311
    MVI A, 19h                  ; 0x1314
    STA 090Ah                   ; 0x1316
    LXI H, 08E3h                ; 0x1319
    LDA 090Ah                   ; 0x131C
    CMP M                       ; 0x131F
    JNZ loc_132C                ; 0x1320
    INX H                       ; 0x1323
    LDA 0909h                   ; 0x1324
    CMP M                       ; 0x1327
    DCX H                       ; 0x1328
    JZ loc_132F                 ; 0x1329
loc_132C:
    CALL func_draw_tile_at_ptr  ; 0x132C
loc_132F:
    LDA 090Ah                   ; 0x132F
    MOV L, A                    ; 0x1332
    LDA 0909h                   ; 0x1333
    MOV H, A                    ; 0x1336
    SHLD 08E3h                  ; 0x1337
    XCHG                        ; 0x133A
    LDA 090Ch                   ; 0x133B
    ADD A                       ; 0x133E
    ADD A                       ; 0x133F
    LXI H, data_tile_table_26DE ; 0x1340
    CALL func_hl_add_a          ; 0x1343
    CALL func_render_tile_vram  ; 0x1346
    LXI H, 08E5h                ; 0x1349
    LDA 090Ah                   ; 0x134C
    CMP M                       ; 0x134F
    JNZ loc_135C                ; 0x1350
    INX H                       ; 0x1353
    LDA 0909h                   ; 0x1354
    CMP M                       ; 0x1357
    DCX H                       ; 0x1358
    JZ loc_135F                 ; 0x1359
loc_135C:
    CALL func_draw_tile_at_ptr  ; 0x135C
loc_135F:
    LDA 090Ah                   ; 0x135F
    MOV L, A                    ; 0x1362
    LDA 0909h                   ; 0x1363
    MOV H, A                    ; 0x1366
    SHLD 08E5h                  ; 0x1367
    XCHG                        ; 0x136A
    LDA 090Ch                   ; 0x136B
    ADD A                       ; 0x136E
    ADD A                       ; 0x136F
    LXI H, data_tile_table_26DE ; 0x1370
    CALL func_hl_add_a          ; 0x1373
    CALL func_render_tile_vram  ; 0x1376
    LXI H, 08E7h                ; 0x1379
    LDA 090Ah                   ; 0x137C
    CMP M                       ; 0x137F
    JNZ loc_138C                ; 0x1380
    INX H                       ; 0x1383
    LDA 0909h                   ; 0x1384
    CMP M                       ; 0x1387
    DCX H                       ; 0x1388
    JZ loc_138F                 ; 0x1389
loc_138C:
    CALL func_draw_tile_at_ptr  ; 0x138C
loc_138F:
    LDA 090Ah                   ; 0x138F
    MOV L, A                    ; 0x1392
    LDA 0909h                   ; 0x1393
    MOV H, A                    ; 0x1396
    SHLD 08E7h                  ; 0x1397
    XCHG                        ; 0x139A
    LDA 090Ch                   ; 0x139B
    ADD A                       ; 0x139E
    ADD A                       ; 0x139F
    LXI H, data_tile_table_26DE ; 0x13A0
    CALL func_hl_add_a          ; 0x13A3
    CALL func_render_tile_vram  ; 0x13A6
    RET                         ; 0x13A9
