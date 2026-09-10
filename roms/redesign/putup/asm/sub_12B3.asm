; sub_12B3 @ 0x12B3

SECTION code

PUBLIC _sub_12B3

_sub_12B3:
    LXI H, 0901                 ; 0x12B3  [33, 1, 9]
    DCR M                       ; 0x12B6  [53]
    MOV E, M                    ; 0x12B7  [94]
    LDA 0902                    ; 0x12B8  [58, 2, 9]
    MOV D, A                    ; 0x12BB  [87]
    CALL sub_1BD4                ; 0x12BC  [205, 212, 27]
    SHLD 0903                    ; 0x12BF  [34, 3, 9]
    LHLD 0903                    ; 0x12C2  [42, 3, 9]
    MOV A, M                    ; 0x12C5  [126]
    CPI 77                      ; 0x12C6  [254, 119]
    JNC .loc_12D2               ; 0x12C8  [210, 210, 18]
    INX H                       ; 0x12CB  [35]
    MOV A, M                    ; 0x12CC  [126]
    CPI 77                      ; 0x12CD  [254, 119]
    JC sub_12E0                ; 0x12CF  [218, 224, 18]
.loc_12D2:
    CMP L                       ; 0x12D2  [175]
    STA 0900                    ; 0x12D3  [50, 0, 9]
    STA 0906                    ; 0x12D6  [50, 6, 9]
    LXI H, 0901                 ; 0x12D9  [33, 1, 9]
    INR M                       ; 0x12DC  [52]
    JMP 0D41                    ; 0x12DD  [195, 65, 13]
