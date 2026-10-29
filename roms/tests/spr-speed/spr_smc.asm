; spr_smc.asm — SPR_FORMAT + SMC-ядро вывода спрайтов (8080).
;
; Файл получен копированием spr_new.asm на момент эксперимента: erase_sprite_box,
; fill_checker, draw_sprite_new (flat) и draw_sprite_new_mask (OR-композит)
; оставлены как есть, чтобы старый и новый блиттинг сравнивались на ОДНИХ и
; тех же дескрипторах (mario_new.inc / mario_new_mask.inc).
;
; ДОБАВЛЕНО (разделы «ЯДРО ВЫВОДА СТОЛБЦА» и «SMC С МАСКОЙ» в конце файла):
;   smc_init()                       — собирает «лесенки» копирования и композиции;
;   draw_sprite_smc(x, y, desc)      — flat-вывод столбец-за-столбцом через CALL;
;   draw_sprite_smc_mask(x, y, desc) — то же, но с OR-композитом по маске
;                                      (dst = (dst AND mask) OR color).
; Обе функции — пара на одной технологии: обработчик столбца (col_copy / col_or)
; плюс развёрнутая в ОЗУ «лесенка». STUB-ядро — тоже парой, stub / stub_mask —
; вынесено в spr_stub.asm и вызывает col_copy / col_or / col_or_plane /
; mask_state отсюда.
;
; Исходный формат дескриптора: [FLAGS, COLS, DEPTH] + DATA
; FLAGS: bit0=П3, bit1=П2, bit2=П1, bit3=П0, bit6=OR-композит
; Данные: для каждой присутствующей плоскости (по порядку П3,П2,П1,П0)
;   подряд по COLS столбцов; столбец = [SHIFT, LEN] + LEN байт:
;   SHIFT — сдвиг от верхней строки спрайта до первой выводимой строки,
;   LEN   — число выводимых байтов (0 = столбец пуст).
;   Выводятся только строки с первой по последнюю ненулевую — головные
;   и хвостовые нули не хранятся и не пишутся в VRAM.
;
; Вызов: draw_sprite_new(x, y, desc) — flat-запись (перезапись VRAM)
;   x — пиксельная координата X (кратна 8)
;   y — пиксельная координата Y (0..248, верх спрайта)
;   desc — указатель на дескриптор
;
; erase_sprite_box(x, y, wcells, hpix) — затереть нулями прямоугольник
;   wcells*8 x hpix в плоскостях П0 (E000) и П1 (C000).
;
; fill_checker(x, y, wcells, hpix) — шахматная подложка под спрайт:
;   строки FF/AA в П0 и П1 — на неё накладывается маска.
;
; draw_sprite_new_mask(x, y, desc) — OR-композит с маской (FLAGS bit4):
;   dst = (dst AND mask) OR color. Блок маски лежит ПЕРВЫМ в DATA
;   (mask_base = DATA), за ним прогоны плоскостей — указатель идёт линейно.

        SECTION code_clib
        PUBLIC  _draw_sprite_new
        PUBLIC  _erase_sprite_box
        PUBLIC  _fill_checker
        PUBLIC  _draw_sprite_new_mask
        PUBLIC  _draw_sprite_smc
        PUBLIC  _draw_sprite_smc_mask
        PUBLIC  _smc_init
        PUBLIC  mask_span
        PUBLIC  mask_state
        PUBLIC  col_copy
        PUBLIC  col_or
        PUBLIC  col_or_plane
        PUBLIC  _rn_mcur

        SECTION bss_compiler
_rn_dst:  defw    0          ; базовый адрес VRAM (верх левого столбца)
_rn_desc: defw    0
_rn_flags: defb   0
_rn_cols: defb    0
_rn_depth: defb   0
_rn_data: defw    0
_rn_x:    defb    0
_rn_y:    defb    0
er_x:     defb    0
er_y:     defb    0
er_w:     defb    0
er_h:     defb    0
er_base:  defw    0

; --- вариант с маской ---
_rn_mask: defw    0          ; база блока маски = DATA (маска лежит первой)
_rn_mcur: defw    0          ; курсор маски (линейно по блоку)
_rn_cbase: defw   0          ; верх текущего столбца ЭТОЙ плоскости
_rn_tab:  defw    0          ; база TABLE [SHIFT, LEN]
_rn_tcur: defw    0          ; курсор TABLE
_rn_tabc: defb    0          ; счётчик столбцов
_rn_sh:   defb    0          ; SHIFT текущего столбца
_rn_len:  defb    0          ; LEN текущего столбца
_rn_cnt:  defb    0          ; счётчик строк композиции

