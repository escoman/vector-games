; Данные: str_bonus
; Адрес: 0x0B29
; Размер: 19 байт (18 симв. + терминатор 0FFh)
; Назначение: сообщение о бонусе "BONUS 50000 POINTS". Печатается в ветке завершения
;             func_level_loader (0x1A3B) по курсору 0x50C6 через func_print_string
;             (0x0321). Терминатор — 0FFh.

str_bonus:
    DEFM "BONUS 50000 POINTS"
    DEFB 0FFh
