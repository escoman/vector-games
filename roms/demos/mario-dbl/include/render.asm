;
; render.asm — примитивы вывода спрайта Марио для double-buffering демки.
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
; всех строках) не пишутся вовсе: res = cur — побитовый no-op; frac=0
; их просто нет в данных, frac=4 пропускает пары пустых соседних тайлов.
;
; Глобалы (определены в main.c; asm читает/пишет напрямую):
;   _rs_spr   указатель на спрайт (заголовок), только mario_draw_sprite
;   _rs_data  старт блока данных текущей колонки (считает сам asm)
;   _rs_p0    байт VRAM верха спрайта, плоскость бита0 (вес 1: E000/A000)
;   _rs_p1    то же для плоскости бита1 (вес 2: C000/8000) = p0 - 0x2000
;   _rs_s0    старт относительного патча для _rs_p0 (плоскость бита0), erase/capture
;   _rs_s1    старт относительного патча для _rs_p1 (плоскость бита1), erase/capture
;   _rs_cols  знаковый счётчик колонок: от -wcells до 0
;   _rs_frac  суб-клеточный сдвиг: 0 = выровнен по сетке 8px (быстрый путь,
;             побайтовая композиция), 4 = сдвиг вправо на 4px — каждая тетрада
;             выходного байта собирается из двух соседних клеток спрайта
;             (старший nibble <- младший nibble левой клетки,
;              младший nibble <- старший nibble текущей).
;
; Примитивы инициализации (замена медленных C-циклов, ~5 c -> ~0.3 c):
;   mario_fill_ground    — тайл земли 224..255 во все 4 плоскости,
;                          указатель tile_ground передаётся в _rs_spr;
;   mario_copy_AB        — копия буфера A -> B (E000->A000, C000->8000,
;                          2 блока по 8 КБ, ручной цикл — плоскости непрерывны);
;   mario_capture_patch — слепок прямоугольника под НОВЫМ спрайтом из
;                          VRAM-буфера в относительный патч (источник для erase).
;
; Геометрия ниже зеркалит main.c (GROUND_TOP=224; ROWS=32 = MARIO_HPIX).
; Патч относительный: байт = relcol*ROWS + row, старт = верх-лево пятна,
; шаг колонки = ROWS (32). Менять синхронно с main.c.
;

        SECTION code_clib
        PUBLIC  _mario_draw_sprite
        PUBLIC  _mario_erase_sprite
        PUBLIC  _mario_fill_ground
        PUBLIC  _mario_copy_AB
        PUBLIC  _mario_capture_patch

        EXTERN  _rs_spr
        EXTERN  _rs_data
        EXTERN  _rs_p0
        EXTERN  _rs_p1
        EXTERN  _rs_s0
        EXTERN  _rs_s1
        EXTERN  _rs_cols
        EXTERN  _rs_frac

ROWS EQU 32                 ; строк спрайта (hcells=4 x CELL=8)

; --- геометрия инициализации (зеркало main.c) ---
NCOLS      EQU 32            ; колонок экрана (256/8)
GROUND_OFS EQU 31            ; 255 - GROUND_TOP: адрес байта верха земли
GROUND_ROWS EQU 32           ; строк земли (224..255)

;
; Рабочие переменные примитивов инициализации (не видны из C).
;
        SECTION bss_clib
fg_tile:    defw    0         ; база tile_ground
fg_cur:     defw    0         ; курсор колонки E000 (+0x100 на колонку)

; --- рабочие переменные сдвига тетрады (mario_draw_sprite, frac=4) ---
;   Плитный стейджинг: ds_buf хранит ОДИН тайл сдвинутой колонки (24 B =
;   8 троек op/b0/b1), заполняется 24 SBYTE-макросами: HL прибит к &ds_t,
;   OR идёт mov m,a / add m (без push/pop), запись в ds_buf — фиксированные
;   sta+ofs (HL больше не курсор), счётчик строк не нужен.
ds_ncols:   defb    0         ; wcells (ширина спрайта в клетках)
ds_cc:      defb    0         ; счётчик колонок вывода (wcells+1 .. 0)
ds_t:       defb    0         ; временный накопитель nibble-OR (через ADD M)
ds_buf:     defs    24        ; staged-тайл (8 троек), формат = payload записи
        ; Нулевой блок-клетка (96 байт = 4 нуля-тайла 8x8) для отсутствующих
        ; соседей: клетка слева от 0-й и cur для spill-колонки справа.
        ; Обнуляется в начале drs_start (секция bss при --no-crt не зануляется).