; --- fill_checker ---
fc_x:     defb    0
fc_y:     defb    0
fc_w:     defb    0
fc_h:     defb    0
fc_base:  defw    0

        SECTION code_clib

; ---------------------------------------------------------------
; void erase_sprite_box(unsigned char x, unsigned char y,
;                       unsigned char wcells, unsigned char hpix)
; ---------------------------------------------------------------
_erase_sprite_box:
        ; Соглашение __z88dk_callee (как lib/gfx/pr.asm): каждый аргумент —
        ; 16-битный слот, значение в младшем байте; последний аргумент сверху.
        ; Стек: ret(2), hpix(2), wcells(2), y(2), x(2).
        pop     d               ; ret
        pop     h
        mov     a, l
        sta     er_h            ; hpix
        pop     h
        mov     a, l
        sta     er_w            ; wcells
        pop     h
        mov     a, l
        sta     er_y            ; y
        pop     h
        mov     a, l
        sta     er_x            ; x
        push    d

        ; base = 0xE000 + (x>>3)*256 + (255-y)
        lda     er_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     0E0h
        mov     h, a
        lda     er_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     e1
        inr     h
e1:     shld    er_base

        ; Плоскость П0 (E000)
        call    erase_plane

        ; Плоскость П1 (C000) = base - 0x2000
        lhld    er_base
        mov     a, h
        sui     20h
        mov     h, a
        shld    er_base
        call    erase_plane
        ret

; Затереть одну плоскость: er_w колонок x er_h строк нулями
erase_plane:
        lhld    er_base
        lda     er_w
        mov     b, a
er_col:
        push    b
        push    h
        lda     er_h
        mov     c, a
er_row:
        mvi     m, 0
        dcx     h
        dcr     c
        jnz     er_row
        pop     h
        inr     h              ; следующий столбец +0x100
        pop     b
        dcr     b
        jnz     er_col
        ret

; ---------------------------------------------------------------
; void fill_checker(unsigned char x, unsigned char y,
;                   unsigned char wcells, unsigned char hpix)
; Шахматная подложка под маску: строки 0xFF, 0xAA, 0xFF, 0xAA...
; сразу в П0 (E000) и П1 (C000). hpix — чётное (пары строк).
; ---------------------------------------------------------------
_fill_checker:
        pop     d               ; ret
        pop     h
        mov     a, l
        sta     fc_h            ; hpix
        pop     h
        mov     a, l
        sta     fc_w            ; wcells
        pop     h
        mov     a, l
        sta     fc_y            ; y
        pop     h
        mov     a, l
        sta     fc_x            ; x
        push    d

        ; base = 0xE000 + (x>>3)*256 + (255-y) — верх левой колонки, П0
        lda     fc_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     0E0h
        mov     h, a
        lda     fc_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     fc1
        inr     h
fc1:    shld    fc_base

        ; B = hpix/2 (пары строк), C = wcells
        lda     fc_h
        ora     a               ; CY=0
        rar
        mov     b, a
        lda     fc_w
        mov     c, a
        lhld    fc_base         ; HL = верх П0
        mov     a, h
        sui     20h
        mov     d, a            ; DE = верх П1 = base - 0x2000
        mov     e, l

fc_col:
        push    b
        push    h
        push    d
fc_pair:
        mvi     a, 0FFh
        mov     m, a            ; П0 = 0xFF
        stax    d               ; П1 = 0xFF
        dcx     h
        dcx     d
        mvi     a, 0AAh
        mov     m, a            ; П0 = 0xAA
        stax    d               ; П1 = 0xAA
        dcx     h
        dcx     d
        dcr     b
        jnz     fc_pair
        pop     d
        pop     h
        inr     h               ; следующий столбец +0x100
        mov     a, h
        sui     20h
        mov     d, a
        mov     e, l
        pop     b
        dcr     c
        jnz     fc_col
        ret

