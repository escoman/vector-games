;
; clr.asm — заполнение плоскостей VRAM Вектора-06Ц.
;
;   void graph_fill_planes(unsigned char mask, unsigned char fill)
;       __z88dk_callee
;
;   Заполняет 8 КБ каждой плоскости, у которой бит в mask
;   установлен. Плоскости (от старшего адреса к младшему):
;     bit 0 → 0xE000, bit 1 → 0xC000, bit 2 → 0xA000,
;     bit 3 → 0x8000.
;   fill: 0x00 — залить нулями, 0xFF — залить единицами.
;
; Алгоритм: 4 итерации (по числу плоскостей). На каждой — сдвигаем
; маску rrca, проверяем бит. Если установлен — заливаем 8 КБ
; (32 страницы по 256 байт, 8 байт за итерацию).
;
; Регистры: C — маска (сдвигается), E — байт заливки,
; B — счётчик страниц/плоскостей, HL — текущий адрес.
;
; Только 8080-инструкции: без jr/djnz и без префиксов CB/DD/ED/FD.
;

        SECTION code_clib
        PUBLIC  _graph_fill_planes

; ---------------------------------------------------------------
; void graph_fill_planes(unsigned char mask, unsigned char fill)
;   __z88dk_callee
;
; Быстрая заливка экранных плоскостей Вектора-06Ц через PUSH.
;
; mask:
;   01h -> 0E000h-0FFFFh
;   02h -> 0C000h-0DFFFh
;   04h -> 0A000h-0BFFFh
;   08h -> 08000h-09FFFh
;
; fill:
;   байт заполнения.
;
; Один PUSH HL записывает 2 байта.
;
; 4096 PUSH = 8192 байта = одна плоскость.
;
; Для каждой плоскости:
;
;   B = 16
;   C = 32
;   8 × PUSH HL
;
;   16 × 32 × 8 = 4096 PUSH
;   4096 × 2 = 8192 байта
;
; ВАЖНО:
;   SP во время PUSH находится внутри VRAM.
;   Поэтому никаких CALL/RET внутри цикла заливки нет.
;
; Только инструкции Intel 8080.
; ---------------------------------------------------------------

_graph_fill_planes:
        di

        ; -------------------------------------------------------
        ; Получаем параметры __z88dk_callee.
        ;
        ; После CALL:
        ;
        ;   SP -> fill
        ;          mask
        ;          return address
        ;
        ; -------------------------------------------------------

        pop     de              ; DE = return address
        pop     hl              ; HL = fill
        pop     bc              ; BC = mask

        push    de              ; вернуть return address

        ; Сохраняем SP вызывающего.
        ld      (_saved_sp), sp

        ; Сохраняем mask.
        ld      a, c
        ld      (_fill_mask), a

        ; -------------------------------------------------------
        ; Преобразуем fill:
        ;
        ;   fill = 00 -> HL = 0000
        ;   fill = A5 -> HL = A5A5
        ;   fill = FF -> HL = FFFF
        ;
        ; После этого HL больше не изменяется.
        ; -------------------------------------------------------

        ld      a, l
        ld      h, a
        ld      l, a

        ; =======================================================
        ; ПЛОСКОСТЬ 0: E000-FFFF
        ;
        ; PUSH сначала уменьшает SP:
        ;
        ;   SP=0000
        ;   PUSH -> FFFF,FFFE
        ;
        ; Далее запись идёт вниз до E000.
        ; =======================================================

        ld      a, (_fill_mask)
        ani     01h
        jp      z, fp_skip_e000

        ld      sp, 0000h

        ld      b, 16

fp_e000_outer:
        ld      c, 32

fp_e000_inner:
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl

        dcr     c
        jp      nz, fp_e000_inner

        dcr     b
        jp      nz, fp_e000_outer

fp_skip_e000:


        ; =======================================================
        ; ПЛОСКОСТЬ 1: C000-DFFF
        ;
        ; SP = E000
        ; PUSH -> DFFF...C000
        ; =======================================================

        ld      a, (_fill_mask)
        ani     02h
        jp      z, fp_skip_c000

        ld      sp, 0E000h

        ld      b, 16

fp_c000_outer:
        ld      c, 32

fp_c000_inner:
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl

        dcr     c
        jp      nz, fp_c000_inner

        dcr     b
        jp      nz, fp_c000_outer

fp_skip_c000:


        ; =======================================================
        ; ПЛОСКОСТЬ 2: A000-BFFF
        ;
        ; SP = C000
        ; PUSH -> BFFF...A000
        ; =======================================================

        ld      a, (_fill_mask)
        ani     04h
        jp      z, fp_skip_a000

        ld      sp, 0C000h

        ld      b, 16

fp_a000_outer:
        ld      c, 32

fp_a000_inner:
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl

        dcr     c
        jp      nz, fp_a000_inner

        dcr     b
        jp      nz, fp_a000_outer

fp_skip_a000:


        ; =======================================================
        ; ПЛОСКОСТЬ 3: 8000-9FFF
        ;
        ; SP = A000
        ; PUSH -> 9FFF...8000
        ; =======================================================

        ld      a, (_fill_mask)
        ani     08h
        jp      z, fp_skip_8000

        ld      sp, 0A000h

        ld      b, 16

fp_8000_outer:
        ld      c, 32

fp_8000_inner:
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl
        push    hl

        dcr     c
        jp      nz, fp_8000_inner

        dcr     b
        jp      nz, fp_8000_outer

fp_skip_8000:


        ; -------------------------------------------------------
        ; Восстанавливаем SP вызывающего.
        ; -------------------------------------------------------

        ld      hl, (_saved_sp)
        ld      sp, hl

        ei
        ret


; ---------------------------------------------------------------
; Рабочие переменные.
;
; Они должны находиться вне VRAM.
; ---------------------------------------------------------------

_fill_mask:
        defb    0

_saved_sp:
        defw    0