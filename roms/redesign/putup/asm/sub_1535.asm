; sub_1535 @ 0x1535

SECTION code

PUBLIC _sub_1535

_sub_1535:
    LDA 090E                    ; 0x1535  [58, 14, 9]
    LXI H, 091F                 ; 0x1538  [33, 31, 9]
    PUSH PSW                     ; 0x153B  [245]
    CALL func_table_lookup       ; 0x153C  [205, 44, 3]
    POP PSW                     ; 0x153F  [241]
    MOV D, M                    ; 0x1540  [86]
    INR D                       ; 0x1541  [20]
    LXI H, 0922                 ; 0x1542  [33, 34, 9]
    PUSH PSW                     ; 0x1545  [245]
    CALL func_table_lookup       ; 0x1546  [205, 44, 3]
    MOV E, M                    ; 0x1549  [94]
    LXI H, 270A                 ; 0x154A  [33, 10, 39]
    CALL sub_1B87                ; 0x154D  [205, 135, 27]
    POP PSW                     ; 0x1550  [241]
    LXI H, 091F                 ; 0x1551  [33, 31, 9]
    PUSH PSW                     ; 0x1554  [245]
    CALL func_table_lookup       ; 0x1555  [205, 44, 3]
    POP PSW                     ; 0x1558  [241]
    MOV D, M                    ; 0x1559  [86]
    LXI H, 0922                 ; 0x155A  [33, 34, 9]
    CALL func_table_lookup       ; 0x155D  [205, 44, 3]
    MOV E, M                    ; 0x1560  [94]
    LXI H, 2752                 ; 0x1561  [33, 82, 39]
    CALL sub_1B87                ; 0x1564  [205, 135, 27]
    RET                         ; 0x1567  [201]
