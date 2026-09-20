; Функция: func_music_process_voice
; Адрес: 0x3946
; Размер: 393 байта (0x3946-0x3B0E, size=-1 до func_music_set_note_params)
; Описание: Обрабатывает текущую ноту по трём каналам. Копирует поля трека из
;           var_music_track_ptr в data_voice_param_buf (через var_music_work_ptr),
;           для каждого канала (индексы нот 383Bh/383Ch/383Dh, таблицы 383Fh/
;           3841h/3843h) вычисляет смещение в таблице нот 421Ah, берёт пару
;           байт (период) и записывает в буфер параметров. Флаг var_music_voice2_flag
;           (3BC8h) и байт 3BC9h управляют ветвлением. При установленном бите 7
;           вызывает func_music_set_note_params (loc_3AC0). В конце вызывает
;           func_music_load_voice_params (loc_3B0B).

func_music_process_voice:
    LHLD var_music_track_ptr    ; 0x3946
    PUSH H                      ; 0x3949
    LXI H, data_voice_param_buf ; 0x394A
    SHLD var_music_work_ptr     ; 0x394D
    POP H                       ; 0x3950
    MOV A, M                    ; 0x3951
    PUSH H                      ; 0x3952
    LHLD var_music_work_ptr     ; 0x3953
    PUSH D                      ; 0x3956
    PUSH PSW                    ; 0x3957
    LXI D, 000Eh                ; 0x3958
    DAD D                       ; 0x395B
    POP PSW                     ; 0x395C
    POP D                       ; 0x395D
    MOV M, A                    ; 0x395E
    POP H                       ; 0x395F
    INX H                       ; 0x3960
    INX H                       ; 0x3961
    INX H                       ; 0x3962
    MOV A, M                    ; 0x3963
    PUSH H                      ; 0x3964
    LHLD var_music_work_ptr     ; 0x3965
    INX H                       ; 0x3968
    INX H                       ; 0x3969
    INX H                       ; 0x396A
    INX H                       ; 0x396B
    INX H                       ; 0x396C
    INX H                       ; 0x396D
    INX H                       ; 0x396E
    INX H                       ; 0x396F
    MOV M, A                    ; 0x3970
    POP H                       ; 0x3971
    INX H                       ; 0x3972
    MOV A, M                    ; 0x3973
    PUSH H                      ; 0x3974
    LHLD var_music_work_ptr     ; 0x3975
    PUSH D                      ; 0x3978
    PUSH PSW                    ; 0x3979
    LXI D, 0009h                ; 0x397A
    DAD D                       ; 0x397D
    POP PSW                     ; 0x397E
    POP D                       ; 0x397F
    MOV M, A                    ; 0x3980
    POP H                       ; 0x3981
    INX H                       ; 0x3982
    MOV A, M                    ; 0x3983
    PUSH H                      ; 0x3984
    LHLD var_music_work_ptr     ; 0x3985
    PUSH D                      ; 0x3988
    PUSH PSW                    ; 0x3989
    LXI D, 000Ah                ; 0x398A
    DAD D                       ; 0x398D
    POP PSW                     ; 0x398E
    POP D                       ; 0x398F
    MOV M, A                    ; 0x3990
    POP H                       ; 0x3991
    INX H                       ; 0x3992
    INX H                       ; 0x3993
    INX H                       ; 0x3994
    INX H                       ; 0x3995
    MOV A, M                    ; 0x3996
    PUSH H                      ; 0x3997
    LHLD var_music_work_ptr     ; 0x3998
    INX H                       ; 0x399B
    INX H                       ; 0x399C
    INX H                       ; 0x399D
    INX H                       ; 0x399E
    INX H                       ; 0x399F
    INX H                       ; 0x39A0
    MOV M, A                    ; 0x39A1
    POP H                       ; 0x39A2
    INX H                       ; 0x39A3
    MOV A, M                    ; 0x39A4
    PUSH H                      ; 0x39A5
    LHLD var_music_work_ptr     ; 0x39A6
    PUSH D                      ; 0x39A9
    PUSH PSW                    ; 0x39AA
    LXI D, 000Bh                ; 0x39AB
    DAD D                       ; 0x39AE
    POP PSW                     ; 0x39AF
    POP D                       ; 0x39B0
    MOV M, A                    ; 0x39B1
    POP H                       ; 0x39B2
    INX H                       ; 0x39B3
    MOV A, M                    ; 0x39B4
    PUSH H                      ; 0x39B5
    LHLD var_music_work_ptr     ; 0x39B6
    PUSH D                      ; 0x39B9
    PUSH PSW                    ; 0x39BA
    LXI D, 000Ch                ; 0x39BB
    DAD D                       ; 0x39BE
    POP PSW                     ; 0x39BF
    POP D                       ; 0x39C0
    MOV M, A                    ; 0x39C1
    POP H                       ; 0x39C2
    INX H                       ; 0x39C3
    MOV A, M                    ; 0x39C4
    PUSH H                      ; 0x39C5
    LHLD var_music_work_ptr     ; 0x39C6
    PUSH D                      ; 0x39C9
    PUSH PSW                    ; 0x39CA
    LXI D, 000Dh                ; 0x39CB
    DAD D                       ; 0x39CE
    POP PSW                     ; 0x39CF
    POP D                       ; 0x39D0
    MOV M, A                    ; 0x39D1
    POP H                       ; 0x39D2
    LHLD 383Fh                  ; 0x39D3
    LDA 383Bh                   ; 0x39D6
    MOV C, A                    ; 0x39D9
    MVI B, 00h                  ; 0x39DA
    DAD B                       ; 0x39DC
    MOV A, M                    ; 0x39DD
    STA var_music_voice2_flag   ; 0x39DE
    CPI 00h                     ; 0x39E1
    JNZ loc_3A01                ; 0x39E3
    MVI A, 00h                  ; 0x39E6
    PUSH H                      ; 0x39E8
    LXI H, data_voice_param_buf ; 0x39E9
    SHLD var_music_work_ptr     ; 0x39EC
    POP H                       ; 0x39EF
    PUSH H                      ; 0x39F0
    LHLD var_music_work_ptr     ; 0x39F1
    INX H                       ; 0x39F4
    INX H                       ; 0x39F5
    INX H                       ; 0x39F6
    INX H                       ; 0x39F7
    INX H                       ; 0x39F8
    INX H                       ; 0x39F9
    INX H                       ; 0x39FA
    INX H                       ; 0x39FB
    MOV M, A                    ; 0x39FC
    POP H                       ; 0x39FD
    JMP loc_3A32                ; 0x39FE
