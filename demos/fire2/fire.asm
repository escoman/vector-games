SECTION code_clib
PUBLIC _rnd_init
PUBLIC _get_fire_buf
PUBLIC _put_fire_buf
PUBLIC _fire_generate
PUBLIC _fire_render

FIRE_W EQU 64
FIRE_H EQU 64

SECTION bss_clib
_rnd_table: defs 256
_rnd_mod3: defs 256
_rnd_idx: defb 0
_rnd_seed: defw 0
_rnd_ptr: defw 0
_rnd_tmp: defb 0
_rnd_tmp2: defb 0
_fire_buf: defs 2048
_fg_power: defb 0
_fg_x: defb 0
_fg_y: defb 0
_fg_above: defb 0
_fg_decay: defb 0
_fg_srcx: defb 0
_fg_value: defb 0
_fg_above_ptr: defw 0
_fg_dest_ptr: defw 0
_fr_fy: defb 0
_fr_fx: defb 0
_fr_byte: defb 0
_fr_val: defb 0

SECTION code_clib

; ================================================================
; void rnd_init(void)
; seed=0x1234; do { seed=seed*251+73; table[i]=seed>>8; } while(++i);
; Also builds table[i] % 3, and initializes a 16-bit random pointer.
; 8080-only; __z88dk_callee.
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
        ; 251*x = 256*x - 5*x (mod 65536).
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
        sta     _rnd_tmp

        ; rnd_table[i] = high byte
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

        ; Build fixed table: rnd_mod3[v] = v % 3 for v=0..255.
        lxi     h,_rnd_mod3
        mvi     c,0
        mvi     b,0
ri_mod_table_loop:
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
        jnz     ri_mod_table_loop
        xra     a
        sta     _rnd_idx
        lxi     h,_rnd_table
        shld    _rnd_ptr
        pop     hl
        pop     de
        pop     bc
        ret

; ================================================================
; Internal rnd_next(), returns A and advances/wraps pointer.
; Clobbers HL and flags only.
; ================================================================
_fg_rnd_next:
        lhld    _rnd_ptr
        mov     a,m
        sta     _rnd_tmp
        inx     h
        lxi     d,_rnd_table+256
        mov     a,h
        cmp     d
        jnz     fg_rnd_store
        mov     a,l
        cmp     e
        jnz     fg_rnd_store
        lxi     h,_rnd_table
fg_rnd_store:
        shld    _rnd_ptr
        lda     _rnd_idx
        inr     a
        sta     _rnd_idx
        lda     _rnd_tmp
        ret

; ================================================================
; unsigned char get_fire_buf(unsigned char x, unsigned char y)
; __z88dk_callee: y at SP+2, x at SP+4.
; ================================================================
_get_fire_buf:
        push    bc
        lxi     h,6
        dad     sp
        mov     a,m
        mov     c,a             ; x
        lxi     h,4
        dad     sp
        mov     a,m
        mov     l,a
        mvi     h,0             ; y
        dad     h
        dad     h
        dad     h
        dad     h
        dad     h                 ; y*32
        mov     a,c
        ora     a
        rar                       ; x>>1
        mov     e,a
        mvi     d,0
        dad     d
        lxi     d,_fire_buf
        dad     d
        mov     a,m
        mov     b,a
        mov     a,c
        ani     1
        jnz     gfb_odd
        mov     a,b
        rrc
        rrc
        rrc
        rrc
        ani     15
        jmp     gfb_ret
 gfb_odd:
        mov     a,b
        ani     15
 gfb_ret:
        mov     l,a
        mvi     h,0
        pop     bc
        pop     de              ; return address
        inx     sp
        inx     sp
        inx     sp
        inx     sp              ; consume y,x
        push    de
        ret

; ================================================================
; void put_fire_buf(unsigned char x, unsigned char y, unsigned char value)
; __z88dk_callee: value at SP+2, y at SP+4, x at SP+6.
; ================================================================
_put_fire_buf:
        push    bc
        lxi     h,4
        dad     sp
        mov     a,m
        ani     15
        mov     b,a             ; value
        lxi     h,8
        dad     sp
        mov     a,m
        mov     c,a             ; x
        lxi     h,6
        dad     sp
        mov     a,m
        mov     l,a
        mvi     h,0
        dad     h
        dad     h
        dad     h
        dad     h
        dad     h               ; y*32
        mov     a,c
        ora     a
        rar
        mov     e,a
        mvi     d,0
        dad     d
        lxi     d,_fire_buf
        dad     d
        mov     a,c
        ani     1
        jnz     pfb_odd
        mov     a,b
        rlc
        rlc
        rlc
        rlc
        mov     c,a
        mov     a,m
        ani     15
        ora     c
        mov     m,a
        jmp     pfb_ret
