; func_piece_move_down @ 0x1568

SECTION code

PUBLIC _func_piece_move_down

_func_piece_move_down:
    LDA 090E                    ; 0x1568  [58, 14, 9]
    PUSH PSW                     ; 0x156B  [245]
    LXI H, 0922                 ; 0x156C  [33, 34, 9]
    CALL func_table_lookup       ; 0x156F  [205, 44, 3]
    DCR M                       ; 0x1572  [53]
    MOV E, M                    ; 0x1573  [94]
    POP PSW                     ; 0x1574  [241]
    LXI H, 091F                 ; 0x1575  [33, 31, 9]
    CALL func_table_lookup       ; 0x1578  [205, 44, 3]
    MOV D, M                    ; 0x157B  [86]
    CALL sub_1BD4                ; 0x157C  [205, 212, 27]
    MOV A, M                    ; 0x157F  [126]
    CPI 20                      ; 0x1580  [254, 32]
    JNZ .loc_158C               ; 0x1582  [194, 140, 21]
    INX H                       ; 0x1585  [35]
    MOV A, M                    ; 0x1586  [126]
    CPI 20                      ; 0x1587  [254, 32]
    JZ sub_15A1                ; 0x1589  [202, 161, 21]
.loc_158C:
    LDA 090E                    ; 0x158C  [58, 14, 9]
    LXI H, 0922                 ; 0x158F  [33, 34, 9]
    PUSH PSW                     ; 0x1592  [245]
    CALL func_table_lookup       ; 0x1593  [205, 44, 3]
    INR M                       ; 0x1596  [52]
    POP PSW                     ; 0x1597  [241]
    LXI H, 0919                 ; 0x1598  [33, 25, 9]
    CALL func_table_lookup       ; 0x159B  [205, 44, 3]
    MVI M, 04                   ; 0x159E  [54, 4]
    RET                         ; 0x15A0  [201]
