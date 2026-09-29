; Текстовый регион вынесен из layout.asm (адреса сохранены): строки без терминатора —
; длину копирования держит код (func_memcpy_bc); метки _end позволяют
; выразить её разностью меток (в коде — str_*_end-str_*).
; In-code литерал «PLAYER^» (7 байт, без терминатора); единственный источник — LXI H,2388 при 0x237B в func_draw_player_speed_text, LXI D,718C, LXI B,0007, копир func_memcpy (0x12E0), затем ADI 30 / STAX D дописывает номер игрока в RAM 0x7193
str_player_label:
        defb    50h,4Ch,41h,59h,45h,52h,5Eh
str_player_label_end:
