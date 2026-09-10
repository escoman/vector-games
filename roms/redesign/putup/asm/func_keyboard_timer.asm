; func_keyboard_timer @ 0x017C
; Keyboard scan + frame timer. IN: A=frame counter (decremented), L=compare value. OUT: A=result (0=key pressed), Z flag. Clobbers: A,flags. Side effect: IN 0x01 every 7 frames.

SECTION code

PUBLIC _func_keyboard_timer

_func_keyboard_timer:
    DCR A                       ; 0x017C  [61]
    JM .loc_0182               ; 0x017D  [250, 130, 1]
    CMP L                       ; 0x0180  [175]
    RET                         ; 0x0181  [201]
.loc_0182:
    MVI A, 07                   ; 0x0182  [62, 7]
    CALL func_read_timer_data    ; 0x0184  [205, 151, 1]
    ANI 80                      ; 0x0187  [230, 128]
    JZ .loc_0195               ; 0x0189  [202, 149, 1]
    IN 01                      ; 0x018C  [219, 1]
    ANI 20                      ; 0x018E  [230, 32]
    JZ .loc_0195               ; 0x0190  [202, 149, 1]
    CMP L                       ; 0x0193  [175]
    RET                         ; 0x0194  [201]
.loc_0195:
    CMA                         ; 0x0195  [47]
    RET                         ; 0x0196  [201]
    PUSH H                       ; 0x0197  [229]
