; Функция: func_raster_guard_hero
; Адрес: 0x1BB3
; Размер: ~90 байт
; Описание: Raster-safe страж перерисовки героя. Гарантирует, что запись тайла
;           героя (стереть prev + OR-наложить new, ~68 строк развёртки) НЕ
;           выполняется, пока луч ЭЛТ проходит по вертикальной полосе героя —
;           иначе 4 плоскости пишутся вразнобой с лучом -> мерцание/tearing.
;
;           Читает позиции из RAM: var_scr_090A = новая строка, var_enemy_rc(lo)
;           = prev-строка (обновляется позже в func_game_update). Полоса = union
;           двух строк тайла 2x2 (каждая глиф-строка = 8 растp-строк, тайл = 16):
;             band_top_line = VISIBLE_TOP + 8*min_row
;             band_bot_line = VISIBLE_TOP + 8*max_row + 15
;           Перевод в отсчёты секундомера (elapsed = строка*96), с VISIBLE_TOP=48:
;             elapsed_top = 0x1200 + (min*3)<<8      (48*96=0x1200; 8*96=768=3*256)
;             elapsed_bot = 0x17A0 + (max*3)<<8      ((48+15)*96=0x17A0)
;
;           Решение (elapsed = 0x7500 - count, растёт сверху вниз по кадру):
;             * elapsed >= elapsed_bot -> луч УЖЕ прошёл полосу => рисуем сейчас;
;             * elapsed <  elapsed_top и (elapsed_top - elapsed) >= MARGIN => луч
;               далеко СВЕРХУ, успеем отрисовать до его прихода => рисуем сейчас;
;               MARGIN теперь берётся из var_raster_margin (тики, = строки*96) и
;               задаётся КАЖДЫМ caller'ом перед CALL. 0 => fallback 0x2A00
;               (112 строк: прежнее worst-case erase+OR героя). Срез A даёт
;               caller'ам возможность сузить ahead-окно до реальной стоимости
;               paint'а: repaint_over 80 (=0x1E00), enemy_render 40 (=0x0F00),
;               hero_render/collision_death 110 (=0x2940).
;               Замер D (erase+OR-композит) в эмуляторе = ~99 строк (guard RET line 9
;               -> render RET line 108); + фаза перезагрузки ~6 => 112 с запасом.
;             * иначе (луч входит/входит в полосу) => крутимся на func_beam_count,
;               пока elapsed не >= elapsed_bot (луч прошёл), затем возврат.
;           ВАЖНО (багфикс): elapsed держим в HL, а пороги band грузим в DE через
;           LDA (НЕ LHLD — LHLD грузит в HL и затирал elapsed, из-за чего сравнения
;           съезжали на bot-count/top-count и страж всегда уходил в early-out).
;           Антизацикливатель var_raster_cap (0FFh итераций) — при исчерпании
;           выходим (fail-safe: рисуем как раньше, без вейта).
;
;           Регистры/флаги прозрачны: PUSH/POP PSW,B,D,H. Внутренне трогает C,L
;           (сохранены косвенно: C — на стеке вызывающего не нужен; стеки сохранены).
;           Вызывается ТОЛЬКО на уровне (после EI;HLT и перед redraw'ом героя);
;           на заставке var_raster_flag=0 и секундомер не идёт — сюда не попадаем.

func_raster_guard_hero:
    PUSH PSW                    ; 0x1BB3
    PUSH B
    PUSH D
    PUSH H
    ; --- min/max строк: new=var_scr_090A, prev=var_enemy_rc(lo) ---
    LDA var_scr_090A
    MOV C, A                    ; C = new row
    LDA var_enemy_rc
    MOV B, A                    ; B = prev row
    MOV A, B
    SUB C                       ; prev - new
    JC  loc_gr_newlt            ; заём => prev<new
    MOV D, C                    ; min = new
    MOV E, B                    ; max = prev
    JMP loc_gr_band
loc_gr_newlt:
    MOV D, B                    ; min = prev
    MOV E, C                    ; max = new
loc_gr_band:
    ; elapsed_top = 0x1200 + (min*3)<<8
    MOV A, D
    ADD A
    ADD D                       ; A = min*3
    ADI 12h                     ; + (48*96)>>8
    MOV H, A
    MVI L, 00h
    SHLD var_raster_top
    ; elapsed_bot = 0x17A0 + (max*3)<<8
    MOV A, E
    ADD A
    ADD E                       ; A = max*3
    ADI 17h                     ; + ((48+15)*96)>>8
    MOV H, A
    MVI L, 0A0h
    SHLD var_raster_bot
    ; антизацикливатель
    MVI A, 0FFh
    STA var_raster_cap
loc_gr_loop:
    CALL func_beam_count        ; DE = count
    ; elapsed(HL) = 0x7500 - count
    LXI H, 7500h
    MOV A, L
    SUB E
    MOV L, A
    MOV A, H
    SBB D
    MOV H, A                    ; HL = elapsed
    ; (1) elapsed >= elapsed_bot ?  -> луч прошёл -> рисуем сейчас
    LDA var_raster_bot          ; A = bot_lo
    MOV E, A
    LDA var_raster_bot+1        ; A = bot_hi
    MOV D, A                    ; DE = bot (HL = elapsed сохранён)
    MOV A, L
    SUB E
    MOV A, H
    SBB D
    JNC loc_gr_ret              ; без займа => elapsed>=bot => past
    ; (2) elapsed >= elapsed_top ?  -> внутри [top,bot) -> ждать
    LDA var_raster_top          ; A = top_lo
    MOV E, A
    LDA var_raster_top+1        ; A = top_hi
    MOV D, A                    ; DE = top (HL = elapsed)
    MOV A, L
    SUB E
    MOV A, H
    SBB D
    JC  loc_gr_below            ; заём => elapsed<top => возможно «далеко»
    JMP loc_gr_wait             ; top<=elapsed<bot => луч в полосе -> ждать
loc_gr_below:
    ; gap = elapsed_top - elapsed ; если gap >= MARGIN -> далеко -> рисуем сейчас
    ; HL = elapsed, DE = top (уже загружен на шаге 2)
    MOV A, E
    SUB L
    MOV C, A                    ; gap_lo
    MOV A, D
    SBB H
    MOV B, A                    ; gap_hi  (BC = gap = top - elapsed > 0)
    ; МARGIN теперь per-caller из var_raster_margin (тики). 0 => default 0x2A00
    ; (прежнее поведение, если caller не объял стоимость).
    LDA var_raster_margin
    MOV E, A
    LDA var_raster_margin+1
    MOV D, A
    MOV A, E
    ORA D
    JNZ loc_gr_margin_ok
    LXI D, 2A00h                ; default MARGIN = 112*96
loc_gr_margin_ok:
    MOV A, C
    SUB E
    MOV A, B
    SBB D
    JNC loc_gr_ret              ; gap>=MARGIN => безопасно сейчас
loc_gr_wait:
    LXI H, var_raster_cap
    DCR M
    JZ  loc_gr_ret              ; cap исчерпан => bail (рисуем)
    JMP loc_gr_loop
loc_gr_ret:
    POP H
    POP D
    POP B
    POP PSW
    RET

; Функция: func_raster_guard_enemy
; Описание: Страж полосы отложенного burst'а погонщика (копия func_raster_guard_hero,
;           но строки берутся из var_ed_dr (prev) и var_ed_newr (new)). Плюс
;           нижняя граница полосы расширяется на строку при активном вертикальном
;           спиле (var_ed_vo!=0 или var_ed_newv!=0) — покрыть 4px сдвинутого вида.
;           Те же пороги (VISIBLE_TOP=48, elapsed=0x7500-count, MARGIN=0x2A00) и тот
;           же антизацикливатель. Регистры прозрачны: PUSH/POP PSW,B,D,H (C/L трогает
;           косвенно — вызывающий func_enemy_chaser_apply не держит в них живых).
func_raster_guard_enemy:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    ; --- min/max строк: new=var_ed_newr, prev=var_ed_dr ---
    LDA var_ed_newr
    MOV C, A                    ; C = new row
    LDA var_ed_dr
    MOV B, A                    ; B = prev row
    MOV A, B
    SUB C                       ; prev - new
    JC  loc_gre_newlt
    MOV D, C                    ; min = new
    MOV E, B                    ; max = prev
    JMP loc_gre_spill
