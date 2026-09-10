; sub_1BC9 @ 0x1BC9

SECTION code

PUBLIC _sub_1BC9

_sub_1BC9:
    MOV A, M                    ; 0x1BC9  [126]
    STAX D                       ; 0x1BCA  [18]
    INX H                       ; 0x1BCB  [35]
    INX D                       ; 0x1BCC  [19]
    DCX B                       ; 0x1BCD  [11]
    MOV A, B                    ; 0x1BCE  [120]
    ADC M                       ; 0x1BCF  [177]
    JNZ sub_1BC9                ; 0x1BD0  [194, 201, 27]
    RET                         ; 0x1BD3  [201]
