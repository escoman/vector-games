; Функция: func_music_init
; Адрес: 0x3D4E
; Размер: 106 байт (0x3D4E-0x3DB7, size=-1 до func_memcpy_keep_psw)
; Описание: Инициализация музыкального движка. Запрещает прерывания (DI),
;           обнуляет var_music_tick (383Ah) и три байта индексов нот 383Bh/
;           383Ch/383Dh. Загружает var_music_track_base (3856h) и записывает
;           младший/старший байты базового указателя трека в три пары ячеек
;           области 383Fh (указатели голосов 383Fh/3841h/3843h) с шагом +0100h
;           для каждого следующего голоса. Затем готовит H=3DCAh (вектор
;           "CALL func_music_tick"), D=03F8h, B=0003h и прыгает на 3DC5h —
;           обёртку (CALL func_memcpy_keep_psw; EI; RET), которая копирует 3 байта
;           в RAM 03F8h (установка хука таймера/ISR) и разрешает прерывания.
;           Примечание: 383Bh/383Ch/383Dh/383Fh, 3DCAh и 3DC5h — gap-байты,
;           не объекты RDB, оставлены как hex.

func_music_init:
    DI                          ; 0x3D4E
    MVI A, 00h                  ; 0x3D4F
    STA var_music_tick          ; 0x3D51
    STA 383Bh                   ; 0x3D54
    STA 383Ch                   ; 0x3D57
    STA 383Dh                   ; 0x3D5A
    LHLD var_music_track_base   ; 0x3D5D
    PUSH H                      ; 0x3D60
    LXI H, 383Fh                ; 0x3D61
    SHLD var_music_work_ptr     ; 0x3D64
    POP H                       ; 0x3D67
    XCHG                        ; 0x3D68
    PUSH H                      ; 0x3D69
    LHLD var_music_work_ptr     ; 0x3D6A
    MOV M, E                    ; 0x3D6D
    POP H                       ; 0x3D6E
    XCHG                        ; 0x3D6F
    XCHG                        ; 0x3D70
    PUSH H                      ; 0x3D71
    LHLD var_music_work_ptr     ; 0x3D72
    INX H                       ; 0x3D75
    MOV M, D                    ; 0x3D76
    POP H                       ; 0x3D77
    XCHG                        ; 0x3D78
    LXI B, 0100h                ; 0x3D79
    DAD B                       ; 0x3D7C
    XCHG                        ; 0x3D7D
    PUSH H                      ; 0x3D7E
    LHLD var_music_work_ptr     ; 0x3D7F
    INX H                       ; 0x3D82
    INX H                       ; 0x3D83
    MOV M, E                    ; 0x3D84
    POP H                       ; 0x3D85
    XCHG                        ; 0x3D86
    XCHG                        ; 0x3D87
    PUSH H                      ; 0x3D88
    LHLD var_music_work_ptr     ; 0x3D89
    INX H                       ; 0x3D8C
    INX H                       ; 0x3D8D
    INX H                       ; 0x3D8E
    MOV M, D                    ; 0x3D8F
    POP H                       ; 0x3D90
    XCHG                        ; 0x3D91
    DAD B                       ; 0x3D92
    XCHG                        ; 0x3D93
    PUSH H                      ; 0x3D94
    LHLD var_music_work_ptr     ; 0x3D95
    INX H                       ; 0x3D98
    INX H                       ; 0x3D99
    INX H                       ; 0x3D9A
    INX H                       ; 0x3D9B
    MOV M, E                    ; 0x3D9C
    POP H                       ; 0x3D9D
    XCHG                        ; 0x3D9E
    XCHG                        ; 0x3D9F
    PUSH H                      ; 0x3DA0
    LHLD var_music_work_ptr     ; 0x3DA1
    INX H                       ; 0x3DA4
    INX H                       ; 0x3DA5
    INX H                       ; 0x3DA6
    INX H                       ; 0x3DA7
    INX H                       ; 0x3DA8
    MOV M, D                    ; 0x3DA9
    POP H                       ; 0x3DAA
    XCHG                        ; 0x3DAB
    LXI H, 3DCAh                ; 0x3DAC
    LXI D, 03F8h                ; 0x3DAF
    LXI B, 0003h                ; 0x3DB2
    JMP 3DC5h                   ; 0x3DB5
