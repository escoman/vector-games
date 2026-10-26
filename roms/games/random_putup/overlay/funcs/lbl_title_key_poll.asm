; Метка: lbl_title_key_poll
; Адрес: 0x0C65
; Размер: 62 байта (0x0C65-0x0CA2)
; Описание: Цикл ожидания нажатия пробела на заставке (Stage 6 step 2).
;           LXI B,01B0h (таймаут=432; компенсация подорожавшей итерации —
;           в цикле дёргается func_prng, см. комментарий у метки; оригинал
;           был 0C00h=3072 при шаге огня ~20 кадров). Цикл опроса loc_0C68:
;           CALL func_prng (энтропия аттракта); XRA A; PUSH B;
;           CALL func_check_start_key; POP B; ORA A; JNZ loc_0C9D (пробел/SHIFT
;           нажат). Иначе DCX B; MOV A,C; ORA B; JNZ loc_0C68 (отсчёт таймаута).
;           По таймауту: анимация ОГНЯ заставки — проход по 32 символам ряда
;           огня, переключение 'u'(75h)<->0FEh через func_draw_char_at_hl, затем
;           JMP lbl_title_key_poll. RANDOM PUTUP: нижняя лента тайлов (огонь+замки)
;           в Stage-3 опущена на 2 знакоместа вниз (ряд 12->14, зазор под 10-
;           рядным логотипом), поэтому цель анимации сдвинута с +180h на +1C0h
;           (0x75 теперь на знакоряду 14), иначе цикл сканировал бы пустой ряд.
;           При нажатии (loc_0C9D): CALL func_music_start_track; JMP func_level_loader.
; RANDOM PUTUP (Stage 2): перед входом в игру (после старта музыки) вызываем
;   func_gen_level — он заполняет ПЕРИМЕТР всех 15 карт стеной и прописывает
;   описатели уровней. Массивы data_level_maps/data_level_params лежат в ОЗУ
;   (образ грузится на 0x0100), поэтому перезаписываемы; func_level_loader не
;   тронут и читает их как обычно.

lbl_title_key_poll:
    ; Таймаут 0C00h (3072) компенсирован до 01B0h (432): с добавлением
    ; CALL func_prng в опрос (энтропия ГПСЧ от тайминга игрока) итерация
    ; подорожала с ~232 T до ~1886 T, и шаг огня/бегущей строки (один шаг
    ; на полный отсчёт) замедлился в ~7 раз. Замер на эмуляторе (кадры TV
    ; между попаданиями на границу такта): без PRNG 20.2 кадра, с PRNG на
    ; 3072 итерациях — 144.6; 432×(144.6/3072) ≈ 20.3 — скорость анимации
    ; восстановлена, частота опроса клавиш с запасом (>1 к 20-мс кадру).
    LXI B, 01B0h                ; 0x0C65
loc_0C68:
    CALL func_prng              ; энтропия аттракта: крутить состояние ГПСЧ на каждой
    ;                             ;   итерации опроса — момент нажатия старта игроком
    ;                             ;   определяет, до какого значения докрутится сид
    XRA A                       ; 0x0C68
    PUSH B                      ; 0x0C69
    CALL func_check_start_key   ; 0x0C6A
    POP B                       ; 0x0C6D
    ORA A                       ; 0x0C6E
    JNZ loc_0C9D                ; 0x0C6F
    DCX B                       ; 0x0C72
    MOV A, C                    ; 0x0C73
    ORA B                       ; 0x0C74
    JNZ loc_0C68                ; 0x0C75
    LXI H, data_text_buffer+01C0h                ; 0x0C78  RANDOM PUTUP: ряд ОГНЯ = знакоряд 14 (0x75 на кол.4..11 и 20..27); в оригинале был ряд 12 (+180h), лента опущена на 2 ряда
    MVI B, 20h                  ; 0x0C7B
loc_0C7D:
    MOV A, M                    ; 0x0C7D
    CPI 75h                     ; 0x0C7E
    JZ loc_0C90                 ; 0x0C80
    CPI 0FEh                    ; 0x0C83
    JNZ loc_0C95                ; 0x0C85
    MVI A, 75h                  ; 0x0C88
    CALL func_draw_char_at_hl   ; 0x0C8A
    JMP loc_0C95                ; 0x0C8D
loc_0C90:
    MVI A, 0FEh                 ; 0x0C90
    CALL func_draw_char_at_hl   ; 0x0C92
loc_0C95:
    INX H                       ; 0x0C95
    DCR B                       ; 0x0C96
    JNZ loc_0C7D                ; 0x0C97
    JMP lbl_title_key_poll      ; 0x0C9A
loc_0C9D:
    CALL func_music_start_track ; 0x0C9D
    CALL func_gen_level         ; RANDOM PUTUP: заполнить карты/описатели на полётке
    JMP func_level_loader       ; 0x0CA0
