; sub_16BE @ 0x16BE

SECTION code

PUBLIC _sub_16BE

_sub_16BE:
    LDA 090E                    ; 0x16BE  [58, 14, 9]
    LXI H, 091F                 ; 0x16C1  [33, 31, 9]
    PUSH PSW                     ; 0x16C4  [245]
    CALL func_table_lookup       ; 0x16C5  [205, 44, 3]
    POP PSW                     ; 0x16C8  [241]
    MOV D, M                    ; 0x16C9  [86]
    DCR D                       ; 0x16CA  [21]
    LXI H, 0922                 ; 0x16CB  [33, 34, 9]
    PUSH PSW                     ; 0x16CE  [245]
    CALL func_table_lookup       ; 0x16CF  [205, 44, 3]
    MOV E, M                    ; 0x16D2  [94]
    LXI H, 270A                 ; 0x16D3  [33, 10, 39]
    CALL sub_1B87                ; 0x16D6  [205, 135, 27]
    POP PSW                     ; 0x16D9  [241]
    LXI H, 091F                 ; 0x16DA  [33, 31, 9]
    PUSH PSW                     ; 0x16DD  [245]
    CALL func_table_lookup       ; 0x16DE  [205, 44, 3]
    POP PSW                     ; 0x16E1  [241]
    MOV D, M                    ; 0x16E2  [86]
    LXI H, 0922                 ; 0x16E3  [33, 34, 9]
    CALL func_table_lookup       ; 0x16E6  [205, 44, 3]
    MOV E, M                    ; 0x16E9  [94]
    LXI H, 2706                 ; 0x16EA  [33, 6, 39]
    LDA 08F9                    ; 0x16ED  [58, 249, 8]
    ADI 0E                      ; 0x16F0  [198, 14]
    CMP B                       ; 0x16F2  [135]
    CMP B                       ; 0x16F3  [135]
    MOV C, A                    ; 0x16F4  [79]
    MVI B, 00                   ; 0x16F5  [6, 0]
    DAD B                       ; 0x16F7  [9]
    CALL sub_1B87                ; 0x16F8  [205, 135, 27]
    RET                         ; 0x16FB  [201]
