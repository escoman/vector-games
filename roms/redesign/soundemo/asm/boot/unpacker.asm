; ===========================================================================
; SOUNDEMO.ROM "shilin" LZ-like unpacker
; Loaded to 0xFF50 by boot; source in ROM at file offset 0x50..0xEF (160 B)
; ===========================================================================
; Opcode classes:
;   0x00..0x2F  literal run of A bytes
;   0x30..0xAF  short back-ref: 2..3-byte copy, offset 2..65 bytes back
;   0xB0..0xCF  medium back-ref: 3-byte opcode, 2-byte operand
;   0xD0..0xEF  zero fill: (A - 0xCE) zeros
;   0xF0..0xFE  RLE fill: (A - 0xED) bytes with next-byte value
;   0xFF        END -- PCHL to stored entry (0x0100)
; ===========================================================================
        .area UNPACKER (ABS)
        .org 0xFF50

    LXI  D, 0100h           ; FF50:  DE = output pointer (0x0100)
    LXI  H, DA80h           ; FF53:  HL = compressed stream base (0xDA80)
loop:
    MOV  A, M               ; FF56:  read opcode
    INX  H                  ; FF57:  advance
    CPI  30h                ; FF58:  class boundary test
    JNC  op_ge_30           ; FF5A:  if A >= 0x30 next class
lit_count:
    MOV  B, A               ; FF5D:  B = literal-run length (1..0x2F)
lit_loop:
    MOV  A, M               ; FF5E:  read literal byte
    STAX D                  ; FF5F:  write literal
    INX  D                  ; FF60:  
    INX  H                  ; FF61:  
    DCR  B                  ; FF62:  count--
    JP   lit_loop           ; FF63:  loop while B >= 0
    JMP  loop               ; FF66:  next opcode
op_ge_30:
    CPI  B0h                ; FF69:  
    JNC  op_ge_B0           ; FF6B:  
    SUI  30h                ; FF6E:  opcode - 0x30 -> 0..0x7F
    MOV  B, A               ; FF70:  save opcode bits
    ANI  3Fh                ; FF71:  low 6 bits = length low
    ADI  02h                ; FF73:  length += 2 (2..65)
    CMA                     ; FF75:  negate
    INR  A                  ; FF76:  two's complement -> -length
    PUSH H                  ; FF77:  save HL (input ptr)
    ADD  E                  ; FF78:  compute DE - length -> back-ref source
    MOV  L, A               ; FF79:  
    MOV  A, D               ; FF7A:  
    CMC                     ; FF7B:  
    SBI  00h                ; FF7C:  
    MOV  H, A               ; FF7E:  HL = source pointer
    MOV  A, B               ; FF7F:  restore opcode bits
    ANI  40h                ; FF80:  bit 6 = extra length
    MVI  B, 06h             ; FF82:  rotate 6x to shift bit6 -> bit0
rot6:
    RRC                     ; FF84:  
    DCR  B                  ; FF85:  
    JNZ  rot6               ; FF86:  
    ADI  02h                ; FF89:  copy count = 2 or 3
    MOV  B, A               ; FF8B:  
cp30_loop:
    MOV  A, M               ; FF8C:  
    STAX D                  ; FF8D:  
    INX  H                  ; FF8E:  
    INX  D                  ; FF8F:  
    DCR  B                  ; FF90:  
    JNZ  cp30_loop          ; FF91:  
    POP  H                  ; FF94:  restore input ptr
    JMP  loop               ; FF95:  
op_ge_B0:
    CPI  D0h                ; FF98:  
    JNC  op_ge_D0           ; FF9A:  
    SUI  B0h                ; FF9D:  opcode - 0xB0 -> 0..0x1F
    MOV  B, A               ; FF9F:  
    PUSH H                  ; FFA0:  
    MOV  L, M               ; FFA1:  L = next byte = offset low
    ANI  0Fh                ; FFA2:  
    ADI  03h                ; FFA4:  length low += 3
    MOV  C, A               ; FFA6:  
    MOV  A, B               ; FFA7:  
    ANI  10h                ; FFA8:  bit 4 = offset high bit
    MVI  B, 04h             ; FFAA:  
rot4:
    RRC                     ; FFAC:  
    DCR  B                  ; FFAD:  
    JNZ  rot4               ; FFAE:  
    MOV  H, A               ; FFB1:  H = 0 or 1
    INX  H                  ; FFB2:  
    INX  H                  ; FFB3:  
    INX  H                  ; FFB4:  H = 2 or 3 (offset high byte bias)
    MOV  A, E               ; FFB5:  compute DE - offset (16-bit)
    SUB  L                  ; FFB6:  
    MOV  L, A               ; FFB7:  
    MOV  A, D               ; FFB8:  
    SBB  H                  ; FFB9:  
    MOV  H, A               ; FFBA:  
cpB0_loop:
    MOV  A, M               ; FFBB:  
    STAX D                  ; FFBC:  
    INX  H                  ; FFBD:  
    INX  D                  ; FFBE:  
    DCR  C                  ; FFBF:  
    JNZ  cpB0_loop          ; FFC0:  
    POP  H                  ; FFC3:  
    INX  H                  ; FFC4:  skip 2-byte operand
    JMP  loop               ; FFC5:  
op_ge_D0:
    CPI  F0h                ; FFC8:  
    JNC  op_ge_F0           ; FFCA:  
    SUI  CEh                ; FFCD:  opcode - 0xCE -> 2..0x21 zeros
    MOV  B, A               ; FFCF:  
    XRA  A                  ; FFD0:  value = 0
zero_loop:
    STAX D                  ; FFD1:  
    INX  D                  ; FFD2:  
    DCR  B                  ; FFD3:  
    JNZ  zero_loop          ; FFD4:  
    JMP  loop               ; FFD7:  
op_ge_F0:
    CPI  FFh                ; FFDA:  
    JZ   end_of_stream      ; FFDC:  
    SUI  EDh                ; FFDF:  opcode - 0xED -> 3..0x11 RLE len
    MOV  B, A               ; FFE1:  
    MOV  A, M               ; FFE2:  read RLE fill value
    INX  H                  ; FFE3:  
    JMP  zero_loop          ; FFE4:  reuse fill loop with A=value
end_of_stream:
    LHLD 0FF51h             ; FFE7:  load stored DE low at 0xFF51..0xFF52
    PCHL                    ; FFEA:  jump to 0x0100 (initial DE value)
