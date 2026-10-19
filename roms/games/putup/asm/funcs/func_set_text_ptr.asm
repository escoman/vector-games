; Функция: func_set_text_ptr
; Адрес: 0x014F
; Размер: 4 байта
; Описание: Установить курсор текста: SHLD var_text_ptr; RET. Параметр: HL = адрес.

func_set_text_ptr:
    SHLD var_text_ptr           ; 0x014F
    RET                         ; 0x0152
