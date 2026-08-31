;
; clr.asm — заполнение плоскостей VRAM Вектора-06Ц.
;
; Две функции:
;
;   void graph_fill_plane(unsigned char mask, unsigned char fill);
;       Заполняет 8 КБ каждой плоскости, у которой бит в mask
;       установлен. Плоскости (от старшего адреса к младшему):
;         bit 0 → 0xE000, bit 1 → 0xC000, bit 2 → 0xA000,
;         bit 3 → 0x8000.
;       fill: 0x00 — залить нулями, 0xFF — залить единицами.
;
;   void graph_clear(unsigned char color);
;       Совместимость: заполняет все 4 плоскости.
;       Эквивалент graph_fill_plane(0x0F, color >= 8 ? 0xFF : 0x00).
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
        PUBLIC  _graph_fill_plane
        PUBLIC  _graph_clear

; ---------------------------------------------------------------
; void graph_fill_plane(unsigned char mask, unsigned char fill)
;
; mask: sp+2 (16-битный слот, значение в младшем байте)
; fill: sp+4 (16-битный слот, значение в младшем байте)
; ---------------------------------------------------------------
_graph_fill_plane:
        ld      hl, 2
        add     hl, sp
        ld      c, (hl)         ; C = маска плоскостей
        ld      hl, 4
        add     hl, sp
        ld      e, (hl)         ; E = байт заливки (0x00 или 0xFF)

        ld      b, 4            ; B = счётчик плоскостей
        ld      h, 0xE0         ; HL = 0xE000 (первая плоскость)
        ld      l, 0

fp_loop:
        ld      a, c
        rra                     ; проверяем младший бит маски
        ld      c, a            ; сохраняём сдвинутую маску
        jp      nc, fp_skip     ; бит 0 — пропускаем плоскость

        ; заливаем 8 КБ по HL байтом E
        push    bc
        ld      a, e
        ld      b, 0x20         ; 32 страницы
fp_page:
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        jp      nz, fp_page     ; L не обнулился — страница не кончилась
        inc     h               ; следующая страница
        dec     b
        jp      nz, fp_page
        pop     bc

fp_skip:
        ld      a, h
        sub     0x20            ; переход к следующей плоскости (адрес уменьшается)
        ld      h, a
        dec     b
        jp      nz, fp_loop
        ret

; ---------------------------------------------------------------
; void graph_clear(unsigned char color)
;
; Совместимость: color на sp+2. Заполняет все 4 плоскости.
; Делегирует graph_fill_plane(0x0F, fill).
; ---------------------------------------------------------------
_graph_clear:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)         ; A = color
        ; байт заливки: если бит 3 (вес 8) установлен → 0xFF
        and     0x08
        ld      e, 0x00
        jp      z, clr_go
        ld      e, 0xFF
clr_go:
        ld      c, 0x0F         ; маска: все 4 плоскости
        ld      b, 4
        ld      h, 0xE0
        ld      l, 0

clr_loop:
        ld      a, c
        rra
        ld      c, a
        jp      nc, clr_skip

        push    bc
        ld      a, e
        ld      b, 0x20
clr_page:
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        ld      (hl), a
        inc     l
        jp      nz, clr_page
        inc     h
        dec     b
        jp      nz, clr_page
        pop     bc

clr_skip:
        ld      a, h
        sub     0x20
        ld      h, a
        dec     b
        jp      nz, clr_loop
        ret
