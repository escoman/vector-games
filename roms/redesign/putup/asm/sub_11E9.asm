; sub_11E9 @ 0x11E9

SECTION code

PUBLIC _sub_11E9

_sub_11E9:
    MVI B, 02                   ; 0x11E9  [6, 2]
    CALL func_sound_init         ; 0x11EB  [205, 33, 1]
    LDA 08FB                    ; 0x11EE  [58, 251, 8]
    CPI 06                      ; 0x11F1  [254, 6]
    JC .loc_1201               ; 0x11F3  [218, 1, 18]
    JZ .loc_1201               ; 0x11F6  [202, 1, 18]
    MVI A, 06                   ; 0x11F9  [62, 6]
    STA 091D                    ; 0x11FB  [50, 29, 9]
    JMP .loc_1204               ; 0x11FE  [195, 4, 18]
.loc_1201:
    STA 091D                    ; 0x1201  [50, 29, 9]
.loc_1204:
    LXI H, 52F9                 ; 0x1204  [33, 249, 82]
    CALL func_store_data_ptr     ; 0x1207  [205, 79, 1]
    LDA 091D                    ; 0x120A  [58, 29, 9]
    MOV B, A                    ; 0x120D  [71]
    CMP M                       ; 0x120E  [183]
    RZ                          ; 0x120F  [200]
    MVI A, 8A                   ; 0x1210  [62, 138]
.loc_1212:
    CALL func_data_loader        ; 0x1212  [205, 161, 1]
    DCR B                       ; 0x1215  [5]
    JNZ .loc_1212               ; 0x1216  [194, 18, 18]
    RET                         ; 0x1219  [201]
