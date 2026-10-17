; basic_new.asm — мастер компоновки RAM-образа BASIC 2.997 (ветвь A).
; Единый ORG + адресный монолит. EQU-справочник подключается до кода
; (байт не добавляет). Собирается строго побайтово в src/basic.r0m.
;
;   z80asm -b -m=8080_strict basic_new.asm -o=basic_new.bin

        org     00000h
        include "equates.asm"
        include "code.asm"
