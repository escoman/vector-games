; Функции: func_enemy_render / func_enemy_render_slot / func_enemy_render_init /
;          func_enemy_render_init_slot / func_ed_target_cell / func_ed_fetch_codes /
;          func_ed_codes_same / func_ed_commit_disp / func_ed_commit_codes /
;          func_ed_erase_old / func_ed_erase_col / func_enemy_build_cache /
;          func_ed_find_pre / func_enemy_prebuild / func_ed_resolve_glyph /
;          func_ed_blit3 / func_ed_blit_frag
; Адрес:   0x4540 (номинальный: файла в оригинале нет, это emit проекта E1;
;           реальное размещение — tools/order.json / tools/layout.json)
; Описание: Плавная (суб-пиксельная) анимация врагов, ШАГИ E1+E2+E3 — вертикальный
;           (voff) и горизонтальный (hoff) easing для обоих слотов, ОБЫЧНАЯ (не OR)
;           перерисовка, предсборка окон на старте (E3-6a) и частичный erase
;           (E3-6b). Вызывается из главного цикла каждый hw-кадр ПЕРЕД
;           func_hero_render (герой рисуется поверх).

; МОДЕЛЬ. Логика врага не тронута: цель = (ycoords[slot], xcoords[slot]), шаги
; идут тем же темпом (1 клетка за проход), текстовый буфер по-прежнему хранит коды
; врага (из него читают коллизии героя). Менялось только КТО и КОГДА рисует VRAM:
; состояния 1..8 пишут буфер через func_set_tile_buf (без блита), а вид догоняет
; цель здесь. Картинка берётся ИЗ БУФЕРА ПО ЦЕЛЕ (4 кода клетки) — поэтому ни
; индекс тайла, ни указатель графики по слотам хранить не нужно, анимационный кадр
; состояний 3..8 подхватывается сам.

; РЕШЕНИЕ на кадр (приоритет — как у героя, сначала доехать активный midpoint):
;   * hoff != 0 или voff != 0 .. доезжаем: new = (tr, tc, 0, 0).
;   * tr == dr+1 и tc == dc .... падение на клетку: new = (dr, dc, voff=4) — рисуем в
;     СТАРОЙ клетке со сдвигом 4 px вниз (середина между старой и новой).
;   * tr == dr и tc == dc±1 ..... шаг по горизонтали: new = (dr, dc, hoff=1|2) —
;     клетка стоит, вид сдвинут на 4 px (E2). hoff=1 вправо (окно col..col+2,
;     нужен dc <= 29), hoff=2 влево (окно col-1..col+1, нужен dc >= 1); у стены и
;     при |delta| > 1 — snap, иначе 3-колоночное окно выйдет за экран.
;   * tr == dr и tc == dc ...... покой: перерисовать только если СМЕНИЛИСЬ коды
;     цели (кадр анимации) — иначе выход без записи в VRAM (0 фликера).
;   * иначе .................... snap new = (tr, tc, 0, 0): подъём и прыжок больше
;     чем на клетку — мгновенно.
;   * state == 0 или state >= 9 . ПАССИВНЫЙ слот: вид не рисуется, отображение
;     молча снапается к цели (погонщик HURRY-UP рисуется сам). Отстающий старый
;     footprint всё-таки стирается, но в пределах инварианта строк (ниже).
;
; ИНВАРИАНТ СТРОКИ (E3): рендерер не трогает VRAM ВНЕ ИГРОВОГО ПОЛЯ, строки
; 00h..17h (24 ряда; ниже — HUD/значки, выше — поля). Клетка строки r — это
; (06600h + r*32) -> hl = r*32+col, а приёмник L = 0E0h - 8*r по модулю 100h,
; т.е. СТРОКИ >= 32 АЛИАСЯТСЯ НА r mod 32 (прямо в видимое поле), а «коды фона»
; для erase читаются из 06600h + r*32 — уже за концом буфера. Так спавн погонщика
; (func_egg_caught кладёт ycoords = 023h = 35, «за экраном внизу») стирал фон в
; строках 3..4, а коды брал из 06A60h = var_ed_ho..newh = scratch самого рендерера
; => буквы-мусор вверху экрана. В E1 scratch там ещё не было, алиас рисовал пустой
; глиф и потому был незаметен (дырки в кирпичях вместо букв).
; Верхняя половина диапазона (18h..1Fh) отрезана по той же причине наоборот: там
; рендерер НИЧЕГО не рисовал (враги живут на поле), значит и стирать нечего, а
; строки 18h..19h — ряды HUD, которые логика красит сама.

; ERASE старого footprint: restore фона ИЗ БУФЕРА (func_draw_tile_at_ptr,
; выровненно, voff/hoff не читает). БЫЛО (E1/E2): восстанавливался ВЕСЬ старый
; footprint — ширина окна 2 колонки, при hoff != 0 — 3 (base = dc или dc-1, второй
; вызов на base+1); высота 2 строки, при voff != 0 ещё строка dr+1 (спил 4 px
; вниз). СТАЛО (E3-6b): если обе отрисовки в тех же двух строках (vo=0, newv=0,
; dr=newr) — восстанавливаются только колонки старого окна ВНЕ [newc, newc+1]
; (func_ed_erase_col, midpoint-кадр не стирает ничего); иначе — прежний полный
; erase. Порядок erase -> коммит -> draw: остатки старого вида всегда
; перекрываются новым в этом же кадре (3-колоночный блит полностью покрывает
; своё 2-колоночное erase-окно).

; ГОРИЗОНТАЛЬНЫЙ СДВИГ (E2, окно предсчитано в E3-6a) — как у героя Step 2b: сдвиг
; на 4 px = перелив nibble-ов в соседний VRAM-столбец, адресной арифметикой не
; выражается, поэтому композит из 3 колонок заранее собран в RAM-таблице окон
; data_enemy_shift_pre (по 192 байта на тайл) и рисуется обычным блитом
; func_ed_blit3 (6 готовых «глифов» по 32 байта).
; В E2 окно было привязано к слоту и пересобиралось лениво в кадре смены кодов —
; это стоило 114 строк растра и делало такие кадры самым тяжёлым классом (замер
; tools/e3_budget.py: burst 407 строк при кадре 312 -> пропуск hw-кадра).
; E3-6a: композит зависит ТОЛЬКО от
; тайла (пара глифов всегда из одной 2x2 записи data_tile_graphics, сдвиг
; фиксированный 4px, вакуум 0) -> все окна собираются на старте
; func_enemy_prebuild, в кадре остаётся поиск по кодам цели func_ed_find_pre.
; disp_codes слота при этом остались: они решают, НАДО ли рисовать покой (кадр
; анимации сменился), но больше не являются ключом годности композита; в пассивных
; состояниях коды по-прежнему не коммитятся (см. loc_ed_passive).

; ВЕРТИКАЛЬНЫЙ СДВИГ БЕЗ ДУБЛЯЖА КОПИРА. var_screen_mode читается ТОЛЬКО
; вычислением адреса приёмника внутри func_render_glyph (пишет его func_hw_init),
; а адрес растёт ВВЕРХ: L = var_screen_mode - rowbits. Значит сдвиг на voff px
; ВНИЗ = на время блита отнять voff от var_screen_mode — и вызвать НЕИЗМЕННУЮ
; func_render_tile_vram, передав в ней роль «тайл-графики» массиву var_ed_gcodes
; (это просто 4 байта кодов). Новый блитер не написан ни одного байта. Окно ~4
; глифа при включённых прерываниях безопасно: в func_vblank_isr нет ни чтения
; var_screen_mode, ни отрисовки (grep).

; Известное ограничение (наследие оригинала): restore фона по footprint врага
; затирает всё, что нарисовано в этих клетках (оверлей героя / второго врага).
; В оригинале тот же erase был немедленным; пересечение с врагом = смерть по
; правилам игры, поэтому окно артефакта <= 1 кадра.

; КОМПАКТНЫЕ ГЛИФЫ (E3 -> E3-6a). Слово в data_glyph_ptr_table = адрес записи + ТЕГ
; в бит0: compact (тег=1) хранит ТОЛЬКО 8-байтную маску плоскости 0 (плоскости 1..3
; сам рендерер пишет нулями, func_render_glyph loc_plane), raw (тег=0) — 32 байта
; подряд. Билдер композита читает запись 32 ПОСЛЕДОВАТЕЛЬНЫМИ байтами, поэтому
; compact-код собрал бы плоскости 1..3 ИЗ СОСЕДНЕЙ записи (мусор вместо глифа).
; Достижимость проверена: 600 кадров + init дают в var_ed_gcodes только 147..154
; (все raw) — проб tools/e3_probe_compact.py. Но коды берутся из текстового
; буфера, а его пишет логика, поэтому компактный код (32/буквы) способен зайти туда
; с новым состоянием. Func_render_glyph не тронута и остаётся верна.
; В E3 окно проверялось на compact КАЖДЫЙ кадр (func_ed_resolve_glyph выставлял
; var_ed_bc_compact, и диспетчер draw рисовал этот кадр выровненно). В E3-6a окна
; предсчитаны на старте, поэтому проверка переехала в func_enemy_prebuild: запись с
; compact-глифом помечается негодной, поиск func_ed_find_pre её пропускает -> тот же
; исход (один кадр без easing вместо мусора), но без единой проверки в кадре. Тайл,
; которого нет в data_enemy_pre_tiles, деградирует точно так же (промах -> loc_ed_drawa).

