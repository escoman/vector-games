; Функция: func_game_update
; Адрес: 0x0CE0
; Размер: 421 байт (0x0CE0-0x0E84, непрерывное тело)
; Описание: Кадровое обновление игры (управление/движение/коллизии игрока).
;           Вызывается из lbl_main_game_loop (0x0ED6). XRA A; CALL
;           func_check_start_key; если нажата клавиша: LDA var_game_state,
;           ==1 -> JZ 12B3h, ==2 -> JZ 12F6h (обработчики вне тела, в gap-зоне).
;           Обычный путь loc_0CF5: var_player_row++ (INR M); E=row; D=var_player_col;
;           CALL func_coords_to_textbuf; SHLD var_player_bufaddr. Сканирование
;           коллизий: var_collision_flag=0; HL+=0020h (ячейка ниже); 2x [MOV A,M;
;           CPI 76h('v'); JC/JZ skip; CMA; STA var_collision_flag]. При коллизии:
;           var_player_row--; var_game_state=1; 0906h=0. Далее CALL func_decode_key;
;           диспетчер кода клавиши: 1,2->loc_0D68; 3,4->0FD4h; 5->1042h; 6,7->1017h
;           (внешние gap-обработчики). loc_0D68: var_work_const=3; 0909h=col;
;           090Ah=row; 090Ch=tile; erase пред.позиции 08E3h через
;           func_draw_tile_at_ptr (EI;HLT синк) + СРАЗУ draw героя func_render_tile_vram_or (OR-композит: пустые пиксели героя не затирают фрукт/фон под ним)
;           (пара в одном окне гашения — инвариант flicker-free, как у врагов);
;           SHLD 08E3h=новая поз.; ШАГ 0: скан буфера 0300h (огонь 75h<->0FEh)
;           ВЫНЕСЕН в func_render_all (по 128 ячеек каждый кадр); здесь остаются
;           мигание выхода (var_exit_phase 0<->1, безусловная перерисовка
;           [7]/[10]) и ПОВТОРНАЯ дорисовка героя (loc_exit_hero) — поверх выхода.
;           Затем второй проход коллизий по 't'(74h); при nonzero -> JNZ 13Ah (gap).
;           Обновление 08E9h, CALL func_erase_char_08E9, проверка 08EAh==2 -> 1252h.
;           Финал: char ниже игрока; если <6Eh -> RC; иначе CALL func_sound_init и
;           диспетчер (A-6Dh): 1..4 -> func_score_and_redraw; 5->0F39h; 6->0F63h;
;           7->0F6Dh (gap-обработчики). Fall-through в lbl_main_game_loop.
;           Примечание: ветви на 0FD4h/1017h/1042h/12B3h/12F6h/13AAh/1252h/
;           0F39h/0F63h/0F6Dh ведут в gap-зоны (не объекты RDB) — оставлены как hex.

func_game_update:
    XRA A                       ; 0x0CE0
    CALL func_check_start_key   ; 0x0CE1
    ORA A                       ; 0x0CE4
    JZ loc_0CF5                 ; 0x0CE5
    LDA var_game_state          ; 0x0CE8
    CPI 01h                     ; 0x0CEB
    JZ func_gamestate_catch         ; 0x0CED
    CPI 02h                     ; 0x0CF0
    JZ func_gamestate_evade         ; 0x0CF2
loc_0CF5:
    LXI H, var_player_row       ; 0x0CF5
    INR M                       ; 0x0CF8
    MOV E, M                    ; 0x0CF9
    LDA var_player_col          ; 0x0CFA
    MOV D, A                    ; 0x0CFD
    CALL func_coords_to_textbuf ; 0x0CFE
    SHLD var_player_bufaddr     ; 0x0D01
    XRA A                       ; 0x0D04
    STA var_collision_flag      ; 0x0D05
    LXI B, 0020h                ; 0x0D08
    DAD B                       ; 0x0D0B
    MOV A, M                    ; 0x0D0C
    CPI 76h                     ; 0x0D0D
    JC loc_0D19                 ; 0x0D0F
    JZ loc_0D19                 ; 0x0D12
    CMA                         ; 0x0D15
    STA var_collision_flag      ; 0x0D16
loc_0D19:
    INX H                       ; 0x0D19
    MOV A, M                    ; 0x0D1A
    CPI 76h                     ; 0x0D1B
    JC loc_0D27                 ; 0x0D1D
    JZ loc_0D27                 ; 0x0D20
    CMA                         ; 0x0D23
    STA var_collision_flag      ; 0x0D24
