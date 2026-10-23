; Данные: str_remastered
; Адрес: 0x0A05 (маркер для сканера gen_layout; реальный адрес — tools/layout.json)
; Размер: 33 байта (32 символа + терминатор 0FFh)
; Назначение: авторская подпись на заставке "REMASTERED BY SARMIN ALEXEY 2026".
;             Печатается в func_main_init по курсору data_text_buffer+0340h
;             (ряд 26 — ниже всего блока credits) в окне var_screen_mode−4,
;             т.е. на 4 px НИЖЕ сетки: y=212..219. Строки str_credits_koi8
;             сдвинуты отдельно: ряд 23 — на +4 px (y=180..187), ряд 25
;             («Центр…», метка str_credits_line2) — на +8 px (y=192..199);
;             ряд 24 пуст (терминатор 0FFh @idx 63).
;             32 символа = ровно вся ширина (32 колонки). Ряд 26 игровой картой
;             не перекрывается; полоса стирается func_clear_vram на старте уровня
;             (CLS затирает всю VRAM 0x8000..0xFFFF) и func_clear_textbuf (0x400
;             байт = все 32 ряда) при пересборке заставки после GAME OVER.
; Все символы — ASCII, в KOI8-R совпадают 1:1. Терминатор — 0FFh.

str_remastered:
    DEFM "REMASTERED BY SARMIN ALEXEY 2026"
    DEFB 0FFh
