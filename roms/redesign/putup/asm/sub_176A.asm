; sub_176A @ 0x176A

SECTION code

PUBLIC _sub_176A

_sub_176A:
    LDA 090E                    ; 0x176A  [58, 14, 9]
    LXI H, 091F                 ; 0x176D  [33, 31, 9]
    PUSH PSW                     ; 0x1770  [245]
    CALL func_table_lookup       ; 0x1771  [205, 44, 3]
    POP PSW                     ; 0x1774  [241]
    MOV D, M                    ; 0x1775  [86]
    INR D                       ; 0x1776  [20]
    LXI H, 0922                 ; 0x1777  [33, 34, 9]
    PUSH PSW                     ; 0x177A  [245]
    CALL func_table_lookup       ; 0x177B  [205, 44, 3]
    MOV E, M                    ; 0x177E  [94]
    LXI H, 270A                 ; 0x177F  [33, 10, 39]
    CALL sub_1B87                ; 0x1782  [205, 135, 27]
    POP PSW                     ; 0x1785  [241]
    LXI H, 091F                 ; 0x1786  [33, 31, 9]
    PUSH PSW                     ; 0x1789  [245]
    CALL func_table_lookup       ; 0x178A  [205, 44, 3]
    POP PSW                     ; 0x178D  [241]
    MOV D, M                    ; 0x178E  [86]
    LXI H, 0922                 ; 0x178F  [33, 34, 9]
    CALL func_table_lookup       ; 0x1792  [205, 44, 3]
    MOV E, M                    ; 0x1795  [94]
    LXI H, 2706                 ; 0x1796  [33, 6, 39]
    LDA 08F9                    ; 0x1799  [58, 249, 8]
    ADI 0E                      ; 0x179C  [198, 14]
    CMP B                       ; 0x179E  [135]
    CMP B                       ; 0x179F  [135]
    MOV C, A                    ; 0x17A0  [79]
    MVI B, 00                   ; 0x17A1  [6, 0]
    DAD B                       ; 0x17A3  [9]
    CALL sub_1B87                ; 0x17A4  [205, 135, 27]
    RET                         ; 0x17A7  [201]
