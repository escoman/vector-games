; mario.asm — горячий путь демки Mario 16-цвет для Вектора-06Ц.
;
;   void render_window(unsigned int cam, unsigned char blk0, unsigned char nblk)
;       — зарисовка nblk экранных блоков (столбцов по 8 пикселей), начиная с
;         blk0, из тайлкарты уровня. cam — номер мирового тайлового столбца у
;         левого края экрана. render_window(cam,0,32) — весь экран.
;
;   void mario_draw(unsigned char x, unsigned char y, const unsigned char *spr)
;       — спрайт 16x16 с маской поверх фона в 16-цветном режиме. x кратно 8.
;
; Формат Вектора: плоскости вес 8/4/2/1 в 0x8000/0xA000/0xC000/0xE000; блок =
; x/8 (256 байт), байт i хранит строку y = 255 - i (строки сверху вниз идут по
; УБЫВАЮЩЕМУ адресу), старший бит байта = левый пиксель.
;
; Тайл 8x8 (tileset): 4 плоскости по 8 байт, порядок весов 8,4,2,1; в плоскости
; строки 0..7 сверху вниз. 32 байта на тайл.
; Тайлкарта (tilemap): tilemap[мировой_столбец*32 + строка] — индекс тайла;
; колонками, чтобы экранный блок читался 32 байтами подряд.
;
; Спрайт 16x16 (mario.inc): mask[32] (колонками: col0 строки 0..15, col1 строки
; 0..15), затем 4 плоскости по 32 байта тем же порядком (вес 8,4,2,1). Итого
; 160 байт. Композиция по плоскостям: res = old ^ ((old ^ src) & mask).
;
; Соглашение вызова z88dk classic (__z88dk_callee): аргументы в 16-битных
; слотах, callee чистит стек. Только инструкции Intel 8080.

        SECTION code_clib

        PUBLIC  _render_window
        PUBLIC  _mario_draw

        EXTERN  _tileset
        EXTERN  _tilemap

ROWS EQU 32                 ; тайлов по высоте экрана (256/8)

; ---------------------------------------------------------------
; BSS — рабочие переменные.
; ---------------------------------------------------------------
        SECTION bss_clib

; --- render_window ---
rw_cam:     defw    0
rw_blk:     defb    0           ; текущий экранный блок
rw_end:     defb    0           ; последний блок (exclusive)
rw_p:       defb    0
rw_poff:    defb    0
rw_row:     defb    0
rw_srccol:  defw    0           ; &tilemap[wc*32] — начало колонки
rw_src:     defw    0           ; текущий указатель в tilemap
rw_dst:     defw    0           ; текущий VRAM-адрес

; --- mario_draw ---
md_xblk:    defb    0
md_ytop:    defb    0           ; 255 - y
md_spr:     defw    0
md_p:       defb    0
md_c:       defb    0
md_msk:     defw    0
md_src:     defw    0
md_dst:     defw    0
md_cnt:     defb    0

; Старшие байты баз плоскостей по весам 8,4,2,1 (адрес = base<<8 | смещение).
vram_bases: defb    080h, 0A0h, 0C0h, 0E0h

; ---------------------------------------------------------------
; void render_window(unsigned int cam, unsigned char blk0, unsigned char nblk)
; ---------------------------------------------------------------
        SECTION code_clib

_render_window:
        ; sccz80 classic: аргументы пушатся слева направо, поэтому arg1 (cam)
        ; дальше всего от SP. Итого: nblk (sp+2), blk0 (sp+4), cam (sp+6).
        lxi     h,6
        dad     sp
        mov     a,m             ; cam lo
        mov     c,a
        inx     h
        mov     h,m             ; cam hi
        mov     l,a
        shld    rw_cam          ; (clobbers HL — offsets ниже пересчитываем)
        lxi     h,4
        dad     sp
        mov     a,m             ; blk0
        sta     rw_blk
        mov     c,a             ; C = blk0
        lxi     h,2
        dad     sp
        mov     a,m             ; nblk
        add     c               ; end = blk0 + nblk
        sta     rw_end

        push    b
        push    d
        push    h
rw_blk_loop:
        call    _rw_do_block
        lda     rw_blk
        inr     a
        sta     rw_blk
        mov     e,a
        lda     rw_end
        cmp     e
        jnz     rw_blk_loop
        pop     h
        pop     d
        pop     b

        pop     de              ; адрес возврата
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp              ; съесть cam, blk0, nblk (6 байт)
        push    de
        ret

; ---------------------------------------------------------------
; _rw_do_block — зарисовать один экранный блок rw_blk.
; Разрушает A, BC, DE, HL.
; ---------------------------------------------------------------
_rw_do_block:
        ; rw_srccol = &tilemap[(cam+blk)*32]
        lda     rw_blk
        mov     e,a
        mvi     d,0
        lhld    rw_cam
        dad     d               ; HL = wc (16-бит, до 382)
        dad     h
        dad     h
        dad     h
        dad     h
        dad     h               ; HL = wc*32
        lxi     d,_tilemap
        dad     d
        shld    rw_srccol

        xra     a
        sta     rw_p
rw_p_loop:
        ; poff = p*8
        lda     rw_p
        add     a
        add     a
        add     a               ; A = p*8
        sta     rw_poff
        ; dst = (vram_bases[p] + blk)<<8 | 255
        lda     rw_p
        mov     l,a
        mvi     h,0
        lxi     d,vram_bases
        dad     d               ; HL = &vram_bases[p]
        mov     e,m             ; E = base_hi (читаём прямо из (HL), не через A)
        lda     rw_blk          ; A = blk
        add     e               ; A = base_hi + blk
        mov     h,a
        mvi     l,255
        shld    rw_dst
        ; src = rw_srccol (с начала колонки)
        lhld    rw_srccol
        shld    rw_src
        xra     a
        sta     rw_row

