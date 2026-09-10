; func_read_16bit_v2 @ 0x0351
; Read 16-bit from [HL] into DE. Alternative entry point (same as func_read_16bit_de).

SECTION code

PUBLIC _func_read_16bit_v2

_func_read_16bit_v2:
    MOV A, L                    ; 0x0351  [125]
    JMP 0364                    ; 0x0352  [195, 100, 3]
