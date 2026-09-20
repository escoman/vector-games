; Функция: func_snd_op_keep_a2
; Адрес: 0x3C77
; Размер: 6 байт
; Описание: Обёртка: вызывает func_sound_op, сохраняя регистр A (PUSH/POP PSW).
;           Используется func_music_play_note_ch0 для выдачи звуковой операции,
;           когда A/E несут параметры звука, которые нельзя искажать флагами.

func_snd_op_keep_a2:
    PUSH PSW                ; 0x3C77
    CALL func_sound_op      ; 0x3C78
    POP PSW                 ; 0x3C7B
    RET                     ; 0x3C7C