; ---------------------------------------------------------------
; void draw_sprite_new(unsigned char x, unsigned int y,
;                      const unsigned char *desc)
; ---------------------------------------------------------------
_draw_sprite_new:
        ; Соглашение __z88dk_callee (как lib/gfx/pr.asm): каждый аргумент —
        ; 16-битный слот, значение в младшем байте; последний аргумент сверху.
        ; Стек: ret(2), desc(2), y(2), x(2).
        pop     d               ; ret

        pop     h
        shld    _rn_desc        ; desc — последний аргумент, снимается первым

        pop     h
        mov     a, l
        sta     _rn_y           ; y

        pop     h
        mov     a, l
        sta     _rn_x           ; x — первый аргумент, снимается последним

        push    d

        ; dst = 0x8000 + (x/8)*256 + (255-y)  — база П3 (верх левого столбца)
        lda     _rn_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     _rn_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     nc1
        inr     h
nc1:    shld    _rn_dst

        ; Разобрать дескриптор
        lhld    _rn_desc
        mov     a, m            ; FLAGS
        sta     _rn_flags
        inx     h
        mov     a, m            ; COLS
        sta     _rn_cols
        inx     h
        mov     a, m            ; DEPTH
        sta     _rn_depth
        inx     h
        shld    _rn_data        ; DATA = desc+3

        ; Перебор плоскостей П3..П0, шаг адреса +0x2000
        mvi     c, 01h          ; бит текущей плоскости: 1,2,4,8
plane_loop:
        lda     _rn_flags
        ana     c
        jz      plane_skip
        push    b
        call    plane_blit
        pop     b
plane_skip:
        lhld    _rn_dst
        mov     a, h
        adi     20h
        mov     h, a
        shld    _rn_dst
        mov     a, c
        rlc
        mov     c, a
        ani     10h             ; прошли все 4 плоскости?
        jz      plane_loop
        ret

; ---------------------------------------------------------------
; plane_blit — flat-запись одной плоскости
; Вход: DE = курсор данных, HL = dst (верх левого столбца), B = cols
; Столбец данных: [SHIFT, LEN] + LEN байт.
; ---------------------------------------------------------------
plane_blit:
        lhld    _rn_data
        xchg                    ; DE = курсор данных
        lhld    _rn_dst         ; HL = VRAM (верх левого столбца)
        lda     _rn_cols
        mov     b, a            ; B = счётчик столбцов
pb_col:
        push    b
        push    h               ; верх колонки (восстановим после столбца)
        ldax    d               ; A = SHIFT
        inx     d
        mov     c, a
        mvi     b, 0            ; BC = SHIFT
        ; HL = HL - SHIFT (адрес убывает вниз по экрану)
        mov     a, l
        sub     c
        mov     l, a
        mov     a, h
        sbb     b
        mov     h, a
        ldax    d               ; A = LEN
        inx     d
        ora     a
        jz      pb_next         ; LEN = 0 — пустой столбец
        mov     c, a
pb_byte:
        ldax    d
        inx     d
        mov     m, a            ; плоская запись
        dcx     h               ; адрес убывает вниз по экрану
        dcr     c
        jnz     pb_byte
pb_next:
        pop     h
        inr     h               ; следующий столбец +0x100
        pop     b
        dcr     b
        jnz     pb_col
        ; Сохранить продвинутый курсор данных
        xchg                    ; HL = DE
        shld    _rn_data
        ret

; ---------------------------------------------------------------
; mask_span — разбор блока маски по TABLE
; Вход: HL = TABLE ([SHIFT, LEN] x COLS), B = COLS.
; Выход: HL = DATA = TABLE + 2*COLS (база блока маски), DE = Σ LEN.
; Σ LEN — длина маски: цвет начинается сразу за ней.
; ---------------------------------------------------------------
mask_span:
        lxi     d, 0
ms_sum:
        inx     h               ; пропустить SHIFT
        mov     a, m            ; LEN
        add     e
        mov     e, a
        mvi     a, 0
        adc     d
        mov     d, a
        inx     h
        dcr     b
        jnz     ms_sum
        ret

; ---------------------------------------------------------------
; mask_state — разбор заголовка дескриптора с маской.
; Вход: HL = TABLE = desc+3 ([SHIFT, LEN] x COLS), B = COLS.
; Выход: _rn_tab = TABLE, _rn_mask = база маски, HL = _rn_data = цвет.
; Маска лежит ПЕРВЫМ блоком DATA, поэтому цвет = маска + Σ LEN.
; ---------------------------------------------------------------
mask_state:
        shld    _rn_tab         ; TABLE — общая для маски и цвета
        call    mask_span       ; HL = DATA (маска), DE = Σ LEN
        shld    _rn_mask        ; mask_base = DATA
        dad     d
        shld    _rn_data        ; цвет = маска + Σ LEN
        ret

