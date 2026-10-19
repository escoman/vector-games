; Функция: func_music_load_voice_params
; Адрес: 0x3902
; Размер: 62 байта (0x3902-0x393F)
; Описание: Последовательно выдает 14 (0x0E) значений параметров голоса из
;           data_voice_param_buf через func_snd_op_keep_a (var_music_work_ptr
;           инкрементируется на каждом шаге), затем загружает 15-й байт
;           (смещение 0x0E) и выдает его с кодом 07h.
;           Примечание: в RDB размер указан как 75, что перекрывает следующие
;           объекты func_snd_op_keep_a (0x3940) и func_music_process_voice
;           (0x3946); фактический конец функции — RET на 0x393F (62 байта).

func_music_load_voice_params:
    PUSH H                          ; 0x3902
    LXI H, data_voice_param_buf     ; 0x3903
    SHLD var_music_work_ptr         ; 0x3906
    POP H                           ; 0x3909
    MVI A, 00h                      ; 0x390A
loc_390C:
    PUSH H                          ; 0x390C
    LHLD var_music_work_ptr         ; 0x390D
    MOV E, M                        ; 0x3910
    POP H                           ; 0x3911
    CALL func_snd_op_keep_a         ; 0x3912
    PUSH H                          ; 0x3915
    LHLD var_music_work_ptr         ; 0x3916
    INX H                           ; 0x3919
    SHLD var_music_work_ptr         ; 0x391A
    POP H                           ; 0x391D
    INR A                           ; 0x391E
    CPI 0Eh                         ; 0x391F
    JNZ loc_390C                    ; 0x3921
    PUSH H                          ; 0x3924
    LXI H, data_voice_param_buf     ; 0x3925
    SHLD var_music_work_ptr         ; 0x3928
    POP H                           ; 0x392B
    PUSH H                          ; 0x392C
    LHLD var_music_work_ptr         ; 0x392D
    PUSH D                          ; 0x3930
    PUSH PSW                        ; 0x3931
    LXI D, 000Eh                    ; 0x3932
    DAD D                           ; 0x3935
    POP PSW                         ; 0x3936
    POP D                           ; 0x3937
    MOV E, M                        ; 0x3938
    POP H                           ; 0x3939
    MVI A, 07h                      ; 0x393A
    CALL func_snd_op_keep_a         ; 0x393C
    RET                             ; 0x393F
