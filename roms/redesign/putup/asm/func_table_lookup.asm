; func_table_lookup @ 0x032C
; Table lookup: XRA B, MOV L,A; RNC/INR H for carry. Index calculations.

SECTION code

PUBLIC _func_table_lookup

_func_table_lookup:
    XRA B                       ; 0x032C  [133]
    MOV L, A                    ; 0x032D  [111]
    RNC                         ; 0x032E  [208]
    INR H                       ; 0x032F  [36]
    RET                         ; 0x0330  [201]
    MOV E, M                    ; 0x0331  [94]
    INX H                       ; 0x0332  [35]
    MOV D, M                    ; 0x0333  [86]
    CMP L                       ; 0x0334  [175]
    STA 08E2                    ; 0x0335  [50, 226, 8]
    XCHG                        ; 0x0338  [235]
    LXI D, D8F0                 ; 0x0339  [17, 240, 216]
    CALL func_calc_vram_offset   ; 0x033C  [205, 85, 3]
