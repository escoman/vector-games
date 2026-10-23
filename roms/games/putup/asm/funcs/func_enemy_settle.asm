; Функция: func_enemy_settle / func_enemy_settle_slot
; Адрес:   0x4540 (номинальный: рядом с func_enemy_render; файла в оригинале нет,
;          это emit проекта; реальное размещение — tools/order.json / layout.json,
;          Stage-4 свободная конкатенация, добавляется в конец порядка эмитов)
; Описание: «Осадка» врагов перед анимацией гибели. Вызывается из
;           func_collision_death ДО начала улёта героя (первой инструкцией).
;
; ЗАЧЕМ. Враг рисуется с суб-пиксельным easing'ом (func_enemy_render): на кадре
; горизонтального/вертикального midpoint он отрисовывается 3-колоночным окном —
; 2 колонки выровненно + 1 колонка-перелив со сдвигом 4 px ( hoff=1/2, voff=4 ).
; Столкновение с героем (func_game_update -> JNZ func_collision_death) может
; застегнуть врага РОВНО на таком midpoint-кадре, и пока идёт улёт/GameOver
; рендерер врагов больше не вызывается -> враг висит отрисованным наполовину
; (левая часть обычными тайлами, правая сдвинута на 4 px) всю анимацию.
;
; ПОЧЕМУ НЕ func_enemy_render. Прямой вызов рендерера на гибели НЕПРАВИЛЕН: он
; рендерит ОБА слота по их решению, и для ВЫРОВНЕННОГО слота (hoff=voff=0), у
; которого цель стоит на клетку в стороне (easing ещё не начал «доезжать»),
; ветка loc_ed_coldiff/rowdiff ЗАПУСТИТ НОВЫЙ midpoint (запишет hoff=1/2) — т.е.
; рендерер сам создаст полу-кадр там, где картинка была целой. Проверено
; дампом: при hoff=0/disp=col20/target=col19 вызов func_enemy_render поднял
; hoff 0->2.
;
; ЧТО ДЕЛАЕМ.
; 1) Слоты в фазе midpoint (disp_hoff!=0 ИЛИ disp_voff!=0): func_enemy_render_slot
;    сам уходит в ветку snap (loc_ed_snap: new=(tr,tc,0,0)) — стирает старый
;    footprint ВМЕСТЕ с колонкой-переливом и рисует выровненный тайл по ЦЕЛИ.
; 2) Выровненные (hoff=voff=0), НО ОТСТАЮЩИЕ по клетке (disp_rc != цель). Это и
;    есть ТИПИЧНАЯ коллизия: func_enemy_render вызывается КАЖДЫЙ hw-кадр, а
;    func_game_update (детект коллизии) — раз в 6 кадров (lbl_main_game_loop,
;    sub==6/12). К моменту гибели враг уже «доехал» суб-пиксельно (hoff=voff=0),
;    но его ОТОБРАЖАЕМАЯ клетка на 1 отстаёт от ЛОГИЧЕСКОЙ: цель сдвинулась на
;    ЭТОМ же проходе логики, а рендерер ещё не перерисовал (он был ДО game_update
;    в этом кадре). Проверено в живом отладчике: при коллизии hero=(6,11),
;    цель врага=(6,12), disp=(6,13), hoff=0. Враг ЦЕЛИКОМ нарисован по disp
;    (колонки 13,14), а тень/перерис func_draw_game_objects работают по ЦЕЛИ
;    (12,13) -> колонка disp остаётся лишним «сдвигом» справа = «правая часть
;    сдвинута на 4px». Значит и такой слот надо досвести к цели.
;    Не трогаем ТОЛЬКО выровненные слоты, у которых disp==цель (картинка верна),
;    и ПАССИВные состояния (0 / >=9 — погонщик): их рисует логика немедленным
;    блитом, erase рендерера стёр бы погонщика.
;
; РЕГИСТРЫ. func_enemy_render_slot сохраняет PSW/B/D/H; var_ed_slot — scratch
; рендерера, collision_death его не читает (свои var_scr_* ставит после).
; func_hl_add_a затирает A (HL += A), поэтому A перезагружаем из регистра/памяти
; перед каждым использованием.

