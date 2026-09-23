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
; fire_buf — «байт на пиксель»: 64*40 = 2560 байт, значение 0..15, строка 64.
; prev_buf (тень рендера) — упакованная, 1280 байт: 2 точки по 4 бита,
;   старшая тетрада = левый (чётный x), младшая = правый (нечётный x).
; Упаковка в тетрады нужна только для записи в плоскости VRAM — делает fire_render.
;
; Только инструкции Intel 8080 (без jr/djnz, без префиксов CB/DD/ED/FD).

        PUBLIC  _rnd_init
        PUBLIC  _fire_generate
        PUBLIC  _fire_render

FIRE_W  EQU 64
FIRE_H  EQU 40
BUFLEN  EQU FIRE_W * FIRE_H             ; 2560 — fire_buf, 1 пиксель/байт
PREVLEN EQU (FIRE_W * FIRE_H) >> 1      ; 1280 — упакованная тень prev_buf
ROWW    EQU FIRE_W                      ; 64 пикселя в строке (генератор)
ROWB    EQU FIRE_W >> 1                 ; 32 VRAM-байта/строка (рендер)
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

_fire_buf:      defs BUFLEN             ; текущий кадр (байт на пиксель, 0..15)
_prev_buf:      defs PREVLEN            ; теневая копия рендера (упакованные тетрады)

; --- fire_generate ---
; Указатели строк живут в регистрах весь цикл (пункт 1д):
;   DE = dest (пишемый пиксель), BC = above_base (base строки y-1).
;   _fg_rnd_next портит лишь A/HL ⇒ BC/DE переживают вызовы ГСЧ.
;   Ни _fg_above_ptr, ни _fg_srcx, ни _fg_dest_ptr не нужны.
_fg_power:      defb 0
_fg_x:          defb 0
_fg_y:          defb 0
_fg_above:      defb 0
_fg_decay:      defb 0

; --- fire_render ---
_fr_cur_ptr:    defw 0                  ; cur-указатель (HL, грузится/инкрементится в прологе)
_fr_prev_ptr:   defw 0                  ; prev-указатель (HL, грузится/инкрементится в прологе)
_fr_cur:        defb 0
_fr_diff:       defb 0
                                        ; Адрес блока живёт в DE — D = col (0..31),
                                        ; E = fylo (fy*4). Прямые stores в VRAM, SP не
                                        ; перехватываем. Ни _fr_addr, ни _fr_pair не нужны.
_fr_fy:         defb 0                  ; номер строки (0..39)

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
        lxi     d,PREVLEN
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
; Точный алгоритм из main.c; доступ к распакованному буферу инлайнится,
; указатели строк — в DE (dest) и BC (above_base), без lhld/shld на пиксель.
; ================================================================
_fire_generate:
        push    bc
        lxi     h,4
        dad     sp
        mov     a,m
        sta     _fg_power       ; power

        ; ---- строка источников y=0 (распакованная: 1 пиксель/байт) ----
        ; DE = dest (пиксель строки 0), B = x. _fg_rnd_next портит лишь A/HL.
        lxi     d,_fire_buf
        mvi     b,0             ; B = x
fg_seed_loop:
        lda     _fg_power
        mov     c,a
        call    _fg_rnd_next            ; A = rnd1
        cmp     c                       ; rnd1 < power ?
        jc      fg_seed_hot
        call    _fg_rnd_next            ; A = rnd2
        cpi     129
        jc      fg_seed_next            ; rnd2 <= 128 → оставить значение
        ldax    d                       ; A = cur
        cpi     3
        jc      fg_seed_zero
        sui     2                       ; cur - 2
        jmp     fg_seed_w
fg_seed_zero:
        xra     a
fg_seed_w:
        stax    d                       ; cur = value
        jmp     fg_seed_next
fg_seed_hot:
        mvi     a,15
        stax    d                       ; = 15
