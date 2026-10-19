; Функция: func_sound_init
; Адрес: 0x0121
; Размер: 36 байт
; Описание: Инициализация звука / стартовый тон: CALL func_sound_op (A=0Ah,E=0Fh),
;           (A=05h,E=00h), (A=04h,E=32h), CALL func_delay, (A=0Ah,E=00h).
;           Сохраняет D и PSW. Настраивает канал 2 VI53 и издаёт beep.

func_sound_init:
    PUSH D                      ; 0x0121
    PUSH PSW                    ; 0x0122
    MVI E, 0Fh                  ; 0x0123
    MVI A, 0Ah                  ; 0x0125
    CALL func_sound_op          ; 0x0127
    MVI A, 05h                  ; 0x012A
    MVI E, 00h                  ; 0x012C
    CALL func_sound_op          ; 0x012E
    MVI E, 32h                  ; 0x0131
    MVI A, 04h                  ; 0x0133
    CALL func_sound_op          ; 0x0135
    CALL func_delay             ; 0x0138
    MVI A, 0Ah                  ; 0x013B
    MVI E, 00h                  ; 0x013D
    CALL func_sound_op          ; 0x013F
    POP PSW                     ; 0x0142
    POP D                       ; 0x0143
    RET                         ; 0x0144
