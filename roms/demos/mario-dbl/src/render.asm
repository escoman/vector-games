;
; render.asm — примитивы вывода спрайта Марио для double-buffering демки.
; Идиомы циклов взяты из mario-16cols/mario.asm (проверенный hot path):
; короткие строковые циклы dcr b / jnz, xchg для загрузки DE, dcr e-поход
; по строкам убывающего адреса.
;
; Формат спрайта (gen_assets.py): заголовок [wcells,hcells,hpix=32],
; далее КОЛОНОЧНЫЕ тройки (op,b0,b1): для каждой клетки-столбца — 32
; пиксель-строки подряд (шаг 3 байта). Столбец VRAM при росте y идёт
; по убывающему адресу: addr = base + col*0x100 + (255 - y),
; поэтому внутренний цикл = data += 3 (INX D), vram -= 1 (DCX H).
;
; Композиция: res = cur ^ ((cur ^ bit) & op). Строка пишется ВСЕГДА
; (даже при op=0): результат тогда равен cur — запись идентичного
; значения в скрытую (замаскированную палитрой) плоскость безопасна
; и дешевле ветвления.
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
;   Стратегия «В-чистовой»: сдвинутую колонку (32×{op,b0,b1}) собрать
;   один раз в ds_buf (96 B), затем прогнать её через тот же быстрый
;   путь dr_p0/dr_p1, что и обычные спрайты. drs_stage полностью
;   unroll'ен на 96 SBYTE-макросов: HL прибит к &ds_t, OR идёт через
;   mov m,a / add m (без push/pop), запись в ds_buf — фиксированные
;   sta+ofs (HL больше не курсор), счётчик строк не нужен.
ds_ncols:   defb    0         ; wcells (ширина спрайта в клетках)
ds_cc:      defb    0         ; счётчик колонок вывода (wcells+1 .. 0)
ds_cptr:    defw    0         ; база данных текущей клетки (cur)
ds_pptr:    defw    0         ; база данных соседней клетки (prev, слева)
ds_t:       defb    0         ; временный накопитель nibble-OR (через ADD M)
ds_buf:     defs    96        ; сдвинутая колонка (32 тройки op/b0/b1),
                              ; формат идентичен обычным данным спрайта
        ; Нулевой блок-клетка (96 байт) для отсутствующего соседа: клетка
        ; слева от 0-й и cur для spill-колонки справа. Обнуляется в начале
        ; drs_start (секция bss при --no-crt не зануляется).
zcol:       defs    96

; --- рабочие переменные тайл-префаба (mario_draw_sprite) ---
;   Спрайт = [wcells,hcells,hpix,nTiles] + nTiles записей [pos]+8 троек.
;   pos = (col<<2)|row. frac=0 рисует только присутствующие тайлы (dr_tile);
;   frac=4 реконструирует плотные колонки в dr_scr и гоняет штатный drs.
MAXWC   EQU 4              ; запас по ширине (макс wcells=3)
dt_rec:     defw    0      ; курсор текущей записи тайла (src)
dt_nc:      defb    0      ; счётчик оставшихся записей
dt_v0:      defw    0      ; VRAM-курсор тайла, плоскость бита0
dt_v1:      defw    0      ; VRAM-курсор тайла, плоскость бита1
rbi:        defb    0      ; текущий слот реконструкции (col*4+row)
rb_cnt:     defb    0      ; оставшихся слотов (wcells*4)
rb_dst:     defw    0      ; курсор записи в dr_scr (плотные колонки)
; плотная реконструкция: заголовок[3] + MAXWC*96 (dr_scr = указатель для drs)
dr_scr:     defs    3 + (MAXWC * 96)

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
        jnz     rec_build             ; frac!=0 -> плотная реконструкция + drs

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
; rec_build — frac=4: разложить тайлы обратно в ПЛОТНЫЕ колонки
;   (dr_scr = заголовок[3] + wcells*96), затем штатный drs_stage.
;   Идём по всем слотам 0..wcells*4-1 (row-мажорно, col=slot>>2):
;   если следующая запись=pos==slot — копируем 24 байта, иначе 0.
;   Умножений нет: dst растёт на 24/слот, presence = сравнение pos/slot.
;   Результат dr_scr побайтово равен исходным колончатым данным.
; -----------------------------------------------------------------
rec_build:
        lhld    _rs_spr               ; переложить заголовок [0..2]
        mov     a,m
        sta     dr_scr                ; [0]=wcells
        inx     h
        mov     a,m
        sta     dr_scr+1
        inx     h
        mov     a,m
        sta     dr_scr+2
        ; слотов = wcells*4
        lda     ds_ncols
        rlc
        rlc
        sta     rb_cnt
        mvi     a,0
        sta     rbi
        lxi     h, dr_scr+3
        shld    rb_dst
rb_loop:
        lda     rb_cnt
        ora     a
        jz      rb_done
        lda     dt_nc
        ora     a
        jz      rb_zero               ; записи кончились — остаток нули
        lhld    dt_rec
        mov     a,m                   ; pos
        mov     b,a
        lda     rbi
        cmp     b                     ; slot == pos ?
        jnz     rb_zero
        ; присутствует: DE=dt_rec+1 (src), HL=rb_dst (dst), 24 байта
        lhld    dt_rec
        inx     h
        xchg                          ; DE = src
        lhld    rb_dst
        call    copy24
        ; dt_rec += 25 ; dt_nc--
        lhld    dt_rec
        lxi     d,25
        dad     d
        shld    dt_rec
        lda     dt_nc
        dcr     a
        sta     dt_nc
        jmp     rb_adv