; ===============================================================
; МАСКА + OR-КОМПОЗИТ (FLAGS bit4/bit5/bit6)
; [FLAGS, COLS, DEPTH] + TABLE + DATA, где DATA = [МАСКА][П3][П2][П1][П0]:
;   - маска лежит ПЕРВОЙ: mask_base = DATA, без арифметики;
;   - TABLE общая для всех блоков, прогоны синхронны;
;   - курсор цвета идёт линейно через блоки плоскостей.
; Композиция строки: dst = (dst AND mask) OR color — фон в прозрачных
; строках сохраняется, erase не нужен.
; ===============================================================
_draw_sprite_new_mask:
        ; Стек: ret(2), desc(2), y(2), x(2)
        pop     d               ; ret
        pop     h
        shld    _rn_desc
        pop     h
        mov     a, l
        sta     _rn_y
        pop     h
        mov     a, l
        sta     _rn_x
        push    d

        ; dst = 0x8000 + (x/8)*256 + (255-y) — база П3
        lda     _rn_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     _rn_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     nm1
        inr     h
nm1:    shld    _rn_dst

        ; Заголовок
        lhld    _rn_desc
        mov     a, m            ; FLAGS
        sta     _rn_flags
        inx     h
        mov     a, m            ; COLS
        sta     _rn_cols
        mov     b, a            ; B = COLS — счётчик для mask_state
        inx     h
        mov     a, m            ; DEPTH
        sta     _rn_depth
        inx     h
        ; Блок маски = DATA, её длина = Σ LEN — цвет сразу за маской
        call    mask_state      ; TABLE, _rn_mask и курсор цвета

        ; Перебор плоскостей П3..П0, шаг адреса +0x2000
        mvi     c, 01h
nplane_loop:
        lda     _rn_flags
        ana     c
        jz      nplane_skip
        push    b
        call    plane_or
        pop     b
nplane_skip:
        lhld    _rn_dst
        mov     a, h
        adi     20h
        mov     h, a
        shld    _rn_dst
        mov     a, c
        rlc
        mov     c, a
        ani     10h             ; прошли все 4 плоскости?
        jz      nplane_loop
        ret

; ---------------------------------------------------------------
; plane_or — OR-композит одной плоскости с маской
; Вход: _rn_data = курсор цвета (продвигается), HL = dst — берётся из
;       _rn_dst; маска перечитывается с начала блока для ЭТОЙ плоскости.
; ---------------------------------------------------------------
plane_or:
        lhld    _rn_data
        xchg                    ; DE = курсор цвета
        lhld    _rn_mask
        shld    _rn_mcur        ; маска — с начала блока для этой плоскости
        lhld    _rn_dst
        shld    _rn_cbase       ; верх столбца: СВОЙ курсор, _rn_dst не трогаем
        lda     _rn_cols
        sta     _rn_tabc
        lhld    _rn_tab
        shld    _rn_tcur
po_col:
        ; SHIFT/LEN из таблицы (HL уходит под VRAM — читаем заранее)
        push    d
        push    b
        lhld    _rn_tcur
        mov     a, m            ; SHIFT
        sta     _rn_sh
        inx     h
        mov     a, m            ; LEN
        sta     _rn_len
        inx     h
        shld    _rn_tcur
        pop     b
        pop     d
        lda     _rn_len
        ora     a
        jz      po_next         ; пустой столбец — ни цвета, ни маски
        sta     _rn_cnt

        ; BC = курсор маски (продолжение с прошлого столбца)
        lhld    _rn_mcur
        mov     c, l
        mov     b, h

        ; HL = _rn_cbase - SHIFT (DE — цвет, откладываем в стек)
        push    d
        lhld    _rn_cbase
        lda     _rn_sh
        mov     e, a
        mvi     d, 0
        mov     a, l
        sub     e
        mov     l, a
        mov     a, h
        sbb     d
        mov     h, a
        pop     d
        call    por_run
po_next:
        lhld    _rn_cbase
        inr     h               ; следующий столбец +0x100
        shld    _rn_cbase
        lda     _rn_tabc
        dcr     a
        sta     _rn_tabc
        jnz     po_col
        xchg                    ; HL = DE (продвинутый курсор цвета)
        shld    _rn_data
        ret

