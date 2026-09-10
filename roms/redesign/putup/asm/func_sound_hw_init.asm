; func_sound_hw_init @ 0x3DCD

SECTION code

PUBLIC _func_sound_hw_init

_func_sound_hw_init:
    LXI H, 3DE8                 ; 0x3DCD  [33, 232, 61]
    LXI D, 03F8                 ; 0x3DD0  [17, 248, 3]
    LXI B, 0003                 ; 0x3DD3  [1, 3, 0]
    DI                          ; 0x3DD6  [243]
    CALL sub_3DB8                ; 0x3DD7  [205, 184, 61]
    EI                          ; 0x3DDA  [251]
    MVI A, 36                   ; 0x3DDB  [62, 54]
    OUT 08                      ; 0x3DDD  [211, 8]
    MVI A, 76                   ; 0x3DDF  [62, 118]
    OUT 08                      ; 0x3DE1  [211, 8]
    MVI A, B6                   ; 0x3DE3  [62, 182]
    OUT 08                      ; 0x3DE5  [211, 8]
    RET                         ; 0x3DE7  [201]