loc_3A01:
    PUSH H                      ; 0x3A01
    LHLD var_music_track_ptr    ; 0x3A02
    SHLD var_music_work_ptr     ; 0x3A05
    POP H                       ; 0x3A08
    MOV B, A                    ; 0x3A09
    PUSH H                      ; 0x3A0A
    LHLD var_music_work_ptr     ; 0x3A0B
    INX H                       ; 0x3A0E
    MOV A, M                    ; 0x3A0F
    POP H                       ; 0x3A10
    ADD B                       ; 0x3A11
    ADD A                       ; 0x3A12
    MOV C, A                    ; 0x3A13
    MVI B, 00h                  ; 0x3A14
    LXI H, 421Ah                ; 0x3A16
    DAD B                       ; 0x3A19
    MOV C, M                    ; 0x3A1A
    INX H                       ; 0x3A1B
    MOV B, M                    ; 0x3A1C
    PUSH H                      ; 0x3A1D
    LXI H, data_voice_param_buf ; 0x3A1E
    SHLD var_music_work_ptr     ; 0x3A21
    POP H                       ; 0x3A24
    PUSH H                      ; 0x3A25
    LHLD var_music_work_ptr     ; 0x3A26
    MOV M, C                    ; 0x3A29
    POP H                       ; 0x3A2A
    PUSH H                      ; 0x3A2B
    LHLD var_music_work_ptr     ; 0x3A2C
    INX H                       ; 0x3A2F
    MOV M, B                    ; 0x3A30
    POP H                       ; 0x3A31
loc_3A32:
    LHLD 3841h                  ; 0x3A32
    LDA 383Ch                   ; 0x3A35
    MOV C, A                    ; 0x3A38
    MVI B, 00h                  ; 0x3A39
    DAD B                       ; 0x3A3B
    MOV A, M                    ; 0x3A3C
    STA 3BC9h                   ; 0x3A3D
    CPI 00h                     ; 0x3A40
    JNZ loc_3A60                ; 0x3A42
    MVI A, 00h                  ; 0x3A45
    PUSH H                      ; 0x3A47
    LXI H, data_voice_param_buf ; 0x3A48
    SHLD var_music_work_ptr     ; 0x3A4B
    POP H                       ; 0x3A4E
    PUSH H                      ; 0x3A4F
    LHLD var_music_work_ptr     ; 0x3A50
    PUSH D                      ; 0x3A53
    PUSH PSW                    ; 0x3A54
    LXI D, 0009h                ; 0x3A55
    DAD D                       ; 0x3A58
    POP PSW                     ; 0x3A59
    POP D                       ; 0x3A5A
    MOV M, A                    ; 0x3A5B
    POP H                       ; 0x3A5C
    JMP loc_3A95                ; 0x3A5D
