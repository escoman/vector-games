; Функция: func_clear_textbuf
; Адрес: 0x1BE5
; Размер: 21 байт
; Описание: Очистка текстового буфера. Устанавливает текстовый указатель на
;           data_ram_buffer_5000 (func_set_text_ptr) и заполняет 0x0400 (1024)
;           байт пробелами (0x20) через func_print_char_at_ptr в цикле loc_1BEE.

func_clear_textbuf:
    LXI H, data_ram_buffer_5000 ; 0x1BE5
    LXI B, 0400h                ; 0x1BE8
    CALL func_set_text_ptr      ; 0x1BEB
loc_1BEE:
    MVI A, 20h                  ; 0x1BEE
    CALL func_print_char_at_ptr ; 0x1BF0
    DCX B                       ; 0x1BF3
    MOV A, C                    ; 0x1BF4
    ORA B                       ; 0x1BF5
    JNZ loc_1BEE                ; 0x1BF6
    RET                         ; 0x1BF9
