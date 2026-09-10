; sub_18FE @ 0x18FE

SECTION code

PUBLIC _sub_18FE

_sub_18FE:
    LXI H, 0920                 ; 0x18FE  [33, 32, 9]
    LDA 0902                    ; 0x1901  [58, 2, 9]
    ORA A                       ; 0x1904  [190]
    JNC .loc_190C               ; 0x1905  [210, 12, 25]
    DCR M                       ; 0x1908  [53]
    JMP .loc_190D               ; 0x1909  [195, 13, 25]
.loc_190C:
    INR M                       ; 0x190C  [52]
.loc_190D:
    LXI H, 0923                 ; 0x190D  [33, 35, 9]
    LDA 0901                    ; 0x1910  [58, 1, 9]
    ORA A                       ; 0x1913  [190]
    JNC sub_1919                ; 0x1914  [210, 25, 25]
    DCR M                       ; 0x1917  [53]
    RET                         ; 0x1918  [201]
