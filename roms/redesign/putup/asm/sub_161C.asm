; sub_161C @ 0x161C

SECTION code

PUBLIC _sub_161C

_sub_161C:
    LDA 090E                    ; 0x161C  [58, 14, 9]
    LXI H, 091F                 ; 0x161F  [33, 31, 9]
    PUSH PSW                     ; 0x1622  [245]
    CALL func_table_lookup       ; 0x1623  [205, 44, 3]
    POP PSW                     ; 0x1626  [241]
    MOV D, M                    ; 0x1627  [86]
    LXI H, 0922                 ; 0x1628  [33, 34, 9]
    PUSH PSW                     ; 0x162B  [245]
    CALL func_table_lookup       ; 0x162C  [205, 44, 3]
    MOV E, M                    ; 0x162F  [94]
    DCR E                       ; 0x1630  [29]
    LXI H, 270A                 ; 0x1631  [33, 10, 39]
    CALL sub_1B87                ; 0x1634  [205, 135, 27]
    POP PSW                     ; 0x1637  [241]
    LXI H, 091F                 ; 0x1638  [33, 31, 9]
    PUSH PSW                     ; 0x163B  [245]
    CALL func_table_lookup       ; 0x163C  [205, 44, 3]
    POP PSW                     ; 0x163F  [241]
    MOV D, M                    ; 0x1640  [86]
    LXI H, 0922                 ; 0x1641  [33, 34, 9]
    CALL func_table_lookup       ; 0x1644  [205, 44, 3]
    MOV E, M                    ; 0x1647  [94]
    LXI H, 274A                 ; 0x1648  [33, 74, 39]
    CALL sub_1B87                ; 0x164B  [205, 135, 27]
    RET                         ; 0x164E  [201]
