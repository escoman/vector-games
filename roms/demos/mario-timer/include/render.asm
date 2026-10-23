;
; render.asm — примитивы вывода спрайта Марио для демки racing-the-beam.
; Идиомы циклов взяты из mario-16cols/mario.asm (проверенный hot path):
; короткие строковые циклы dcr b / jnz, xchg для загрузки DE, dcr e-поход
; по строкам убывающего адреса.
;
; Формат спрайта (gen_assets.py) — тайл-ПРЕФАБ: заголовок
; [wcells,hcells,hpix=32,nTiles], затем nTiles записей [pos]+8 троек
; (op,b0,b1): pos=(col<<2)|row, тайлы только с непустым содержимым.
; Столбец VRAM при росте y идёт по убывающему адресу:
; addr = base + col*0x100 + (255 - y), поэтому внутренний цикл =
; data += 3 (INX D), vram -= 1 (DCX H).
;
; Композиция: res = cur ^ ((cur ^ bit) & op). Пустые тайлы (op=0 во
; всех строках) не пишутся вовсе: res = cur — побитовый no-op.
;
; СУБ-ПИКСЕЛЬНОГО СДВИГА В ASM БОЛЬШЕ НЕТ. Проход frac=4 (tab2/pres,
; SBYTE-стейджинг 24 байта на тайл) удалён: все сдвинутые на 4 px варианты
; поз генерируются ОДИН РАЗ на старте ROM в RAM (main.c: sh_build_one ->
; sh_pool) в ТОМ ЖЕ формате префаба. main.c выбирает базовый префаб при
; x кратно 8 и предсдвинутый при x ≡ 4 (mod 8) — и вывод всегда идёт этим
; единым быстрым путём dr_tile (байты уже смержены, колонки уже +1).
;
; Глобалы (определены в main.c; asm читает/пишет напрямую):
;   _rs_spr   указатель на спрайт (заголовок)
;   _rs_p0    байт VRAM верха спрайта, плоскость бита0 (вес 1: E000/A000)
;   _rs_p1    то же для плоскости бита1 (вес 2: C000/8000) = p0 - 0x2000
;   _rs_zero  режим вывода: 0 = рисовать payload (draw), 1 = занулять те же
;             адреса, что рисовал draw (sparse erase). Стирание = вызов
;             mario_draw_sprite с _rs_zero=1 на данных ПРОШЛОГО спрайта
;             (того же — базового или предсдвинутого; footprint совпадает).
;
; Примитивы инициализации (замена медленных C-циклов, ~5 c -> ~0.3 c):
;   mario_fill_ground    — тайл земли 224..255 во все 4 плоскости,
;                          указатель tile_ground передаётся в _rs_spr;
;   mario_copy_AB        — копия буфера A -> B (E000->A000, C000->8000,
;                          2 блока по 8 КБ, ручной цикл — плоскости непрерывны).
;
; Геометрия ниже зеркалит main.c (GROUND_TOP=224; ROWS=32 = MARIO_HPIX).
;

        SECTION code_clib
        PUBLIC  _mario_draw_sprite
        PUBLIC  _mario_fill_ground
        PUBLIC  _mario_copy_AB

        EXTERN  _rs_spr
        EXTERN  _rs_p0
        EXTERN  _rs_p1
        EXTERN  _rs_zero

; --- рабочие переменные тайл-префаба (mario_draw_sprite) ---
;   Спрайт = [wcells,hcells,hpix,nTiles] + nTiles записей [pos]+8 троек.
;   pos = (col<<2)|row. Рисуем только присутствующие тайлы (dr_tile).
        SECTION bss_clib
dt_rec:     defw    0      ; курсор текущей записи тайла (src)
dt_nc:      defb    0      ; счётчик оставшихся записей
dt_v0:      defw    0      ; VRAM-курсор тайла, плоскость бита0
dt_v1:      defw    0      ; VRAM-курсор тайла, плоскость бита1

; --- рабочие переменные примитивов инициализации (не видны из C) ---
fg_tile:    defw    0         ; база tile_ground
fg_cur:     defw    0         ; курсор колонки E000 (+0x100 на колонку)

