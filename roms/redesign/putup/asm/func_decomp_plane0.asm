; func_decomp_plane0 @ 0x0439
; Bitplane 0 decompressor. IN: DE=source (decrementing), HL=dest (incrementing). OUT: DE-=8, HL+=8. Extracts bits 7 and 3 from each source byte. Clobbers: A,B,C,DE,HL.

SECTION code

PUBLIC _func_decomp_plane0

_func_decomp_plane0:
    MVI C, 08                   ; 0x0439  [14, 8]
.loc_043B:
    PUSH B                       ; 0x043B  [197]
    LDAX D                       ; 0x043C  [26]
    DCX D                       ; 0x043D  [27]
    MOV C, A                    ; 0x043E  [79]
    MOV A, M                    ; 0x043F  [126]
    CMA                         ; 0x0440  [47]
    MOV B, A                    ; 0x0441  [71]
    MOV A, C                    ; 0x0442  [121]
    ANI 80                      ; 0x0443  [230, 128]
    MVI A, 00                   ; 0x0445  [62, 0]
    JZ .loc_044B               ; 0x0447  [202, 75, 4]
    MOV A, M                    ; 0x044A  [126]
.loc_044B:
    MOV M, A                    ; 0x044B  [119]
    MOV A, C                    ; 0x044C  [121]
    ANI 08                      ; 0x044D  [230, 8]
    MVI A, 00                   ; 0x044F  [62, 0]
    JZ .loc_0455               ; 0x0451  [202, 85, 4]
    MOV A, B                    ; 0x0454  [120]
.loc_0455:
    ORA M                       ; 0x0455  [182]
    MOV M, A                    ; 0x0456  [119]
    INX H                       ; 0x0457  [35]
    POP B                       ; 0x0458  [193]
    DCR C                       ; 0x0459  [13]
    JNZ .loc_043B               ; 0x045A  [194, 59, 4]
    RET                         ; 0x045D  [201]