pfb_odd:
        mov     a,m
        ani     240
        mov     c,a
        mov     a,b
        ora     c
        mov     m,a
pfb_ret:
        pop     bc
        pop     de
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp              ; consume value,y,x
        push    de
        ret

; ================================================================
; void fire_generate(unsigned char power)
; Exact C algorithm from main.c.old, but with packed-buffer access inlined.
; ================================================================
_fire_generate:
        push    bc
        lxi     h,4
        dad     sp
        mov     a,m
        sta     _fg_power

        ; ---- source row y=0 ----
        lxi     h,_fire_buf
        shld    _fg_dest_ptr
        mvi     b,0
fg_seed_loop:
        ; rnd_next()
        call    _fg_rnd_next
        sta     _fg_value
        lda     _fg_power
        mov     c,a
        lda     _fg_value
        cmp     c
        jc      fg_seed_hot
        ; second rnd_next() > 128 ?
        call    _fg_rnd_next
        cpi     129
        jc      fg_seed_keep
        ; current value, then current > 2 ? current-2 : 0
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
        ; advance packed destination after odd x
        mov     a,b
        ani     1
        jz      fg_seed_no_ptr_inc
        lhld    _fg_dest_ptr
        inx     h
        shld    _fg_dest_ptr
fg_seed_no_ptr_inc:
        inr     b
        mov     a,b
        cpi     64
        jnz     fg_seed_loop

        ; ---- rows y=1..63 ----
        lxi     h,_fire_buf
        shld    _fg_above_ptr
        lxi     h,_fire_buf+32
        shld    _fg_dest_ptr
        mvi     b,1
        mov     a,b
        sta     _fg_y
fg_y_loop:
        mvi     c,0
        mov     a,c
        sta     _fg_x
fg_x_loop:
        ; random shift: rnd_table[rnd_idx] % 3
        call    _fg_rnd_next
        mov     e,a
        mvi     d,0
        lxi     h,_rnd_mod3
        dad     d
        mov     a,m
        ; 0 => -1, 1 => 0, 2 => +1
        cpi     0
        jnz     fg_shift_not_minus
        ; C expression converts -1 to unsigned char 63, then adds to x.
        lda     _fg_x
        adi     63
        jmp     fg_shift_store
fg_shift_not_minus:
        cpi     1
        jnz     fg_shift_plus
        lda     _fg_x
        jmp     fg_shift_store
fg_shift_plus:
        lda     _fg_x
        inr     a
fg_shift_store:
        sta     _fg_srcx

        ; read above[srcx]
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
        jnz     fg_above_odd
        mov     a,d
        rrc
        rrc
        rrc
        rrc
        ani     15
        jmp     fg_above_done
fg_above_odd:
        mov     a,d
        ani     15
fg_above_done:
        sta     _fg_above

        ; decay = rnd_next() & 1
        call    _fg_rnd_next
        ani     1
        sta     _fg_decay
        ; if (y < 32 && rnd_next() > 178) decay++
        lda     _fg_y
        cpi     32
        jnc     fg_no_extra
        call    _fg_rnd_next
        cpi     179
        jc      fg_no_extra
        lda     _fg_decay
        inr     a
        sta     _fg_decay
fg_no_extra:
        ; if (above > decay) result = above-decay, else 0
        lda     _fg_above
        mov     c,a
        lda     _fg_decay
        mov     e,a
        mov     a,c
        cmp     e
        jnc     fg_above_ge_decay
        xra     a
        sta     _fg_value
        jmp     fg_result_store
fg_above_ge_decay:
        mov     a,c
        cmp     e
        jz      fg_result_zero
        sub     e
        sta     _fg_value
        jmp     fg_result_store
fg_result_zero:
        xra     a
        sta     _fg_value
fg_result_store:
        lhld    _fg_dest_ptr
        lda     _fg_x
        ani     1
        jnz     fg_store_odd
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
        jmp     fg_store_advance
fg_store_odd:
        mov     a,m
        ani     240
        mov     c,a
        lda     _fg_value
        ora     c
        mov     m,a
fg_store_advance:
        ; destination byte pointer advances after odd x
        lda     _fg_x
        ani     1
        jz      fg_no_dest_inc
        inx     h
