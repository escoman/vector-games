; Функция: func_snd_op_epilogue
; Адрес: 0x026A
; Размер: 4 байта
; Описание: Общий эпилог диспетчера func_sound_op — восстановление контекста
;           (POP PSW/DE/HL) и возврат. Цель JMP во всех обработчиках операций;
;           dispatch [14]/[15]@0x026A указывают прямо на POP PSW. Метка
;           func_snd_op_epilogue_ret (0x026D, RET) — цель data_snd_toggle_table[0]
;           («нет каналов»: сразу возврат без действия).

func_snd_op_epilogue:           ; 0x026A — POP PSW/DE/HL
    POP PSW                     ; 0x026A
    POP D                       ; 0x026B
    POP H                       ; 0x026C
func_snd_op_epilogue_ret:       ; 0x026D — RET (toggle_table[0])
    RET                         ; 0x026D
