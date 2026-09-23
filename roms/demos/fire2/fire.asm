; fire.asm — огонь 64×40 → 256×256 для Вектора-06Ц.
;
; Точная реализация алгоритма из main.c (см. main.c.old) на 8080-ассемблере.
; Все три функции — __z88dk_callee (вызывающая сторона кладёт аргументы,
; callee чистит стек).
;
;   void rnd_init(void)                      — ГСЧ-таблица + обнуление буферов
;   void fire_generate(unsigned char power)  — генерация кадра огня
;   void fire_render(void)                   — вывод на экран (теневой буфер)
;
; Буфер: 2 точки по 4 бита в одном байте. FIRE_W=64, FIRE_H=40.
;   размер = (64*40)/2 = 1280 байт, строка = 32 байта.
;   старшая тетрада = левый (чётный x) пиксель, младшая = правый (нечётный x).
;
; Только инструкции Intel 8080 (без jr/djnz, без префиксов CB/DD/ED/FD).

        PUBLIC  _rnd_init
        PUBLIC  _fire_generate
        PUBLIC  _fire_render

FIRE_W  EQU 64
FIRE_H  EQU 40
BUFLEN  EQU (FIRE_W * FIRE_H) >> 1      ; 1280 байт
ROWB    EQU FIRE_W >> 1                 ; 32 байта на строку
HALFH   EQU FIRE_H >> 1                 ; 20 — порог доп. затухания

; ================================================================
; BSS — массивы и рабочие переменные (вне VRAM).
; ================================================================
        SECTION bss_clib
        ALIGN 256
_rnd_table:     defs 256                ; таблица ГСЧ
_rnd_mod3:      defs 256                ; rnd_mod3[v] = v % 3
_rnd_idx:       defb 0                  ; индекс ГСЧ (авто-обёртка на 256)
_rnd_seed:      defw 0                  ; 16-битное семя LCG
_rnd_tmp:       defb 0

_fire_buf:      defs BUFLEN             ; текущий кадр (упакованные тетрады)
_prev_buf:      defs BUFLEN             ; теневая копия (что уже в VRAM)

; --- fire_generate ---
_fg_power:      defb 0
_fg_x:          defb 0
_fg_y:          defb 0
_fg_above:      defb 0
_fg_decay:      defb 0
_fg_srcx:       defb 0
_fg_value:      defb 0
_fg_above_ptr:  defw 0
_fg_dest_ptr:   defw 0
_fg_merged:     defb 0                  ; старший нибл текущего байта (шаг 1б)

; --- fire_render ---
_fr_cur_ptr:    defw 0
_fr_prev_ptr:   defw 0
_fr_cur:        defb 0
_fr_prev:       defb 0
_fr_diff:       defb 0
_fr_addr:       defw 0                  ; H = col, L = fy*4
_fr_pair:       defb 0                  ; счётчик байтов в строке (32)
_fr_fy:         defb 0                  ; номер строки (0..39)
_fr_saved_sp:   defw 0

        SECTION code_clib

; ================================================================
; void rnd_init(void)  __z88dk_callee
;
;   seed = 0x1234;
;   do { seed = seed*251 + 73; rnd_table[i] = seed >> 8; } while (++i);
;   rnd_mod3[v] = v % 3;
;   rnd_idx = 0;
;   fire_buf[] = prev_buf[] = 0;   (BSS при --no-crt не обнуляется)
; ================================================================
_rnd_init:
        push    bc
        push    de
        push    hl

        xra     a
        sta     _rnd_idx
        lxi     h,0x1234
        shld    _rnd_seed
        mvi     c,0
ri_loop:
        lhld    _rnd_seed
        ; 251*x = 256*x - 5*x (mod 65536)
        push    hl
        dad     h
        dad     h
        pop     de
        dad     d               ; HL = 5*x
        push    hl
        mov     a,e
        mov     h,a
        mvi     l,0             ; HL = 256*x
        pop     de              ; DE = 5*x
        mov     a,l
        sub     e
        mov     l,a
        mov     a,h
        sbb     d
        mov     h,a             ; HL = 251*x
        lxi     d,73
        dad     d
        shld    _rnd_seed
        mov     a,h
        sta     _rnd_tmp        ; старший байт

        lxi     h,_rnd_table
        mov     e,c
        mvi     d,0
        dad     d
        lda     _rnd_tmp
        mov     m,a

        inr     c
        mov     a,c
        ora     a
        jnz     ri_loop

        ; rnd_mod3[v] = v % 3, v = 0..255
        lxi     h,_rnd_mod3
        mvi     c,0
        mvi     b,0