; Композиция LEN строк: DE = цвет, BC = маска, HL = VRAM (вниз).
; Счётчик строк — в _rn_cnt (на 8080 нет третьей пары под него).
por_run:
        ldax    b               ; A = маска строки
        ana     m               ; A = фон AND маска
        xchg                    ; HL = цвет, DE = VRAM
        ora     m               ; A = (фон AND msk) OR цвет
        xchg                    ; HL = VRAM, DE = цвет
        mov     m, a
        inx     b               ; следующая строка маски
        inx     d               ; следующая строка цвета
        dcx     h               ; адрес убывает вниз по экрану
        lda     _rn_cnt
        dcr     a
        sta     _rn_cnt
        jnz     por_run
        mov     h, b            ; курсор маски — в _rn_mcur
        mov     l, c
        shld    _rn_mcur
        ret

; ===============================================================
; ЯДРО ВЫВОДА СТОЛБЦА: обработчик col_copy + «лесенка» в ОЗУ
; ===============================================================
; Идея: столбец спрайта копирует ОДНА короткая подпрограмма col_copy.
; Вызывающий держит DE = указатель на столбец данных [SHIFT][LEN][байты],
; HL = адрес верха столбца в VRAM; после CALL нужен только INR H — и
; следующий столбец (DE уже за байтами столбца). Обработчик сам
; сохраняет/восстанавливает HL, читает SHIFT/LEN и уходит в «лесенку».
;
; Вызов — обычный CALL (17 тактов, 3 байта): обработчик живёт в обычном
; коде ROM по своему адресу, нулевая страница не нужна, инициализация
; сводится к сборке лесенки. Вариант с RST 1 (11 тактов, 1 байт на вызов)
; экономил 8 реальных тактов на столбец — на спрайт это 24 тика VI53
; (0,6 %), поэтому вектор не занимаем.
;
; Лесенка — развёрнутое тело копирования: 32 строки по 4 байта
; (ldax d / mov m,a / inx d / dcx h = 24 такта на строку) вместо цикла
; с DCR/JNZ (39 тактов на байт). Вход в лесенку = 0x7080 - 4*LEN:
; исполнив LEN строк, поток проваливается в хвост pop h / ret, который
; возвращает HL вызывающего и уходит в цикл по столбцам; LEN = 0 даёт
; вход ровно в хвост. Ни таблицы переходов, ни патча кода на каждом
; вызове не нужно — только LEN из данных.
;
; Раскладка в ОЗУ (ставит _smc_init один раз при старте):
;   0x7000 — лесенка (32 строки + хвост). Страница выровнена, поэтому адрес
;            входа считается по младшему байту, H всегда 0x70.
; Предел: LEN <= 32 (в mario_new.inc максимум 28).
;
; Стек на один столбец (popов в обработчике нет — они в хвосте лесенки):
;   CALL      -2  адрес возврата в ps_col
;   push h    -2  верх столбца (HL входа)
;   push h    -2  начало столбца (HL после SHIFT)
;   XTHL       0  начало уходит в HL, в стеке остаётся адрес входа
;   ret       +2  прыжок в лесенку; верх стека — верх столбца
;   хвост 0x7080: pop h +2 (HL = верх столбца), ret +2 (назад в ps_col)
; Баланс нулевой: SP на входе в столбец равен SP после хвоста.

SMC_LADDER      EQU     7000h   ; страница лесенки (кратна 0x100!)
SMC_PAGE        EQU     70h     ; = SMC_LADDER >> 8
SMC_LAST        EQU     80h     ; младший байт хвоста (SMC_LADDER + 128)
SMC_ROWS        EQU     32      ; строк лесенки = максимальный LEN

OR_LADDER       EQU     7100h   ; страница лесенки композиции (кратна 0x100!)
OR_PAGE         EQU     71h     ; = OR_LADDER >> 8
OR_LAST         EQU     0FCh    ; младший байт хвоста (OR_LADDER + 9*OR_ROWS)
OR_ROWS         EQU     28      ; строк лесенки = максимальный LEN маски
OR_ROW_LEN      EQU     9       ; байт в строке лесенки композиции

; ---------------------------------------------------------------
; col_copy — скопировать один столбец в VRAM (вызов: CALL col_copy).
; Вход: DE = [SHIFT][LEN][LEN байт], HL = верх столбца в VRAM.
; Выход: DE — за байтами столбца, HL = верх столбца (как на входе).
; ---------------------------------------------------------------
col_copy:
        push    h               ; [top] верх столбца — вернётся из хвоста лесенки
        ldax    d               ; A = SHIFT
        inx     d
        mov     c, a
        mov     a, l            ; HL -= SHIFT: первая выводимая строка
        sub     c
        mov     l, a
        jnc     rs_nb
        dcr     h
