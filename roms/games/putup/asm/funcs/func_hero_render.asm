; Функция: func_hero_render
; Адрес: 0x1C60
; Описание: Easing-машина суб-пиксельной отрисовки героя (ШАГ 2a/2b, Вариант A).
;           Вызывается ИЗ ГЛАВНОГО ЦИКЛА каждый hw-кадр (после func_render_all,
;           до гейта полукадров). Герой рисуется СЮДА, а не из func_game_update:
;           игровая логика (var_player_row/col, коллизии, темп) не меняется —
;           game_update лишь выставляет ЦЕЛЬ, а здесь цель плавно догоняется по
;           4px по ВЕРТИКАЛИ (var_glyph_voff) И ГОРИЗОНТАЛИ (var_glyph_hoff).
;
;           СОСТОЯНИЕ отображения героя (единственные источники истины):
;           var_enemy_rc(lo=строка cr, hi=колонка cc) + var_glyph_voff(cv, 0..4;
;           func_blit_glyph_or -> L-=voff, сдвиг вниз) + var_glyph_hoff(ch, 0..2;
;           midpoint-режим горизонтали: 1=сдвиг 4px в cc+1, 2=сдвиг 4px в cc-1).
;           ЦЕЛЬ: var_player_row (tr), var_player_col (tc).
;
;           РЕШЕНИЕ (на этот кадр), инкрементально, без деления (приоритет:
;           сначала доехать любой активный midpoint, потом завести новый):
;             * ohoff!=0 ..................... доезжаем горизонтальный midpoint:
;               new=(tr, cv=0, col=tc, hoff=0). (hoff!=0 <=> cc!=tc по инварианту.)
;             * ohoff==0, tc!=cc ............. СТАРТ горизонтального midpoint:
;               col остаётся cc, hoff=1 (tc>cc, вправо) / 2 (tc<cc, влево), row=cr, cv=0.
;               рисуется широкй 3-колоночный OR-blit из кэша (func_render_tile_vram_or3).
;             * tc==cc, cv!=0 ................ доезжаем вертикальный midpoint:
;               new=(tr, cv=0, hoff=0).
;             * tc==cc, cv==0, tr==cr ........ покой -> new==old. Перерисовка, только
;               если СМЕНИЛСЯ кадр анимации (предлагаемый idx != var_hero_idx —
;               последний нарисованный); иначе НИЧЕГО (0 фликера). Это ловит
;               остановку после ходьбы: клетка та же, но work_const=стойка.
;             * tc==cc, cv==0, tr==cr+1 ...... падение: midpoint new=(cr, cv=4).
;             * tc==cc, cv==0, иначе ......... snap new=(tr, cv=0, hoff=0).
;
;           ERASE старого footprint (restore фона выровненным func_render_glyph,
;           котopый voff/hoff НЕ читает): колонки = oldcol..oldcol+1, РАСШИРЯЮТСЯ
;           до 3 колонок при ohoff!=0 (base=oldcol при hoff=1, oldcol-1 при hoff=2);
;           строки = cr..cr+1, РАСШИРЯЮТСЯ до cr+2 при ocv!=0. Реализовано до
;           4 вызовов func_draw_tile_at_ptr (2x2) по декартову произведению.
;
;           RASTER-GUARD: полоса гашения = union(старой cr в var_enemy_rc и новой
;           строки в var_scr_090A). При cv!=0 добавляем +1 строку (нижняя граница
;           полосы покрыла спил сдвинутого вниз спрайта). hoff не меняет набор строк.
;
;           Прозрачность для вызывающего: PUSH/POP PSW,B,D,H. Порядок: snapshot ->
;           решение -> (idle? выход) -> коммит voff/hoff -> guard -> erase ->
;           коммит new в var_enemy_rc -> OR-draw (or2 hoff=0 / or3 hoff!=0).

