; func_sound_init @ 0x0121
; Sound init: 4x dispatch with hardcoded params, clears VRAM. IN: none. OUT: none. Clobbers: A,E. Saves: D,PSW.

SECTION code

PUBLIC _func_sound_init

_func_sound_init:
    PUSH D                       ; 0x0121  [213]
    PUSH PSW                     ; 0x0122  [245]
    MVI E, 0F                   ; 0x0123  [30, 15]
    MVI A, 0A                   ; 0x0125  [62, 10]
    CALL func_jmp_table_dispatch ; 0x0127  [205, 188, 1]
    MVI A, 05                   ; 0x012A  [62, 5]
    MVI E, 00                   ; 0x012C  [30, 0]
    CALL func_jmp_table_dispatch ; 0x012E  [205, 188, 1]
    MVI E, 32                   ; 0x0131  [30, 50]
    MVI A, 04                   ; 0x0133  [62, 4]
    CALL func_jmp_table_dispatch ; 0x0135  [205, 188, 1]
    CALL func_vram_clear         ; 0x0138  [205, 247, 14]
    MVI A, 0A                   ; 0x013B  [62, 10]
    MVI E, 00                   ; 0x013D  [30, 0]
    CALL func_jmp_table_dispatch ; 0x013F  [205, 188, 1]
    POP PSW                     ; 0x0142  [241]
    POP D                       ; 0x0143  [209]
    RET                         ; 0x0144  [201]
