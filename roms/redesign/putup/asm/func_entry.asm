; Функция: func_entry
; Адрес: 0x0100
; Размер: 4 байта
; Описание: Точка входа ROM (mapping entry point). DI; JMP func_main_init (0x0B57).

func_entry:
    DI                          ; 0x0100
    JMP func_main_init          ; 0x0101
