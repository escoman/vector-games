; Функция: func_render_glyph
; Адрес: 0x0803
; Размер: 192 байт (исполняемый код 0x0803-0x08A2 = 160 байт; хвост 0x08A3-0x08C2
;         = 32 байта — не код, данные/выравнивание, учтены как DEFB ниже)
; Описание: Отрисовка глифа символа A в VRAM-буфер. Вычисляет адрес в буфере
;           (база 0B000h + смещение), определяет колонку (L & 1Fh -> C) и строку
;           ((H>>2)&0C0h | (L>>2)&38h -> B). Сохраняет SP в var_saved_sp, затем
;           через таблицу указателей глифов (страница 06h, индекс = A*2) берёт
;           адрес 32-байтного глифа в DE. Готовит адрес назначения через
;           data_vram_col_table (0x051B) и var_screen_mode, переключает SP на
;           буфер (SPHL) и развёрнутым циклом POP D / MOV M,E / MOV M,D копирует
;           32 байта глифа в VRAM. Восстанавливает SP из var_saved_sp, регистры,
;           EI, RET. Входа DCR/ fall-through от func_put_char @0x0800.

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
    MOV E, M                    ; 0x082E
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
    MOV L, A                    ; 0x083F
    LXI B, 1FF8h                ; 0x0840
    XCHG                        ; 0x0843
    SPHL                        ; 0x0844
    XCHG                        ; 0x0845
    POP D                       ; 0x0846
    MOV M, E                    ; 0x0847
    INX H                       ; 0x0848
    MOV M, D                    ; 0x0849
    INX H                       ; 0x084A
    POP D                       ; 0x084B
    MOV M, E                    ; 0x084C
    INX H                       ; 0x084D
    MOV M, D                    ; 0x084E
    INX H                       ; 0x084F
    POP D                       ; 0x0850
    MOV M, E                    ; 0x0851
    INX H                       ; 0x0852
    MOV M, D                    ; 0x0853
    INX H                       ; 0x0854
    POP D                       ; 0x0855
    MOV M, E                    ; 0x0856
    INX H                       ; 0x0857
    MOV M, D                    ; 0x0858
    INX H                       ; 0x0859
    DAD B                       ; 0x085A
    POP D                       ; 0x085B
    MOV M, E                    ; 0x085C
    INX H                       ; 0x085D
    MOV M, D                    ; 0x085E
    INX H                       ; 0x085F
    POP D                       ; 0x0860
    MOV M, E                    ; 0x0861
    INX H                       ; 0x0862
    MOV M, D                    ; 0x0863
    INX H                       ; 0x0864
    POP D                       ; 0x0865
    MOV M, E                    ; 0x0866
    INX H                       ; 0x0867
    MOV M, D                    ; 0x0868
    INX H                       ; 0x0869
    POP D                       ; 0x086A
    MOV M, E                    ; 0x086B
    INX H                       ; 0x086C
    MOV M, D                    ; 0x086D
    INX H                       ; 0x086E
    DAD B                       ; 0x086F
    POP D                       ; 0x0870
    MOV M, E                    ; 0x0871
    INX H                       ; 0x0872
    MOV M, D                    ; 0x0873
    INX H                       ; 0x0874
    POP D                       ; 0x0875
    MOV M, E                    ; 0x0876
    INX H                       ; 0x0877
    MOV M, D                    ; 0x0878
    INX H                       ; 0x0879
    POP D                       ; 0x087A
    MOV M, E                    ; 0x087B
    INX H                       ; 0x087C
    MOV M, D                    ; 0x087D
    INX H                       ; 0x087E
    POP D                       ; 0x087F
    MOV M, E                    ; 0x0880
    INX H                       ; 0x0881
    MOV M, D                    ; 0x0882
    INX H                       ; 0x0883
    DAD B                       ; 0x0884
    POP D                       ; 0x0885
    MOV M, E                    ; 0x0886
    INX H                       ; 0x0887
    MOV M, D                    ; 0x0888
    INX H                       ; 0x0889
    POP D                       ; 0x088A
    MOV M, E                    ; 0x088B
    INX H                       ; 0x088C
    MOV M, D                    ; 0x088D
    INX H                       ; 0x088E
    POP D                       ; 0x088F
    MOV M, E                    ; 0x0890
    INX H                       ; 0x0891
    MOV M, D                    ; 0x0892
    INX H                       ; 0x0893
    POP D                       ; 0x0894
    MOV M, E                    ; 0x0895
    INX H                       ; 0x0896
    MOV M, D                    ; 0x0897
    INX H                       ; 0x0898
    LHLD var_saved_sp           ; 0x0899
    SPHL                        ; 0x089C
    POP H                       ; 0x089D
    POP D                       ; 0x089E
    POP B                       ; 0x089F
    POP PSW                     ; 0x08A0
    EI                          ; 0x08A1
    RET                         ; 0x08A2
    ; --- Хвост объекта 0x08A3-0x08C2 (32 байта): не исполняемый код ---
    ; Палитра: 16 слотов, OUT 02h=slot / OUT 0Ch=mem[0x08A3+slot] в func_vblank_isr.
    ; ОСОЗНАННОЕ отхождение от оригинала (накоплено в 2 стадии):
    ;  (Фаза 3) чанк E000 (вес бита 1) инвертирован во всех глифах -> индекс I->I^1;
    ;    компенсация — перестановка соседних пар слотов PAL'[j]=PAL[j^1].
    ;  (Стадия 1) цвет текста перемаркирован индекс 15<->8 (глифы: текст пишется
    ;    только в плоскость 0x8000); компенсация — свап слотов 8 и 15 местами.
    ; Итоговая РАСКРАШЕННАЯ картинка побайтово та же (гейт tools/compare_color.py).
    defb 00h, 00h, 7Bh, 30h, 0DAh, 0C9h, 0F2h, 0Dh   ; 0x08A3  (slot0..7 = old 1,0,3,2,5,4,7,6)
    defb 0ADh, 0Fh, 3Fh, 37h, 0DEh, 21h, 0FFh, 0A7h   ; 0x08AB  (slot8..15; свап 8<->15: slot8=серый текста)
    defb 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h       ; 0x08B3
    defb 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h       ; 0x08BB