loc_0D27:
    LDA var_collision_flag      ; 0x0D27
    ORA A                       ; 0x0D2A
    JZ loc_0D3E                 ; 0x0D2B
    LXI H, var_player_row       ; 0x0D2E
    DCR M                       ; 0x0D31
    MVI A, 01h                  ; 0x0D32
    STA var_game_state          ; 0x0D34
    XRA A                       ; 0x0D37
    STA var_scr_0906                    ; 0x0D38
    JMP loc_0D41                ; 0x0D3B
loc_0D3E:
    STA var_game_state          ; 0x0D3E
loc_0D41:
    XRA A                       ; 0x0D41
    CALL func_decode_key        ; 0x0D42
    CPI 01h                     ; 0x0D45
    JZ loc_0D68                 ; 0x0D47
    CPI 02h                     ; 0x0D4A
    JZ loc_0D68                 ; 0x0D4C
    CPI 03h                     ; 0x0D4F
    JZ func_player_move_b        ; 0x0D51
    CPI 04h                     ; 0x0D54
    JZ func_player_move_b        ; 0x0D56
    CPI 05h                     ; 0x0D59
    JZ func_player_move_d        ; 0x0D5B
    CPI 06h                     ; 0x0D5E
    JZ func_player_move_c        ; 0x0D60
    CPI 07h                     ; 0x0D63
    JZ func_player_move_c        ; 0x0D65
loc_0D68:
    MVI A, 03h                  ; 0x0D68
    STA var_work_const          ; 0x0D6A
loc_0D6D:
    LDA var_player_col          ; 0x0D6D
    STA var_scr_0909                    ; 0x0D70
    LDA var_player_row          ; 0x0D73
    STA var_scr_090A                    ; 0x0D76
    LDA var_move_dir                    ; 0x0D79
    MOV B, A                    ; 0x0D7C
    RLC                         ; 0x0D7D
    ADD B                       ; 0x0D7E
    MOV B, A                    ; 0x0D7F
    LDA var_work_const          ; 0x0D80
    ADD B                       ; 0x0D83
    DCR A                       ; 0x0D84
    STA var_obj_type_idx                    ; 0x0D85
    ; --- Step 2a (Вариант A): erase+snap+draw героя ВЫНЕСЕН из game_update -----
    ;     сюда больше не лезут var_enemy_rc (кэш отображения) и var_glyph_voff:
    ;     плавный твин и сама отрисовка героя — в func_hero_render (главный цикл,
    ;     каждый кадр). Здесь только выставлен ЦЕЛЬ var_scr_090A/0909 (выше) и
    ;     вычислен var_obj_type_idx — их читает func_hero_render и loc_exit_hero.
    ; --- Step 0: скан огня (loc_0DBE..loc_0DD6) вынесен в func_render_all,
    ;     теперь он идёт по 128 ячеек каждый кадр из главного цикла. Здесь
    ;     остаётся только мигание выхода и повторная дорисовка героя. ------
    ; --- Фаза 4: мигание выхода 6<->5 в том же темпе, что огонь выше ----------
    ; Появляется вместе с выходом (ветка 0x10C8 handlers), гаснет в func_level_loader.
    LDA var_exit_phase          ; 0FFh = выход не активен
    CPI 0FFh
    JZ loc_exit_done            ; выхода нет: ни мигания, ни дорисовки героя
    INR A
    ANI 01h                     ; фаза: 0=светлый(нарисован), 1=тёмный
    STA var_exit_phase
    MOV B, A
    LHLD var_exit_rc            ; lo=строка, hi=колонка (кэш из loc_10FD)
    XCHG                        ; DE=позиция — как в вызовах отрисовки выхода
    LXI H, data_tile_table_26DE+01Ch   ; [7] = светлый выход (глифы BC..BF)
    MOV A, B
    ORA A
    JZ loc_exit_draw
    LXI H, data_tile_table_26DE+028h   ; [10] = тёмный выход (глифы 12..15)
loc_exit_draw:
    CALL func_render_tile_vram
