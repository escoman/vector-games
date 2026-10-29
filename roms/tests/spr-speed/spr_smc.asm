; spr_smc.asm — SPR_FORMAT + SMC/RST-ядро вывода спрайтов (8080).
;
; Файл получен копированием spr_new.asm на момент эксперимента: erase_sprite_box,
; fill_checker, draw_sprite_new (flat) и draw_sprite_new_mask (OR-композит)
; оставлены как есть, чтобы старый и новый блиттинг сравнивались на ОДНИХ и
; тех же дескрипторах (mario_new.inc / mario_new_mask.inc).
;
; ДОБАВЛЕНО (раздел «SMC/RST-ЯДРО» в конце файла):
;   smc_init()                  — ставит обработчик RST 1 и «лесенку» в ОЗУ;
;   draw_sprite_smc(x, y, desc) — flat-вывод столбец-за-столбцом через RST 1.
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
        PUBLIC  _smc_init

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
        inx     h
        mov     a, m            ; DEPTH
        sta     _rn_depth
        inx     h
        shld    _rn_tab         ; TABLE = desc+3

        ; DATA = TABLE + 2*COLS (маска — первым блоком)
        lda     _rn_cols
        add     a               ; A = 2*COLS
        mov     e, a
        mvi     d, 0
        lhld    _rn_tab
        dad     d
        shld    _rn_mask        ; mask_base = DATA

        ; Σ LEN по TABLE -> DE; так как блок маски = Σ LEN,
        ; курсор цвета = mask_base + Σ LEN (маска кончилась — начались П1)
        lhld    _rn_tab         ; HL = TABLE (после dad d HL указывает на DATA)
        lda     _rn_cols
        mov     b, a
        lxi     d, 0
nm_sum:
        inx     h               ; пропустить SHIFT
        mov     a, m            ; LEN
        add     e
        mov     e, a
        mvi     a, 0
        adc     d
        mov     d, a
        inx     h
        dcr     b
        jnz     nm_sum
        lhld    _rn_mask
        dad     d
        shld    _rn_data

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
; SMC/RST-ЯДРО: flat-вывод столбца через вектор RST 1
; ===============================================================
; Идея: столбец спрайта копирует ОДНА короткая подпрограмма по адресу 0x0008
; (вектор RST 1). Вызывающий держит DE = указатель на столбец данных
; [SHIFT][LEN][байты], HL = адрес верха столбца в VRAM; после RST 1 нужен
; только INR H — и следующий столбец (DE уже за байтами столбца).
; Обработчик сам сохраняет/восстанавливает HL, читает SHIFT/LEN и уходит
; в «лесенку».
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
;   0x0008 — обработчик RST 1 (25 байт: 0x0008..0x0020). Векторы RST 2
;            (0x0010) и RST 3 (0x0018) при этом затираются — мы их не зовём;
;            вектор кадрового прерывания 0x0038 не задет;
;   0x7000 — лесенка (32 строки + хвост). Страница выровнена, поэтому адрес
;            входа считается по младшему байту, H всегда 0x70.
; Предел: LEN <= 32 (в mario_new.inc максимум 28).
;
; Стек на один столбец (popов в обработчике нет — они в хвосте лесенки):
;   RST 1     -2  адрес возврата в ps_col
;   push h    -2  верх столбца (HL входа)
;   push h    -2  начало столбца (HL после SHIFT)
;   XTHL       0  начало уходит в HL, в стеке остаётся адрес входа
;   ret       +2  прыжок в лесенку; верх стека — верх столбца
;   хвост 0x7080: pop h +2 (HL = верх столбца), ret +2 (назад в ps_col)
; Баланс нулевой: SP на входе в столбец равен SP после хвоста.

SMC_RST1        EQU     0008h   ; адрес вектора RST 1
SMC_LADDER      EQU     7000h   ; страница лесенки (кратна 0x100!)
SMC_PAGE        EQU     70h     ; = SMC_LADDER >> 8
SMC_LAST        EQU     80h     ; младший байт хвоста (SMC_LADDER + 128)
SMC_ROWS        EQU     32      ; строк лесенки = максимальный LEN

; ---------------------------------------------------------------
; Обработчик RST 1 — образец, копируется в 0x0008 при старте.
; Вход: DE = [SHIFT][LEN][LEN байт], HL = верх столбца в VRAM.
; Выход: DE — за байтами столбца, HL = верх столбца (как на входе).
; ---------------------------------------------------------------
rst1_proto:
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
rst1_end:
; Смещение rs_nb внутри обработчика: по нему _smc_init правит операнд jnc,
; иначе копия прыгает в прототип (работает лишь пока код позиционно-независим).
RS_NB_OFF       EQU     rs_nb - rst1_proto

; ---------------------------------------------------------------
; void smc_init(void) — разложить обработчик и лесенку по адресам.
; Зовётся один раз из main() до первого draw_sprite_smc.
; ---------------------------------------------------------------
_smc_init:
        ; 1) обработчик -> 0x0008
        lxi     h, rst1_proto
        lxi     d, SMC_RST1
        mvi     b, rst1_end - rst1_proto
sc_h:
        mov     a, m
        stax    d
        inx     h
        inx     d
        dcr     b
        jnz     sc_h

        ; 2) операнд jnc в копии -> rs_nb копии (прототип остаётся как есть)
        mvi     a, SMC_RST1 + RS_NB_OFF ; младший байт адреса входа в копии
        sta     SMC_RST1 + RS_NB_OFF - 3
        mvi     a, 0            ; адрес < 0x100, старший байт нулевой
        sta     SMC_RST1 + RS_NB_OFF - 2

        ; 3) лесенка -> 0x7000: SMC_ROWS строк по 4 байта + хвост pop h / ret
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
        ret

; Шаблон одной строки лесенки (только копируется, не исполняется).
ladder_row:
        ldax    d               ; байт данных
        mov     m, a            ; -> VRAM
        inx     d               ; следующая строка данных
        dcx     h               ; адрес в VRAM убывает вниз по экрану

; ---------------------------------------------------------------
; void draw_sprite_smc(unsigned char x, unsigned int y,
;                      const unsigned char *desc)
; Flat-вывод через RST 1; формат дескриптора — как у draw_sprite_new.
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
; plane_smc — одна плоскость через RST 1
; Вход: B = cols (счётчик), HL = верх левого столбца, DE = данные.
; ---------------------------------------------------------------
plane_smc:
        lhld    _rn_data
        xchg                    ; DE = курсор данных столбцов
        lhld    _rn_dst         ; HL = верх левого столбца
        lda     _rn_cols
        mov     b, a
ps_col:
        defb    0CFh            ; RST 1 (адрес 0x0008). Байтом, а не `rst 08h`:
                                ; asm80 требует адрес, а тест-ассемблер
                                ; utils/emulator — номер вектора.
        inr     h               ; следующий столбец +0x100
        dcr     b
        jnz     ps_col
        xchg                    ; HL = DE (продвинутый курсор данных)
        shld    _rn_data
        ret