; --- геометрия инициализации (зеркало main.c) ---
NCOLS      EQU 32            ; колонок экрана (256/8)
GROUND_OFS EQU 31            ; 255 - GROUND_TOP: адрес байта верха земли
GROUND_ROWS EQU 32           ; строк земли (224..255)

; ---------------------------------------------------------------
; void mario_draw_sprite(void)
;   Нарисовать (rs_zero=0) или СПАРСНО стереть (rs_zero=1) весь спрайт
;   (_rs_spr) в пару плоскостей _rs_p0/_rs_p1. Колонки заданы в
;   x-выравнивании по сетке 8 px — побайтовые записи.
; ---------------------------------------------------------------
        SECTION code_clib
_mario_draw_sprite:
        lhld    _rs_spr               ; HL = заголовок префаба
        inx     h                     ; [1]=hcells
        inx     h                     ; [2]=hpix
        inx     h                     ; [3]=nTiles
        mov     a,m
        sta     dt_nc
        inx     h                     ; [4]=старт записей тайлов
        shld    dt_rec

; -----------------------------------------------------------------
; dr_tile — единственный путь вывода: цикл по присутствующим тайлам.
;   Для записи pos: col=pos>>2, row=pos&3, delta=row*8.
;   VRAM0 = _rs_p0 + col*0x100 - delta ; VRAM1 = _rs_p1 + то же.
;   col добавляется в старший байт (0x100/col), delta вычитается из
;   младшего с займом в старший (dcr h). Рисуем 8 строк dr_p0 / dr_p1.
; -----------------------------------------------------------------
dr_tile:
        lda     dt_nc
        ora     a
        jz      dr_ret
        lhld    dt_rec
        mov     a,m                   ; pos
        mov     e,a                   ; сохранить pos
        ani     03h                   ; row
        rlc
        rlc
        rlc                           ; delta = row*8
        mov     d,a                   ; D = delta
        mov     a,e                   ; pos
        ora     a                     ; CY=0
        rar
        rar                           ; col = pos>>2
        ani     0Fh
        mov     e,a                   ; E = col
        ; --- VRAM0 = _rs_p0 + col*0x100 - delta ---
        lhld    _rs_p0
        mov     a,h
        add     e                     ; H += col
        mov     h,a
        mov     a,l
        sub     d                     ; L -= delta (CY = заём)
        mov     l,a
        jnc     tv0
        dcr     h                     ; заём -> H--
tv0:    shld    dt_v0
        ; --- VRAM1 = _rs_p1 + col*0x100 - delta ---
        lhld    _rs_p1
        mov     a,h
        add     e
        mov     h,a
        mov     a,l
        sub     d
        mov     l,a
        jnc     tv1
        dcr     h
tv1:    shld    dt_v1
        ; --- вывод тайла: draw = payload, erase = 0 (тот же footprint) ---
        lda     _rs_zero
        ora     a
        jnz     dr_tile_z
        lhld    dt_rec
        inx     h
        xchg                          ; DE = данные тайла (pos+1)
        lhld    dt_v0
        call    dr_p0
        lhld    dt_rec
        inx     h
        xchg
        lhld    dt_v1
        call    dr_p1
        jmp     dr_tile_next
dr_tile_z:
        lhld    dt_v0
        call    dr_pz                 ; erase: занулить 8 строк без чтения данных
        lhld    dt_v1
        call    dr_pz
dr_tile_next:
        ; --- следующая запись ---
        lhld    dt_rec
        lxi     d,25
        dad     d
        shld    dt_rec
        lda     dt_nc
        dcr     a
        sta     dt_nc
        jmp     dr_tile
dr_ret:
        ret

