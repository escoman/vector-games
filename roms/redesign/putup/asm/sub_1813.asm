; sub_1813 @ 0x1813

SECTION code

PUBLIC _sub_1813

_sub_1813:
    LDA 090E                    ; 0x1813  [58, 14, 9]
    LXI H, 091F                 ; 0x1816  [33, 31, 9]
    PUSH PSW                     ; 0x1819  [245]
    CALL func_table_lookup       ; 0x181A  [205, 44, 3]
    POP PSW                     ; 0x181D  [241]
    MOV D, M                    ; 0x181E  [86]
    LXI H, 0922                 ; 0x181F  [33, 34, 9]
    PUSH PSW                     ; 0x1822  [245]
    CALL func_table_lookup       ; 0x1823  [205, 44, 3]
    MOV E, M                    ; 0x1826  [94]
    INR E                       ; 0x1827  [28]
    LXI H, 270A                 ; 0x1828  [33, 10, 39]
    CALL sub_1B87                ; 0x182B  [205, 135, 27]
    POP PSW                     ; 0x182E  [241]
    LXI H, 091F                 ; 0x182F  [33, 31, 9]
    PUSH PSW                     ; 0x1832  [245]
    CALL func_table_lookup       ; 0x1833  [205, 44, 3]
    POP PSW                     ; 0x1836  [241]
    MOV D, M                    ; 0x1837  [86]
    LXI H, 0922                 ; 0x1838  [33, 34, 9]
    CALL func_table_lookup       ; 0x183B  [205, 44, 3]
    MOV E, M                    ; 0x183E  [94]
    LXI H, 2706                 ; 0x183F  [33, 6, 39]
    LDA 08F9                    ; 0x1842  [58, 249, 8]
    ADI 0E                      ; 0x1845  [198, 14]
    CMP B                       ; 0x1847  [135]
    CMP B                       ; 0x1848  [135]
    MOV C, A                    ; 0x1849  [79]
    MVI B, 00                   ; 0x184A  [6, 0]
    DAD B                       ; 0x184C  [9]
    CALL sub_1B87                ; 0x184D  [205, 135, 27]
    RET                         ; 0x1850  [201]
