; graphlz.asm
; LZ tile unpacker for the classic Vector-06C (KR580VM80A / Intel 8080).
;
; z88dk / z80asm source. Assemble with:
;     z88dk-z80asm -m8080 graphlz.asm
;
; C interface (standard linkage):
;     void graph_lz_expand(const unsigned char *src);
;
; The routine is a direct assembly implementation of graphlz.c:
;   - header: tpp(16), ntiles(16), h_div8(8)
;   - dictionary: ntiles * 8 bytes
;   - four LZ streams
;   - literal token: 9-bit dictionary index in two bytes
;   - reference token: 12-bit offset + 4-bit length
;
; VRAM:
;   plane 0 = 8000h
;   plane 1 = A000h
;   plane 2 = C000h
;   plane 3 = E000h
;
; A tile occupies eight bytes at descending addresses.
; Tile #0 starts at xxxx:00FF, tile #1 at xxxx:00F7, etc.
;
; This source uses only the Intel 8080 instruction set. No Z80-only
; instructions or registers are used.

SECTION code_user

PUBLIC _graph_lz_expand

; ---------------------------------------------------------------------------
; void graph_lz_expand(const unsigned char *src)
;
; Standard z88dk linkage:
;   stack -> return address, src
; The stack is restored unchanged before returning.
; ---------------------------------------------------------------------------
_graph_lz_expand:
        POP     B               ; BC = return address
        POP     H               ; HL = src
        PUSH    H
        PUSH    B
        SHLD    glz_src

        ; tpp = src[0] | (src[1] << 8)
        MOV     A,M
        STA     glz_tpp
        INX     H
        MOV     A,M
        STA     glz_tpp+1
        INX     H

        ; ntiles = src[2] | (src[3] << 8)
        MOV     A,M
        STA     glz_ntiles
        INX     H
        MOV     A,M
        STA     glz_ntiles+1
        INX     H

        ; h_div8 = src[4]
        MOV     A,M
        STA     glz_hdiv
        INX     H

        ; dict = src + 5
        SHLD    glz_dict

        ; p = dict + ntiles * 8
        LHLD    glz_ntiles
        DAD     H
        DAD     H
        DAD     H
        XCHG
        LHLD    glz_dict
        DAD     D
        SHLD    glz_p

        XRA     A
        STA     glz_plane

; ---------------------------------------------------------------------------
; Start a plane.
; ---------------------------------------------------------------------------
glz_plane_start:
        XRA     A
        STA     glz_cur
        STA     glz_cur+1
        STA     glz_flag
        STA     glz_nbits
        STA     glz_row

        ; dst = address of tile 0 on this plane.
        CALL    glz_set_plane_base
        SHLD    glz_dst

; ---------------------------------------------------------------------------
; Read one LZ token.
; ---------------------------------------------------------------------------
glz_token:
        LDA     glz_nbits
        ORA     A
        JNZ     glz_token_have_flag

        ; If cur >= tpp, this plane is finished.
        CALL    glz_cur_ge_tpp
        JNC     glz_plane_done

        ; flag = *p++
        LHLD    glz_p
        MOV     A,M
        INX     H
        SHLD    glz_p
        STA     glz_flag
        MVI     A,8
        STA     glz_nbits

glz_token_have_flag:
        LDA     glz_flag
        ANI     1
        JZ      glz_reference

; ---------------------------------------------------------------------------
; Literal token.
; idx = ((p[0] & 1) << 8) | p[1]
; ---------------------------------------------------------------------------
glz_literal:
        LHLD    glz_p
        MOV     A,M
        ANI     1
        MOV     B,A
        INX     H
        MOV     A,M
        MOV     C,A
        INX     H
        SHLD    glz_p

        ; C version suppresses the write if a token starts past tpp.
        CALL    glz_cur_ge_tpp
        JNC     glz_literal_no_write

        ; HL = idx
        MOV     H,B
        MOV     L,C

        ; HL = idx * 8
        DAD     H
        DAD     H
        DAD     H

        ; HL = dict + idx*8
        XCHG
        LHLD    glz_dict
        DAD     D               ; HL = dictionary source
        XCHG                    ; DE = dictionary source

        LHLD    glz_dst
        XCHG                    ; HL = source, DE = VRAM destination
        CALL    glz_copy8

        CALL    glz_advance_dst
        CALL    glz_inc_cur
        CALL    glz_consume_flag
        JMP     glz_token

glz_literal_no_write:
        CALL    glz_inc_cur
        CALL    glz_consume_flag
        JMP     glz_token

