; Имена 20 уровней — строка NEXT SCENE IS (NUL-терминированный ASCII).
; Читатель: func_level_name_ptr (A = номер уровня) пропускает A-1 строк
; от начала (лимит 0x1E байт на имя) и возвращает HL на имя;
; порядок имён = порядок data_level_keywords (UNDR→UNDERGROUND, ...).
data_level_names:
        defb    55h,4Eh,44h,45h,52h,47h,52h,4Fh,55h,4Eh,44h,00h   ; уровень 1: UNDERGROUND
        defb    53h,4Eh,41h,4Bh,45h,00h                           ; уровень 2: SNAKE
        defb    42h,45h,47h,49h,4Eh,00h                           ; уровень 3: BEGIN
        defb    47h,52h,41h,53h,50h,00h                           ; уровень 4: GRASP
        defb    4Ch,41h,44h,44h,45h,52h,00h                       ; уровень 5: LADDER
        defb    54h,57h,49h,4Eh,20h,54h,4Fh,57h,45h,52h,53h,00h   ; уровень 6: TWIN TOWERS
        defb    41h,53h,43h,49h,49h,00h                           ; уровень 7: ASCII
        defb    4Ch,4Fh,4Fh,50h,53h,00h                           ; уровень 8: LOOPS
        defb    52h,4Fh,4Fh,4Dh,53h,00h                           ; уровень 9: ROOMS
        defb    41h,4Dh,49h,44h,41h,00h                           ; уровень 10: AMIDA
        defb    46h,49h,46h,54h,48h,20h,54h,4Fh,57h,45h,52h,00h   ; уровень 11: FIFTH TOWER
        defb    49h,4Eh,20h,54h,48h,45h,20h,4Ch,41h,4Bh,45h,00h   ; уровень 12: IN THE LAKE
        defb    47h,52h,41h,56h,45h,59h,41h,52h,44h,00h           ; уровень 13: GRAVEYARD
        defb    50h,59h,52h,41h,4Dh,49h,44h,5Eh,32h,00h           ; уровень 14: PYRAMID^2
        defb    50h,59h,52h,41h,4Dh,49h,44h,5Eh,33h,00h           ; уровень 15: PYRAMID^3
        defb    50h,45h,52h,56h,45h,52h,53h,45h,00h               ; уровень 16: PERVERSE
        defb    50h,59h,52h,41h,4Dh,49h,44h,5Eh,31h,00h           ; уровень 17: PYRAMID^1
        defb    50h,59h,52h,41h,4Dh,49h,44h,5Eh,34h,00h           ; уровень 18: PYRAMID^4
        defb    54h,52h,41h,50h,53h,00h                           ; уровень 19: TRAPS
        defb    57h,41h,54h,45h,52h,20h,54h,41h,4Eh,4Bh,00h       ; уровень 20: WATER TANK
