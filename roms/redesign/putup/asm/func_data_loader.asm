; func_data_loader @ 0x01A1
; Data loader: reads ptr from [0x0B53], calls 0x0800, increments ptr

SECTION code

PUBLIC _func_data_loader

_func_data_loader:
    PUSH H                       ; 0x01A1  [229]
    LHLD 0B53                    ; 0x01A2  [42, 83, 11]
    CALL func_copy_to_vram       ; 0x01A5  [205, 0, 8]
    INX H                       ; 0x01A8  [35]
    SHLD 0B53                    ; 0x01A9  [34, 83, 11]
    POP H                       ; 0x01AC  [225]
    RET                         ; 0x01AD  [201]
