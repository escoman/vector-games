; ============================================================================
; Функция: func_gen_level   (RANDOM PUTUP, Stage 2 — рантайм-генератор уровней)
; Вызов:   из lbl_title_key_poll на старте игры (после func_music_start_track,
;          перед JMP func_level_loader) — т.е. «по нажатию пробела», ОДИН раз.
;
; Идея (минимальные правки исходной игры): НЕ вводить новые RAM-буферы, а
;   ЗАПОЛНИТЬ ПЕРИМЕТРОМ/ПУСТОТОЙ уже существующие массивы прямо в ОЗУ:
;     * data_level_maps — 15 карт по 176 Б (row-major 16 колонок x 11 рядов),
;       карта N лежит по data_level_maps + (N-1)*0xB0 (так же их читает loader);
;     * data_level_params — 16 записей по 8 Б (описатель уровня: exit X/Y +
;       2 сущности state/X/Y); запись уровня N лежит по data_level_params + N*8.
;   Образ грузится на 0x0100 в ОЗУ, поэтому обе таблицы перезаписываемы;
;   func_level_loader остаётся НЕТРОНУТЫМ и читает то, что написал генератор.
;
; Шаг 1 (каркас): каждая карта — периметр стеной (тайл 0x02), интерьер пустой/
;   проходимый (тайл 0x01; байт карты = ИНДЕКС в data_tile_graphics, 0x01 —
;   запись «4 пробела 0x20»), пол row10 — сплошная стена (опора коридора row9).
; Шаг 2 (random, решаемость ПО КОНСТРУКЦИИ): см. блок rgl_gen ниже.
; Шаг 3 (кураторский уровень 1): поверх каркаса кладётся СПРОЕКТИРОВАННАЯ карта
;   и описатель уровня 1 (гарантированный референс для регресс-теста).
;
; Счётчики внешних циклов — в RAM (rgl_cnt): стек 8080 умеет только 16-битные
;   пары (PUSH/POP B|D|H|PSW), одиночные регистры (C/E) push-ить нельзя.
; Регистры не сохраняются (вызывающий их пересоздаёт). Scratch/состояние цикла —
;   в rand_ram_symbols.asm (rgl_mapbase/descbase/s1../y2).
; ============================================================================

func_gen_level:
    ; ---------------------------------------------------------------------
    ; 1) 15 карт: залить всё тайлом 0x01, затем периметр тайлом 0x02.
    ;    HL — курсор по tableau карт (176 Б подряд); rgl_cnt — счётчик карт.
    ; ---------------------------------------------------------------------
    LXI H, data_level_maps
    MVI A, 15
    STA rgl_cnt                         ; карт (data_level_01..15)
rgl_map_loop:
    PUSH H                              ; база текущей карты
    ; --- memset 176 -> 0x01 (пустая/проходимая клетка) ---
    MVI B, 176
rgl_mem_lp:
    MVI M, 01h
    INX H
    DCR B
    JNZ rgl_mem_lp                      ; HL = база + 176
    POP H                               ; HL = база карты (row0,col0)
    ; --- row0: 16 стен ---
    MVI B, 16
rgl_r0:
    MVI M, 02h
    INX H
    DCR B
    JNZ rgl_r0                          ; HL = row1,col0
    ; --- rows 1..9: col0 и col15 стены (interior остаётся 0x01) ---
    MVI E, 9                            ; E — счётчик рядов 1..9 (to15 его не трогает)
rgl_rn:
    MVI M, 02h                          ; col0
    MVI B, 15
rgl_to15:
    INX H
    DCR B
    JNZ rgl_to15                        ; HL = col15
    MVI M, 02h                          ; col15
    INX H                               ; HL = col0 следующего ряда
    DCR E
    JNZ rgl_rn                          ; HL = row10,col0
    ; --- row10: 16 стен ---
    MVI B, 16
