; Функция: func_render_glyph
; Адрес: 0x0803
; Размер: 192 байт (исполняемый код 0x0803-0x08A2 = 160 байт; хвост 0x08A3-0x08C2
;         = 32 байта — не код: палитра 0x08A3..0x08B2 + нуль-зона 0x08B3..0x08C2)
; Описание: Отрисовка глифа символа A в VRAM-буфер. Вычисляет адрес в буфере
;           (база 0B000h + смещение), определяет колонку (L & 1Fh -> C) и строку
;           ((H>>2)&0C0h | (L>>2)&38h -> B). Сохр. SP в var_saved_sp (наследие),
;           через таблицу указателей глифов (стр. 06h, индекс = A*2) берёт СЛОВО
;           глифа в DE. Готовит адрес назначения через data_vram_col_table (0x051B)
;           и var_screen_mode.
;
; Tier 2 (компакция одноплоскостных глифов): слово указателя = адрес записи глифа,
;   бит0 = ТЕГ компактности. Запись compact (тег=1) хранит 8-байтную маску плоскости
;   0x0800 (прочие плоскости нулевые); raw (тег=0) — 32 байта (4 плоскости подряд).
;   Единый цикл по 4 плоскостям (0x0800..0x0800+3*0x2000): для каждого plane пишется
;   8 байт; источник — DE (raw — идёт последовательно; compact plane0 — маска, а
;   compact plane1..3 — общая нуль-зона zero8). Развёрнутый перенос по 8 байт (быстро,
;   чтобы не просадить кадр). Выход в VRAM побайтово идентичен прежней 32-байтной
;   версии (гейт tools/compare_color.py = 0 расхождений цвета + VRAM не меняется).
;   Регистры/флаги прозрачны: PUSH PSW/B/D/H на входе, POP обратно на выходе; EI, RET.
;   Входа DCR/ fall-through от func_put_char @0x0800.

func_render_glyph:
    PUSH PSW                    ; 0x0803
    PUSH B                      ; 0x0804
    PUSH D                      ; 0x0805
    PUSH H                      ; 0x0806
    MOV D, A                    ; 0x0807
    LXI B, textbuf_to_vram               ; 0x0808
    DAD B                       ; 0x080B
    MOV A, L                    ; 0x080C
    ANI 1Fh                     ; 0x080D
    MOV C, A                    ; 0x080F
    MOV A, H                    ; 0x0810
    RRC                         ; 0x0811
    RRC                         ; 0x0812
    ANI 0C0h                    ; 0x0813
    MOV B, A                    ; 0x0815
    MOV A, L                    ; 0x0816
    RRC                         ; 0x0817
    RRC                         ; 0x0818
    ANI 38h                     ; 0x0819
    ORA B                       ; 0x081B
    MOV B, A                    ; 0x081C
    MOV A, D                    ; 0x081D
    DI                          ; 0x081E
    LXI H, 0000h                ; 0x081F
    DAD SP                      ; 0x0822
    SHLD var_saved_sp           ; 0x0823
    ADD A                       ; 0x0826
    MVI H, 06h                  ; 0x0827
    MOV L, A                    ; 0x0829
    JNC loc_082E                ; 0x082A
    INR H                       ; 0x082D
loc_082E:
    MOV E, M                    ; 0x082E   DE = слово указателя (бит0 = тег)
    INX H                       ; 0x082F
    MOV D, M                    ; 0x0830
    MVI H, 00h                  ; 0x0831
    MOV L, C                    ; 0x0833
    PUSH B                      ; 0x0834
    LXI B, data_vram_col_table  ; 0x0835
    DAD B                       ; 0x0838
    MOV H, M                    ; 0x0839
    LDA var_screen_mode         ; 0x083A
    POP B                       ; 0x083D
    SUB B                       ; 0x083E
    MOV L, A                    ; 0x083F   HL = адрес приёмника (плоскость 0x0800)
    ; --- Tier 2: единый копир по 4 плоскостям (тег в бит0 DE) ---
    MOV A, E                    ; 0x0840   A = бит0 (тег компактности)
    ANI 01h                     ; 0x0841   C=тег; Z=1 если raw
    MOV C, A                    ; 0x0843   C = тег (0 raw / 1 compact)
    MOV A, E                    ; 0x0844
    SUB C                       ; 0x0845   снять бит0 -> адрес записи
    MOV E, A                    ; 0x0846   DE = база записи (бегущий источник)
    MVI B, 04h                  ; 0x0847   счётчик плоскостей 4..1
