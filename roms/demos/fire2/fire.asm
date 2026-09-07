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
_fr_saved_sp: defw 0
_fr_fire_ptr: defw 0
_fr_addr: defw 0
_fr_pair: defb 0

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
; ================================================================
; void fire_render(void)
; Optimized 8080 renderer.
; Uses PUSH BC twice to write four identical bytes at once.
; Interrupts are disabled while SP is redirected into VRAM.
; ================================================================
_fire_render:
        di

        ; Save caller SP before using SP as a temporary VRAM pointer.
        lxi     h,0
        dad     sp
        shld    _fr_saved_sp
        push    bc
        push    de
        push    hl

        xra     a
        sta     _fr_fy
        sta     _fr_addr
        mvi     a,4
        sta     _fr_addr
        xra     a
        sta     _fr_addr+1
        lxi     h,_fire_buf
        shld    _fr_fire_ptr

fr_y_loop:
        mvi     a,32
        sta     _fr_pair
fr_pair_loop:
        lhld    _fr_fire_ptr
        mov     a,m
        ora     a
        jz      fr_pair_next
        sta     _fr_val

        ; ============================================================
        ; Plane 0: masks 10h / 01h, base E000.
        ; ============================================================
        lda     _fr_val
        ani     10h
        jz      fr0_nohi
        mvi     a,0F0h
        jmp     fr0_hi_done
fr0_nohi:
        xra     a
fr0_hi_done:
        mov     b,a
        lda     _fr_val
        ani     01h
        jz      fr0_ready
        mov     a,b
        ori     0Fh
        mov     b,a
fr0_ready:
        mov     a,b
        ora     a
        jz      fr1_build
        mov     c,a
        lhld    _fr_addr
        mvi     a,0E0h
        add     h
        mov     h,a
        sphl
        push    bc
        push    bc

        ; ============================================================
        ; Plane 1: masks 20h / 02h, base C000.
        ; ============================================================
fr1_build:
        lda     _fr_val
        ani     20h
        jz      fr1_nohi
        mvi     a,0F0h
        jmp     fr1_hi_done
fr1_nohi:
        xra     a
fr1_hi_done:
        mov     b,a
        lda     _fr_val
        ani     02h
        jz      fr1_ready
        mov     a,b
        ori     0Fh
        mov     b,a
fr1_ready:
        mov     a,b
        ora     a
        jz      fr2_build
        mov     c,a
        lhld    _fr_addr
        mvi     a,0C0h
        add     h
        mov     h,a
        sphl
        push    bc
        push    bc

        ; ============================================================
        ; Plane 2: masks 40h / 04h, base A000.
        ; ============================================================
fr2_build:
        lda     _fr_val
        ani     40h
        jz      fr2_nohi
        mvi     a,0F0h
        jmp     fr2_hi_done
fr2_nohi:
        xra     a
fr2_hi_done:
        mov     b,a
        lda     _fr_val
        ani     04h
        jz      fr2_ready
        mov     a,b
        ori     0Fh
        mov     b,a
fr2_ready:
        mov     a,b
        ora     a
        jz      fr3_build
        mov     c,a
        lhld    _fr_addr
        mvi     a,0A0h
        add     h
        mov     h,a
        sphl
        push    bc
        push    bc

        ; ============================================================
        ; Plane 3: masks 80h / 08h, base 8000.
        ; ============================================================
fr3_build:
        lda     _fr_val
        ani     80h
        jz      fr3_nohi
        mvi     a,0F0h
        jmp     fr3_hi_done
fr3_nohi:
        xra     a
fr3_hi_done:
        mov     b,a
        lda     _fr_val
        ani     08h
        jz      fr3_ready
        mov     a,b
        ori     0Fh
        mov     b,a
fr3_ready:
        mov     a,b
        ora     a
        jz      fr_pair_next
        mov     c,a
        lhld    _fr_addr
        mvi     a,080h
        add     h
        mov     h,a
        sphl
        push    bc
        push    bc

fr_pair_next:
        lhld    _fr_fire_ptr
        inx     h
        shld    _fr_fire_ptr
        lhld    _fr_addr
        inr     h
        shld    _fr_addr
        lda     _fr_pair
        dcr     a
        sta     _fr_pair
        jnz     fr_pair_loop

        lhld    _fr_addr
        mov     a,l
        adi     4
        mov     l,a
        mvi     h,0
        jnc     fr_row_no_carry
        inr     h
fr_row_no_carry:
        shld    _fr_addr
        lda     _fr_fy
        inr     a
        sta     _fr_fy
        cpi     64
        jnz     fr_y_loop

fr_restore:
        ; Restore the register-save frame.  Three registers were pushed
        ; at entry, so start six bytes below the original SP.
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
        ; RET consumes the original return address: final SP = entry SP+2.
        ei
        ret