rs_nb:
        push    h               ; [start][top] начало данных в VRAM; снимает XTHL ниже
        ldax    d               ; A = LEN
        inx     d
        add     a               ; A = 4*LEN
        add     a
        cma                     ; A = 0x80 - 4*LEN — младший байт входа
        inr     a
        adi     SMC_LAST
        mov     l, a
        mvi     h, SMC_PAGE
        xthl                    ; HL = начало столбца, в стеке — адрес входа
        ret                     ; ret-прыжок: PC = вход, HL = начало столбца
col_copy_end:

; ---------------------------------------------------------------
; col_or — скомпоновать один столбец в VRAM (вызов: CALL col_or).
; Пара к col_copy: строка не копируется, а компонуется
;   dst = (dst AND mask) OR color
; Отличие от col_copy: в маске-дескрипторе заголовков [SHIFT][LEN] в потоке
; цвета НЕТ — они берутся из общей TABLE (курсор _rn_tcur), а маска — из
; _rn_mcur. Поэтому DE растёт ровно на LEN байт.
; Вход: DE = курсор цвета (LEN байт), HL = верх столбца в VRAM.
; Выход: DE — за байтами цвета, HL = верх столбца (как на входе),
;        _rn_tcur / _rn_mcur — продвинуты, B сохранён (C — нет).
; Перед каждой плоскостью курсоры сбрасывает col_or_plane.
;
; Стек на столбец: CALL -2; push b -2 (счётчик вызывающего); push h x2 -4
; (верх и рабочий экземпляр); push h -2 (начало столбца); push h -2 (адрес
; входа). Дальше XTHL (начало уходит в HL, вход остаётся под RET) + RET —
; поток проваливается в хвост 0x71FC: mov h,b / mov l,c / shld _rn_mcur /
; pop h / pop b / ret — баланс нулевой, SP возвращается к уровню после CALL.
; ---------------------------------------------------------------
col_or:
        push    b               ; B вызывающего — счётчик столбцов — не трогаем
        push    h               ; [top] верх столбца — вернётся из хвоста
        push    h               ; второй экземпляр: снимаемым получим начало
        lhld    _rn_tcur
        mov     a, m            ; SHIFT
        inx     h
        mov     c, a
        mov     a, m            ; LEN
        inx     h
        shld    _rn_tcur        ; TABLE продвинута
        mov     b, a            ; B = LEN (BC пока свободен)
        pop     h               ; HL = верх столбца
        mov     a, l            ; HL -= SHIFT: первая выводимая строка
        sub     c
        mov     l, a
        jnc     or_nb
        dcr     h
or_nb:
        push    h               ; [start][top][B] начало данных в VRAM
        mov     a, b            ; A = LEN
        add     a               ; 2*LEN
        add     a               ; 4*LEN
        add     a               ; 8*LEN
        add     b               ; 9*LEN
        cma
        inr     a               ; A = -9*LEN — младший байт входа
        adi     OR_LAST
        mov     l, a
        mvi     h, OR_PAGE      ; HL = адрес входа в лесенку
        push    h               ; [entry][start][top][B]
        lhld    _rn_mcur
        mov     c, l
        mov     b, h            ; BC = курсор маски
        pop     h               ; HL = адрес входа
        xthl                    ; HL = начало столбца, в стеке — адрес входа
        ret                     ; ret-прыжок: PC = вход, HL = начало столбца
col_or_end:

; ---------------------------------------------------------------
; col_or_plane — сбросить курсоры композиции на начало блоков.
; Маска и TABLE общие для всех плоскостей, цвет идёт линейно — поэтому
; перед каждой плоскостью их курсоры возвращаются назад. HL и DE не трогает.
; ---------------------------------------------------------------
col_or_plane:
        push    h
        push    d
        lhld    _rn_mask
        shld    _rn_mcur        ; маска — с начала блока
        lhld    _rn_tab
        shld    _rn_tcur        ; TABLE — с первого столбца
        pop     d
        pop     h
        ret

