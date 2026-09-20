; Функция: func_music_set_note_params
; Адрес: 0x3B0F
; Размер: 185 байт (0x3B0F-0x3BC7, size=-1 до var_music_voice2_flag)
; Описание: Берёт из текущего байта трека (через var_music_work_ptr) значение
;           ноты, маскирует бит 7, декрементирует и умножает на 8 (цикл
;           loc_3B1B: +08h, DCR B) — получает смещение в data_note_param_table_43F9.
;           Копирует 5 последовательных байт таблицы в data_voice_param_buf по
;           смещениям +4..+8, затем ещё 4 байта по смещениям +0Ah..+0Dh.
;           Последний байт: если != 0 устанавливает бит 5 (ORI 20h) по смещению +0Eh,
;           иначе сбрасывает (ANI DFh). Два выхода RET (0x3BB5 / 0x3BC7).

func_music_set_note_params:
    MOV A, M                        ; 0x3B0F
    ANI 7Fh                         ; 0x3B10
    DCR A                           ; 0x3B12
    CPI 00h                         ; 0x3B13
    JZ loc_3B28                     ; 0x3B15
    MOV B, A                        ; 0x3B18
    MVI A, 00h                      ; 0x3B19
loc_3B1B:
    MVI E, 08h                      ; 0x3B1B
    ADD E                           ; 0x3B1D
    PUSH PSW                        ; 0x3B1E
    DCR B                           ; 0x3B1F
    JZ loc_3B27                     ; 0x3B20
    POP PSW                         ; 0x3B23
    JMP loc_3B1B                    ; 0x3B24
loc_3B27:
    POP PSW                         ; 0x3B27
loc_3B28:
    MOV C, A                        ; 0x3B28
    MVI B, 00h                      ; 0x3B29
    LXI H, data_note_param_table_43F9 ; 0x3B2B
    DAD B                           ; 0x3B2E
    PUSH H                          ; 0x3B2F
    LXI H, data_voice_param_buf     ; 0x3B30
    SHLD var_music_work_ptr         ; 0x3B33
    POP H                           ; 0x3B36
    MOV A, M                        ; 0x3B37
    PUSH H                          ; 0x3B38
    LHLD var_music_work_ptr         ; 0x3B39
    INX H                           ; 0x3B3C
    INX H                           ; 0x3B3D
    INX H                           ; 0x3B3E
    INX H                           ; 0x3B3F
    MOV M, A                        ; 0x3B40
    POP H                           ; 0x3B41
    INX H                           ; 0x3B42
    MOV A, M                        ; 0x3B43
    PUSH H                          ; 0x3B44
    LHLD var_music_work_ptr         ; 0x3B45
    INX H                           ; 0x3B48
    INX H                           ; 0x3B49
    INX H                           ; 0x3B4A
    INX H                           ; 0x3B4B
    INX H                           ; 0x3B4C
    MOV M, A                        ; 0x3B4D
    POP H                           ; 0x3B4E
    INX H                           ; 0x3B4F
    MOV A, M                        ; 0x3B50
    PUSH H                          ; 0x3B51
    LHLD var_music_work_ptr         ; 0x3B52
    INX H                           ; 0x3B55
    INX H                           ; 0x3B56
    INX H                           ; 0x3B57
    INX H                           ; 0x3B58
    INX H                           ; 0x3B59
    INX H                           ; 0x3B5A
    MOV M, A                        ; 0x3B5B
    POP H                           ; 0x3B5C
    INX H                           ; 0x3B5D
    MOV A, M                        ; 0x3B5E
    PUSH H                          ; 0x3B5F
    LHLD var_music_work_ptr         ; 0x3B60
    PUSH D                          ; 0x3B63
    PUSH PSW                        ; 0x3B64
    LXI D, 000Ah                    ; 0x3B65
    DAD D                           ; 0x3B68
    POP PSW                         ; 0x3B69
    POP D                           ; 0x3B6A
    MOV M, A                        ; 0x3B6B
    POP H                           ; 0x3B6C
    INX H                           ; 0x3B6D
    MOV A, M                        ; 0x3B6E
    PUSH H                          ; 0x3B6F
    LHLD var_music_work_ptr         ; 0x3B70
    PUSH D                          ; 0x3B73
    PUSH PSW                        ; 0x3B74
    LXI D, 000Bh                    ; 0x3B75
    DAD D                           ; 0x3B78
    POP PSW                         ; 0x3B79
    POP D                           ; 0x3B7A
    MOV M, A                        ; 0x3B7B
    POP H                           ; 0x3B7C
    INX H                           ; 0x3B7D
    MOV A, M                        ; 0x3B7E
    PUSH H                          ; 0x3B7F
    LHLD var_music_work_ptr         ; 0x3B80
    PUSH D                          ; 0x3B83
    PUSH PSW                        ; 0x3B84
    LXI D, 000Ch                    ; 0x3B85
    DAD D                           ; 0x3B88
    POP PSW                         ; 0x3B89
    POP D                           ; 0x3B8A
    MOV M, A                        ; 0x3B8B
    POP H                           ; 0x3B8C
    INX H                           ; 0x3B8D
    MOV A, M                        ; 0x3B8E
    PUSH H                          ; 0x3B8F
    LHLD var_music_work_ptr         ; 0x3B90
    PUSH D                          ; 0x3B93
    PUSH PSW                        ; 0x3B94
    LXI D, 000Dh                    ; 0x3B95
    DAD D                           ; 0x3B98
    POP PSW                         ; 0x3B99
    POP D                           ; 0x3B9A
    MOV M, A                        ; 0x3B9B
    POP H                           ; 0x3B9C
    INX H                           ; 0x3B9D
    MOV A, M                        ; 0x3B9E
    CPI 00h                         ; 0x3B9F
    JZ loc_3BB6                     ; 0x3BA1
    PUSH PSW                        ; 0x3BA4
    PUSH H                          ; 0x3BA5
    LHLD var_music_work_ptr         ; 0x3BA6
    PUSH D                          ; 0x3BA9
    LXI D, 000Eh                    ; 0x3BAA
    DAD D                           ; 0x3BAD
    POP D                           ; 0x3BAE
    MOV A, M                        ; 0x3BAF
    ORI 20h                         ; 0x3BB0
    MOV M, A                        ; 0x3BB2
    POP H                           ; 0x3BB3
    POP PSW                         ; 0x3BB4
    RET                             ; 0x3BB5
loc_3BB6:
    PUSH PSW                        ; 0x3BB6
    PUSH H                          ; 0x3BB7
    LHLD var_music_work_ptr         ; 0x3BB8
    PUSH D                          ; 0x3BBB
    LXI D, 000Eh                    ; 0x3BBC
    DAD D                           ; 0x3BBF
    POP D                           ; 0x3BC0
    MOV A, M                        ; 0x3BC1
    ANI DFh                         ; 0x3BC2
    MOV M, A                        ; 0x3BC4
    POP H                           ; 0x3BC5
    POP PSW                         ; 0x3BC6
    RET                             ; 0x3BC7
