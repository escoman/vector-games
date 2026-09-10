; func_mul7 @ 0x020E
; Multiply [HL] 16-bit value by 12 via DAD chain. IN: HL=ptr to 16-bit value. OUT: HL=value*12. Clobbers: HL,DE. Note: actually x12, not x7.

SECTION code

PUBLIC _func_mul7

_func_mul7:
    MOV A, M                    ; 0x020E  [126]
    INX H                       ; 0x020F  [35]
    MOV H, M                    ; 0x0210  [102]
    MOV L, A                    ; 0x0211  [111]
    DAD H                       ; 0x0212  [41]
    MOV E, L                    ; 0x0213  [93]
    MOV D, H                    ; 0x0214  [84]
    DAD H                       ; 0x0215  [41]
    DAD D                       ; 0x0216  [25]
    DAD H                       ; 0x0217  [41]
    RET                         ; 0x0218  [201]