; Прозрачность: func_enemy_render сохраняет PSW/B/D/H.

func_enemy_render:
    ; Погонщик рисуется OR-композитом (func_render_tile_vram_or/or3), который
    ; применяет геройский вертикальный суб-сдвиг var_glyph_voff. Рендерер врагов
    ; идёт В КАДРЕ РАНЬШЕ героя, поэтому var_glyph_voff здесь = остаток прошлого
    ; кадра; его надо обнулить на время enemy-отрисовки (вертикаль погонщика уже
    ; задаётся сдвигом var_screen_mode в loc_ed_draw/post), иначе твин героя
    ; просочится в позицию погонщика. Сохраняем и возвращаем — repaint-героя и
    ; func_hero_render читают var_glyph_voff позже в этом же кадре.
    LDA var_glyph_voff
    STA var_ed_voff_sv
    XRA A
    STA var_glyph_voff
    STA var_chaser_pending    ; pending — СВЕЖИЙ флаг каждого кадра: обнуляем ДО
    ;                             ;   проходов слотов (слот-погонщик выставит его сам
    ;                             ;   через func_ed_stash_chaser). Иначе мусор в newly-
    ;                             ;   claimed RAM-зоне 0x6A80 на 1-м кадре уровня дал бы
    ;                             ;   ложный apply с мусорными var_ch_* (на обычных
    ;                             ;   уровнях погонщика нет — apply обязан молчать).
    MVI A, 01h
    STA var_ed_slot
    CALL func_enemy_render_slot
    MVI A, 02h
    STA var_ed_slot
    CALL func_enemy_render_slot
    LDA var_ed_voff_sv
    STA var_glyph_voff
    RET

; --- инициализация отображения (func_level_loader, сразу после координат спауна)
; disp = цель, voff = hoff = 0, кэш кодов = что уже лежит в буфере на клетке цели
; (уровень отрисован загрузчиком немедленно) -> первый кадр рендерер не рисует
; ничего. E3-6a: ничего засеивать в композиты не нужно — окна готовы со старта
; (func_enemy_prebuild), поиск по кодам происходит в кадре.
func_enemy_render_init:
    MVI A, 01h
    STA var_ed_slot
    CALL func_enemy_render_init_slot
    MVI A, 02h
    STA var_ed_slot
    CALL func_enemy_render_init_slot
    RET

func_enemy_render_init_slot:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    CALL func_ed_target_cell        ; var_ed_tr/tc = цель
    CALL func_ed_fetch_codes        ; var_ed_gcodes = коды цели
    ; commit_disp пишет var_ed_new*, поэтому решение «инициализации» собираем тут:
    ; отображение := цель, суб-сдвиги := 0 (иначе заселился бы нулевой scratch и
    ; первый кадр стёр бы фон в клетке (0,0) вместо спауна).
    LDA var_ed_tr
    STA var_ed_newr
    LDA var_ed_tc
    STA var_ed_newc
    XRA A
    STA var_ed_newv
    STA var_ed_newh
    CALL func_ed_commit_disp
    CALL func_ed_commit_codes
    POP H
    POP D
    POP B
    POP PSW
    RET

; --- один слот ---------------------------------------------------------------
func_enemy_render_slot:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    ; --- снимок отображения ---
    LDA var_ed_slot
    ADD A                           ; slot*2 (запись rc = строка,колонка)
    LXI H, var_enemy_disp_rc
    CALL func_hl_add_a
    MOV A, M
    STA var_ed_dr
    INX H
    MOV A, M
    STA var_ed_dc
    LDA var_ed_slot
    LXI H, var_enemy_disp_voff
    CALL func_hl_add_a
    MOV A, M
    STA var_ed_vo
    LDA var_ed_slot
    LXI H, var_enemy_disp_hoff      ; E2: горизонтальный суб-сдвиг
    CALL func_hl_add_a
    MOV A, M
    STA var_ed_ho
    ; --- цель и картинка цели (4 кода из буфера по клетке цели) ---
    CALL func_ed_target_cell        ; var_ed_tr/tc = цель
    CALL func_ed_fetch_codes        ; var_ed_gcodes = коды цели (4 глифа)
    ; --- ПАССИВНЫЕ СОСТОЯНИЯ: VRAM слота принадлежит логике, рендерер отступает.
    ; state==0 (врага нет) и state>=0A (0Ah — пассивный маркер слота 2 при HURRY-UP).
    ; state==09 (погонщик) БОЛЬШЕ НЕ пассивно: он участвует в easing-лифтнике,
    ; коды берутся из data_tile_table_26DE[8] (погонщик не пишет текстовый буфер).
    LDA var_ed_slot
    LXI H, data_level_param_buf_end
    CALL func_hl_add_a
    MOV A, M
    ORA A
    JZ loc_ed_passive                 ; state == 0 — врага нет
    CPI 0Ah
    JNC loc_ed_passive                ; state >= 0A — пассивный маркер
    ; --- chaser codes override: state==09 → коды из data_tile_table_26DE[8] ----
    ; Погонщик не пишет текстовый буфер, его «вид» всегда берётся из табличного
    ; тайла 8. Флаг var_ed_is_chaser включает симметричный midpoint + диагональ в
    ; loc_ed_rowdiff (обычные враги остаются на старом «только падение» поведении).
    CPI 09h
    JNZ loc_ed_not_chaser
    MVI A, 01h
    STA var_ed_is_chaser
    LXI H, data_tile_table_26DE + 8 * 4
    LXI D, var_ed_gcodes
    MOV A, M
    STAX D
    INX H
    INX D
    MOV A, M
    STAX D
    INX H
    INX D
    MOV A, M
    STAX D
    INX H
    INX D
    MOV A, M
    STAX D
    JMP loc_ed_codes_ok
loc_ed_not_chaser:
    XRA A
    STA var_ed_is_chaser              ; обычный враг: только падение -> midpoint
loc_ed_codes_ok:
    CALL func_ed_codes_same
    STA var_ed_same                 ; 0 = картинка не менялась
    ; --- решение ---
    LDA var_ed_ho
    ORA A
    JNZ loc_ed_snap                 ; активный горизонтальный midpoint -> доезжаем
    LDA var_ed_vo
    ORA A
    JNZ loc_ed_snap                 ; активный вертикальный midpoint -> доезжаем
    LDA var_ed_dr
    MOV C, A
    LDA var_ed_tr
    SUB C                           ; A = tr - dr
    JNZ loc_ed_rowdiff
    LDA var_ed_dc
    MOV C, A
    LDA var_ed_tc
    SUB C                           ; A = tc - dc
    JNZ loc_ed_coldiff              ; E2: горизонтальный midpoint?
    LDA var_ed_same                 ; та же клетка: возможен только новый кадр
    ORA A
    JNZ loc_ed_reanim               ; сменились коды -> перерисовать
    ; коды те же. Обычный враг: ничего не рисуем. Погонщик: всё равно перекрасить
    ; поверх героя — в idle-кадрах между его шагами движущийся герой затирает его.
    LDA var_ed_is_chaser
    ORA A
    JZ loc_ed_done
    JMP loc_ed_repaint_chaser
; --- смена колонки (A = tc - dc): середина по горизонтали или snap -----------
; Композит НЕ зависит от направления, задаёт его только базовая колонка
; блита (hoff=1: base=dc, hoff=2: base=dc-1) — как у героя. Клетка отображения
; стоит, едут только пиксели; на следующем кадре hoff!=0 -> доезжаем (snap к цели).
loc_ed_coldiff:
    CPI 01h                         ; ровно +1 вправо?
    JNZ loc_ed_cd_left
    LDA var_ed_dc
    CPI 1Eh                         ; dc >= 30 -> окну col..col+2 не хватает места
    JNC loc_ed_snap                 ; у правой стены — мгновенно
    MVI A, 01h
    STA var_ed_newh                 ; hoff=1: вид на 4px в col+1
    JMP loc_ed_hset
loc_ed_cd_left:
    CPI 0FFh                        ; ровно -1 (влево)?
    JNZ loc_ed_snap                 ; больше чем на клетку — мгновенно
    LDA var_ed_dc
    ORA A
    JZ loc_ed_snap                  ; у левой стены — мгновенно
    MVI A, 02h
    STA var_ed_newh                 ; hoff=2: вид на 4px в col-1
loc_ed_hset:
    LDA var_ed_dr                   ; клетка отображения НЕ едет: сдвиг пикселями
    STA var_ed_newr
    LDA var_ed_dc
    STA var_ed_newc
    XRA A
    STA var_ed_newv
    JMP loc_ed_erase
