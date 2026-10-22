; Функция: func_build_hero_shift_cache
; Адрес: 0x45E0
; Размер: ~180 байт (генератор + локальный резолвинг глифа)
; Описание: ОДНОРАЗОВО при инициализации заполняет RAM-кэш data_hero_shift_cache
;           (Step 2b: горизонтальный easing героя). Для каждого тайла-героя
;          records[0..7] строит широкий композит 3 колонки x 2 строки = 6 фрагментов
;           (обычный raw-глиф: П3 +0, П2 +8, П1 +16, П0/маска +24 = 32 байта).
;           Индекс: (tile*6 + row*3 + colpos)*32 (см. var_ram_symbols).
;
;           СМЫСЛ ±4px-сдвига. Бит7 (0x80) = ЛЕВЫЙ пиксель, бит0 (0x01) = ПРАВЫЙ;
;           VRAM-адрес = (0x80+col)*256 + L, кол растёт ВЛЕВО->ВПРАВО. Сдвиг героя
;           на 4px = сдвиг НИББЛОВ с переливом в соседний VRAM-столбец. Для пары
;           исходных глифов (L в col, R в col+1) три выходные колонки окна:
;             frag0 = L>>4                    ; (освободившийся левый nibble)
;             frag1 = ((L AND 0F)<<4) | (R>>4); (полностью перекрыт)
;             frag2 = (R AND 0F)<<4           ; (освободившийся правый nibble)
;           Для ЦВЕТНЫХ плоскостей (П3,П2,П1) освободившийся nibble = 0. Для МАСКИ
;          (П0, plane==3) освободившийся nibble = 1 (сохранить фон): frag0 |=0F0h,
;           frag2 |=00Fh. Реализовано регистрами D=fill0, E=fill2 (0 или F0/0F).
;
;           ВАЖНО: содержимое НЕ зависит от направления (hoff=1/2 дают одинаковые
;           байты) — различается лишь базовая колонка приёмника, которую передаёт
;           func_render_tile_vram_or3. Поэтому направление в кэш НЕ пишется.
;
;           ВРЕМЯ: не горячий путь (инициализация), поэтому допускаются LHLD/SHLD
;           через zero-page указатели (gsc_*, см. var_ram_symbols) без бережливости.
;           Регистры вызывающего прозрачны: PUSH/POP PSW,B,D,H.

func_build_hero_shift_cache:
    PUSH PSW
    PUSH B
    PUSH D
    PUSH H
    MVI A, 00h
    STA gsc_tile
gsc_next_tile:
    LDA gsc_tile
    CPI 08h
    JZ gsc_done                       ; 8 тайлов (0..7) готовы
    ; --- загрузить 4 кода глифов записи тайла: TL,TR,BL,BR ---
    LDA gsc_tile
    ADD A
    ADD A                             ; A = tile*4
    MOV L, A
    MVI H, 00h
    LXI D, data_tile_table_26DE
    DAD D                             ; HL = &record[tile]
    MOV A, M
    STA gsc_TL
    INX H
    MOV A, M
    STA gsc_TR
    INX H
    MOV A, M
    STA gsc_BL
    INX H
    MOV A, M
    STA gsc_BR
    MVI A, 00h
    STA gsc_row
gsc_row_begin:
    LDA gsc_row
    CPI 02h
    JZ gsc_tile_advance               ; обе строки -> следующий тайл
    ; --- резолвинг L/R источника по строке (0=TL/TR, 1=BL/BR) ---
    CPI 00h
    JNZ gsc_row_low
    LDA gsc_TL
    CALL gsc_resolve                  ; HL = адрес raw-записи глифа
    SHLD gsc_pL
    LDA gsc_TR
    CALL gsc_resolve
    SHLD gsc_pR
    JMP gsc_row_dest
gsc_row_low:
    LDA gsc_BL
    CALL gsc_resolve
    SHLD gsc_pL
    LDA gsc_BR
    CALL gsc_resolve
    SHLD gsc_pR
gsc_row_dest:
    ; --- база окна = data_hero_shift_cache + tile*192 + row*96 ---
    LDA gsc_tile
    MOV E, A                          ; E = счётчик итераций (tile)
    MVI D, 00h
    LXI H, 0000h
    MOV A, E
    ORA A
    JZ gsc_mul_done                   ; tile==0 -> HL=0
gsc_mul192:
    MOV A, L
    ADI 0C0h                          ; +192
    MOV L, A
    MOV A, H
    ACI 00h
    MOV H, A
    DCR E
    JNZ gsc_mul192
