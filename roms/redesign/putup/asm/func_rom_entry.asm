; func_rom_entry @ 0x0100
; ROM entry: DI; JMP 0x0B57 (decompressed main init)

SECTION code

PUBLIC _func_rom_entry

_func_rom_entry:
    DI                          ; 0x0100  [243]
    JMP func_main_init          ; 0x0101  [195, 87, 11]
