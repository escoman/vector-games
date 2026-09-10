; func_text_render @ 0x0321

SECTION code

PUBLIC _func_text_render

_func_text_render:
    MOV A, M                    ; 0x0321  [126]
    INR A                       ; 0x0322  [60]
    RZ                          ; 0x0323  [200]
    DCR A                       ; 0x0324  [61]
    CALL func_data_loader        ; 0x0325  [205, 161, 1]
    INX H                       ; 0x0328  [35]