rw_row_loop:
        ; t = *(src)++
        lhld    rw_src
        mov     a,m
        inx     h
        shld    rw_src
        ; HL = _tileset + t*32 + poff
        mov     l,a
        mvi     h,0
        dad     h
        dad     h
        dad     h
        dad     h
        dad     h               ; t*32
        lda     rw_poff
        add     l
        mov     l,a             ; + poff (без переноса)
        lxi     d,_tileset
        dad     d               ; HL = адрес тайла в tileset
        xchg                    ; DE = источник (tileset), HL = мусор
        lhld    rw_dst          ; HL = VRAM-назначение
        ; 8 байт: (DE)->(HL), DE++, HL--
        ldax    d
        mov     m,a
        inx     d
        dcx     h
        ldax    d
        mov     m,a
        inx     d
        dcx     h
        ldax    d
        mov     m,a
        inx     d
        dcx     h
        ldax    d
        mov     m,a
        inx     d
        dcx     h
        ldax    d
        mov     m,a
        inx     d
        dcx     h
        ldax    d
        mov     m,a
        inx     d
        dcx     h
        ldax    d
        mov     m,a
        inx     d
        dcx     h
        ldax    d
        mov     m,a
        dcx     h
        shld    rw_dst

        lda     rw_row
        inr     a
        sta     rw_row
        cpi     ROWS
        jnz     rw_row_loop

        lda     rw_p
        inr     a
        sta     rw_p
        cpi     4
        jnz     rw_p_loop
        ret

; ---------------------------------------------------------------
; void mario_draw(unsigned char x, unsigned char y, const unsigned char *spr)
; ---------------------------------------------------------------
_mario_draw:
        ; sccz80 classic: arg1 (x) дальше всего от SP. Итого:
        ; spr (sp+2), y (sp+4), x (sp+6).
        lxi     h,6
        dad     sp
        mov     a,m             ; x
        rra
        rra
        rra
        ani     1Fh             ; x/8 (0..31)
        sta     md_xblk
        lxi     h,4
        dad     sp
        mov     a,m             ; y
        cma                     ; 255 - y
        sta     md_ytop
        lxi     h,2
        dad     sp
        mov     a,m             ; spr lo
        mov     c,a
        inx     h
        mov     h,m             ; spr hi
        mov     l,a
        shld    md_spr

        push    b
        push    d
        push    h
        xra     a
        sta     md_p
md_p_loop:
        xra     a
        sta     md_c
md_c_loop:
        ; md_msk = spr + c*16
        lda     md_c
        add     a
        add     a
        add     a
        add     a               ; c*16
        mov     e,a
        mvi     d,0
        lhld    md_spr
        dad     d
        shld    md_msk

        ; md_src = spr + 32 + p*32 + c*16
        lda     md_p
        add     a
        add     a
        add     a
        add     a
        add     a               ; p*32
        mov     e,a
        lda     md_c
        add     a
        add     a
        add     a
        add     a               ; c*16
        add     e               ; p*32 + c*16
        adi     32              ; + mask[32]
        mov     e,a
        mvi     d,0
        lhld    md_spr
        dad     d
        shld    md_src

        ; md_dst = (vram_bases[p] + xblk + c)<<8 | ytop
        ; ВНИМАНИЕ: lxi d, vram_bases затирает E (младший байт адреса метки),
        ; поэтому смещение блока (xblk + c) считаем ПОСЛЕ lxi — как в _rw_do_block.
        lda     md_p
        mov     l,a
        mvi     h,0
        lxi     d,vram_bases
        dad     d               ; HL = &vram_bases[p]
        mov     a,m             ; A = base_hi
        mov     l,a             ; L = base_hi (lxi уже отработал, L не затирается)
        lda     md_xblk
        mov     e,a             ; E = xblk
        lda     md_c
        add     e               ; A = c + xblk
        add     l               ; A = base_hi + xblk + c
        mov     h,a
        lda     md_ytop
        mov     l,a
        shld    md_dst

        mvi     a,16
        sta     md_cnt
md_px_loop:
        ; m = *(msk)++
        lhld    md_msk
        mov     a,m
        inx     h
        shld    md_msk
        mov     c,a             ; C = mask
        ; s = *(src)++
        lhld    md_src
        mov     a,m
        inx     h
        shld    md_src
        mov     b,a             ; B = src
        ; res = old ^ ((old ^ src) & mask)
        lhld    md_dst
        mov     a,m             ; A = old
        mov     d,a             ; D = old
        mov     a,b             ; A = src
        xra     d               ; src ^ old
        mov     e,c             ; E = mask
        ana     e               ; (src^old) & mask
        xra     d               ; ^ old
        mov     m,a             ; (dst) = res
        dcx     h
        shld    md_dst

        lda     md_cnt
        dcr     a
        sta     md_cnt
        jnz     md_px_loop

        lda     md_c
        inr     a
        sta     md_c
        cpi     2
        jnz     md_c_loop
        lda     md_p
        inr     a
        sta     md_p
        cpi     4
        jnz     md_p_loop

        pop     h
        pop     d
        pop     b
        pop     de              ; адрес возврата
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp              ; съесть x, y, spr (6 байт)
        push    de
        ret
