; fire.asm -- optimized Intel 8080 implementation of fire_frame()
; Target: Vector-06C / KR580VM80A / Intel 8080
; Calling convention: __z88dk_callee (sccz80)
;
; Parameters:
;   plane_base, decay, base_ht, height
; Entry stack:
;   SP+0 return address
;   SP+2 height
;   SP+4 base_ht
;   SP+6 decay
;   SP+8 plane_base
;
; The inner loop keeps:
;   HL = source row address, H = column address, L = row offset
;   DE = random-table pointer (only E changes; wraps at 256)
;   B  = column counter
; Horizontal neighbours are obtained by H-1 / H+1, avoiding address rebuilds.

        SECTION code_user
        PUBLIC _fire_frame_asm
        EXTERN _rnd_table
        EXTERN _rnd_idx

_fire_frame_asm:
        pop     h
        shld    _ff_ret
        pop     b
        mov     a,c
        sta     _ff_height
        pop     b
        mov     a,c
        sta     _ff_base
        pop     b
        mov     a,c
        sta     _ff_decay
        pop     h
        shld    _ff_plane

        ; top = base + height - 1, 8-bit wrap
        lda     _ff_base
        mov     c,a
        lda     _ff_height
        add     c
        dcr     a
        sta     _ff_top

        ; ------------------------------------------------------------
        ; Seed row: 32 random bytes.
        ; HL = plane + base
        ; DE = _rnd_table + rnd_idx
        ; ------------------------------------------------------------
        lhld    _ff_plane
        lda     _ff_base
        add     l
        mov     l,a
        jnc     seed_dest_nc
        inr     h
seed_dest_nc:
        xchg                        ; DE = destination, HL = temporary
        lxi     h,_rnd_table
        lda     _rnd_idx
        mov     c,a
        cma
        inr     a
        sta     _ff_rleft             ; 0 means 256 bytes remaining
        mov     a,c
        mvi     b,0
        dad     b
        xchg                        ; HL = destination, DE = random
        mvi     b,32

seed_loop:
        xchg                        ; HL=random, DE=destination
        mov     a,m
        xchg                        ; HL=destination, DE=random
        mov     m,a
        inr     h                   ; next column = +256
        inr     e                   ; next random byte (16-bit pointer)
        jnz     seed_ptr_nc
        inr     d
seed_ptr_nc:
        lda     _ff_rleft
        dcr     a
        sta     _ff_rleft
        jnz     seed_rnd_no_wrap
        lxi     d,_rnd_table         ; completed 256-byte circular table
seed_rnd_no_wrap:
        dcr     b
        jnz     seed_loop

        ; rnd_idx += 32
        lda     _rnd_idx
        adi     32
        sta     _rnd_idx

        ; ------------------------------------------------------------
        ; Rows base+1 .. top.
        ; HL = source row, DE = random pointer.
        ; ------------------------------------------------------------
        lda     _ff_base
        inr     a
        sta     _ff_ofs

row_loop:
        lda     _ff_ofs
        mov     b,a
        lda     _ff_top
        cmp     b
        jc      done

        ; HL = plane + (ofs-1), column 0
        lhld    _ff_plane
        lda     _ff_ofs
        dcr     a
        add     l
        mov     l,a
        jnc     row_addr_nc
        inr     h
row_addr_nc:
        mvi     b,0

col_loop:
        ; center
        mov     a,m
        sta     _ff_center

        ; left = center << 1
        add     a
        sta     _ff_left

        ; if col != 0, OR previous column bit 7 -> bit 0
        mov     a,b
        ora     a
        jz      no_left
        dcr     h
        mov     a,m
        inr     h
        ani     128
        jz      left_zero
        mvi     a,1
left_zero:
        mov     c,a
        lda     _ff_left
        ora     c
        sta     _ff_left
no_left:

        ; right = center >> 1 (force CY=0 before RAR)
        lda     _ff_center
        ora     a
        rar
        sta     _ff_right

        ; if col != 31, OR next column bit 0 -> bit 7
        mov     a,b
        cpi     31
        jz      no_right
        inr     h
        mov     a,m
        dcr     h
        ani     1
        jz      right_zero
        mvi     a,128
        jmp     right_merge
right_zero:
        xra     a
right_merge:
        mov     c,a
        lda     _ff_right
        ora     c
        sta     _ff_right
no_right:

        ; majority = (L&C) | (L&R) | (C&R)
        lda     _ff_left
        mov     c,a
        lda     _ff_center
        ana     c
        sta     _ff_m1

        lda     _ff_left
        mov     c,a
        lda     _ff_right
        ana     c
        sta     _ff_m2

        lda     _ff_center
        mov     c,a
        lda     _ff_right
        ana     c
        mov     c,a
        lda     _ff_m1
        ora     c
        mov     c,a
        lda     _ff_m2
        ora     c
        sta     _ff_avg

        ; decay: avg &= ~(~decay & rnd)
        xchg                        ; HL=random, DE=source row
        mov     a,m
        mov     c,a                  ; preserve random byte
        inr     l                   ; next random byte (16-bit pointer)
        jnz     rnd_ptr_nc
        inr     h
rnd_ptr_nc:
        lda     _ff_rleft
        dcr     a
        sta     _ff_rleft
        jnz     rnd_inc_nc
        lxi     h,_rnd_table         ; completed 256-byte circular table
rnd_inc_nc:
        xchg                        ; HL=source row, DE=random

        lda     _ff_decay
        cma
        ana     c
        cma
        mov     c,a
        lda     _ff_avg
        ana     c
        sta     _ff_avg

        ; store at current row (source row + 1).
        ; INR does not affect CY, so use Z to detect FF->00.
        inr     l
        jnz     store_no_wrap
        inr     h
store_wrapped:
        lda     _ff_avg
        mov     m,a
        dcr     h                   ; return to source page
        mvi     l,0ffh              ; source row was FF
        inr     h                   ; next column
        jmp     store_next_col
store_no_wrap:
        lda     _ff_avg
        mov     m,a
        dcr     l                   ; back to source row
        inr     h                   ; next column
store_next_col:
        inr     b
        mov     a,b
        cpi     32
        jnz     col_loop

        ; 32 random bytes were consumed by the row, then skip 7.
        ; Rebuild the random pointer from the new modulo-256 rnd_idx.
        ; This also handles a non-page-aligned _rnd_table correctly.
        lda     _rnd_idx
        adi     39
        sta     _rnd_idx
        cma
        inr     a
        sta     _ff_rleft             ; remaining bytes to table wrap
        lda     _rnd_idx
        mov     c,a
        mvi     b,0
        lxi     h,_rnd_table
        dad     b
        xchg                        ; DE = _rnd_table + rnd_idx

        lda     _ff_ofs
        inr     a
        sta     _ff_ofs
        jmp     row_loop

done:
        lhld    _ff_ret
        pchl

        SECTION data_user
_ff_ret:    defw 0
_ff_plane:  defw 0
_ff_decay:  defb 0
_ff_base:   defb 0
_ff_height: defb 0
_ff_top:    defb 0
_ff_ofs:    defb 0
_ff_center: defb 0
_ff_left:   defb 0
_ff_right:  defb 0
_ff_avg:    defb 0
_ff_m1:     defb 0
_ff_m2:     defb 0
_ff_rleft:  defb 0
