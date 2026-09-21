; Данные: str_congratulation
; Адрес: 0x0B18
; Размер: 17 байт (16 симв. + терминатор 0FFh)
; Назначение: сообщение о прохождении всех 15 уровней "CONGRATULATION !". Печатается
;             в ветке завершения func_level_loader (0x1A3B) по курсору 0x5087 через
;             func_print_string (0x0321). Терминатор — 0FFh.

str_congratulation:
    DEFM "CONGRATULATION !"
    DEFB 0FFh
