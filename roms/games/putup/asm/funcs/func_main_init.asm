; Функция: func_main_init
; Адрес: 0x0B57
; Размер: 262 байт кода (оригинал 0x0B57-0x0C64 = 270 Б; −11 Б inline-петли +3 Б
;         CALL func_clear_vram), fall-through в lbl_title_key_poll. Перед меткой
;         layout'ится 16-байтовый блок data_palette (не код).
; Описание: Инициализация программы и вывод заставки. DI; LXI SP,0100h;
;           CALL func_clear_vram (выделена из inline-петли 0x0B5B..0x0B65;
;           очистка VRAM 0x8000-0xFFFF=0); CALL func_hw_init; var_palette_ptr=data_palette+00Fh (метка);
;           var_palette_timer=09h; заполнение data_text_buffer (0x400 байт)=0FFh;
;           CALL func_load_glyph_block УДАЛЁН (Stage-3/4A): глифы запечены в ROM,
;           адрес блока задаёт компоновщик (data_glyph_block, свободная конкатенация);
;           копирование спрайтов data_sprites_2F61 ->
;           data_ram_sprites_7418 (1Ch блоков по 8 байт, источник убывает вниз) —
;           в PUTUP_NEW выведено: одноразовый init-write, читателя адресу 0x7418
;           в ROM нет, а источник (хвост data_gfx_2761) обнулён как мёртвый пакет;
;           инициализация игровых переменных 0x08EB-0x08FB; CALL func_music_init;
;           var_score=0, var_level=0, var_page_flip=1, var_bonus_counter,
;           var_bonus_threshold=07D0h; CALL func_clear_textbuf; рисунок заставки
;           тайлами data_tile_graphics; строки str_title_logo, str_push_space,
;           str_msx_magazine, str_hi + счёт, str_credits_koi8. Далее без возврата
;           переходит в lbl_title_key_poll (ожидание пробела).
;
; data_palette (16 слотов BBGGGRRR) перенесена из хвоста func_render_glyph —
;   это стартовые данные HR-инициализации, они логически принадлежат main_init
;   (LXI H, data_palette+00Fh; SHLD var_palette_ptr), а не рендереру глифов.
;   В Execution flow безопасно ставить перед меткой func_main_init: сюда входят
;   только через JMP func_main_init (func_entry) и LXI H,func_main_init; SHLD 0001h
;   (reset vector в func_hw_init) — flow-through никогда не доходит до данных.
;   func_vblank_isr читает палитру через var_palette_ptr (де-факто адрес метки).
;   ОСОЗНАННОЕ отхождение от оригинала (2 стадии):
;     Фаза 3: чанк E000 (вес бита 1) инвертирован во всех глифах -> индекс I->I^1;
;       компенсация — перестановка соседних пар слотов PAL'[j]=PAL[j^1].
;     Стадия 1: цвет текста перемаркирован 15<->8 (текст пишется только в
;       плоскость 0x8000); компенсация — свап слотов 8 и 15.
;   Итоговая РАСКРАШЕННАЯ картинка побайтово та же (гейт tools/compare_color.py).
data_palette:
    DEFB 00h, 00h, 7Bh, 30h, 0DAh, 0C9h, 0F2h, 0Dh   ; slot0..7 = old 1,0,3,2,5,4,7,6
    DEFB 0ADh, 0Fh, 3Fh, 37h, 0DEh, 21h, 0FFh, 0A7h   ; slot8..15; свап 8<->15: slot8=серый текста

func_main_init:
    DI                          ; 0x0B57
    LXI SP, 0100h               ; 0x0B58
    CALL func_clear_vram        ; 0x0B5B..0x0B65  (была inline-петля очистки VRAM)
    CALL func_hw_init           ; 0x0B66
    LXI H, data_palette+00Fh                 ; 0x0B69
    SHLD var_palette_ptr        ; 0x0B6C
    MVI A, 09h                  ; 0x0B6F
    STA var_palette_timer       ; 0x0B71
    MVI A, 0FFh                 ; (Фаза 4) мигание выхода выключено до появления
    STA var_exit_phase
    XRA A                       ; raster-sync выключен на заставке (ch1 остаётся за музыкой)
    STA var_raster_flag
    LXI H, data_text_buffer ; 0x0B74
    LXI B, 0400h                ; 0x0B77