; ---------------------------------------------------------------
; dr_p0 / dr_p1 — внутренний цикла одной колонки тайла (8 строк).
; Вход: HL = VRAM-курсор (верх колонки), DE = данные тайла.
; ЧИСТАЯ ЗАПИСЬ (без чтения VRAM): в схеме сплита плоскостей Mario живёт
;   в младших плоскостях E000/C000, которые ПРЕДВАРИТЕЛЬНО обнулены
;   (erase через dr_pz / gfx_fill_planes), поэтому cur==0 и полная
;   композиция res = cur ^ ((cur ^ bit) & op) выроджается в res = bit & op.
;   Убрали 2 чтения (xra m / mov a,m) и лишний ALU на байт -> ~2x быстрее
;   dr-цикла; весь erase+draw успевает закончиться до прихода луча.
; HL уменьшается (y+1), DE +3/строку.
; Выход: HL = низ колонки, DE = следующая колонка; Z-флаг не является
; частью интерфейса.
; ---------------------------------------------------------------
dr_p0:
        ; Ровно 8 строк: развёрнутый цикл устраняет DCR B/JNZ на каждой строке.
        ; row 0
        ldax    d
        mov     c,a
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        inx     d
        dcx     h
        ; row 1
        ldax    d
        mov     c,a
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        inx     d
        dcx     h
        ; row 2
        ldax    d
        mov     c,a
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        inx     d
        dcx     h
        ; row 3
        ldax    d
        mov     c,a
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        inx     d
        dcx     h
        ; row 4
        ldax    d
        mov     c,a
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        inx     d
        dcx     h
        ; row 5
        ldax    d
        mov     c,a
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        inx     d
        dcx     h
        ; row 6
        ldax    d
        mov     c,a
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        inx     d
        dcx     h
        ; row 7
        ldax    d
        mov     c,a
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        inx     d
        dcx     h
        ret

dr_p1:
        ; Ровно 8 строк: развёрнутый цикл.
        ; row 0
        ldax    d
        mov     c,a
        inx     d
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        dcx     h
        ; row 1
        ldax    d
        mov     c,a
        inx     d
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        dcx     h
        ; row 2
        ldax    d
        mov     c,a
        inx     d
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        dcx     h
        ; row 3
        ldax    d
        mov     c,a
        inx     d
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        dcx     h
        ; row 4
        ldax    d
        mov     c,a
        inx     d
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        dcx     h
        ; row 5
        ldax    d
        mov     c,a
        inx     d
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        dcx     h
        ; row 6
        ldax    d
        mov     c,a
        inx     d
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        dcx     h
        ; row 7
        ldax    d
        mov     c,a
        inx     d
        inx     d
        ldax    d
        inx     d
        ana     c
        mov     m,a
        dcx     h
        ret

; ---------------------------------------------------------------
; dr_pz — erase-вариант внутреннего цикла одной колонки: занулить 8 строк
;   тайла в одной плоскости (шаг адреса -1, как dr_p0/dr_p1). НЕ читает
;   данные тайла; footprint (адреса) точно совпадает с dr_p0/dr_p1, поэтому
;   стирание убирает ровно то, что поставил прошлый draw.
; Вход: HL = VRAM-курсор верха тайла. Выход: HL = низ тайла.
; ---------------------------------------------------------------
dr_pz:
        mvi     a, 0
        mov     m, a
        dcx     h
        mov     m, a
        dcx     h
        mov     m, a
        dcx     h
        mov     m, a
        dcx     h
        mov     m, a
        dcx     h
        mov     m, a
        dcx     h
        mov     m, a
        dcx     h
        mov     m, a
        dcx     h
        ret

; ---------------------------------------------------------------
; mario_zero_sprite (плотное стирание прямоугольником ROWS×колонок) УДАЛЁН.
; Стирание прежнего Mariо теперь идёт через mario_draw_sprite с _rs_zero=1:
; тот же обход тайл-префаба, но dr_pz пишет 0 в те же адреса, что рисовал
; dr_p0/dr_p1. Footprint стирания == footprint отрисовки -> младшие плоскости
; (E000/C000) снова чисты перед рисованием нового, призраков нет, а пустые
; клетки внутри bounding box больше не затираются (экономия растра).
; ---------------------------------------------------------------

; ---------------------------------------------------------------
; void mario_fill_ground(void)
;   Тайл земли (16 байт: 32 строки x 2 плоскости А, шаг 2) — во все 4
;   плоскости, строки 224..255, все 32 колонки. Плоскости B — те же
;   данные (фон одинаков в A и B; копия на всякий случай делается и
;   mario_copy_AB, здесь пишем сразу 4 плоскости).
;   Вход: _rs_spr = tile_ground. Строка y => адрес base + col*100 + (255-y),
;   т.е. внутри колонки строки идут по убывающему адресу (DCX H),
;   а строки тайла — по возрастающему (INX DE, INX DE — шаг 2).
; ---------------------------------------------------------------
        SECTION code_clib