zcol:       defs    96

; --- рабочие переменные тайл-префаба (mario_draw_sprite) ---
;   Спрайт = [wcells,hcells,hpix,nTiles] + nTiles записей [pos]+8 троек.
;   pos = (col<<2)|row. frac=0 рисует только присутствующие тайлы (dr_tile);
;   frac=4 стейджерит и рисует тайлами через таблицу указателей tab2.
MAXWC   EQU 4              ; запас по ширине (макс wcells=3)
dt_rec:     defw    0      ; курсор текущей записи тайла (src)
dt_nc:      defb    0      ; счётчик оставшихся записей
dt_v0:      defw    0      ; VRAM-курсор тайла, плоскость бита0
dt_v1:      defw    0      ; VRAM-курсор тайла, плоскость бита1
rbi:        defb    0      ; строящийся слот (col*4+row)
rb_cnt:     defb    0      ; оставшихся слотов (wcells*4)
rb_dst:     defw    0      ; временное: 16-бит значение для записи в (HL)

; --- frac=4 tile-цикл: указатели тайлов и presence ---
;   pres_buf[j]: 1 = тайл присутствует. [0..3]=sentinel (prev кол.0),
;   [4+k*4+r]=слот (k,r); хвост [4+wc*4..]=0 — пустые тайлы spill-колонки.
;   tab2[j] (defw): адрес данных тайла; предзаполнение = zcol+(j&3)*24
;   (нулевой тайл), для присутствующих слотов — адрес payload записи.
;   Курсоры колонки k: prev = tab2+k*8, cur = tab2+(k+1)*8 — сами идут
;   +2/тайл и +4 записи/колонку (prev след. колонки = cur текущей).
ds_td:      defb    0      ; VRAM-delta тайла: 0,8,16,24
ds_tc:      defb    0      ; счётчик тайлов 4..0 (dr_p0 clobbers B/C — память)
ds_ctab:    defw    0      ; курсор defw-записи tab2 для cur-тайла
ds_ptab:    defw    0      ; курсор defw-записи tab2 для prev-тайла
ds_pres_p:  defw    0      ; курсор prev pres-байтов (шаг +1/тайл)
ds_pres_c:  defw    0      ; курсор cur pres-байтов
pres_buf:   defs    (MAXWC + 2) * 4
tab2:       defs    (MAXWC + 2) * 8

; ---------------------------------------------------------------
; void mario_draw_sprite(void)
;   Нарисовать весь спрайт (_rs_spr) в пару плоскостей _rs_p0/_rs_p1.
;   Колонки заданы в x-выравнивании по сетке 8 px — побайтовые записи.
; ---------------------------------------------------------------
        SECTION code_clib
_mario_draw_sprite:
        lhld    _rs_spr               ; HL = заголовок префаба
        mov     a,m                   ; [0]=wcells
        sta     ds_ncols              ; ширина (нужна frac=4 и реконструкции)
        inx     h                     ; [1]=hcells
        inx     h                     ; [2]=hpix
        inx     h                     ; [3]=nTiles
        mov     a,m
        sta     dt_nc
        inx     h                     ; [4]=старт записей тайлов
        shld    dt_rec
        lda     _rs_frac
        ora     a
        jnz     rec_build             ; frac!=0 -> сборка tab2/pres + tile-drs

; -----------------------------------------------------------------
; dr_tile — быстрый путь frac=0: цикл по присутствующим тайлам.
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
        ; --- плоскость 0 ---
        lhld    dt_rec
        inx     h
        xchg                          ; DE = данные тайла (pos+1)
        lhld    dt_v0
        mvi     b,8
        call    dr_p0
        ; --- плоскость 1 ---
        lhld    dt_rec
        inx     h
        xchg
        lhld    dt_v1
        mvi     b,8
        call    dr_p1
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

