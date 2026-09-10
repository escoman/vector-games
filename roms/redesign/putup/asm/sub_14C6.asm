; sub_14C6 @ 0x14C6

SECTION code

PUBLIC _sub_14C6

_sub_14C6:
    LDA 090E                    ; 0x14C6  [58, 14, 9]
    LXI H, 091F                 ; 0x14C9  [33, 31, 9]
    PUSH PSW                     ; 0x14CC  [245]
    CALL func_table_lookup       ; 0x14CD  [205, 44, 3]
    POP PSW                     ; 0x14D0  [241]
    MOV D, M                    ; 0x14D1  [86]
    DCR D                       ; 0x14D2  [21]
    LXI H, 0922                 ; 0x14D3  [33, 34, 9]
    PUSH PSW                     ; 0x14D6  [245]
    CALL func_table_lookup       ; 0x14D7  [205, 44, 3]
    MOV E, M                    ; 0x14DA  [94]
    LXI H, 270A                 ; 0x14DB  [33, 10, 39]
    CALL sub_1B87                ; 0x14DE  [205, 135, 27]
    POP PSW                     ; 0x14E1  [241]
    LXI H, 091F                 ; 0x14E2  [33, 31, 9]
    PUSH PSW                     ; 0x14E5  [245]
    CALL func_table_lookup       ; 0x14E6  [205, 44, 3]
    POP PSW                     ; 0x14E9  [241]
    MOV D, M                    ; 0x14EA  [86]
    LXI H, 0922                 ; 0x14EB  [33, 34, 9]
    CALL func_table_lookup       ; 0x14EE  [205, 44, 3]
    MOV E, M                    ; 0x14F1  [94]
    LXI H, 2756                 ; 0x14F2  [33, 86, 39]
    CALL sub_1B87                ; 0x14F5  [205, 135, 27]
    RET                         ; 0x14F8  [201]