ri_mod_loop:
        mov     m,b
        inr     b
        mov     a,b
        cpi     3
        jnz     ri_mod_no_reset
        mvi     b,0
ri_mod_no_reset:
        inx     h
        inr     c
        mov     a,c
        ora     a
        jnz     ri_mod_loop

        xra     a
        sta     _rnd_idx

        ; Обнуление fire_buf и prev_buf (экран очищён в main).
        ; mvi m,0 не трогает A, поэтому A свободно для проверки счётчика DE.
        lxi     h,_fire_buf
        lxi     d,BUFLEN
ri_clr_fire:
        mvi     m,0
        inx     h
        dcx     d
        mov     a,d
        ora     e
        jnz     ri_clr_fire

        lxi     h,_prev_buf
        lxi     d,BUFLEN
ri_clr_prev:
        mvi     m,0
        inx     h
        dcx     d
        mov     a,d
        ora     e
        jnz     ri_clr_prev

        pop     hl
        pop     de
        pop     bc
        ret

; ================================================================
; Внутренний rnd_next(): A = rnd_table[rnd_idx++].
; Портит только HL и флаги (rnd_idx — 8 бит, обёртка автоматическая).
; ================================================================
_fg_rnd_next:
        lda     _rnd_idx
        lxi     h,_rnd_table    ; ALIGN 256 ⇒ мл. байт адреса = 00
        mov     l,a             ; HL = &_rnd_table[idx]
        inr     a
        sta     _rnd_idx        ; rnd_idx++ (8-бит обёртка)
        mov     a,m             ; A = rnd_table[idx]
        ret

; ================================================================
; void fire_generate(unsigned char power)  __z88dk_callee
; Точный алгоритм из main.c; доступ к упакованному буферу инлайнится.
; ================================================================
_fire_generate:
        push    bc
        lxi     h,4
        dad     sp
        mov     a,m
        sta     _fg_power       ; power

        ; ---- строка источников y=0 ----
        lxi     h,_fire_buf
        shld    _fg_dest_ptr
        mvi     b,0             ; B = x
fg_seed_loop:
        call    _fg_rnd_next
        sta     _fg_value
        lda     _fg_power
        mov     c,a
        lda     _fg_value
        cmp     c
        jc      fg_seed_hot     ; rnd < power → 15
        ; иначе: rnd_next() > 128 ?
        call    _fg_rnd_next
        cpi     129
        jc      fg_seed_keep    ; rnd <= 128 → оставить
        ; current > 2 ? current-2 : 0
        lhld    _fg_dest_ptr
        mov     a,m
        mov     d,a
        mov     a,b
        ani     1
        jnz     fg_seed_cur_odd
        mov     a,d
        rrc
        rrc
        rrc
        rrc
        ani     15
        jmp     fg_seed_cur_have
fg_seed_cur_odd:
        mov     a,d
        ani     15
fg_seed_cur_have:
        cpi     3
        jc      fg_seed_zero
        sui     2
        sta     _fg_value
        jmp     fg_seed_store
fg_seed_zero:
        xra     a
        sta     _fg_value
        jmp     fg_seed_store
fg_seed_hot:
        mvi     a,15
        sta     _fg_value
        jmp     fg_seed_store
fg_seed_keep:
        jmp     fg_seed_advance
fg_seed_store:
        lhld    _fg_dest_ptr
        mov     a,b
        ani     1
        jnz     fg_seed_store_odd
        lda     _fg_value
        rlc
        rlc
        rlc
        rlc
        mov     c,a
        mov     a,m
        ani     15
        ora     c
        mov     m,a
        jmp     fg_seed_advance
fg_seed_store_odd:
        mov     a,m
        ani     240
        mov     c,a
        lda     _fg_value
        ora     c
        mov     m,a
fg_seed_advance:
        mov     a,b
        ani     1
        jz      fg_seed_no_ptr_inc
        lhld    _fg_dest_ptr
        inx     h
        shld    _fg_dest_ptr
fg_seed_no_ptr_inc:
        inr     b
        mov     a,b
        cpi     FIRE_W
        jnz     fg_seed_loop

        ; ---- строки y = 1 .. FIRE_H-1 ----
        lxi     h,_fire_buf
        shld    _fg_above_ptr
        lxi     h,_fire_buf+ROWB
        shld    _fg_dest_ptr
        mvi     b,1
        mov     a,b
        sta     _fg_y
