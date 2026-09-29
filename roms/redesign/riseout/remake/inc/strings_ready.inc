; Текстовый регион вынесен из layout.asm (адреса сохранены): строки без терминатора —
; длину копирования держит код (func_memcpy_bc); метки _end позволяют
; выразить её разностью меток (в коде — str_*_end-str_*).
; In-code литерал «^ READY ^» (9 байт, без терминатора, длина 09 в коде); единственный источник — LXI H,233A при 0x231D в func_level_complete_sequence, копир func_memcpy (0x12E0) в текстовый буфер RAM 0x71CB
str_ready:
        defb    5Eh,20h,52h,45h,41h,44h,59h,20h
        defb    5Eh
str_ready_end:
