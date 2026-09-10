; sub_0FD4 @ 0x0FD4

SECTION code

PUBLIC _sub_0FD4

_sub_0FD4:
    LXI H, 0902                 ; 0x0FD4  [33, 2, 9]
    INR M                       ; 0x0FD7  [52]
    CMP L                       ; 0x0FD8  [175]
    STA 090D                    ; 0x0FD9  [50, 13, 9]
    MOV D, M                    ; 0x0FDC  [86]
    LDA 0901                    ; 0x0FDD  [58, 1, 9]
    MOV E, A                    ; 0x0FE0  [95]
    CALL sub_1BD4                ; 0x0FE1  [205, 212, 27]
    SHLD 0903                    ; 0x0FE4  [34, 3, 9]
    INX H                       ; 0x0FE7  [35]
    MOV A, M                    ; 0x0FE8  [126]
    CPI 77                      ; 0x0FE9  [254, 119]
    JNC .loc_0FF8               ; 0x0FEB  [210, 248, 15]
    LXI B, 0020                 ; 0x0FEE  [1, 32, 0]
    DAD B                       ; 0x0FF1  [9]
    MOV A, M                    ; 0x0FF2  [126]
    CPI 77                      ; 0x0FF3  [254, 119]
    JC .loc_0FFC               ; 0x0FF5  [218, 252, 15]
.loc_0FF8:
    LXI H, 0902                 ; 0x0FF8  [33, 2, 9]
    DCR M                       ; 0x0FFB  [53]
.loc_0FFC:
    LDA 08F8                    ; 0x0FFC  [58, 248, 8]
    MOV B, A                    ; 0x0FFF  [71]
    LDA 08F7                    ; 0x1000  [58, 247, 8]
    STA 08F8                    ; 0x1003  [50, 248, 8]
    MOV A, B                    ; 0x1006  [120]
    STA 08F7                    ; 0x1007  [50, 247, 8]
    CMP M                       ; 0x100A  [183]
    JNZ 0D68                    ; 0x100B  [194, 104, 13]
    LDA 08F9                    ; 0x100E  [58, 249, 8]
    STA 0907                    ; 0x1011  [50, 7, 9]
    JMP 0D6D                    ; 0x1014  [195, 109, 13]
