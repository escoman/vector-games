; Функция: func_render_all
; Адрес: 0x1BF0
; Размер: ~40 байт
; Описание: Единый покадровый рендер (Step 0). Делает ОДИН чанк скана огня —
;           128 ячеек из data_text_buffer начиная с var_scan_ptr. Полный оборот
;           скана = 768/128 = 6 кадров -> 2 оборота за 12-кадровый тик, т.е.
;           частота 2 flip/тик сохранена (как в исходном inline-скане
;           func_game_update: 2 вызова game_update * полный скан = 2 оборота).
;           После последней ячейки курсор возвращается к началу буфера (wrap).
;           Тело побайтово совпадает со старым loc_0DBE..loc_0DD6, изменены
;           только: счётчик B (0x300->0x80) и хранение курсора в var_scan_ptr.
; Прозрачность: трогает A/B/C/D/H/L/F. Вызывается из lbl_main_game_loop над
;              PUSH B, поэтому сохранение не нужно. В func_draw_char_at_hl
;              PUSH/POP H уже встроен — HL остаётся корректным между ячейками.

func_render_all:
    LHLD var_scan_ptr           ; HL = курсор на начало кадра
    MVI B, 080h                 ; 128 ячеек за проход
loc_ra_cell:
    MOV A, M                    ; A = код клетки
    CPI 75h                     ; светлый огонь -> тёмный
    JZ loc_ra_to_dark
    CPI 0FEh                    ; тёмный огонь -> светлый
    JNZ loc_ra_next
    MVI A, 75h
    CALL func_draw_char_at_hl
    JMP loc_ra_next
loc_ra_to_dark:
    MVI A, 0FEh
    CALL func_draw_char_at_hl
loc_ra_next:
    INX H                       ; следующая клетка
    DCR B
    JNZ loc_ra_cell
    SHLD var_scan_ptr           ; сохранить курсор
    ; wrap по data_text_buffer+0x300
    LXI D, data_text_buffer+300h
    MOV A, L
    SUB E
    MOV A, H
    SBB D
    JNZ loc_ra_done
    LXI H, data_text_buffer
    SHLD var_scan_ptr
loc_ra_done:
    RET
