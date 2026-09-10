; sub_0104 @ 0x0104

SECTION code

PUBLIC _sub_0104

_sub_0104:
    MOV E, M                    ; 0x0104  [94]
    INX H                       ; 0x0105  [35]
    MOV D, M                    ; 0x0106  [86]
    CALL sub_1BD4                ; 0x0107  [205, 212, 27]
    MOV A, M                    ; 0x010A  [126]
    CALL func_render_block       ; 0x010B  [205, 3, 8]
    INX H                       ; 0x010E  [35]
    MOV A, M                    ; 0x010F  [126]
    CALL func_render_block       ; 0x0110  [205, 3, 8]
    LXI B, 001F                 ; 0x0113  [1, 31, 0]
    DAD B                       ; 0x0116  [9]
    MOV A, M                    ; 0x0117  [126]
    CALL func_render_block       ; 0x0118  [205, 3, 8]
    INX H                       ; 0x011B  [35]
    MOV A, M                    ; 0x011C  [126]
    CALL func_render_block       ; 0x011D  [205, 3, 8]
    RET                         ; 0x0120  [201]
