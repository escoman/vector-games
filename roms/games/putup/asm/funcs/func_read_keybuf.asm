; Функция: func_read_keybuf
; Адрес: 0x0197
; Размер: 10 байт
; Описание: Чтение буфера клавиатуры: LXI H, data_kbd_matrix; CALL func_hl_add_a;
;           MOV A,M — возвращает байт строки матрицы по индексу A. Сохраняет HL.

func_read_keybuf:
    PUSH H                      ; 0x0197
    LXI H, data_kbd_matrix      ; 0x0198
    CALL func_hl_add_a          ; 0x019B
    MOV A, M                    ; 0x019E
    POP H                       ; 0x019F
    RET                         ; 0x01A0
