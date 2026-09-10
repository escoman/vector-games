; sub_0159 @ 0x0159

SECTION code

PUBLIC _sub_0159

_sub_0159:
    CMP L                       ; 0x0159  [175]
    CALL func_read_timer_data    ; 0x015A  [205, 151, 1]
    RRC                         ; 0x015D  [15]
    RRC                         ; 0x015E  [15]
    RRC                         ; 0x015F  [15]
    RRC                         ; 0x0160  [15]
    ANI 0F                      ; 0x0161  [230, 15]
    LXI H, 016C                 ; 0x0163  [33, 108, 1]
    MOV E, A                    ; 0x0166  [95]
    MVI D, 00                   ; 0x0167  [22, 0]
    DAD D                       ; 0x0169  [25]
    MOV A, M                    ; 0x016A  [126]
    RET                         ; 0x016B  [201]
