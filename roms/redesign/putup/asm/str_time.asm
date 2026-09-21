; Данные: str_time
; Адрес: 0x0AFB
; Размер: 6 байт (5 симв. + терминатор 0FFh)
; Назначение: метка HUD "TIME ". Печатается func_draw_status_hud (0x121A) по курсору
;             0x5302 через func_print_string (0x0321). Терминатор — 0FFh.

str_time:
    DEFM "TIME "
    DEFB 0FFh