fg_y_loop:
        ; rnd_idx += 7 — снять периодичность ГСЧ между строками
        lda     _rnd_idx
        adi     7
        sta     _rnd_idx

        mvi     b,ROWB          ; шаг 1б: цикл по байтам (2 пикселя за итерацию)
        xra     a
        sta     _fg_x           ; _fg_x = чётный x текущего байта
fg_x_loop:
        ; ================= ЛЕВЫЙ пиксель (x = _fg_x, чётный) =================
        ; rnd_next инлайн → mod3 (сдвиг)
        lda     _rnd_idx
        lxi     h,_rnd_table    ; ALIGN 256 ⇒ мл. байт = 00, DE не портируется
        mov     l,a             ; HL = &_rnd_table[idx]
        inr     a
        sta     _rnd_idx
        mov     a,m
        mov     e,a
        mvi     d,0
        lxi     h,_rnd_mod3
        dad     d
        mov     a,m             ; 0 / 1 / 2
        cpi     0
        jnz     fgl_shift_notm
        lda     _fg_x
        ora     a
        jz      fgl_shift_wrap
        dcr     a
        jmp     fgl_shift_st
fgl_shift_wrap:
        mvi     a,FIRE_W-1
        jmp     fgl_shift_st
fgl_shift_notm:
        cpi     1
        jnz     fgl_shift_plus
        lda     _fg_x
        jmp     fgl_shift_st
fgl_shift_plus:
        lda     _fg_x
        inr     a
        cpi     FIRE_W
        jc      fgl_shift_st
        xra     a
fgl_shift_st:
        sta     _fg_srcx
        ; above = get_fire_buf(srcx, y-1)
        lhld    _fg_above_ptr
        lda     _fg_srcx
        mov     c,a
        ora     a
        rar
        mov     e,a
        mvi     d,0
        dad     d
        mov     a,m
        mov     d,a
        lda     _fg_srcx
        ani     1
        jnz     fgl_above_odd
        mov     a,d
        rrc
        rrc
        rrc
        rrc
        ani     15
        jmp     fgl_above_done
fgl_above_odd:
        mov     a,d
        ani     15
fgl_above_done:
        sta     _fg_above
        ; decay = rnd_next() & 1 (+доп. при y>=HALFH)
        lda     _rnd_idx
        lxi     h,_rnd_table    ; ALIGN 256 ⇒ мл. байт = 00, DE не портируется
        mov     l,a             ; HL = &_rnd_table[idx]
        inr     a
        sta     _rnd_idx
        mov     a,m
        ani     1
        sta     _fg_decay
        lda     _fg_y
        cpi     HALFH
        jc      fgl_no_extra
        lda     _rnd_idx
        lxi     h,_rnd_table    ; ALIGN 256 ⇒ мл. байт = 00, DE не портируется
        mov     l,a             ; HL = &_rnd_table[idx]
        inr     a
        sta     _rnd_idx
        mov     a,m
        cpi     179
        jc      fgl_no_extra
        lda     _fg_decay
        inr     a
        sta     _fg_decay
fgl_no_extra:
        ; value = (above > decay) ? above - decay : 0
        lda     _fg_above
        mov     c,a
        lda     _fg_decay
        mov     e,a
        mov     a,c
        cmp     e
        jc      fgl_zero
        sub     e
        sta     _fg_value
        jmp     fgl_have
fgl_zero:
        xra     a
        sta     _fg_value
fgl_have:
        ; сохранить value<<4 как старший нибл текущего байта
        lda     _fg_value
        rlc
        rlc
        rlc
        rlc
        sta     _fg_merged
        lda     _fg_x
        inr     a
        sta     _fg_x           ; теперь _fg_x = нечётный правый пиксель

        ; ================= ПРАВЫЙ пиксель (x = _fg_x, нечётный) =================
        lda     _rnd_idx
        lxi     h,_rnd_table    ; ALIGN 256 ⇒ мл. байт = 00, DE не портируется
        mov     l,a             ; HL = &_rnd_table[idx]
        inr     a
        sta     _rnd_idx
        mov     a,m
        mov     e,a
        mvi     d,0
        lxi     h,_rnd_mod3
        dad     d
        mov     a,m
        cpi     0
        jnz     fgr_shift_notm
        lda     _fg_x
        ora     a
        jz      fgr_shift_wrap
        dcr     a
        jmp     fgr_shift_st
fgr_shift_wrap:
        mvi     a,FIRE_W-1
        jmp     fgr_shift_st