func_hero_render:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    ; --- HERO-IN-WALL фикс: отложить форс по sentinel'у до 1-го прохода гравит. -
    ;     var_hero_idx=0xFF (засиднен в func_level_loader) форсит СТОЯЧУЮ
    ;     отрисовку в воздушном спауне на самом 1-м кадре — герой «висит» так до
    ;     первого func_game_update (sub==6) и только потом падает («голова на
    ;     кирпиче над позицией», на любом уровне). Пока sentinel не снят И sub<6
    ;     (гравитация ещё не действовала) — ничего не рисуем, sentinel НЕ трогаем.
    ;     На sub>=6 форс сработает уже в упавшей/покоящейся клетке.
    LDA var_hero_idx
    CPI 0FFh
    JNZ loc_hr_firstok
    LDA var_frame_sub
    CPI 06h
    JC loc_hr_done                   ; ранний выход: POP H/D/B/PSW; RET
loc_hr_firstok:
    ; --- снимок СТАРОГО отображения (для erase-прямоугольника) ---------------
    LDA var_enemy_rc                   ; old row (lo)
    STA var_hero_orow
    LDA var_enemy_rc+1                 ; old col (hi)
    STA var_hero_ocow
    LDA var_glyph_voff                 ; old cv
    STA var_hero_ocv
    LDA var_glyph_hoff                 ; old hoff
    STA var_hero_ohoff
    ; --- предлагаемый индекс тайла-героя (кадр/направление) ----------------------
    ;     idx = var_work_const + 3*var_move_dir - 1. Считается ДО решения, чтобы
    ;     детектировать смену кадра даже при неизменной позиции (остановка после
    ;     ходьбы: work_const=стойка при той же клетке). L — temp (свободен здесь).
    LDA var_move_dir
    MOV L, A
    RLC
    ADD L                              ; 3*move_dir
    MOV L, A
    LDA var_work_const
    ADD L
    DCR A
    STA var_hero_newidx
    ; --- решение: proposed new = (E=row, C=cv, D=col, B=hoff) ----------------
    LDA var_player_col
    MOV D, A                           ; D = tc (заодно предположим snap-колонку)
    MVI B, 00h                         ; new hoff = 0 (переопределяет только hstart)
    ; --- доезжаем активный горизонтальный midpoint? (ohoff != 0) -------------
    LDA var_hero_ohoff
    ORA A
    JZ loc_hr_hcheck                   ; hoff==0 -> разбираем старт горизонтали
    LDA var_player_row                 ; доехать: col=tc(D), hoff=0(B), row=tr, cv=0
    MOV E, A
    MVI C, 00h
    JMP loc_hr_decided
loc_hr_hcheck:
    ; --- старт горизонтального midpoint? (tc != oldcol) ----------------------
    LDA var_hero_ocow
    MOV L, A                           ; L = oldcol
    MOV A, D                           ; A = tc
    SUB L                              ; tc - oldcol
    JZ loc_hr_vert                     ; кол стабильна -> вертикаль
    LDA var_player_col
    SUB L                              ; A = tc - oldcol (CY=1 если едем ВЛЕВО)
    JC loc_hr_hs_left
    ; ВПРАВО (hoff=1): рисуем cols oldcol..oldcol+2 -> нужен oldcol <= 29
    LDA var_hero_ocow
    CPI 1Eh                            ; oldcol >= 30? (CY=0 -> JNC)
    JNC loc_hr_snap                    ; у правой стены -> мгновенно (без spill-забора)
    LDA var_hero_ocow
    MOV D, A                           ; new col = oldcol (midpoint клеткой не едет)
    LDA var_hero_orow
    MOV E, A                           ; new row = cr
    MVI C, 00h                         ; cv = 0
    MVI B, 01h                         ; hoff=1: midpoint в col+1 (вправо)
    JMP loc_hr_decided
