; func_vram_clear @ 0x0EF7
; VRAM clear. IN: B=iteration count (scope), HL=start addr. OUT: VRAM area zeroed. Clobbers: A,B,HL. Saves: H,PSW.

SECTION code

PUBLIC _func_vram_clear

_func_vram_clear:
    PUSH H                       ; 0x0EF7  [229]
    PUSH PSW                     ; 0x0EF8  [245]
.loc_0EF9:
    LXI H, 1000                 ; 0x0EF9  [33, 0, 16]
.loc_0EFC:
    DCX H                       ; 0x0EFC  [43]
    MOV A, L                    ; 0x0EFD  [125]
    ANA M                       ; 0x0EFE  [180]
    JNZ .loc_0EFC               ; 0x0EFF  [194, 252, 14]
    DCR B                       ; 0x0F02  [5]
    JNZ .loc_0EF9               ; 0x0F03  [194, 249, 14]
    POP PSW                     ; 0x0F06  [241]
    POP H                       ; 0x0F07  [225]
    RET                         ; 0x0F08  [201]
    LDA 0905                    ; 0x0F09  [58, 5, 9]
    SUI 6D                      ; 0x0F0C  [214, 109]