loc_gre_newlt:
    MOV D, B                    ; min = prev
    MOV E, C                    ; max = new
loc_gre_spill:
    ; спил вниз на 4px добавляет строку к нижней границе полосы
    LDA var_ed_newv
    ORA A
    JNZ loc_gre_e1
    LDA var_ed_vo
    ORA A
    JZ  loc_gre_band
loc_gre_e1:
    INR E                       ; max+1 строка
loc_gre_band:
    ; elapsed_top = 0x1200 + (min*3)<<8
    MOV A, D
    ADD A
    ADD D                       ; A = min*3
    ADI 12h                     ; + (48*96)>>8
    MOV H, A
    MVI L, 00h
    SHLD var_raster_top
    ; elapsed_bot = 0x17A0 + (max*3)<<8
    MOV A, E
    ADD A
    ADD E                       ; A = max*3
    ADI 17h                     ; + ((48+15)*96)>>8
    MOV H, A
    MVI L, 0A0h
    SHLD var_raster_bot
    MVI A, 0FFh
    STA var_raster_cap
loc_gre_loop:
    CALL func_beam_count        ; DE = count
    ; elapsed(HL) = 0x7500 - count
    LXI H, 7500h
    MOV A, L
    SUB E
    MOV L, A
    MOV A, H
    SBB D
    MOV H, A                    ; HL = elapsed
    ; (1) elapsed >= elapsed_bot ?  -> луч прошёл -> рисуем сейчас
    LDA var_raster_bot
    MOV E, A
    LDA var_raster_bot+1
    MOV D, A                    ; DE = bot
    MOV A, L
    SUB E
    MOV A, H
    SBB D
    JNC loc_gre_ret             ; elapsed>=bot -> past
    ; (2) elapsed >= elapsed_top ?  -> внутри [top,bot) -> ждать
    LDA var_raster_top
    MOV E, A
    LDA var_raster_top+1
    MOV D, A                    ; DE = top
    MOV A, L
    SUB E
    MOV A, H
    SBB D
    JC  loc_gre_below           ; elapsed<top -> возможно «далеко»
    JMP loc_gre_wait            ; top<=elapsed<bot -> луч в полосе -> ждать
loc_gre_below:
    ; gap = elapsed_top - elapsed ; если gap >= MARGIN -> далеко -> рисуем сейчас
    MOV A, E
    SUB L
    MOV C, A                    ; gap_lo
    MOV A, D
    SBB H
    MOV B, A                    ; gap_hi  (BC = gap > 0)
    ; МARGIN теперь per-caller из var_raster_margin (тики). 0 => default 0x2A00.
    LDA var_raster_margin
    MOV E, A
    LDA var_raster_margin+1
    MOV D, A
    MOV A, E
    ORA D
    JNZ loc_gre_margin_ok
    LXI D, 2A00h                ; default MARGIN = 112*96
loc_gre_margin_ok:
    MOV A, C
    SUB E
    MOV A, B
    SBB D
    JNC loc_gre_ret             ; gap>=MARGIN -> безопасно сейчас
loc_gre_wait:
    LXI H, var_raster_cap
    DCR M
    JZ  loc_gre_ret             ; cap исчерпан -> bail
    JMP loc_gre_loop
loc_gre_ret:
    POP H
    POP D
    POP B
    POP PSW
    RET
