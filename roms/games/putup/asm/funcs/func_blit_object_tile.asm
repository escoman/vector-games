; Функция: func_blit_object_tile
; Адрес: 0x0542
; Размер: 190 байт
; Описание: Диспетчер отрисовки объекта-тайла: SP->0x0013, счётчик анимации 0x0010,
;   адрес VRAM из 0x000C; цикл CMP по data_vram_col_table (+0x18/+0x1B),
;   выбор растра по коду объекта -> func_blit_plane_mask{80/40/20/10}
;   (+4/+4/+3/+4) и общий выход; указатель глифа из data_glyph_ptr_table+0x2C.
;   Двусмысленные цели (0x0364/0x038A/0x0376) и RAM-векторы (0x0015/0x002E) — raw.

func_blit_object_tile:
    LXI   H, 0000h          ; 0x0542
    DAD   SP          ; 0x0545
    SHLD  0013h          ; 0x0546
    LDA   0010h          ; 0x0549
    ORA   A          ; 0x054C
    JZ    0364h          ; 0x054D
    LXI   H, 0FFFFh          ; 0x0550
    SHLD  000Eh          ; 0x0553
    INR   A          ; 0x0556
    JNZ   0364h          ; 0x0557
    INR   A          ; 0x055A
    STA   0010h          ; 0x055B
    LHLD  000Ch          ; 0x055E
    JMP   038Ah          ; 0x0561
    CALL  0691h          ; 0x0564
    JNZ   0533h          ; 0x0567
    LXI   H, 0010h          ; 0x056A
    MOV   A, M          ; 0x056D
    ORA   A          ; 0x056E
    JZ    0376h          ; 0x056F
    DCR   M          ; 0x0572
    JZ    0533h          ; 0x0573
    LHLD  000Ch          ; 0x0576
    CALL  0694h          ; 0x0579
    CALL  002Eh          ; 0x057C
    MVI   C, 20h          ; 0x057F
    CALL  0015h          ; 0x0581
    CALL  0015h          ; 0x0584
    CALL  032Eh          ; 0x0587
    CALL  0296h          ; 0x058A
    MOV   D, A          ; 0x058D
    LXI   H, data_vram_col_table+001Dh          ; 0x058E
    LXI   B, 0011h          ; 0x0591
    CMP   M          ; 0x0594
    JZ    04F0h          ; 0x0595
    INX   H          ; 0x0598
    DCR   C          ; 0x0599
    JNZ   0394h          ; 0x059A
    MVI   C, 0Ah          ; 0x059D
    CMP   M          ; 0x059F
    JZ    04DCh          ; 0x05A0
    INX   H          ; 0x05A3
    DCR   C          ; 0x05A4
    JNZ   039Fh          ; 0x05A5
    MVI   C, 06h          ; 0x05A8
    CMP   M          ; 0x05AA
    JZ    04C1h          ; 0x05AB
    INX   H          ; 0x05AE
    DCR   C          ; 0x05AF
    JNZ   03AAh          ; 0x05B0
    ANI   0C0h          ; 0x05B3
    CPI   40h          ; 0x05B5
    JZ    04A7h          ; 0x05B7
    CPI   80h          ; 0x05BA
    JZ    0498h          ; 0x05BC
    MOV   A, D          ; 0x05BF
    ANI   0C7h          ; 0x05C0
    SUI   04h          ; 0x05C2
    JZ    0489h          ; 0x05C4
    DCR   A          ; 0x05C7
    JZ    0483h          ; 0x05C8
    DCR   A          ; 0x05CB
    JZ    046Fh          ; 0x05CC
    MOV   A, D          ; 0x05CF
    ANI   0C0h          ; 0x05D0
    JZ    043Dh          ; 0x05D2
    MOV   A, D          ; 0x05D5
    ANI   07h          ; 0x05D6
    JZ    0432h          ; 0x05D8
    SUI   02h          ; 0x05DB
    JZ    0427h          ; 0x05DD
    SUI   02h          ; 0x05E0
    JZ    041Ch          ; 0x05E2
    SUI   03h          ; 0x05E5
    JZ    040Dh          ; 0x05E7
    MOV   A, D          ; 0x05EA
    ANI   08h          ; 0x05EB
    JNZ   04FEh          ; 0x05ED
    MOV   A, D          ; 0x05F0
    ANI   07h          ; 0x05F1
    MOV   C, A          ; 0x05F3
    DCR   A          ; 0x05F4
    LXI   H, data_glyph_ptr_table+002Ch          ; 0x05F5
    DAD   B          ; 0x05F8
    CALL  02E6h          ; 0x05F9
    CALL  02F6h          ; 0x05FC
    ; --- хвост 0x05FF..0x05FF (не размечен как код) ---
    DEFB 0FEh
