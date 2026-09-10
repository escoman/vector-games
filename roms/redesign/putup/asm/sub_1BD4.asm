; sub_1BD4 @ 0x1BD4

SECTION code

PUBLIC _sub_1BD4

_sub_1BD4:
    MOV L, E                    ; 0x1BD4  [107]
    MVI H, 00                   ; 0x1BD5  [38, 0]
    DAD H                       ; 0x1BD7  [41]
    DAD H                       ; 0x1BD8  [41]
    DAD H                       ; 0x1BD9  [41]
    DAD H                       ; 0x1BDA  [41]
    DAD H                       ; 0x1BDB  [41]
    MOV E, D                    ; 0x1BDC  [90]
    MVI D, 00                   ; 0x1BDD  [22, 0]
    DAD D                       ; 0x1BDF  [25]
    LXI D, 5000                 ; 0x1BE0  [17, 0, 80]
    DAD D                       ; 0x1BE3  [25]
    RET                         ; 0x1BE4  [201]