fgr_shift_notm:
        cpi     1
        jnz     fgr_shift_plus
        lda     _fg_x
        jmp     fgr_shift_st
fgr_shift_plus:
        lda     _fg_x
        inr     a
        cpi     FIRE_W
        jc      fgr_shift_st
        xra     a
fgr_shift_st:
        sta     _fg_srcx
        lhld    _fg_above_ptr
        lda     _fg_srcx
        mov     c,a
        ora     a
        rar
        mov     e,a
        mvi     d,0
        dad     d
        mov     a,m
        mov     d,a
        lda     _fg_srcx
        ani     1
        jnz     fgr_above_odd
        mov     a,d
        rrc
        rrc
        rrc
        rrc
        ani     15
        jmp     fgr_above_done
fgr_above_odd:
        mov     a,d
        ani     15
fgr_above_done:
        sta     _fg_above
        lda     _rnd_idx
        lxi     h,_rnd_table    ; ALIGN 256 ⇒ мл. байт = 00, DE не портируется
        mov     l,a             ; HL = &_rnd_table[idx]
        inr     a
        sta     _rnd_idx
        mov     a,m
        ani     1
        sta     _fg_decay
        lda     _fg_y
        cpi     HALFH
        jc      fgr_no_extra
        lda     _rnd_idx
        lxi     h,_rnd_table    ; ALIGN 256 ⇒ мл. байт = 00, DE не портируется
        mov     l,a             ; HL = &_rnd_table[idx]
        inr     a
        sta     _rnd_idx
        mov     a,m
        cpi     179
        jc      fgr_no_extra
        lda     _fg_decay
        inr     a
        sta     _fg_decay
fgr_no_extra:
        lda     _fg_above
        mov     c,a
        lda     _fg_decay
        mov     e,a
        mov     a,c
        cmp     e
        jc      fgr_zero
        sub     e
        sta     _fg_value
        jmp     fgr_have
fgr_zero:
        xra     a
        sta     _fg_value
fgr_have:
        ; собрать полный байт (merged | младший нибл) и записать ОДНО mov m,a
        lda     _fg_value
        ani     15
        mov     c,a
        lda     _fg_merged
        ora     c
        lhld    _fg_dest_ptr
        mov     m,a
        inx     h
        shld    _fg_dest_ptr
        lda     _fg_x
        inr     a               ; следующий чётный x
        sta     _fg_x
        dcr     b
        jnz     fg_x_loop

        ; следующая строка
        lhld    _fg_dest_ptr
        lxi     d,0-ROWB        ; -32: строка, которую только что закончили
        dad     d
        shld    _fg_above_ptr
        lxi     d,ROWB          ; +32: следующая целевая строка
        dad     d
        shld    _fg_dest_ptr
        lda     _fg_y
        inr     a
        sta     _fg_y
        cpi     FIRE_H
        jnz     fg_y_loop

        pop     bc
        pop     de              ; адрес возврата
        inx     sp
        inx     sp              ; съесть power
        push    de
        ret

; ================================================================
; void fire_render(void)  __z88dk_callee
;
; Теневой буфер: идём по fire_buf и prev_buf параллельно.
;   cur == prev → блок не менялся, VRAM не трогаем.
;   иначе: prev_buf[idx] = cur; diff = cur ^ prev.
;   Для каждой плоскости p (0..3): если diff & mask_p — пишем 4 одинаковых
;   байта byte_val (из текущего цвета) через PUSH BC ×2 (SP-hijack).
;   Маски плоскостей: 0=11h, 1=22h, 2=44h, 3=88h
;   (бит 4+p — левый пиксель, бит p — правый).
;
; block_addr = col*256 + fy*4;  col = idx & 31, fy = idx >> 5.
; Базы плоскостей: E000 / C000 / A000 / 8000.
; ================================================================
_fire_render:
        di

        lxi     h,0
        dad     sp
        shld    _fr_saved_sp
        push    bc
        push    de
        push    hl

        lxi     h,_fire_buf
        shld    _fr_cur_ptr
        lxi     h,_prev_buf
        shld    _fr_prev_ptr
        xra     a
        sta     _fr_addr+1      ; H = col = 0
        sta     _fr_fy
        mvi     a,4
        sta     _fr_addr        ; L = fy*4 + 4: SP-hijack пишет ВНИЗ,
                                ; поэтому SP = block_addr+4 → байты block..block+3

fr_y_loop:
        mvi     a,ROWB
        sta     _fr_pair
