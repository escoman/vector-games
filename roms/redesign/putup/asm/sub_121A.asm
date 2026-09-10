; sub_121A @ 0x121A

SECTION code

PUBLIC _sub_121A

_sub_121A:
    LXI H, 52F2                 ; 0x121A  [33, 242, 82]
    CALL func_store_data_ptr     ; 0x121D  [205, 79, 1]
    LXI H, 08F5                 ; 0x1220  [33, 245, 8]
    CALL 0331                    ; 0x1223  [205, 49, 3]
    LXI H, 52EF                 ; 0x1226  [33, 239, 82]
    CALL func_store_data_ptr     ; 0x1229  [205, 79, 1]
    LXI H, 0AF4                 ; 0x122C  [33, 244, 10]
    CALL func_text_render        ; 0x122F  [205, 33, 3]
    LXI H, 5302                 ; 0x1232  [33, 2, 83]
    CALL func_store_data_ptr     ; 0x1235  [205, 79, 1]
    LXI H, 0AFB                 ; 0x1238  [33, 251, 10]
    CALL func_text_render        ; 0x123B  [205, 33, 3]
    LXI H, 5307                 ; 0x123E  [33, 7, 83]
    CALL func_store_data_ptr     ; 0x1241  [205, 79, 1]
    LDA 091E                    ; 0x1244  [58, 30, 9]
    MOV B, A                    ; 0x1247  [71]
    MVI A, 9B                   ; 0x1248  [62, 155]
.loc_124A:
    CALL func_data_loader        ; 0x124A  [205, 161, 1]
    DCR B                       ; 0x124D  [5]
    JNZ .loc_124A               ; 0x124E  [194, 74, 18]
    RET                         ; 0x1251  [201]
