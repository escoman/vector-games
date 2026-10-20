; Функция: func_snd_dispatch_nops
; Адрес: 0x025B
; Размер: 15 байт
; Описание: Холостые позиции диспетчера func_sound_op (операции VI53 без действия)
;           и точка вызова переключателя. [6]@0x025B, [11]@0x025E, [12]@0x0261,
;           [13]@0x0264 — JMP func_snd_op_epilogue (nicего не делают, возврат).
;           [7]@0x0267 — CALL func_snd_toggle, затем fall-through в эпилог.

snd_dispatch_nop:               ; dispatch [6] @0x025B
    JMP func_snd_op_epilogue    ; 0x025B
snd_dispatch_nop11:             ; dispatch [11] @0x025E
    JMP func_snd_op_epilogue    ; 0x025E
snd_dispatch_nop12:             ; dispatch [12] @0x0261
    JMP func_snd_op_epilogue    ; 0x0261
snd_dispatch_nop13:             ; dispatch [13] @0x0264
    JMP func_snd_op_epilogue    ; 0x0264
snd_dispatch_toggle:            ; dispatch [7] @0x0267
    CALL func_snd_toggle        ; 0x0267