fg_seed_next:
        inx     d                       ; dest++ (распакованно: +1 на пиксель)
        inr     b
        mov     a,b
        cpi     FIRE_W
        jnz     fg_seed_loop

        ; ---- строки y = 1 .. FIRE_H-1 (распакованные) ----
        ; Регистры на весь цикл строк (пункт 1д):
        ;   DE = dest       — пишемый пиксель строки y, +1 на пиксель
        ;   BC = above_base — base предыдущей строки y-1 (_fire_buf+(y-1)*64),
        ;                     constant внутри строки, +64 на строку.
        ; _fg_rnd_next портит только A/HL ⇒ BC/DE переживают вызовы ГСЧ,
        ; поэтому above-адрес собирается как HL = BC + sx без lhld/shld.
        lxi     b,_fire_buf             ; above_base для y=1 = строка 0
        mvi     a,1
        sta     _fg_y
fg_y_loop:
        ; rnd_idx += 7 — снять периодичность ГСЧ между строками
        lda     _rnd_idx
        adi     7
        sta     _rnd_idx
        xra     a
        sta     _fg_x                   ; x = 0
fg_x_loop:
        ; shift = rnd % 3;  sx = x + shift - 1 (wrap 0..63)
        call    _fg_rnd_next            ; A = rnd (портит A/HL)
        lxi     h,_rnd_mod3             ; ALIGN 256 ⇒ мл. байт 00
        mov     l,a                     ; HL = &_rnd_mod3[rnd]
        mov     a,m                     ; A = shift ∈ {0,1,2}
        mov     h,a                     ; H = shift (L больше не нужен)
        lda     _fg_x
        add     h                       ; A = x + shift
        sui     1                       ; A = x + shift - 1 (CY если x+shift==0)
        jc      fg_sx_wrap63
        cpi     FIRE_W
        jz      fg_sx_wrap0
        jmp     fg_sx_done
fg_sx_wrap63:
        mvi     a,FIRE_W-1              ; 63
        jmp     fg_sx_done
fg_sx_wrap0:
        xra     a                       ; 0
fg_sx_done:
        ; above = *(above_base + sx) = *(BC + A);  HL := BC + sx
        add     c                       ; A = sx + above_base_lo
        mov     l,a
        mov     a,b
        aci     0                       ; старший байт + перенос
        mov     h,a                     ; HL = &above[sx]
        mov     a,m
        sta     _fg_above
        ; decay = rnd & 1 (+1 при y>=HALFH и rnd>178)
        call    _fg_rnd_next
        ani     1
        sta     _fg_decay
        lda     _fg_y
        cpi     HALFH
        jc      fg_no_extra
        call    _fg_rnd_next
        cpi     179
        jc      fg_no_extra
        lda     _fg_decay
        inr     a
        sta     _fg_decay
fg_no_extra:
        ; value = above > decay ? above - decay : 0  (HL свободен — temps в H/L)
        lda     _fg_above
        mov     l,a                     ; L = above
        lda     _fg_decay
        mov     h,a                     ; H = decay
        mov     a,l                     ; A = above
        cmp     h                       ; above vs decay
        jc      fg_x_zero
        sub     h                       ; above - decay
        jmp     fg_x_store
fg_x_zero:
        xra     a
fg_x_store:
        stax    d                       ; *dest = value
        inx     d                       ; dest++
        lda     _fg_x
        inr     a
        sta     _fg_x
        cpi     FIRE_W
        jnz     fg_x_loop

        ; следующая строка: DE уже на базе следующей; above_base (BC) += 64
        lda     _fg_y
        inr     a
        sta     _fg_y
        cpi     FIRE_H
        jz      fg_gend
        mov     a,c
        adi     ROWW                    ; above_base_lo += 64
        mov     c,a
        jnc     fg_no_carry
        inr     b
fg_no_carry:
        jmp     fg_y_loop