; ---------------------------------------------------------------------------
; Reference token.
;
; offset = ((p[0] & 0x0f) << 8) | p[1]
; length = (p[0] >> 4) + 3
; ---------------------------------------------------------------------------
glz_reference:
        LHLD    glz_p
        MOV     A,M
        MOV     B,A
        INX     H
        MOV     A,M
        MOV     C,A
        INX     H
        SHLD    glz_p

        ; offset = ((p[0] & 0x0f) << 8) | p[1]
        MOV     A,B
        ANI     0FH
        MOV     H,A
        MOV     L,C
        SHLD    glz_offset

        MOV     A,B
        ANI     0F0H
        RRC
        RRC
        RRC
        RRC
        ADI     3
        STA     glz_len

        ; src_tile = cur - offset
        LHLD    glz_cur
        XCHG
        LHLD    glz_offset
        MOV     A,E
        SUB     L
        MOV     E,A
        MOV     A,D
        SBB     H
        MOV     D,A

        LDA     glz_plane
        CALL    glz_tile_addr
        SHLD    glz_src_tile

; ---------------------------------------------------------------------------
; Copy one referenced tile, then continue with the next tile in the
; reference run. The source address is recalculated from cur-offset after
; every copied tile. This exactly matches the C implementation and handles
; column wrapping correctly.
; ---------------------------------------------------------------------------
glz_reference_loop:
        LDA     glz_len
        ORA     A
        JZ      glz_reference_done

        ; C version does not write tiles beyond tpp, but still advances cur.
        CALL    glz_cur_ge_tpp
        JNC     glz_reference_skip_copy

        LHLD    glz_src_tile
        XCHG                    ; DE = source
        LHLD    glz_dst
        XCHG                    ; HL = source, DE = destination
        CALL    glz_copy8_vram

        CALL    glz_advance_dst

glz_reference_skip_copy:
        CALL    glz_inc_cur

        ; Recalculate src_tile = cur - offset.
        LHLD    glz_cur
        XCHG
        LHLD    glz_offset
        MOV     A,E
        SUB     L
        MOV     E,A
        MOV     A,D
        SBB     H
        MOV     D,A

        LDA     glz_plane
        CALL    glz_tile_addr
        SHLD    glz_src_tile

        LDA     glz_len
        DCR     A
        STA     glz_len
        JMP     glz_reference_loop

glz_reference_done:
        CALL    glz_consume_flag
        JMP     glz_token

; ---------------------------------------------------------------------------
; Consume one flag bit.
; ---------------------------------------------------------------------------
glz_consume_flag:
        LDA     glz_flag
        RRC
        STA     glz_flag

        LDA     glz_nbits
        DCR     A
        STA     glz_nbits
        RET

; ---------------------------------------------------------------------------
; cur++
; ---------------------------------------------------------------------------
glz_inc_cur:
        LHLD    glz_cur
        INX     H
        SHLD    glz_cur
        RET

; ---------------------------------------------------------------------------
; Carry set if cur < tpp, carry clear if cur >= tpp.
; ---------------------------------------------------------------------------
glz_cur_ge_tpp:
        LHLD    glz_cur
        XCHG
        LHLD    glz_tpp

        ; Compute cur - tpp. Carry is set when cur < tpp.
        MOV     A,E
        SUB     L
        MOV     A,D
        SBB     H
        RET

; ---------------------------------------------------------------------------
; Finish a plane and move to the next one.
; ---------------------------------------------------------------------------
glz_plane_done:
        LDA     glz_plane
        INR     A
        STA     glz_plane
        CPI     4
        JZ      glz_return
        JMP     glz_plane_start

glz_return:
        RET

; ---------------------------------------------------------------------------
; Advance current destination tile.
;
; row 0..h_div8-1:
;   next row: dst -= 8
; after the last row:
;   next column: dst += 256 + 8*(h_div8-1)
; ---------------------------------------------------------------------------
glz_advance_dst:
        ; Move from current tile to the next tile in post-column order.
        ;
        ; row = 0 .. h_div8-1
        ; next row:    dst -= 8
        ; new column: dst += 256 + 8*(h_div8-1)

        LDA     glz_row
        INR     A
        MOV     B,A

        LDA     glz_hdiv
        CMP     B
        JZ      glz_new_column

        ; row++
        MOV     A,B
        STA     glz_row

        ; dst -= 8
        LHLD    glz_dst
        LXI     D,8
        MOV     A,L
        SUB     E
        MOV     L,A
        MOV     A,H
        SBB     D
        MOV     H,A
        SHLD    glz_dst
        RET

glz_new_column:
        XRA     A
        STA     glz_row

        ; delta = 256 + 8*(h_div8-1)
        LDA     glz_hdiv
        DCR     A
        MOV     L,A
        MVI     H,0
        DAD     H
        DAD     H
        DAD     H               ; HL = 8*(h_div8-1)

        ; delta = HL + 256
        MOV     A,H
        INR     A
        MOV     H,A

        XCHG                    ; DE = delta
        LHLD    glz_dst
        DAD     D
        SHLD    glz_dst
        RET

; ---------------------------------------------------------------------------
; Set base address for current plane.
; Returns HL = 8000h + plane*2000h + 00ffh.
; ---------------------------------------------------------------------------
glz_set_plane_base:
        LDA     glz_plane
        MOV     L,A
        MVI     H,0

        ; HL = plane * 8192
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H

        LXI     D,8000H
        DAD     D
        LXI     D,255
        DAD     D
        RET

