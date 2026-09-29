; 4-символьные ключи-читы 20 уровней (уровень N — имя N в data_level_names).
; Сравнивает рутина ввода @0x1277 (сырой код внутри gap_125C: LXI H,1F49h /
; MVI B,14h / при совпадении уровень = 0x15-B-1 → 0x7C66); копирует
; func_init_playfield_buffers (0x1C52) по индексу 4*level в RAM 0x742B для показа.
data_level_keywords:
        defb    55h,4Eh,44h,52h                                   ; уровень 1: UNDR (UNDERGROUND)
        defb    53h,4Eh,41h,4Bh                                   ; уровень 2: SNAK (SNAKE)
        defb    42h,49h,47h,49h                                   ; уровень 3: BIGI (BEGIN)
        defb    47h,52h,41h,53h                                   ; уровень 4: GRAS (GRASP)
        defb    4Ch,41h,44h,52h                                   ; уровень 5: LADR (LADDER)
        defb    32h,54h,4Fh,57h                                   ; уровень 6: 2TOW (TWIN TOWERS)
        defb    41h,53h,43h,49h                                   ; уровень 7: ASCI (ASCII)
        defb    4Ch,4Fh,4Fh,50h                                   ; уровень 8: LOOP (LOOPS)
        defb    52h,4Fh,4Fh,4Dh                                   ; уровень 9: ROOM (ROOMS)
        defb    41h,4Dh,49h,44h                                   ; уровень 10: AMID (AMIDA)
        defb    35h,54h,4Fh,57h                                   ; уровень 11: 5TOW (FIFTH TOWER)
        defb    4Ch,41h,4Bh,45h                                   ; уровень 12: LAKE (IN THE LAKE)
        defb    47h,4Fh,4Ch,47h                                   ; уровень 13: GOLG (GRAVEYARD)
        defb    50h,59h,52h,32h                                   ; уровень 14: PYR2 (PYRAMID^2)
        defb    50h,59h,52h,33h                                   ; уровень 15: PYR3 (PYRAMID^3)
        defb    4Fh,4Fh,42h,41h                                   ; уровень 16: OOBA (PERVERSE)
        defb    50h,59h,52h,31h                                   ; уровень 17: PYR1 (PYRAMID^1)
        defb    50h,59h,52h,34h                                   ; уровень 18: PYR4 (PYRAMID^4)
        defb    54h,52h,41h,50h                                   ; уровень 19: TRAP (TRAPS)
        defb    54h,41h,4Eh,4Bh                                   ; уровень 20: TANK (WATER TANK)
