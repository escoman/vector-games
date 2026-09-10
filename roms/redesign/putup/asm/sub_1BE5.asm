; sub_1BE5 @ 0x1BE5

SECTION code

PUBLIC _sub_1BE5

_sub_1BE5:
    LXI H, 5000                 ; 0x1BE5  [33, 0, 80]
    LXI B, 0400                 ; 0x1BE8  [1, 0, 4]
    CALL func_store_data_ptr     ; 0x1BEB  [205, 79, 1]
.loc_1BEE:
    MVI A, 20                   ; 0x1BEE  [62, 32]
    CALL func_data_loader        ; 0x1BF0  [205, 161, 1]
    DCX B                       ; 0x1BF3  [11]
    MOV A, C                    ; 0x1BF4  [121]
    ADD M                       ; 0x1BF5  [176]
    JNZ .loc_1BEE               ; 0x1BF6  [194, 238, 27]
    RET                         ; 0x1BF9  [201]
