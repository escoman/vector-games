; sub_1B87 @ 0x1B87

SECTION code

PUBLIC _sub_1B87

_sub_1B87:
    PUSH B                       ; 0x1B87  [197]
    PUSH H                       ; 0x1B88  [229]
    CALL sub_1BD4                ; 0x1B89  [205, 212, 27]
    POP D                       ; 0x1B8C  [209]
    LDAX D                       ; 0x1B8D  [26]
    CALL func_data_loader2       ; 0x1B8E  [205, 69, 1]
    INX D                       ; 0x1B91  [19]
    INX H                       ; 0x1B92  [35]
    LDAX D                       ; 0x1B93  [26]
    CALL func_data_loader2       ; 0x1B94  [205, 69, 1]
    INX D                       ; 0x1B97  [19]
    LXI B, 001F                 ; 0x1B98  [1, 31, 0]
    DAD B                       ; 0x1B9B  [9]
    LDAX D                       ; 0x1B9C  [26]
    CALL func_data_loader2       ; 0x1B9D  [205, 69, 1]
    INX D                       ; 0x1BA0  [19]
    INX H                       ; 0x1BA1  [35]
    LDAX D                       ; 0x1BA2  [26]
    CALL func_data_loader2       ; 0x1BA3  [205, 69, 1]
    POP B                       ; 0x1BA6  [193]
    RET                         ; 0x1BA7  [201]
