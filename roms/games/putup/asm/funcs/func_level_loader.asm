; Функция: func_level_loader
; Адрес: 0x197C
; Размер: 523 байта
; Описание: Загрузка следующего уровня. var_level++; если var_level >= 10h
;           (16) -> ветка победы/бонуса (func_hall_of_fame). Иначе: обнуление 090Fh,
;           копирование 8 байт параметров уровня из data_level_params[level*8]
;           в data_level_param_buf (func_memcpy), сброс стека, очистка видео-ОЗУ
;           (func_clear_vram, шаг E3 — иначе пустые клетки хранят пиксели врага,
;           см. комментарий на loc_19A0), очистка
;           текстового буфера (func_clear_textbuf), вычисление указателя карты
;           уровня в data_level_maps (карта = 0B0h байт = 16x11 тайлов),
;           отрисовка всех тайлов карты в буфер (func_draw_tile_to_buf),
;           отрисовка HUD (счёт/жизни/статус), инициализация координат игрока и
;           сущностей из буфера параметров, затем JMP lbl_main_game_loop.
;           Ветка победы: рисует рамку, поздравление (str_congratulation) и
;           бонус (str_bonus), начисляет 5000 (1388h) очков, JMP 1447h
;           (обработчик вне RDB).

; Стоп-колонка ходьбы героя в зале славы: награда (глифы 9Dh/9Eh) рисуется в
; data_text_buffer+0250h = row18*32+col16, т.е. col 16h (центр экрана). Герой
; (ширина 2 колонки) встаёт сразу СПРАВА от награды -> base col = 16h+1 = 11h.
hof_walk_stop_col EQU 11h

func_level_loader:
    MVI A, 0FFh                 ; (Фаза 4) выключить мигание выхода до появления
    STA var_exit_phase
    LXI H, var_level            ; 0x197C
    INR M                       ; 0x197F
    MOV A, M                    ; 0x1980
    CPI 10h                     ; 0x1981
    JNC func_hall_of_fame       ; 0x1983
    XRA A                       ; 0x1986
    STA var_egg_counter                    ; 0x1987
    LXI H, data_level_params    ; 0x198A
    LDA var_level               ; 0x198D
    RLC                         ; 0x1990
    RLC                         ; 0x1991
    RLC                         ; 0x1992
    MOV E, A                    ; 0x1993
    MVI D, 00h                  ; 0x1994
    DAD D                       ; 0x1996
    LXI D, data_level_param_buf ; 0x1997
    LXI B, 0008h                ; 0x199A
    CALL func_memcpy            ; 0x199D
loc_19A0:
    MVI A, 0FFh                 ; (Фаза 4) сброс мигания и на путях входа в середину
    STA var_exit_phase          ; функции:death-restart(JMP 19A0), след. уровень(CALL)
    LXI SP, 0100h               ; 0x19A0
    ; --- Шаг E3: полный CLS VRAM перед сборкой уровня -------------------------
    ;     Оригинальный func_put_char пропускает рисование клетки, если её код в
    ;     буфере уже равен записываемому (CMP M / RZ), а func_clear_textbuf стоит
    ;     РАНЬШЕ рисовки карты. Значит пустые клетки (0x20) при рестарте в VRAM
    ;     вообще не перерисовываются, и пиксели врага, оставленные в пустой
    ;     клетке, переживают рестарт / переход на уровень. Карта покрывает только
    ;     16x11 тайлов, поэтому нижние строки поля и траектория яйца не
    ;     перерисовываются вообще никем — чистить надо всё видео-ОЗУ.
    ;
    ;     Инструмент берём существующий: func_clear_vram (тот же CLS, что и в
    ;     func_main_init на загрузке) — 32 КБ через PUSH H, ~6 T/байт. Она делает
    ;     DI и сама не включает прерывания обратно, поэтому EI сразу после неё:
    ;     без этого загрузчик (~32 hw-кадров) прошёл бы при DISABLED прерываниях
    ;     и мы потеряли бы асинхронный SFX/driver и перевзвод cnt1 в VBlank.
    ;     Регистры func_clear_vram не ломают семантику пути: A и E она сохраняет,
    ;     B/C/D/H/L всё равно перезаписываются ниже, а SP := 0100h сделан до вызова
    ;     и восстанавливается самой функцией (saved_sp).
    CALL func_clear_vram
    EI
    CALL func_clear_textbuf     ; 0x19A3
    LDA var_level               ; 0x19A6
    DCR A                       ; 0x19A9
    LXI H, data_level_maps      ; 0x19AA
    JZ loc_19B8                 ; 0x19AD
    LXI D, 00B0h                ; 0x19B0