rgl_r10:
    MVI M, 02h
    INX H
    DCR B
    JNZ rgl_r10                         ; HL = база + 176 = следующая карта
    LDA rgl_cnt
    DCR A
    STA rgl_cnt
    JNZ rgl_map_loop

    ; =====================================================================
    ; 2) РАНДОМНАЯ НАЧИНКА уровней 2..15 (Stage 2b — «RANDOM»).
    ;    Решаемость ПО КОНСТРУКЦИИ (см. GAMEPLAY.MD §10):
    ;      * герой стартует char(1,2)=tile(0,1), падает по col1 на пол row9
    ;        (опора — сплошная стена row10), дальше идёт ВДОЛЬ коридора row9;
    ;      * на row9 кладём ТОЛЬКО пол/ключ(0x07)/фрукт(0x0A..0x0D) — у всех
    ;        TL<0x77, значит горизонтальный ход НИКОГДА не блокируется ⇒ путь
    ;        ключ→замок-сверху→выход существует всегда;
    ;      * замок(0x08) и скрытая коробка(0x05) — в полу row10 (твёрдые),
    ;        герой встаёт НАД ними (char row18, char col=2*colX — чётный) и
    ;        жмёт DOWN (func_player_move_d/loc_106B) → var_egg_seq++; замок
    ;        пишем ПОСЛЕДНИМ в row10, чтобы не был перезаписан коробкой;
    ;      * огонь(0x06) — отдельные клетки в воздухе (rows 3..7, cols 4..11):
    ;        вне коридора row9 и вне col1 (линия падения); опасен при лазании;
    ;      * 2 врага — ГОРИЗОНТАЛЬНЫЕ (state 1/2) в air-рядах 3..7, запертые
    ;        НЕВИДИМЫМИ отражателями (тайл 3, 0x60) на col2 и col13 своего ряда:
    ;        враг отскакивает (0x60!=0x20), герой проходит (0x60<0x77). Так они
    ;        не заходят ни на col1 (спавн), ни на коридор row9 (фикс. высота).
    ;    Число ключей B = 1 для lv 2..9, 2 для lv 10..15 (B = порог var_egg_seq).
    ;    Итераций 14 (уровни 2..15). rgl_mapbase: карта lv2 (base+176), +176.
    ;    rgl_descbase: описатель lv2 (params+16), +8.
    ; =====================================================================
    LXI H, data_level_maps+176          ; карта уровня 2
    SHLD rgl_mapbase
    LXI H, data_level_params+16         ; описатель уровня 2 (record 2)
    SHLD rgl_descbase
    MVI A, 02h
    STA rgl_level                       ; номер уровня (2..15)
    MVI A, 14                           ; 14 итераций (уровни 2..15)
    STA rgl_cnt
rgl_gen:
    ; ---- B = число ключей: 1 (lv<10) / 2 (lv>=10) ----
    LDA rgl_level
    CPI 10
    JC rgl_b1
    MVI A, 02h
    JMP rgl_haveb
rgl_b1:
    MVI A, 01h
