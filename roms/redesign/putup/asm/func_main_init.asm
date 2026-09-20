; Функция: func_main_init
; Адрес: 0x0B57
; Размер: 270 байт (0x0B57-0x0C64), fall-through в lbl_title_key_poll
; Описание: Инициализация программы и вывод заставки. DI; LXI SP,0100h;
;           очистка VRAM 0x8000-0xFFFF=0; CALL func_hw_init; var_palette_ptr=08B2h;
;           var_palette_timer=09h; заполнение data_ram_buffer_5000 (0x400 байт)=0FFh;
;           CALL func_load_glyph_block; копирование спрайтов data_sprites_2F61 ->
;           data_ram_sprites_7418 (1Ch блоков по 8 байт, источник убывает);
;           инициализация игровых переменных 0x08EB-0x08FB; CALL func_music_init;
;           var_score=0, var_level=0, var_page_flip=1, var_bonus_counter,
;           var_bonus_threshold=07D0h; CALL func_clear_textbuf; рисунок заставки
;           тайлами data_tile_graphics; строки str_title_logo, str_push_space,
;           str_msx_magazine, str_hi + счёт, str_credits_koi8. Далее без возврата
;           переходит в lbl_title_key_poll (ожидание пробела).

func_main_init:
    DI                          ; 0x0B57
    LXI SP, 0100h               ; 0x0B58
    LXI H, 8000h                ; 0x0B5B
loc_0B5E:
    MVI M, 00h                  ; 0x0B5E
    INX H                       ; 0x0B60
    MOV A, H                    ; 0x0B61
    ORA L                       ; 0x0B62
    JNZ loc_0B5E                ; 0x0B63
    CALL func_hw_init           ; 0x0B66
    LXI H, 08B2h                ; 0x0B69
    SHLD var_palette_ptr        ; 0x0B6C
    MVI A, 09h                  ; 0x0B6F
    STA var_palette_timer       ; 0x0B71
    LXI H, data_ram_buffer_5000 ; 0x0B74
    LXI B, 0400h                ; 0x0B77
loc_0B7A:
    MVI M, 0FFh                 ; 0x0B7A
    INX H                       ; 0x0B7C
    DCX B                       ; 0x0B7D
    MOV A, B                    ; 0x0B7E
    ORA C                       ; 0x0B7F
    JNZ loc_0B7A                ; 0x0B80
    CALL func_load_glyph_block  ; 0x0B83
    LXI H, data_ram_sprites_7418 ; 0x0B86
    LXI D, data_sprites_2F61    ; 0x0B89
    MVI B, 1Ch                  ; 0x0B8C
loc_0B8E:
    PUSH B                      ; 0x0B8E
    MVI C, 08h                  ; 0x0B8F
loc_0B91:
    LDAX D                      ; 0x0B91
    MOV M, A                    ; 0x0B92
    INX H                       ; 0x0B93
    DCX D                       ; 0x0B94
    DCR C                       ; 0x0B95
    JNZ loc_0B91                ; 0x0B96
    LXI B, 0010h                ; 0x0B99
    XCHG                        ; 0x0B9C
    DAD B                       ; 0x0B9D
    XCHG                        ; 0x0B9E
    LXI B, 0018h                ; 0x0B9F
    DAD B                       ; 0x0BA2
    POP B                       ; 0x0BA3
    DCR B                       ; 0x0BA4
    JNZ loc_0B8E                ; 0x0BA5
    LXI H, 07D0h                ; 0x0BA8
    SHLD 08EBh                  ; 0x0BAB
    MVI A, 01h                  ; 0x0BAE
    STA 08EEh                   ; 0x0BB0
    MVI A, 03h                  ; 0x0BB3
    STA 08EFh                   ; 0x0BB5
    MVI A, 05h                  ; 0x0BB8
    STA 08F0h                   ; 0x0BBA
    MVI A, 08h                  ; 0x0BBD
    STA 08F1h                   ; 0x0BBF
    CALL func_music_init        ; 0x0BC2
    XRA A                       ; 0x0BC5
    LXI H, 0000h                ; 0x0BC6
    SHLD var_score              ; 0x0BC9
    STA var_level               ; 0x0BCC
    STA 08F7h                   ; 0x0BCF
    INR A                       ; 0x0BD2
    STA 08F8h                   ; 0x0BD3
    STA var_page_flip           ; 0x0BD6
    INR A                       ; 0x0BD9
    STA 08FAh                   ; 0x0BDA
    INR A                       ; 0x0BDD
    STA var_bonus_counter       ; 0x0BDE
    LXI H, 07D0h                ; 0x0BE1
    SHLD var_bonus_threshold    ; 0x0BE4
    CALL func_clear_textbuf     ; 0x0BE7
    LXI H, 0986h                ; 0x0BEA
    LXI D, 0000h                ; 0x0BED
    LXI B, 0080h                ; 0x0BF0
loc_0BF3:
    PUSH B                      ; 0x0BF3
    PUSH H                      ; 0x0BF4
    MOV A, M                    ; 0x0BF5
    ADD A                       ; 0x0BF6
    ADD A                       ; 0x0BF7
    LXI H, data_tile_graphics   ; 0x0BF8
    CALL func_hl_add_a          ; 0x0BFB
    PUSH D                      ; 0x0BFE
    CALL func_draw_tile_to_buf  ; 0x0BFF
    POP D                       ; 0x0C02
    INR D                       ; 0x0C03
    INR D                       ; 0x0C04
    MOV A, D                    ; 0x0C05
    CPI 20h                     ; 0x0C06
    JNZ loc_0C0F                ; 0x0C08
    MVI D, 00h                  ; 0x0C0B
    INR E                       ; 0x0C0D
    INR E                       ; 0x0C0E
loc_0C0F:
    POP H                       ; 0x0C0F
    INX H                       ; 0x0C10
    POP B                       ; 0x0C11
    DCX B                       ; 0x0C12
    MOV A, B                    ; 0x0C13
    ORA C                       ; 0x0C14
    JNZ loc_0BF3                ; 0x0C15
    LXI H, 50A0h                ; 0x0C18
    CALL func_set_text_ptr      ; 0x0C1B
    LXI H, str_title_logo       ; 0x0C1E
    CALL func_print_string      ; 0x0C21
    LXI H, 5229h                ; 0x0C24
    CALL func_set_text_ptr      ; 0x0C27
    LXI H, str_push_space       ; 0x0C2A
    CALL func_print_string      ; 0x0C2D
    LXI H, 5287h                ; 0x0C30
    CALL func_set_text_ptr      ; 0x0C33
    LXI H, str_msx_magazine     ; 0x0C36
    CALL func_print_string      ; 0x0C39
    LXI H, 506Bh                ; 0x0C3C
    CALL func_set_text_ptr      ; 0x0C3F
    LXI H, str_hi               ; 0x0C42
    CALL func_print_string      ; 0x0C45
    LXI H, 506Eh                ; 0x0C48
    CALL func_set_text_ptr      ; 0x0C4B
    LXI H, 08EBh                ; 0x0C4E
    CALL func_print_uint16      ; 0x0C51
    MVI A, 30h                  ; 0x0C54
    CALL func_print_char_at_ptr ; 0x0C56
    LXI H, 52E0h                ; 0x0C59
    CALL func_set_text_ptr      ; 0x0C5C
    LXI H, str_credits_koi8     ; 0x0C5F
    CALL func_print_string      ; 0x0C62
    ; fall-through в lbl_title_key_poll (0x0C65)
