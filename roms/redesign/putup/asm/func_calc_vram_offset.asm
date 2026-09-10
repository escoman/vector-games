; func_calc_vram_offset @ 0x0355
; 16-bit division via repeated subtraction. Computes HL/DE with remainder. Used for coordinate calculations.

SECTION code

PUBLIC _func_calc_vram_offset

_func_calc_vram_offset:
    MVI C, FF                   ; 0x0355  [14, 255]
.loc_0357:
    INR C                       ; 0x0357  [12]
    DAD D                       ; 0x0358  [25]
    JC .loc_0357               ; 0x0359  [218, 87, 3]
    MOV A, L                    ; 0x035C  [125]
    SBB D                       ; 0x035D  [147]
    MOV E, A                    ; 0x035E  [95]
    MOV A, H                    ; 0x035F  [124]
    SUB E                       ; 0x0360  [154]
    MOV D, A                    ; 0x0361  [87]
    MOV A, C                    ; 0x0362  [121]
    XCHG                        ; 0x0363  [235]
    ORI 30                      ; 0x0364  [246, 48]
    PUSH PSW                     ; 0x0366  [245]
    CPI 30                      ; 0x0367  [254, 48]
    JZ .loc_0371               ; 0x0369  [202, 113, 3]
    MVI A, 01                   ; 0x036C  [62, 1]
    STA 08E2                    ; 0x036E  [50, 226, 8]
.loc_0371:
    LDA 08E2                    ; 0x0371  [58, 226, 8]
    CMP M                       ; 0x0374  [183]
    JNZ sub_037F                ; 0x0375  [194, 127, 3]
    MVI A, 20                   ; 0x0378  [62, 32]
    CALL func_data_loader        ; 0x037A  [205, 161, 1]
    POP PSW                     ; 0x037D  [241]
    RET                         ; 0x037E  [201]