; -----------------------------------------------------------------
; rec_build — frac=4 подготовка: построить таблицу указателей тайлов
;   tab2 и карту присутствия pres_buf. Идём по слотам 0..wcells*4-1
;   (row-мажорно): если следующая запись pos==slot — tab2[4+slot] =
;   адрес payload записи, pres=1, запись += 25; иначе слот сохраняет
;   предзаполненный указатель нулевого тайла (zcol + (slot&3)*24).
;   Копирований нет: стейджер читает байты записей напрямую по указателям.
; -----------------------------------------------------------------
rec_build:
        ; --- занулить pres_buf ((MAXWC+2)*4 = 24 B): sentinel/хвост/пустые ---
        lxi     h, pres_buf
        mvi     b, (MAXWC + 2) * 4
        mvi     a, 0
rb_zpres:
        mov     m, a
        inx     h
        dcr     b
        jnz     rb_zpres
        ; --- tab2[0..3] = zcol + {0,24,48,72} (указатели нуля-тайлов) ---
        lxi     h, tab2
        lxi     d, zcol
        mov     m, e
        inx     h
        mov     m, d
        inx     h
        lxi     d, zcol+24
        mov     m, e
        inx     h
        mov     m, d
        inx     h
        lxi     d, zcol+48
        mov     m, e
        inx     h
        mov     m, d
        inx     h
        lxi     d, zcol+72
        mov     m, e
        inx     h
        mov     m, d
        inx     h
        ; --- период 8 B: размножить tab2[0..7] в 5 следующих блоков (24 defw) ---
        mvi     b, 5
        lxi     h, tab2+8
rb_blk:
        mvi     c, 8
        lxi     d, tab2
rb_byt:
        ldax    d
        mov     m, a
        inx     d
        inx     h
        dcr     c
        jnz     rb_byt
        dcr     b
        jnz     rb_blk
        ; --- обход слотов: count = wcells*4 ---
        lda     ds_ncols
        rlc
        rlc
        sta     rb_cnt
        mvi     a, 0
        sta     rbi
rb_loop:
        lda     rb_cnt
        ora     a
        jz      rb_done
        lda     dt_nc
        ora     a
        jz      rb_done               ; записи кончились: остаток — нуль-тайлы
        lhld    dt_rec
        mov     a, m                  ; pos
        mov     b, a
        lda     rbi
        cmp     b                     ; slot == pos ?
        jnz     rb_adv                ; нет — оставляем предзаполненный указатель
        ; --- присутствует: pres_buf[4+slot]=1; tab2[4+slot]=dt_rec+1 ---
        lda     rbi
        mov     e, a
        mvi     d, 0
        lxi     h, pres_buf+4
        dad     d
        mvi     m, 1
        lhld    dt_rec
        inx     h
        shld    rb_dst                ; значение = адрес payload тайла
        lda     rbi
        mov     l, a
        mvi     h, 0
        dad     h                     ; HL = 2*slot
        lxi     d, tab2+8
        dad     d                     ; HL = &tab2[4+slot]
        lda     rb_dst
        mov     m, a
        inx     h
        lda     rb_dst+1
        mov     m, a
        ; --- запись += 25 ---
        lhld    dt_rec
        lxi     d, 25
        dad     d
        shld    dt_rec
        lda     dt_nc
        dcr     a
        sta     dt_nc
rb_adv:
        lda     rbi
        inr     a
        sta     rbi
        lda     rb_cnt
        dcr     a
        sta     rb_cnt
        jmp     rb_loop
rb_done:
        jmp     drs_start