rb_zero:
        lhld    rb_dst
        call    zero24
rb_adv:
        lhld    rb_dst                ; dst += 24
        lxi     d,24
        dad     d
        shld    rb_dst
        lda     rbi
        inr     a
        sta     rbi
        lda     rb_cnt
        dcr     a
        sta     rb_cnt
        jmp     rb_loop
rb_done:
        lxi     h, dr_scr             ; drs читает колонки из dr_scr
        shld    _rs_spr
        jmp     drs_start

; --- подпрограммы переноса 24 байт тайла (HL=dst, DE=src) ---
copy24:
        mvi     b,24
c24:
        ldax    d
        mov     m,a
        inx     d
        inx     h
        dcr     b
        jnz     c24
        ret
zero24:
        mvi     b,24
        mvi     a,0
z24:
        mov     m,a
        inx     h
        dcr     b
        jnz     z24
        ret

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
; Сдвиг тетрады (frac=4) — «В-чистовой»: вывод спрайта со сдвигом
; вправо на 4px.
;
; Выходной байт клетки col+j собирается из двух клеток спрайта:
;   low  nibble <- high nibble клетки j     (cur >> 4)
;   high nibble <- low  nibble клетки j-1   (prev << 4)
; j пробегает 0..wcells (wcells+1 колонок): слева prev=zcol, справа для
; spill-колонки cur=zcol. 8080 не имеет сдвига на 4 — делаем 4x RRC/RLC.
;
; На каждой колонке:
;   1) drs_stage — собрать 32 тройки (op,b0,b1) в ds_buf (96 B);
;   2) CALL dr_p0 / CALL dr_p1 — быстрый путь, ровно как для frac=0.
; Внутренняя композиция и VRAM-стейджинг из старого drs_row удалены.
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
        ; --- базы данных: cur = spr+3, prev = zcol ---
        lhld    _rs_spr
        inx     h
        inx     h
        inx     h
        shld    ds_cptr
        lxi     h, zcol
        shld    ds_pptr

drs_col:
        ; DE = cur (zcol на spill-колонке, cc==1), BC = prev
        lda     ds_cc
        sui     1
        jz      drs_cur_z
        lhld    ds_cptr
        jmp     drs_cur_ok
drs_cur_z:
        lxi     h, zcol
drs_cur_ok:
        xchg                          ; DE = cur
        lhld    ds_pptr               ; BC = prev
        mov     b, h
        mov     c, l
        lxi     h, ds_t               ; HL = &ds_t, стоит весь drs_stage

; ---------------------------------------------------------------
; drs_stage — полный unroll 32 строк × 3 байта = 96 SBYTE-макросов.
;HL/DE/BC инициализированы в drs_col; после 96 макросов
; DE/BC = cur+96 / prev+96 (не используются — drs_col перезагрузит),
; ds_buf забит целиком. Falling-through в dr_p0/dr_p1 ниже.
; ---------------------------------------------------------------
drs_stage:
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
        SBYTE   24
        SBYTE   25
        SBYTE   26
        SBYTE   27
        SBYTE   28
        SBYTE   29
        SBYTE   30
        SBYTE   31
        SBYTE   32
        SBYTE   33
        SBYTE   34
        SBYTE   35
        SBYTE   36
        SBYTE   37
        SBYTE   38
        SBYTE   39
        SBYTE   40
        SBYTE   41
        SBYTE   42
        SBYTE   43
        SBYTE   44
        SBYTE   45
        SBYTE   46
        SBYTE   47
        SBYTE   48
        SBYTE   49
        SBYTE   50
        SBYTE   51
        SBYTE   52
        SBYTE   53
        SBYTE   54
        SBYTE   55
        SBYTE   56
        SBYTE   57
        SBYTE   58
        SBYTE   59
        SBYTE   60
        SBYTE   61
        SBYTE   62
        SBYTE   63
        SBYTE   64
        SBYTE   65
        SBYTE   66
        SBYTE   67
        SBYTE   68
        SBYTE   69
        SBYTE   70
        SBYTE   71
        SBYTE   72
        SBYTE   73
        SBYTE   74
        SBYTE   75
        SBYTE   76
        SBYTE   77
        SBYTE   78
        SBYTE   79
        SBYTE   80
        SBYTE   81
        SBYTE   82
        SBYTE   83
        SBYTE   84
        SBYTE   85
        SBYTE   86
        SBYTE   87
        SBYTE   88
        SBYTE   89
        SBYTE   90
        SBYTE   91
        SBYTE   92
        SBYTE   93
        SBYTE   94
        SBYTE   95

        ; ---- плоскость 0: dr_p0(ds_buf -> _rs_p0) ----
        lxi     d, ds_buf
        lhld    _rs_p0
        mvi     b, ROWS
        call    dr_p0
        ; ---- плоскость 1: dr_p1(ds_buf -> _rs_p1) ----
        lxi     d, ds_buf
        lhld    _rs_p1
        mvi     b, ROWS
        call    dr_p1

        ; ---- следующая колонка: prev=cur, cur+=96, VRAM += 0x100 ----
        lhld    ds_cptr
        shld    ds_pptr
        lxi     d, 0060h
        dad     d
        shld    ds_cptr
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