; ---------------------------------------------------------------
; void smc_init(void) — собрать обе «лесенки» в ОЗУ (единственная SMC-часть).
; Зовётся один раз из main() до первого вызова SMC/STUB-ядер с маской или без.
;   0x7000 — строки копирования (4 байта x 32) + хвост pop h / ret;
;   0x7100 — строки композиции (9 байт x 28) + хвост mov h,b / mov l,c /
;            shld _rn_mcur / pop h / pop b / ret (8 байт, 0x71FC..0x7203).
; ---------------------------------------------------------------
_smc_init:
        ; лесенка -> 0x7000: SMC_ROWS строк по 4 байта + хвост pop h / ret
        lxi     d, SMC_LADDER
        mvi     b, SMC_ROWS
sc_row:
        lxi     h, ladder_row
        mvi     c, 4
sc_b:
        mov     a, m
        stax    d
        inx     h
        inx     d
        dcr     c
        jnz     sc_b
        dcr     b
        jnz     sc_row
        mvi     a, 0E1h         ; pop h — вернуть вызывающему верх столбца
        stax    d
        inx     d
        mvi     a, 0C9h         ; ret — назад в цикл по столбцам
        stax    d

        ; лесенка композиции -> 0x7100: OR_ROWS строк по 9 байт + хвост
        lxi     d, OR_LADDER
        mvi     b, OR_ROWS
oc_row:
        lxi     h, ladder_or_row
        mvi     c, OR_ROW_LEN
oc_b:
        mov     a, m
        stax    d
        inx     h
        inx     d
        dcr     c
        jnz     oc_b
        dcr     b
        jnz     oc_row
        mvi     a, 60h          ; mov h,b — продвинутый курсор маски...
        stax    d
        inx     d
        mvi     a, 69h          ; mov l,c
        stax    d
        inx     d
        mvi     a, 22h          ; shld — ...в _rn_mcur
        stax    d
        inx     d
        lxi     h, _rn_mcur
        mov     a, l
        stax    d
        inx     d
        mov     a, h
        stax    d
        inx     d
        mvi     a, 0E1h         ; pop h — вернуть вызывающему верх столбца
        stax    d
        inx     d
        mvi     a, 0C1h         ; pop b — вернуть счётчик столбцов
        stax    d
        inx     d
        mvi     a, 0C9h         ; ret — назад в цикл по столбцам
        stax    d
        ret

; Шаблон одной строки лесенки (только копируется, не исполняется).
ladder_row:
        ldax    d               ; байт данных
        mov     m, a            ; -> VRAM
        inx     d               ; следующая строка данных
        dcx     h               ; адрес в VRAM убывает вниз по экрану

; Шаблон одной строки лесенки композиции (только копируется, не исполняется).
; 53 такта против 94 у цикла por_run (тот же композит + счётчик строк в ОЗУ).
ladder_or_row:
        ldax    b               ; A = маска строки
        ana     m               ; A = фон AND маска
        xchg                    ; HL = цвет, DE = VRAM
        ora     m               ; A = (фон AND маска) OR цвет
        xchg                    ; HL = VRAM, DE = цвет
        mov     m, a            ; -> VRAM
        inx     b               ; следующая строка маски
        inx     d               ; следующая строка цвета
        dcx     h               ; адрес в VRAM убывает вниз по экрану

; ---------------------------------------------------------------
; void draw_sprite_smc(unsigned char x, unsigned int y,
;                      const unsigned char *desc)
; Flat-вывод через col_copy; формат дескриптора — как у draw_sprite_new.
; ---------------------------------------------------------------
_draw_sprite_smc:
        ; Стек: ret(2), desc(2), y(2), x(2).
        pop     d               ; ret
        pop     h
        shld    _rn_desc
        pop     h
        mov     a, l
        sta     _rn_y
        pop     h
        mov     a, l
        sta     _rn_x
        push    d

        ; dst = 0x8000 + (x/8)*256 + (255-y) — база П3 (верх левого столбца)
        lda     _rn_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     _rn_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     sx1
        inr     h
sx1:    shld    _rn_dst

        ; Заголовок
        lhld    _rn_desc
        mov     a, m            ; FLAGS
        sta     _rn_flags
        inx     h
        mov     a, m            ; COLS
        sta     _rn_cols
        inx     h
        mov     a, m            ; DEPTH
        sta     _rn_depth
        inx     h
        shld    _rn_data        ; DATA = desc+3

        ; Перебор плоскостей П3..П0, шаг адреса +0x2000
        mvi     c, 01h
