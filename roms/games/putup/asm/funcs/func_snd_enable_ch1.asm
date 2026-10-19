; Функция: func_snd_enable_ch1
; Адрес: 0x029E
; Размер: 14 байт
; Описание: Включение канала 1: E = маска (проверяется bit1); A=E; STA var_snd_state;
;           ANI 02h; если 0 -> JZ func_snd_out_ch1; иначе код управления VI53
;           0x76 в порт 08h (гейт ch1).

func_snd_enable_ch1:
    MOV A, E                    ; 0x029E
    STA var_snd_state           ; 0x029F
    ANI 02h                     ; 0x02A2
    JZ func_snd_out_ch1         ; 0x02A4
    MVI A, 76h                  ; 0x02A7
    OUT 08h                     ; 0x02A9
    RET                         ; 0x02AB
