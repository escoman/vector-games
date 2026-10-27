; SOUNDEMO.ROM main include
; ROM: SOUNDEMO.ROM  Size: 9344  SHA-256: 41eefb4fb175a8c16be1da9cf76d12cf3a2cfcd589a2e750b3cfb3c824467815
; Self-extracting shilin-LZ; decompressed image at 0x0000..0x3FFF

        org     0000h

        include "boot/boot.asm"
        include "boot/unpacker.asm"
        include "code/main.asm"
        include "data/data.asm"
