; sub_15DF @ 0x15DF

SECTION code

PUBLIC _sub_15DF

_sub_15DF:
    LDA 090E                    ; 0x15DF  [58, 14, 9]
    PUSH PSW                     ; 0x15E2  [245]
    LXI H, 0922                 ; 0x15E3  [33, 34, 9]
    CALL func_table_lookup       ; 0x15E6  [205, 44, 3]
    INR M                       ; 0x15E9  [52]
    MOV E, M                    ; 0x15EA  [94]
    POP PSW                     ; 0x15EB  [241]
    LXI H, 091F                 ; 0x15EC  [33, 31, 9]
    CALL func_table_lookup       ; 0x15EF  [205, 44, 3]
    MOV D, M                    ; 0x15F2  [86]
    CALL sub_1BD4                ; 0x15F3  [205, 212, 27]
    LXI B, 0020                 ; 0x15F6  [1, 32, 0]
    DAD B                       ; 0x15F9  [9]
    MOV A, M                    ; 0x15FA  [126]
    CPI 20                      ; 0x15FB  [254, 32]
    JNZ .loc_1607               ; 0x15FD  [194, 7, 22]
    INX H                       ; 0x1600  [35]
    MOV A, M                    ; 0x1601  [126]
    CPI 20                      ; 0x1602  [254, 32]
    JZ sub_161C                ; 0x1604  [202, 28, 22]
.loc_1607:
    LDA 090E                    ; 0x1607  [58, 14, 9]
    LXI H, 0922                 ; 0x160A  [33, 34, 9]
    PUSH PSW                     ; 0x160D  [245]
    CALL func_table_lookup       ; 0x160E  [205, 44, 3]
    DCR M                       ; 0x1611  [53]
    POP PSW                     ; 0x1612  [241]
    LXI H, 0919                 ; 0x1613  [33, 25, 9]
    CALL func_table_lookup       ; 0x1616  [205, 44, 3]
    MVI M, 03                   ; 0x1619  [54, 3]
    RET                         ; 0x161B  [201]