loc_hr_hs_left:
    ; ВЛЕВО (hoff=2): рисуем cols oldcol-1..oldcol+1 -> нужен oldcol >= 1
    LDA var_hero_ocow
    CPI 01h                            ; oldcol == 0? (CY=1 -> JC)
    JC loc_hr_snap                     ; у левой стены -> мгновенно
    LDA var_hero_ocow
    MOV D, A                           ; new col = oldcol
    LDA var_hero_orow
    MOV E, A                           ; new row = cr
    MVI C, 00h                         ; cv = 0
    MVI B, 02h                         ; hoff=2: midpoint в col-1 (влево)
    JMP loc_hr_decided
loc_hr_vert:
    ; --- col стабильна: разбираем вертикаль -------------------------------
    LDA var_hero_ocv
    ORA A
    JNZ loc_hr_finish                  ; cv!=0 -> доезжаем vertical midpoint
    LDA var_hero_orow
    MOV L, A                           ; L = cr
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
loc_hr_finish:
loc_hr_snap:
    LDA var_player_row
    MOV E, A                           ; new row = tr (мгновенно)
    MVI C, 00h                         ; cv = 0 (D=tc уже)
loc_hr_decided:
    ; --- if (E,C,D,B)==(orow,ocv,ocol,ohoff) -> ничего (idle) ----------------
    LDA var_hero_orow
    CMP E
    JNZ loc_hr_move
    LDA var_hero_ocv
    CMP C
    JNZ loc_hr_move
    LDA var_hero_ocow
    CMP D
    JNZ loc_hr_move
    LDA var_hero_ohoff
    CMP B
    JNZ loc_hr_move                    ; hoff изменился -> перерисовать
    ; Позиция/easing не изменились, но мог смениться КАДР анимации (остановка
    ; после ходьбы: work_const=стойка при той же клетке). var_hero_idx хранит
    ; ПОСЛЕДНИЙ НАРИСОВАННЫЙ индекс (обновляется только при реальном рисовании),
    ; поэтому сверяем предлагаемый idx с ним, а не с самим собой.
    LDA var_hero_newidx
    MOV L, A                           ; L = proposed idx (L here свободна)
    LDA var_hero_idx                   ; A = последний нарисованный idx
    CMP L                              ; CMP r (8080): A - L
    JZ loc_hr_done                     ; idx тот же -> истинный покой, 0 фликера
    JMP loc_hr_move                    ; сменился кадр -> перерисовать стоячим
loc_hr_move:
    ; --- заготовим new-состояние; cv/hoff пишем сейчас (erase читает оcv/оhoff) -
    MOV A, E
    STA var_hero_newr
    MOV A, D
    STA var_hero_newc
    MOV A, C
    STA var_glyph_voff
    MOV A, B
    STA var_glyph_hoff
    ; --- фиксируем нарисованный индекс тайла-героя (уже посчитан в var_hero_newidx) --
    LDA var_hero_newidx
    STA var_hero_idx
    ; --- raster guard: полоса = var_enemy_rc(old cr) ∪ var_scr_090A(новая) ----
    LDA var_hero_newr
    MOV E, A                           ; E = new row
    MOV A, E
    ORA C                              ; C = new cv
    JZ loc_hr_band0
    INR A                              ; cv!=0 -> +1 строка (покрыть спил снизу)
loc_hr_band0:
    STA var_scr_090A
    ; Срез A: cost-hint = erase+OR (up to 3-col wide + spill) ~110 строк*96 = 0x2940
    PUSH H
    LXI H, 2940h
    SHLD var_raster_margin
    POP H
    CALL func_raster_guard_hero
    ; --- ERASE старого footprint (restore фона из текстового буфера) ----------
    ; base = oldcol; при hoff=2 base=oldcol-1; wide = (ohoff!=0) -> доп. колонка.
    LDA var_hero_ocow
    STA var_hero_ebase
    LDA var_hero_ohoff
    CPI 02h
    JNZ loc_hr_eb1
    LDA var_hero_ebase
    SUI 01h
    STA var_hero_ebase                 ; base = oldcol-1 (hoff влево)
