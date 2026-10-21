; Функция: func_hero_render
; Адрес: 0x1C60
; Описание: Easing-машина суб-пиксельной отрисовки героя (ШАГ 2a, Вариант A).
;           Вызывается ИЗ ГЛАВНОГО ЦИКЛА каждый hw-кадр (после func_render_all,
;           до гейта полукадров). Теперь герой рисуется СЮДА, а не из
;           func_game_update: игровая логика (var_player_row/col, коллизии,
;           темп) не меняется — game_update лишь выставляет ЦЕЛЬ, а здесь цель
;           плавно догоняется по 4px по ВЕРТИКАЛИ (горизонталь — мгновенно).
;
;           СОСТОЯНИЕ отображения героя (единственные источники истины для
;           отрисовки): var_enemy_rc(lo=строка cr, hi=колонка) + var_glyph_voff(cv,
;           0..4; читает func_render_glyph_or -> L-=voff, сдвиг вниз). ЦЕЛЬ:
;           var_player_row (tr), var_player_col (tc).
;
;           РЕШЕНИЕ (на этот кадр), инкрементально, без деления:
;             * col != tc .............................. горизонталь: мгновенно,
;               new=(tr, cv=0) — шаг по колонке не твинимус (Step 2b отдельно).
;             * col == tc, cv==0, tr==cr ............... покой -> new==old ->
;               НИЧЕГО не перерисовываем (0 стоимости/фликера на idle-кадрах).
;             * col == tc, cv==0, tr==cr+1 ............. падение на 1 клетку:
;               вставляем midpoint new=(cr, cv=4) (сдвиг вниз на 4px).
;             * col == tc, cv!=0 ....................... завершаем midpoint:
;               new=(tr, cv=0) — дозаезд ровно в цель.
;             * col == tc, иначе (rise/>1 клетки) ...... snap new=(tr, cv=0).
;
;           ERASE-ПРЯМОУГОЛЬНИК старого отображения (restore фона из текстового
;           буфера выровненным func_render_glyph, котopый voff НЕ читает):
;             footprint cv==0 -> 2 строки [cr..cr+1]; cv!=0 -> 3 строки
;             [cr..cr+2] (спил сдвинутого вниз спрайта в нижнюю клетку). Делаем
;             2x2@(cr) + (если cv!=0) 2x2@(cr+1) через func_draw_tile_at_ptr.
;
;           RASTER-GUARD: полоса гашения = union(старой cr в var_enemy_rc и новой
;           строки в var_scr_090A). При cv!=0 добавляем к новой строке +1, чтобы
;           нижняя границка полосы покрыла спил сдвинутого спрайта (без tearing).
;
;           Прозрачность для вызывающего: PUSH/POP PSW,B,D,H (внутренне трогает
;           A,B,C,D,E,H,L; стека вызывающего не задевает). Порядок: guard ->
;           erase(starое) -> коммит new в var_enemy_rc/var_glyph_voff -> OR-draw.

func_hero_render:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    ; --- снимок СТАРОГО отображения (для erase-прямоугольника) ---------------
    LDA var_enemy_rc                   ; old row (lo)
    STA var_hero_orow
    LDA var_enemy_rc+1                 ; old col (hi)
    STA var_hero_ocow
    LDA var_glyph_voff                 ; old cv
    STA var_hero_ocv
    ; --- решение: proposed new = (E=row, C=cv, D=col) ------------------------
    LDA var_player_col
    MOV D, A                           ; D = tc (новая колонка)
    LDA var_hero_ocow
    MOV L, A                           ; L = oldcol (8080: SUB только через регистр)
    MOV A, D
    SUB L                              ; tc - oldcol
    JNZ loc_hr_hmove                   ; горизонталь -> мгновенно
    ; col стабилен: разбираем вертикаль
    LDA var_hero_ocv
    ORA A
    JNZ loc_hr_finish                  ; cv!=0 -> доезжаем midpoint в цель
    LDA var_hero_orow
    MOV L, A                           ; L = cr (8080: SUB только через регистр)
    LDA var_player_row                 ; A = tr
    SUB L                              ; tr - cr
    JZ loc_hr_rest                     ; aligned & та же строка -> покой
    CPI 01h                            ; ровно +1 вниз (падение)?
    JNZ loc_hr_snap                    ; иначе (rise / >1 клетки) -> snap
    LDA var_hero_orow
    MOV E, A                           ; new row = cr (остаёмся в клетке)
    MVI C, 04h                         ; new cv = 4 (midpoint вниз)
    JMP loc_hr_decided
