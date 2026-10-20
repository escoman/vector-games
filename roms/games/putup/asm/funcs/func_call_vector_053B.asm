; Функция: func_call_vector_053B
; Адрес: 0x053B
; Размер: 7 байт
; Описание: Трамплин RAM-вектора: два CALL на обработчик в low-RAM (вектор 0x0015) и RET. Вход в отрисовку объекта через PCHL/RAM-вектор, прямых CALL нет.

func_call_vector_053B:
    CALL  0015h          ; 0x053B
    CALL  0015h          ; 0x053E
    RET          ; 0x0541
