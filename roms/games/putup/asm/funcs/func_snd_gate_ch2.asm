; Функция: func_snd_gate_ch2
; Адрес: 0x0302
; Размер: 24 байта
; Описание: Гейт канала 2 (операция 10 диспетчера): если E bit4 установлен ->
;           JMP 026Ah (эпилог); иначе E&0Fh сравнивается с 03h (A=0Fh, JC
;           пропускает A=00h). CALL 02B0h (середина func_snd_enable_ch2);
;           JMP 026Ah (эпилог диспетчера).

func_snd_gate_ch2:
    MOV A, E                    ; 0x0302
    ANI 10h                     ; 0x0303
    JNZ func_snd_op_epilogue     ; 0x0305 — эпилог диспетчера
    MOV A, E                    ; 0x0308
    ANI 0Fh                     ; 0x0309
    CPI 03h                     ; 0x030B
    MVI A, 0Fh                  ; 0x030D
    JC loc_0314                 ; 0x030F
    MVI A, 00h                  ; 0x0312
loc_0314:
    CALL func_snd_enable_ch2_gate ; 0x0314 — mid-function вход func_snd_enable_ch2
    JMP func_snd_op_epilogue      ; 0x0317 — эпилог диспетчера