; --- смена строки (A = tr - dr, знаковое): вертикальный midpoint (СИММЕТРИЧНО)
; или диагональ (вертикаль + горизонталь вместе). Клетка отображения стоит
; (newr=dr, newc=dc), едут только пиксели: вертикаль — знаковым newv (+4 вниз
; = 04h, вверх = 0FCh; механизм SUB/ADD трактует его как знаковый байт),
; горизонталь — hoff (1 вправо, 2 влево) + 3-колоночное окно blit3.
; На следующем кадре vo!=0 || ho!=0 -> доезжаем (loc_ed_snap).
loc_ed_rowdiff:
    ; Обычный враг (не погонщик): старая асимметрия — midpoint ТОЛЬКО при падении
    ; (Δrow=+1) и неподвижной колонке; подъём/диагональ -> snap. Не менять: её
    ; правка не заказывалась.
    LDA var_ed_is_chaser
    ORA A
    JZ loc_ed_rd_legacy
    MOV C, A                          ; C = Δrow (tr-dr), знаковый
    ; Δcol = tc - dc
    LDA var_ed_dc
    MOV B, A
    LDA var_ed_tc
    SUB B                             ; A = Δcol
    CPI 01h
    JZ loc_ed_rd_right                ; вправо -> hoff=1
    CPI 0FFh
    JZ loc_ed_rd_left                 ; влево  -> hoff=2
    ORA A
    JNZ loc_ed_snap                   ; |Δcol|>1 -> мгновенно
    XRA A
    STA var_ed_newh                   ; Δcol=0 -> hoff=0
    JMP loc_ed_rd_row
loc_ed_rd_right:
    LDA var_ed_dc                     ; окно col..col+2: у правой стены нет места
    CPI 1Eh
    JNC loc_ed_snap
    MVI A, 01h
    STA var_ed_newh
    JMP loc_ed_rd_row
loc_ed_rd_left:
    LDA var_ed_dc                     ; окно col-1..col+1: у левой стены нет места
    ORA A
    JZ loc_ed_snap
    MVI A, 02h
    STA var_ed_newh
loc_ed_rd_row:
    ; клетка отображения не едет: сдвиг пикселями (newr=dr, newc=dc)
    LDA var_ed_dr
    STA var_ed_newr
    LDA var_ed_dc
    STA var_ed_newc
    MOV A, C                          ; A = Δrow
    CPI 01h
    JZ loc_ed_rd_vdown                ; вниз: newv=+4
    CPI 0FFh
    JZ loc_ed_rd_vup                  ; вверх: newv=0FCh (= -4)
    JMP loc_ed_snap                   ; |Δrow|>1 -> мгновенно
loc_ed_rd_vdown:
    MVI A, 04h
    STA var_ed_newv
    JMP loc_ed_erase
loc_ed_rd_vup:
    MVI A, 0FCh
    STA var_ed_newv
    JMP loc_ed_erase
loc_ed_rd_legacy:
    ; A = Δrow (вход rowdiff). Ровно +1 вниз иначе snap.
    LDA var_ed_dr
    MOV C, A
    LDA var_ed_tr
    SUB C                             ; A = Δrow (tr-dr)
    CPI 01h
    JNZ loc_ed_snap                   ; подъём / >1 клетки -> snap
    LDA var_ed_dc
    MOV C, A
    LDA var_ed_tc
    SUB C
    JNZ loc_ed_snap                   ; одновременно со сменой колонки -> snap
    LDA var_ed_dr                     ; падение: остаёмся в dr, сдвиг 4 px вниз
    STA var_ed_newr
    LDA var_ed_dc
    STA var_ed_newc
    MVI A, 04h
    STA var_ed_newv
    XRA A
    STA var_ed_newh
    JMP loc_ed_erase
loc_ed_reanim:
    LDA var_ed_dr
    STA var_ed_newr
    LDA var_ed_dc
    STA var_ed_newc
    XRA A
    STA var_ed_newv
    STA var_ed_newh
    JMP loc_ed_erase
; Перекраска ПОКОЯЩЕГОСЯ погонщика: new := текущий disp (dr/dc, vo=ho=0 на покое).
; Координаты уже в var_ed_*, коды var_ed_gcodes загружены оверрайдом state==09.
; Выставляем repaint=1 и stash -> func_enemy_chaser_apply вызовет func_ed_draw_slot,
; который НЕПРОЗРАЧно переложит погонщика поверх героя (restore фона клетки + OR).
loc_ed_repaint_chaser:
    LDA var_ed_dr
    STA var_ed_newr
    LDA var_ed_dc
    STA var_ed_newc
    LDA var_ed_vo
    STA var_ed_newv
    LDA var_ed_ho
    STA var_ed_newh
    MVI A, 01h
    STA var_ch_repaint
    CALL func_ed_stash_chaser
    JMP loc_ed_done
; loc_ed_finish: (E1) убрана — «доехать» активный midpoint и snap к цели
; это одно и то же решение new=(tr,tc,0,0), наследие разветвления.
loc_ed_snap:
    LDA var_ed_tr
    STA var_ed_newr
    LDA var_ed_tc
    STA var_ed_newc
    XRA A
    STA var_ed_newv
    STA var_ed_newh
loc_ed_erase:
    ; E3-6a: пересборки композита в кадре нет — окна предсдвинуты на старте
    ; (func_enemy_prebuild), в кадре их только ищут (func_ed_find_pre в draw-теле).
    ; var_ed_same остаётся: он решает НАДО ли рисовать покой, а не что собирать.
    ; Применение решения (erase -> commit -> draw) вынесено в func_ed_apply_slot.
    ; ДВУХФАЗА (Hurry-up): погонщик НЕ рисуется здесь — его burst откладывается в
    ; func_enemy_chaser_apply ПОСЛЕ func_hero_render, иначе непрозрачный erase героя
    ; затирает погонщика. Обычные слоты (is_chaser==0) применяются как раньше.
    LDA var_ed_is_chaser
    ORA A
    JNZ loc_ed_defer
    CALL func_ed_apply_slot
    JMP loc_ed_done
loc_ed_defer:
    XRA A
    STA var_ch_repaint          ; move-burst: полный erase(src)->commit->draw(с restore dst)
    CALL func_ed_stash_chaser   ; var_ed_* -> var_ch_*; var_chaser_pending=1
loc_ed_done:
    POP H
    POP D
    POP B
    POP PSW
    RET

; Молча подтянуть отображение к цели (никаких отрисовок ВИДА) — для пассивных
; состояний 0 / 9 / 0Ah. Но если отображение ОТСТАЛО от цели, старый footprint
; всё-таки стирается (restore фона из буфера): иначе враг замрёт призраком в
; клетке отображения до конца уровня. Клетку цели не трогаем — если disp == цель,
; там уже нарисовано то, что нарисовала логика (egg-кадр / погонщик).
; КОДЫ НЕ КОММИТЯТСЯ: рендерер в этом слоте ничего не рисовал, поэтому кэш кодов
; (и, следом, композит E2) остаётся привязанным к последнему НАРИСОВАННОМУ виду.
; Выйти из 0/9/0Ah в 1..8 посреди уровня невозможно (09h/0Ah пишет только
; func_egg_caught, обратно — лишь func_level_loader, который вызывает init) —
; переспаун всегда пересевает кэш через func_enemy_render_init.
loc_ed_passive:
    ; Решение «подтянуть к цели» готовим ДО erase: func_ed_erase_old (E3-6b)
    ; смотрит на var_ed_new*, чтобы понять, какие колонки перекроет новая отрисовка.
    ; Здесь новое отображение всегда выровненное (newv=newh=0) и равно цели.
    LDA var_ed_tr
    STA var_ed_newr
    LDA var_ed_tc
    STA var_ed_newc
    XRA A
    STA var_ed_newv
    STA var_ed_newh
    ; disp == цель -> стирать нечего (клетку цели рисует логика)
    LDA var_ed_dr
    MOV C, A
    LDA var_ed_newr
    SUB C
    JNZ loc_ed_p_erase
    LDA var_ed_dc
    MOV C, A
    LDA var_ed_newc
    SUB C
    JZ loc_ed_p_commit
loc_ed_p_erase:
    CALL func_ed_erase_old
loc_ed_p_commit:
    CALL func_ed_commit_disp
    JMP loc_ed_done

; --- func_ed_apply_slot: применить решение, посчитанное в var_ed_* --------------
; Хвост func_enemy_render_slot, вынесенный без изменений: erase старого footprint
; (func_ed_erase_old) -> коммит disp+codes -> draw нового вида. Индекс var_ed_*
; (dr/dc/vo/ho/newr/newc/newv/newh/gcodes/is_chaser/slot) уже выставлен решением
; вызывающего; draw-тело опирается только на память, живых регистров не несёт.
; Регистры прозрачны: PUSH/POP PSW,B,D,H. Вызывается из func_enemy_render_slot и из
; func_enemy_chaser_apply (отложенный burst погонщика).
func_ed_apply_slot:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    CALL func_ed_erase_old
    POP H
    POP D
    POP B
    POP PSW
    ; Полный burst (erase+draw): сначала стирание старого footprint, затем хвост.
    JMP func_ed_draw_slot

