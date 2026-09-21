; Данные: str_push_space
; Адрес: 0x0AC7
; Размер: 15 байт (14 симв. + терминатор 0FFh)
; Назначение: подсказка на заставке "PUSH SPACE KEY". Печатается по курсору 0x5229
;             через func_print_string (0x0321). Терминатор строки — 0FFh.

str_push_space:
    DEFM "PUSH SPACE KEY"
    DEFB 0FFh
