; Функция: func_music_start_track
; Адрес: 0x3DCD
; Размер: 26 байт
; Описание: Запускает трек: копирует 3 байта из data_music_track_setup (3DE8h)
;           в RAM 03F8h через func_memcpy_keep_psw (с запретом/разрешением
;           прерываний DI/EI), затем выдаёт три значения в порт 08h
;           (аппаратный звук Vector-06C: 36h/76h/B6h) для инициализации
;           генераторов шума/тона.

func_music_start_track:
    LXI H, data_music_track_setup   ; 0x3DCD
    LXI D, 03F8h                    ; 0x3DD0
    LXI B, 0003h                    ; 0x3DD3
    DI                              ; 0x3DD6
    CALL func_memcpy_keep_psw       ; 0x3DD7
    EI                              ; 0x3DDA
    MVI A, 36h                      ; 0x3DDB
    OUT 08h                         ; 0x3DDD
    MVI A, 76h                      ; 0x3DDF
    OUT 08h                         ; 0x3DE1
    MVI A, B6h                      ; 0x3DE3
    OUT 08h                         ; 0x3DE5
    RET                             ; 0x3DE7
