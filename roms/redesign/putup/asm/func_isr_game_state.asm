; func_isr_game_state @ 0x3858
; ISR game state handler. Reads state data from [0x3854] pointer, checks state byte at offset+2. Uses [0x383A] as toggle/counter. Calls sub-functions at 0x3890, 0x3BCA, 0x3C7D depending on state.

SECTION code

PUBLIC _func_isr_game_state

_func_isr_game_state:
    PUSH H                       ; 0x3858  [229]
    LHLD 3854                    ; 0x3859  [42, 84, 56]
    SHLD 0B41                    ; 0x385C  [34, 65, 11]
    POP H                       ; 0x385F  [225]
    PUSH H                       ; 0x3860  [229]
    LHLD 0B41                    ; 0x3861  [42, 65, 11]
    INX H                       ; 0x3864  [35]
    INX H                       ; 0x3865  [35]
    MOV A, M                    ; 0x3866  [126]
    POP H                       ; 0x3867  [225]
    MOV B, A                    ; 0x3868  [71]
    LDA 383A                    ; 0x3869  [58, 58, 56]
    ADD A                       ; 0x386C  [184]
    JNZ .loc_3875               ; 0x386D  [194, 117, 56]
    MVI A, 00                   ; 0x3870  [62, 0]
    STA 383A                    ; 0x3872  [50, 58, 56]
.loc_3875:
    CPI 00                      ; 0x3875  [254, 0]
    CZ sub_3890                ; 0x3877  [204, 144, 56]
    CALL sub_3BCA                ; 0x387A  [205, 202, 59]
    CALL sub_3C7D                ; 0x387D  [205, 125, 60]
    LDA 383A                    ; 0x3880  [58, 58, 56]
    INR A                       ; 0x3883  [60]
    STA 383A                    ; 0x3884  [50, 58, 56]
    RET                         ; 0x3887  [201]
