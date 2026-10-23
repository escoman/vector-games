; Функция: func_entity_state10
; Адрес: 0x191B
; Размер: 97 байт
; Описание: Обработчик сущности в состоянии 10 — погонщик HURRY-UP (slot 1,
;           state==09h). Вывод на экран перенесён в общий easing-лифтник
;           func_enemy_render_slot (плавное догоняние + маска вместо немедленного
;           блита с EI;HLT). Здесь остаётся ТОЛЬКО коллизия-чек: вычисление
;           |dx|,|dy| между var_player_col/var_player_row и сущностью
;           (0920h/0923h); если обе разности >= 2 -> RNC (возврат), иначе
;           JMP func_collision_death. Рёбра CPI 17h / JNC loc_1958 сохранены: пока
;           погонщик ещё не спавнился на поле (ycoords>=17h), коллизия сама не
;           срабатывает по |dy|. Вспомогательная loc_1979: A = -A (CMA/INR A).

func_entity_state10:
    ; Погонщик (state==09h, slot 1): ветки erase/немедленного блита УБРАНЫ — теперь
    ; его рисует общий easing-лифтник func_enemy_render_slot (симметричный вертикаль-
    ; ный midpoint + диагональ, hoff через 3-колоночное предсдвинутое окно).var_egg_rc
    ; больше не пишется: потребитель переведён на var_enemy_disp_rc[1]. Остаётся
    ; только коллизия-чек ниже. Инвариант newr<18h в renderer не выпустит спрайт за
    ; поле, поэтому немедленная отрисовка не нужна и при ycoords[1]>=17h.
    LDA data_entity_ycoords+01h
    CPI 17h
    JNC loc_1958                ; сущность ещё не спавнилась на поле -> только коллизия
loc_1958:
    LDA data_entity_xcoords+01h                    ; 0x1958
    MOV B, A                    ; 0x195B
    LDA var_player_col          ; 0x195C
    SUB B                       ; 0x195F
    CC loc_1979                 ; 0x1960
    MOV D, A                    ; 0x1963
    LDA data_entity_ycoords+01h                    ; 0x1964
    MOV B, A                    ; 0x1967
    LDA var_player_row          ; 0x1968
    SUB B                       ; 0x196B
    CC loc_1979                 ; 0x196C
    CPI 02h                     ; 0x196F
    RNC                         ; 0x1971
    MOV A, D                    ; 0x1972
    CPI 02h                     ; 0x1973
    RNC                         ; 0x1975
    JMP func_collision_death                    ; 0x1976
loc_1979:
    CMA                         ; 0x1979
    INR A                       ; 0x197A
    RET                         ; 0x197B
