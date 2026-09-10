; func_read_timer_data @ 0x0197

SECTION code

PUBLIC _func_read_timer_data

_func_read_timer_data:
    PUSH H                       ; 0x0197  [229]
    LXI H, 08D3                 ; 0x0198  [33, 211, 8]
    CALL func_table_lookup       ; 0x019B  [205, 44, 3]
    MOV A, M                    ; 0x019E  [126]
    POP H                       ; 0x019F  [225]
    RET                         ; 0x01A0  [201]
