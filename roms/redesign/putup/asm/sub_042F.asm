; sub_042F @ 0x042F

SECTION code

PUBLIC _sub_042F

_sub_042F:
    PUSH H                       ; 0x042F  [229]
    LXI H, 0008                 ; 0x0430  [33, 8, 0]
    DAD D                       ; 0x0433  [25]
    XCHG                        ; 0x0434  [235]
    POP H                       ; 0x0435  [225]
    JMP 0410                    ; 0x0436  [195, 16, 4]