; ---------------------------------------------------------------
; dr_p0 / dr_p1 — внутренний цикл одной колонки, вызывается и из
; быстрого пути (dr_col), и из сдвинутого (после набора ds_buf).
; Вход: HL = VRAM-курсор (верх колонки), DE = данные колонки,
;   B = счётчик строк (ROWS=32). Побайтовая композиция
;   res = vram ^ ((vram ^ bit) & op). HL уменьшается (y+1), DE +3/строку.
; Выход: HL = низ колонки, DE = следующая колонка, B=0; Z=1.
; ---------------------------------------------------------------
dr_p0:
        ldax    d                     ; op
        mov     c,a
        inx     d                     ; -> b0
        ldax    d                     ; b0
        inx     d                     ; -> b1 (в этом проходе не нужен)
        xra     m                     ; b0 ^ cur
        ana     c                     ; & op          = diff
        mov     c,a                   ; diff в C (op больше не нужен)
        mov     a,m                   ; cur
        xra     c                     ; res = cur ^ diff
        mov     m,a                   ; запись в плоскость
        inx     d                     ; -> op следующей строки
        dcx     h                     ; y+1 => адрес -1
        dcr     b
        jnz     dr_p0
        ret

dr_p1:
        ldax    d                     ; op
        mov     c,a
        inx     d                     ; пропуск b0
        inx     d                     ; -> b1
        ldax    d                     ; b1
        inx     d                     ; -> op следующей строки
        xra     m                     ; b1 ^ cur
        ana     c                     ; & op          = diff
        mov     c,a
        mov     a,m                   ; cur
        xra     c                     ; res
        mov     m,a
        dcx     h                     ; y+1 => адрес -1
        dcr     b
        jnz     dr_p1
        ret

; ---------------------------------------------------------------
; SBYTE — макро-конструктор одного байта сдвинутой колонки.
;   A = (cur >> 4) | (prev << 4);  запись в ds_buf+ofs;  DE,BC += 1.
; HL должен указывать на &ds_t и НЕ двигается в makro'е —
; therefore OR идёт напрямую (mov m,a пишет prev<<4 в (HL),
; add m читает обратно ds_t и складывает с cur>>4), без push/pop.
; ---------------------------------------------------------------
SBYTE   MACRO   ofs
        ldax    b                     ; prev byte
        rlc
        rlc
        rlc
        rlc
        ani     0F0h                  ; high nibble = prev<<4
        mov     m,a                   ; (HL)=ds_t = prev<<4
        ldax    d                     ; cur byte
        rrc
        rrc
        rrc
        rrc
        ani     0Fh                   ; low nibble = cur>>4
        add     m                     ; A = (cur>>4)+(prev<<4) == OR
        sta     ds_buf+ofs            ; фиксированный адрес, HL не трогаем
        inx     b
        inx     d
        ENDM

; ---------------------------------------------------------------
; Сдвиг тетрады (frac=4) — tile-стейджинг: вывод спрайта со сдвигом
; вправо на 4px за один обход тайлов (без плотной реконструкции).
;
; Выходной байт клетки col+j собирается из двух клеток спрайта:
;   low  nibble <- high nibble клетки j     (cur >> 4)
;   high nibble <- low  nibble клетки j-1   (prev << 4)
; j пробегает 0..wcells (wcells+1 колонок): слева prev=zcol, справа для
; spill-колонки cur=zcol (шлёпки tab2 sentinel/хвост указывают на
; нуля-тайлы zcol). 8080 не имеет сдвига на 4 — делаем 4x RRC/RLC.
;
; ds_tloop идёт по 4 тайлам колонки:
;   pres_prev|pres_cur оба нуля -> пропускаем и стейджинг, и вывод
;   (staged op заведомо 0, результат побитово = полный проход);
;   иначе стейдим 24 байта в ds_buf (24 SBYTE, источники — payload
;   записей по указателям tab2) и рисуем 8 строк dr_p0/dr_p1 (B=8).
; ---------------------------------------------------------------
drs_start:
        ; --- занулить zcol (96 байт): bss при --no-crt не инициализирован ---
        lxi     h, zcol
        mvi     a, 0
        mvi     c, 96