loc_hr_rest:
    LDA var_hero_orow
    MOV E, A                           ; new = old (строка)
    LDA var_hero_ocv
    MOV C, A                           ; new = old (cv) -> decided пропустит
    JMP loc_hr_decided
loc_hr_hmove:
loc_hr_finish:
loc_hr_snap:
    LDA var_player_row
    MOV E, A                           ; new row = tr (мгновенно)
    MVI C, 00h                         ; cv = 0
loc_hr_decided:
    ; --- if (E,C,D)==(orow,ocv,ocol) -> ничего не делаем (idle) --------------
    LDA var_hero_orow
    CMP E
    JNZ loc_hr_move
    LDA var_hero_ocv
    CMP C
    JNZ loc_hr_move
    LDA var_hero_ocow
    CMP D
    JZ loc_hr_done                     ; без изменений -> не перерисовываем
loc_hr_move:
    ; --- заготовим new-состояние; cv пишем сейчас (erase его НЕ читает) ------
    MOV A, E
    STA var_hero_newr
    MOV A, D
    STA var_hero_newc
    MOV A, C
    STA var_glyph_voff
    ; --- raster guard: полоса = var_enemy_rc(old cr) ∪ var_scr_090A(новая) ----
    MOV A, E
    ORA C
    JZ loc_hr_band0
    INR A                              ; cv!=0 -> +1 строка (покрыть спил снизу)
loc_hr_band0:
    STA var_scr_090A
    CALL func_raster_guard_hero
    ; --- ERASE старого footprint (restore фона из текстового буфера) ----------
    LDA var_hero_ocow
    STA var_hero_ecol                  ; (HL+1)=col
    LDA var_hero_orow
    STA var_hero_erow                  ; (HL)=row
    LXI H, var_hero_erow
    CALL func_draw_tile_at_ptr         ; 2x2 @ (cr, col)
    LDA var_hero_ocv
    ORA A
    JZ loc_hr_erased                   ; cv==0: 2 строки достаточно
    LDA var_hero_erow
    INR A                              ; row = cr+1 (третяя строка спила)
    STA var_hero_erow
    LXI H, var_hero_erow
    CALL func_draw_tile_at_ptr         ; 2x2 @ (cr+1, col)
loc_hr_erased:
    ; --- коммит NEW отображения в кэш (после erase, котopый варит var_hero_*) -
    LDA var_hero_newr
    STA var_enemy_rc                   ; lo = new row
    LDA var_hero_newc
    STA var_enemy_rc+1                 ; hi = new col
    ; --- указатель графики тайла героя = data_tile_table_26DE + idx*4 ----------
    ;     idx = work_const + 3*move_dir - 1 (та же формула, что loc_0D6D).
    LDA var_move_dir
    MOV B, A
    RLC
    ADD B                              ; 3*move_dir
    MOV B, A
    LDA var_work_const
    ADD B
    DCR A                              ; idx
    ADD A
    ADD A                              ; idx*4
    LXI H, data_tile_table_26DE
    CALL func_hl_add_a                 ; HL = указатель графики тайла
    ; --- DE = (D=col, E=row) НОВОЙ позиции (erase clobbered D/E/B) ------------
    LDA var_enemy_rc+1
    MOV D, A
    LDA var_enemy_rc
    MOV E, A
    CALL func_render_tile_vram_or      ; OR-композит; читает var_glyph_voff (сдвиг)
loc_hr_done:
    POP H
    POP D
    POP B
    POP PSW
    RET
