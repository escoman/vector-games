; Данные: str_score
; Адрес: 0x0AED
; Размер: 7 байт (6 симв. + терминатор 0FFh)
; Назначение: метка HUD "SCORE ". Печатается func_draw_score_hud (0x1197) по курсору
;             0x52E1 через func_print_string (0x0321), за ней — очки. Терминатор — 0FFh.

str_score:
    DEFM "SCORE "
    DEFB 0FFh
