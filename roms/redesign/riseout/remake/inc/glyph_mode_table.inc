; Атрибуты (режимы) служебных глифов кодов 0x60..0x6F: 16 групп по 8 байт, ROM 0x3514+8*(код-0x60) -> RAM 0x5B00+8*(код-0x60) @0x23F2 (LXI H,3514 / LXI D,5B00 / LXI B,0080 / CALL 017C); func_render_glyph_vram читает режим из RAM 0x5807+8*код для кодов <0x65 и >=0x70 (@0x0579) и из RAM 0x5800+8*код для кодов 0x65..0x6F (@0x05F5), маска режима ANI 0x88
data_glyph_mode_table:
        defb    0F1h,0E1h,0E1h,0E1h,0E1h,0F1h,0F1h,0E1h
        defb    1Eh,1Eh,1Eh,1Eh,1Eh,1Eh,1Eh,1Eh
        defb    1Eh,1Eh,1Eh,1Eh,1Eh,1Eh,1Eh,1Eh
        defb    81h,81h,81h,81h,81h,81h,81h,81h
        defb    41h,41h,41h,41h,41h,41h,41h,41h
        defb    1Eh,1Eh,1Eh,1Eh,1Eh,1Eh,1Eh,1Eh
        defb    04h,44h,04h,44h,04h,44h,04h,04h
        defb    81h,81h,81h,81h,81h,81h,81h,81h
        defb    0C1h,0C1h,0C1h,0C4h,0C4h,0C4h,44h,41h
        defb    01h,0F1h,01h,81h,41h,41h,81h,41h
        defb    01h,0F1h,01h,81h,41h,41h,81h,41h
        defb    14h,14h,14h,14h,14h,14h,14h,14h
        defb    41h,81h,41h,81h,41h,81h,41h,81h
        defb    01h,0F1h,01h,81h,41h,41h,81h,41h
        defb    1Ch,81h,81h,81h,01h,01h,01h,01h
        defb    1Ch,81h,81h,81h,01h,01h,01h,01h