loc_19B3:
    DAD D                       ; 0x19B3
    DCR A                       ; 0x19B4
    JNZ loc_19B3                ; 0x19B5
loc_19B8:
    LXI D, 0000h                ; 0x19B8
    LXI B, 00B0h                ; 0x19BB
loc_19BE:
    PUSH B                      ; 0x19BE
    PUSH H                      ; 0x19BF
    MOV A, M                    ; 0x19C0
    ADD A                       ; 0x19C1
    ADD A                       ; 0x19C2
    LXI H, data_tile_graphics   ; 0x19C3
    CALL func_hl_add_a          ; 0x19C6
    PUSH D                      ; 0x19C9
    CALL func_draw_tile_to_buf  ; 0x19CA
    POP D                       ; 0x19CD
    INR D                       ; 0x19CE
    INR D                       ; 0x19CF
    MOV A, D                    ; 0x19D0
    CPI 20h                     ; 0x19D1
    JNZ loc_19DA                ; 0x19D3
    MVI D, 00h                  ; 0x19D6
    INR E                       ; 0x19D8
    INR E                       ; 0x19D9
loc_19DA:
    POP H                       ; 0x19DA
    INX H                       ; 0x19DB
    POP B                       ; 0x19DC
    DCX B                       ; 0x19DD
    MOV A, B                    ; 0x19DE
    ORA C                       ; 0x19DF
    JNZ loc_19BE                ; 0x19E0
    CALL func_draw_score_hud    ; 0x19E3
    CALL func_play_sfx          ; 0x19E6
    MVI A, 10h                  ; 0x19E9
    STA var_lives_icons         ; 0x19EB
    CALL func_draw_status_hud   ; 0x19EE
    MVI A, 01h                  ; 0x19F1
    STA var_player_row          ; 0x19F3
    INR A                       ; 0x19F6
    STA var_player_col          ; 0x19F7
    XRA A                       ; 0x19FA
    STA var_game_state          ; 0x19FB
    LDA data_level_param_buf+02h                    ; 0x19FE
    STA var_entity1_state       ; 0x1A01
    LDA data_level_param_buf+05h                    ; 0x1A04
    STA var_entity2_state       ; 0x1A07
    LDA data_level_param_buf+03h                    ; 0x1A0A
    STA data_entity_xcoords+01h                    ; 0x1A0D
    LDA data_level_param_buf+04h                    ; 0x1A10
    STA data_entity_ycoords+01h                    ; 0x1A13
    LDA data_level_param_buf+06h                    ; 0x1A16
    STA data_entity_xcoords+02h                    ; 0x1A19
    LDA data_level_param_buf+07h                    ; 0x1A1C
    STA data_entity_ycoords+02h                    ; 0x1A1F
    XRA A                       ; 0x1A22
    STA var_egg_seq                    ; 0x1A23
    LXI H, 0000h                ; 0x1A26
    SHLD var_blink_cell                   ; 0x1A29
    CALL func_draw_game_objects ; 0x1A2C
    XRA A                       ; 0x1A2F
    STA var_move_dir                    ; 0x1A30
    MVI A, 03h                  ; 0x1A33
    STA var_work_const          ; 0x1A35
    CALL func_raster_timer_init ; включить секундомер растра (ch1) — растр-safe рисование героя
    ; --- Step 0: сброс кадрового каркеса перед входом в игровой цикл ---------
    XRA A
    STA var_frame_sub           ; sub=0: до первого тика = 12 hw-кадров
    STA var_glyph_voff          ; Step 2a: герой выровнен по клетке (твин-сдвиг=0)
    STA var_glyph_hoff          ; Step 2b: горизонтальный midpoint-режим=0 (выровненно)
    ; --- Step 2b fix: засеять кэш отображения героя точкой спауна ---------------
    ;     var_enemy_rc нигде в обычном пути загрузки не инициализируется (только в
    ;     ветке победы/смерти). Первый func_hero_render брал СТАРЫЙ var_enemy_rc
    ;     (со заставки) и анимировал из него -> фантомный полукадр внутри стены на
    ;     самом первом кадре. Здесь cr/cc := row/col спауна, voff/hoff уже =0.
    ;     var_hero_idx := sentinel (!= idx стойки 2) -> первый кадр ЧИСТО рисует
    ;     стоящего героя в спауне (erase-footprint==новая клетка, без перехода). --
    LDA var_player_row
    STA var_enemy_rc            ; cr(отображ.) = row спауна (1)
    LDA var_player_col
    STA var_enemy_rc+1          ; cc(отображ.) = col спауна (2)
    MVI A, 0FFh
    STA var_hero_idx            ; sentinel -> форсируем первый draw стоящего героя
    ;     ВНИМАНИЕ (HERO-IN-WALL): сам по себе этот sentinel рисовал стоячего героя
    ;     в воздушном спауне на 1-м кадре (герой «висел» до 1-го game_update).
    ;     Форс отложен в func_hero_render до sub>=6 (после 1-го прохода гравитации).
    LXI H, data_text_buffer
    SHLD var_scan_ptr           ; курсор чанка скана огня = 0-я клетка буфера
    ; --- Step E1: засеять отображение врагов (плавная анимация) --------------
    ;     disp := цель (координаты спауна), voff=0, кэш кодов := то, что уже лежит
    ;     в буфере на клетке цели (уровень нарисован загрузчиком немедленно), поэтому
    ;     первый кадр func_enemy_render не рисует ничего — фантомов как у героя нет.
    CALL func_enemy_render_init
    JMP lbl_main_game_loop      ; 0x1A38
