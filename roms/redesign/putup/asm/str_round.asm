; Данные: str_round
; Адрес: 0x0AF4
; Размер: 7 байт (6 симв. + терминатор 0FFh)
; Назначение: метка HUD "ROUND ". Печатается func_draw_status_hud (0x121A) по курсору
;             0x52EF через func_print_string (0x0321). Терминатор — 0FFh.

str_round:
    DEFM "ROUND "
    DEFB 0FFh