loc_3A60:
    MOV B, A                    ; 0x3A60
    PUSH H                      ; 0x3A61
    LHLD var_music_track_ptr    ; 0x3A62
    SHLD var_music_work_ptr     ; 0x3A65
    POP H                       ; 0x3A68
    PUSH H                      ; 0x3A69
    LHLD var_music_work_ptr     ; 0x3A6A
    INX H                       ; 0x3A6D
    MOV A, M                    ; 0x3A6E
    POP H                       ; 0x3A6F
    ADD B                       ; 0x3A70
    ADD A                       ; 0x3A71
    MOV C, A                    ; 0x3A72
    MVI B, 00h                  ; 0x3A73
    LXI H, 421Ah                ; 0x3A75
    DAD B                       ; 0x3A78
    MOV C, M                    ; 0x3A79
    INX H                       ; 0x3A7A
    MOV B, M                    ; 0x3A7B
    PUSH H                      ; 0x3A7C
    LXI H, data_voice_param_buf ; 0x3A7D
    SHLD var_music_work_ptr     ; 0x3A80
    POP H                       ; 0x3A83
    PUSH H                      ; 0x3A84
    LHLD var_music_work_ptr     ; 0x3A85
    INX H                       ; 0x3A88
    INX H                       ; 0x3A89
    MOV M, C                    ; 0x3A8A
    POP H                       ; 0x3A8B
    PUSH H                      ; 0x3A8C
    LHLD var_music_work_ptr     ; 0x3A8D
    INX H                       ; 0x3A90
    INX H                       ; 0x3A91
    INX H                       ; 0x3A92
    MOV M, B                    ; 0x3A93
    POP H                       ; 0x3A94
loc_3A95:
    LHLD 3843h                  ; 0x3A95
    LDA 383Dh                   ; 0x3A98
    MOV C, A                    ; 0x3A9B
    MVI B, 00h                  ; 0x3A9C
    DAD B                       ; 0x3A9E
    MOV A, M                    ; 0x3A9F
    CPI 00h                     ; 0x3AA0
    JNZ loc_3AC0                ; 0x3AA2
    MVI A, 00h                  ; 0x3AA5
    PUSH H                      ; 0x3AA7
    LXI H, data_voice_param_buf ; 0x3AA8
    SHLD var_music_work_ptr     ; 0x3AAB
    POP H                       ; 0x3AAE
    PUSH H                      ; 0x3AAF
    LHLD var_music_work_ptr     ; 0x3AB0
    PUSH D                      ; 0x3AB3
    PUSH PSW                    ; 0x3AB4
    LXI D, 000Ah                ; 0x3AB5
    DAD D                       ; 0x3AB8
    POP PSW                     ; 0x3AB9
    POP D                       ; 0x3ABA
    MOV M, A                    ; 0x3ABB
    POP H                       ; 0x3ABC
    JMP loc_3B0B                ; 0x3ABD
loc_3AC0:
    STA 0B3Dh                   ; 0x3AC0
    ANI 80h                     ; 0x3AC3
    LDA 0B3Dh                   ; 0x3AC5
    JZ loc_3AD1                 ; 0x3AC8
    CALL func_music_set_note_params ; 0x3ACB
    JMP loc_3B0B                ; 0x3ACE
loc_3AD1:
    MOV A, M                    ; 0x3AD1
    MOV B, A                    ; 0x3AD2
    PUSH H                      ; 0x3AD3
    LHLD var_music_track_ptr    ; 0x3AD4
    SHLD var_music_work_ptr     ; 0x3AD7
    POP H                       ; 0x3ADA
    PUSH H                      ; 0x3ADB
    LHLD var_music_work_ptr     ; 0x3ADC
    INX H                       ; 0x3ADF
    MOV A, M                    ; 0x3AE0
    POP H                       ; 0x3AE1
    ADD B                       ; 0x3AE2
    ADD A                       ; 0x3AE3
    MOV C, A                    ; 0x3AE4
    MVI B, 00h                  ; 0x3AE5
    LXI H, 421Ah                ; 0x3AE7
    DAD B                       ; 0x3AEA
    MOV C, M                    ; 0x3AEB
    INX H                       ; 0x3AEC
    MOV B, M                    ; 0x3AED
    PUSH H                      ; 0x3AEE
    LXI H, data_voice_param_buf ; 0x3AEF
    SHLD var_music_work_ptr     ; 0x3AF2
    POP H                       ; 0x3AF5
    PUSH H                      ; 0x3AF6
    LHLD var_music_work_ptr     ; 0x3AF7
    INX H                       ; 0x3AFA
    INX H                       ; 0x3AFB
    INX H                       ; 0x3AFC
    INX H                       ; 0x3AFD
    MOV M, C                    ; 0x3AFE
    POP H                       ; 0x3AFF
    PUSH H                      ; 0x3B00
    LHLD var_music_work_ptr     ; 0x3B01
    INX H                       ; 0x3B04
    INX H                       ; 0x3B05
    INX H                       ; 0x3B06
    INX H                       ; 0x3B07
    INX H                       ; 0x3B08
    MOV M, B                    ; 0x3B09
    POP H                       ; 0x3B0A
loc_3B0B:
    CALL func_music_load_voice_params ; 0x3B0B
    RET                         ; 0x3B0E