_mario_fill_ground:
        lhld    _rs_spr
        shld    fg_tile
        lxi     h,0E000h
        shld    fg_cur
        mvi     c,NCOLS                 ; счётчик колонок
fg_col:
        ; ---- 4 прогона: (смещение плоскости, смещение в тайле) ----
        lhld    fg_cur                  ; w1 -> E000, tile+0
        mvi     a,0
        call    fg_run
        lhld    fg_cur                  ; w2 -> C000 = cur+0E000 (wrap)
        lxi     d,0E000h
        dad     d
        mvi     a,1
        call    fg_run
        lhld    fg_cur                  ; w4 -> A000 = cur+0C000, tile+0
        lxi     d,0C000h
        dad     d
        mvi     a,0
        call    fg_run
        lhld    fg_cur                  ; w8 -> 8000 = cur+0A000, tile+1
        lxi     d,0A000h
        dad     d
        mvi     a,1
        call    fg_run
        ; ---- следующая колонка ----
        lhld    fg_cur
        lxi     d,0100h
        dad     d
        shld    fg_cur
        dcr     c
        jnz     fg_col
        ret

; HL = база колонки плоскости, A = смещение в паре байтов тайла (0/1).
; Пишет GROUND_ROWS байтов: tile[ofs],tile[ofs+2],... в (HL+31),(HL+30),...
fg_run:
        lxi     d,GROUND_OFS
        dad     d                       ; HL = адрес верхней строки земли
        push    h                       ; сохранить VRAM-курсор
        mov     e,a
        mvi     d,0
        lhld    fg_tile
        dad     d                       ; HL = tile + смещение
        xchg                            ; DE = источник тайла
        pop     h                       ; HL = VRAM-курсор
        mvi     b,GROUND_ROWS
fg_row:
        ldax    d
        mov     m,a
        inx     d
        inx     d                       ; шаг пары байтов (плоскость w1/w2)
        dcx     h                       ; строка y+1 => адрес -1
        dcr     b
        jnz     fg_row
        ret

; ---------------------------------------------------------------
; void mario_copy_AB(void)
;   Копия буфера A -> B. Столбцы VRAM идут подряд (блок = 0x100),
;   поэтому вся плоскость — непрерывные 8 КБ (32 блока): E000->A000,
;   C000->8000. Источник — HL, приёмник — DE (STAX D пишет в (DE)!).
;   Копируем ручным циклом (MOV A,M / STAX D / INX): LDIR — Z80-команда,
;   ядро заявлено как КР580ВМ80А, поддержку ED B0 в эмуляторе проверить
;   нельзя; 8080-цикл стоит ~70 T/байт, на 16 КБ это ~0.3 c — терпимо.
; ---------------------------------------------------------------
        SECTION code_clib
_mario_copy_AB:
        lxi     h,0E000h                ; HL = источник (буфер A)
        lxi     d,0A000h                ; DE = приёмник (буфер B)
        mvi     b,020h                  ; 32 x 256 = 8 КБ
        call    cp_block
        lxi     h,0C000h
        lxi     d,08000h
        mvi     b,020h
        call    cp_block
        ret

; Копировать B*256 байт: (HL) -> (DE). C — внутренний счётчик (256).
cp_block:
        mvi     c,0
cp_inner:
        mov     a,m
        stax    d
        inx     d
        inx     h
        dcr     c
        jnz     cp_inner
        dcr     b
        jnz     cp_block
        ret

; ---------------------------------------------------------------
; УДАЛЕНО вместе с рантайм-сдвиг frac=4: mario_init_renderer/zcol,
; rec_build (tab2/pres_buf), SBYTE-стейджер (ds_buf/ds_*), проход
; drs_start..drs_col. Их работа переехала в генератор предсдвигов на
; старте ROM (main.c sh_build_one) — asm видит только готовые префабы.
; mario_capture_patch / mario_erase_sprite удалены ранее: в схеме сплита
; по плоскостям фон живёт в старших (A000/8000), Mariо — в младших
; (E000/C000), стирание = обнуление следа (_rs_zero=1), слепок не нужен.
; ---------------------------------------------------------------
