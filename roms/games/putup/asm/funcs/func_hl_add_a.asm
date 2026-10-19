; Функция: func_hl_add_a
; Адрес: 0x032C
; Размер: 5 байт
; Описание: 16-битное прибавление A к HL: ADD L; MOV L,A; RNC; INR H; RET.
;           Используется диспетчером func_sound_op для индексации таблицы
;           переходов data_snd_dispatch_table (базовый адрес + 2*индекс).

func_hl_add_a:
    ADD L                       ; 0x032C
    MOV L, A                    ; 0x032D
    RNC                         ; 0x032E
    INR H                       ; 0x032F
    RET                         ; 0x0330
