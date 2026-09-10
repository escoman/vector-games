; sub_15A1 @ 0x15A1

SECTION code

PUBLIC _sub_15A1

_sub_15A1:
    LDA 090E                    ; 0x15A1  [58, 14, 9]
    LXI H, 091F                 ; 0x15A4  [33, 31, 9]
    PUSH PSW                     ; 0x15A7  [245]
    CALL func_table_lookup       ; 0x15A8  [205, 44, 3]
    POP PSW                     ; 0x15AB  [241]
    MOV D, M                    ; 0x15AC  [86]
    LXI H, 0922                 ; 0x15AD  [33, 34, 9]
    PUSH PSW                     ; 0x15B0  [245]
    CALL func_table_lookup       ; 0x15B1  [205, 44, 3]
    MOV E, M                    ; 0x15B4  [94]
    INR E                       ; 0x15B5  [28]
    LXI H, 270A                 ; 0x15B6  [33, 10, 39]
    CALL sub_1B87                ; 0x15B9  [205, 135, 27]
    POP PSW                     ; 0x15BC  [241]
    LXI H, 091F                 ; 0x15BD  [33, 31, 9]
    PUSH PSW                     ; 0x15C0  [245]
    CALL func_table_lookup       ; 0x15C1  [205, 44, 3]
    POP PSW                     ; 0x15C4  [241]
    MOV D, M                    ; 0x15C5  [86]
    LXI H, 0922                 ; 0x15C6  [33, 34, 9]
    CALL func_table_lookup       ; 0x15C9  [205, 44, 3]
    MOV E, M                    ; 0x15CC  [94]
    LDA 08F9                    ; 0x15CD  [58, 249, 8]
    ADI 10                      ; 0x15D0  [198, 16]
    CMP B                       ; 0x15D2  [135]
    CMP B                       ; 0x15D3  [135]
    MOV C, A                    ; 0x15D4  [79]
    MVI B, 00                   ; 0x15D5  [6, 0]
    LXI H, 2706                 ; 0x15D7  [33, 6, 39]
    DAD B                       ; 0x15DA  [9]
    CALL sub_1B87                ; 0x15DB  [205, 135, 27]
    RET                         ; 0x15DE  [201]
