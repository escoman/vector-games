; Метка: lbl_main_game_loop
; Адрес: 0x0E85
; Описание: Главный игровой цикл, ШАГ 1 — плавное распределение логики по кадрам.
;
;   Структура кадра (каждый hw-кадр):
;     EI; HLT                         ; один wait-VBlank на кадр (INT RST7 ->
;                                      func_vblank_isr). Эмулятор фиксирует
;                                      was_halt:true каждый кадр.
;     CALL func_render_all            ; единый рендер: чанк скана огня 128 ячеек
;     INR var_frame_sub               ; досчётчик кадра в 12-кадровом окне (1..12)
;
;   Шаг 1 (полукадры): раньше оба entity-прохода (BC=1,2) с двумя вызовами
;   func_game_update шли СПИНА К СПИНЕ в одном кадре тика (Step 0) — герой
;   прыгал на 2 строки за раз и замирал на 12 кадров («отрывисто»). Теперь
;   два прохода разнесены по кадрам того же 12-кадрового окна:
;     sub==6  -> проход 1: entity1 + func_game_update (шаг героя №1)
;     sub==12 -> проход 2: entity2 + func_game_update (шаг №2) + обмен страницей
;   Герой/враги идут «шаг раз в ~6 кадров» — плавность как в оригинале (где
;   проходы разносили внутренний EI;HLT + func_delay), темп тот же. Каждый
;   проходный кадр делает вдвое меньше работы, чем тик-тело Step 0, поэтому
;   перестает переползать границу кадра -> период тика ровно 12 (не 13).
;
;   Особые пути: func_game_update в конце может не вернуть RC (перезапуск
;   при A=(HL) below >= 6Eh и ни один item-dispatch не сработал) — fall-
;   through в lbl_main_game_loop (физически идёт сразу за телом game_update в
;   layout). После fall-through CPU идёт в EI; HLT, т.е. ждёт следующий VBlank;
;   PUSH B/CALL-адрес этой же итерации осиротеют — ровно как в оригинале
;   (глубина стека game_update не увеличена: тело прохода инлайн, не CALL).
;
;   Сброс var_frame_sub / var_scan_ptr выполняется в func_level_loader перед
;   JMP сюда; инициализация до первого прохода = 6 hw-кадров после входа.

lbl_main_game_loop:
    ; --- Шаг 1: кадровый синхрон + единый рендер ---------------------------
    EI                          ; разрешить INT; следующий VBlank вернёт управление
    HLT                         ; спать до RST7 (was_halt=true каждый кадр)
    CALL func_render_all        ; чанк скана огня (128 ячеек из data_text_buffer)
    CALL func_enemy_render      ; Step E1: плавный vertical easing врагов (обычный блит)
    CALL func_hero_render       ; Step 2a (Вариант A): плавный твин+отрисовка героя
    ;                             ;   (цель = var_player_row/col; каждый кадр шаг 4px
    ;                             ;    по вертикали; на покое — без перерисовки)
    ; --- гейт: два проходных кадра в 12-кадровом окне ----------------------
    LXI H, var_frame_sub
    INR M                       ; sub++ (кадр учтён), 1..12
    MVI A, 6d
    CMP M                       ; Z, если sub==6 (середина тика)
    JZ  lbl_mgl_pass1           ; -> entity1 + game_update (шаг героя №1)
    MVI A, 12d
    CMP M                       ; Z, если sub==12 (конец тика)
    JZ  lbl_mgl_pass2           ; -> entity2 + game_update (шаг №2) + флип
    JMP lbl_main_game_loop      ; idle-кадр: только рендер огня
lbl_mgl_pass1:
    LXI B, 0001h
    JMP lbl_mgl_body
lbl_mgl_pass2:
    MVI M, 00h                  ; reset sub (HL = &var_frame_sub, не менялся)
    LXI B, 0002h
    ; fall-through в тело одного прохода
lbl_mgl_body:                   ; ОДИН проход: диспетчер сущности BC + game_update
    PUSH B                      ; 0x0E88
    MOV A, C                    ; 0x0E89
    STA var_entity_index        ; 0x0E8A
    LXI H, data_level_param_buf_end                 ; 0x0E8D
    DAD B                       ; 0x0E90
    MOV A, M                    ; 0x0E91
    CPI 01h                     ; 0x0E92
    PUSH PSW                    ; 0x0E94
    CZ func_entity_state1       ; 0x0E95
    POP PSW                     ; 0x0E98
    CPI 02h                     ; 0x0E99
    PUSH PSW                    ; 0x0E9B
    CZ func_entity_state2       ; 0x0E9C
    POP PSW                     ; 0x0E9F
    CPI 03h                     ; 0x0EA0
    PUSH PSW                    ; 0x0EA2
    CZ func_entity_state3       ; 0x0EA3
    POP PSW                     ; 0x0EA6
    CPI 04h                     ; 0x0EA7
    PUSH PSW                    ; 0x0EA9
    CZ func_entity_state4       ; 0x0EAA
    POP PSW                     ; 0x0EAD
    CPI 05h                     ; 0x0EAE
    PUSH PSW                    ; 0x0EB0
    CZ func_entity_state5       ; 0x0EB1
    POP PSW                     ; 0x0EB4
    CPI 06h                     ; 0x0EB5
    PUSH PSW                    ; 0x0EB7
    CZ func_entity_state6       ; 0x0EB8
    POP PSW                     ; 0x0EBB
    CPI 07h                     ; 0x0EBC
    PUSH PSW                    ; 0x0EBE
    CZ func_entity_state7       ; 0x0EBF
    POP PSW                     ; 0x0EC2
    CPI 08h                     ; 0x0EC3
    PUSH PSW                    ; 0x0EC5
    CZ func_entity_state8       ; 0x0EC6
    POP PSW                     ; 0x0EC9
    CPI 09h                     ; 0x0ECA
    PUSH PSW                    ; 0x0ECC
    CZ func_entity_state9       ; 0x0ECD
    POP PSW                     ; 0x0ED0
    CPI 0Ah                     ; 0x0ED1
    CZ func_entity_state10      ; 0x0ED3
    CALL func_game_update       ; 0x0ED6  ; RC -> след.; fall-through -> lbl_main_game_loop
    ; --- починка мерцания: герой ПОСЛЕДНИМ экранным писателем в свою область ----
    ; Любая запись экрана внутри прохода (скан огня, стирание собранного фрукта
    ; func_score_and_redraw, mover объектов) идёт ВЫШЕ героя и затирает его OR-оверлей.
    ; Идемпотентная beam-safe перекраска героя (guard + OR в var_enemy_rc, кадр из
    ; var_hero_idx) восстанавливает оверлей. Поймано и на collect-пути: score_and_redraw
    ; RET-ится ровно сюда (на POP B), поэтому CALL выполняется и после сбора.
    CALL func_hero_repaint_over
    POP B                       ; 0x0EDE
    ; --- обмен страницей только после pass2 (C==2) -------------------------
    MOV A, C                    ; 0x0EE0
    CPI 02h                     ; 0x0EE1
    JNZ lbl_main_game_loop      ; pass1 — без флипа, следующий кадр
    LDA var_page_flip           ; 0x0EE6
    MOV B, A                    ; 0x0EE9
    LDA var_page_flip_hi                    ; 0x0EEA
    STA var_page_flip           ; 0x0EED
    MOV A, B                    ; 0x0EF0
    STA var_page_flip_hi                    ; 0x0EF1
    JMP lbl_main_game_loop
