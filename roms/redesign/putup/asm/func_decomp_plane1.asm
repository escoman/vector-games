; func_decomp_plane1 @ 0x045E
; Bitplane 1 decompressor. IN: DE=source, HL=dest. OUT: DE-=8, HL+=8. Extracts bits 6 and 2. Clobbers: A,B,C,DE,HL.

SECTION code

PUBLIC _func_decomp_plane1

_func_decomp_plane1:
    MVI C, 08                   ; 0x045E  [14, 8]
.loc_0460:
    PUSH B                       ; 0x0460  [197]
    LDAX D                       ; 0x0461  [26]
    DCX D                       ; 0x0462  [27]
    MOV C, A                    ; 0x0463  [79]
    MOV A, M                    ; 0x0464  [126]
    CMA                         ; 0x0465  [47]
    MOV B, A                    ; 0x0466  [71]
    MOV A, C                    ; 0x0467  [121]
    ANI 40                      ; 0x0468  [230, 64]
    MVI A, 00                   ; 0x046A  [62, 0]
    JZ .loc_0470               ; 0x046C  [202, 112, 4]
    MOV A, M                    ; 0x046F  [126]
.loc_0470:
    MOV M, A                    ; 0x0470  [119]
    MOV A, C                    ; 0x0471  [121]
    ANI 04                      ; 0x0472  [230, 4]
    MVI A, 00                   ; 0x0474  [62, 0]
    JZ .loc_047A               ; 0x0476  [202, 122, 4]
    MOV A, B                    ; 0x0479  [120]
.loc_047A:
    ORA M                       ; 0x047A  [182]
    MOV M, A                    ; 0x047B  [119]
    INX H                       ; 0x047C  [35]
    POP B                       ; 0x047D  [193]
    DCR C                       ; 0x047E  [13]
    JNZ .loc_0460               ; 0x047F  [194, 96, 4]
    RET                         ; 0x0482  [201]