drs_zclr:
        mov     m, a
        inx     h
        dcr     c
        jnz     drs_zclr
        ; --- cc = wcells + 1 (колонок вывода) ---
        lda     ds_ncols
        mov     c, a
        inr     c
        mov     a, c
        sta     ds_cc
        ; --- курсоры tab2: prev = sentinel [0..3], cur = слоты [4..] ---
        lxi     h, tab2
        shld    ds_ptab
        lxi     h, tab2+8
        shld    ds_ctab
        ; --- pres-курсоры: prev = sentinel[0..3], cur = pres_buf+4 (col 0) ---
        lxi     h, pres_buf
        shld    ds_pres_p
        lxi     h, pres_buf+4
        shld    ds_pres_c

drs_col:
        ; --- начало колонки: 4 тайла, delta=0 ---
        mvi     a, 4
        sta     ds_tc
        mvi     a, 0
        sta     ds_td
ds_tloop:
        lhld    ds_pres_p             ; pres_prev[r] | pres_cur[r]
        mov     a, m
        lhld    ds_pres_c
        ora     m
        jz      ds_tskip              ; оба тайла пусты -> нечего стейдить
        ; --- стейджинг 24 B: cur-тайл -> DE ---
        lhld    ds_ctab               ; HL = *ctab (payload записи или zcol-тайл)
        mov     a, m
        inx     h
        mov     h, m
        mov     l, a
        xchg                          ; DE = src cur
        ; --- prev-тайл -> BC ---
        lhld    ds_ptab               ; HL = *ptab
        mov     a, m
        inx     h
        mov     h, m
        mov     l, a
        mov     b, h
        mov     c, l                  ; BC = src prev
        lxi     h, ds_t               ; накопитель, HL стоит весь стейджинг
        SBYTE   0
        SBYTE   1
        SBYTE   2
        SBYTE   3
        SBYTE   4
        SBYTE   5
        SBYTE   6
        SBYTE   7
        SBYTE   8
        SBYTE   9
        SBYTE   10
        SBYTE   11
        SBYTE   12
        SBYTE   13
        SBYTE   14
        SBYTE   15
        SBYTE   16
        SBYTE   17
        SBYTE   18
        SBYTE   19
        SBYTE   20
        SBYTE   21
        SBYTE   22
        SBYTE   23
        ; ---- VRAM-курсоры: dt_v0/v1 = _rs_p0/p1 - delta (заём -> dcr h) ----
        lhld    _rs_p0
        lda     ds_td
        mov     e, a
        mov     a, l
        sub     e
        mov     l, a
        jnc     dsv0
        dcr     h
dsv0:   shld    dt_v0
        lhld    _rs_p1
        lda     ds_td
        mov     e, a
        mov     a, l
        sub     e
        mov     l, a
        jnc     dsv1
        dcr     h
dsv1:   shld    dt_v1
        ; ---- вывод 8 строк плоскость 0 ----
        lxi     d, ds_buf
        lhld    dt_v0
        mvi     b, 8
        call    dr_p0
        ; ---- плоскость 1 ----
        lxi     d, ds_buf
        lhld    dt_v1
        mvi     b, 8
        call    dr_p1
ds_tskip:
        lda     ds_td                 ; delta += 8
        adi     8
        sta     ds_td
        lhld    ds_ctab               ; tab-курсоры += 2 (defw; за колонку +8
        inx     h                     ; = 4 записи, prev след. кол. = cur текущей)
        inx     h
        shld    ds_ctab
        lhld    ds_ptab
        inx     h
        inx     h
        shld    ds_ptab
        lhld    ds_pres_p             ; pres-курсоры += 1
        inx     h
        shld    ds_pres_p
        lhld    ds_pres_c
        inx     h
        shld    ds_pres_c
        lda     ds_tc
        dcr     a
        sta     ds_tc
        jnz     ds_tloop

        ; ---- следующая колонка: VRAM += 0x100 (курсоры tab/pres уже смещены) ----
        lda     _rs_p0+1
        inc     a
        sta     _rs_p0+1
        lda     _rs_p1+1
        inc     a
        sta     _rs_p1+1
        lda     ds_cc
        sui     1
        sta     ds_cc
        jnz     drs_col
        ret

