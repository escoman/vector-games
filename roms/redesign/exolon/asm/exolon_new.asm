; exolon_new.asm — мастер компоновки (Stage 10, tools/gen_layout.py)
; Побайтовая копия exolon.rom из ОДНОГО монолита asm/code.asm.
; Сборка: z80asm -b -m=8080_strict -o=src/EXOLON_NEW.ROM exolon_new.asm

        org 0100h
        include "code.asm"
