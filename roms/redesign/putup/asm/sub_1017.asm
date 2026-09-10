; sub_1017 @ 0x1017

SECTION code

PUBLIC _sub_1017

_sub_1017:
    LXI H, 0902                 ; 0x1017  [33, 2, 9]
    DCR M                       ; 0x101A  [53]
    MVI A, 01                   ; 0x101B  [62, 1]
    STA 090D                    ; 0x101D  [50, 13, 9]
    MOV D, M                    ; 0x1020  [86]
    LDA 0901                    ; 0x1021  [58, 1, 9]
    MOV E, A                    ; 0x1024  [95]
    CALL sub_1BD4                ; 0x1025  [205, 212, 27]
    SHLD 0903                    ; 0x1028  [34, 3, 9]
    MOV A, M                    ; 0x102B  [126]
    CPI 77                      ; 0x102C  [254, 119]
    JNC .loc_103B               ; 0x102E  [210, 59, 16]
    LXI B, 0020                 ; 0x1031  [1, 32, 0]
    DAD B                       ; 0x1034  [9]
    MOV A, M                    ; 0x1035  [126]
    CPI 77                      ; 0x1036  [254, 119]
    JC .loc_103F               ; 0x1038  [218, 63, 16]
.loc_103B:
    LXI H, 0902                 ; 0x103B  [33, 2, 9]
    INR M                       ; 0x103E  [52]
.loc_103F:
    JMP 0FFC                    ; 0x103F  [195, 252, 15]
