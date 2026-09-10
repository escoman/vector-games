; sub_18C0 @ 0x18C0

SECTION code

PUBLIC _sub_18C0

_sub_18C0:
    LDA 090E                    ; 0x18C0  [58, 14, 9]
    LXI H, 091F                 ; 0x18C3  [33, 31, 9]
    PUSH PSW                     ; 0x18C6  [245]
    CALL func_table_lookup       ; 0x18C7  [205, 44, 3]
    POP PSW                     ; 0x18CA  [241]
    MOV D, M                    ; 0x18CB  [86]
    LXI H, 0922                 ; 0x18CC  [33, 34, 9]
    PUSH PSW                     ; 0x18CF  [245]
    CALL func_table_lookup       ; 0x18D0  [205, 44, 3]
    MOV E, M                    ; 0x18D3  [94]
    DCR E                       ; 0x18D4  [29]
    LXI H, 270A                 ; 0x18D5  [33, 10, 39]
    CALL sub_1B87                ; 0x18D8  [205, 135, 27]
    POP PSW                     ; 0x18DB  [241]
    LXI H, 091F                 ; 0x18DC  [33, 31, 9]
    PUSH PSW                     ; 0x18DF  [245]
    CALL func_table_lookup       ; 0x18E0  [205, 44, 3]
    POP PSW                     ; 0x18E3  [241]
    MOV D, M                    ; 0x18E4  [86]
    LXI H, 0922                 ; 0x18E5  [33, 34, 9]
    CALL func_table_lookup       ; 0x18E8  [205, 44, 3]
    MOV E, M                    ; 0x18EB  [94]
    LXI H, 2706                 ; 0x18EC  [33, 6, 39]
    LDA 08F9                    ; 0x18EF  [58, 249, 8]
    ADI 0E                      ; 0x18F2  [198, 14]
    CMP B                       ; 0x18F4  [135]
    CMP B                       ; 0x18F5  [135]
    MOV C, A                    ; 0x18F6  [79]
    MVI B, 00                   ; 0x18F7  [6, 0]
    DAD B                       ; 0x18F9  [9]
    CALL sub_1B87                ; 0x18FA  [205, 135, 27]
    RET                         ; 0x18FD  [201]
