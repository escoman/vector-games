; func_decomp_plane2 @ 0x0483
; Bitplane 2 decompressor. IN: DE=source, HL=dest. OUT: DE-=8, HL+=8. Extracts bits 5 and 1. Clobbers: A,B,C,DE,HL.

SECTION code

PUBLIC _func_decomp_plane2

_func_decomp_plane2:
    MVI C, 08                   ; 0x0483  [14, 8]
.loc_0485:
    PUSH B                       ; 0x0485  [197]
    LDAX D                       ; 0x0486  [26]
    DCX D                       ; 0x0487  [27]
    MOV C, A                    ; 0x0488  [79]
    MOV A, M                    ; 0x0489  [126]
    CMA                         ; 0x048A  [47]
    MOV B, A                    ; 0x048B  [71]
    MOV A, C                    ; 0x048C  [121]
    ANI 20                      ; 0x048D  [230, 32]
    MVI A, 00                   ; 0x048F  [62, 0]
    JZ .loc_0495               ; 0x0491  [202, 149, 4]
    MOV A, M                    ; 0x0494  [126]
.loc_0495:
    MOV M, A                    ; 0x0495  [119]
    MOV A, C                    ; 0x0496  [121]
    ANI 02                      ; 0x0497  [230, 2]
    MVI A, 00                   ; 0x0499  [62, 0]
    JZ .loc_049F               ; 0x049B  [202, 159, 4]
    MOV A, B                    ; 0x049E  [120]
.loc_049F:
    ORA M                       ; 0x049F  [182]
    MOV M, A                    ; 0x04A0  [119]
    INX H                       ; 0x04A1  [35]
    POP B                       ; 0x04A2  [193]
    DCR C                       ; 0x04A3  [13]
    JNZ .loc_0485               ; 0x04A4  [194, 133, 4]
    RET                         ; 0x04A7  [201]
