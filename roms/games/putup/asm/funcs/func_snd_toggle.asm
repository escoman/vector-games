; Функция: func_snd_toggle
; Адрес: 0x026E
; Размер: 18 байт
; Описание: Переключение/перенастройка звука: E = ror3(E) | E; A = var_snd_state
;           XOR E; индекс = (A & 7); повторный вход в диспетчер через 8-словную
;           таблицу data_snd_toggle_table @0x0280 для включения нужной комбинации
;           каналов. JMP 01C2h — повторный вход в func_sound_op (ANI 0Fh).
;           Примечание: размер в RDB был 16, фактически 18 (0x026E..0x027F).

func_snd_toggle:
    MOV A, E                    ; 0x026E
    RRC                         ; 0x026F
    RRC                         ; 0x0270
    RRC                         ; 0x0271
    ORA E                       ; 0x0272
    MOV E, A                    ; 0x0273
    LDA var_snd_state           ; 0x0274
    XRA E                       ; 0x0277
    LXI H, data_snd_toggle_table ; 0x0278
    ANI 07h                     ; 0x027B
    JMP 01C2h                   ; 0x027D — повторный вход в func_sound_op
