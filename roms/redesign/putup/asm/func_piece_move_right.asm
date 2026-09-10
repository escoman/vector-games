; func_piece_move_right @ 0x1489

SECTION code

PUBLIC _func_piece_move_right

_func_piece_move_right:
    LDA 090E                    ; 0x1489  [58, 14, 9]
    PUSH PSW                     ; 0x148C  [245]
    LXI H, 091F                 ; 0x148D  [33, 31, 9]
    CALL func_table_lookup       ; 0x1490  [205, 44, 3]
    INR M                       ; 0x1493  [52]
    MOV D, M                    ; 0x1494  [86]
    POP PSW                     ; 0x1495  [241]
    LXI H, 0922                 ; 0x1496  [33, 34, 9]
    CALL func_table_lookup       ; 0x1499  [205, 44, 3]
    MOV E, M                    ; 0x149C  [94]
    CALL sub_1BD4                ; 0x149D  [205, 212, 27]
    INX H                       ; 0x14A0  [35]
    MOV A, M                    ; 0x14A1  [126]
    CPI 20                      ; 0x14A2  [254, 32]
    JNZ .loc_14B1               ; 0x14A4  [194, 177, 20]
    LXI B, 0020                 ; 0x14A7  [1, 32, 0]
    DAD B                       ; 0x14AA  [9]
    MOV A, M                    ; 0x14AB  [126]
    CPI 20                      ; 0x14AC  [254, 32]
    JZ sub_14C6                ; 0x14AE  [202, 198, 20]
.loc_14B1:
    LDA 090E                    ; 0x14B1  [58, 14, 9]
    LXI H, 091F                 ; 0x14B4  [33, 31, 9]
    PUSH PSW                     ; 0x14B7  [245]
    CALL func_table_lookup       ; 0x14B8  [205, 44, 3]
    DCR M                       ; 0x14BB  [53]
    POP PSW                     ; 0x14BC  [241]
    LXI H, 0919                 ; 0x14BD  [33, 25, 9]
    CALL func_table_lookup       ; 0x14C0  [205, 44, 3]
    MVI M, 02                   ; 0x14C3  [54, 2]
    RET                         ; 0x14C5  [201]
