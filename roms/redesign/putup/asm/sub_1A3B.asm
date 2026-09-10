; sub_1A3B @ 0x1A3B

SECTION code

PUBLIC _sub_1A3B

_sub_1A3B:
    CALL sub_130A                ; 0x1A3B  [205, 10, 19]
    CALL sub_1BE5                ; 0x1A3E  [205, 229, 27]
    LXI H, 5100                 ; 0x1A41  [33, 0, 81]
    CALL func_store_data_ptr     ; 0x1A44  [205, 79, 1]
    LXI B, 0180                 ; 0x1A47  [1, 128, 1]
.loc_1A4A:
    MVI A, 9C                   ; 0x1A4A  [62, 156]
    CALL func_data_loader        ; 0x1A4C  [205, 161, 1]
    DCX B                       ; 0x1A4F  [11]
    MOV A, C                    ; 0x1A50  [121]
    ADD M                       ; 0x1A51  [176]
    JNZ .loc_1A4A               ; 0x1A52  [194, 74, 26]
    PUSH B                       ; 0x1A55  [197]
    MOV A, B                    ; 0x1A56  [120]
    CMP B                       ; 0x1A57  [135]
    MOV D, A                    ; 0x1A58  [87]
