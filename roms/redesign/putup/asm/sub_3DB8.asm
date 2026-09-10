; sub_3DB8 @ 0x3DB8

SECTION code

PUBLIC _sub_3DB8

_sub_3DB8:
    PUSH PSW                     ; 0x3DB8  [245]
.loc_3DB9:
    MOV A, M                    ; 0x3DB9  [126]
    STAX D                       ; 0x3DBA  [18]
    INX H                       ; 0x3DBB  [35]
    INX D                       ; 0x3DBC  [19]
    DCX B                       ; 0x3DBD  [11]
    MOV A, B                    ; 0x3DBE  [120]
    ADC M                       ; 0x3DBF  [177]
    JNZ .loc_3DB9               ; 0x3DC0  [194, 185, 61]
    POP PSW                     ; 0x3DC3  [241]
    RET                         ; 0x3DC4  [201]
