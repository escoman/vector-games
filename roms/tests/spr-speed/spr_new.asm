; spr_new.asm — новый алгоритм отрисовки спрайтов (SPR_FORMAT) для 8080
; Формат дескриптора: [FLAGS, COLS, DEPTH] + DATA
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

        SECTION code_clib
        PUBLIC  _draw_sprite_new
        PUBLIC  _erase_sprite_box

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
