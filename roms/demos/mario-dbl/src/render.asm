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

; ---------------------------------------------------------------
; void mario_draw_sprite(void)
;   Нарисовать весь спрайт (_rs_spr) в пару плоскостей _rs_p0/_rs_p1.
;   Колонки заданы в x-выравнивании по сетке 8 px — побайтовые записи.
; ---------------------------------------------------------------
        SECTION code_clib
_mario_draw_sprite:
        lhld    _rs_spr               ; HL = спрайт
        mov     a,m                   ; wcells
        cma
        inr     a
        sta     _rs_cols              ; _rs_cols = -wcells
        inx     h
        inx     h
        inx     h                     ; spr + 3 = старт данных
        shld    _rs_data

dr_col:
        ; ================= проход 0: плоскость бита 0 =================
        lhld    _rs_data
        xchg                          ; DE = данные колонки
        lhld    _rs_p0                ; HL = VRAM (верх колонки)
        mvi     b,ROWS
dr_row0:
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
        jnz     dr_row0

        ; ================= проход 1: плоскость бита 1 =================
        lhld    _rs_data              ; DE = данные колонки (сначала)
        xchg
        lhld    _rs_p1
        mvi     b,ROWS
dr_row1:
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
        jnz     dr_row1

        ; ------------------- сдвиг на следующую колонку ----------------
        mov     a,e                   ; DE уже = старт_колонки + 96
        sta     _rs_data
        mov     a,d
        sta     _rs_data+1
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
        lxi     h,_shadow0              ; АДРЕС массива тени (не lhld —
        shld    cap_s                   ; это прочитал бы первые 2 байта!)
        lxi     h,_shadow1
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
