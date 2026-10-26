; Метка: lbl_main_game_loop
; Адрес: 0x0E85
; Описание: Главный игровой цикл. ШАГ 1 — плавное распределение логики по кадрам.
;           Срез B — raster-порядок КАДРА ПО ПОЛОСЕ ГЕРОЯ (selector):
;
;   В начале кадра вычисляется var_hero_ahead: можно ли нарисовать героя
;   AHEAD-of-beam (между верхом полосы героя и лучом заведомо больше его
;   стоимости erase+OR ~110 строк). От ответа зависит порядок:
;
;   HEAD-порядок (var_hero_ahead!=0, глубокие полосы row>=~13 И враги не смежны
;   с полосой героя — Срез B2): после VBlank прнг -> hero_render -> chaser_apply
;     -> enemy_render -> render_all(огонь) -> гейт/проход. Герой рисуется БЕЗ
;     ожидания луча (луч далеко сверху); враги/огонь пишутся ПОЗДЕ его окна, и
;     все последующие затирания его пикселей (огонь/враги/логика) идут ПОЗДЕ
;     луча — видимый скан этой строки уже прошёл, а следующий кадр восстановит
;     героя в самом начале, до прихода луча => tearing-free без repaint_over.
;
;   TAIL-порядок (var_hero_ahead==0, верхние/средние row, где герой обязан
;     ЖДАТЬ прохода луча): прнг -> enemy_render -> render_all -> гейт/проход ->
;     hero_render -> chaser_apply — порядок Среза A: ожидание guard'а героя
;     поглощает хвост кадра, после героя в кадре больше нет писателей (он
;     последний), repaint_over также не нужен. Ждать всё равно приходится —
;     ждём в конце, а не в начале, не сериализуя остальную работу за паузой.
;
;   Выбор детерминирован позицией героя: полоса меняется не чаще раза в 6
;   кадров (logic-проход) + easing-шаг 4px => дребезга порядок-по-кадрам нет.
;   Порог стоимости = 0x2940 (110 строк) — та же оценка, что var_raster_margin
;   caller'а hero_render; guard внутри hero_render перепроверяет сам (двойная
;   страховка: ошибся selector -> guard просто подождёт, безопасность не грубится).
;
;   Структура кадра (каждый hw-кадр):
;     EI; HLT                         ; один wait-VBlank на кадр (INT RST7 ->
;                                      func_vblank_isr). Эмулятор фиксирует
;                                      was_halt:true каждый кадр.
;     CALL func_prng                  ; энтропия ГПСЧ на границе VBlank
;     CALL func_hero_render           ; СПРАЗУ после VBlank: луч вверху, глубокие
;                                        полосы (row>=13) рисуются AHEAD без
;                                        ожидания; конец окна ~110-я строка
;     CALL func_enemy_chaser_apply    ; инвариант: погонщик сразу ПОСЛЕ героя
;     CALL func_enemy_render          ; враги: полосы выше героя, пишутся у/за лучом
;     CALL func_render_all            ; чанк скана огня (128 ячеек): хвост кадра,
;                                        guard_row ждёт прохода луча (позади) —
;                                        затирание пикселей героя происходит ПОСЛЕ
;                                        их скана, а следующий кадр восстанавливает
;                                        героя ДО прихода луча на его полосу =>
;                                        незаметно (tearing-free без repaint_over)
;     [pass-кадры] entity-диспетчер + func_game_update + flip страницы ; -> пишем позади
;                                        луча в самом конце кадра (как сегодня);
;                                        досчётчик var_frame_sub (1..12) — перед
;                                        гейтом прохода
;
;   Срез B УДАЛЯЕТ unconditional CALL func_hero_repaint_over из конца кадра:
;   герой больше не затирается «между фазами» видимого скана — все писатели после
;   hero_render идут позади луча, их следы видны только до следующего hero_render
;   начала кадра (ahead-реставрация). Остался только gated repaint в loc_exit_hero
;   (игрок в покое + мигающий выход под ногами — единственный писатель внутри
;   полосы героя, чей флип может попасть в видимый скан, пока герой не движется).
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
    ; --- Шаг 1 + Срез B selector: кадровый синхрон и выбор порядка -----------
    EI                          ; разрешить INT; следующий VBlank вернёт управление
    HLT                         ; спать до RST7 (was_halt=true каждый кадр)
    CALL func_prng              ; энтропия игрового цикла: крутить ГПСЧ один раз за
    ;                             ;   hw-кадр на границе VBlank (вне raster-окна героя),
    ;                             ;   так число кадров до события влияет на сид
    ; --- var_hero_ahead = (band_top - elapsed >= 0x2940) && (elapsed < top) ---
    CALL func_beam_count        ; DE = count
    LXI H, 7500h
    MOV A, L
    SUB E
    MOV L, A
    MOV A, H
    SBB D
    MOV H, A                    ; HL = elapsed (тики, растёт сверху вниз)
    LDA var_scr_090A            ; новая строка героя (цель) -> C
    MOV C, A
    LDA var_enemy_rc            ; старая строка героя (отображение) -> B
    MOV B, A
    ; --- Срез B2: ТЕСТ ЗАТРАВИВАНИЯ ПОЛОСЫ (всегда, не только при HEAD) -------
    ; erase врага — присваивание фона: если отображаемый ряд врага попадает в
    ; окно полосы героя [hmin-2 .. hmax+2], то HEAD-рисование героя ПЕРВЫМ
    ; означало бы, что враг затурует OR-оверлей героя ниже по кадру (чёрные
    ; квадраты половины спрайта). Поэтому trample=1 => форсируем TAIL (герой
    ; последний) и, если герой стоит в покое, дополнительно OR через
    ; func_hero_repaint_over. TAIL корректен всегда; HEAD — только trample=0.
    MOV A, B
    CMP C
    JC  lbl_mgl_hminw
    MOV A, C
