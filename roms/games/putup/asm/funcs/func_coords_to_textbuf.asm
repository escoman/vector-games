; Функция: func_coords_to_textbuf
; Адрес: 0x1BD4
; Размер: 17 байт
; Описание: Преобразование координат клетки в адрес текстового буфера.
;           Вход: D = колонка, E = строка. Выход: HL = 0x5000 + row*32 + col.
;           row*32 вычисляется пятью DAD H (сдвиг на 5 бит), затем прибавляется
;           колонка и базовый адрес data_ram_buffer_5000 (LXI D,5000h; DAD D).

func_coords_to_textbuf:
    MOV L, E                    ; 0x1BD4
    MVI H, 00h                  ; 0x1BD5
    DAD H                       ; 0x1BD7
    DAD H                       ; 0x1BD8
    DAD H                       ; 0x1BD9
    DAD H                       ; 0x1BDA
    DAD H                       ; 0x1BDB
    MOV E, D                    ; 0x1BDC
    MVI D, 00h                  ; 0x1BDD
    DAD D                       ; 0x1BDF
    LXI D, data_ram_buffer_5000 ; 0x1BE0
    DAD D                       ; 0x1BE3
    RET                         ; 0x1BE4
