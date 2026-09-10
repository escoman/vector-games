; sub_12E0 @ 0x12E0

SECTION code

PUBLIC _sub_12E0

_sub_12E0:
    LXI H, 0906                 ; 0x12E0  [33, 6, 9]
    INR M                       ; 0x12E3  [52]
    MOV A, M                    ; 0x12E4  [126]
    CPI 04                      ; 0x12E5  [254, 4]
    JC .loc_12F3               ; 0x12E7  [218, 243, 18]
    CMP L                       ; 0x12EA  [175]
    STA 0906                    ; 0x12EB  [50, 6, 9]
    MVI A, 02                   ; 0x12EE  [62, 2]
    STA 0900                    ; 0x12F0  [50, 0, 9]
.loc_12F3:
    JMP 0D41                    ; 0x12F3  [195, 65, 13]
