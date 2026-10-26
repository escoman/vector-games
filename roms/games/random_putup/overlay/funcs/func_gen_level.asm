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

    ; ---- ОГОНЬ: 2..5 клеток в воздухе (rows 3..7, cols 4..11) ----
    CALL func_prng
    ANI 03h
    ADI 02h                             ; 2..5
    STA rgl_off
rgl_fire:
    LXI D, rgl_erow8                    ; tile-row 3..7
    CALL rgl_rndpick
    STA rgl_row
    LXI D, rgl_ecol8                    ; tile-col 4..11
    CALL rgl_rndpick
    STA rgl_col
    MVI A, 06h                          ; тайл огонь
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    LDA rgl_off
    DCR A
    STA rgl_off
    JNZ rgl_fire

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

    ; ---- КЛЮЧИ (яйцо 0x07) на row9, ровно B штук ----
    LDA rgl_run
    STA rgl_off
rgl_egg:
    LXI D, rgl_col8
    CALL rgl_rndpick
    STA rgl_col
    MVI A, 09h
    STA rgl_row
    MVI A, 07h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell
    LDA rgl_off
    DCR A
    STA rgl_off
    JNZ rgl_egg

    ; ---- СКРЫТАЯ КОРОБКА (тайл 5) в полу row10 (1 шт) ----
    LXI D, rgl_col8
    CALL rgl_rndpick
    STA rgl_col
    MVI A, 0Ah
    STA rgl_row
    MVI A, 05h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell

    ; ---- ЗАМОК (тайл 8) в полу row10 — пишем ПОСЛЕДНИМ (власть над row10) ----
    LXI D, rgl_col8
    CALL rgl_rndpick
    STA rgl_col
    MVI A, 0Ah
    STA rgl_row
    MVI A, 08h
    STA rgl_tmp
    LHLD rgl_mapbase
    CALL rgl_setcell

    ; ---- ВРАГ-1: горизонтальный (state 1/2), air-row 3..7, col 4..11 + клетка ----
    CALL func_prng
    ANI 01h
    ADI 01h                             ; state = 1 или 2
    STA rgl_s1
    LXI D, rgl_erow8
    CALL rgl_rndpick
    STA rgl_row                         ; tile-row (нужен для клетки-отражателя)
    RLC
    STA rgl_y1                          ; char-Y = 2*row
    LXI D, rgl_ecol8
    CALL rgl_rndpick
    STA rgl_col
    RLC
    STA rgl_x1                          ; char-X = 2*col
    MVI A, 03h                          ; тайл-отражатель (невидимка для героя)
    STA rgl_tmp
    MVI A, 02h
    STA rgl_col                         ; левая граница клетки
    LHLD rgl_mapbase
    CALL rgl_setcell                    ; (row,2)=03
    MVI A, 0Dh
    STA rgl_col                         ; правая граница клетки
    LHLD rgl_mapbase
    CALL rgl_setcell                    ; (row,13)=03

    ; ---- ВРАГ-2: аналогично ----
    CALL func_prng
    ANI 01h
    ADI 01h
    STA rgl_s2
    LXI D, rgl_erow8
    CALL rgl_rndpick
    STA rgl_row
    RLC
    STA rgl_y2
    LXI D, rgl_ecol8
    CALL rgl_rndpick
    STA rgl_col
    RLC
    STA rgl_x2
    MVI A, 03h
    STA rgl_tmp
    MVI A, 02h
    STA rgl_col
    LHLD rgl_mapbase
    CALL rgl_setcell
    MVI A, 0Dh
    STA rgl_col
    LHLD rgl_mapbase
    CALL rgl_setcell

    ; ---- ВЫХОД (дверь): col из rgl_col8 на row9; charX=2*col, charY=18 ----
    LXI D, rgl_col8
    CALL rgl_rndpick
    RLC                                 ; charX = 2*col
    LHLD rgl_descbase
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

; --- 8-байтные таблицы случайного выбора (индекс = func_prng & 7) -----------
rgl_col8:  DEFB 04h, 06h, 08h, 0Ah, 0Ch, 0Eh, 05h, 09h   ; колонки предметов/выхода (4..14)
rgl_ecol8: DEFB 04h, 05h, 06h, 07h, 08h, 09h, 0Ah, 0Bh   ; колонки огня/врагов (4..11)
rgl_erow8: DEFB 03h, 04h, 05h, 06h, 07h, 05h, 03h, 06h   ; air-ряды огня/врагов (3..7)
rgl_frt8:  DEFB 0Ah, 0Bh, 0Ch, 0Dh, 0Bh, 0Ch, 0Dh, 0Ah   ; тайлы фруктов (10..13)

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
