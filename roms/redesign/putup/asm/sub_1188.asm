; sub_1188 @ 0x1188

SECTION code

PUBLIC _sub_1188

_sub_1188:
    LHLD 0901                    ; 0x1188  [42, 1, 9]
    XCHG                        ; 0x118B  [235]
    INR E                       ; 0x118C  [28]
    INR E                       ; 0x118D  [28]
    LXI H, 2716                 ; 0x118E  [33, 22, 39]
    CALL sub_1B87                ; 0x1191  [205, 135, 27]
    JMP 0D68                    ; 0x1194  [195, 104, 13]
