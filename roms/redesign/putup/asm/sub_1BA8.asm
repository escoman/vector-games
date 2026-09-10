; sub_1BA8 @ 0x1BA8

SECTION code

PUBLIC _sub_1BA8

_sub_1BA8:
    PUSH B                       ; 0x1BA8  [197]
    PUSH H                       ; 0x1BA9  [229]
    CALL sub_1BD4                ; 0x1BAA  [205, 212, 27]
    POP D                       ; 0x1BAD  [209]
    LDAX D                       ; 0x1BAE  [26]
    CALL func_render_block       ; 0x1BAF  [205, 3, 8]
    INX D                       ; 0x1BB2  [19]
    INX H                       ; 0x1BB3  [35]
    LDAX D                       ; 0x1BB4  [26]
    CALL func_render_block       ; 0x1BB5  [205, 3, 8]
    INX D                       ; 0x1BB8  [19]
    LXI B, 001F                 ; 0x1BB9  [1, 31, 0]
    DAD B                       ; 0x1BBC  [9]
    LDAX D                       ; 0x1BBD  [26]
    CALL func_render_block       ; 0x1BBE  [205, 3, 8]
    INX D                       ; 0x1BC1  [19]
    INX H                       ; 0x1BC2  [35]
    LDAX D                       ; 0x1BC3  [26]
    CALL func_render_block       ; 0x1BC4  [205, 3, 8]
    POP B                       ; 0x1BC7  [193]
    RET                         ; 0x1BC8  [201]
