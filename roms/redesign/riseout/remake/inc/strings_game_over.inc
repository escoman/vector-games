; Текстовый регион вынесен из layout.asm (адреса сохранены): строки без терминатора —
; длину копирования держит код (func_memcpy_bc); метки _end позволяют
; выразить её разностью меток (в коде — str_*_end-str_*).
; In-code литерал «^ GAME OVER ^» (13 байт, без терминатора); единственный источник — LXI H,2356 при 0x2278 в func_game_over_high_score, LXI D,714A и LXI B,000D, копир func_memcpy (0x12E0) в текстовый буфер RAM 0x714A
str_game_over:
        defb    5Eh,20h,47h,41h,4Dh,45h,20h,4Fh
        defb    56h,45h,52h,20h,5Eh
str_game_over_end:
; In-code литерал «HIGH SCORE: 00:» (18 байт, без терминатора); единственный источник — LXI H,2363 при 0x228A в func_game_over_high_score, LXI D,71C8, LXI B,0011 — в RAM 0x71C8 копируются первые 17 байт, завершающее «:» остаётся неиспользованным
str_high_score:
        defb    48h,49h,47h,48h,20h,53h,43h,4Fh
        defb    52h,45h,3Ah,20h,20h,20h,20h,30h
        defb    30h
str_high_score_end:
