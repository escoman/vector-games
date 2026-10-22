; Функция: func_score_and_redraw
; Адрес: 0x0F09
; Размер: 48 байт
; Описание: Начисление очков за собранный предмет и перерисовка. A=var_collision_flag;
;           A-=6Dh (тип предмета); HL=08EDh+A (таблица стоимости предмета);
;           CALL func_hl_add_a; L=(HL); H=0; вычисляет DE=HL, HL=HL*8+DE (умножение
;           на 9); var_score += DE; CALL func_draw_score_hud (обновление HUD счёта);
;           затем D=var_player_col, E=var_player_row; HL=270Ah (тайл пустой клетки);
;           CALL func_draw_tile_to_buf (стереть предмет в текстовом буфере);
;           RET — выход в главный цикл (см. комментарий у loc_0F28 ниже).
;
; Точки входа: сюда прыгают из диспетчера предметов func_game_update по типу
; (char-6Dh) 1..4, а также func_item_bonus_collect -> loc_0F25 и
; func_item_bonus_timer -> loc_0F28, т.е. эпilog общий для всех сборов.

func_score_and_redraw:
    LDA var_collision_flag      ; 0x0F09
    SUI 6Dh                     ; 0x0F0C
    LXI H, var_item_cost_table   ; 0x0F0E
    CALL func_hl_add_a          ; 0x0F11
    MOV L, M                    ; 0x0F14
    MVI H, 00h                  ; 0x0F15
    DAD H                       ; 0x0F17
    MOV D, H                    ; 0x0F18
    MOV E, L                    ; 0x0F19
    DAD H                       ; 0x0F1A
    DAD H                       ; 0x0F1B
    DAD D                       ; 0x0F1C
    XCHG                        ; 0x0F1D
    LHLD var_score              ; 0x0F1E
    DAD D                       ; 0x0F21
    SHLD var_score              ; 0x0F22
loc_0F25:
    CALL func_draw_score_hud    ; 0x0F25
loc_0F28:
    LDA var_player_col          ; 0x0F28
    MOV D, A                    ; 0x0F2B
    LDA var_player_row          ; 0x0F2C
    MOV E, A                    ; 0x0F2F
    LXI H, data_tile_empty      ; 0x0F30
    CALL func_draw_tile_to_buf  ; 0x0F33
    ; ШАГ «убрать повторный проход кадра».
    ; В оригинале здесь был JMP func_game_update (0x0F36) — полный ПОВТОРНЫЙ вход
    ; в кадровое обновление внутри того же прохода. Он удваивает всё, что делает
    ; проход: гравитацию (INR var_player_row @0x0CF8), чтение клавиатуры
    ; (CALL func_decode_key @0x0D42 — декодер уровня, не по фронту, поэтому
    ; удерживаемое направление сдвигает героя ещё раз: func_player_move_b,
    ; INR var_player_col) и скан коллизий. Замер в эмуляторе: вход в сбор при
    ; var_frame_counter=32 и вход в func_game_update по этому JMP — тоже 32
    ; (один и тот же hw-кадр), следующий обычный проход — 38. То есть сбор
    ; предмета давал 2 шага логики в одном кадре вместо 1/6 кадра = ускорение
    ; героя ровно в момент сбора.
    ; Раньше это было незаметно, потому что тот же путь включал СИНХРОННЫЙ звук:
    ; блокирующий func_delay(2) внутри func_sound_init добавлял к итерации ~5
    ; кадров, и сбор стоил 2 шага / (6+5) кадров ~= обычный темп. После перехода
    ; на async-SFX простой исчез (звук справедливо ортогонален анимации), а его
    ; «компенсация» удвоенного прохода осталась здесь — поэтому JMP убран.
    ; RET, а не JMP: к этому моменту на стеке ровно один адрес, возвращённый
    ; CALL func_game_update из главного цикла (весь хвост game_update — JMP/JZ без
    ; вызовов), т.е. depth такая же, как на обычном выходе RC @0x0CD0. Возврат
    ; попадает на POP B @0x0EDE — штатное продолжение прохода (в т.ч. флип
    ; страниц на sub==12, которое при fall-through оригинального пути терялось).
    ; Побочный эффект (осознанный): перескан клетки под героем в том же кадре
    ; больше не делается — стоящие «стопкой» предметы собираются по одному за
    ; проход (разница ~6 кадров на каждый следующий), а не два в одном кадре.
    RET                         ; было JMP func_game_update (0x0F36)
