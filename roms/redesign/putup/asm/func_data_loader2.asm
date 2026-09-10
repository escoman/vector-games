; func_data_loader2 @ 0x0145
; Data loader 2: CALL 0x0800, INX H, SHLD 0x0B53. Simpler data loading.

SECTION code

PUBLIC _func_data_loader2

_func_data_loader2:
    PUSH H                       ; 0x0145  [229]
    CALL func_copy_to_vram       ; 0x0146  [205, 0, 8]
    INX H                       ; 0x0149  [35]
    SHLD 0B53                    ; 0x014A  [34, 83, 11]
    POP H                       ; 0x014D  [225]
    RET                         ; 0x014E  [201]
