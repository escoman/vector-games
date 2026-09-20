; Функция: func_play_sfx
; Адрес: 0x11E9
; Размер: 5 байт
; Описание: Проигрывание короткого звукового эффекта: MVI B,02h (номер/тон);
;           CALL func_sound_init. Собственного RET не имеет — после возврата из
;           func_sound_init выполнение продолжается fall-through в
;           func_draw_level_hud (0x11EE).

func_play_sfx:
    MVI B, 02h                  ; 0x11E9
    CALL func_sound_init        ; 0x11EB
    ; fall-through в func_draw_level_hud (0x11EE)
