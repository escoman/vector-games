; func_piece_move_left @ 0x14F9

SECTION code

PUBLIC _func_piece_move_left

_func_piece_move_left:
    LDA 090E                    ; 0x14F9  [58, 14, 9]
    PUSH PSW                     ; 0x14FC  [245]
    LXI H, 091F                 ; 0x14FD  [33, 31, 9]
    CALL func_table_lookup       ; 0x1500  [205, 44, 3]
    DCR M                       ; 0x1503  [53]
    MOV D, M                    ; 0x1504  [86]
    POP PSW                     ; 0x1505  [241]
    LXI H, 0922                 ; 0x1506  [33, 34, 9]
    CALL func_table_lookup       ; 0x1509  [205, 44, 3]
    MOV E, M                    ; 0x150C  [94]
    CALL sub_1BD4                ; 0x150D  [205, 212, 27]
    MOV A, M                    ; 0x1510  [126]
    CPI 20                      ; 0x1511  [254, 32]
    JNZ .loc_1520               ; 0x1513  [194, 32, 21]
    LXI B, 0020                 ; 0x1516  [1, 32, 0]
    DAD B                       ; 0x1519  [9]
    MOV A, M                    ; 0x151A  [126]
    CPI 20                      ; 0x151B  [254, 32]
    JZ sub_1535                ; 0x151D  [202, 53, 21]
.loc_1520:
    LDA 090E                    ; 0x1520  [58, 14, 9]
    LXI H, 091F                 ; 0x1523  [33, 31, 9]
    PUSH PSW                     ; 0x1526  [245]
    CALL func_table_lookup       ; 0x1527  [205, 44, 3]
    INR M                       ; 0x152A  [52]
    POP PSW                     ; 0x152B  [241]
    LXI H, 0919                 ; 0x152C  [33, 25, 9]
    CALL func_table_lookup       ; 0x152F  [205, 44, 3]
    MVI M, 01                   ; 0x1532  [54, 1]
    RET                         ; 0x1534  [201]