; --- func_ed_draw_slot: commit disp/codes + draw NEW-вида ------------------------
; Хвост func_ed_apply_slot. Вызывается также из func_enemy_chaser_apply напрямую для
; перекраски НЕПОДВИЖНОГО погонщика: каждый кадр ПОСЛЕ героя заново наложить спрайт
; по текущему disp (new*=disp, commit идемпотентен).
; НЕПРОЗРАЧНОСТЬ ПОГОНЩИКА: OR-композит умеет только ДОБАВЛЯТЬ биты, поэтому биты
; героя, попавшие в окно погонщика, OR не стирает -> спрайты сливались (жалоба
; «герой затирает погонщика», зонд probe_chaser_overlay: потеря битов 0, объединение 76).
; Поэтому перед OR-отрисовкой для ПОГОНЩИКА (is_chaser!=0) восстанавливаем фон 2x2
; ТЕКУЩЕЙ клетки из текстового буфера (func_draw_tile_at_ptr): стираем пиксели героя
; в окне, оставляем чистый лабиринт, сверху OR-им спрайт. Итог: погонщик целый, герой
; аккуратно обрезан его квадратом (приоритет погонщика). Обычные враги НЕ трог
; уются (у них плоский непрозрачный блит func_render_tile_vram). Рег. прозрачны.
func_ed_draw_slot:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    ; --- погонщик: непрозрачная подложка — restore фона destination 2x2 (ho=vo=0
    ;     на покойной перекраске; на move-кадре src уже стёр erase_old'ом) ---
    LDA var_ed_is_chaser
    ORA A
    JZ loc_ed_ds_nobuf
    LDA var_ed_newr
    CPI 18h                         ; вне поля — не рисуем и не трог
    JNC loc_ed_ds_nobuf
    STA var_ed_erase_rc
    LDA var_ed_newc
    STA var_ed_erase_rc+1
    LXI H, var_ed_erase_rc
    CALL func_draw_tile_at_ptr      ; восстановить лабиринт под клеткой погонщика
loc_ed_ds_nobuf:
    CALL func_ed_commit_disp
    CALL func_ed_commit_codes
    ; --- draw: вертикальный сдвиг = вычесть ЗНАКОВЫЙ newv из var_screen_mode на
    ; время блита. newv=04h -> mode-4 (вниз); newv=0FCh -> mode-FCh = mode+4 (вверх)
    ; по дополнительному коду, поэтому ветка по знаку НЕ нужна — SUB/ADD симметричны.
    LDA var_ed_newv
    ORA A
    JZ loc_ed_draw
    MOV C, A
    LDA var_screen_mode
    SUB C
    STA var_screen_mode
loc_ed_draw:
    LDA var_ed_newr                 ; E3: инвариант строки (см. шапку) — draw берёт
    CPI 18h                         ;   строки newr и newr+1, вне поля не рисуем
    JNC loc_ed_post
    LDA var_ed_newh
    ORA A
    JZ loc_ed_drawa                 ; hoff=0 -> выровненно
    CALL func_ed_find_pre           ; E3-6a: готовое окно для var_ed_gcodes (HL)
    ORA A
    JNZ loc_ed_drawa                ;   окна нет -> этот кадр выровненно (без easing)
    JMP loc_ed_draw3
loc_ed_drawa:
    LDA var_ed_newc
    MOV D, A
    LDA var_ed_newr
    MOV E, A
    LXI H, var_ed_gcodes            ; «тайл-графика» = забранные коды цели
    LDA var_ed_is_chaser
    ORA A
    JZ loc_ed_drawa_flat
    CALL func_render_tile_vram_or   ; погонщик: OR-композит поверх стен (маска П0=entry+24)
    JMP loc_ed_post
loc_ed_drawa_flat:
    CALL func_render_tile_vram      ; обычная (не OR) перерисовка 4 глифов
    JMP loc_ed_post
loc_ed_draw3:
    ; HL = окно из var_enemy_pre_keys (его сюда вернул func_ed_find_pre); между
    ; поиском и blit3 регистр HL не затирается (только LDA/MOV в D и E).
    LDA var_ed_newh
    CPI 02h                         ; hoff=2 -> base = col-1 (окно col-1..col+1)
    JNZ loc_ed_d1
    LDA var_ed_newc
    SUI 01h
    JMP loc_ed_dset
loc_ed_d1:
    LDA var_ed_newc                 ; hoff=1 -> base = col (окно col..col+2)
loc_ed_dset:
    MOV D, A
    LDA var_ed_newr
    MOV E, A
    LDA var_ed_is_chaser
    ORA A
    JZ loc_ed_d3_flat
    CALL func_render_tile_vram_or3   ; погонщик: OR 3 колонки из предсдвинутого окна
    JMP loc_ed_post
loc_ed_d3_flat:
    CALL func_ed_blit3              ; обычный (не OR) блит 6 готовых фрагментов
loc_ed_post:
    LDA var_ed_newv
    ORA A
    JZ loc_ed_ap_done
    MOV C, A
    LDA var_screen_mode
    ADD C
    STA var_screen_mode             ; восстановить режим экрана
loc_ed_ap_done:
    POP H
    POP D
    POP B
    POP PSW
    RET

; --- func_ed_stash_chaser: переписать контекст применения погонщика в var_ch_* ---
; Вызывается из func_enemy_render_slot, когда var_ed_is_chaser!=0: решение уже в
; var_ed_*, снимки старого disp (dr/dc/vo/ho) тоже. Копируем всё, что нужно
; func_ed_apply_slot, и выставляем var_chaser_pending, чтобы func_enemy_chaser_apply
; доделал burst после героя (иначе непрозрачный erase героя затирает погонщика).
func_ed_stash_chaser:
    LDA var_ed_slot
    STA var_ch_slot
    LDA var_ed_dr
    STA var_ch_dr
    LDA var_ed_dc
    STA var_ch_dc
    LDA var_ed_vo
    STA var_ch_vo
    LDA var_ed_ho
    STA var_ch_ho
    LDA var_ed_newr
    STA var_ch_newr
    LDA var_ed_newc
    STA var_ch_newc
    LDA var_ed_newv
    STA var_ch_newv
    LDA var_ed_newh
    STA var_ch_newh
    LDA var_ed_is_chaser
    STA var_ch_is
    LDA var_ed_gcodes
    STA var_ch_gcodes
    LDA var_ed_gcodes+1
    STA var_ch_gcodes+1
    LDA var_ed_gcodes+2
    STA var_ch_gcodes+2
    LDA var_ed_gcodes+3
    STA var_ch_gcodes+3
    MVI A, 01h
    STA var_chaser_pending
    RET

; --- func_enemy_chaser_apply: отложенный burst погонщика (после func_hero_render) --
; Из главного цикла каждый кадр. Если погонщик был отложен (var_chaser_pending),
; восстановить var_ed_* из stash, отгвардить полосу погонщика и нарисовать:
;   * var_ch_repaint==0 (погонщик ДВИГАЛСЯ) — полный burst erase(src)->commit->draw;
;   * var_ch_repaint==1 (погонщик ПОКОИТСЯ, перекраска) — только commit+draw.
; В ОБОИХ случаях func_ed_draw_slot для погонщика сначала восстановит фон клетки
; (непрозрачная подложка), затем OR-нимает спрайт — иначе биты героя внутри окна
; погонщика не стирались бы и спрайты сливались.
; Если погонщика не было — мгновенный RET (обычные уровни byte-for-byte не затронуты).
; var_glyph_voff на время OR-draw обнуляется (твин героя не должен просочиться в
; позицию погонщика), затем восстанавливается — как на входе func_enemy_render.
func_enemy_chaser_apply:
    LDA var_chaser_pending
    ORA A
    RZ
    XRA A
    STA var_chaser_pending
    LDA var_ch_slot
    STA var_ed_slot
    LDA var_ch_dr
    STA var_ed_dr
    LDA var_ch_dc
    STA var_ed_dc
    LDA var_ch_vo
    STA var_ed_vo
    LDA var_ch_ho
    STA var_ed_ho
    LDA var_ch_newr
    STA var_ed_newr
    LDA var_ch_newc
    STA var_ed_newc
    LDA var_ch_newv
    STA var_ed_newv
    LDA var_ch_newh
    STA var_ed_newh
    LDA var_ch_is
    STA var_ed_is_chaser
    LDA var_ch_gcodes
    STA var_ed_gcodes
    LDA var_ch_gcodes+1
    STA var_ed_gcodes+1
    LDA var_ch_gcodes+2
    STA var_ed_gcodes+2
    LDA var_ch_gcodes+3
    STA var_ed_gcodes+3
    LDA var_glyph_voff
    STA var_ed_voff_sv
    XRA A
    STA var_glyph_voff
    ; Срез A: cost-hint = burst погонщика (1 tile draw + sparse erase) ~40 строк*96 = 0x0F00
    PUSH H
    LXI H, 0F00h
    SHLD var_raster_margin
    POP H
    CALL func_raster_guard_enemy
    LDA var_ch_repaint
    ORA A
    JNZ loc_cap_repaint
    CALL func_ed_apply_slot         ; погонщик двигался: erase старого + draw нового
    JMP loc_cap_after
loc_cap_repaint:
    CALL func_ed_draw_slot          ; покой: непрозрачная перекраска (restore+OR)
loc_cap_after:
    LDA var_ed_voff_sv
    STA var_glyph_voff
    RET

; --- хелперы -----------------------------------------------------------------
; ERASE старого footprint: restore фона ИЗ БУФЕРА. Ширина старого окна: 2 колонки,
; а при ho != 0 — 3 (base = dc-1 для ho=2); высота: 2 строки, а при vo != 0 ещё
; строка dr+1 (покрыть 4 px спила вниз). Зеркало erase героя.
; E3-6b: если обе отрисовки в тех же строках (vo=0, newv=0, dr=newr), восстанавливаются
; только колонки старого окна, НЕ перекрываемые новой отрисовкой (см. ЧАСТИЧНЫЙ ERASE
; внутри); иначе — полный erase по 2x2-вызовам func_draw_tile_at_ptr.
func_ed_erase_old:
    LDA var_ed_dr                   ; E3: инвариант строки (см. шапку): вне поля
    CPI 18h                         ;   рендерер ничего не рисовал, значит и стирать
    RNC                             ;   нечего; 17h не рисуем, т.к. берём пару dr/dr+1
    PUSH B
    PUSH D
    PUSH H
    LDA var_ed_dc
    STA var_ed_ebase
    LDA var_ed_ho
    CPI 02h
    JNZ loc_ed_eo_b1
    LDA var_ed_ebase
    SUI 01h
    STA var_ed_ebase                ; base = dc-1 (вид был сдвинут влево)
loc_ed_eo_b1:
    ; --- E3-6b: ЧАСТИЧНЫЙ ERASE -----------------------------------------------
    ; Restore фона нужен только там, куда НОВАЯ отрисовка не достала. Гарантированно
    ; перерисованные колонки = [newc, newc+1]: выровненный тайл рисуется и при newh=0,
    ; и при промахе поиска func_ed_find_pre (loc_ed_drawa) — на третью колонку
    ; blit3-окна опираться нельзя.
    ; Применяется, когда обе отрисовки идут в тех же двух строках (vo=0, newv=0,
    ; dr=newr); при вертикальном easing полоса не совпадает -> полный erase ниже.
    ; Экономия: midpoint-кадр (старое окно = те же 2 колонки) не стирает НИЧЕГО
    ; (было 79 строк растра), «доезжаем»-кадр — 1 колонку (2 глифа вместо 8).
    ; Побочный эффект: под оверлей героя попадает меньше restore-вызовов.
    LDA var_ed_vo
    ORA A
    JNZ loc_ed_eo_full
    LDA var_ed_newv
    ORA A
    JNZ loc_ed_eo_full
    LDA var_ed_dr
    MOV C, A
    LDA var_ed_newr
    SUB C                             ; newr - dr
    JNZ loc_ed_eo_full
    ; C = ob + ow (конец старого окна), ow = 3 при ho != 0
    LDA var_ed_ebase
    MOV C, A
    LDA var_ed_ho
    ORA A
    JZ loc_ed_eo_w2
    INR C
    INR C
    INR C
    JMP loc_ed_eo_it
loc_ed_eo_w2:
    INR C
    INR C
loc_ed_eo_it:
    ; D = newc+2 — первая колонка ПРАВЕЕ нового окна (D сохраняет func_ed_erase_col)
    LDA var_ed_newc
    MVI D, 02h
    ADD D
    MOV D, A
    ; --- левый край: колонки [ob, min(newc, ob+ow)) ---
    LDA var_ed_ebase
    MOV B, A                          ; B = курсор колонки
loc_ed_eo_l1:
    MOV A, B
    CMP C                             ; col >= ob+ow -> влево больше нечего
    JNC loc_ed_eo_l2
    LDA var_ed_newc
    CMP B                             ; newc <= col -> колонка перерисована
    JC loc_ed_eo_l2                   ;   (C: newc < col, Z: newc == col)
    JZ loc_ed_eo_l2
    MOV A, B
    CALL func_ed_erase_col
    INR B
    JMP loc_ed_eo_l1
    ; --- правый край: колонки [max(newc+2, ob), ob+ow) ---
loc_ed_eo_l2:
    MOV B, D
    LDA var_ed_ebase
    CMP D                             ; ob < newc+2 -> старт с newc+2
    JC loc_ed_eo_r1
    MOV B, A                          ; иначе старт с ob (новое окно левее старого)
loc_ed_eo_r1:
    MOV A, B
    CMP C
    JNC loc_ed_eo_done
    CALL func_ed_erase_col            ; A = col
    INR B
    JMP loc_ed_eo_r1

; Полный erase: вертикальный easing либо смена строки (зеркало erase героя).
loc_ed_eo_full:
    ; строка dr: 2x2 @ (dr, base); если ho != 0 -> ещё 2x2 @ (dr, base+1)
    LDA var_ed_dr
    STA var_ed_erase_rc
    LDA var_ed_ebase
    STA var_ed_erase_rc+1
    LXI H, var_ed_erase_rc
    CALL func_draw_tile_at_ptr
    LDA var_ed_ho
    ORA A
    JZ loc_ed_eo_vo
    LDA var_ed_ebase
    INR A
    STA var_ed_erase_rc+1
    LXI H, var_ed_erase_rc
    CALL func_draw_tile_at_ptr
loc_ed_eo_vo:
    LDA var_ed_vo
    ORA A
    JZ loc_ed_eo_done
    ; строка спила: знак vo задаёт направление. vo>0 (04h) -> dr+1 (вниз),
    ; vo<0 (0FCh) -> dr-1 (вверх). Base erase выше покрыл dr,dr+1.
    ; 8080_strict: BIT нет, знак снимаем сравнением с 80h (borrow => |vo|<80h).
    CPI 80h
    JC loc_ed_eo_vdown                ; vo < 80h (положительный) -> спил вниз
    LDA var_ed_dr
    DCR A                             ; vo >= 80h (отрицательный) -> вверх (dr>=1)
    JMP loc_ed_eo_vset
loc_ed_eo_vdown:
    LDA var_ed_dr
    INR A                             ; vo>0 -> вниз
loc_ed_eo_vset:
    STA var_ed_erase_rc
    LDA var_ed_ebase
    STA var_ed_erase_rc+1
    LXI H, var_ed_erase_rc
    CALL func_draw_tile_at_ptr
    LDA var_ed_ho
    ORA A
    JZ loc_ed_eo_done
    LDA var_ed_ebase
    INR A
    STA var_ed_erase_rc+1
    LXI H, var_ed_erase_rc
    CALL func_draw_tile_at_ptr
loc_ed_eo_done:
    POP H
    POP D
    POP B
    RET

; --- func_ed_erase_col: restore фона ОДНОЙ колонки (2 строки) ------------------
; Вход A = колонка, строка берётся из var_ed_dr. В отличие от func_draw_tile_at_ptr
; (2x2, 4 глифа) рисует только нужные глифы: клетку (dr,col) и (dr+1,col). Тот же
; источник (текстовый буфер) и тот же примитив func_render_glyph, что у 2x2-варианта,
; поэтому побайтовый результат совпадает с «полным» erase на этих колонках.
; Меняет A/D/E/H/L, B и C сохраняет (курсор и границы цикла живёт в них).
func_ed_erase_col:
    PUSH B
    PUSH D
    PUSH H
    MOV D, A
    LDA var_ed_dr
    MOV E, A
    CALL func_coords_to_textbuf         ; HL = клетка (dr, col)
    MOV A, M
    CALL func_render_glyph
    LXI B, 0020h                        ; шаг строки текстового буфера. НЕ 001Fh как
                                        ; в func_draw_tile_at_ptr: там между глифами
                                        ; строки есть INX H, и 0x1F дополняет его до
                                        ; 32; здесь глиф на строку один, поэтому шаг
                                        ; берётся полным (иначе пишем (dr+1,col-1)).
    DAD B                               ; HL = клетка (dr+1, col)
    MOV A, M
    CALL func_render_glyph
    POP H
    POP D
    POP B
    RET

; Цель слота: var_ed_tr = ycoords[slot], var_ed_tc = xcoords[slot]; выход HL =
; адрес клетки цели в текстовом буфере (для func_ed_fetch_codes).
func_ed_target_cell:
    PUSH B
    LDA var_ed_slot
    LXI H, data_entity_ycoords
    CALL func_hl_add_a
    MOV A, M
    STA var_ed_tr
    LDA var_ed_slot
    LXI H, data_entity_xcoords
    CALL func_hl_add_a
    MOV A, M
    STA var_ed_tc
    MOV D, A                        ; D = колонка цели
    LDA var_ed_tr
    MOV E, A                        ; E = строка цели
    CALL func_coords_to_textbuf     ; HL = клетка цели в буфере
    POP B
    RET

; 4 кода тайла 2x2 по адресу клетки цели (HL) -> var_ed_gcodes. Обход клеток —
; как в func_draw_tile_to_buf: +0, +1, +32, +33.
func_ed_fetch_codes:
    PUSH D
    PUSH H
    LXI D, var_ed_gcodes
    MOV A, M
    STAX D
    INX D
    INX H
    MOV A, M
    STAX D
    INX D
    LXI B, 001Fh
    DAD B
    MOV A, M
    STAX D
    INX D
    INX H
    MOV A, M
    STAX D
    POP H
    POP D
    RET

; Совпадают ли var_ed_gcodes с кэшем слота -> A = 0 (равны) / 1 (разные).
func_ed_codes_same:
    PUSH B
    PUSH D
    PUSH H
    LDA var_ed_slot
    ADD A
    ADD A                           ; slot*4
    LXI H, var_enemy_disp_codes
    CALL func_hl_add_a              ; HL = кэш слота
    LXI D, var_ed_gcodes
    LDAX D
    CMP M
    JNZ loc_ed_diff
    INX D
    INX H
    LDAX D
    CMP M
    JNZ loc_ed_diff
    INX D
    INX H
    LDAX D
    CMP M
    JNZ loc_ed_diff
    INX D
    INX H
    LDAX D
    CMP M
    JNZ loc_ed_diff
    XRA A
    JMP loc_ed_cmp_done
loc_ed_diff:
    MVI A, 01h
loc_ed_cmp_done:
    POP H
    POP D
    POP B
    RET

; Коммит отображения: disp_rc[slot] = (var_ed_newr, var_ed_newc),
; disp_voff[slot] = var_ed_newv, disp_hoff[slot] = var_ed_newh.
func_ed_commit_disp:
    PUSH B
    PUSH H
    LDA var_ed_newr
    MOV C, A                        ; C = строка (первая в записи rc)
    LDA var_ed_newc
    MOV B, A                        ; B = колонка
    LDA var_ed_slot
    ADD A
    LXI H, var_enemy_disp_rc
    CALL func_hl_add_a
    MOV M, C
    INX H
    MOV M, B
    LDA var_ed_slot
    LXI H, var_enemy_disp_voff
    CALL func_hl_add_a
    LDA var_ed_newv
    MOV M, A
    LDA var_ed_slot
    LXI H, var_enemy_disp_hoff      ; E2
    CALL func_hl_add_a
    LDA var_ed_newh
    MOV M, A
    POP H
    POP B
    RET

; Коммит кэша кодов слота = var_ed_gcodes. Вызывать ТОЛЬКО вместе с реальным
; рисованием вида (и при init): кэш кодов = ключ актуальности композита E2.
func_ed_commit_codes:
    PUSH D
    PUSH H
    LDA var_ed_slot
    ADD A
    ADD A
    LXI H, var_enemy_disp_codes
    CALL func_hl_add_a              ; HL = кэш слота
    LXI D, var_ed_gcodes
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    POP H
    POP D
    RET

; --- func_ed_find_pre: готовое окно для кодов целевой клетки -------------------
; Вход: var_ed_gcodes = 4 кода (TL,TR,BL,BR). Выход: HL = 192-байтное окно,
; предсдвинутое на 4px вправо, и A=0; либо A=0FFh — окна нет, и вызывающий рисует
; ЭТОТ кадр выровненно (loc_ed_drawa). Так деградируют тайлы вне data_enemy_pre_tiles
; и записи, помеченные негодными из-за compact-глифа.
; Ключ записи n = var_enemy_pre_keys + n*8: [годно][код0][код1][код2][код3][pad x3].
; Адрес ключа пересчитывается из индекса (ADD A x3), поэтому частичное сравнение не
; надо «отматывать» назад; старший байт не меняется — таблица (8 записей по 8 байт)
; лежит в одной странице.
; Экономия: сравнение с первым кодом отсекает чужую запись одним CMP, все 4 кода
; смотрим только при совпадении первого. Полный промах по 8 записям ~4 строки
; растра (пересборка окна стоила 114).
; Меняет A/B/D/H/L, C сохраняет.
func_ed_find_pre:
    LXI H, var_enemy_pre_keys         ; H = старшая половина таблицы (постоянна)
    LDA var_enemy_pre_n
    MOV B, A                          ; записей построено на старте
    MVI D, 00h                        ; индекс записи
loc_fp_rec:
    MOV A, D
    CMP B
    JNC loc_fp_miss                   ; перебрали всё -> окна нет
    ADD A
    ADD A
    ADD A                             ; A = n*8 (шаг записи)
    MOV L, A
    MOV A, M                          ; байт «годно»
    ORA A
    JZ loc_fp_next
    INX H                             ; -> код0
    LDA var_ed_gcodes
    CMP M
    JNZ loc_fp_next
    INX H
    LDA var_ed_gcodes+1
    CMP M
    JNZ loc_fp_next
    INX H
    LDA var_ed_gcodes+2
    CMP M
    JNZ loc_fp_next
    INX H
    LDA var_ed_gcodes+3
    CMP M
    JZ loc_fp_hit
    ; --- не совпало: следующая запись ---
loc_fp_next:
    INR D
    JMP loc_fp_rec
    ; --- совпало: HL = data_enemy_shift_pre + n*192 ---
loc_fp_hit:
    LXI H, data_enemy_shift_pre
    MOV A, D
    ORA A
    JZ loc_fp_ok
    LXI B, 00C0h                      ; шаг окна = 192 байта
loc_fp_mul:
    PUSH PSW
    DAD B
    POP PSW
    DCR A
    JNZ loc_fp_mul
loc_fp_ok:
    XRA A                             ; 0 = попадание
    RET
loc_fp_miss:
    MVI A, 0FFh
    RET

; --- data_enemy_pre_tiles: тайлы, для которых на старте собирается окно --------
; Индексы записей data_tile_graphics, которые реально выдают состояния врагов 1..8
; (валидные индексы 00..14, хвост таблицы +54h.. не тайлы):
;   01h = data_tile_graphics+04h (клетка очищена: state1/2/4/6/7/8, score_and_redraw)
;   10h, 11h = +40h/+44h (state3..8: (var_page_flip+10h)*4 — кадр анимации шага)
;   13h = +4Ch (state2), 14h = +50h (state1)
; 0Fh, 12h — соседи по хвосту таблицы: окно дешёвое (сборка один раз на старте),
; а промах поиска стоит лишь один кадр без easing. 0FFh = стоп.
; 0F0h — sentinel: коды погонщика из data_tile_table_26DE[8], не из data_tile_graphics.
; Тайл, которого в списке нет, рисуется выровненно (не ошибка, просто без easing).
; При изменении списка синхронно проверяем разметку var_enemy_pre_keys (0x7E00,
; <=8 записей по 8 байт = 64 байта внутри одной страницы): число записей берётся из
; var_enemy_pre_n, но пока оно <=31, курсор поиска не меняет старший байт.
data_enemy_pre_tiles:
    DEFB 01h, 0Fh, 10h, 11h, 12h, 13h, 14h, 0F0h, 0FFh   ; 8 записей

; --- func_enemy_prebuild: собрать ВСЕ предсдвинутые окна врагов -----------------
; Вызывается ОДИН раз из func_main_init, до первого кадра. Для каждого индекса из
; data_enemy_pre_tiles: 4 кода тайла -> var_ed_gcodes, func_enemy_build_cache пишет
; 192 байта окна в приёмник, в ключ записи кладутся [годно][код0..код3].
; Если билдер увидел compact-глиф (var_ed_bc_compact), байт «годно» в записи
; обнуляется: окно остаётся лежать в таблице, но func_ed_find_pre на него не
; ссылается, и рендерер рисует выровненно — это перенесённая на старт проверка E3.
; Реальный такой случай в текущей графике: тайл 1 = data_tile_empty (коды 0x20,
; а 0x20 в data_glyph_ptr_table именно compact) -> его запись всегда негодна.
; Стоимость: ~8 окон x 114 строк = ~3 hw-кадра, один раз на заставке (вне игрового
; цикла и вне темпа игры). Прозрачность: сохраняет PSW/B/D/H.
func_enemy_prebuild:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    XRA A
    STA var_enemy_pre_n
    LXI H, data_enemy_pre_tiles
    LXI D, data_enemy_shift_pre        ; приёмник окна
    LXI B, var_enemy_pre_keys         ; приёмник ключа (шаг 8 байт)
loc_epb_tile:
    MOV A, M                          ; индекс тайла
    CPI 0FFh
    JZ loc_epb_done
    PUSH H                            ; курсор списка
    PUSH D                            ; приёмник окна
    PUSH B                            ; приёмник ключа
    ; --- 0F0h: погонщик, коды из data_tile_table_26DE[8] ---
    CPI 0F0h
    JZ loc_epb_chaser
    ; --- HL = data_tile_graphics + idx*4, его 4 кода -> var_ed_gcodes ---
    ADD A
    ADD A
    MOV L, A
    MVI H, 00h
    LXI B, data_tile_graphics
    DAD B
    LXI B, var_ed_gcodes
    MOV A, M
    STAX B
    INX H
    INX B
    MOV A, M
    STAX B
    INX H
    INX B
    MOV A, M
    STAX B
    INX H
    INX B
    MOV A, M
    STAX B
    XRA A
    STA var_ed_bc_or              ; обычный враг: вакуум маски = 0 (плоский блит)
    JMP loc_epb_lddone
loc_epb_chaser:
    LXI H, data_tile_table_26DE + 8 * 4
    LXI B, var_ed_gcodes
    MOV A, M
    STAX B
    INX H
    INX B
    MOV A, M
    STAX B
    INX H
    INX B
    MOV A, M
    STAX B
    INX H
    INX B
    MOV A, M
    STAX B
    MVI A, 01h
    STA var_ed_bc_or              ; погонщик: окно нужно для OR (вакуум маски = 1)
loc_epb_lddone:
    POP B
    POP D
    POP H
    CALL func_enemy_build_cache       ; DE = приёмник окна, коды в var_ed_gcodes
    ; Погонщик рисуется OR-композитом, поэтому его предсдвинутое окно должно иметь
    ; вакуум МАСКИ (П0) = 1 на освобождённых 4px-крайках (сохранить фон), как у героя;
    ; билдер оставил вакуум = 0 во всех плоскостях (расчёт на плоский блит). Правим
    ; только маски frag0/frag2 (верх) и frag3/frag5 (низ); DE = база окна (билдер
    ; восстанавливает DE), сохранны для шага цикла loc_epb_step.
    LDA var_ed_bc_or
    ORA A
    JZ loc_epb_noor
    CALL loc_epb_orfill               ; DE = база окна; OR фикс вакуума маски
loc_epb_noor:
    ; Ключ записи пишем ВСЕГДА (таблица саморасшифруема для отладчика), а байт
    ; «годно» — по флагу compact. Форма явная (LDA -> ORA A -> JZ): ORA A пересчитывает
    ; Z из уже загруженного значения, поэтому результат не зависит от того, переживёт
    ; ли флаг следующая MVI. На 8080 MVI флаги не трогает и короткий вариант
    ; (LDA / MVI A,01h / JZ) тоже был бы корректен, но он читается как зависящий от
    ; тонкости системы флагов — здесь экономии на этом нет (дело один раз на старте).
    LDA var_ed_bc_compact
    ORA A
    JZ loc_epb_good
    XRA A
    STAX B                          ; негодно: был compact-глиф (приёмник ключа — BC,
    JMP loc_epb_codes               ;   НЕ HL: HL здесь курсор списка тайлов)
loc_epb_good:
    MVI A, 01h
    STAX B
loc_epb_codes:
    INX B
    LDA var_ed_gcodes
    STAX B
    INX B
    LDA var_ed_gcodes+1
    STAX B
    INX B
    LDA var_ed_gcodes+2
    STAX B
    INX B
    LDA var_ed_gcodes+3
    STAX B
loc_epb_step:
    ; курсоры вперёд: ключ +8 (маской — из любой точки записи), окно +192, список +1
    MOV A, C
    ANI 0F8h
    ADI 08h
    MOV C, A                          ; B не меняется: таблица в одной странице
    MOV A, E
    ADI 0C0h
    MOV E, A
    MOV A, D
    ACI 00h
    MOV D, A
    INX H
    LDA var_enemy_pre_n
    INR A
    STA var_enemy_pre_n
    JMP loc_epb_tile
loc_epb_done:
    POP H
    POP D
    POP B
    POP PSW
    RET

; --- loc_epb_orfill: довести окно погонщика до OR-формата ---------------------
; Вход: DE = база окна (192 Б = 6 фрагментов по 32 Б; маска П0 = фрагмент+24).
; func_enemy_build_cache оставил вакуум = 0 во всех плоскостях (обычный блит).
; Для OR освобождённый nibble МАСКИ обязан = 1 (сохранить фон), как в
; func_build_hero_shift_cache: ЛЕВЫЙ nibble крайних левых колонок (frag0/frag3)
; = 0xF0, ПРАВЫЙ nibble крайних правых (frag2/frag5) = 0x0F. Средняя колонка
; (frag1/frag4) целиком перекрыта — не трогаем. Цветовые плоскости не правим:
; освобождённый nibble цвета = 0 корректен (фон под OR сохраняется маской).
; Смещения масок от базы окна: frag0 +24, frag2 +88, frag3 +120, frag5 +184
; (порядок обхода окон: TL,TR,правый-верх / BL,BR,правый-низ;row0 +0..95,row1 +96..191).
; Сохраняет PSW,B,D,H (цикл держит базу окна в DE, курсор списка в HL, ключ в BC);
; внутри сломит только A,C,HL.
loc_epb_orfill:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    XCHG                              ; HL = база окна (была в DE)
    LXI B, 0018h
    DAD B                             ; +24  -> маска frag0
    MVI C, 0F0h
    CALL loc_epb_or8                  ; HL |= C ×8; HL->+8 (=+32)
    LXI B, 0038h
    DAD B                             ; +56  -> +88  маска frag2
    MVI C, 00Fh
    CALL loc_epb_or8                  ; HL->+8 (=+96)
    LXI B, 0018h
    DAD B                             ; +24  -> +120 маска frag3
    MVI C, 0F0h
    CALL loc_epb_or8                  ; HL->+8 (=+128)
    LXI B, 0038h
    DAD B                             ; +56  -> +184 маска frag5
    MVI C, 00Fh
    CALL loc_epb_or8                  ; HL->+8 (=+192)
    POP H
    POP D
    POP B
    POP PSW
    RET

; --- loc_epb_or8: (HL) |= C, 8 байт; HL += 8. Лобит A,HL; B,C,D целые. --------
loc_epb_or8:
    MOV A, M
    ORA C
    MOV M, A
    INX H
    MOV A, M
    ORA C
    MOV M, A
    INX H
    MOV A, M
    ORA C
    MOV M, A
    INX H
    MOV A, M
    ORA C
    MOV M, A
    INX H
    MOV A, M
    ORA C
    MOV M, A
    INX H
    MOV A, M
    ORA C
    MOV M, A
    INX H
    MOV A, M
    ORA C
    MOV M, A
    INX H
    MOV A, M
    ORA C
    MOV M, A
    INX H
    RET

; --- func_ed_resolve_glyph: код глифа -> адрес его записи ---------------------
; Вход A = код. Выход HL = адрес записи (слово data_glyph_ptr_table со снятым
; тегом compactness). Меняет A/D/E/HL/флаги, BC и PSW сохраняет (кодер ниже
; держит в B сумматор шага плоскости). Запись = raw: 4 плоскости по 8 байт.
; E3: если код COMPACT (тег=1 — только маска плоскости 0, остальные плоскости
; рендерер пишет нулями), билдер композита
; прочитал бы плоскости 1..3 из соседней записи -> выставляем var_ed_bc_compact,
; диспетчер draw на этот кадр откажется от кэша в пользу выровненного блита.
; Побочный эффект по RAM (только var_ed_bc_compact) безвреден: функцию зовёт
; исключительно func_enemy_build_cache, который обнуляет флаг на входе.
func_ed_resolve_glyph:
    PUSH PSW
    ADD A                             ; DE = 2*код (смещение в таблице указателей)
    MOV E, A
    MVI A, 00h
    ADC A
    MOV D, A
    LXI H, data_glyph_ptr_table
    DAD D
    MOV A, M                          ; мл. байт слова (бит0 = тег compact)
    MOV D, A                          ; D = словоцело (тег ещё на месте, DE свободен)
    ANI 01h                           ; E3: compact?
    JZ loc_rg_addr                    ;   raw -> флаг не трогаем
    MVI A, 01h
    STA var_ed_bc_compact
loc_rg_addr:
    MOV A, D
    ANI 0FEh                          ; снять тег
    MOV E, A
    INX H
    MOV A, M                          ; ст. байт
    MOV H, A
    MOV L, E                          ; HL = адрес записи
    POP PSW
    RET

; --- func_enemy_build_cache: композит 3 колонок для 4 кодов тайла --------------
; Вход: DE = приёмник (192 байта), var_ed_gcodes (4 кода тайла 2x2: TL,TR,BL,BR).
; Выход: 192 байт по [DE] — 6 фрагментов (3 колонки x 2 строки) по 32 байта
; (4 плоскости x 8), вид, сдвинутый НА 4px ВПРАВО от выравнивания. Направление
; задаёт вызывающий базовой колонкой блита, поэтому композит ОДИН на оба направления
; (как у героя, Step 2b). DE вызывающего восстановлено на выходе (PUSH/POP D).
;
; АРИФМЕТИКА (бит7 = левый пиксель, колонки VRAM растут влево->вправо): для пары
; исходных глифов строки (L в col, R в col+1) три колонки окна:
;   frag0 = L>>4                      ; левый nibble L уехал вправо, вакуум = 0
;   frag1 = ((L AND 0F)<<4) | (R>>4)  ; перелив через границу колонки
;   frag2 = (R&0F)<<4                 ; правый nibble R, вакуум = 0
; У героя освобождённый nibble маски = 1 (сохранить фон под OR-оверлеем); здесь
; перерисовка ОБЫЧНАЯ, поэтому вакуум = 0 во всех четырёх плоскостях — освобождённые
; пиксели становятся чёрным фоном (заодно затирая остатки старого вида).
;
; Реализация: по 4 прохода на плоскость, каждый проход = 8 байт с ОДНИМ источником
; и одним приёмником (пары регистров DE=источник, HL=приёмник), поэтому третья
; ссылка не нужна: (sr) frag0 = L>>4; (sl) frag1 = (L&0F)<<4; (or sr) frag1 |= R>>4;
; (sl) frag2 = (R&0F)<<4.
; E3-6a: вызывается ТОЛЬКО func_enemy_prebuild со старта (по разу на тайл списка);
; в кадровом пути его заменил поиск окна func_ed_find_pre.
; Прозрачность: PUSH/POP PSW/B/D/H.
func_enemy_build_cache:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    XRA A
    STA var_ed_bc_compact             ; флаг compact сбрасывается на каждой сборке
    XCHG                              ; HL = приёмник окна (из DE вызывающего)
    SHLD var_ed_bc_dst0
    XRA A
    STA var_ed_bc_row                 ; строка тайла: 0 = верх (TL/TR), 1 = низ
gbc_row:
    ; --- источники строки: pL = запись кода [row*2], pR = [row*2+1] ---
    LDA var_ed_bc_row
    ADD A
    MOV L, A
    MVI H, 00h
    LXI D, var_ed_gcodes
    DAD D
    MOV A, M
    CALL func_ed_resolve_glyph
    SHLD var_ed_bc_pL
    LDA var_ed_bc_row
    ADD A
    INR A
    MOV L, A
    MVI H, 00h
    LXI D, var_ed_gcodes
    DAD D
    MOV A, M
    CALL func_ed_resolve_glyph
    SHLD var_ed_bc_pR
    ; --- приёмник строки: dst0 + row*96 ---
    LHLD var_ed_bc_dst0
    LDA var_ed_bc_row
    ORA A
    JZ loc_gbc_dst
    LXI B, 0060h
    DAD B
loc_gbc_dst:
    SHLD var_ed_bc_dst
    XRA A
    STA var_ed_bc_pl                  ; плоскость 0..3 (в записи глифа блоки подряд)
gbc_plane:
    ; frag0 = L>>4
    LHLD var_ed_bc_pL
    XCHG
    LHLD var_ed_bc_dst
    CALL loc_eb_emit_sr
    ; frag1 = (L AND 0F)<<4
    LHLD var_ed_bc_pL
    XCHG
    LHLD var_ed_bc_dst
    LXI B, 0020h
    DAD B
    CALL loc_eb_emit_sl
    ; frag1 |= R>>4
    LHLD var_ed_bc_pR
    XCHG
    LHLD var_ed_bc_dst
    LXI B, 0020h
    DAD B
    CALL loc_eb_or_sr
    ; frag2 = (R AND 0F)<<4
    LHLD var_ed_bc_pR
    XCHG
    LHLD var_ed_bc_dst
    LXI B, 0040h
    DAD B
    CALL loc_eb_emit_sl
    ; --- шаг на следующую плоскость: все три указателя +8 ---
    LXI B, 0008h
    LHLD var_ed_bc_pL
    DAD B
    SHLD var_ed_bc_pL
    LHLD var_ed_bc_pR
    DAD B
    SHLD var_ed_bc_pR
    LHLD var_ed_bc_dst
    DAD B
    SHLD var_ed_bc_dst
    LDA var_ed_bc_pl
    INR A
    CPI 04h
    JZ loc_gbc_row_next
    STA var_ed_bc_pl
    JMP gbc_plane
loc_gbc_row_next:
    LDA var_ed_bc_row
    INR A
    CPI 02h
    JZ loc_gbc_done
    STA var_ed_bc_row
    JMP gbc_row
loc_gbc_done:
    POP H
    POP D
    POP B
    POP PSW
    RET

; --- проходы билдера: 8 байт источник(DE) -> приёмник(HL), оба +8 -------------
; dest = src >> 4 (освободившийся левый nibble = 0)
loc_eb_emit_sr:
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    MOV M, A
    INX D
    INX H
    RET

; dest = (src AND 0F) << 4 (освободившийся правый nibble = 0)
loc_eb_emit_sl:
    LDAX D
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC
    MOV M, A
    INX D
    INX H
    LDAX D
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC
    MOV M, A
    INX D
    INX H
    LDAX D
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC
    MOV M, A
    INX D
    INX H
    LDAX D
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC
    MOV M, A
    INX D
    INX H
    LDAX D
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC
    MOV M, A
    INX D
    INX H
    LDAX D
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC
    MOV M, A
    INX D
    INX H
    LDAX D
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC
    MOV M, A
    INX D
    INX H
    LDAX D
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC
    MOV M, A
    INX D
    INX H
    RET

; dest |= src >> 4 (дорасчёт средней колонки: перелив правого глифа)
loc_eb_or_sr:
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    ORA M
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    ORA M
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    ORA M
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    ORA M
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    ORA M
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    ORA M
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    ORA M
    MOV M, A
    INX D
    INX H
    LDAX D
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh
    ORA M
    MOV M, A
    INX D
    INX H
    RET

; --- func_ed_blit3: обычный (не OR) блит 3 колонок из кэша --------------------
; Вход: HL = база 6 фрагментов (192 Б, порядок TL,TR,правый / BL,BR,правый),
;       D = базовая колонка, E = строка. Контракт как у func_render_tile_vram_or3,
;       только композиция прямая (без маски): пиксели вне спрайта = 0 = фон.
; hoff=1 -> caller даёт D=col (колонки col,col+1,col+2); hoff=2 -> D=col-1.
; func_ed_blit_frag сохраняет DE/HL, поэтому здесь шагают только вызывающий:
; DE на +32 (XCHG-парой), HL по клеткам +1, +1, затем +0x1E в (col, row+1).
; Прозрачность: PUSH/POP PSW,B (D/H — входы).
func_ed_blit3:
    PUSH PSW
    PUSH B
    PUSH H
    CALL func_coords_to_textbuf     ; HL = адрес базовой клетки в буфере
    POP D                           ; DE = база фрагментов
    CALL func_ed_blit_frag          ; frag0 (col,   row)
    XCHG
    LXI B, 0020h
    DAD B
    XCHG                            ; DE -> frag1
    INX H
    CALL func_ed_blit_frag          ; frag1 (col+1, row)
    XCHG
    LXI B, 0020h
    DAD B
    XCHG                            ; DE -> frag2
    INX H
    CALL func_ed_blit_frag          ; frag2 (col+2, row)
    XCHG
    LXI B, 0020h
    DAD B
    XCHG                            ; DE -> frag3
    LXI B, 001Eh
    DAD B                           ; HL -> (col, row+1)
    CALL func_ed_blit_frag          ; frag3 (col,   row+1)
    XCHG
    LXI B, 0020h
    DAD B
    XCHG                            ; DE -> frag4
    INX H
    CALL func_ed_blit_frag          ; frag4 (col+1, row+1)
    XCHG
    LXI B, 0020h
    DAD B
    XCHG                            ; DE -> frag5
    INX H
    CALL func_ed_blit_frag          ; frag5 (col+2, row+1)
    POP B
    POP PSW
    RET

; --- func_ed_blit_frag: прямой перенос одного готового фрагмента (32 Б) -------
; Вход: DE = фрагмент кэша, HL = клетка текстового буфера — приёмник. СОХРАНЯЕТ
; DE/HL (вызывающий двигает сам). Вычисление адреса приёмника и обход 4 плоскостей
; (шаг +0x2000) — один в один с raw-ветвью func_render_glyph, поэтому выровненный
; кадр (фрагменты = исходные глифы) побайтно совпал бы с func_render_tile_vram.
; var_screen_mode читается как есть -> вертикальный трюк E1 (mode -= voff) работает
; и здесь, хотя по лестнице решения voff и hoff никогда не бывают ненулевыми сразу.
; CLOBBERS: A,B,C,флаги.
func_ed_blit_frag:
    PUSH D
    PUSH H
    LXI B, textbuf_to_vram          ; HL = смещение клетки
    DAD B
    MOV A, L
    ANI 1Fh
    MOV C, A                        ; C = колонка
    MOV A, H
    RRC
    RRC
    ANI 0C0h
    MOV B, A
    MOV A, L
    RRC
    RRC
    ANI 38h
    ORA B
    MOV B, A                        ; B = rowbits
    MVI H, 00h
    MOV L, C
    PUSH B
    LXI B, data_vram_col_table
    DAD B
    MOV H, M                        ; H = база плоскости по колонке
    LDA var_screen_mode
    POP B
    SUB B
    MOV L, A                        ; HL = приёмник (первая плоскость)
    MVI B, 04h                      ; 4 плоскости
loc_ebf_plane:
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    ; шаг приёмника на следующую плоскость: +0x1FF8 (8 INX H уже дали +8)
    MOV A, L
    ADI 0F8h
    MOV L, A
    MOV A, H
    ACI 1Fh
    MOV H, A
    DCR B
    JNZ loc_ebf_plane
    POP H
    POP D
    RET