rgl_haveb:
    STA rgl_run                         ; rgl_run = B

    ; ---- ОГОНЬ (#4): перенесён БЛОКОМ ПОСЛЕ МЕБЕЛИ (нужен routeRight, чтобы
    ;      класть «огонь на дне» правее обязательного маршрута). См. rgl_fire_draw.

    ; ---- ПЛАТФОРМЫ (Stage 5 / #3): 1..2 горизонтальных уступа из стен (0x02).
    ;      #3: раньше ряд брался из rgl_erow8 (air 3..7) — ВЫШЕ высоты прыжка, ни
    ;      на одну платформу нельзя запрыгнуть. Теперь ряд = rgl_prow8 = row8:
    ;      герой на коридоре row9 прыжком поднимается на 2 тайл-ряда (var_scr_0906
    ;      доезжает до 4 знакорядов, func_gamestate_handlers loc_12E0) => ногами на
    ;      row7, опираясь на solid row8. Т.е. solid ровно на 1 ряд выше пола —
    ;      ЕДИНСТВЕНная высота, запрыгиваемая с земли за 1 прыжок.
    ;      Платформы НЕ трогают коридор row9 и линию col1 => решаемость по
    ;      построению сохранена (путь яйцо->замок->дверь идёт шагом по row9).
    ;      Стартовая колонка <=8 и длина <=6 => правый край <=13 (interior).
    CALL func_prng
    ANI 01h
    ADI 01h                             ; число платформ 1..2
    STA rgl_off
rgl_plat:
    LXI D, rgl_prow8                    ; #3: row8 (запрыгиваемая с земли)
    CALL rgl_rndpick
    STA rgl_row
    LXI D, rgl_pcol8                    ; стартовая колонка (<=8)
    CALL rgl_rndpick
    STA rgl_col
    CALL func_prng
    ANI 03h
    ADI 03h                             ; длина 3..6 (rgl_len, НЕ rgl_run — тот хранит B)
    STA rgl_len
rgl_plat_fill:
    MVI A, 02h                          ; тайл стена
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    LDA rgl_col
    INR A
    STA rgl_col                         ; шаг вправо
    LDA rgl_len
    DCR A
    STA rgl_len
    JNZ rgl_plat_fill
    LDA rgl_off
    DCR A
    STA rgl_off
    JNZ rgl_plat

    ; ---- ФРУКТЫ: 3 клетки на коридоре row9 (проходимый декор/+очки) ----
    MVI A, 03h
    STA rgl_off
rgl_frt:
    LXI D, rgl_col8
    CALL rgl_rndpick                    ; col 4..14
    STA rgl_col
    MVI A, 09h
    STA rgl_row
    LXI D, rgl_frt8                     ; тайл 0x0A..0x0D
    CALL rgl_rndpick
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    LDA rgl_off
    DCR A
    STA rgl_off
    JNZ rgl_frt

    ; ---- КЛЮЧИ (яйцо 0x07) на row9, ровно B РАЗНЫХ колонок ----
    ; Коллизия двух независимых rndpick(rgl_col8) давала 1 яйцо при пороге B=2
    ; (уровни 10..15) => var_egg_seq не доходил до B => уровень нерешаем.
    ; Ловит validate_random.py (--sweep). Лечим сдвигом на заведомо свободную
    ; колонку (4<->6): клетка (9,col)==0x07 только если там уже лежит яйцо.
    ; Число вызовов func_prng не меняется (B штук) => поток врагов/двери и
    ; уровни 2..9 (B=1) не затронуты.
    LDA rgl_run
    STA rgl_off
rgl_egg:
    LXI D, rgl_col8
    CALL rgl_rndpick
    STA rgl_col
    MVI A, 09h
    STA rgl_row
    LHLD rgl_mapbase
    CALL rgl_getcell                    ; A = map(9,col)
    CPI 07h
    JNZ rgl_egg_place                   ; клетка свободна от яйца — кладём
    LDA rgl_col                         ; коллизия: увести на 4<->6
    CPI 04h
    JNZ rgl_egg_to4
    MVI A, 06h
    JMP rgl_egg_setc
rgl_egg_to4:
    MVI A, 04h
rgl_egg_setc:
    STA rgl_col
rgl_egg_place:
    MVI A, 07h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    LDA rgl_off
    DCR A
    STA rgl_off
    JNZ rgl_egg

    ; ---- МЕБЕЛЬ (выход + коробка + ЗАМКИ) по базовому индексу --------------
    ; Замок ОДНОРАЗОВЫЙ: после депозита func_game_update_handlers(loc_106B)
    ;   перезаписывает его глифы на 0x7B/0x7C, а проверка депозита требует
    ;   TL==0x79 => повторно сдать в тот же замок нельзя. Значит для B=2
    ;   (lv>=10) нужно ДВА замка на РАЗНЫХ колонках.
    ; Выход НЕ должен стоять прямо над замком: игрок, сдав последнее яйцо на
    ;   замке (row9 над замком row10), уже стоит на клетке двери => мгновенная
    ;   победа. Поэтому колонка выхода обязана отличаться от колонок замков.
    ; Индексы rgl_col8 (все 8 значений различны):
    ;   выход = base; коробка = (base+6)&7; замки = (base+loff)&7, (base+loff+1)&7.
    ;   loff in 1..4 => ни один индекс замка/коробки не равен base и все различны
    ;   mod 8 => колонки попарно различны (дверь не над замком, коробка не под замком).
    CALL func_prng
    ANI 07h
    STA rgl_fbase                       ; base 0..7
    CALL func_prng
    ANI 03h
    ADI 01h                             ; loff = 1..4
    STA rgl_loff

    ; --- выход: charX = 2*col8[base] (в desc[0] запишем в конце цикла) ---
    LDA rgl_fbase
    CALL rgl_c8
    RLC
    STA rgl_doorx

    ; --- скрытая коробка (тайл 5) в полу row10: col8[(base+6)&7] ---
    LDA rgl_fbase
    ADI 06h
    ANI 07h
    CALL rgl_c8
    STA rgl_col
    MVI A, 0Ah
    STA rgl_row
    MVI A, 05h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell

    ; --- замок-1 (тайл 8) row10: col8[(base+loff)&7] ---
    LDA rgl_fbase
    MOV C, A
    LDA rgl_loff
    ADD C
    ANI 07h
    CALL rgl_c8
    STA rgl_col
    MVI A, 0Ah
    STA rgl_row
    MVI A, 08h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell

    ; --- замок-2 (только B=2): col8[(base+loff+1)&7] ---
    LDA rgl_run
    CPI 02h
    JNZ rgl_have_furn
    LDA rgl_fbase
    MOV C, A
    LDA rgl_loff
    INR A
    ADD C
    ANI 07h
    CALL rgl_c8
    STA rgl_col
    MVI A, 0Ah
    STA rgl_row
    MVI A, 08h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
rgl_have_furn:

    ; ==== ОГОНЬ (#4): два стиля, выбирается случайно разбором бита func_prng ====
    ;  Решаемость ПО ПОСТРОЕНИЮ сохранена (коридор row9 + опора row10 под
    ;  обязательным путём целы):
    ;   * стиль P (бит4=0): огонь СИДИТ НА кирпичной полке в air-области —
    ;     опора-кирпич (8,c) + боковые кирпичи (7,c-1),(7,c+1) + огонь (7,c).
    ;     Зеркалит ориг. PUTUP ур.5 (огонь на полке). Не трогает row9/row10.
    ;   * стиль B (бит4=1): «огонь на дне» в row10, НО только правее routeRight
    ;     (правой нужной маршруту колонки: дверь/яйца/замки) куда герой не
    ;     доходит => опора под путём НЕ нарушена. Кладём лишь на свободный пол
    ;     (клетка==0x02), не затирая замок/коробку. Нет места (routeRight>=13) ->
    ;     откат к стилю P.
    ;  Порядок func_prng-вызовов: 1 на разбор стиля/числа + 1 rndpick(rgl_ecol8)
    ;  на клетку (только стиль P). Поток ДРУГОЙ, чем до #4 -> кросс-чек перечитан.
    ; ========================================================================
rgl_fire_draw:
    CALL func_prng
    MOV C, A                            ; C = сырой байт
    ANI 03h
    ADI 02h                             ; 2..5 клеток
    STA rgl_fcount
    MOV A, C
    ANI 10h                             ; бит4 = выбор стиля
    ORA A
    JZ rgl_fire_plat                    ; 0 -> платформа

    ; ---- стиль B: огонь на дне правее маршрута ----
    CALL rgl_route_right                ; A = routeRight
    CPI 0Dh                             ; >=13 справа нет места (14 буфер,15 стена)
    JNC rgl_fire_plat                   ; -> откат к платформе
    INR A
    INR A                               ; стартовая колонка = routeRight+2
    STA rgl_fc
rgl_fb_lp:
    LDA rgl_fc
    CPI 0Fh                             ; col15 = правая стена периметра
    JNC rgl_fire_done                   ; дошли до края
    LDA rgl_fc
    STA rgl_col
    MVI A, 0Ah
    STA rgl_row
    LHLD rgl_mapbase
    CALL rgl_getcell
    CPI 02h                             ; только свободный пол-стена
    JNZ rgl_fb_next                     ; занято (замок/коробка) -> пропустить
    LDA rgl_fc
    STA rgl_col
    MVI A, 0Ah
    STA rgl_row
    MVI A, 06h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    LDA rgl_fcount
    DCR A
    STA rgl_fcount
    JZ rgl_fire_done
rgl_fb_next:
    LDA rgl_fc
    INR A
    STA rgl_fc
    JMP rgl_fb_lp

    ; ---- стиль P: огонь на кирпичной полке (row7 на опоре row8) ----
rgl_fire_plat:
    LDA rgl_fcount
    STA rgl_off                         ; счётчик клеток
rgl_fp_lp:
    LXI D, rgl_ecol8                    ; колонка 4..11
    CALL rgl_rndpick
    STA rgl_col                         ; c
    ; опора-кирпич (8,c)
    MVI A, 08h
    STA rgl_row
    MVI A, 02h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    ; левый кирпич (7,c-1)
    LDA rgl_col
    DCR A
    STA rgl_col                         ; col = c-1
    MVI A, 07h
    STA rgl_row
    MVI A, 02h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    ; огонь (7,c) = (c-1)+1
    LDA rgl_col
    INR A
    STA rgl_col                         ; col = c
    MVI A, 06h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    ; правый кирпич (7,c+1)
    LDA rgl_col
    INR A
    STA rgl_col                         ; col = c+1
    MVI A, 02h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    LDA rgl_off
    DCR A
    STA rgl_off
    JNZ rgl_fp_lp
rgl_fire_done:

    ; ==== ВРАГИ: тип из тех же 3 вызовов func_prng на слот ==================
    ;  b = func_prng;  type = b&3: 0/1 -> ходок(1/2), 2 -> ворона(3/4),
    ;                  3 -> вертолёт(5..8).  sub = (b>>2)&3:
    ;   ходок state = 1+(sub&1); ворона = 3+(sub&1); вертолёт = 5+(sub&3).
    ;  Позиция: row=rgl_erow8 (3..7), col=rgl_ecol8 (4..11) — тот же расход
    ;  func_prng, что и раньше (3 вызова/враг), поэтому ПОТОК НЕ СМЕЩАЕТСЯ.
    ;  Клетки: ходок — боковые (row,2),(row,13); ворона — (2,col),(8,col);
    ;  вертолёт — общей рамкой-ареной ПОСЛЕ обоих врагов (rgl_frame).
    ; ========================================================================
    XRA A
    STA rgl_frame                           ; сброс флага арены на этом уровне

    ; ---- ВРАГ-1 ----
    CALL func_prng
    STA rgl_b
    ANI 03h
    STA rgl_t
    LDA rgl_b
    ORA A                                   ; сброс переноса для лог. сдвига
    RAR
    RAR
    ANI 03h
    STA rgl_sub
    LDA rgl_t
    CPI 02h
    JC rgl_e1_walk                           ; type 0/1 -> ходок
    JZ rgl_e1_crow                           ; type 2    -> ворона
    MVI A, 01h
    STA rgl_frame                            ; type 3 -> вертолёт: нужна арена
    LDA rgl_sub
    ANI 03h
    ADI 05h
    JMP rgl_e1_setst
rgl_e1_crow:
    LDA rgl_sub
    ANI 01h
    ADI 03h
    JMP rgl_e1_setst
rgl_e1_walk:
    LDA rgl_sub
    ANI 01h
    ADI 01h
rgl_e1_setst:
    STA rgl_s1
    LXI D, rgl_erow8
    CALL rgl_rndpick
    STA rgl_row
    RLC
    STA rgl_y1
    LXI D, rgl_ecol8
    CALL rgl_rndpick
    STA rgl_col
    RLC
    STA rgl_x1
    MVI A, 03h
    STA rgl_tmp
    LDA rgl_t
    CPI 02h
    JZ rgl_e1_crow_cage
    CPI 03h
    JZ rgl_e1_cage_done                      ; вертолёт: рамка позже
    MVI A, 02h
    STA rgl_col
    LHLD rgl_mapbase
    CALL rgl_setcell                         ; (row,2)=03
    MVI A, 0Dh
    STA rgl_col
    LHLD rgl_mapbase
    CALL rgl_setcell                         ; (row,13)=03
    JMP rgl_e1_cage_done
rgl_e1_crow_cage:
    MVI A, 02h
    STA rgl_row
    LHLD rgl_mapbase
    CALL rgl_setcell                         ; (2,col)=03
    MVI A, 08h
    STA rgl_row
    LHLD rgl_mapbase
    CALL rgl_setcell                         ; (8,col)=03
rgl_e1_cage_done:

    ; ---- ВРАГ-2 ----
    CALL func_prng
    STA rgl_b
    ANI 03h
    STA rgl_t
    LDA rgl_b
    ORA A
    RAR
    RAR
    ANI 03h
    STA rgl_sub
    LDA rgl_t
    CPI 02h
    JC rgl_e2_walk
    JZ rgl_e2_crow
    MVI A, 01h
    STA rgl_frame
    LDA rgl_sub
    ANI 03h
    ADI 05h
    JMP rgl_e2_setst
rgl_e2_crow:
    LDA rgl_sub
    ANI 01h
    ADI 03h
    JMP rgl_e2_setst
rgl_e2_walk:
    LDA rgl_sub
    ANI 01h
    ADI 01h
rgl_e2_setst:
    STA rgl_s2
    LXI D, rgl_erow8
    CALL rgl_rndpick
    STA rgl_row
    RLC
    STA rgl_y2
    ; ---- #1: не сливать двух врагов в одном air-ряду (3<->5). PRNG не тратим.
    LDA rgl_y2
    MOV C, A
    LDA rgl_y1
    SUB C
    JNZ rgl_e2_lane_ok
    LDA rgl_row
    CPI 03h
    JNZ rgl_e2_to3
    MVI A, 05h
    JMP rgl_e2_setlane
rgl_e2_to3:
    MVI A, 03h
rgl_e2_setlane:
    STA rgl_row
    RLC
    STA rgl_y2
rgl_e2_lane_ok:
    LXI D, rgl_ecol8
    CALL rgl_rndpick
    STA rgl_col
    RLC
    STA rgl_x2
    MVI A, 03h
    STA rgl_tmp
    LDA rgl_t
    CPI 02h
    JZ rgl_e2_crow_cage
    CPI 03h
    JZ rgl_e2_cage_done
    MVI A, 02h
    STA rgl_col
    LHLD rgl_mapbase
    CALL rgl_setcell
    MVI A, 0Dh
    STA rgl_col
    LHLD rgl_mapbase
    CALL rgl_setcell
    JMP rgl_e2_cage_done
rgl_e2_crow_cage:
    MVI A, 02h
    STA rgl_row
    LHLD rgl_mapbase
    CALL rgl_setcell
    MVI A, 08h
    STA rgl_row
    LHLD rgl_mapbase
    CALL rgl_setcell
rgl_e2_cage_done:

    ; ---- РАМКА-АРЕНА для вертолётов (если rgl_frame) -----------------------
    ;  Невидимые отражатели по периметру air-области: row2 и row8 (cols2..13),
    ;  col2 и col13 (rows2..8). Замкнутый контур держит 2D-преследователя в
    ;  rows3..7/cols3..12 => он НЕ сойдёт на коридор row9 (выигрышный путь)
    ;  и не доберётся до col1 (линия падения героя). Герою проходимо (0x60).
    LDA rgl_frame
    ORA A
    JZ rgl_no_frame
    MVI A, 03h
    STA rgl_tmp
    MVI A, 02h
    STA rgl_row
    CALL rgl_frame_row                        ; row2, cols2..13
    MVI A, 08h
    STA rgl_row
    CALL rgl_frame_row                        ; row8, cols2..13
    MVI A, 02h
    STA rgl_col
    CALL rgl_frame_col                        ; col2, rows2..8
    MVI A, 0Dh
    STA rgl_col
    CALL rgl_frame_col                        ; col13, rows2..8
rgl_no_frame:

    ; ---- ВЫХОД (дверь): charX из rgl_doorx (=2*col8[base]), charY=18 (row9) ----
    ;      Колонка выхода уже гарантированно отличается от колонок замков (см.
    ;      МЕБЕЛЬ выше), поэтому дверь никогда не встанет прямо над замком.
    LHLD rgl_descbase
    LDA rgl_doorx
    MOV M, A                            ; [0]=X выхода
    INX H
    MVI M, 12h                          ; [1]=Y выхода = 18 (row9)
    INX H
    LDA rgl_s1
    MOV M, A                            ; [2]=state1
    INX H
    LDA rgl_x1
    MOV M, A                            ; [3]=X1
    INX H
    LDA rgl_y1
    MOV M, A                            ; [4]=Y1
    INX H
    LDA rgl_s2
    MOV M, A                            ; [5]=state2
    INX H
    LDA rgl_x2
    MOV M, A                            ; [6]=X2
    INX H
    LDA rgl_y2
    MOV M, A                            ; [7]=Y2

    ; ---- сдвиг баз, номер уровня, внешний счётчик ----
    LHLD rgl_mapbase
    LXI D, 176
    DAD D
    SHLD rgl_mapbase
    LHLD rgl_descbase
    LXI D, 008h
    DAD D
    SHLD rgl_descbase
    LDA rgl_level
    INR A
    STA rgl_level
    LDA rgl_cnt
    DCR A
    STA rgl_cnt
    JNZ rgl_gen

    ; ---------------------------------------------------------------------
    ; 3) КУРАТОРСКИЙ уровень 1 (референс играбельности). Поверх каркаса
    ;    кладём СПРОЕКТИРОВАННУЮ карту и описатель уровня 1:
    ;      * герой (char 1,2) падает на пол row9 и идёт ВПРАВО по одному ряду
    ;        (прыжки НЕ нужны): КЛЮЧ (0x07) на (9,3);
    ;      * ЗАМОК (0x08) в полу row10 на col6 — герой стоит НАД ним и по
    ;        DOWN (func_player_move_d/loc_106B) вставляет яйцо → var_egg_seq++;
    ;      * var_egg_seq==B=1 (lv1) → из описателя открывается ВЫХОД (дверь)
    ;        на клетке (9,10) — тот же ряд пола, достижим шагом вправо;
    ;      * ОГОНЬ (0x06) — полоса в воздухе (row5, cols5..10) как элемент
    ;        сложности (ALGORITHM.MD §6: смертелен лишь при входе ВНУТРЬ клетки
    ;        в фазе 0x75; фаза 0xFE отталкивает); ФРУКТЫ (0x0A/0x0B) на (9,13/14);
    ;      * 2 ВРАГА state 1 патрулируют воздух (col5, rows 3 и 6).
    ;    176 Б rgl_map1 -> data_level_maps (карта уровня 1).
    ; ---------------------------------------------------------------------
    LXI H, rgl_map1
    LXI D, data_level_maps
    MVI B, 176
rgl_cp_map1:
    MOV A, M
    STAX D
    INX H
    INX D
    DCR B
    JNZ rgl_cp_map1
    ;    8 Б rgl_desc1 -> data_level_params+8 (запись уровня 1).
    LXI H, rgl_desc1
    LXI D, data_level_params+8
    MVI B, 8
rgl_cp_desc1:
    MOV A, M
    STAX D
    INX H
    INX D
    DCR B
    JNZ rgl_cp_desc1
    RET                                 ; ← выход из генератора (не проваливаемся в хелперы)

; ============================================================================
; Хелперы генератора (вызываются только по CALL; доступ через RET выше).
; ============================================================================

; rgl_rndpick: DE = адрес 8-байтной таблицы → A = table[func_prng & 7].
;   Clobbers: A,H,L (D,E восстановлены func_prng + POP D). B,C сохранены (PUSH/POP B).
rgl_rndpick:
    PUSH B
    PUSH D
    CALL func_prng                      ; A = псевдослучайный байт
    ANI 07h
    MOV L, A
    MVI H, 000h
    POP D                               ; DE = база таблицы
    DAD D                               ; HL = таблица + индекс
    MOV A, M
    POP B
    RET

; rgl_setcell: HL = база КАРТЫ уровня; пишет rgl_tmp в (mapbase + rgl_row*16 + rgl_col).
;   Clobbers: A,B,C,D,E,H,L. Не трогает RAM-состояние цикла (rgl_off/..).
rgl_setcell:
    LDA rgl_row
    RLC
    RLC
    RLC
    RLC                                 ; A = row*16 (row<=10 → <256)
    MOV C, A
    MVI B, 000h
    LDA rgl_col
    ADD C
    MOV C, A                            ; BC = row*16 + col (<256)
    DAD B                               ; HL = &клетки
    LDA rgl_tmp
    MOV M, A
    RET

; rgl_getcell: HL = база КАРТЫ уровня; A = map(rgl_row*16 + rgl_col).
;   Зеркало rgl_setcell без записи. Clobbers: A,B,C,H,L.
rgl_getcell:
    LDA rgl_row
    RLC
    RLC
    RLC
    RLC                                 ; A = row*16
    MOV C, A
    MVI B, 000h
    LDA rgl_col
    ADD C
    MOV C, A                            ; BC = row*16 + col
    DAD B                               ; HL = &клетки
    MOV A, M
    RET

; rgl_c8: A = индекс 0..7 -> A = rgl_col8[A]. Без func_prng (т.е. не тратит поток).
;   Clobbers: A,H,L,D,B (сохранены PUSH). Used для раскладки мебели по индексам.
rgl_c8:
    PUSH B
    PUSH D
    MOV L, A
    MVI H, 000h
    LXI D, rgl_col8
    DAD D
    MOV A, M
    POP D
    POP B
    RET

; rgl_route_right: #4 — A = правая колонка, обязательная выигрышному маршруту
;   (максимум из doorcol и самой правой клетки row9/row10 с яйцом 0x07 или
;   замком 0x08). Фрукты/коробка — опциональны, не учитываются. Возвращает A.
;   Clobbers: A,B,C,H,L (сохраняет D через rgl_getcell не нужен; B,C scratch).
rgl_route_right:
    LDA rgl_doorx                       ; char-X выхода = 2*doorcol
    ORA A                                ; сброс CY для чистого сдвига
    RAR                                  ; A = doorcol
    STA rgl_rmax                         ; старт: routeRight = doorcol
    MVI A, 0Eh                           ; скан col 14..2 (справа налево)
    STA rgl_fc
rrc_col:
    LDA rgl_fc
    CPI 02h
    JC rrc_none                          ; дошли до col<2 — яйца/замка справа нет
    STA rgl_col
    MVI A, 09h
    STA rgl_row
    LHLD rgl_mapbase
    CALL rgl_getcell                     ; (9,col)
    CPI 07h
    JZ rrc_found
    CPI 08h
    JZ rrc_found
    MVI A, 0Ah
    STA rgl_row
    LHLD rgl_mapbase
    CALL rgl_getcell                     ; (10,col)
    CPI 07h
    JZ rrc_found
    CPI 08h
    JZ rrc_found
    LDA rgl_fc
    DCR A
    STA rgl_fc
    JMP rrc_col
rrc_found:
    LDA rgl_fc                           ; A = колонка правого яйца/замка
    MOV C, A                             ; C = candidate
    LDA rgl_rmax                         ; A = doorcol
    SUB C                                ; CY если doorcol < candidate
    JC rrc_take                          ; doorcol < candidate -> брать candidate
    LDA rgl_rmax                         ; иначе вернуть doorcol
    RET
rrc_take:
    MOV A, C
    RET
rrc_none:
    LDA rgl_rmax                         ; только doorcol (яйца/замка справа нет)
    RET

; rgl_frame_row: пишет rgl_tmp в (rgl_row, 2..13). Счётчик — rgl_off (свободен
;   на этапе рамки). #3: НЕ перекрашивает уже твёрдую стену-платформу (0x02) в
;   отражатель — wall row8 сам служит полом арены (solid => вертолёт не проходит),
;   и остаётся запрыгиваемым для героя. Clobbers A,B,C,H,L (через rgl_getcell/setcell).
rgl_frame_row:
    MVI A, 0Ch
    STA rgl_off
    MVI A, 02h
    STA rgl_col
rgl_frlp:
    LHLD rgl_mapbase
    CALL rgl_getcell                    ; A = текущая клетка
    CPI 02h
    JZ rgl_frlp_next                    ; стена-платформа — оставить как есть
    LHLD rgl_mapbase
    CALL rgl_setcell                    ; иначе — отражатель арены
rgl_frlp_next:
    LDA rgl_col
    INR A
    STA rgl_col
    LDA rgl_off
    DCR A
    STA rgl_off
    JNZ rgl_frlp
    RET

; rgl_frame_col: пишет rgl_tmp в (2..8, rgl_col). См. rgl_frame_row (тот же skip 0x02).
rgl_frame_col:
    MVI A, 07h
    STA rgl_off
    MVI A, 02h
    STA rgl_row
rgl_fclp:
    LHLD rgl_mapbase
    CALL rgl_getcell
    CPI 02h
    JZ rgl_fclp_next
    LHLD rgl_mapbase
    CALL rgl_setcell
rgl_fclp_next:
    LDA rgl_row
    INR A
    STA rgl_row
    LDA rgl_off
    DCR A
    STA rgl_off
    JNZ rgl_fclp
    RET

; --- 8-байтные таблицы случайного выбора (индекс = func_prng & 7) -----------
rgl_col8:  DEFB 04h, 06h, 08h, 0Ah, 0Ch, 0Eh, 05h, 09h   ; колонки предметов/выхода (4..14)
rgl_ecol8: DEFB 04h, 05h, 06h, 07h, 08h, 09h, 0Ah, 0Bh   ; колонки огня/врагов (4..11)
rgl_erow8: DEFB 03h, 04h, 05h, 06h, 07h, 05h, 03h, 06h   ; air-ряды врагов (3..7); огонь (#4) больше не использует
rgl_frt8:  DEFB 0Ah, 0Bh, 0Ch, 0Dh, 0Bh, 0Ch, 0Dh, 0Ah   ; тайлы фруктов (10..13)
rgl_pcol8: DEFB 03h, 04h, 05h, 06h, 07h, 08h, 04h, 06h   ; стартовые колонки платформ (<=8)
rgl_prow8: DEFB 08h, 08h, 08h, 08h, 08h, 08h, 08h, 06h   ; #3: ряд платформ (row8 = запрыг. с земли; row6 = верхняя полка-ступенька)

; ============================================================================
; КУРАТОРСКИЕ данные уровня 1.
;   Карта 1: #=стена 02, .=пол 01, ~=огонь 06, K=ключ 07, L=замок 08, o/p=фрукт 0A/0B.
;   Описатель: выход(X=14h=col10,Y=12h=row9); ent1(1,X=0Ah=col5,Y=06h=row3);
;              ent2(1,X=0Ah=col5,Y=0Ch=row6).
; ============================================================================
rgl_map1:
    DEFB 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h   ; ряд 0  (потолок)
    DEFB 02h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 02h   ; ряд 1
    DEFB 02h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 02h   ; ряд 2
    DEFB 02h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 02h   ; ряд 3
    DEFB 02h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 02h   ; ряд 4
    DEFB 02h, 01h, 01h, 01h, 01h, 06h, 06h, 06h, 06h, 06h, 06h, 01h, 01h, 01h, 01h, 02h   ; ряд 5  (огонь в воздухе)
    DEFB 02h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 02h   ; ряд 6
    DEFB 02h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 02h   ; ряд 7
    DEFB 02h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 02h   ; ряд 8
    DEFB 02h, 01h, 01h, 07h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h, 0Ah, 0Bh, 02h   ; ряд 9  (K@col3; дверь@col10; плоды@col13,14)
    DEFB 02h, 02h, 02h, 02h, 02h, 02h, 08h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h   ; ряд 10 (пол-стена; L=замок@col6)

rgl_desc1:
    DEFB 014h, 012h, 001h, 00Ah, 006h, 001h, 00Ah, 00Ch
