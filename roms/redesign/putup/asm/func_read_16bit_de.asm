; func_read_16bit_de @ 0x010C
; Read 16-bit from [HL] into DE, advance HL+2. Then call func_render_block x4 for data loading. IN: HL=ptr. OUT: DE=value, HL+=2. Clobbers: A,DE,HL.

SECTION code

PUBLIC _func_read_16bit_de

_func_read_16bit_de:
    INX B                       ; 0x010C  [3]
    NOP                         ; 0x010D  [8]
    INX H                       ; 0x010E  [35]
    MOV A, M                    ; 0x010F  [126]
    CALL func_render_block       ; 0x0110  [205, 3, 8]
    LXI B, 001F                 ; 0x0113  [1, 31, 0]
    DAD B                       ; 0x0116  [9]
    MOV A, M                    ; 0x0117  [126]
    CALL func_render_block       ; 0x0118  [205, 3, 8]
    INX H                       ; 0x011B  [35]
