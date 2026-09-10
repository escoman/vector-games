; sub_3C77 @ 0x3C77

SECTION code

PUBLIC _sub_3C77

_sub_3C77:
    PUSH PSW                     ; 0x3C77  [245]
    CALL func_jmp_table_dispatch ; 0x3C78  [205, 188, 1]
    POP PSW                     ; 0x3C7B  [241]
    RET                         ; 0x3C7C  [201]
