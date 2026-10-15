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
;   _rs_s0    старт тени прямоугольника для _rs_p0 (shadow0), erase
;   _rs_s1    старт тени прямоугольника для _rs_p1 (shadow1), erase
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
;   mario_capture_shadow — слепок полосы BAND_TOP..BAND_BOT из плоскостей
;                          A в колоночные тени shadow0/shadow1.
;
; Геометрия ниже зеркалит main.c (BAND_TOP=104, BAND_BOT=223, GROUND_TOP=224,
; BAND_STRIDE=128). Менять синхронно в обоих файлах.
;

        SECTION code_clib
        PUBLIC  _mario_draw_sprite
        PUBLIC  _mario_erase_sprite
        PUBLIC  _mario_fill_ground
        PUBLIC  _mario_copy_AB
        PUBLIC  _mario_capture_shadow

        EXTERN  _rs_spr
        EXTERN  _rs_data
        EXTERN  _rs_p0
        EXTERN  _rs_p1
        EXTERN  _rs_s0
        EXTERN  _rs_s1
        EXTERN  _rs_cols
        EXTERN  _rs_frac
        EXTERN  _shadow0
        EXTERN  _shadow1

ROWS EQU 32                 ; строк спрайта (hcells=4 x CELL=8)

; --- геометрия инициализации (зеркало main.c) ---
NCOLS      EQU 32            ; колонок экрана (256/8)
GROUND_OFS EQU 31            ; 255 - GROUND_TOP: адрес байта верха земли
GROUND_ROWS EQU 32           ; строк земли (224..255)
BAND_OFS   EQU 151           ; 255 - BAND_TOP: адрес байта верха полосы
BAND_ROWS  EQU 120           ; строк полосы (BAND_TOP..BAND_BOT)
BAND_STEP  EQU 128           ; BAND_STRIDE: шаг колонки тени

;
; Рабочие переменные примитивов инициализации (не видны из C).
;
        SECTION bss_clib
fg_tile:    defw    0         ; база tile_ground
fg_cur:     defw    0         ; курсор колонки E000 (+0x100 на колонку)
cap_p:      defw    0         ; курсор колонки E000 (capture)
cap_q:      defw    0         ; курсор колонки C000 (capture)
cap_s:      defw    0         ; курсор колонки shadow0 (+BAND_STEP)
cap_t:      defw    0         ; курсор колонки shadow1 (+BAND_STEP)

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

; ---------------------------------------------------------------
; void mario_draw_sprite(void)
;   Нарисовать весь спрайт (_rs_spr) в пару плоскостей _rs_p0/_rs_p1.
;   Колонки заданы в x-выравнивании по сетке 8 px — побайтовые записи.
; ---------------------------------------------------------------
        SECTION code_clib
_mario_draw_sprite:
        lhld    _rs_spr               ; HL = спрайт
        mov     a,m                   ; wcells
        sta     ds_ncols              ; ширина в клетках (нужна shift-пути)
        cma
        inr     a
        sta     _rs_cols              ; _rs_cols = -wcells
        inx     h
        inx     h
        inx     h                     ; spr + 3 = старт данных
        shld    _rs_data
        lda     _rs_frac              ; суб-клеточный сдвиг?
        ora     a
        jnz     drs_start             ; frac!=0 -> сдвиг тетрады (4px)
dr_col:
        ; ================= проход 0: плоскость бита 0 =================
        lhld    _rs_data
        xchg                          ; DE = данные колонки
        lhld    _rs_p0                ; HL = VRAM (верх колонки)
        mvi     b,ROWS
        call    dr_p0

        ; ================= проход 1: плоскость бита 1 =================
        lhld    _rs_data              ; DE = данные колонки (сначала)
        xchg
        lhld    _rs_p1
        mvi     b,ROWS
        call    dr_p1

        ; ------------------- сдвиг на следующую колонку ----------------
        lhld    _rs_data              ; старт + 96 (DE после dr_p1)
        lxi     d,0060h
        dad     d
        shld    _rs_data
        lda     _rs_p0+1
        inc     a                     ; VRAM += 0x100 (блок следующий)
        sta     _rs_p0+1
        lda     _rs_p1+1
        inc     a
        sta     _rs_p1+1
        lda     _rs_cols
        inc     a
        sta     _rs_cols
        jnz     dr_col                ; INR задал Z
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
;   Вернуть фон: копировать ROWS строк тени (_rs_s0/_rs_s1) в
;   плоскости (_rs_p0/_rs_p1) по _rs_cols (знаковый счётчик) колонкам.
;   Шаг: VRAM +0x100 (блок), тень +BAND_STRIDE = 0x80 (DAD с переносом).
; ---------------------------------------------------------------
        SECTION code_clib
_mario_erase_sprite:
er_col:
        ; -------- плоскость бита 0: shadow0 -> p0 --------
        lhld    _rs_s0                ; DE = тень (источник)
        xchg
        lhld    _rs_p0                ; HL = VRAM (приёмник)
        mvi     b,ROWS
er_row0:
        ldax    d
        mov     m,a
        inx     d                     ; тень: y+1 => адрес +1
        dcx     h                     ; VRAM: y+1 => адрес -1
        dcr     b
        jnz     er_row0

        ; -------- плоскость бита 1: shadow1 -> p1 --------
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
        lxi     d,0080h
        dad     d                       ; тень += BAND_STRIDE (0x80)
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
; void mario_capture_shadow(void)
;   Слепок полосы BAND_TOP..BAND_BOT из плоскостей A в колоночные тени:
;     shadow0[c*128 + i] = E000 + c*256 + (151 - i),
;     shadow1[c*128 + i] = C000 + c*256 + (151 - i).
;   Источник (VRAM) — по убывающему адресу, приёмник (тень) — по
;   возрастающему: mov a,m / stax d / dcx h / inx d.
; ---------------------------------------------------------------
        SECTION code_clib
_mario_capture_shadow:
        lxi     h,0E000h
        shld    cap_p
        lxi     h,0C000h
        shld    cap_q
        lhld    _shadow0              ; АДРЕС буфера из кучи (значение
        shld    cap_s                   ; указателя; lxi дал бы адрес переменной)
        lhld    _shadow1
        shld    cap_t
        mvi     c,NCOLS
cs_col:
        ; ---- тень 0 <- E000-колонка ----
        lhld    cap_p
        lxi     d,BAND_OFS
        dad     d                       ; HL = src верх полосы
        xchg                            ; DE = src (сохранён)
        lhld    cap_s
        xchg                            ; DE = тень, HL = src ✓
        mvi     b,BAND_ROWS
cs_row0:
        mov     a,m
        stax    d
        dcx     h                       ; VRAM: строка ниже = адрес -1
        inx     d                       ; тень: строка ниже = адрес +1
        dcr     b
        jnz     cs_row0
        ; ---- тень 1 <- C000-колонка ----
        lhld    cap_q
        lxi     d,BAND_OFS
        dad     d
        xchg
        lhld    cap_t
        xchg
        mvi     b,BAND_ROWS
cs_row1:
        mov     a,m
        stax    d
        dcx     h
        inx     d
        dcr     b
        jnz     cs_row1
        ; ---- следующая колонка ----
        lhld    cap_p
        lxi     d,0100h
        dad     d
        shld    cap_p
        lhld    cap_q
        dad     d
        shld    cap_q
        lhld    cap_s
        lxi     d,BAND_STEP
        dad     d
        shld    cap_s
        lhld    cap_t
        dad     d
        shld    cap_t
        dcr     c
        jnz     cs_col
        ret