; ---------------------------------------------------------------------------
; glz_tile_addr
;
; Input:
;   A  = plane
;   DE = tile index
;
; Output:
;   HL = first (highest-address) byte of the tile
;
; Address:
;   base + (tile / h_div8) * 256
;        + 255 - (tile % h_div8) * 8
;
; The division is a general 16/8-bit division by repeated subtraction.
; ---------------------------------------------------------------------------
glz_tile_addr:
        ; A  = plane
        ; DE = tile index
        ;
        ; Return:
        ;   HL = 8000h + plane*2000h
        ;        + (tile/h_div8)*256
        ;        + 255 - (tile%h_div8)*8

        STA     glz_tmp_plane

        ; Divide tile index by h_div8.
        ; Keep quotient in glz_quot and remainder in glz_rem.
        LDA     glz_hdiv
        MOV     C,A
        MVI     B,0

        LXI     H,0               ; quotient

glz_div_loop:
        ; Test DE >= BC without destroying DE.
        MOV     A,D
        CMP     B
        JC      glz_div_done
        JNZ     glz_div_sub
        MOV     A,E
        CMP     C
        JC      glz_div_done

glz_div_sub:
        MOV     A,E
        SUB     C
        MOV     E,A
        MOV     A,D
        SBB     B
        MOV     D,A
        INX     H
        JMP     glz_div_loop

glz_div_done:
        SHLD    glz_quot
        XCHG
        SHLD    glz_rem

        ; DE = quotient * 256.
        LHLD    glz_quot
        MOV     D,L
        MVI     E,0

        ; HL = plane * 2000h.
        LDA     glz_tmp_plane
        MOV     L,A
        MVI     H,0

        ; *8192
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        DAD     H

        ; +8000h
        LXI     B,8000H
        DAD     B

        ; + quotient * 256
        DAD     D

        ; +255
        LXI     D,255
        DAD     D
        SHLD    glz_tmp_addr

        ; - remainder * 8
        LHLD    glz_rem
        DAD     H
        DAD     H
        DAD     H
        XCHG                    ; DE = remainder*8
        LHLD    glz_tmp_addr

        MOV     A,L
        SUB     E
        MOV     L,A
        MOV     A,H
        SBB     D
        MOV     H,A
        RET

; ---------------------------------------------------------------------------
; Copy exactly 8 bytes.
;
; Input:
;   DE = source address
;   HL = destination address
;
; The source and destination pointers are both advanced by eight.
; ---------------------------------------------------------------------------
glz_copy8:
        ; HL = source address
        ; DE = destination address (highest-address byte of tile)
        MOV     A,M
        STAX    D
        INX     H
        DCX     D
        MOV     A,M
        STAX    D
        INX     H
        DCX     D
        MOV     A,M
        STAX    D
        INX     H
        DCX     D
        MOV     A,M
        STAX    D
        INX     H
        DCX     D
        MOV     A,M
        STAX    D
        INX     H
        DCX     D
        MOV     A,M
        STAX    D
        INX     H
        DCX     D
        MOV     A,M
        STAX    D
        INX     H
        DCX     D
        MOV     A,M
        STAX    D
        RET

; ---------------------------------------------------------------------------
; Copy exactly 8 bytes from a tile already in VRAM.
;
; Input:
;   HL = source tile's highest-address byte
;   DE = destination tile's highest-address byte
;
; Both source and destination advance towards lower addresses.
; ---------------------------------------------------------------------------
glz_copy8_vram:
        MOV     A,M
        STAX    D
        DCX     H
        DCX     D

        MOV     A,M
        STAX    D
        DCX     H
        DCX     D

        MOV     A,M
        STAX    D
        DCX     H
        DCX     D

        MOV     A,M
        STAX    D
        DCX     H
        DCX     D

        MOV     A,M
        STAX    D
        DCX     H
        DCX     D

        MOV     A,M
        STAX    D
        DCX     H
        DCX     D

        MOV     A,M
        STAX    D
        DCX     H
        DCX     D

        MOV     A,M
        STAX    D
        RET

; ---------------------------------------------------------------------------
; Persistent working storage.
; ---------------------------------------------------------------------------
SECTION bss_user

glz_src:         DEFS 2
glz_dict:        DEFS 2
glz_p:           DEFS 2

glz_tpp:         DEFS 2
glz_ntiles:      DEFS 2
glz_cur:         DEFS 2
glz_offset:      DEFS 2
glz_src_tile:    DEFS 2
glz_dst:         DEFS 2

glz_rem:         DEFS 2
glz_quot:        DEFS 2
glz_tmp_word:    DEFS 2
glz_tmp_addr:    DEFS 2

glz_plane:       DEFS 1
glz_tmp_plane:   DEFS 1
glz_hdiv:        DEFS 1
glz_row:         DEFS 1
glz_flag:        DEFS 1
glz_nbits:       DEFS 1
glz_len:         DEFS 1