func_hall_of_fame:
    ; Зал славы (экран награждения): герой идёт по залу, надпись CONGRATULATION/BONUS,
    ; начисление 1388h очков, уход на loc_1447 (общий эпилог -> заставка).
    ; Суб-сдвиги твина композитинга маской+OR обнуляем — на этом пути
    ; func_hero_render (пишущий их в обычной загрузке уровня) минуется, а
    ; RAM-мусор дал бы кривой сдвиг OR-глифа.
    XRA A                       ; var_glyph_voff = 0 (выровненно по клетке)
    STA var_glyph_voff
    STA var_glyph_hoff          ; var_glyph_hoff = 0
    CALL func_draw_game_objects ; 0x1A3B
    CALL func_clear_textbuf     ; 0x1A3E
    LXI H, data_text_buffer+0100h                ; 0x1A41
    CALL func_set_text_ptr      ; 0x1A44
    LXI B, 0180h                ; 0x1A47
loc_1A4A:
    MVI A, 9Ch                  ; 0x1A4A
    CALL func_print_char_at_ptr ; 0x1A4C
    DCX B                       ; 0x1A4F
    MOV A, C                    ; 0x1A50
    ORA B                       ; 0x1A51
    JNZ loc_1A4A                ; 0x1A52
loc_1A55:
    PUSH B                      ; 0x1A55
    MOV A, B                    ; 0x1A56
    ADD A                       ; 0x1A57
    MOV D, A                    ; 0x1A58
    MVI E, 14h                  ; 0x1A59
    LXI H, data_tile_graphics+08h                 ; 0x1A5B
    CALL func_draw_tile_to_buf  ; 0x1A5E
    POP B                       ; 0x1A61
    INR B                       ; 0x1A62
    MOV A, B                    ; 0x1A63
    CPI 10h                     ; 0x1A64
    JNZ loc_1A55                ; 0x1A66
    XRA A                       ; 0x1A69
    STA var_player_col          ; 0x1A6A
    CALL func_draw_score_hud    ; 0x1A6D
    CALL func_draw_level_hud    ; 0x1A70
    CALL func_draw_status_hud   ; 0x1A73
    LXI H, data_text_buffer+0250h                ; 0x1A76
    CALL func_set_text_ptr      ; 0x1A79
    MVI A, 9Dh                  ; 0x1A7C
    CALL func_print_char_at_ptr ; 0x1A7E
    LXI H, data_text_buffer+0270h                ; 0x1A81
    CALL func_set_text_ptr      ; 0x1A84
    MVI A, 9Eh                  ; 0x1A87
    CALL func_print_char_at_ptr ; 0x1A89
loc_1A8C:
    LDA var_egg_hist_prev                    ; 0x1A8C
    MOV B, A                    ; 0x1A8F
    LDA var_egg_hist_cur                    ; 0x1A90
    STA var_egg_hist_prev                    ; 0x1A93
    MOV A, B                    ; 0x1A96
    STA var_egg_hist_cur                    ; 0x1A97
    LXI H, var_player_col       ; 0x1A9A
    INR M                       ; 0x1A9D
    LDA var_egg_hist_prev                    ; 0x1A9E
    CPI 01h                     ; 0x1AA1
    JZ loc_1ABD                 ; 0x1AA3
    LDA var_page_flip           ; 0x1AA6
    MOV B, A                    ; 0x1AA9
    LDA var_page_flip_hi                    ; 0x1AAA
    STA var_page_flip           ; 0x1AAD
    MOV A, B                    ; 0x1AB0
    STA var_page_flip_hi                    ; 0x1AB1
    LDA var_page_flip           ; 0x1AB4
    STA var_collision_flag      ; 0x1AB7
    JMP loc_1AC2                ; 0x1ABA
