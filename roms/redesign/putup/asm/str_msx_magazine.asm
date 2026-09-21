; Данные: str_msx_magazine
; Адрес: 0x0AD6
; Размер: 19 байт (18 симв. + терминатор 0FFh)
; Назначение: указание источника на заставке "MSX MAGAZINE, 1987". Печатается по
;             курсору 0x5287 через func_print_string (0x0321). Терминатор — 0FFh.

str_msx_magazine:
    DEFM "MSX MAGAZINE, 1987"
    DEFB 0FFh
