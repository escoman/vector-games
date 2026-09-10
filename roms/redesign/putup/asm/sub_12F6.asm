; sub_12F6 @ 0x12F6

SECTION code

PUBLIC _sub_12F6

_sub_12F6:
    LXI H, 0906                 ; 0x12F6  [33, 6, 9]
    INR M                       ; 0x12F9  [52]
    MOV A, M                    ; 0x12FA  [126]
    CPI 03                      ; 0x12FB  [254, 3]
    JC .loc_1307               ; 0x12FD  [218, 7, 19]
    CMP L                       ; 0x1300  [175]
    STA 0906                    ; 0x1301  [50, 6, 9]
    STA 0900                    ; 0x1304  [50, 0, 9]
.loc_1307:
    JMP 0D41                    ; 0x1307  [195, 65, 13]
