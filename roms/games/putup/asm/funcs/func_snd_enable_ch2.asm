; Функция: func_snd_enable_ch2
; Адрес: 0x02AC
; Размер: 14 байт
; Описание: Включение канала 2: E = маска (проверяется bit2); A=E; STA var_snd_state;
;           ANI 04h; если 0 -> JZ func_snd_out_ch2; иначе код управления VI53
;           0xB6 в порт 08h (гейт ch2).

func_snd_enable_ch2:
    MOV A, E                    ; 0x02AC
    STA var_snd_state           ; 0x02AD
    ANI 04h                     ; 0x02B0
    JZ func_snd_out_ch2         ; 0x02B2
    MVI A, 0B6h                 ; 0x02B5
    OUT 08h                     ; 0x02B7
    RET                         ; 0x02B9