loc_1ABD:
    MVI A, 03h                  ; 0x1ABD
    STA var_collision_flag      ; 0x1ABF
loc_1AC2:
    MVI A, 12h                  ; 0x1AC2
    STA var_scr_090A                    ; 0x1AC4
    LDA var_player_col          ; 0x1AC7
    STA var_scr_0909                    ; 0x1ACA
    LDA var_collision_flag      ; 0x1ACD
    DCR A                       ; 0x1AD0
    STA var_obj_type_idx                    ; 0x1AD1
    LXI H, var_enemy_rc                 ; 0x1AD4
    LDA var_scr_090A                    ; 0x1AD7
    CMP M                       ; 0x1ADA
    JNZ loc_1AE7                ; 0x1ADB
    INX H                       ; 0x1ADE
    LDA var_scr_0909                    ; 0x1ADF
    CMP M                       ; 0x1AE2
    DCX H                       ; 0x1AE3
    JZ loc_1AEA                 ; 0x1AE4
loc_1AE7:
    CALL func_draw_tile_at_ptr  ; 0x1AE7
loc_1AEA:
    LDA var_scr_090A                    ; 0x1AEA
    MOV L, A                    ; 0x1AED
    LDA var_scr_0909                    ; 0x1AEE
    MOV H, A                    ; 0x1AF1
    SHLD var_enemy_rc                   ; 0x1AF2
    XCHG                        ; 0x1AF5
    LDA var_obj_type_idx                    ; 0x1AF6
    ADD A                       ; 0x1AF9
    ADD A                       ; 0x1AFA
    LXI H, data_tile_table_26DE ; 0x1AFB
    CALL func_hl_add_a          ; 0x1AFE
    CALL func_render_tile_vram_or  ; 0x1B01  (было func_render_tile_vram)
    MVI B, 02h                  ; 0x1B04  (выровненный кадр: средняя скорость)
    CALL func_delay             ; 0x1B06
    ; --- полукадр: горизонтальный midpoint +4px вправо (func_render_tile_vram_or3) ---
    ; Тот же примитив, что в основной игре (func_hero_render loc_hr_draw3): широкий
    ; 3-колоночный OR-blit из precompute-кэша data_hero_shift_cache ( hoff=1 ). Стираем
    ; выровненный кадр A(c) из буфера (клетка var_enemy_rc = cols c,c+1), затем
    ; накладываем спрайт на полклетки правее (cols c..c+2). Следующий A(c+1) перекроет
    ; хвост col c+2, поэтому расширять стирание не нужно. var_glyph_voff=0 (func_hall_of_fame).
    LXI   H, var_enemy_rc
    CALL  func_draw_tile_at_ptr ; стереть выровненный A(c)
    LDA   var_obj_type_idx      ; idx (запись [0]/[1]/[2])
    MOV   E, A
    MVI   D, 00h
    LXI   H, 0000h
    ORA   A
    JZ    vw_mid_done           ; idx==0 -> HL=0
vw_mid_mul:
    MOV   A, L
    ADI   0C0h                  ; +192 (окно тайла = 6 фрагментов x 32)
    MOV   L, A
    MOV   A, H
    ACI   00h
    MOV   H, A
    DCR   E
    JNZ   vw_mid_mul