loc_0B7A:
    MVI M, 0FFh                 ; 0x0B7A
    INX H                       ; 0x0B7C
    DCX B                       ; 0x0B7D
    MOV A, B                    ; 0x0B7E
    ORA C                       ; 0x0B7F
    JNZ loc_0B7A                ; 0x0B80
    ; Stage-4A (шлак удалён): были 3 NOP (заглушка CALL func_load_glyph_block —
    ; глифы запечены в ROM) и мёртвый спрайт-копир (0x0B86..0x0BA7, 34 Б): reader
    ; адреса 0x7418 в ROM отсутствует, источник (хвост data_gfx_2761) обнулён.
    LXI H, 07D0h
    SHLD var_score_delta                   ; 0x0BAB
    MVI A, 01h                  ; 0x0BAE
    STA var_scr_08EE                    ; 0x0BB0
    MVI A, 03h                  ; 0x0BB3
    STA var_scr_08EF                    ; 0x0BB5
    MVI A, 05h                  ; 0x0BB8
    STA var_scr_08F0                    ; 0x0BBA
    MVI A, 08h                  ; 0x0BBD
    STA var_scr_08F1                    ; 0x0BBF
loc_0BC2:
    CALL func_music_init        ; 0x0BC2
    XRA A                       ; 0x0BC5
    LXI H, 0000h                ; 0x0BC6
    SHLD var_score              ; 0x0BC9
    STA var_level               ; 0x0BCC
    STA var_egg_hist_prev                    ; 0x0BCF
    INR A                       ; 0x0BD2
    STA var_egg_hist_cur                    ; 0x0BD3
    STA var_page_flip           ; 0x0BD6
    INR A                       ; 0x0BD9
    STA var_page_flip_hi                    ; 0x0BDA
    INR A                       ; 0x0BDD
    STA var_bonus_counter       ; 0x0BDE
    LXI H, 07D0h                ; 0x0BE1
    SHLD var_bonus_threshold    ; 0x0BE4
    CALL func_clear_textbuf     ; 0x0BE7
    LXI H, str_credits_koi8+061h                 ; 0x0BEA
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
    LXI H, data_text_buffer+00A0h                ; 0x0C18
    CALL func_set_text_ptr      ; 0x0C1B
    LXI H, str_title_logo       ; 0x0C1E
    CALL func_print_string      ; 0x0C21
    LXI H, data_text_buffer+0229h                ; 0x0C24
    CALL func_set_text_ptr      ; 0x0C27
    LXI H, str_push_space       ; 0x0C2A
    CALL func_print_string      ; 0x0C2D
    LXI H, data_text_buffer+0287h                ; 0x0C30
    CALL func_set_text_ptr      ; 0x0C33
    LXI H, str_msx_magazine     ; 0x0C36
    CALL func_print_string      ; 0x0C39
    LXI H, data_text_buffer+006Bh                ; 0x0C3C
    CALL func_set_text_ptr      ; 0x0C3F
    LXI H, str_hi               ; 0x0C42
    CALL func_print_string      ; 0x0C45
    LXI H, data_text_buffer+006Eh                ; 0x0C48
    CALL func_set_text_ptr      ; 0x0C4B
    LXI H, var_score_delta                 ; 0x0C4E
    CALL func_print_uint16      ; 0x0C51
    MVI A, 30h                  ; 0x0C54
    CALL func_print_char_at_ptr ; 0x0C56
    LXI H, data_text_buffer+02E0h                ; 0x0C59
    CALL func_set_text_ptr      ; 0x0C5C
    LXI H, str_credits_koi8     ; 0x0C5F
    CALL func_print_string      ; 0x0C62
    ; fall-through в lbl_title_key_poll (0x0C65)
