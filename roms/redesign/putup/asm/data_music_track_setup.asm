; Данные: data_music_track_setup
; Адрес: 0x3DE8
; Размер: 3 байта
; Назначение: 3 байта установки музыкального трека. func_music_start_track (0x3DCD)
;             копирует их (func_memcpy_keep_psw) в RAM по адресу 0x03F8 перед
;             программированием VI53. В данном ROM все три байта = 0.

data_music_track_setup:
    DEFB 00h, 00h, 00h      ; 0x3DE8
