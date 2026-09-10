; sub_1477 @ 0x1477

SECTION code

PUBLIC _sub_1477

_sub_1477:
    PUSH H                       ; 0x1477  [229]
    PUSH PSW                     ; 0x1478  [245]
.loc_1479:
    LXI H, 0000                 ; 0x1479  [33, 0, 0]
.loc_147C:
    DCX H                       ; 0x147C  [43]
    MOV A, L                    ; 0x147D  [125]
    ANA M                       ; 0x147E  [180]
    JNZ .loc_147C               ; 0x147F  [194, 124, 20]
    DCR B                       ; 0x1482  [5]
    JNZ .loc_1479               ; 0x1483  [194, 121, 20]
    POP PSW                     ; 0x1486  [241]
    POP H                       ; 0x1487  [225]
    RET                         ; 0x1488  [201]
