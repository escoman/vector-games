; sub_0F39 @ 0x0F39

SECTION code

PUBLIC _sub_0F39

_sub_0F39:
    LHLD 08F3                    ; 0x0F39  [42, 243, 8]
    LXI B, 0064                 ; 0x0F3C  [1, 100, 0]
    DAD B                       ; 0x0F3F  [9]
    SHLD 08F3                    ; 0x0F40  [34, 243, 8]
    LXI H, 090F                 ; 0x0F43  [33, 15, 9]
    INR M                       ; 0x0F46  [52]
    MOV A, M                    ; 0x0F47  [126]
    RLC                         ; 0x0F48  [7]
    ADI 17                      ; 0x0F49  [198, 23]
    STA 08FE                    ; 0x0F4B  [50, 254, 8]
    MVI A, 18                   ; 0x0F4E  [62, 24]
    STA 08FF                    ; 0x0F50  [50, 255, 8]
    CALL func_set_stream_pos     ; 0x0F53  [205, 174, 1]
    MVI A, 72                   ; 0x0F56  [62, 114]
    CALL func_data_loader        ; 0x0F58  [205, 161, 1]
    MVI A, 6D                   ; 0x0F5B  [62, 109]
    CALL func_data_loader        ; 0x0F5D  [205, 161, 1]
    JMP sub_0F25                ; 0x0F60  [195, 37, 15]
