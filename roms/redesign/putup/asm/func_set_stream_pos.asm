; func_set_stream_pos @ 0x01AE
; Set stream position from vars 0x08FE/0x08FF. Reads 16-bit via 0x1BD4, stores to 0x0B53.

SECTION code

PUBLIC _func_set_stream_pos

_func_set_stream_pos:
    LDA 08FE                    ; 0x01AE  [58, 254, 8]
    MOV D, A                    ; 0x01B1  [87]
    LDA 08FF                    ; 0x01B2  [58, 255, 8]
    MOV E, A                    ; 0x01B5  [95]
    CALL sub_1BD4                ; 0x01B6  [205, 212, 27]
