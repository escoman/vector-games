; func_decomp_plane3 @ 0x04A8
; Bitplane 3 decompressor. IN: DE=source, HL=dest. OUT: DE-=8, HL+=8. Extracts bits 4 and 0. Clobbers: A,B,C,DE,HL.

SECTION code

PUBLIC _func_decomp_plane3

_func_decomp_plane3:
    MVI C, 08                   ; 0x04A8  [14, 8]
.loc_04AA:
    PUSH B                       ; 0x04AA  [197]
    LDAX D                       ; 0x04AB  [26]
    DCX D                       ; 0x04AC  [27]
    MOV C, A                    ; 0x04AD  [79]
    MOV A, M                    ; 0x04AE  [126]
    CMA                         ; 0x04AF  [47]
    MOV B, A                    ; 0x04B0  [71]
    MOV A, C                    ; 0x04B1  [121]
    ANI 10                      ; 0x04B2  [230, 16]
    MVI A, 00                   ; 0x04B4  [62, 0]
    JZ .loc_04BA               ; 0x04B6  [202, 186, 4]
    MOV A, M                    ; 0x04B9  [126]
.loc_04BA:
    MOV M, A                    ; 0x04BA  [119]
    MOV A, C                    ; 0x04BB  [121]
    ANI 01                      ; 0x04BC  [230, 1]
    MVI A, 00                   ; 0x04BE  [62, 0]
    JZ .loc_04C4               ; 0x04C0  [202, 196, 4]
    MOV A, B                    ; 0x04C3  [120]
.loc_04C4:
    ORA M                       ; 0x04C4  [182]
    MOV M, A                    ; 0x04C5  [119]
    INX H                       ; 0x04C6  [35]
    POP B                       ; 0x04C7  [193]
    DCR C                       ; 0x04C8  [13]
    JNZ .loc_04AA               ; 0x04C9  [194, 170, 4]
    RET                         ; 0x04CC  [201]