smc_plane:
        lda     _rn_flags
        ana     c
        jz      smc_skip
        push    b
        call    plane_smc
        pop     b
smc_skip:
        lhld    _rn_dst
        mov     a, h
        adi     20h
        mov     h, a
        shld    _rn_dst
        mov     a, c
        rlc
        mov     c, a
        ani     10h             ; прошли все 4 плоскости?
        jz      smc_plane
        ret

; ---------------------------------------------------------------
; plane_smc — одна плоскость через col_copy
; Вход: B = cols (счётчик), HL = верх левого столбца, DE = данные.
; ---------------------------------------------------------------
plane_smc:
        lhld    _rn_data
        xchg                    ; DE = курсор данных столбцов
        lhld    _rn_dst         ; HL = верх левого столбца
        lda     _rn_cols
        mov     b, a
ps_col:
        call    col_copy        ; столбец целиком: SHIFT/LEN читает сам
        inr     h               ; следующий столбец +0x100
        dcr     b
        jnz     ps_col
        xchg                    ; HL = DE (продвинутый курсор данных)
        shld    _rn_data
        ret

; ===============================================================
; SMC С МАСКОЙ: пара к draw_sprite_smc на той же технологии
; ===============================================================
; Разница только в обработчике столбца (col_or вместо col_copy) и в том,
; что маска лежит ПЕРВЫМ блоком DATA, а SHIFT/LEN — в общей TABLE. Курсор
; маски живёт в _rn_mcur, курсор TABLE — в _rn_tcur; оба ведёт сам col_or.
; В каждой плоскости они сбрасываются на начало блоков (col_or_plane),
; цвет при этом идёт линейно.
;
; Композиция — 53 такта на строку против 94 у цикла por_run (тот же композит
; плюс счётчик строк в ОЗУ и переход) — это и есть выигрыш от «лесенки».

; ---------------------------------------------------------------
; plane_smc_or — одна плоскость через col_or
; Вход: _rn_data = курсор цвета, _rn_dst = верх левого столбца.
; ---------------------------------------------------------------
plane_smc_or:
        call    col_or_plane    ; маска и TABLE — с начала блоков
        lhld    _rn_data
        xchg                    ; DE = курсор цвета
        lhld    _rn_dst
        lda     _rn_cols
        mov     b, a
pso_col:
        call    col_or          ; столбец: SHIFT/LEN из TABLE, маска из _rn_mcur
        inr     h               ; следующий столбец +0x100
        dcr     b
        jnz     pso_col
        xchg                    ; HL = DE (продвинутый курсор цвета)
        shld    _rn_data
        ret

; ---------------------------------------------------------------
; void draw_sprite_smc_mask(unsigned char x, unsigned int y,
;                           const unsigned char *desc)
; OR-композит через col_or; дескриптор — вариант с маской (FLAGS bit4),
; маска ПЕРВЫМ блоком DATA, erase под спрайтом не нужен.
; ---------------------------------------------------------------
_draw_sprite_smc_mask:
        ; Стек: ret(2), desc(2), y(2), x(2).
        pop     d               ; ret
        pop     h
        shld    _rn_desc
        pop     h
        mov     a, l
        sta     _rn_y
        pop     h
        mov     a, l
        sta     _rn_x
        push    d

        ; dst = 0x8000 + (x/8)*256 + (255-y) — база П3 (верх левого столбца)
        lda     _rn_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     _rn_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     sxm1
        inr     h
sxm1:   shld    _rn_dst

        ; Заголовок + база маски и курсор цвета
        lhld    _rn_desc
        mov     a, m            ; FLAGS
        sta     _rn_flags
        inx     h
        mov     a, m            ; COLS
        sta     _rn_cols
        mov     b, a            ; B = COLS — счётчик для mask_state
        inx     h
        mov     a, m            ; DEPTH
        sta     _rn_depth
        inx     h
        call    mask_state      ; TABLE, _rn_mask и курсор цвета

        ; Перебор плоскостей П3..П0, шаг адреса +0x2000
        mvi     c, 01h
sxm_plane:
        lda     _rn_flags
        ana     c
        jz      sxm_skip
        push    b
        call    plane_smc_or
        pop     b
sxm_skip:
        lhld    _rn_dst
        mov     a, h
        adi     20h
        mov     h, a
        shld    _rn_dst
        mov     a, c
        rlc
        mov     c, a
        ani     10h             ; прошли все 4 плоскости?
        jz      sxm_plane
        ret

