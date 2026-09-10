; func_piece_type_lookup @ 0x0153
; Piece type lookup: uses timer upper nibble as index into 9-byte table at 0x016C. IN: A=piece type (1-7). OUT: A=variant (0-7). Clobbers: A,D,E,HL.

SECTION code

PUBLIC _func_piece_type_lookup

_func_piece_type_lookup:
    DCR A                       ; 0x0153  [61]
    JM sub_0159                ; 0x0154  [250, 89, 1]
    CMP L                       ; 0x0157  [175]
    RET                         ; 0x0158  [201]
