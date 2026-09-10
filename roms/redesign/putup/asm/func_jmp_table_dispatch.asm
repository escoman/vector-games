; func_jmp_table_dispatch @ 0x01BC
; Jump table dispatcher. IN: A=index (ANI 0F, 0-15), E=param, B=compare. OUT: depends on index (PCHL). Clobbers: A,HL,D. Saves: H,D,PSW.

SECTION code

PUBLIC _func_jmp_table_dispatch

_func_jmp_table_dispatch:
    PUSH H                       ; 0x01BC  [229]
    PUSH D                       ; 0x01BD  [213]
    PUSH PSW                     ; 0x01BE  [245]
    LXI H, 01CD                 ; 0x01BF  [33, 205, 1]
    ANI 0F                      ; 0x01C2  [230, 15]
    CMP B                       ; 0x01C4  [135]
    CALL func_table_lookup       ; 0x01C5  [205, 44, 3]
    MOV D, M                    ; 0x01C8  [86]
    INX H                       ; 0x01C9  [35]
    MOV H, M                    ; 0x01CA  [102]
    MOV L, D                    ; 0x01CB  [106]
    PCHL                        ; 0x01CC  [233]
    DB ED                      ; 0x01CD  [237]
    LXI B, 01F7                 ; 0x01CE  [1, 247, 1]
    DAD D                       ; 0x01D1  [25]
    STAX B                       ; 0x01D2  [2]
    INX H                       ; 0x01D3  [35]
