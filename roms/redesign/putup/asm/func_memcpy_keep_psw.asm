; Функция: func_memcpy_keep_psw
; Адрес: 0x3DB8
; Размер: 13 байт
; Описание: Копирует BC байт из (HL) в (DE), сохраняя регистр A (PUSH/POP PSW).
;           Классический цикл LDIR-подобного копирования: MOV A,M / STAX D /
;           INX H / INX D / DCX B / JNZ. Используется для установки 3-байтного
;           вектора "CALL func_music_tick" в RAM 03F8h и для func_music_start_track.

func_memcpy_keep_psw:
    PUSH PSW                    ; 0x3DB8
loc_3DB9:
    MOV A, M                    ; 0x3DB9
    STAX D                      ; 0x3DBA
    INX H                       ; 0x3DBB
    INX D                       ; 0x3DBC
    DCX B                       ; 0x3DBD
    MOV A, B                    ; 0x3DBE
    ORA C                       ; 0x3DBF
    JNZ loc_3DB9                ; 0x3DC0
    POP PSW                     ; 0x3DC3
    RET                         ; 0x3DC4
