; Функция: func_music_play_note_ch0
; Адрес: 0x3BCA
; Размер: 173 байта (0x3BCA-0x3C76, size=-1 до func_snd_op_keep_a2)
; Описание: Проигрывает ноту канала 0. Читает из трека (var_music_track_ptr →
;           var_music_work_ptr) байт по смещению +0Dh — индекс ноты. Если != 0,
;           вычисляет смещение в data_note_freq_table_ch0 (индекс*0x14, цикл
;           loc_3BF2), добавляет var_music_tick (огибающая/вибрато), берёт байт
;           периода из data_voice_param_buf[0], суммирует и выдаёт через
;           func_snd_op_keep_a2 с кодом 00h (канал 0). Затем повторяет то же для
;           байта по смещению +0Eh (loc_3C20): смещение *0x14 в той же таблице,
;           + var_music_tick, + data_voice_param_buf[2], выдача с кодом 02h.

func_music_play_note_ch0:
    PUSH H                          ; 0x3BCA
    LHLD var_music_track_ptr        ; 0x3BCB
    SHLD var_music_work_ptr         ; 0x3BCE
    POP H                           ; 0x3BD1
    PUSH H                          ; 0x3BD2
    LHLD var_music_work_ptr         ; 0x3BD3
    PUSH D                          ; 0x3BD6
    PUSH PSW                        ; 0x3BD7
    LXI D, 000Dh                    ; 0x3BD8
    DAD D                           ; 0x3BDB
    POP PSW                         ; 0x3BDC
    POP D                           ; 0x3BDD
    MOV A, M                        ; 0x3BDE
    POP H                           ; 0x3BDF
    CPI 00h                         ; 0x3BE0
    JZ loc_3C20                     ; 0x3BE2
    LXI H, data_note_freq_table_ch0 ; 0x3BE5
    DCR A                           ; 0x3BE8
    CPI 00h                         ; 0x3BE9
    JZ loc_3BFF                     ; 0x3BEB
    MOV C, A                        ; 0x3BEE
    MVI A, 00h                      ; 0x3BEF
    MOV B, C                        ; 0x3BF1
loc_3BF2:
    MVI E, 14h                      ; 0x3BF2
    ADD E                           ; 0x3BF4
    PUSH PSW                        ; 0x3BF5
    DCR B                           ; 0x3BF6
    JZ loc_3BFE                     ; 0x3BF7
    POP PSW                         ; 0x3BFA
    JMP loc_3BF2                    ; 0x3BFB
loc_3BFE:
    POP PSW                         ; 0x3BFE
loc_3BFF:
    MOV C, A                        ; 0x3BFF
    MVI B, 00h                      ; 0x3C00
    DAD B                           ; 0x3C02
    LDA var_music_tick              ; 0x3C03
    MOV C, A                        ; 0x3C06
    MVI B, 00h                      ; 0x3C07
    DAD B                           ; 0x3C09
    MOV A, M                        ; 0x3C0A
    PUSH H                          ; 0x3C0B
    LXI H, data_voice_param_buf     ; 0x3C0C
    SHLD var_music_work_ptr         ; 0x3C0F
    POP H                           ; 0x3C12
    PUSH H                          ; 0x3C13
    LHLD var_music_work_ptr         ; 0x3C14
    MOV B, M                        ; 0x3C17
    POP H                           ; 0x3C18
    ADD B                           ; 0x3C19
    MOV E, A                        ; 0x3C1A
    MVI A, 00h                      ; 0x3C1B
    CALL func_snd_op_keep_a2        ; 0x3C1D
loc_3C20:
    PUSH H                          ; 0x3C20
    LHLD var_music_track_ptr        ; 0x3C21
    SHLD var_music_work_ptr         ; 0x3C24
    POP H                           ; 0x3C27
    PUSH H                          ; 0x3C28
    LHLD var_music_work_ptr         ; 0x3C29
    PUSH D                          ; 0x3C2C
    PUSH PSW                        ; 0x3C2D
    LXI D, 000Eh                    ; 0x3C2E
    DAD D                           ; 0x3C31
    POP PSW                         ; 0x3C32
    POP D                           ; 0x3C33
    MOV A, M                        ; 0x3C34
    POP H                           ; 0x3C35
    CPI 00h                         ; 0x3C36
    JZ loc_3C76                     ; 0x3C38
    LXI H, data_note_freq_table_ch0 ; 0x3C3B
    DCR A                           ; 0x3C3E
    CPI 00h                         ; 0x3C3F
    JZ loc_3C55                     ; 0x3C41
    MOV C, A                        ; 0x3C44
    MVI A, 00h                      ; 0x3C45
    MOV B, C                        ; 0x3C47
loc_3C48:
    MVI E, 14h                      ; 0x3C48
    ADD E                           ; 0x3C4A
    PUSH PSW                        ; 0x3C4B
    DCR B                           ; 0x3C4C
    JZ loc_3C54                     ; 0x3C4D
    POP PSW                         ; 0x3C50
    JMP loc_3C48                    ; 0x3C51
loc_3C54:
    POP PSW                         ; 0x3C54
loc_3C55:
    MOV C, A                        ; 0x3C55
    MVI B, 00h                      ; 0x3C56
    DAD B                           ; 0x3C58
    LDA var_music_tick              ; 0x3C59
    MOV C, A                        ; 0x3C5C
    DAD B                           ; 0x3C5D
    MOV A, M                        ; 0x3C5E
    PUSH H                          ; 0x3C5F
    LXI H, data_voice_param_buf     ; 0x3C60
    SHLD var_music_work_ptr         ; 0x3C63
    POP H                           ; 0x3C66
    PUSH H                          ; 0x3C67
    LHLD var_music_work_ptr         ; 0x3C68
    INX H                           ; 0x3C6B
    INX H                           ; 0x3C6C
    MOV B, M                        ; 0x3C6D
    POP H                           ; 0x3C6E
    ADD B                           ; 0x3C6F
    MOV E, A                        ; 0x3C70
    MVI A, 02h                      ; 0x3C71
    CALL func_snd_op_keep_a2        ; 0x3C73
loc_3C76:
    RET                             ; 0x3C76
