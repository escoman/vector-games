; func_sound_timer_write @ 0x0201
; Sound/timer write: read 16-bit from 0x031A, mul7, OUT 0x0B

SECTION code

PUBLIC _func_sound_timer_write

_func_sound_timer_write:
    LXI H, 031A                 ; 0x0201  [33, 26, 3]
    CALL func_mul7               ; 0x0204  [205, 14, 2]
    MOV A, L                    ; 0x0207  [125]
    OUT 0B                      ; 0x0208  [211, 11]
    MOV A, H                    ; 0x020A  [124]
    OUT 0B                      ; 0x020B  [211, 11]
    RET                         ; 0x020D  [201]