gsc_mul_done:
    LDA gsc_row
    CPI 00h
    JZ gsc_no_rowadd
    MOV A, L
    ADI 060h                          ; +96 (нижняя строка)
    MOV L, A
    MOV A, H
    ACI 00h
    MOV H, A
gsc_no_rowadd:
    LXI D, data_hero_shift_cache
    DAD D                             ; HL = база окна (frag0)
    SHLD gsc_pD0
    LXI D, 0020h
    DAD D                             ; frag1 = база+32
    SHLD gsc_pD1
    DAD D                             ; frag2 = база+64
    SHLD gsc_pD2
gsc_plane_begin:
    MVI A, 00h
    STA gsc_plane
gsc_plane_loop:
    ; --- заполнить D=fill0, E=fill2 по типу плоскости (3=маска) ---
    LDA gsc_plane
    CPI 03h
    JZ gsc_fill_mask
    MVI D, 00h
    MVI E, 00h
    JMP gsc_byte_init
gsc_fill_mask:
    MVI D, 0F0h                       ; mask: левый nibble frag0 -> 1
    MVI E, 00Fh                       ; mask: правый nibble frag2 -> 1
gsc_byte_init:
    MVI A, 00h
    STA gsc_byte
gsc_byte_loop:
    ; --- прочитать байты источников (pL,pR), оставить lp=C, rp=B ---
    LHLD gsc_pL
    MOV C, M
    INX H
    SHLD gsc_pL
    LHLD gsc_pR
    MOV B, M
    INX H
    SHLD gsc_pR
    ; --- frag0 = (lp>>4) | fill0 ---
    MOV A, C
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh                           ; логический lp>>4 (high nibble в low)
    ORA D
    LHLD gsc_pD0
    MOV M, A
    INX H
    SHLD gsc_pD0
    ; --- frag1 = ((lp AND 0F)<<4) | (rp>>4) ---
    MOV A, C
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC                               ; (lp&0x0F)<<4 (low->high nibble)
    MOV L, A                          ; stash (HL-свободна после SHLD выше)
    MOV A, B
    RRC
    RRC
    RRC
    RRC
    ANI 0Fh                           ; rp>>4
    ORA L
    LHLD gsc_pD1
    MOV M, A
    INX H
    SHLD gsc_pD1
    ; --- frag2 = (rp AND 0F)<<4 | fill2 ---
    MOV A, B
    ANI 0Fh
    RLC
    RLC
    RLC
    RLC
    ORA E
    LHLD gsc_pD2
    MOV M, A
    INX H
    SHLD gsc_pD2
    ; --- следующий байт плоскости (0..7) ---
    LDA gsc_byte
    INR A
    CPI 08h
    JZ gsc_plane_next
    STA gsc_byte
    JMP gsc_byte_loop
gsc_plane_next:
    LDA gsc_plane
    INR A
    CPI 04h
    JZ gsc_row_advance
    STA gsc_plane
    JMP gsc_plane_loop
gsc_row_advance:
    LDA gsc_row
    INR A
    STA gsc_row
    JMP gsc_row_begin
gsc_tile_advance:
    LDA gsc_tile
    INR A
    STA gsc_tile
    JMP gsc_next_tile
gsc_done:
    POP H
    POP D
    POP B
    POP PSW
    RET

; --- gsc_resolve: индекс глифа -> адрес raw-записи --------------------------
; Вход: A = код глифа. Выход: HL = адрес записи (слово data_glyph_ptr_table с
; снятым тегом compactness, бит0 мл. байта). Меняет A,D,E,HL,флаги; BC не трогает.
gsc_resolve:
    PUSH PSW
    ADD A                             ; DE = 2*код (смещение в таблице указателей)
    MOV E, A
    MVI A, 00h
    ADC A
    MOV D, A
    LXI H, data_glyph_ptr_table
    DAD D                             ; HL = &entry
    MOV A, M                          ; мл. байт слова (бит0 = тег compact)
    ANI 0FEh                          ; снять тег -> адрес записи (raw выровнен)
    MOV E, A                          ; E = мл. байт указателя (смещение DE уже не нужно)
    INX H                             ; HL = &entry+1 (адрес цел ДО порчи L/H)
    MOV A, M                          ; ст. байт адреса (читаем ВЕРНЫЙ entry+1)
    MOV H, A                          ; H = ст. байт (не нужен для адреса)
    MOV L, E                          ; L = мл. байт -> HL = адрес записи
    POP PSW
    RET