fr_pair_loop:
        lhld    _fr_cur_ptr
        mov     a,m
        sta     _fr_cur
        lhld    _fr_prev_ptr
        mov     a,m
        sta     _fr_prev

        ; cur == prev → пропуск блока (VRAM не трогаем)
        lhld    _fr_cur_ptr
        mov     a,m
        lhld    _fr_prev_ptr
        cmp     m
        jz      fr_pair_next

        ; diff = cur ^ prev — по сохранённым значениям, ДО перезаписи тени
        lda     _fr_cur
        mov     b,a
        lda     _fr_prev
        xra     b
        sta     _fr_diff

        ; prev_buf[idx] = cur (ленивое обновление тени)
        lhld    _fr_prev_ptr
        lda     _fr_cur
        mov     m,a

        ; ---- плоскость 0: маска 11h, база E000 ----
        lda     _fr_diff
        ani     11h
        jz      fr1_build
        xra     a
        mov     b,a
        lda     _fr_cur
        ani     10h
        jz      fr0_lo
        mov     a,b
        ori     0F0h
        mov     b,a
fr0_lo:
        lda     _fr_cur
        ani     01h
        jz      fr0_wr
        mov     a,b
        ori     0Fh
        mov     b,a
fr0_wr:
        mov     c,b             ; C = byte_val (B уже собран; A здесь не reliably)
        lhld    _fr_addr
        mvi     a,0E0h
        add     h
        mov     h,a
        sphl
        push    bc
        push    bc

        ; ---- плоскость 1: маска 22h, база C000 ----
fr1_build:
        lda     _fr_diff
        ani     22h
        jz      fr2_build
        xra     a
        mov     b,a
        lda     _fr_cur
        ani     20h
        jz      fr1_lo
        mov     a,b
        ori     0F0h
        mov     b,a
fr1_lo:
        lda     _fr_cur
        ani     02h
        jz      fr1_wr
        mov     a,b
        ori     0Fh
        mov     b,a
fr1_wr:
        mov     c,b             ; C = byte_val
        lhld    _fr_addr
        mvi     a,0C0h
        add     h
        mov     h,a
        sphl
        push    bc
        push    bc

        ; ---- плоскость 2: маска 44h, база A000 ----
fr2_build:
        lda     _fr_diff
        ani     44h
        jz      fr3_build
        xra     a
        mov     b,a
        lda     _fr_cur
        ani     40h
        jz      fr2_lo
        mov     a,b
        ori     0F0h
        mov     b,a
fr2_lo:
        lda     _fr_cur
        ani     04h
        jz      fr2_wr
        mov     a,b
        ori     0Fh
        mov     b,a
fr2_wr:
        mov     c,b             ; C = byte_val
        lhld    _fr_addr
        mvi     a,0A0h
        add     h
        mov     h,a
        sphl
        push    bc
        push    bc

        ; ---- плоскость 3: маска 88h, база 8000 ----
fr3_build:
        lda     _fr_diff
        ani     88h
        jz      fr_pair_next
        xra     a
        mov     b,a
        lda     _fr_cur
        ani     80h
        jz      fr3_lo
        mov     a,b
        ori     0F0h
        mov     b,a
fr3_lo:
        lda     _fr_cur
        ani     08h
        jz      fr3_wr
        mov     a,b
        ori     0Fh
        mov     b,a
fr3_wr:
        mov     c,b             ; C = byte_val
        lhld    _fr_addr
        mvi     a,80h
        add     h
        mov     h,a
        sphl
        push    bc
        push    bc

fr_pair_next:
        lhld    _fr_cur_ptr
        inx     h
        shld    _fr_cur_ptr
        lhld    _fr_prev_ptr
        inx     h
        shld    _fr_prev_ptr
        lhld    _fr_addr
        inr     h               ; col++
        shld    _fr_addr
        lda     _fr_pair
        dcr     a
        sta     _fr_pair
        jnz     fr_pair_loop

        ; конец строки: col = 0, fy*4 += 4
        lhld    _fr_addr
        mvi     h,0
        mov     a,l
        adi     4
        mov     l,a
        shld    _fr_addr
        lda     _fr_fy
        inr     a
        sta     _fr_fy
        cpi     FIRE_H
        jnz     fr_y_loop

        ; восстановить SP и кадр сохранённых регистров
        lhld    _fr_saved_sp
        dcx     h
        dcx     h
        dcx     h
        dcx     h
        dcx     h
        dcx     h
        sphl
        pop     hl
        pop     de
        pop     bc
        ei
        ret