func_enemy_settle:
    MVI   A, 01h
    CALL  func_enemy_settle_slot
    MVI   A, 02h
    ; fall-through во второй слот (хвостовой вызов: RET из render_slot/settle_slot
    ; вернёт прямо в caller func_enemy_settle, т.е. в func_collision_death)

func_enemy_settle_slot:
    STA   var_ed_slot
    ; --- hoff[slot] != 0 ? ---
    LDA   var_ed_slot
    LXI   H, var_enemy_disp_hoff
    CALL  func_hl_add_a             ; HL = &disp_hoff[slot]
    MOV   A, M
    ORA   A
    JNZ   func_enemy_settle_run     ; midpoint по горизонтали -> snap нужен
    ; --- voff[slot] != 0 ? ---
    LDA   var_ed_slot
    LXI   H, var_enemy_disp_voff
    CALL  func_hl_add_a             ; HL = &disp_voff[slot]
    MOV   A, M
    ORA   A
    JNZ   func_enemy_settle_run     ; midpoint по вертикали -> snap нужен
    ; --- обе 0: слот ВЫРОВНЕН. Но он может ОТСТАВАТЬ по КЛЕТКЕ (disp != цель) --
    ; типичная коллизия (см. шапку). Трогаем только НОРМАЛЬНЫХ врагов (state
    ; 1..8): пассивные (0 / >=9 — погонщик) рисует логика, erase их сотрёт.
    LDA   var_ed_slot
    LXI   H, data_level_param_buf_end
    CALL  func_hl_add_a             ; HL = &state[slot]
    MOV   A, M
    ORA   A
    JZ    func_enemy_settle_ret     ; state==0 — врага нет
    CPI   09h
    JNC   func_enemy_settle_ret     ; state>=9 — погонщик, не трогаем
    ; disp_row == tr ? disp_col == tc ? — если оба равны, картинка верна.
    CALL  func_ed_target_cell       ; var_ed_tr/tc = цель слота
    LDA   var_ed_slot
    ADD   A
    LXI   H, var_enemy_disp_rc
    CALL  func_hl_add_a             ; HL = &disp_rc[slot] (row)
    MOV   A, M
    LXI   H, var_ed_tr
    CMP   M
    JNZ   func_enemy_settle_force   ; строка отстаёт -> снап
    LDA   var_ed_slot
    ADD   A
    LXI   H, var_enemy_disp_rc
    CALL  func_hl_add_a
    INX   H                          ; -> col
    MOV   A, M
    LXI   H, var_ed_tc
    CMP   M
    JZ    func_enemy_settle_ret      ; disp==цель, выровнен -> ничего не рисуем
func_enemy_settle_force:
    ; Выровненный, но отстающий: помечаем слот как midpoint (hoff=1), чтобы
    ; func_enemy_render_slot ушёл в loc_ed_snap (new=(цель,0,0)) вместо того,
    ; чтобы ветка loc_ed_coldiff ЗАПУСТИЛА новый midpoint. Snap сотрёт disp-
    ; footprint (base=disp_col, ширина 3 колонки — сверх старого 2-колоночного
    ; окна) и нарисует врага выровненно по ЦЕЛИ; commit вернёт hoff=0.
    LDA   var_ed_slot
    LXI   H, var_enemy_disp_hoff
    CALL  func_hl_add_a             ; HL = &disp_hoff[slot]
    MVI   M, 01h
func_enemy_settle_run:
    ; var_ed_slot уже выставан; func_enemy_render_slot сделает snap сам
    JMP   func_enemy_render_slot
func_enemy_settle_ret:
    RET