loc_exit_hero:
    ; --- герой поверх огня и мигания выхода: ПОВТОРНАЯ дорисовка --------------
    ; Step 2a (Вариант A): рисуем героя в его ТЕКУЩЕЙ отображаемой позиции
    ; (var_enemy_rc + var_glyph_voff), а не в целевой var_player_row/col — иначе
    ; мигание выхода сорвало бы твин. func_render_tile_vram_or сам применит
    ; var_glyph_voff (суб-сдвиг). Идемпотентно: кладёт героя поверх тайла выхода.
    CALL func_raster_guard_hero ; raster-sync: повторная дорисовка тоже вне прохода луча
    LDA var_enemy_rc            ; ОТОБРАЖАЕМая строка героя (твин-cr, lo слова)
    MOV L, A
    LDA var_enemy_rc+1          ; ОТОБРАЖАЕМая колонка героя (hi слова)
    MOV H, A
    XCHG                        ; DE = (D=col, E=row) — позиция для render
    LDA var_obj_type_idx        ; тайл героя (из loc_0D85; скан/мигание его не меняют)
    ADD A
    ADD A
    LXI H, data_tile_table_26DE
    CALL func_hl_add_a
    CALL func_render_tile_vram_or  ; герой OR-композитом поверх огня/мигания выхода (не затирает то, под чем стоит)
loc_exit_done:
    LDA var_player_col          ; 0x0DDD
    MOV D, A                    ; 0x0DE0
    LDA var_player_row          ; 0x0DE1
    MOV E, A                    ; 0x0DE4
    CALL func_coords_to_textbuf ; 0x0DE5
    SHLD var_player_bufaddr     ; 0x0DE8
    XRA A                       ; 0x0DEB
    STA var_collision_flag      ; 0x0DEC
    MOV A, M                    ; 0x0DEF
    CPI 74h                     ; 0x0DF0
    JC loc_0DFC                 ; 0x0DF2
    JZ loc_0DFC                 ; 0x0DF5
    CMA                         ; 0x0DF8
    STA var_collision_flag      ; 0x0DF9
loc_0DFC:
    INX H                       ; 0x0DFC
    MOV A, M                    ; 0x0DFD
    CPI 74h                     ; 0x0DFE
    JC loc_0E0A                 ; 0x0E00
    JZ loc_0E0A                 ; 0x0E03
    CMA                         ; 0x0E06
    STA var_collision_flag      ; 0x0E07
loc_0E0A:
    LXI B, 001Fh                ; 0x0E0A
    DAD B                       ; 0x0E0D
    MOV A, M                    ; 0x0E0E
    CPI 74h                     ; 0x0E0F
    JC loc_0E1B                 ; 0x0E11
    JZ loc_0E1B                 ; 0x0E14
    CMA                         ; 0x0E17
    STA var_collision_flag      ; 0x0E18
loc_0E1B:
    INX H                       ; 0x0E1B
    MOV A, M                    ; 0x0E1C
    CPI 74h                     ; 0x0E1D
    JC loc_0E29                 ; 0x0E1F
    JZ loc_0E29                 ; 0x0E22
    CMA                         ; 0x0E25
    STA var_collision_flag      ; 0x0E26
loc_0E29:
    LDA var_collision_flag      ; 0x0E29
    ORA A                       ; 0x0E2C
    JNZ func_collision_death        ; 0x0E2D
    LHLD var_blink_cell                   ; 0x0E30
    INX H                       ; 0x0E33
    SHLD var_blink_cell                   ; 0x0E34
    LDA var_blink_cell                    ; 0x0E37
    ANI 1Fh                     ; 0x0E3A
    JNZ loc_0E4A                ; 0x0E3C
    CALL func_erase_char_08E9   ; 0x0E3F
    LDA var_blink_type                    ; 0x0E42
    CPI 02h                     ; 0x0E45
    JZ func_egg_caught              ; 0x0E47
loc_0E4A:
    LHLD var_player_bufaddr     ; 0x0E4A
    LXI B, 0020h                ; 0x0E4D
    DAD B                       ; 0x0E50
    MOV A, M                    ; 0x0E51
    STA var_collision_flag      ; 0x0E52
    CPI 6Eh                     ; 0x0E55
    RC                          ; 0x0E57
    MVI B, 02h                  ; 0x0E58
    CALL func_sound_init        ; 0x0E5A
    LDA var_collision_flag      ; 0x0E5D
    SUI 6Dh                     ; 0x0E60
    CPI 01h                     ; 0x0E62
    JZ func_score_and_redraw    ; 0x0E64
    CPI 02h                     ; 0x0E67
    JZ func_score_and_redraw    ; 0x0E69
    CPI 03h                     ; 0x0E6C
    JZ func_score_and_redraw    ; 0x0E6E
    CPI 04h                     ; 0x0E71
    JZ func_score_and_redraw    ; 0x0E73
    CPI 05h                     ; 0x0E76
    JZ func_item_bonus_collect   ; 0x0E78
    CPI 06h                     ; 0x0E7B
    JZ func_item_bonus_timer     ; 0x0E7D
    CPI 07h                     ; 0x0E80
    JZ func_player_move_a        ; 0x0E82
    ; fall-through в lbl_main_game_loop (0x0E85)