fg_gend:

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
;   байта byte_val (из текущего цвета) прямыми stores (mov m,a / inx h).
;   SP не перехватываем → прерывания не запрещаем (di/ei не нужны).
;   Маски плоскостей: 0=11h, 1=22h, 2=44h, 3=88h
;   (бит 4+p — левый пиксель, бит p — правый).
;
; block_addr = col*256 + fy*4;  col = idx & 31, fy = idx >> 5.
; Базы плоскостей: E000 / C000 / A000 / 8000.
; ================================================================
_fire_render:
        push    bc
        push    de
        push    hl

        lxi     h,_fire_buf
        shld    _fr_cur_ptr
        lxi     h,_prev_buf
        shld    _fr_prev_ptr
        ; Адрес блока в DE: D = col = 0, E = fylo = fy*4 (прямые stores пишут
        ; ВВЕРХ block..block+3). SP не трогаем → прерывания не запрещаем.
        mvi     d,0
        mvi     e,0
        xra     a
        sta     _fr_fy

fr_pair_loop:
        ; cur: упаковать 2 распакованных пикселя (_fire_buf) в тетрады
        lhld    _fr_cur_ptr
        mov     a,m              ; A = cur_hi (чётный пиксель)
        rlc
        rlc
        rlc
        rlc                      ; A = cur_hi << 4
        inx     h
        ora     m                ; A = (cur_hi<<4) | cur_lo  (cur_lo 0..15)
        sta     _fr_cur
        mov     b,a              ; B = cur (упакованный)
        inx     h
        shld    _fr_cur_ptr      ; cur_ptr += 2
        lhld    _fr_prev_ptr     ; HL = prev_ptr (упакованная тень)
        mov     a,m              ; A = prev
        ; diff = cur ^ prev; если 0 → cur == prev, блок не менялся, пропускаем
        xra     b                ; A = prev ^ cur = diff
        jz      fr_pair_skip     ; HL ещё = prev_ptr → докрутим prev в skip

        sta     _fr_diff
        ; тень = cur (упакованный) и prev_ptr++ — HL валиден, advance в прологе
        lda     _fr_cur
        mov     m,a
        inx     h
        shld    _fr_prev_ptr

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
        mvi     a,0E0h          ; адрес блока = (база+col)<<8 | fylo
        add     d
        mov     h,a
        mov     l,e
        mov     a,b             ; A = byte_val (B держит byte_val)
        mov     m,a             ; [block+0]
        inx     h
        mov     m,a             ; [block+1]
        inx     h
        mov     m,a             ; [block+2]
        inx     h
        mov     m,a             ; [block+3]

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
        mvi     a,0C0h
        add     d
        mov     h,a
        mov     l,e
        mov     a,b
        mov     m,a
        inx     h
        mov     m,a
        inx     h
        mov     m,a
        inx     h
        mov     m,a

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
        mvi     a,0A0h
        add     d
        mov     h,a
        mov     l,e
        mov     a,b
        mov     m,a
        inx     h
        mov     m,a
        inx     h
        mov     m,a
        inx     h
        mov     m,a

        ; ---- плоскость 3: маска 88h, база 8000 ----
fr3_build:
        lda     _fr_diff
        ani     88h
        jz      fr_pair_count
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
        mvi     a,80h
        add     d
        mov     h,a
        mov     l,e
        mov     a,b
        mov     m,a
        inx     h
        mov     m,a
        inx     h
        mov     m,a
        inx     h
        mov     m,a

fr_pair_count:
        inr     d               ; col++ (адрес следующего байта = +256 → мл. байт не тронут)
        mov     a,d
        cpi     ROWB            ; 32 байта строки обработаны?
        jnz     fr_pair_loop

        ; конец строки: col = 0, fylo += 4, fy++
        mvi     d,0
        mov     a,e
        adi     4
        mov     e,a
        lda     _fr_fy
        inr     a
        sta     _fr_fy
        cpi     FIRE_H
        jnz     fr_pair_loop

        pop     hl
        pop     de
        pop     bc
        ret

; сюда прыгает «cur == prev» (diff == 0): cur уже увеличен в прологе, HL всё ещё
; = prev_ptr — докручиваем prev и уходим на общий счётчик/адрес.
fr_pair_skip:
        inx     h
        shld    _fr_prev_ptr     ; prev_ptr++
        jmp     fr_pair_count
