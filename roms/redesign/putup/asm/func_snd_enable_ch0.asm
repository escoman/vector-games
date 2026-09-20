; Функция: func_snd_enable_ch0
; Адрес: 0x0290
; Размер: 14 байт
; Описание: Включение канала 0: E = маска (проверяется bit0); A=E; STA var_snd_state;
;           ANI 01h; если 0 -> JZ func_snd_out_ch0 (вывести период); иначе запись
;           кода управления VI53 0x36 в порт 08h (гейт ch0).

func_snd_enable_ch0:
    MOV A, E                    ; 0x0290
    STA var_snd_state           ; 0x0291
    ANI 01h                     ; 0x0294
    JZ func_snd_out_ch0         ; 0x0296
    MVI A, 36h                  ; 0x0299
    OUT 08h                     ; 0x029B
    RET                         ; 0x029D
