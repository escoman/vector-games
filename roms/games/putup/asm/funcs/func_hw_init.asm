; Функция: func_hw_init
; Адрес: 0x0383
; Размер: 33 байт
; Описание: Аппаратная инициализация. XRA A; OUT 10h; var_scroll = 0;
;           var_screen_mode = 0E0h. Устанавливает векторы прерываний:
;           data_int_vector_rst7@0x0038 = 0C3h (JMP) и data_int_vector_reset@
;           0x0000 = 0C3h; LXI H,func_vblank_isr; SHLD 0039h (адрес RST7);
;           LXI H,func_main_init; SHLD 0001h (адрес сброса); EI; RET.
;           Примечание: 0x0039/0x0001 — старшие байты векторов (внутри объектов
;           data_int_vector_*, не их начало), поэтому оставлены как hex.

func_hw_init:
    XRA A                       ; 0x0383
    OUT 10h                     ; 0x0384
    STA var_scroll              ; 0x0386
    MVI A, 0E0h                 ; 0x0389
    STA var_screen_mode         ; 0x038B
    MVI A, 0C3h                 ; 0x038E
    STA data_int_vector_rst7    ; 0x0390
    STA data_int_vector_reset   ; 0x0393
    LXI H, func_vblank_isr      ; 0x0396
    SHLD 0039h                  ; 0x0399
    LXI H, func_main_init       ; 0x039C
    SHLD 0001h                  ; 0x039F
    EI                          ; 0x03A2
    RET                         ; 0x03A3
