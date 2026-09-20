; Функция: func_restore_cursor
; Адрес: 0x01AE
; Размер: 14 байт
; Описание: Восстановить курсор текста: DE = слово из 0x08FE/0x08FF (сохранённые
;           координаты), CALL func_coords_to_textbuf (координаты -> адрес в HL),
;           затем JMP func_set_text_ptr (SHLD var_text_ptr).

func_restore_cursor:
    LDA 08FEh                   ; 0x01AE — saved coords lo (не объект RDB)
    MOV D, A                    ; 0x01B1
    LDA 08FFh                   ; 0x01B2 — saved coords hi (не объект RDB)
    MOV E, A                    ; 0x01B5
    CALL func_coords_to_textbuf ; 0x01B6
    JMP func_set_text_ptr       ; 0x01B9
