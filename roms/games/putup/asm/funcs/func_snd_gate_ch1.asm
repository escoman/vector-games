; Функция: func_snd_gate_ch1
; Адрес: 0x02EA
; Размер: 24 байта
; Описание: Гейт канала 1 (операция 9 диспетчера): если E bit4 установлен ->
;           JMP 026Ah (эпилог); иначе E&0Fh сравнивается с 03h (A=0Fh, JC
;           пропускает A=00h). CALL 02A2h (середина func_snd_enable_ch1);
;           JMP 026Ah (эпилог диспетчера).

func_snd_gate_ch1:
    MOV A, E                    ; 0x02EA
    ANI 10h                     ; 0x02EB
    JNZ 026Ah                   ; 0x02ED — эпилог диспетчера
    MOV A, E                    ; 0x02F0
    ANI 0Fh                     ; 0x02F1
    CPI 03h                     ; 0x02F3
    MVI A, 0Fh                  ; 0x02F5
    JC loc_02FC                 ; 0x02F7
    MVI A, 00h                  ; 0x02FA
loc_02FC:
    CALL 02A2h                  ; 0x02FC — вход в середину func_snd_enable_ch1
    JMP 026Ah                   ; 0x02FF — эпилог диспетчера
