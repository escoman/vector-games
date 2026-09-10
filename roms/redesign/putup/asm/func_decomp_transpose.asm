; func_decomp_transpose @ 0x04CD
; Data transpose/copy. IN: none (hardcoded HL=0x2761, BC=0x6000). OUT: BC=updated dest, HL=updated source. 4 blocks x 8 bytes. Clobbers: A,BC,DE,HL.

SECTION code

PUBLIC _func_decomp_transpose

_func_decomp_transpose:
    LXI H, 2761                 ; 0x04CD  [33, 97, 39]
    LXI B, 6000                 ; 0x04D0  [1, 0, 96]
    LXI D, 0008                 ; 0x04D3  [17, 8, 0]
.loc_04D6:
    MOV A, M                    ; 0x04D6  [126]
    STAX B                       ; 0x04D7  [2]
    DCX H                       ; 0x04D8  [43]
    INX B                       ; 0x04D9  [3]
    DCR E                       ; 0x04DA  [29]
    JNZ .loc_04D6               ; 0x04DB  [194, 214, 4]
    PUSH B                       ; 0x04DE  [197]
    LXI B, 0008                 ; 0x04DF  [1, 8, 0]
    DAD B                       ; 0x04E2  [9]
    POP B                       ; 0x04E3  [193]
    MVI E, 08                   ; 0x04E4  [30, 8]
.loc_04E6:
    MOV A, M                    ; 0x04E6  [126]
    STAX B                       ; 0x04E7  [2]
    DCX H                       ; 0x04E8  [43]
    INX B                       ; 0x04E9  [3]
    DCR E                       ; 0x04EA  [29]
    JNZ .loc_04E6               ; 0x04EB  [194, 230, 4]
    PUSH B                       ; 0x04EE  [197]
    LXI B, 0008                 ; 0x04EF  [1, 8, 0]
    DAD B                       ; 0x04F2  [9]
    POP B                       ; 0x04F3  [193]
    MVI E, 08                   ; 0x04F4  [30, 8]
.loc_04F6:
    MOV A, M                    ; 0x04F6  [126]
    STAX B                       ; 0x04F7  [2]
    DCX H                       ; 0x04F8  [43]
    INX B                       ; 0x04F9  [3]
    DCR E                       ; 0x04FA  [29]
    JNZ .loc_04F6               ; 0x04FB  [194, 246, 4]
    PUSH B                       ; 0x04FE  [197]
    LXI B, 0008                 ; 0x04FF  [1, 8, 0]
    DAD B                       ; 0x0502  [9]
    POP B                       ; 0x0503  [193]
    MVI E, 08                   ; 0x0504  [30, 8]
.loc_0506:
    MOV A, M                    ; 0x0506  [126]
    STAX B                       ; 0x0507  [2]
    DCX H                       ; 0x0508  [43]
    INX B                       ; 0x0509  [3]
    DCR E                       ; 0x050A  [29]
    JNZ .loc_0506               ; 0x050B  [194, 6, 5]
    DCR D                       ; 0x050E  [21]
    MVI E, 08                   ; 0x050F  [30, 8]
    PUSH B                       ; 0x0511  [197]
    LXI B, 0010                 ; 0x0512  [1, 16, 0]
    DAD B                       ; 0x0515  [9]
    POP B                       ; 0x0516  [193]
    JNZ .loc_04D6               ; 0x0517  [194, 214, 4]
    RET                         ; 0x051A  [201]