lbl_mgl_hminw:                  ; A = hmin = min(prev,new)
    SUI 02h                     ; нижняя граница hmin-2 (заём => hero у верха)
    JNC lbl_mgl_lokneg
    MVI E, 00h
    JMP lbl_mgl_gotlo
lbl_mgl_lokneg:
    MOV E, A                    ; E = нижняя граница (включительно)
lbl_mgl_gotlo:
    MOV A, B                    ; hmax = max(prev,new)
    CMP C
    JNC lbl_mgl_hmaxw
    MOV A, C
lbl_mgl_hmaxw:
    ADI 03h                     ; верхняя граница hmax+3 (исключительно)
    MOV D, A                    ; D = верхняя граница окна
    LDA var_enemy_disp_rc+2     ; строка отображения слота 1
    CMP E
    JC  lbl_mgl_ts2
    CMP D
    JC  lbl_mgl_trample
lbl_mgl_ts2:
    LDA var_enemy_disp_rc+4     ; строка отображения слота 2
    CMP E
    JC  lbl_mgl_notramble
    CMP D
    JNC lbl_mgl_notramble
lbl_mgl_trample:
    MVI A, 01h
    STA var_hero_trample
    XRA A                       ; trample -> ahead=0 (TAIL)
    JMP lbl_mgl_hstore
lbl_mgl_notramble:
    XRA A
    STA var_hero_trample        ; trample=0: полоса героя чиста
    ; --- нет конфликта полос: решаем HEAD/TAIL по зазору до луча -------------
    MOV A, B                    ; hmin = min(prev,new)
    CMP C
    JC  lbl_mgl_hminprev
    MOV A, C
lbl_mgl_hminprev:
    MOV B, A
    ADD A
    ADD B                       ; A = min*3
    ADI 12h                     ; + (48*96)>>8 => band_top (младший байт 00)
    MOV D, A
    MVI E, 00h                  ; DE = band_top
    MOV A, L
    SUB E
    MOV A, H
    SBB D
    JNC lbl_mgl_htail           ; elapsed >= top: луч вошёл в полосу -> TAIL
    MOV A, E
    SUB L
    MOV C, A
    MOV A, D
    SBB H
    MOV B, A                    ; BC = gap = top - elapsed > 0
    LXI D, 2940h                ; стоимость hero erase+OR ~110 строк*96
    MOV A, C
    SUB E
    MOV A, B
    SBB D
    JC  lbl_mgl_htail           ; gap < стоимости -> guard ждал бы -> TAIL
    MVI A, 01h                  ; полоса чиста и зазор достаточен -> HEAD
    JMP lbl_mgl_hstore
lbl_mgl_htail:
    XRA A
lbl_mgl_hstore:
    STA var_hero_ahead
    ORA A
    JZ  lbl_mgl_ohead           ; TAIL: hero/chaser уйдут в конец кадра
    CALL func_hero_render       ; HEAD: твин+отрисовка героя ПЕРВОЙ, ahead-of-beam
    CALL func_enemy_chaser_apply ; инвариант: погонщик сразу ПОСЛЕ героя
lbl_mgl_ohead:
    CALL func_enemy_render      ; Step E1: плавный vertical easing врагов (обычный блит)
    CALL func_render_all        ; чанк скана огня (128 ячеек из data_text_buffer)
    ; --- гейт: два проходных кадра в 12-кадровом окне ----------------------
    LXI H, var_frame_sub
    INR M                       ; sub++ (кадр учтён), 1..12
    MVI A, 6d
    CMP M                       ; Z, если sub==6 (середина тика)
    JZ  lbl_mgl_pass1           ; -> entity1 + game_update (шаг героя №1)
    MVI A, 12d
    CMP M                       ; Z, если sub==12 (конец тика)
    JZ  lbl_mgl_pass2           ; -> entity2 + game_update (шаг №2) + флип
    JMP lbl_mgl_afterbody       ; idle-кадр: рендер+гейт сделан, хвост TAIL-порядка
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
    ; --- Срез B: unconditional func_hero_repaint_over УДАЛЁН ---------------
    ; HEAD: затирания после героя идут позади луча, восстановятся ahead-рендером
    ; след. кадра. TAIL: герой рисуется последним писателем кадра (как в Срезе A,
    ; но без repaint: логики после героя больше нет). Gated repaint остался
    ; только в loc_exit_hero (покой + мигающий выход под ногами).
    POP B                       ; 0x0EDE
    ; --- обмен страницей только после pass2 (C==2) -------------------------
    MOV A, C                    ; 0x0EE0
    CPI 02h                     ; 0x0EE1
    JNZ lbl_mgl_afterbody       ; pass1 — без флипа, в хвост кадра
    LDA var_page_flip           ; 0x0EE6
    MOV B, A                    ; 0x0EE9
    LDA var_page_flip_hi                    ; 0x0EEA
    STA var_page_flip           ; 0x0EED
    MOV A, B                    ; 0x0EF0
    STA var_page_flip_hi                    ; 0x0EF1
lbl_mgl_afterbody:              ; хвост кадра: TAIL-порядок дорисовывает героя здесь
    LDA var_hero_ahead
    ORA A
    JNZ lbl_main_game_loop      ; HEAD: герой уже нарисован в начале кадра
    CALL func_hero_render       ; TAIL: герой+погонщик ПОСЛЕДНИМИ (у/за лучом,
    CALL func_enemy_chaser_apply ;   как в Срезе A; guard при необходимости подождёт)
    JMP lbl_main_game_loop
