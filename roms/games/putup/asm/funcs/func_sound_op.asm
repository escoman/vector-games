; Функция: func_sound_op
; Адрес: 0x01BC
; Размер: 17 байт
; Описание: 16-позиционный диспетчер звуковых операций (таблица переходов PCHL
;           data_snd_dispatch_table @0x01CD). Параметры: A = индекс операции
;           (0..15, маскируется ANI 0Fh), E = значение. Операции: 0/1 = период
;           ch0 lo/hi + play (порт 0Bh); 2/3 = ch1 (0Ah); 4/5 = ch2 (09h);
;           6 = nop; 7 = toggle состояния через data_snd_toggle_table @0x0280;
;           8/9/10 = вкл/выкл ch0/ch1/ch2; 11-15 = nop. Управляет 3-канальным
;           генератором KR580VI53. Примечание: 0x01C2 — точка повторного входа
;           диспетчера (используется func_snd_toggle через JMP 01C2h).

func_sound_op:
    PUSH H                      ; 0x01BC
    PUSH D                      ; 0x01BD
    PUSH PSW                    ; 0x01BE
    LXI H, data_snd_dispatch_table ; 0x01BF
    ANI 0Fh                     ; 0x01C2 — точка повторного входа диспетчера
    ADD A                       ; 0x01C4
    CALL func_hl_add_a          ; 0x01C5
    MOV D, M                    ; 0x01C8
    INX H                       ; 0x01C9
    MOV H, M                    ; 0x01CA
    MOV L, D                    ; 0x01CB
    PCHL                        ; 0x01CC
