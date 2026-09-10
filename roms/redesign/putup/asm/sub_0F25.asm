; sub_0F25 @ 0x0F25

SECTION code

PUBLIC _sub_0F25

_sub_0F25:
    CALL sub_1197                ; 0x0F25  [205, 151, 17]
    LDA 0902                    ; 0x0F28  [58, 2, 9]
    MOV D, A                    ; 0x0F2B  [87]
    LDA 0901                    ; 0x0F2C  [58, 1, 9]
    MOV E, A                    ; 0x0F2F  [95]
    LXI H, 270A                 ; 0x0F30  [33, 10, 39]
    CALL sub_1B87                ; 0x0F33  [205, 135, 27]
    JMP func_game_loop          ; 0x0F36  [195, 224, 12]
