; Функция: func_load_gfx_2761
; Адрес: 0x04CD
; Размер: 78 байт
; Назначение: распаковщик блока глифов — копирует 2048 Б из data_gfx_2761 (0x2761,
;   обратный порядок байт источника) в экранную область глифов 0x6000 поблочными
;   пересылками по 8 байт (4 подблока × строки, шаг строки 0x10). МЁРТВЫЙ код в
;   реконструкции: data_glyph_block уже распакован заранее (data_glyph_block_unpacked),
;   поэтому диапазон выжжен нулями (KEEP_DEAD=0) и рантайм не исполняется.
;   Дизассемблирован полностью (50 инстр., без рассинхрона) для последующей оптимизации.
func_load_gfx_2761:
    LXI   H, data_gfx_2761      ; 0x04CD  источник упакованных глифов
    LXI   B, data_glyph_block   ; 0x04D0  приём: экранная область глифов
    LXI   D, 0008h              ; 0x04D3  D — счётчик строк (8)
loc_04D6:
    MOV   A, M                  ; 0x04D6
    STAX  B                     ; 0x04D7
    DCX   H                     ; 0x04D8  источник — обратный ход
    INX   B                     ; 0x04D9  приём — прямой ход
    DCR   E                     ; 0x04DA
    JNZ   loc_04D6              ; 0x04DB  8 байт подблока
    PUSH  B                     ; 0x04DE
    LXI   B, 0008h              ; 0x04DF
    DAD   B                     ; 0x04E2
    POP   B                     ; 0x04E3
    MVI   E, 08h                ; 0x04E4
loc_04E6:
    MOV   A, M                  ; 0x04E6
    STAX  B                     ; 0x04E7
    DCX   H                     ; 0x04E8
    INX   B                     ; 0x04E9
    DCR   E                     ; 0x04EA
    JNZ   loc_04E6              ; 0x04EB
    PUSH  B                     ; 0x04EE
    LXI   B, 0008h              ; 0x04EF
    DAD   B                     ; 0x04F2
    POP   B                     ; 0x04F3
    MVI   E, 08h                ; 0x04F4
loc_04F6:
    MOV   A, M                  ; 0x04F6
    STAX  B                     ; 0x04F7
    DCX   H                     ; 0x04F8
    INX   B                     ; 0x04F9
    DCR   E                     ; 0x04FA
    JNZ   loc_04F6              ; 0x04FB
    PUSH  B                     ; 0x04FE
    LXI   B, 0008h              ; 0x04FF
    DAD   B                     ; 0x0502
    POP   B                     ; 0x0503
    MVI   E, 08h                ; 0x0504
loc_0506:
    MOV   A, M                  ; 0x0506
    STAX  B                     ; 0x0507
    DCX   H                     ; 0x0508
    INX   B                     ; 0x0509
    DCR   E                     ; 0x050A
    JNZ   loc_0506              ; 0x050B
    DCR   D                     ; 0x050E  следующий ряд
    MVI   E, 08h                ; 0x050F
    PUSH  B                     ; 0x0511
    LXI   B, 0010h              ; 0x0512  шаг строки 0x10
    DAD   B                     ; 0x0515
    POP   B                     ; 0x0516
    JNZ   loc_04D6              ; 0x0517
    RET                         ; 0x051A
