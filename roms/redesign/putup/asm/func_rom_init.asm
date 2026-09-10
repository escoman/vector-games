; func_rom_init @ 0x0383
; ROM init: PIA port 0x10, timer vars, ISR vector at 0x0038, JMP 0x0B57 at 0x0000, EI

SECTION code

PUBLIC _func_rom_init

_func_rom_init:
    CMP L                       ; 0x0383  [175]
    OUT 10                      ; 0x0384  [211, 16]
    STA 08CF                    ; 0x0386  [50, 207, 8]
    MVI A, E0                   ; 0x0389  [62, 224]
    STA 08D0                    ; 0x038B  [50, 208, 8]
    MVI A, C3                   ; 0x038E  [62, 195]
    STA 0038                    ; 0x0390  [50, 56, 0]
    STA 0000                    ; 0x0393  [50, 0, 0]
    LXI H, 03A4                 ; 0x0396  [33, 164, 3]
    SHLD 0039                    ; 0x0399  [34, 57, 0]
    LXI H, 0B57                 ; 0x039C  [33, 87, 11]
    SHLD 0001                    ; 0x039F  [34, 1, 0]
    EI                          ; 0x03A2  [251]
    RET                         ; 0x03A3  [201]
