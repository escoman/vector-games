; Функция: func_render_glyph
; Адрес: 0x0803
; Размер: 167 байт (исполняемый код 0x0803..0x0899 = 151 байт; хвост 16 байт —
;         не код: нуль-зона zero8). data_palette → func_main_init.asm
; Описание: Отрисовка глифа символа A в VRAM-буфер. Вычисляет адрес в буфере
;           (база 0B000h + смещение), определяет колонку (L & 1Fh -> C) и строку
;           ((H>>2)&0C0h | (L>>2)&38h -> B). Через таблицу указателей глифов
;           (база = метка data_glyph_ptr_table, индекс = A*2; Stage-4A: вместо
;           зашитой страницы 06h — `LXI H, метка; DAD D`) берёт СЛОВО глифа в DE.
;           Готовит адрес назначения через data_vram_col_table и var_screen_mode.
;
; DI/EI и LXI H/DAD SP/SHLD var_saved_sp УБРАНЫ (стадия: title-music slowdown):
;   в прежней версии SP сохранялся через DAD SP между PUSH/POP-стеком — для
;   атомарности этой пары и нужен был DI. В Tier-2-копире SP не модифицируется,
;   сохранение мертво (LHLD var_saved_sp в ROM нет), а DI на ~900 T (~300 µs)
;   на глиф глошил VBlank ISR — а из VBlank тикает музыкальный секвенсор, отсюда
;   просадка темпа музыки на заставке, где рисуется ~768 тайлов подряд.
;
; Tier 2 (компакция одноплоскостных глифов): слово указателя = адрес записи глифа,
;   бит0 = ТЕГ компактности. Запись compact (тег=1) хранит 8-байтную маску плоскости
;   0x0800 (прочие плоскости нулевые); raw (тег=0) — 32 байта (4 плоскости подряд).
;   Единый цикл по 4 плоскостям (0x0800..0x0800+3*0x2000): для каждого plane пишется
;   8 байт; источник — DE (raw — идёт последовательно; compact plane0 — маска, а
;   compact plane1..3 — общая нуль-зона zero8). Развёрнутый перенос по 8 байт (быстро,
;   чтобы не просадить кадр). Выход в VRAM побайтово идентичен прежней 32-байтной
;   версии (гейт tools/compare_color.py = 0 расхождений цвета + VRAM не меняется).
;   Регистры/флаги прозрачны: PUSH PSW/B/D/H на входе, POP обратно на выходе; RET.
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
    ADD A                       ; A = 2*char (младший байт), CY = старший бит
    MOV E, A                    ; E = младший offset
    MVI A, 00h
    ADC A                       ; A = 0 + 0 + CY = старший байт (0/1)
    MOV D, A                    ; DE = 2*char (16-бит смещение)
    LXI H, data_glyph_ptr_table ; база таблицы — метка (relocatable, Stage-4A)
    DAD D                       ; HL = таблица + 2*char
    MOV E, M                    ; DE = слово указателя (бит0 = тег)
    INX H                       ;
    MOV D, M                    ; (было: MVI H,06h + страница 0x0600 — абсолют)
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
    RET                         ; 0x0887
    ; data_palette перенесена в func_main_init.asm (перед меткой func_main_init:)
zero8:                                                ; 0x08B3 — источник нулей для compact plane1..3
    defb 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h       ; 0x08B3
    defb 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h       ; 0x08BB
