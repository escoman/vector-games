; clrs_new.asm — объединённый файл для clrs_new.rom
; Описание: ROM содержит 4 функции, идущие непрерывно от 0x0100 до 0x0176.
;   func_setup_and_halt (0x0100–0x013E) — инициализация и основной цикл HLT.
;   func_isr_delay_and_setup (0x013F–0x0151) — ISR: задержка и настройка регистров.
;   func_isr_palette_cycle (0x0152–0x0171) — ISR: вывод 9 значений палитры.
;   func_isr_rearm_and_exit (0x0172–0x0176) — ISR: перезапуск и выход.
;
; Данные RAM (data_rst7_vector, data_rst55_vector, data_rst75_vector,
;   var_palette_stack, data_isr_code_overlap) инициализируются во время
;   выполнения и НЕ включаются в ROM.
;
; Примечание: z80asm интерпретирует "ORA M" как "ORA B" (0xB6) вместо
;   "ORA [HL]" (0xBE). Для корректной генерации кода 0xBE используется
;   DEFB 0BEh (аналогично clrs.asm из tests/clrs/).

    org 0100h

; ============================================================
; Функция: func_setup_and_halt
; Адрес: 0x0100, Размер: 63 байта
; Точка входа ROM. (1) DI. (2) Очистка VRAM 8000h–FFFFh.
; (3) Запись вектора RST 7. (4) Инициализация стека палитры.
; (5) OUT 02h — граница. (6) EI / HLT — ожидание VBlank.
; ============================================================

func_setup_and_halt:
    DI                          ; 0x0100
    LXI H, 8000h                ; 0x0101
clrs_loc_0104:
    MVI M, 00h                  ; 0x0104
    INR L                       ; 0x0106
    JNZ clrs_loc_0104           ; 0x0107
    INR H                       ; 0x010A
    JNZ clrs_loc_0104           ; 0x010B
    MVI A, 0C3h                 ; 0x010E
    STA 0038h                   ; 0x0110 — код JP в вектор RST 7
    LXI H, func_isr_delay_and_setup  ; 0x0113
    SHLD 0039h                  ; 0x0116 — адрес ISR в вектор RST 7
    LXI SP, 0577h               ; 0x0119
    LXI H, func_isr_rearm_and_exit   ; 0x011C
    PUSH H                      ; 0x011F
    LXI H, func_isr_palette_cycle    ; 0x0120
    MVI A, 0F8h                 ; 0x0123
    PUSH PSW                    ; 0x0125
    MVI B, 07h                  ; 0x0126
clrs_loc_0128:
    PUSH H                      ; 0x0128
    PUSH PSW                    ; 0x0129
    DCR B                       ; 0x012A
    JNZ clrs_loc_0128           ; 0x012B
    MVI B, 08h                  ; 0x012E
    SUB B                       ; 0x0130
    JNC clrs_loc_0128           ; 0x0131
    XRA A                       ; 0x0134
    OUT 02h                     ; 0x0135
    LXI SP, func_setup_and_halt      ; 0x0137
    EI                          ; 0x013A
clrs_loc_013B:
    HLT                         ; 0x013B
    JMP clrs_loc_013B           ; 0x013C

; ============================================================
; Функция: func_isr_delay_and_setup
; Адрес: 0x013F, Размер: 19 байт
; Точка входа VBlank ISR. Задержка, настройка BC=0703h, D=01h,
; SP=0177h. Проваливается в func_isr_palette_cycle.
; ============================================================

func_isr_delay_and_setup:
    LXI B, 00ECh                ; 0x013F
clrs_loc_0142:
    DCX B                       ; 0x0142
    MOV A, B                    ; 0x0143
    ORA C                       ; 0x0144
    JNZ clrs_loc_0142           ; 0x0145
    NOP                         ; 0x0148
    NOP                         ; 0x0149
    LXI B, 0703h                ; 0x014A
    MVI D, 01h                  ; 0x014D
    LXI SP, 0177h               ; 0x014F

; ============================================================
; Функция: func_isr_palette_cycle
; Адрес: 0x0152, Размер: 32 байта
; Вывод палитры: POP PSW, задержка ORA M ×3, 9× OUT 0Ch
; с арифметикой XOR D/C/B, XRA A, RET.
;
; Примечание: ORA M (0xBE) заменён на DEFB 0BEh из-за ошибки z80asm.
; ============================================================

func_isr_palette_cycle:
    POP PSW                     ; 0x0152
    DEFB 0BEh                   ; 0x0153 — ORA M (z80asm: ORA M → ORA B)
    DEFB 0BEh                   ; 0x0154 — ORA M
    DEFB 0BEh                   ; 0x0155 — ORA M
    NOP                         ; 0x0156
    OUT 0Ch                     ; 0x0157
    XRA D                       ; 0x0159
    OUT 0Ch                     ; 0x015A
    XRA C                       ; 0x015C
    OUT 0Ch                     ; 0x015D
    XRA D                       ; 0x015F
    OUT 0Ch                     ; 0x0160
    XRA B                       ; 0x0162
    OUT 0Ch                     ; 0x0163
    XRA D                       ; 0x0165
    OUT 0Ch                     ; 0x0166
    XRA C                       ; 0x0168
    OUT 0Ch                     ; 0x0169
    XRA D                       ; 0x016B
    OUT 0Ch                     ; 0x016C
    XRA A                       ; 0x016E
    OUT 0Ch                     ; 0x016F
    RET                         ; 0x0171

; ============================================================
; Функция: func_isr_rearm_and_exit
; Адрес: 0x0172, Размер: 5 байт
; Выход ISR: LXI SP,00FEh / EI / RET.
; ============================================================

func_isr_rearm_and_exit:
    LXI SP, 00FEh               ; 0x0172
    EI                          ; 0x0175
    RET                         ; 0x0176
