; Функция: func_collision_death
; Адрес: 0x13AA
; Размер: 205 байт (0x13AA-0x1476, непрерывное тело)
; Описание: Коллизия/гибель: проход по data_egg_speed_table, сравнение с
;   врагом (var_enemy_rc), перерис тайлов, подсчёт дельты счёта. 0x143B —
;   site релокации textbuf (516Ah). Входы loc_ из func_game_update (JNZ 13AA).
;   Улёт героя: каждый шаг рисуется guarded OR-композитом (func_raster_guard_hero +
;   func_render_tile_vram_or, кадр [6] выровненно) — единый flicker-free-идиом с
;   gameplay/exit; ранняя opaque-запись func_render_tile_vram затирала фон под героем.

func_collision_death:
    ; При коллизии враг может быть застёгнут на midpoint-кадре easing'а
    ; (hoff/voff != 0): 3-колоночное окно = выровненно + перелив со сдвигом 4px.
    ; func_game_update уходит сюда по JNZ, и пока идёт улёт/GameOver рендерер
    ; врагов не вызывается -> враг остаётся отрисованным наполовину весь пролёт.
    ; Нельзя просто вызвать func_enemy_render: он рендерит ОБА слота и для
    ; ВЫРОВНЕННОГО слота с целью на клетку в стороне запустит НОВЫЙ midpoint
    ; (hoff 0->2), т.е. сам создаст полу-кадр. func_enemy_settle трогает только
    ; слоты в фазе midpoint (snap: стереть перелив + нарисовать выровненно по
    ; цели), выровненные оставляет как есть.
    CALL  func_enemy_settle
    MVI   B, 0002h            ; 0x13AA
    CALL  func_sound_init     ; 0x13AC
    LDA   var_player_row      ; 0x13AF
    SUI   02h                 ; 0x13B2
    STA   var_entity_index                ; 0x13B4
    LDA   var_player_col      ; 0x13B7
    STA   var_collision_flag  ; 0x13BA
    LXI   B, 0000h            ; 0x13BD
loc_13C0:
    LXI   H, data_egg_speed_table; 0x13C0
    DAD   B                   ; 0x13C3
    MOV   A, M                ; 0x13C4
    CPI   0FFh                ; 0x13C5
    JZ    loc_1424            ; 0x13C7
    RRC                       ; 0x13CA
    RRC                       ; 0x13CB
    RRC                       ; 0x13CC
    ANI   01Fh                ; 0x13CD
    MOV   E, A                ; 0x13CF
    LDA   var_entity_index                ; 0x13D0
    ADD   E                   ; 0x13D3
    CPI   018h                ; 0x13D4
    JNC   loc_1424            ; 0x13D6
    STA   var_scr_090A                ; 0x13D9
    LDA   var_collision_flag  ; 0x13DC
    STA   var_scr_0909                ; 0x13DF
    MVI   A, 06h              ; 0x13E2
    STA   var_obj_type_idx    ; 0x13E4
    ; --- flicker-free: тот же идиом, что gameplay/exit-перекраска героя -------
    ; Один raster-guard на окно erase+draw этого шага улёта: полоса = union(старая
    ; строка в var_enemy_rc, новая в var_scr_090A). Пишется вне прохода луча.
    ; Срез A: cost-hint = erase+OR шага улёта ~110 строк*96 = 0x2940
    PUSH H
    LXI H, 2940h
    SHLD var_raster_margin
    POP H
    CALL  func_raster_guard_hero
    PUSH  H                   ; 0x13E7
    PUSH  B                   ; 0x13E8
    LXI   H, var_enemy_rc     ; 0x13E9
    LDA   var_scr_090A                ; 0x13EC
    CMP   M                   ; 0x13EF
    JNZ   loc_13FC            ; 0x13F0
    INX   H                   ; 0x13F3
    LDA   var_scr_0909                ; 0x13F4
    CMP   M                   ; 0x13F7
    DCX   H                   ; 0x13F8
    JZ    loc_13FF            ; 0x13F9
loc_13FC:
    CALL  func_draw_tile_at_ptr; 0x13FC