loc_hr_eb1:
    ; строка cr: 2x2 @ (cr, base); если wide -> ещё 2x2 @ (cr, base+1)
    LDA var_hero_ebase
    STA var_hero_ecol
    LDA var_hero_orow
    STA var_hero_erow
    LXI H, var_hero_erow
    CALL func_draw_tile_at_ptr
    LDA var_hero_ohoff
    ORA A
    JZ loc_hr_e_cv
    LDA var_hero_ebase
    INR A
    STA var_hero_ecol
    LXI H, var_hero_erow               ; erow всё ещё cr
    CALL func_draw_tile_at_ptr
loc_hr_e_cv:
    LDA var_hero_ocv
    ORA A
    JZ loc_hr_erased                   ; cv==0: 2 строки (cr,cr+1) достаточно
    ; строка cr+1 (спил вниз): те же колонки (base, и base+1 если wide)
    LDA var_hero_ebase
    STA var_hero_ecol
    LDA var_hero_orow
    INR A
    STA var_hero_erow                  ; erow = cr+1
    LXI H, var_hero_erow
    CALL func_draw_tile_at_ptr
    LDA var_hero_ohoff
    ORA A
    JZ loc_hr_erased
    LDA var_hero_ebase
    INR A
    STA var_hero_ecol
    LXI H, var_hero_erow               ; erow = cr+1
    CALL func_draw_tile_at_ptr
loc_hr_erased:
    ; --- коммит NEW отображения в кэш (после erase, котopый варит var_hero_*) -
    LDA var_hero_newr
    STA var_enemy_rc                   ; lo = new row
    LDA var_hero_newc
    STA var_enemy_rc+1                 ; hi = new col
    ; --- OR-draw: hoff==0 -> 2x2 из тайл-графики; hoff!=0 -> 3 колонки из кэша -
    LDA var_glyph_hoff
    ORA A
    JNZ loc_hr_draw3
    LDA var_hero_idx
    ADD A
    ADD A                              ; idx*4
    LXI H, data_tile_table_26DE
    CALL func_hl_add_a                 ; HL = указатель графики тайла
    LDA var_enemy_rc+1
    MOV D, A
    LDA var_enemy_rc
    MOV E, A
    CALL func_render_tile_vram_or      ; OR-композит; читает var_glyph_voff
    JMP loc_hr_done
loc_hr_draw3:
    ; --- широкий 3-колоночный OR-blit из кэша (func_render_tile_vram_or3) -----
    ; HL = data_hero_shift_cache + idx*192 (6 фрагментов: 3 колонки x 2 строки)
    LDA var_hero_idx
    MOV E, A                           ; E = счётчик (idx)
    MVI D, 00h
    LXI H, 0000h
    MOV A, E
    ORA A
    JZ loc_hr_cdone                    ; idx==0 -> HL=0
loc_hr_cm192:
    MOV A, L
    ADI 0C0h                           ; +192 (блок тайла = 6*32)
    MOV L, A
    MOV A, H
    ACI 00h
    MOV H, A
    DCR E
    JNZ loc_hr_cm192
loc_hr_cdone:
    LXI D, data_hero_shift_cache
    DAD D                              ; HL = база кэша для idx
    ; D = base col = curcol - (hoff==2?1:0); E = row (curcol = var_enemy_rc.hi)
    LDA var_enemy_rc+1
    MOV D, A
    LDA var_glyph_hoff
    CPI 02h
    JNZ loc_hr_d3ok
    LDA var_enemy_rc+1
    SUI 01h
    MOV D, A                           ; hoff влево -> base = curcol-1
loc_hr_d3ok:
    LDA var_enemy_rc                   ; row
    MOV E, A
    CALL func_render_tile_vram_or3     ; 3 колонки из кэша; читает var_glyph_voff
loc_hr_done:
    POP H
    POP D
    POP B
    POP PSW
    RET
