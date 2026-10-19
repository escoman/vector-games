; Функция: func_snd_gate_ch0
; Адрес: 0x02D2
; Размер: 24 байт
; Описание: Гейт канала 0 (операция 8 диспетчера): если E bit4 установлен ->
;           JMP 026Ah (эпилог); иначе берёт E&0Fh, сравнивает с 03h: A=0Fh, и
;           если A<03h (JC) пропускает A=00h. CALL 0294h (вход в середину
;           func_snd_enable_ch0); JMP 026Ah (эпилог диспетчера).

func_snd_gate_ch0:
    MOV A, E                    ; 0x02D2
    ANI 10h                     ; 0x02D3
    JNZ 026Ah                   ; 0x02D5 — эпилог диспетчера (не объект RDB)
    MOV A, E                    ; 0x02D8
    ANI 0Fh                     ; 0x02D9
    CPI 03h                     ; 0x02DB
    MVI A, 0Fh                  ; 0x02DD
    JC loc_02E4                 ; 0x02DF
    MVI A, 00h                  ; 0x02E2
loc_02E4:
    CALL 0294h                  ; 0x02E4 — вход в середину func_snd_enable_ch0
    JMP 026Ah                   ; 0x02E7 — эпилог диспетчера