fg_no_dest_inc:
        shld    _fg_dest_ptr
        lda     _fg_x
        inr     a
        sta     _fg_x
        cpi     64
        jnz     fg_x_loop
        ; next row
        lhld    _fg_dest_ptr
        ; After x=63 the pointer is at the NEXT row.  Source for the
        ; following iteration is the row just completed, i.e. -32 bytes.
        lxi     d,0xFFE0
        dad     d
        shld    _fg_above_ptr
        lxi     d,32
        dad     d
        shld    _fg_dest_ptr
        lda     _fg_y
        inr     a
        sta     _fg_y
        cpi     64
        jnz     fg_y_loop
        pop     bc
        pop     de
        inx     sp
        inx     sp              ; consume power
        push    de
        ret

; ================================================================
; void fire_render(void)
; Exact C mapping. Processes one packed buffer byte (two pixels) at a time.
; ================================================================
_fire_render:
        push    bc
        ; fy=0; fx=0
        xra     a
        sta     _fr_fy
        sta     _fr_fx
fr_y_loop:
        lda     _fr_fx
        cpi     64
        jnc     fr_next_y
        ; value = fire_buf[fy*32 + fx/2]
        lda     _fr_fy
        mov     l,a
        mvi     h,0
        dad     h
        dad     h
        dad     h
        dad     h
        dad     h
        mov     e,a             ; dummy; recompute byte offset below
        lda     _fr_fx
        ora     a
        rar
        mov     e,a
        mvi     d,0
        dad     d
        lxi     d,_fire_buf
        dad     d
        mov     a,m
        ora     a
        jz      fr_pair_next
        sta     _fr_val

        ; p=0..3. Build plane byte and write four rows.
        mvi     c,0
fr_p_loop:
        ; high nibble bit p -> F0
        lda     _fr_val
        ; mask = 0x10 << p, built in A via p loop using table-like shift
        lxi     h,0x0010
        mov     e,c
        mvi     d,0
fr_hi_shift:
        mov     a,e
        ora     a
        jz      fr_hi_mask_ready
        dad     h
        dcr     e
        jmp     fr_hi_shift
fr_hi_mask_ready:
        lda     _fr_val
        ana     l
        jz      fr_hi_zero
        mvi     a,240
        sta     _fr_byte
        jmp     fr_low_test
fr_hi_zero:
        xra     a
        sta     _fr_byte
fr_low_test:
        ; low mask = 1 << p
        lxi     h,1
        mov     e,c
        mvi     d,0
fr_lo_shift:
        mov     a,e
        ora     a
        jz      fr_lo_mask_ready
        dad     h
        dcr     e
        jmp     fr_lo_shift
fr_lo_mask_ready:
        lda     _fr_val
        ana     l
        jz      fr_byte_ready
        lda     _fr_byte
        ori     15
        sta     _fr_byte
fr_byte_ready:
        lda     _fr_byte
        ora     a
        jz      fr_p_next
        ; offset = (fx/2)*256 + fy*4
        lda     _fr_fx
        ora     a
        rar
        mov     h,a
        mvi     l,0
        lda     _fr_fy
        mov     e,a
        mvi     d,0
        mov     a,e
        add     a
        mov     e,a
        mov     a,d
        adc     a
        mov     d,a
        mov     a,e
        add     e
        mov     e,a
        mov     a,d
        adc     d
        mov     d,a
        mov     a,e
        add     l
        mov     l,a
        mov     a,d
        adc     h
        mov     h,a
        ; choose plane base by p
        mov     a,c
        cpi     0
        jnz     fr_base_p1
        lxi     d,0xE000
        jmp     fr_have_base
fr_base_p1:
        cpi     1
        jnz     fr_base_p2
        lxi     d,0xC000
        jmp     fr_have_base
fr_base_p2:
        cpi     2
        jnz     fr_base_p3
        lxi     d,0xA000
        jmp     fr_have_base
fr_base_p3:
        lxi     d,0x8000
fr_have_base:
        dad     d
        lda     _fr_byte
        mov     d,a
        mov     m,a
        inx     h
        mov     m,a
        inx     h
        mov     m,a
        inx     h
        mov     m,a
fr_p_next:
        inr     c
        mov     a,c
        cpi     4
        jnz     fr_p_loop
fr_pair_next:
        lda     _fr_fx
        adi     2
        sta     _fr_fx
        jmp     fr_y_loop
fr_next_y:
        xra     a
        sta     _fr_fx
        lda     _fr_fy
        inr     a
        sta     _fr_fy
        cpi     64
        jnz     fr_y_loop
        pop     bc
        ret
