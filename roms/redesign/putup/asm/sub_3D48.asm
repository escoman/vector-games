; sub_3D48 @ 0x3D48

SECTION code

PUBLIC _sub_3D48

_sub_3D48:
    PUSH PSW                     ; 0x3D48  [245]
    CALL func_jmp_table_dispatch ; 0x3D49  [205, 188, 1]
    POP PSW                     ; 0x3D4C  [241]
    RET                         ; 0x3D4D  [201]