loc_13FF:
    LDA   var_scr_090A                ; 0x13FF
    MOV   L, A                ; 0x1402
    LDA   var_scr_0909                ; 0x1403
    MOV   H, A                ; 0x1406
    SHLD  var_enemy_rc        ; 0x1407
    XCHG                      ; 0x140A
    LDA   var_obj_type_idx    ; 0x140B
    ADD   A                   ; 0x140E
    ADD   A                   ; 0x140F
    LXI   H, data_tile_table_26DE; 0x1410
    CALL  func_hl_add_a       ; 0x1413
    ; OR-композит улетающего героя (было func_render_tile_vram — непрозрачно,
    ; пустые пиксели героя zero-write'ом затирали фон/огонь -> чёрный прямоугольник).
    ; Кадр [6] (var_obj_type_idx) при DEAD не использует суб-сдвиг -> выровненно:
    ; обнуляем var_glyph_voff, чтобы func_render_tile_vram_or не применил твин-сдвиг
    ; от последнего hero_render-кадра. Erase старой клетки (loc_13FC) остаётся restore
    ; из тени — корректно снимает OR-оверлей.
    XRA   A
    STA   var_glyph_voff
    CALL  func_render_tile_vram_or
    MVI   B, 0001h            ; 0x1419
    CALL  func_delay          ; 0x141B
    POP   B                   ; 0x141E
    POP   H                   ; 0x141F
    INR   C                   ; 0x1420
    JMP   loc_13C0            ; 0x1421
loc_1424:
    CALL  func_draw_game_objects; 0x1424
    XRA   A                   ; 0x1427
    STA   var_egg_counter     ; 0x1428
    LXI   H, var_bonus_counter; 0x142B
    DCR   M                   ; 0x142E
    MOV   A, M                ; 0x142F
    CPI   0FFh                ; 0x1430
    JZ    loc_1438            ; 0x1432
    JMP   loc_19A0            ; 0x1435
loc_1438:
    ; --- полная очистка экрана в начале GAME OVER -----------------------------
    ; func_clear_textbuf чистит лишь ТЕНЬ (data_text_buffer), а func_put_char
    ; дифует по ней (CMP M / RZ) и НЕ перерисовывает VRAM-клетку, чей код уже в
    ; буфере. OR-оверлеи (герой/враги/огонь) в тени не лежат: их клетки в тени =
    ; пробел, а в VRAM = пиксель оверлея -> redraw не происходит -> следы.
    ; Поэтому стираем VRAM целиком (тот же идиом, что func_level_loader loc_19A0
    ; перед сборкой уровня), затем чистим тень и печатаем GAME OVER.
    CALL  func_clear_vram
    EI                          ; func_clear_vram делает DI; вернуть прерывания
    CALL  func_clear_textbuf  ; 0x1438
    LXI   H, data_text_buffer+016Ah; 0x143B
    CALL  func_set_text_ptr   ; 0x143E
    LXI   H, str_game_over      ; 0x1441
    CALL  func_print_string   ; 0x1444
loc_1447:                    ; сюда влетает func_level_loader (JMP) — общий эпилог начисления очков
    LHLD  var_score           ; 0x1447
    XCHG                      ; 0x144A
    LHLD  var_score_delta     ; 0x144B
    STA   var_score_scratch   ; 0x144E
    MOV   A, L                ; 0x1451
    SBB   E                   ; 0x1452
    MOV   L, A                ; 0x1453
    MOV   A, H                ; 0x1454
    SBB   D                   ; 0x1455
    MOV   H, A                ; 0x1456
    PUSH  H                   ; 0x1457
    PUSH  PSW                 ; 0x1458
    ORA   L                   ; 0x1459
    JZ    loc_1463            ; 0x145A
    POP   H                   ; 0x145D
    MVI   A, 0BFh             ; 0x145E
    ANA   L                   ; 0x1460
    MOV   L, A                ; 0x1461
    PUSH  H                   ; 0x1462
loc_1463:
    POP   PSW                 ; 0x1463
    POP   H                   ; 0x1464
    LDA   var_score_scratch   ; 0x1465
    JNC   loc_146F            ; 0x1468
    XCHG                      ; 0x146B
    SHLD  var_score_delta     ; 0x146C
loc_146F:
    MVI   B, 0005h            ; 0x146F
    CALL  func_delay_long     ; 0x1471
    JMP   loc_0BC2            ; 0x1474
