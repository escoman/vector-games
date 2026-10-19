; Функция: func_snd_op_keep_a3
; Адрес: 0x3D48
; Размер: 6 байт
; Описание: Обёртка: вызывает func_sound_op, сохраняя регистр A (PUSH/POP PSW).
;           Используется func_music_play_note_ch1 для выдачи звуковой операции
;           без искажения параметров звука в A/E вызывающего кода.

func_snd_op_keep_a3:
    PUSH PSW                ; 0x3D48
    CALL func_sound_op      ; 0x3D49
    POP PSW                 ; 0x3D4C
    RET                     ; 0x3D4D
