; Функция: func_music_tick
; Адрес: 0x3858
; Размер: 52 байта
; Описание: Тик музыкального движка (вызывается из ISR). Копирует
;           var_music_track_ptr в var_music_work_ptr, читает байт длительности
;           (work_ptr+2) и сравнивает со счётчиком var_music_tick; при
;           совпадении обнуляет счётчик. Если var_music_tick == 0 -> вызывает
;           подпрограмму 3890h (вне RDB, обработка смены нот). Затем вызывает
;           func_music_play_note_ch0 и func_music_play_note_ch1, инкрементирует
;           var_music_tick. По адресу 0x3888 в размер объекта попадает
;           вспомогательная обёртка: CALL func_music_init / RET.

func_music_tick:
    PUSH H                      ; 0x3858
    LHLD var_music_track_ptr    ; 0x3859
    SHLD var_music_work_ptr     ; 0x385C
    POP H                       ; 0x385F
    PUSH H                      ; 0x3860
    LHLD var_music_work_ptr     ; 0x3861
    INX H                       ; 0x3864
    INX H                       ; 0x3865
    MOV A, M                    ; 0x3866
    POP H                       ; 0x3867
    MOV B, A                    ; 0x3868
    LDA var_music_tick          ; 0x3869
    CMP B                       ; 0x386C
    JNZ loc_3875                ; 0x386D
    MVI A, 00h                  ; 0x3870
    STA var_music_tick          ; 0x3872
loc_3875:
    CPI 00h                     ; 0x3875
    CZ 3890h                    ; 0x3877
    CALL func_music_play_note_ch0 ; 0x387A
    CALL func_music_play_note_ch1 ; 0x387D
    LDA var_music_tick          ; 0x3880
    INR A                       ; 0x3883
    STA var_music_tick          ; 0x3884
    RET                         ; 0x3887
    CALL func_music_init        ; 0x3888
    RET                         ; 0x388B