vw_mid_done:
    LXI   D, data_hero_shift_cache
    DAD   D                     ; HL = база окна для idx
    LDA   var_scr_0909          ; col c
    MOV   D, A                  ; base col = c (hoff=1, сдвиг вправо)
    LDA   var_scr_090A          ; row 12h
    MOV   E, A
    CALL  func_render_tile_vram_or3
    MVI   B, 01h                ; (полукадр midpoint: чуть короче выровненного)
    CALL  func_delay
    LDA var_player_col          ; 0x1B09
    CPI hof_walk_stop_col       ; 0x1B0C  (стоп справа от награды, было 1Ch)
    JC loc_1A8C                 ; 0x1B0E
    LDA var_player_col          ; 0x1B11
    STA var_scr_0909                    ; 0x1B14
    MVI A, 12h                  ; 0x1B17
    STA var_scr_090A                    ; 0x1B19
    MVI A, 06h                  ; 0x1B1C
    STA var_obj_type_idx                    ; 0x1B1E
    ; --- перед финальным «стоит лицом вперёд»: перерисовать стену за героем ---
    ; Последний midpoint ходьбы оставил в VRAM пиксели спрайта в колонках
    ; stop..stop+2 (строки 12h/13h): OR-путь их не перекрывает, и под стоячим
    ; кадром видны остатки фазы ходьбы, а хвост col stop+2 торчит справа от героя.
    ; Восстанавливаем фон из текстового буфера двумя вызовами func_draw_tile_at_ptr
    ; (каждый рисует блок 2x2): (12h,stop) -> stop/stop+1, (12h,stop+1) -> stop+1/+2.
    ; Прежнее условное стирание (сравнение с var_enemy_rc) убрано — оно
    ; пропускалось ровно в нашем случае: герой финиширует в своей же клетке.
    MVI   A, 12h
    STA   var_enemy_rc            ; пара (row, col) для func_draw_tile_at_ptr
    MVI   A, hof_walk_stop_col
    STA   var_enemy_rc+1
    LXI   H, var_enemy_rc
    CALL  func_draw_tile_at_ptr   ; стена за колонками stop/stop+1
    MVI   A, hof_walk_stop_col+1
    STA   var_enemy_rc+1
    LXI   H, var_enemy_rc
    CALL  func_draw_tile_at_ptr   ; стена за колонками stop+1/stop+2
    LDA var_scr_090A                    ; 0x1B37
    MOV L, A                    ; 0x1B3A
    LDA var_scr_0909                    ; 0x1B3B
    MOV H, A                    ; 0x1B3E
    SHLD var_enemy_rc                   ; 0x1B3F
    XCHG                        ; 0x1B42
    LDA var_obj_type_idx                    ; 0x1B43
    ADD A                       ; 0x1B46
    ADD A                       ; 0x1B47
    LXI H, data_tile_table_26DE ; 0x1B48
    CALL func_hl_add_a          ; 0x1B4B
    CALL func_render_tile_vram_or  ; 0x1B4E  (было func_render_tile_vram)
    LXI H, data_text_buffer+0250h                ; 0x1B51
    CALL func_set_text_ptr      ; 0x1B54
    MVI A, 9Ch                  ; 0x1B57
    CALL func_print_char_at_ptr ; 0x1B59
    LXI H, data_text_buffer+0087h                ; 0x1B5C
    CALL func_set_text_ptr      ; 0x1B5F
    LXI H, str_congratulation   ; 0x1B62
    CALL func_print_string      ; 0x1B65
    LXI H, data_text_buffer+00C6h                ; 0x1B68
    CALL func_set_text_ptr      ; 0x1B6B
    LXI H, str_bonus            ; 0x1B6E
    CALL func_print_string      ; 0x1B71
    LHLD var_score              ; 0x1B74
    LXI D, 1388h                ; 0x1B77
    DAD D                       ; 0x1B7A
    SHLD var_score              ; 0x1B7B
    CALL func_draw_score_hud    ; 0x1B7E
    CALL func_draw_game_objects ; 0x1B81
    ; FIX (экран награждения): func_draw_game_objects первым блоком затирает клетку
    ; var_enemy_rc — а в ней последняя позиция идущего персонажа (row 12h / col stop).
    ; Оверлей персонажа лежит только в VRAM (рисовался стандартным путём
    ; func_render_tile_vram, в текстовый буфер не писался), поэтому стирание из
    ; буфера его убирает — персонаж «пропадает» сразу после вывода CONGRATULATION.
    ; Перерисуем финальный кадр персонажа (запись [6] тайл-таблицы) поверх стёртой
    ; клетки, чтобы он оставался видимым в удерживаемом кадре до возврата на заставку.
    MVI   D, hof_walk_stop_col    ; col финальной позиции персонажа (было 1Ch)
    MVI   E, 12h                  ; row финальной позиции персонажа
    MVI   A, 06h                  ; obj_type финального (стоячего) кадра
    ADD   A
    ADD   A                       ; *4 = смещение записи в data_tile_table_26DE
    LXI   H, data_tile_table_26DE
    CALL  func_hl_add_a           ; HL = указатель графики тайла
    CALL  func_render_tile_vram_or  ; персонаж поверх стёртой клетки
    JMP loc_1447                    ; 0x1B84