loc_plane:
    MOV A, C                    ; 0x0849   compact?
    ORA A                       ; 0x084A
    JZ loc_copy                 ; 0x084B   raw -> источник уже DE (последовательный)
    MOV A, B                    ; 0x084E   compact plane0 (B=4)?
    CPI 04h                     ; 0x084F
    JZ loc_copy                 ; 0x0851   plane0 -> маска в DE
    LXI D, zero8                ; 0x0854   compact plane1..3 -> нуль-зона
loc_copy:
    LDAX D                      ; 0x0857   развёрнутый перенос 8 байт plane
    MOV M, A                    ; 0x0858
    INX D                       ; 0x0859
    INX H                       ; 0x085A
    LDAX D                      ; 0x085B
    MOV M, A                    ; 0x085C
    INX D                       ; 0x085D
    INX H                       ; 0x085E
    LDAX D                      ; 0x085F
    MOV M, A                    ; 0x0860
    INX D                       ; 0x0861
    INX H                       ; 0x0862
    LDAX D                      ; 0x0863
    MOV M, A                    ; 0x0864
    INX D                       ; 0x0865
    INX H                       ; 0x0866
    LDAX D                      ; 0x0867
    MOV M, A                    ; 0x0868
    INX D                       ; 0x0869
    INX H                       ; 0x086A
    LDAX D                      ; 0x086B
    MOV M, A                    ; 0x086C
    INX D                       ; 0x086D
    INX H                       ; 0x086E
    LDAX D                      ; 0x086F
    MOV M, A                    ; 0x0870
    INX D                       ; 0x0871
    INX H                       ; 0x0872
    LDAX D                      ; 0x0873
    MOV M, A                    ; 0x0874
    INX D                       ; 0x0875
    INX H                       ; 0x0876
    ; шаг приёмника к следующей плоскости: HL += 0x1FF8 (после 8 INX H => +0x2000)
    MOV A, L                    ; 0x0877
    ADI 0F8h                    ; 0x0878
    MOV L, A                    ; 0x087A
    MOV A, H                    ; 0x087B
    ACI 1Fh                     ; 0x087C
    MOV H, A                    ; 0x087E
    DCR B                       ; 0x087F
    JNZ loc_plane               ; 0x0880
    POP H                       ; 0x0883
    POP D                       ; 0x0884
    POP B                       ; 0x0885
    POP PSW                     ; 0x0886
    EI                          ; 0x0887
    RET                         ; 0x0888
    defs 0x08A3 - $ ; pad — недостижимый код до хвоста палитры (сохраняет 192 Б объекта)
    ; --- Хвост объекта 0x08A3-0x08C2 (32 байта): не исполняемый код ---
    ; Палитра: 16 слотов, OUT 02h=slot / OUT 0Ch=mem[0x08A3+slot] в func_vblank_isr.
    ; ОСОЗНАННОЕ отхождение от оригинала (накоплено в 2 стадии):
    ;  (Фаза 3) чанк E000 (вес бита 1) инвертирован во всех глифах -> индекс I->I^1;
    ;    компенсация — перестановка соседних пар слотов PAL'[j]=PAL[j^1].
    ;  (Стадия 1) цвет текста перемаркирован индекс 15<->8 (глифы: текст пишется
    ;    только в плоскость 0x8000); компенсация — свап слотов 8 и 15 местами.
    ; Итоговая РАСКРАШЕННАЯ картинка побайтово та же (гейт tools/compare_color.py).
data_palette:
    defb 00h, 00h, 7Bh, 30h, 0DAh, 0C9h, 0F2h, 0Dh   ; 0x08A3  (slot0..7 = old 1,0,3,2,5,4,7,6)
    defb 0ADh, 0Fh, 3Fh, 37h, 0DEh, 21h, 0FFh, 0A7h   ; 0x08AB  (slot8..15; свап 8<->15: slot8=серый текста)
zero8:                                                ; 0x08B3 — источник нулей для compact plane1..3
    defb 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h       ; 0x08B3
    defb 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h       ; 0x08BB