; ---------------------------------------------------------------
; void mario_erase_sprite(void)
;   Вернуть фон: копировать ROWS строк относительного патча (_rs_s0/_rs_s1)
;   в плоскости (_rs_p0/_rs_p1) по _rs_cols (знаковый счётчик) колонкам.
;   Шаг: VRAM +0x100 (блок), патч +ROWS = 0x20 ( колонок идут подряд по 32 Б).
; ---------------------------------------------------------------
        SECTION code_clib
_mario_erase_sprite:
er_col:
        ; -------- плоскость бита 0: s0 (патч) -> p0 --------
        lhld    _rs_s0                ; HL = патч -> после XCHG DE = патч (источник)
        xchg
        lhld    _rs_p0                ; HL = VRAM (приёмник)
        mvi     b,ROWS
er_row0:
        ldax    d
        mov     m,a
        inx     d                     ; патч: y+1 => адрес +1
        dcx     h                     ; VRAM: y+1 => адрес -1
        dcr     b
        jnz     er_row0

        ; -------- плоскость бита 1: s1 (патч) -> p1 --------
        lhld    _rs_s1
        xchg
        lhld    _rs_p1
        mvi     b,ROWS
er_row1:
        ldax    d
        mov     m,a
        inx     d
        dcx     h
        dcr     b
        jnz     er_row1

        ; ------------------- следующая колонка -------------------
        lhld    _rs_s0
        lxi     d,0020h
        dad     d                       ; патч += ROWS (0x20)
        shld    _rs_s0
        lhld    _rs_s1
        dad     d
        shld    _rs_s1
        lhld    _rs_p0
        lxi     d,0100h
        dad     d                       ; VRAM += 0x100 (блок)
        shld    _rs_p0
        lhld    _rs_p1
        dad     d
        shld    _rs_p1
        lda     _rs_cols
        inc     a
        sta     _rs_cols
        jnz     er_col
        ret

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
; void mario_capture_patch(void)
;   Слепок прямоугольника под НОВЫМ спрайтом: копировать ROWS строк
;   из плоскостей (_rs_p0/_rs_p1) в относительный патч (_rs_s0/_rs_s1)
;   по _rs_cols (знаковый счётчик) колонкам. Вызывается ПОСЛЕ erase
;   (старый спрайт стёрт -> в VRAM чистый фон) и ДО draw_sprite.
;   Источник (VRAM) — по убывающему адресу, приёмник (патч) — по
;   возрастающему: ldax d / mov m,a / dcx d / inx h.
;   Шаг колонки: VRAM += 0x100 (блок), патч += ROWS (32).
; ---------------------------------------------------------------
        SECTION code_clib
_mario_capture_patch:
cpc_col:
        ; -------- плоскость бита 0: p0 (VRAM) -> s0 (патч) --------
        lhld    _rs_p0
        xchg                            ; DE = VRAM (источник)
        lhld    _rs_s0                  ; HL = патч (приёмник)
        mvi     b,ROWS
cpc_row0:
        ldax    d                       ; a = VRAM-байт
        mov     m,a                     ; -> патч
        dcx     d                       ; VRAM: y+1 => адрес -1
        inx     h                       ; патч:  y+1 => адрес +1
        dcr     b
        jnz     cpc_row0

        ; -------- плоскость бита 1: p1 -> s1 --------
        lhld    _rs_p1
        xchg
        lhld    _rs_s1
        mvi     b,ROWS
cpc_row1:
        ldax    d
        mov     m,a
        dcx     d
        inx     h
        dcr     b
        jnz     cpc_row1

        ; ------------------- следующая колонка -------------------
        lhld    _rs_p0
        lxi     d,0100h
        dad     d                       ; VRAM += 0x100 (блок)
        shld    _rs_p0
        lhld    _rs_p1
        dad     d
        shld    _rs_p1
        lhld    _rs_s0
        lxi     d,0020h
        dad     d                       ; патч += ROWS (32)
        shld    _rs_s0
        lhld    _rs_s1
        dad     d
        shld    _rs_s1
        lda     _rs_cols
        inc     a
        sta     _rs_cols
        jnz     cpc_col
        ret
