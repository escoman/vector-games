; Функция: func_music_play_note_ch1
; Адрес: 0x3C7D
; Размер: 203 байта (0x3C7D-0x3D47, size=-1 до func_snd_op_keep_a3)
; Описание: Проигрывает ноты канала 1 (и третьего голоса). Проверяет флаг
;           var_music_voice2_flag (3BC8h): если != 0, читает из трека байт по
;           смещению +0Ah — индекс ноты, вычисляет смещение в data_note_table_ch1
;           (индекс*0Ah, цикл loc_3CAD), добавляет var_music_tick, берёт байт по
;           data_voice_param_buf[+8], суммирует и выдаёт через func_snd_op_keep_a3
;           с кодом 08h. Затем по байту 3BC9h (gap, не объект RDB) повторяет для
;           смещения +0Bh: индекс*0Ah в data_note_table_ch1, + var_music_tick,
;           + data_voice_param_buf[+9], выдача с кодом 09h.

func_music_play_note_ch1:
    LDA var_music_voice2_flag       ; 0x3C7D
    CPI 00h                         ; 0x3C80
    JZ loc_3CE3                     ; 0x3C82
    PUSH H                          ; 0x3C85
    LHLD var_music_track_ptr        ; 0x3C86
    SHLD var_music_work_ptr         ; 0x3C89
    POP H                           ; 0x3C8C
    PUSH H                          ; 0x3C8D
    LHLD var_music_work_ptr         ; 0x3C8E
    PUSH D                          ; 0x3C91
    PUSH PSW                        ; 0x3C92
    LXI D, 000Ah                    ; 0x3C93
    DAD D                           ; 0x3C96
    POP PSW                         ; 0x3C97
    POP D                           ; 0x3C98
    MOV A, M                        ; 0x3C99
    POP H                           ; 0x3C9A
    CPI 00h                         ; 0x3C9B
    JZ loc_3CE3                     ; 0x3C9D
    LXI H, data_note_table_ch1      ; 0x3CA0
    DCR A                           ; 0x3CA3
    CPI 00h                         ; 0x3CA4
    JZ loc_3CBA                     ; 0x3CA6
    MOV C, A                        ; 0x3CA9
    MVI A, 00h                      ; 0x3CAA
    MOV B, C                        ; 0x3CAC
loc_3CAD:
    MVI E, 0Ah                      ; 0x3CAD
    ADD E                           ; 0x3CAF
    PUSH PSW                        ; 0x3CB0
    DCR B                           ; 0x3CB1
    JZ loc_3CB9                     ; 0x3CB2
    POP PSW                         ; 0x3CB5
    JMP loc_3CAD                    ; 0x3CB6
loc_3CB9:
    POP PSW                         ; 0x3CB9
loc_3CBA:
    MOV C, A                        ; 0x3CBA
    MVI B, 00h                      ; 0x3CBB
    DAD B                           ; 0x3CBD
    LDA var_music_tick              ; 0x3CBE
    MOV C, A                        ; 0x3CC1
    MVI B, 00h                      ; 0x3CC2
    DAD B                           ; 0x3CC4
    MOV A, M                        ; 0x3CC5
    PUSH H                          ; 0x3CC6
    LXI H, data_voice_param_buf     ; 0x3CC7
    SHLD var_music_work_ptr         ; 0x3CCA
    POP H                           ; 0x3CCD
    PUSH H                          ; 0x3CCE
    LHLD var_music_work_ptr         ; 0x3CCF
    INX H                           ; 0x3CD2
    INX H                           ; 0x3CD3
    INX H                           ; 0x3CD4
    INX H                           ; 0x3CD5
    INX H                           ; 0x3CD6
    INX H                           ; 0x3CD7
    INX H                           ; 0x3CD8
    INX H                           ; 0x3CD9
    MOV B, M                        ; 0x3CDA
    POP H                           ; 0x3CDB
    ADD B                           ; 0x3CDC
    MOV E, A                        ; 0x3CDD
    MVI A, 08h                      ; 0x3CDE
    CALL func_snd_op_keep_a3        ; 0x3CE0
loc_3CE3:
    LDA 3BC9h                       ; 0x3CE3
    CPI 00h                         ; 0x3CE6
    JZ loc_3D47                     ; 0x3CE8
    PUSH H                          ; 0x3CEB
    LHLD var_music_track_ptr        ; 0x3CEC
    SHLD var_music_work_ptr         ; 0x3CEF
    POP H                           ; 0x3CF2
    PUSH H                          ; 0x3CF3
    LHLD var_music_work_ptr         ; 0x3CF4
    PUSH D                          ; 0x3CF7
    PUSH PSW                        ; 0x3CF8
    LXI D, 000Bh                    ; 0x3CF9
    DAD D                           ; 0x3CFC
    POP PSW                         ; 0x3CFD
    POP D                           ; 0x3CFE
    MOV A, M                        ; 0x3CFF
    POP H                           ; 0x3D00
    CPI 00h                         ; 0x3D01
    JZ loc_3D47                     ; 0x3D03
    LXI H, data_note_table_ch1      ; 0x3D06
    DCR A                           ; 0x3D09
    CPI 00h                         ; 0x3D0A
    JZ loc_3D20                     ; 0x3D0C
    MOV C, A                        ; 0x3D0F
    MVI A, 00h                      ; 0x3D10
    MOV B, C                        ; 0x3D12
loc_3D13:
    MVI E, 0Ah                      ; 0x3D13
    ADD E                           ; 0x3D15
    PUSH PSW                        ; 0x3D16
    DCR B                           ; 0x3D17
    JZ loc_3D1F                     ; 0x3D18
    POP PSW                         ; 0x3D1B
    JMP loc_3D13                    ; 0x3D1C
loc_3D1F:
    POP PSW                         ; 0x3D1F
loc_3D20:
    MOV C, A                        ; 0x3D20
    MVI B, 00h                      ; 0x3D21
    DAD B                           ; 0x3D23
    LDA var_music_tick              ; 0x3D24
    MOV C, A                        ; 0x3D27
    DAD B                           ; 0x3D28
    MOV A, M                        ; 0x3D29
    PUSH H                          ; 0x3D2A
    LXI H, data_voice_param_buf     ; 0x3D2B
    SHLD var_music_work_ptr         ; 0x3D2E
    POP H                           ; 0x3D31
    PUSH H                          ; 0x3D32
    LHLD var_music_work_ptr         ; 0x3D33
    PUSH D                          ; 0x3D36
    PUSH PSW                        ; 0x3D37
    LXI D, 0009h                    ; 0x3D38
    DAD D                           ; 0x3D3B
    POP PSW                         ; 0x3D3C
    POP D                           ; 0x3D3D
    MOV B, M                        ; 0x3D3E
    POP H                           ; 0x3D3F
    ADD B                           ; 0x3D40
    MOV E, A                        ; 0x3D41
    MVI A, 09h                      ; 0x3D42
    CALL func_snd_op_keep_a3        ; 0x3D44
loc_3D47:
    RET                             ; 0x3D47
