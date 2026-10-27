; ===========================================================================
; SOUNDEMO.ROM -- decompressed program (code view)
; Origin 0x0100, self-extracting shilin LZ; decompressed size 0x4000 bytes
; ROM file 9344 bytes  SHA256 see provenance
; Read-only view -- build consumes asm/layout.asm
; ===========================================================================

; --- Code range 0000..0002 (3 bytes) ---
; CPU RESET vector -> JMP func_main_entry
vec_reset:
    JMP 37A8                ; 0000: C3 A8 37

; --- Code range 0038..003A (3 bytes) ---
; RST 7 (VBlank ISR) -> JMP func_irq_vblank
vec_rst7:
    JMP 394B                ; 0038: C3 4B 39

; --- Code range 2AC0..3068 (1449 bytes) ---
; Self-modifying ch0 (port 0x0B) period writer. Table lookup at 3289 -> control word; branches by [3289] value: 1=attack, 2=decay, 3=sustain, 4=release, 5=release_alt
func_channel_A_dispatcher:
    MVI A, 0C               ; 2AC0: 3E 0C
    ORA A                   ; 2AC2: B7
    JNZ 2B8E                ; 2AC3: C2 8E 2B
    LXI H, 3289             ; 2AC6: 21 89 32
    MOV A, M                ; 2AC9: 7E
    STA 2B3C                ; 2ACA: 32 3C 2B
    INX H                   ; 2ACD: 23
    ORA A                   ; 2ACE: B7
    JZ 2BDE                 ; 2ACF: CA DE 2B
    DCR A                   ; 2AD2: 3D
    JZ 2B82                 ; 2AD3: CA 82 2B
    DCR A                   ; 2AD6: 3D
    JZ 2B65                 ; 2AD7: CA 65 2B
    DCR A                   ; 2ADA: 3D
    JZ 2B74                 ; 2ADB: CA 74 2B
    DCR A                   ; 2ADE: 3D
    JZ 2B3D                 ; 2ADF: CA 3D 2B
    DCR A                   ; 2AE2: 3D
    JZ 2B54                 ; 2AE3: CA 54 2B
    XCHG                    ; 2AE6: EB
    LXI H, 3089             ; 2AE7: 21 89 30
    LXI B, 0002             ; 2AEA: 01 02 00
    DCR A                   ; 2AED: 3D
    JZ 2B20                 ; 2AEE: CA 20 2B
    DCR A                   ; 2AF1: 3D
    JZ 2AFA                 ; 2AF2: CA FA 2A
    DAD B                   ; 2AF5: 09
    DCR A                   ; 2AF6: 3D
    JNZ 2AF5                ; 2AF7: C2 F5 2A
    PUSH H                  ; 2AFA: E5
    POP B                   ; 2AFB: C1
    LDAX B                  ; 2AFC: 0A
    MOV L, A                ; 2AFD: 6F
    INX B                   ; 2AFE: 03
    LDAX B                  ; 2AFF: 0A
    MOV H, A                ; 2B00: 67
    SHLD 2B05               ; 2B01: 22 05 2B
    LXI H, 0A89             ; 2B04: 21 89 0A
    XCHG                    ; 2B07: EB
    MOV A, M                ; 2B08: 7E
    INX H                   ; 2B09: 23
    DCR A                   ; 2B0A: 3D
    STA 2AC1                ; 2B0B: 32 C1 2A
    MOV A, E                ; 2B0E: 7B
; OUT 0Bh (LSB of counter 0 period)
label_ch0_out_lo:
    OUT 0B                  ; 2B0F: D3 0B
    MOV A, D                ; 2B11: 7A
; OUT 0Bh (MSB of counter 0 period)
label_ch0_out_hi:
    OUT 0B                  ; 2B12: D3 0B
    SHLD 2AC7               ; 2B14: 22 C7 2A
    XRA A                   ; 2B17: AF
    STA 2B93                ; 2B18: 32 93 2B
    INR A                   ; 2B1B: 3C
    STA 2BC6                ; 2B1C: 32 C6 2B
    RET                     ; 2B1F: C9
    LXI H, 0000             ; 2B20: 21 00 00
    SHLD 2B05               ; 2B23: 22 05 2B
    XCHG                    ; 2B26: EB
    MOV A, M                ; 2B27: 7E
    INX H                   ; 2B28: 23
    DCR A                   ; 2B29: 3D
    STA 2AC1                ; 2B2A: 32 C1 2A
    XRA A                   ; 2B2D: AF
    STA 2B93                ; 2B2E: 32 93 2B
    STA 2BC6                ; 2B31: 32 C6 2B
    MVI A, 36               ; 2B34: 3E 36
; OUT 08h control word latch
label_ch0_out_ctl:
    OUT 08                  ; 2B36: D3 08
    SHLD 2AC7               ; 2B38: 22 C7 2A
    RET                     ; 2B3B: C9
    DAD B                   ; 2B3C: 09
    MOV E, M                ; 2B3D: 5E
    INX H                   ; 2B3E: 23
    MOV D, M                ; 2B3F: 56
    INX H                   ; 2B40: 23
    XCHG                    ; 2B41: EB
    SHLD 2AC7               ; 2B42: 22 C7 2A
    LHLD 2B52               ; 2B45: 2A 52 2B
    MOV M, E                ; 2B48: 73
    INX H                   ; 2B49: 23
    MOV M, D                ; 2B4A: 72
    INX H                   ; 2B4B: 23
    SHLD 2B52               ; 2B4C: 22 52 2B
    JMP 2AC6                ; 2B4F: C3 C6 2A
    NOP                     ; 2B52: 08
    MOV A, H                ; 2B53: 7C
; ch0 attack path -- selfmod slot 2AC1=period base
func_channel_A_attack:
    LHLD 2B52               ; 2B54: 2A 52 2B
    DCX H                   ; 2B57: 2B
    MOV D, M                ; 2B58: 56
    DCX H                   ; 2B59: 2B
    MOV E, M                ; 2B5A: 5E
    SHLD 2B52               ; 2B5B: 22 52 2B
    XCHG                    ; 2B5E: EB
    SHLD 2AC7               ; 2B5F: 22 C7 2A
    JMP 2AC6                ; 2B62: C3 C6 2A
    LXI H, 3738             ; 2B65: 21 38 37
    SHLD 2AC7               ; 2B68: 22 C7 2A
    LXI H, 7C00             ; 2B6B: 21 00 7C
    SHLD 2B52               ; 2B6E: 22 52 2B
    JMP 2AC6                ; 2B71: C3 C6 2A
    MVI A, 36               ; 2B74: 3E 36
    OUT 08                  ; 2B76: D3 08
    MVI A, C9               ; 2B78: 3E C9
    STA 2AC0                ; 2B7A: 32 C0 2A
    XRA A                   ; 2B7D: AF
    STA 2BC6                ; 2B7E: 32 C6 2B
    RET                     ; 2B81: C9
    MOV E, M                ; 2B82: 5E
    INX H                   ; 2B83: 23
    MOV D, M                ; 2B84: 56
    INX H                   ; 2B85: 23
    XCHG                    ; 2B86: EB
    SHLD 2AE8               ; 2B87: 22 E8 2A
    XCHG                    ; 2B8A: EB
    JMP 2AC9                ; 2B8B: C3 C9 2A
    DCR A                   ; 2B8E: 3D
    STA 2AC1                ; 2B8F: 32 C1 2A
    MVI A, 01               ; 2B92: 3E 01
    ORA A                   ; 2B94: B7
    RZ                      ; 2B95: C8
    LXI H, 31A6             ; 2B96: 21 A6 31
    MVI A, 00               ; 2B99: 3E 00
    ORA A                   ; 2B9B: B7
    CZ 2BD2                 ; 2B9C: CC D2 2B
    DCR A                   ; 2B9F: 3D
    STA 2B9A                ; 2BA0: 32 9A 2B
    MOV E, M                ; 2BA3: 5E
    MOV C, M                ; 2BA4: 4E
    INX H                   ; 2BA5: 23
    MOV D, M                ; 2BA6: 56
    INX H                   ; 2BA7: 23
    SHLD 2B97               ; 2BA8: 22 97 2B
    MOV A, D                ; 2BAB: 7A
    INR C                   ; 2BAC: 0C
    INR A                   ; 2BAD: 3C
    ORA C                   ; 2BAE: B1
    JZ 2BC5                 ; 2BAF: CA C5 2B
    LXI H, 53F9             ; 2BB2: 21 F9 53
    DAD D                   ; 2BB5: 19
    SHLD 2BB3               ; 2BB6: 22 B3 2B
    MOV A, L                ; 2BB9: 7D
; OUT 0B,lo / OUT 0B,hi on attack
label_ch0_attack_out_lohi:
    OUT 0B                  ; 2BBA: D3 0B
    MOV A, H                ; 2BBC: 7C
    OUT 0B                  ; 2BBD: D3 0B
    XRA A                   ; 2BBF: AF
    INR A                   ; 2BC0: 3C
    STA 2BC6                ; 2BC1: 32 C6 2B
    RET                     ; 2BC4: C9
    MVI A, 01               ; 2BC5: 3E 01
    ORA A                   ; 2BC7: B7
    RZ                      ; 2BC8: C8
    DCR A                   ; 2BC9: 3D
    STA 2BC6                ; 2BCA: 32 C6 2B
    MVI A, 36               ; 2BCD: 3E 36
; OUT 08 control after attack
label_ch0_attack_ctl:
    OUT 08                  ; 2BCF: D3 08
    RET                     ; 2BD1: C9
    LXI H, 31A4             ; 2BD2: 21 A4 31
    SHLD 2B97               ; 2BD5: 22 97 2B
    MVI A, 01               ; 2BD8: 3E 01
    STA 2B9A                ; 2BDA: 32 9A 2B
    RET                     ; 2BDD: C9
    MOV E, M                ; 2BDE: 5E
    INX H                   ; 2BDF: 23
    MOV D, M                ; 2BE0: 56
    INX H                   ; 2BE1: 23
    XCHG                    ; 2BE2: EB
    MOV A, M                ; 2BE3: 7E
    INX H                   ; 2BE4: 23
    STA 2BD9                ; 2BE5: 32 D9 2B
    SHLD 2BD3               ; 2BE8: 22 D3 2B
    CALL 2BD2               ; 2BEB: CD D2 2B
    XCHG                    ; 2BEE: EB
    MOV A, M                ; 2BEF: 7E
    STA 2B3C                ; 2BF0: 32 3C 2B
    INX H                   ; 2BF3: 23
    SUI 06                  ; 2BF4: D6 06
    XCHG                    ; 2BF6: EB
    LHLD 2AE8               ; 2BF7: 2A E8 2A
    LXI B, 0002             ; 2BFA: 01 02 00
    DCR A                   ; 2BFD: 3D
    JZ 2C06                 ; 2BFE: CA 06 2C
    DAD B                   ; 2C01: 09
    DCR A                   ; 2C02: 3D
    JNZ 2C01                ; 2C03: C2 01 2C
    PUSH H                  ; 2C06: E5
    POP B                   ; 2C07: C1
    LDAX B                  ; 2C08: 0A
    MOV L, A                ; 2C09: 6F
    INX B                   ; 2C0A: 03
    LDAX B                  ; 2C0B: 0A
    MOV H, A                ; 2C0C: 67
    SHLD 2B05               ; 2C0D: 22 05 2B
    SHLD 2BB3               ; 2C10: 22 B3 2B
    XCHG                    ; 2C13: EB
    XRA A                   ; 2C14: AF
    INR A                   ; 2C15: 3C
    STA 2B93                ; 2C16: 32 93 2B
    MOV A, M                ; 2C19: 7E
    INX H                   ; 2C1A: 23
    SHLD 2AC7               ; 2C1B: 22 C7 2A
    ORA A                   ; 2C1E: B7
    JNZ 2C25                ; 2C1F: C2 25 2C
    LDA 2BD9                ; 2C22: 3A D9 2B
    STA 2AC1                ; 2C25: 32 C1 2A
    JMP 2B8E                ; 2C28: C3 8E 2B
    SHLD 2AC7               ; 2C2B: 22 C7 2A
    SHLD 2B66               ; 2C2E: 22 66 2B
    XCHG                    ; 2C31: EB
    SHLD 2B6C               ; 2C32: 22 6C 2B
    SHLD 2B52               ; 2C35: 22 52 2B
    MOV H, B                ; 2C38: 60
    MOV L, C                ; 2C39: 69
    SHLD 2AE8               ; 2C3A: 22 E8 2A
    XRA A                   ; 2C3D: AF
    STA 2AC1                ; 2C3E: 32 C1 2A
    STA 2B93                ; 2C41: 32 93 2B
    INR A                   ; 2C44: 3C
    STA 2BC6                ; 2C45: 32 C6 2B
    MVI A, 3E               ; 2C48: 3E 3E
    STA 2AC0                ; 2C4A: 32 C0 2A
    MVI A, 36               ; 2C4D: 3E 36
; ch0 release: OUT 08h
label_ch0_release_ctl1:
    OUT 08                  ; 2C4F: D3 08
    MVI A, 06               ; 2C51: 3E 06
    STA 2B3C                ; 2C53: 32 3C 2B
    RET                     ; 2C56: C9
    MVI A, C9               ; 2C57: 3E C9
    STA 2AC0                ; 2C59: 32 C0 2A
    XRA A                   ; 2C5C: AF
    STA 2BC6                ; 2C5D: 32 C6 2B
    MVI A, 36               ; 2C60: 3E 36
; ch0 release: OUT 08h (second latch)
label_ch0_release_ctl2:
    OUT 08                  ; 2C62: D3 08
    RET                     ; 2C64: C9
    SHLD 2C6D               ; 2C65: 22 6D 2C
    XRA A                   ; 2C68: AF
    STA 2C7C                ; 2C69: 32 7C 2C
    LXI H, EF42             ; 2C6C: 21 42 EF
    LDA 2BC6                ; 2C6F: 3A C6 2B
    ORA A                   ; 2C72: B7
    JZ 2C7B                 ; 2C73: CA 7B 2C
    LDA 2B3C                ; 2C76: 3A 3C 2B
    SUI 06                  ; 2C79: D6 06
    CPI 03                  ; 2C7B: FE 03
    RZ                      ; 2C7D: C8
    JNC 2C92                ; 2C7E: D2 92 2C
    LDA 2C7C                ; 2C81: 3A 7C 2C
    DCR A                   ; 2C84: 3D
    STA 2C7C                ; 2C85: 32 7C 2C
    DCR L                   ; 2C88: 2D
    MVI M, 00               ; 2C89: 36 00
    DCR L                   ; 2C8B: 2D
    MVI M, 00               ; 2C8C: 36 00
    SHLD 2C6D               ; 2C8E: 22 6D 2C
    RET                     ; 2C91: C9
    LDA 2C7C                ; 2C92: 3A 7C 2C
    INR A                   ; 2C95: 3C
    STA 2C7C                ; 2C96: 32 7C 2C
    MVI M, 00               ; 2C99: 36 00
    INR L                   ; 2C9B: 2C
    MVI M, 3C               ; 2C9C: 36 3C
    INR L                   ; 2C9E: 2C
    SHLD 2C6D               ; 2C9F: 22 6D 2C
    RET                     ; 2CA2: C9
    MVI A, 0C               ; 2CA3: 3E 0C
    ORA A                   ; 2CA5: B7
    JNZ 2D71                ; 2CA6: C2 71 2D
    LXI H, 3289             ; 2CA9: 21 89 32
    MOV A, M                ; 2CAC: 7E
    STA 2D1F                ; 2CAD: 32 1F 2D
    INX H                   ; 2CB0: 23
    ORA A                   ; 2CB1: B7
    JZ 2DC1                 ; 2CB2: CA C1 2D
    DCR A                   ; 2CB5: 3D
    JZ 2D65                 ; 2CB6: CA 65 2D
    DCR A                   ; 2CB9: 3D
    JZ 2D48                 ; 2CBA: CA 48 2D
    DCR A                   ; 2CBD: 3D
    JZ 2D57                 ; 2CBE: CA 57 2D
    DCR A                   ; 2CC1: 3D
    JZ 2D20                 ; 2CC2: CA 20 2D
    DCR A                   ; 2CC5: 3D
    JZ 2D37                 ; 2CC6: CA 37 2D
    XCHG                    ; 2CC9: EB
    LXI H, 3089             ; 2CCA: 21 89 30
    LXI B, 0002             ; 2CCD: 01 02 00
    DCR A                   ; 2CD0: 3D
    JZ 2D03                 ; 2CD1: CA 03 2D
    DCR A                   ; 2CD4: 3D
    JZ 2CDD                 ; 2CD5: CA DD 2C
    DAD B                   ; 2CD8: 09
    DCR A                   ; 2CD9: 3D
    JNZ 2CD8                ; 2CDA: C2 D8 2C
    PUSH H                  ; 2CDD: E5
    POP B                   ; 2CDE: C1
    LDAX B                  ; 2CDF: 0A
    MOV L, A                ; 2CE0: 6F
    INX B                   ; 2CE1: 03
    LDAX B                  ; 2CE2: 0A
    MOV H, A                ; 2CE3: 67
    SHLD 2CE8               ; 2CE4: 22 E8 2C
    LXI H, 0A89             ; 2CE7: 21 89 0A
    XCHG                    ; 2CEA: EB
    MOV A, M                ; 2CEB: 7E
    INX H                   ; 2CEC: 23
    DCR A                   ; 2CED: 3D
    STA 2CA4                ; 2CEE: 32 A4 2C
    MOV A, E                ; 2CF1: 7B
; OUT 0Ah (LSB of counter 1)
label_ch1_out_lo:
    OUT 0A                  ; 2CF2: D3 0A
    MOV A, D                ; 2CF4: 7A
; OUT 0Ah (MSB of counter 1)
label_ch1_out_hi:
    OUT 0A                  ; 2CF5: D3 0A
    SHLD 2CAA               ; 2CF7: 22 AA 2C
    XRA A                   ; 2CFA: AF
    STA 2D76                ; 2CFB: 32 76 2D
    INR A                   ; 2CFE: 3C
    STA 2DA9                ; 2CFF: 32 A9 2D
    RET                     ; 2D02: C9
    LXI H, 0000             ; 2D03: 21 00 00
    SHLD 2CE8               ; 2D06: 22 E8 2C
    XCHG                    ; 2D09: EB
    MOV A, M                ; 2D0A: 7E
    INX H                   ; 2D0B: 23
    DCR A                   ; 2D0C: 3D
    STA 2CA4                ; 2D0D: 32 A4 2C
    XRA A                   ; 2D10: AF
    STA 2D76                ; 2D11: 32 76 2D
    STA 2DA9                ; 2D14: 32 A9 2D
    MVI A, 76               ; 2D17: 3E 76
; OUT 08 control (ch1)
label_ch1_ctl1:
    OUT 08                  ; 2D19: D3 08
    SHLD 2CAA               ; 2D1B: 22 AA 2C
    RET                     ; 2D1E: C9
    DAD B                   ; 2D1F: 09
    MOV E, M                ; 2D20: 5E
    INX H                   ; 2D21: 23
    MOV D, M                ; 2D22: 56
    INX H                   ; 2D23: 23
    XCHG                    ; 2D24: EB
    SHLD 2CAA               ; 2D25: 22 AA 2C
    LHLD 2D35               ; 2D28: 2A 35 2D
    MOV M, E                ; 2D2B: 73
    INX H                   ; 2D2C: 23
    MOV M, D                ; 2D2D: 72
    INX H                   ; 2D2E: 23
    SHLD 2D35               ; 2D2F: 22 35 2D
    JMP 2CA9                ; 2D32: C3 A9 2C
    NOP                     ; 2D35: 08
    MOV A, L                ; 2D36: 7D
    LHLD 2D35               ; 2D37: 2A 35 2D
    DCX H                   ; 2D3A: 2B
    MOV D, M                ; 2D3B: 56
    DCX H                   ; 2D3C: 2B
    MOV E, M                ; 2D3D: 5E
    SHLD 2D35               ; 2D3E: 22 35 2D
    XCHG                    ; 2D41: EB
    SHLD 2CAA               ; 2D42: 22 AA 2C
    JMP 2CA9                ; 2D45: C3 A9 2C
    LXI H, 36E9             ; 2D48: 21 E9 36
    SHLD 2CAA               ; 2D4B: 22 AA 2C
    LXI H, 7D00             ; 2D4E: 21 00 7D
    SHLD 2D35               ; 2D51: 22 35 2D
    JMP 2CA9                ; 2D54: C3 A9 2C
    MVI A, 76               ; 2D57: 3E 76
; OUT 08 with 76h mode word -- ch1 stop
label_ch1_release_ctl:
    OUT 08                  ; 2D59: D3 08
    MVI A, C9               ; 2D5B: 3E C9
    STA 2CA3                ; 2D5D: 32 A3 2C
    XRA A                   ; 2D60: AF
    STA 2DA9                ; 2D61: 32 A9 2D
    RET                     ; 2D64: C9
    MOV E, M                ; 2D65: 5E
    INX H                   ; 2D66: 23
    MOV D, M                ; 2D67: 56
    INX H                   ; 2D68: 23
    XCHG                    ; 2D69: EB
    SHLD 2CCB               ; 2D6A: 22 CB 2C
    XCHG                    ; 2D6D: EB
    JMP 2CAC                ; 2D6E: C3 AC 2C
    DCR A                   ; 2D71: 3D
    STA 2CA4                ; 2D72: 32 A4 2C
    MVI A, 01               ; 2D75: 3E 01
    ORA A                   ; 2D77: B7
    RZ                      ; 2D78: C8
    LXI H, 31A4             ; 2D79: 21 A4 31
    MVI A, 00               ; 2D7C: 3E 00
    ORA A                   ; 2D7E: B7
    CZ 2DB5                 ; 2D7F: CC B5 2D
    DCR A                   ; 2D82: 3D
    STA 2D7D                ; 2D83: 32 7D 2D
    MOV E, M                ; 2D86: 5E
    MOV C, M                ; 2D87: 4E
    INX H                   ; 2D88: 23
    MOV D, M                ; 2D89: 56
    INX H                   ; 2D8A: 23
    SHLD 2D7A               ; 2D8B: 22 7A 2D
    MOV A, D                ; 2D8E: 7A
    INR C                   ; 2D8F: 0C
    INR A                   ; 2D90: 3C
    ORA C                   ; 2D91: B1
    JZ 2DA8                 ; 2D92: CA A8 2D
    LXI H, 5395             ; 2D95: 21 95 53
    DAD D                   ; 2D98: 19
    SHLD 2D96               ; 2D99: 22 96 2D
    MOV A, L                ; 2D9C: 7D
; OUT 0A,lo / OUT 0A,hi sweep
label_ch1_sweep_lohi:
    OUT 0A                  ; 2D9D: D3 0A
    MOV A, H                ; 2D9F: 7C
    OUT 0A                  ; 2DA0: D3 0A
    XRA A                   ; 2DA2: AF
    INR A                   ; 2DA3: 3C
    STA 2DA9                ; 2DA4: 32 A9 2D
    RET                     ; 2DA7: C9
    MVI A, 01               ; 2DA8: 3E 01
    ORA A                   ; 2DAA: B7
    RZ                      ; 2DAB: C8
    DCR A                   ; 2DAC: 3D
    STA 2DA9                ; 2DAD: 32 A9 2D
    MVI A, 76               ; 2DB0: 3E 76
; OUT 08 ch1 sweep control
label_ch1_sweep_ctl:
    OUT 08                  ; 2DB2: D3 08
    RET                     ; 2DB4: C9
    LXI H, 31A4             ; 2DB5: 21 A4 31
    SHLD 2D7A               ; 2DB8: 22 7A 2D
    MVI A, 01               ; 2DBB: 3E 01
    STA 2D7D                ; 2DBD: 32 7D 2D
    RET                     ; 2DC0: C9
    MOV E, M                ; 2DC1: 5E
    INX H                   ; 2DC2: 23
    MOV D, M                ; 2DC3: 56
    INX H                   ; 2DC4: 23
    XCHG                    ; 2DC5: EB
    MOV A, M                ; 2DC6: 7E
    INX H                   ; 2DC7: 23
    STA 2DBC                ; 2DC8: 32 BC 2D
    SHLD 2DB6               ; 2DCB: 22 B6 2D
    CALL 2DB5               ; 2DCE: CD B5 2D
    XCHG                    ; 2DD1: EB
    MOV A, M                ; 2DD2: 7E
    STA 2D1F                ; 2DD3: 32 1F 2D
    INX H                   ; 2DD6: 23
    SUI 06                  ; 2DD7: D6 06
    XCHG                    ; 2DD9: EB
    LHLD 2CCB               ; 2DDA: 2A CB 2C
    LXI B, 0002             ; 2DDD: 01 02 00
    DCR A                   ; 2DE0: 3D
    JZ 2DE9                 ; 2DE1: CA E9 2D
    DAD B                   ; 2DE4: 09
    DCR A                   ; 2DE5: 3D
    JNZ 2DE4                ; 2DE6: C2 E4 2D
    PUSH H                  ; 2DE9: E5
    POP B                   ; 2DEA: C1
    LDAX B                  ; 2DEB: 0A
    MOV L, A                ; 2DEC: 6F
    INX B                   ; 2DED: 03
    LDAX B                  ; 2DEE: 0A
    MOV H, A                ; 2DEF: 67
    SHLD 2CE8               ; 2DF0: 22 E8 2C
    SHLD 2D96               ; 2DF3: 22 96 2D
    XCHG                    ; 2DF6: EB
    XRA A                   ; 2DF7: AF
    INR A                   ; 2DF8: 3C
    STA 2D76                ; 2DF9: 32 76 2D
    MOV A, M                ; 2DFC: 7E
    INX H                   ; 2DFD: 23
    SHLD 2CAA               ; 2DFE: 22 AA 2C
    ORA A                   ; 2E01: B7
    JNZ 2E08                ; 2E02: C2 08 2E
    LDA 2DBC                ; 2E05: 3A BC 2D
    STA 2CA4                ; 2E08: 32 A4 2C
    JMP 2D71                ; 2E0B: C3 71 2D
    SHLD 2CAA               ; 2E0E: 22 AA 2C
    SHLD 2D49               ; 2E11: 22 49 2D
    XCHG                    ; 2E14: EB
    SHLD 2D4F               ; 2E15: 22 4F 2D
    SHLD 2D35               ; 2E18: 22 35 2D
    MOV H, B                ; 2E1B: 60
    MOV L, C                ; 2E1C: 69
    SHLD 2CCB               ; 2E1D: 22 CB 2C
    XRA A                   ; 2E20: AF
    STA 2CA4                ; 2E21: 32 A4 2C
    STA 2D76                ; 2E24: 32 76 2D
    INR A                   ; 2E27: 3C
    STA 2DA9                ; 2E28: 32 A9 2D
    MVI A, 3E               ; 2E2B: 3E 3E
    STA 2CA3                ; 2E2D: 32 A3 2C
    MVI A, 76               ; 2E30: 3E 76
; OUT 08 ch2 init
label_ch2_ctl_1:
    OUT 08                  ; 2E32: D3 08
    MVI A, 06               ; 2E34: 3E 06
    STA 2D1F                ; 2E36: 32 1F 2D
    RET                     ; 2E39: C9
    MVI A, C9               ; 2E3A: 3E C9
    STA 2CA3                ; 2E3C: 32 A3 2C
    XRA A                   ; 2E3F: AF
    STA 2DA9                ; 2E40: 32 A9 2D
    MVI A, 76               ; 2E43: 3E 76
; OUT 08 ch2 init 2
label_ch2_ctl_2:
    OUT 08                  ; 2E45: D3 08
    RET                     ; 2E47: C9
    SHLD 2E50               ; 2E48: 22 50 2E
    XRA A                   ; 2E4B: AF
    STA 2E5F                ; 2E4C: 32 5F 2E
    LXI H, F042             ; 2E4F: 21 42 F0
    LDA 2DA9                ; 2E52: 3A A9 2D
    ORA A                   ; 2E55: B7
    JZ 2E5E                 ; 2E56: CA 5E 2E
    LDA 2D1F                ; 2E59: 3A 1F 2D
    SUI 06                  ; 2E5C: D6 06
    CPI 03                  ; 2E5E: FE 03
    RZ                      ; 2E60: C8
    JNC 2E75                ; 2E61: D2 75 2E
    LDA 2E5F                ; 2E64: 3A 5F 2E
    DCR A                   ; 2E67: 3D
    STA 2E5F                ; 2E68: 32 5F 2E
    DCR L                   ; 2E6B: 2D
    MVI M, 00               ; 2E6C: 36 00
    DCR L                   ; 2E6E: 2D
    MVI M, 00               ; 2E6F: 36 00
    SHLD 2E50               ; 2E71: 22 50 2E
    RET                     ; 2E74: C9
    LDA 2E5F                ; 2E75: 3A 5F 2E
    INR A                   ; 2E78: 3C
    STA 2E5F                ; 2E79: 32 5F 2E
    MVI M, 00               ; 2E7C: 36 00
    INR L                   ; 2E7E: 2C
    MVI M, 3C               ; 2E7F: 36 3C
    INR L                   ; 2E81: 2C
    SHLD 2E50               ; 2E82: 22 50 2E
    RET                     ; 2E85: C9
    MVI A, 0D               ; 2E86: 3E 0D
    ORA A                   ; 2E88: B7
    JNZ 2F54                ; 2E89: C2 54 2F
    LXI H, 3289             ; 2E8C: 21 89 32
    MOV A, M                ; 2E8F: 7E
    STA 2F02                ; 2E90: 32 02 2F
    INX H                   ; 2E93: 23
    ORA A                   ; 2E94: B7
    JZ 2FA4                 ; 2E95: CA A4 2F
    DCR A                   ; 2E98: 3D
    JZ 2F48                 ; 2E99: CA 48 2F
    DCR A                   ; 2E9C: 3D
    JZ 2F2B                 ; 2E9D: CA 2B 2F
    DCR A                   ; 2EA0: 3D
    JZ 2F3A                 ; 2EA1: CA 3A 2F
    DCR A                   ; 2EA4: 3D
    JZ 2F03                 ; 2EA5: CA 03 2F
    DCR A                   ; 2EA8: 3D
    JZ 2F1A                 ; 2EA9: CA 1A 2F
    XCHG                    ; 2EAC: EB
    LXI H, 3089             ; 2EAD: 21 89 30
    LXI B, 0002             ; 2EB0: 01 02 00
    DCR A                   ; 2EB3: 3D
    JZ 2EE6                 ; 2EB4: CA E6 2E
    DCR A                   ; 2EB7: 3D
    JZ 2EC0                 ; 2EB8: CA C0 2E
    DAD B                   ; 2EBB: 09
    DCR A                   ; 2EBC: 3D
    JNZ 2EBB                ; 2EBD: C2 BB 2E
    PUSH H                  ; 2EC0: E5
    POP B                   ; 2EC1: C1
    LDAX B                  ; 2EC2: 0A
    MOV L, A                ; 2EC3: 6F
    INX B                   ; 2EC4: 03
    LDAX B                  ; 2EC5: 0A
    MOV H, A                ; 2EC6: 67
    SHLD 2ECB               ; 2EC7: 22 CB 2E
    LXI H, 0A89             ; 2ECA: 21 89 0A
    XCHG                    ; 2ECD: EB
    MOV A, M                ; 2ECE: 7E
    INX H                   ; 2ECF: 23
    DCR A                   ; 2ED0: 3D
    STA 2E87                ; 2ED1: 32 87 2E
    MOV A, E                ; 2ED4: 7B
; OUT 09h (LSB counter 2)
label_ch2_out_lo:
    OUT 09                  ; 2ED5: D3 09
    MOV A, D                ; 2ED7: 7A
; OUT 09h (MSB counter 2)
label_ch2_out_hi:
    OUT 09                  ; 2ED8: D3 09
    SHLD 2E8D               ; 2EDA: 22 8D 2E
    XRA A                   ; 2EDD: AF
    STA 2F59                ; 2EDE: 32 59 2F
    INR A                   ; 2EE1: 3C
    STA 2F8C                ; 2EE2: 32 8C 2F
    RET                     ; 2EE5: C9
    LXI H, 0000             ; 2EE6: 21 00 00
    SHLD 2ECB               ; 2EE9: 22 CB 2E
    XCHG                    ; 2EEC: EB
    MOV A, M                ; 2EED: 7E
    INX H                   ; 2EEE: 23
    DCR A                   ; 2EEF: 3D
    STA 2E87                ; 2EF0: 32 87 2E
    XRA A                   ; 2EF3: AF
    STA 2F59                ; 2EF4: 32 59 2F
    STA 2F8C                ; 2EF7: 32 8C 2F
    MVI A, B6               ; 2EFA: 3E B6
; OUT 08 ch2
label_ch2_ctl_3:
    OUT 08                  ; 2EFC: D3 08
    SHLD 2E8D               ; 2EFE: 22 8D 2E
    RET                     ; 2F01: C9
    DAD B                   ; 2F02: 09
    MOV E, M                ; 2F03: 5E
    INX H                   ; 2F04: 23
    MOV D, M                ; 2F05: 56
    INX H                   ; 2F06: 23
    XCHG                    ; 2F07: EB
    SHLD 2E8D               ; 2F08: 22 8D 2E
    LHLD 2F18               ; 2F0B: 2A 18 2F
    MOV M, E                ; 2F0E: 73
    INX H                   ; 2F0F: 23
    MOV M, D                ; 2F10: 72
    INX H                   ; 2F11: 23
    SHLD 2F18               ; 2F12: 22 18 2F
    JMP 2E8C                ; 2F15: C3 8C 2E
    NOP                     ; 2F18: 08
    MOV A, M                ; 2F19: 7E
    LHLD 2F18               ; 2F1A: 2A 18 2F
    DCX H                   ; 2F1D: 2B
    MOV D, M                ; 2F1E: 56
    DCX H                   ; 2F1F: 2B
    MOV E, M                ; 2F20: 5E
    SHLD 2F18               ; 2F21: 22 18 2F
    XCHG                    ; 2F24: EB
    SHLD 2E8D               ; 2F25: 22 8D 2E
    JMP 2E8C                ; 2F28: C3 8C 2E
    LXI H, 3691             ; 2F2B: 21 91 36
    SHLD 2E8D               ; 2F2E: 22 8D 2E
    LXI H, 7E00             ; 2F31: 21 00 7E
    SHLD 2F18               ; 2F34: 22 18 2F
    JMP 2E8C                ; 2F37: C3 8C 2E
    MVI A, B6               ; 2F3A: 3E B6
; OUT 08 B6h mode word -- ch2 stop
label_ch2_release_ctl:
    OUT 08                  ; 2F3C: D3 08
    MVI A, C9               ; 2F3E: 3E C9
    STA 2E86                ; 2F40: 32 86 2E
    XRA A                   ; 2F43: AF
    STA 2F8C                ; 2F44: 32 8C 2F
    RET                     ; 2F47: C9
    MOV E, M                ; 2F48: 5E
    INX H                   ; 2F49: 23
    MOV D, M                ; 2F4A: 56
    INX H                   ; 2F4B: 23
    XCHG                    ; 2F4C: EB
    SHLD 2EAE               ; 2F4D: 22 AE 2E
    XCHG                    ; 2F50: EB
    JMP 2E8F                ; 2F51: C3 8F 2E
    DCR A                   ; 2F54: 3D
    STA 2E87                ; 2F55: 32 87 2E
    MVI A, 01               ; 2F58: 3E 01
    ORA A                   ; 2F5A: B7
    RZ                      ; 2F5B: C8
    LXI H, 31A6             ; 2F5C: 21 A6 31
    MVI A, 00               ; 2F5F: 3E 00
    ORA A                   ; 2F61: B7
    CZ 2F98                 ; 2F62: CC 98 2F
    DCR A                   ; 2F65: 3D
    STA 2F60                ; 2F66: 32 60 2F
    MOV E, M                ; 2F69: 5E
    MOV C, M                ; 2F6A: 4E
    INX H                   ; 2F6B: 23
    MOV D, M                ; 2F6C: 56
    INX H                   ; 2F6D: 23
    SHLD 2F5D               ; 2F6E: 22 5D 2F
    MOV A, D                ; 2F71: 7A
    INR C                   ; 2F72: 0C
    INR A                   ; 2F73: 3C
    ORA C                   ; 2F74: B1
    JZ 2F8B                 ; 2F75: CA 8B 2F
    LXI H, 5395             ; 2F78: 21 95 53
    DAD D                   ; 2F7B: 19
    SHLD 2F79               ; 2F7C: 22 79 2F
    MOV A, L                ; 2F7F: 7D
; OUT 09,lo / OUT 09,hi sweep
label_ch2_sweep_lohi:
    OUT 09                  ; 2F80: D3 09
    MOV A, H                ; 2F82: 7C
    OUT 09                  ; 2F83: D3 09
    XRA A                   ; 2F85: AF
    INR A                   ; 2F86: 3C
    STA 2F8C                ; 2F87: 32 8C 2F
    RET                     ; 2F8A: C9
    MVI A, 01               ; 2F8B: 3E 01
    ORA A                   ; 2F8D: B7
    RZ                      ; 2F8E: C8
    DCR A                   ; 2F8F: 3D
    STA 2F8C                ; 2F90: 32 8C 2F
    MVI A, B6               ; 2F93: 3E B6
; OUT 08 ch2 sweep control
label_ch2_sweep_ctl:
    OUT 08                  ; 2F95: D3 08
    RET                     ; 2F97: C9
    LXI H, 31A4             ; 2F98: 21 A4 31
    SHLD 2F5D               ; 2F9B: 22 5D 2F
    MVI A, 01               ; 2F9E: 3E 01
    STA 2F60                ; 2FA0: 32 60 2F
    RET                     ; 2FA3: C9
    MOV E, M                ; 2FA4: 5E
    INX H                   ; 2FA5: 23
    MOV D, M                ; 2FA6: 56
    INX H                   ; 2FA7: 23
    XCHG                    ; 2FA8: EB
    MOV A, M                ; 2FA9: 7E
    INX H                   ; 2FAA: 23
    STA 2F9F                ; 2FAB: 32 9F 2F
    SHLD 2F99               ; 2FAE: 22 99 2F
    CALL 2F98               ; 2FB1: CD 98 2F
    XCHG                    ; 2FB4: EB
    MOV A, M                ; 2FB5: 7E
    STA 2F02                ; 2FB6: 32 02 2F
    INX H                   ; 2FB9: 23
    SUI 06                  ; 2FBA: D6 06
    XCHG                    ; 2FBC: EB
    LHLD 2EAE               ; 2FBD: 2A AE 2E
    LXI B, 0002             ; 2FC0: 01 02 00
    DCR A                   ; 2FC3: 3D
    JZ 2FCC                 ; 2FC4: CA CC 2F
    DAD B                   ; 2FC7: 09
    DCR A                   ; 2FC8: 3D
    JNZ 2FC7                ; 2FC9: C2 C7 2F
    PUSH H                  ; 2FCC: E5
    POP B                   ; 2FCD: C1
    LDAX B                  ; 2FCE: 0A
    MOV L, A                ; 2FCF: 6F
    INX B                   ; 2FD0: 03
    LDAX B                  ; 2FD1: 0A
    MOV H, A                ; 2FD2: 67
    SHLD 2ECB               ; 2FD3: 22 CB 2E
    SHLD 2F79               ; 2FD6: 22 79 2F
    XCHG                    ; 2FD9: EB
    XRA A                   ; 2FDA: AF
    INR A                   ; 2FDB: 3C
    STA 2F59                ; 2FDC: 32 59 2F
    MOV A, M                ; 2FDF: 7E
    INX H                   ; 2FE0: 23
    SHLD 2E8D               ; 2FE1: 22 8D 2E
    ORA A                   ; 2FE4: B7
    JNZ 2FEB                ; 2FE5: C2 EB 2F
    LDA 2F9F                ; 2FE8: 3A 9F 2F
    STA 2E87                ; 2FEB: 32 87 2E
    JMP 2F54                ; 2FEE: C3 54 2F
    SHLD 2E8D               ; 2FF1: 22 8D 2E
    SHLD 2F2C               ; 2FF4: 22 2C 2F
    XCHG                    ; 2FF7: EB
    SHLD 2F32               ; 2FF8: 22 32 2F
    SHLD 2F18               ; 2FFB: 22 18 2F
    MOV H, B                ; 2FFE: 60
    MOV L, C                ; 2FFF: 69
    SHLD 2EAE               ; 3000: 22 AE 2E
    XRA A                   ; 3003: AF
    STA 2E87                ; 3004: 32 87 2E
    STA 2F59                ; 3007: 32 59 2F
    INR A                   ; 300A: 3C
    STA 2F8C                ; 300B: 32 8C 2F
    MVI A, 3E               ; 300E: 3E 3E
    STA 2E86                ; 3010: 32 86 2E
    MVI A, B6               ; 3013: 3E B6
; OUT 08 tail control
label_end_ctl_1:
    OUT 08                  ; 3015: D3 08
    MVI A, 06               ; 3017: 3E 06
    STA 2F02                ; 3019: 32 02 2F
    RET                     ; 301C: C9
    MVI A, C9               ; 301D: 3E C9
    STA 2E86                ; 301F: 32 86 2E
    XRA A                   ; 3022: AF
    STA 2F8C                ; 3023: 32 8C 2F
    MVI A, B6               ; 3026: 3E B6
; OUT 08 tail control 2
label_end_ctl_2:
    OUT 08                  ; 3028: D3 08
    RET                     ; 302A: C9
    SHLD 3033               ; 302B: 22 33 30
    XRA A                   ; 302E: AF
    STA 3042                ; 302F: 32 42 30
    LXI H, F142             ; 3032: 21 42 F1
    LDA 2F8C                ; 3035: 3A 8C 2F
    ORA A                   ; 3038: B7
    JZ 3041                 ; 3039: CA 41 30
    LDA 2F02                ; 303C: 3A 02 2F
    SUI 06                  ; 303F: D6 06
    CPI 03                  ; 3041: FE 03
    RZ                      ; 3043: C8
    JNC 3058                ; 3044: D2 58 30
    LDA 3042                ; 3047: 3A 42 30
    DCR A                   ; 304A: 3D
    STA 3042                ; 304B: 32 42 30
    DCR L                   ; 304E: 2D
    MVI M, 00               ; 304F: 36 00
    DCR L                   ; 3051: 2D
    MVI M, 00               ; 3052: 36 00
    SHLD 3033               ; 3054: 22 33 30
    RET                     ; 3057: C9
    LDA 3042                ; 3058: 3A 42 30
    INR A                   ; 305B: 3C
    STA 3042                ; 305C: 32 42 30
    MVI M, 00               ; 305F: 36 00
    INR L                   ; 3061: 2C
    MVI M, 3C               ; 3062: 36 3C
    INR L                   ; 3064: 2C
    SHLD 3033               ; 3065: 22 33 30
    RET                     ; 3068: C9

; --- Code range 37A8..3D29 (1410 bytes) ---
; Entry after unpacker; DI, XRA A, OUT 10h, zero 0100..0102, LXI SP,7FFF, CALL func_vi53_mode_setup, install vectors, enter HLT loop
func_main_entry:
    DI                      ; 37A8: F3
    XRA A                   ; 37A9: AF
    OUT 10                  ; 37AA: D3 10
    STA 0100                ; 37AC: 32 00 01
    STA 0101                ; 37AF: 32 01 01
    STA 0102                ; 37B2: 32 02 01
    LXI SP, 7FFF            ; 37B5: 31 FF 7F
    CALL 3892               ; 37B8: CD 92 38
; Write JMP opcode (C3h) to 0000h and 0038h; SHLD target addrs
label_install_vectors:
    MVI A, C3               ; 37BB: 3E C3
    STA 0000                ; 37BD: 32 00 00
    STA 0038                ; 37C0: 32 38 00
    LXI H, 37A8             ; 37C3: 21 A8 37
    SHLD 0001               ; 37C6: 22 01 00
    LXI H, 394B             ; 37C9: 21 4B 39
    SHLD 0039               ; 37CC: 22 39 00
; CALL func_sys_init; enter main loop
label_call_init_and_halt:
    CALL 389F               ; 37CF: CD 9F 38
; Main: LXI H,2977 -- glyph table base
label_main_prepare:
    LXI H, 2977             ; 37D2: 21 77 29
    MVI A, 07               ; 37D5: 3E 07
    MVI B, 7A               ; 37D7: 06 7A
    CALL 392A               ; 37D9: CD 2A 39
    LXI H, A334             ; 37DC: 21 34 A3
    LXI D, 0100             ; 37DF: 11 00 01
    LXI B, 1A20             ; 37E2: 01 20 1A
    MVI A, 03               ; 37E5: 3E 03
; CALL func_stamp_vram_banks -- first VRAM stamp
label_boot_stamp1:
    CALL 3AE7               ; 37E7: CD E7 3A
    LXI H, 8383             ; 37EA: 21 83 83
    LXI D, 0AC0             ; 37ED: 11 C0 0A
    LXI B, 1A49             ; 37F0: 01 49 1A
    CALL 3AE5               ; 37F3: CD E5 3A
    LXI H, 8464             ; 37F6: 21 64 84
    LXI D, 2868             ; 37F9: 11 68 28
    LXI B, 010F             ; 37FC: 01 0F 01
    CALL 3AE5               ; 37FF: CD E5 3A
    LXI H, 9B64             ; 3802: 21 64 9B
    LXI D, 28E0             ; 3805: 11 E0 28
    LXI B, 010F             ; 3808: 01 0F 01
    CALL 3AE5               ; 380B: CD E5 3A
    LXI H, 8564             ; 380E: 21 64 85
    LXI D, 28A4             ; 3811: 11 A4 28
    LXI B, 010F             ; 3814: 01 0F 01
    MVI A, 16               ; 3817: 3E 16
    PUSH PSW                ; 3819: F5
    PUSH H                  ; 381A: E5
    PUSH D                  ; 381B: D5
    PUSH B                  ; 381C: C5
    CALL 3AE5               ; 381D: CD E5 3A
    POP B                   ; 3820: C1
    POP D                   ; 3821: D1
    POP H                   ; 3822: E1
    POP PSW                 ; 3823: F1
    INR H                   ; 3824: 24
    DCR A                   ; 3825: 3D
    JNZ 3819                ; 3826: C2 19 38
    CALL 382F               ; 3829: CD 2F 38
    JMP 3848                ; 382C: C3 48 38
    XRA A                   ; 382F: AF
    STA 3C17                ; 3830: 32 17 3C
; CALL func_melody_frame -- song loop entry
label_melody_start:
    CALL 3BFE               ; 3833: CD FE 3B
    LXI H, 9A68             ; 3836: 21 68 9A
    LXI D, 3D2A             ; 3839: 11 2A 3D
    MVI B, 16               ; 383C: 06 16
    MVI C, 7A               ; 383E: 0E 7A
    MVI A, 07               ; 3840: 3E 07
    CALL 38C1               ; 3842: CD C1 38
    JMP 3BCB                ; 3845: C3 CB 3B
    LXI H, 3B99             ; 3848: 21 99 3B
    CALL 3C2D               ; 384B: CD 2D 3C
    LXI H, 3B89             ; 384E: 21 89 3B
    CALL 3C2D               ; 3851: CD 2D 3C
    LXI H, 3B79             ; 3854: 21 79 3B
    CALL 3C2D               ; 3857: CD 2D 3C
    LXI H, 3B69             ; 385A: 21 69 3B
    CALL 3C2D               ; 385D: CD 2D 3C
    LDA 3C17                ; 3860: 3A 17 3C
    ORA A                   ; 3863: B7
    JNZ 3C7F                ; 3864: C2 7F 3C
    HLT                     ; 3867: 76
    CALL 3BCB               ; 3868: CD CB 3B
    CALL 3BFE               ; 386B: CD FE 3B
    CALL 3C44               ; 386E: CD 44 3C
    LDA 3C78                ; 3871: 3A 78 3C
    CPI 3A                  ; 3874: FE 3A
    JNZ 3860                ; 3876: C2 60 38
    LXI H, 3B79             ; 3879: 21 79 3B
    CALL 3C2D               ; 387C: CD 2D 3C
    LXI H, 3B89             ; 387F: 21 89 3B
    CALL 3C2D               ; 3882: CD 2D 3C
    LXI H, 3B99             ; 3885: 21 99 3B
    CALL 3C2D               ; 3888: CD 2D 3C
    LXI H, 39BA             ; 388B: 21 BA 39
    CALL 3C2D               ; 388E: CD 2D 3C
    RST 00                  ; 3891: C7
; MVI A,36h;OUT 08h; MVI A,76h;OUT 08h; MVI A,B6h;OUT 08h; RET  -- mode 3 square wave, RW=11 both bytes on ch0/ch1/ch2
func_vi53_mode_setup:
    MVI A, 36               ; 3892: 3E 36
    OUT 08                  ; 3894: D3 08
    MVI A, 76               ; 3896: 3E 76
    OUT 08                  ; 3898: D3 08
    MVI A, B6               ; 389A: 3E B6
    OUT 08                  ; 389C: D3 08
    RET                     ; 389E: C9
; LXI H,39BA; SHLD 3979; EI; HLT -- set stream base, wait for VBlank
func_sys_init:
    LXI H, 39BA             ; 389F: 21 BA 39
    SHLD 3979               ; 38A2: 22 79 39
    EI                      ; 38A5: FB
    HLT                     ; 38A6: 76
; Save SP to 38BE, LXI B,4000 (aux init path)
func_alt_init_save_sp:
    DI                      ; 38A7: F3
    LXI H, 0000             ; 38A8: 21 00 00
    DAD SP                  ; 38AB: 39
    SHLD 38BE               ; 38AC: 22 BE 38
    LXI H, 0000             ; 38AF: 21 00 00
    SPHL                    ; 38B2: F9
    LXI B, 4000             ; 38B3: 01 00 40
    PUSH H                  ; 38B6: E5
    DCX B                   ; 38B7: 0B
    MOV A, B                ; 38B8: 78
    ORA C                   ; 38B9: B1
    JNZ 38B6                ; 38BA: C2 B6 38
    LXI SP, 7FFD            ; 38BD: 31 FD 7F
    RET                     ; 38C0: C9
    STA 38F1                ; 38C1: 32 F1 38
    STA 3913                ; 38C4: 32 13 39
    SHLD 390D               ; 38C7: 22 0D 39
    XCHG                    ; 38CA: EB
    SHLD 38D7               ; 38CB: 22 D7 38
    MOV A, B                ; 38CE: 78
    STA 391A                ; 38CF: 32 1A 39
    MOV A, C                ; 38D2: 79
    STA 38E9                ; 38D3: 32 E9 38
    LXI H, 3D2A             ; 38D6: 21 2A 3D
    SHLD 38DD               ; 38D9: 22 DD 38
    LXI H, 3D50             ; 38DC: 21 50 3D
    MOV A, M                ; 38DF: 7E
    ORA A                   ; 38E0: B7
    JZ 38D6                 ; 38E1: CA D6 38
    INX H                   ; 38E4: 23
    SHLD 38DD               ; 38E5: 22 DD 38
    MVI D, 7A               ; 38E8: 16 7A
    MOV E, A                ; 38EA: 5F
    LDAX D                  ; 38EB: 1A
    MOV L, A                ; 38EC: 6F
    INR D                   ; 38ED: 14
    LDAX D                  ; 38EE: 1A
    MOV H, A                ; 38EF: 67
    MVI E, 07               ; 38F0: 1E 07
    LXI B, 393B             ; 38F2: 01 3B 39
    MOV A, M                ; 38F5: 7E
    STAX B                  ; 38F6: 02
    INX H                   ; 38F7: 23
    INX B                   ; 38F8: 03
    DCR E                   ; 38F9: 1D
    JNZ 38F5                ; 38FA: C2 F5 38
    MVI A, 09               ; 38FD: 3E 09
    STA 3903                ; 38FF: 32 03 39
    MVI A, 01               ; 3902: 3E 01
    DCR A                   ; 3904: 3D
    STA 3903                ; 3905: 32 03 39
    ORA A                   ; 3908: B7
    JZ 38DC                 ; 3909: CA DC 38
    LXI H, 9A68             ; 390C: 21 68 9A
    LXI B, 393B             ; 390F: 01 3B 39
    MVI D, 07               ; 3912: 16 07
    PUSH H                  ; 3914: E5
    LDAX B                  ; 3915: 0A
    RLC                     ; 3916: 07
    STAX B                  ; 3917: 02
    INX B                   ; 3918: 03
    MVI E, 16               ; 3919: 1E 16
    MOV A, M                ; 391B: 7E
    RAL                     ; 391C: 17
    MOV M, A                ; 391D: 77
    DCR H                   ; 391E: 25
    DCR E                   ; 391F: 1D
    JNZ 391B                ; 3920: C2 1B 39
    POP H                   ; 3923: E1
    INR L                   ; 3924: 2C
    DCR D                   ; 3925: 15
    JNZ 3914                ; 3926: C2 14 39
    RET                     ; 3929: C9
    MOV E, A                ; 392A: 5F
    MVI D, 00               ; 392B: 16 00
    MVI C, 01               ; 392D: 0E 01
    MOV A, L                ; 392F: 7D
    STAX B                  ; 3930: 02
    INR B                   ; 3931: 04
    MOV A, H                ; 3932: 7C
    STAX B                  ; 3933: 02
    DCR B                   ; 3934: 05
    DAD D                   ; 3935: 19
    INR C                   ; 3936: 0C
    JNZ 392F                ; 3937: C2 2F 39
    RET                     ; 393A: C9
    ANI E6                  ; 393B: E6 E6
    ANI FC                  ; 393D: E6 FC
    ANI E6                  ; 393F: E6 E6
    ANI 00                  ; 3941: E6 00
    NOP                     ; 3943: 00
    NOP                     ; 3944: 00
    NOP                     ; 3945: 00
    NOP                     ; 3946: 00
    NOP                     ; 3947: 00
    NOP                     ; 3948: 00
    NOP                     ; 3949: 00
    NOP                     ; 394A: 00
; RST 7 handler: PUSH H/D/B/PSW, keyboard matrix scan (OUT 00h=8Ah, row strobe via 03h, read 02h, 8 rows stored at 39BB+), then palette rampa via 0Ch
func_irq_vblank:
    PUSH H                  ; 394B: E5
    PUSH D                  ; 394C: D5
    PUSH B                  ; 394D: C5
    PUSH PSW                ; 394E: F5
    LXI H, 39C3             ; 394F: 21 C3 39
    MVI A, 8A               ; 3952: 3E 8A
    OUT 00                  ; 3954: D3 00
    LXI D, 39BB             ; 3956: 11 BB 39
    MVI C, 08               ; 3959: 0E 08
    LDAX D                  ; 395B: 1A
    OUT 03                  ; 395C: D3 03
    IN 02                   ; 395E: DB 02
    MOV M, A                ; 3960: 77
    INX H                   ; 3961: 23
    INX D                   ; 3962: 13
    DCR C                   ; 3963: 0D
    JNZ 395B                ; 3964: C2 5B 39
; After matrix scan; continue with palette update
label_kbd_done_xra:
    XRA A                   ; 3967: AF
    OUT 07                  ; 3968: D3 07
    IN 07                   ; 396A: DB 07
    STA 39A9                ; 396C: 32 A9 39
    MVI A, 88               ; 396F: 3E 88
    OUT 00                  ; 3971: D3 00
    IN 01                   ; 3973: DB 01
    STA 39AA                ; 3975: 32 AA 39
    LXI H, 3B69             ; 3978: 21 69 3B
    LXI D, 100F             ; 397B: 11 0F 10
    MOV A, E                ; 397E: 7B
    OUT 02                  ; 397F: D3 02
    MOV A, M                ; 3981: 7E
    NOP                     ; 3982: 00
    OUT 0C                  ; 3983: D3 0C
    OUT 0C                  ; 3985: D3 0C
    OUT 0C                  ; 3987: D3 0C
    OUT 0C                  ; 3989: D3 0C
    DCX H                   ; 398B: 2B
    OUT 0C                  ; 398C: D3 0C
    DCR E                   ; 398E: 1D
    OUT 0C                  ; 398F: D3 0C
    DCR D                   ; 3991: 15
    OUT 0C                  ; 3992: D3 0C
    JNZ 397E                ; 3994: C2 7E 39
    MVI A, FF               ; 3997: 3E FF
    OUT 03                  ; 3999: D3 03
    MVI A, 00               ; 399B: 3E 00
    OUT 02                  ; 399D: D3 02
    MVI A, 00               ; 399F: 3E 00
    OUT 01                  ; 39A1: D3 01
    POP PSW                 ; 39A3: F1
    POP B                   ; 39A4: C1
    POP D                   ; 39A5: D1
    POP H                   ; 39A6: E1
    EI                      ; 39A7: FB
    RET                     ; 39A8: C9
    NOP                     ; 39A9: 00
    RPO                     ; 39AA: E0
    NOP                     ; 39AB: 00
    NOP                     ; 39AC: 00
    NOP                     ; 39AD: 00
    NOP                     ; 39AE: 00
    NOP                     ; 39AF: 00
    NOP                     ; 39B0: 00
    NOP                     ; 39B1: 00
    NOP                     ; 39B2: 00
    NOP                     ; 39B3: 00
    NOP                     ; 39B4: 00
    NOP                     ; 39B5: 00
    NOP                     ; 39B6: 00
    NOP                     ; 39B7: 00
    NOP                     ; 39B8: 00
    NOP                     ; 39B9: 00
    NOP                     ; 39BA: 00
    CPI FB                  ; 39BB: FE FB
    RST 30                  ; 39BD: F7
    RST 28                  ; 39BE: EF
    RST 18                  ; 39BF: DF
    CMP A                   ; 39C0: BF
    MOV A, A                ; 39C1: 7F
    DB FD                   ; 39C2: FD
    RST 38                  ; 39C3: FF
    RST 38                  ; 39C4: FF
    RST 38                  ; 39C5: FF
    RST 38                  ; 39C6: FF
    RST 38                  ; 39C7: FF
    RST 38                  ; 39C8: FF
    RST 38                  ; 39C9: FF
    RST 38                  ; 39CA: FF
    MVI C, 01               ; 39CB: 0E 01
    ANI 08                  ; 39CD: E6 08
    RNZ                     ; 39CF: C0
    MVI C, FF               ; 39D0: 0E FF
    RET                     ; 39D2: C9
    MVI C, FA               ; 39D3: 0E FA
    ANI 10                  ; 39D5: E6 10
    RNZ                     ; 39D7: C0
    MVI C, F8               ; 39D8: 0E F8
    ANI 40                  ; 39DA: E6 40
    RNZ                     ; 39DC: C0
    MVI C, FF               ; 39DD: 0E FF
    RET                     ; 39DF: C9
    MVI C, F9               ; 39E0: 0E F9
    ANI 80                  ; 39E2: E6 80
    RNZ                     ; 39E4: C0
    MVI C, F7               ; 39E5: 0E F7
    ANI 20                  ; 39E7: E6 20
    RNZ                     ; 39E9: C0
    MVI C, FF               ; 39EA: 0E FF
    RET                     ; 39EC: C9
    MVI A, 00               ; 39ED: 3E 00
    ORA A                   ; 39EF: B7
    LDA 39A9                ; 39F0: 3A A9 39
    JZ 3A36                 ; 39F3: CA 36 3A
    CALL 3ABB               ; 39F6: CD BB 3A
    MOV A, C                ; 39F9: 79
    CPI FF                  ; 39FA: FE FF
    CZ 3A6B                 ; 39FC: CC 6B 3A
    STA 3A66                ; 39FF: 32 66 3A
    CALL 3A84               ; 3A02: CD 84 3A
    STA 3A6A                ; 3A05: 32 6A 3A
    LDA 39A9                ; 3A08: 3A A9 39
    CALL 3AC3               ; 3A0B: CD C3 3A
    MOV A, C                ; 3A0E: 79
    CPI FF                  ; 3A0F: FE FF
    CZ 3A79                 ; 3A11: CC 79 3A
    STA 3A67                ; 3A14: 32 67 3A
    LDA 39A9                ; 3A17: 3A A9 39
    CALL 3AD8               ; 3A1A: CD D8 3A
    MOV A, C                ; 3A1D: 79
    CPI FF                  ; 3A1E: FE FF
    CZ 3A8F                 ; 3A20: CC 8F 3A
    STA 3A68                ; 3A23: 32 68 3A
    LDA 39A9                ; 3A26: 3A A9 39
    CALL 3ACB               ; 3A29: CD CB 3A
    MOV A, C                ; 3A2C: 79
    CPI FF                  ; 3A2D: FE FF
    CZ 3AA5                 ; 3A2F: CC A5 3A
    STA 3A69                ; 3A32: 32 69 3A
    RET                     ; 3A35: C9
    CALL 39CB               ; 3A36: CD CB 39
    MOV A, C                ; 3A39: 79
    CPI FF                  ; 3A3A: FE FF
    CZ 3A6B                 ; 3A3C: CC 6B 3A
    STA 3A66                ; 3A3F: 32 66 3A
    CALL 3A79               ; 3A42: CD 79 3A
    STA 3A67                ; 3A45: 32 67 3A
    CALL 3A84               ; 3A48: CD 84 3A
    STA 3A6A                ; 3A4B: 32 6A 3A
    LDA 39A9                ; 3A4E: 3A A9 39
    CALL 39E0               ; 3A51: CD E0 39
    MOV A, C                ; 3A54: 79
    CPI FF                  ; 3A55: FE FF
    CZ 3A8F                 ; 3A57: CC 8F 3A
    STA 3A68                ; 3A5A: 32 68 3A
    LDA 39A9                ; 3A5D: 3A A9 39
    CALL 39D3               ; 3A60: CD D3 39
    JMP 3A2C                ; 3A63: C3 2C 3A
    NOP                     ; 3A66: 00
    NOP                     ; 3A67: 00
    NOP                     ; 3A68: 00
    NOP                     ; 3A69: 00
    NOP                     ; 3A6A: 00
    LDA 39C9                ; 3A6B: 3A C9 39
    ANI 80                  ; 3A6E: E6 80
    JNZ 3A76                ; 3A70: C2 76 3A
    MVI A, 01               ; 3A73: 3E 01
    RET                     ; 3A75: C9
    MVI A, FF               ; 3A76: 3E FF
    RET                     ; 3A78: C9
    LDA 39CA                ; 3A79: 3A CA 39
    ANI 04                  ; 3A7C: E6 04
    JNZ 3A76                ; 3A7E: C2 76 3A
    MVI A, 02               ; 3A81: 3E 02
    RET                     ; 3A83: C9
    LDA 39C3                ; 3A84: 3A C3 39
    ANI 04                  ; 3A87: E6 04
    JNZ 3A76                ; 3A89: C2 76 3A
    MVI A, 03               ; 3A8C: 3E 03
    RET                     ; 3A8E: C9
    LDA 39C3                ; 3A8F: 3A C3 39
    ANI 80                  ; 3A92: E6 80
    JZ 3AA2                 ; 3A94: CA A2 3A
    LDA 39C3                ; 3A97: 3A C3 39
    ANI 20                  ; 3A9A: E6 20
    JNZ 3A76                ; 3A9C: C2 76 3A
    MVI A, F9               ; 3A9F: 3E F9
    RET                     ; 3AA1: C9
    MVI A, F7               ; 3AA2: 3E F7
    RET                     ; 3AA4: C9
    LDA 39C3                ; 3AA5: 3A C3 39
    ANI 10                  ; 3AA8: E6 10
    JZ 3AB8                 ; 3AAA: CA B8 3A
    LDA 39C3                ; 3AAD: 3A C3 39
    ANI 40                  ; 3AB0: E6 40
    JNZ 3A76                ; 3AB2: C2 76 3A
    MVI A, F8               ; 3AB5: 3E F8
    RET                     ; 3AB7: C9
    MVI A, FA               ; 3AB8: 3E FA
    RET                     ; 3ABA: C9
    MVI C, 01               ; 3ABB: 0E 01
    ANI 20                  ; 3ABD: E6 20
    RNZ                     ; 3ABF: C0
    MVI C, FF               ; 3AC0: 0E FF
    RET                     ; 3AC2: C9
    MVI C, 02               ; 3AC3: 0E 02
    ANI 40                  ; 3AC5: E6 40
    RNZ                     ; 3AC7: C0
    MVI C, FF               ; 3AC8: 0E FF
    RET                     ; 3ACA: C9
    MVI C, FA               ; 3ACB: 0E FA
    ANI 10                  ; 3ACD: E6 10
    RNZ                     ; 3ACF: C0
    MVI C, F8               ; 3AD0: 0E F8
    ANI 04                  ; 3AD2: E6 04
    RNZ                     ; 3AD4: C0
    MVI C, FF               ; 3AD5: 0E FF
    RET                     ; 3AD7: C9
    MVI C, F9               ; 3AD8: 0E F9
    ANI 01                  ; 3ADA: E6 01
    RNZ                     ; 3ADC: C0
    MVI C, F7               ; 3ADD: 0E F7
    ANI 08                  ; 3ADF: E6 08
    RNZ                     ; 3AE1: C0
    MVI C, FF               ; 3AE2: 0E FF
    RET                     ; 3AE4: C9
; DE->HL copy with nested B,C counters; stamps bytes across VRAM banks (HL advances by INR L, outer loop INR H)
func_stamp_vram_banks:
    MVI A, 04               ; 3AE5: 3E 04
; Variant entry: MVI A,04h sets bank count in PSW before entering shared body
func_stamp_vram_banks_alt:
    PUSH PSW                ; 3AE7: F5
    PUSH H                  ; 3AE8: E5
    PUSH B                  ; 3AE9: C5
    PUSH H                  ; 3AEA: E5
    PUSH B                  ; 3AEB: C5
    LDAX D                  ; 3AEC: 1A
    MOV M, A                ; 3AED: 77
    INR L                   ; 3AEE: 2C
    INX D                   ; 3AEF: 13
    DCR C                   ; 3AF0: 0D
    JNZ 3AEC                ; 3AF1: C2 EC 3A
    POP B                   ; 3AF4: C1
    POP H                   ; 3AF5: E1
    INR H                   ; 3AF6: 24
    DCR B                   ; 3AF7: 05
    JNZ 3AEA                ; 3AF8: C2 EA 3A
    POP B                   ; 3AFB: C1
    POP H                   ; 3AFC: E1
    MOV A, H                ; 3AFD: 7C
    ADI 20                  ; 3AFE: C6 20
    MOV H, A                ; 3B00: 67
    POP PSW                 ; 3B01: F1
    DCR A                   ; 3B02: 3D
    JNZ 3AE7                ; 3B03: C2 E7 3A
    RET                     ; 3B06: C9
    LXI H, 39C3             ; 3B07: 21 C3 39
    XRA A                   ; 3B0A: AF
    MOV E, A                ; 3B0B: 5F
    DCR A                   ; 3B0C: 3D
    MOV D, A                ; 3B0D: 57
    MVI B, 08               ; 3B0E: 06 08
    MOV C, B                ; 3B10: 48
    MOV A, M                ; 3B11: 7E
    INX H                   ; 3B12: 23
    CMP D                   ; 3B13: BA
    JNZ 3B21                ; 3B14: C2 21 3B
    MOV A, E                ; 3B17: 7B
    ADD B                   ; 3B18: 80
    MOV E, A                ; 3B19: 5F
    DCR C                   ; 3B1A: 0D
    JNZ 3B11                ; 3B1B: C2 11 3B
    XRA A                   ; 3B1E: AF
    DCR A                   ; 3B1F: 3D
    RET                     ; 3B20: C9
    MOV D, A                ; 3B21: 57
    DCR C                   ; 3B22: 0D
    JZ 3B30                 ; 3B23: CA 30 3B
    MOV A, M                ; 3B26: 7E
    CPI FF                  ; 3B27: FE FF
    INX H                   ; 3B29: 23
    JZ 3B22                 ; 3B2A: CA 22 3B
    XRA A                   ; 3B2D: AF
    DCR A                   ; 3B2E: 3D
    RET                     ; 3B2F: C9
    MOV A, D                ; 3B30: 7A
    CALL 3B37               ; 3B31: CD 37 3B
    MOV A, E                ; 3B34: 7B
    ADD C                   ; 3B35: 81
    RET                     ; 3B36: C9
    CPI FE                  ; 3B37: FE FE
    RZ                      ; 3B39: C8
    INR C                   ; 3B3A: 0C
    CPI FD                  ; 3B3B: FE FD
    RZ                      ; 3B3D: C8
    INR C                   ; 3B3E: 0C
    CPI FB                  ; 3B3F: FE FB
    RZ                      ; 3B41: C8
    INR C                   ; 3B42: 0C
    CPI F7                  ; 3B43: FE F7
    RZ                      ; 3B45: C8
    INR C                   ; 3B46: 0C
    CPI EF                  ; 3B47: FE EF
    RZ                      ; 3B49: C8
    INR C                   ; 3B4A: 0C
    CPI DF                  ; 3B4B: FE DF
    RZ                      ; 3B4D: C8
    INR C                   ; 3B4E: 0C
    CPI BF                  ; 3B4F: FE BF
    RZ                      ; 3B51: C8
    INR C                   ; 3B52: 0C
    CPI 7F                  ; 3B53: FE 7F
    RZ                      ; 3B55: C8
    POP H                   ; 3B56: E1
    XRA A                   ; 3B57: AF
    DCR A                   ; 3B58: 3D
    RET                     ; 3B59: C9
    NOP                     ; 3B5A: 00
    SHLD C0D0               ; 3B5B: 22 D0 C0
    ADD B                   ; 3B5E: 80
    STAX D                  ; 3B5F: 12
    MOV D, D                ; 3B60: 52
    MOV B, B                ; 3B61: 40
    RLC                     ; 3B62: 07
    MVI B, 05               ; 3B63: 06 05
    INR B                   ; 3B65: 04
    INR B                   ; 3B66: 04
    RLC                     ; 3B67: 07
    ADD M                   ; 3B68: 86
    XRA L                   ; 3B69: AD
    NOP                     ; 3B6A: 00
    NOP                     ; 3B6B: 10
    ADD B                   ; 3B6C: 80
    ADD B                   ; 3B6D: 80
    MOV B, B                ; 3B6E: 40
    DCR B                   ; 3B6F: 05
    ADD B                   ; 3B70: 80
    MOV B, B                ; 3B71: 40
    DCR B                   ; 3B72: 05
    INR B                   ; 3B73: 04
    INX B                   ; 3B74: 03
    STAX B                  ; 3B75: 02
    STAX B                  ; 3B76: 02
    DCR B                   ; 3B77: 05
    DCR B                   ; 3B78: 05
    MOV D, D                ; 3B79: 52
    NOP                     ; 3B7A: 00
    NOP                     ; 3B7B: 08
    MOV B, B                ; 3B7C: 40
    MOV B, B                ; 3B7D: 40
    MOV B, B                ; 3B7E: 40
    STAX B                  ; 3B7F: 02
    MOV B, B                ; 3B80: 40
    MOV B, B                ; 3B81: 40
    STAX B                  ; 3B82: 02
    LXI B, 0101             ; 3B83: 01 01 01
    LXI B, 0202             ; 3B86: 01 02 02
    ADD B                   ; 3B89: 80
    NOP                     ; 3B8A: 00
    NOP                     ; 3B8B: 08
    MOV B, B                ; 3B8C: 40
    MOV B, B                ; 3B8D: 40
    MOV B, B                ; 3B8E: 40
    LXI B, 4040             ; 3B8F: 01 40 40
    LXI B, 0101             ; 3B92: 01 01 01
    LXI B, 0101             ; 3B95: 01 01 01
    LXI B, 0E40             ; 3B98: 01 40 0E
    MVI D, 7E               ; 3B9B: 16 7E
    STAX D                  ; 3B9D: 12
    INR D                   ; 3B9E: 14
    INR H                   ; 3B9F: 24
    DCR C                   ; 3BA0: 0D
    JNZ 3B9C                ; 3BA1: C2 9C 3B
    MVI H, 85               ; 3BA4: 26 85
    INR L                   ; 3BA6: 2C
    RET                     ; 3BA7: C9
    LXI H, 8568             ; 3BA8: 21 68 85
    LXI D, A568             ; 3BAB: 11 68 A5
    CALL 3B9A               ; 3BAE: CD 9A 3B
    LXI D, C569             ; 3BB1: 11 69 C5
    CALL 3B9A               ; 3BB4: CD 9A 3B
    LXI D, E56A             ; 3BB7: 11 6A E5
    CALL 3B9A               ; 3BBA: CD 9A 3B
    INR L                   ; 3BBD: 2C
    INR L                   ; 3BBE: 2C
    LXI D, E56D             ; 3BBF: 11 6D E5
    CALL 3B9A               ; 3BC2: CD 9A 3B
    LXI D, C56E             ; 3BC5: 11 6E C5
    JMP 3B9A                ; 3BC8: C3 9A 3B
    CALL 3902               ; 3BCB: CD 02 39
    JMP 3BA8                ; 3BCE: C3 A8 3B
; Read 7 rows x 16 bytes from DE (glyph), AND-clear bits in VRAM banks 0x8568/0xA568/0xC568/0xE568 with stride 0x2000 (4-bank stamp)
func_draw_masked_glyph_4banks:
    LXI H, 8568             ; 3BD1: 21 68 85
    MVI B, 07               ; 3BD4: 06 07
    MVI C, 16               ; 3BD6: 0E 16
    PUSH H                  ; 3BD8: E5
    PUSH H                  ; 3BD9: E5
    PUSH B                  ; 3BDA: C5
    LXI B, 2000             ; 3BDB: 01 00 20
    LDAX D                  ; 3BDE: 1A
    ANA M                   ; 3BDF: A6
    MOV M, A                ; 3BE0: 77
    DAD B                   ; 3BE1: 09
    LDAX D                  ; 3BE2: 1A
    ANA M                   ; 3BE3: A6
    MOV M, A                ; 3BE4: 77
    DAD B                   ; 3BE5: 09
    LDAX D                  ; 3BE6: 1A
    ANA M                   ; 3BE7: A6
    MOV M, A                ; 3BE8: 77
    DAD B                   ; 3BE9: 09
    LDAX D                  ; 3BEA: 1A
    ANA M                   ; 3BEB: A6
    MOV M, A                ; 3BEC: 77
    POP B                   ; 3BED: C1
    POP H                   ; 3BEE: E1
    INR H                   ; 3BEF: 24
    DCR C                   ; 3BF0: 0D
    JNZ 3BD9                ; 3BF1: C2 D9 3B
    POP H                   ; 3BF4: E1
    INR L                   ; 3BF5: 2C
    DCR B                   ; 3BF6: 05
    JNZ 3BD6                ; 3BF7: C2 D6 3B
    HLT                     ; 3BFA: 76
    HLT                     ; 3BFB: 76
    NOP                     ; 3BFC: 00
    RET                     ; 3BFD: C9
; Stream-fetch: HL=C444 or D544 based on flag 3982; DE=291C or 2931; CALL 3AE7 with BC=0307, A=01 (play 3-byte note event x 7 rows)
func_melody_frame:
    LXI H, C444             ; 3BFE: 21 44 C4
    LXI D, 291C             ; 3C01: 11 1C 29
    LDA 3982                ; 3C04: 3A 82 39
    ORA A                   ; 3C07: B7
    JZ 3C0E                 ; 3C08: CA 0E 3C
    LXI D, 2931             ; 3C0B: 11 31 29
    LXI B, 0307             ; 3C0E: 01 07 03
    MVI A, 01               ; 3C11: 3E 01
    CALL 3AE7               ; 3C13: CD E7 3A
    MVI A, 01               ; 3C16: 3E 01
    LXI H, D544             ; 3C18: 21 44 D5
    LXI D, 291C             ; 3C1B: 11 1C 29
    ORA A                   ; 3C1E: B7
    JZ 3C25                 ; 3C1F: CA 25 3C
    LXI D, 2931             ; 3C22: 11 31 29
    LXI B, 0307             ; 3C25: 01 07 03
    MVI A, 01               ; 3C28: 3E 01
    JMP 3AE7                ; 3C2A: C3 E7 3A
; Second channel: HL=D544
label_melody_B_stream:
    SHLD 3979               ; 3C2D: 22 79 39
    EI                      ; 3C30: FB
    MVI A, 03               ; 3C31: 3E 03
    PUSH PSW                ; 3C33: F5
    HLT                     ; 3C34: 76
    CALL 3BCB               ; 3C35: CD CB 3B
    CALL 3C44               ; 3C38: CD 44 3C
    CALL 3BFE               ; 3C3B: CD FE 3B
    POP PSW                 ; 3C3E: F1
    DCR A                   ; 3C3F: 3D
    JNZ 3C33                ; 3C40: C2 33 3C
    RET                     ; 3C43: C9
    CALL 3B07               ; 3C44: CD 07 3B
    STA 3C78                ; 3C47: 32 78 3C
    MVI A, 08               ; 3C4A: 3E 08
    DCR A                   ; 3C4C: 3D
    CZ 3C63                 ; 3C4D: CC 63 3C
    JMP 3E79                ; 3C50: C3 79 3E
    ORA A                   ; 3C53: B7
    RNZ                     ; 3C54: C0
    LDA 3C78                ; 3C55: 3A 78 3C
    CPI 21                  ; 3C58: FE 21
    JZ 3C66                 ; 3C5A: CA 66 3C
    CPI 28                  ; 3C5D: FE 28
    JZ 3C79                 ; 3C5F: CA 79 3C
    RET                     ; 3C62: C9
    MVI A, 08               ; 3C63: 3E 08
    RET                     ; 3C65: C9
    LDA 3982                ; 3C66: 3A 82 39
    ORA A                   ; 3C69: B7
    JZ 3C72                 ; 3C6A: CA 72 3C
    XRA A                   ; 3C6D: AF
    STA 3982                ; 3C6E: 32 82 39
    RET                     ; 3C71: C9
    MVI A, 2F               ; 3C72: 3E 2F
    STA 3982                ; 3C74: 32 82 39
    RET                     ; 3C77: C9
    NOP                     ; 3C78: 28
    XRA A                   ; 3C79: AF
    INR A                   ; 3C7A: 3C
    STA 3C17                ; 3C7B: 32 17 3C
    RET                     ; 3C7E: C9
; CALL func_melody_frame x2 then 7x CALL func_draw_masked_glyph_4banks with glyph ptrs 2946,294D,2954,295B,2962,2969,2970
label_draw_frame_dispatch:
    CALL 3BFE               ; 3C7F: CD FE 3B
    LXI D, 2946             ; 3C82: 11 46 29
    CALL 3BD1               ; 3C85: CD D1 3B
    LXI D, 294D             ; 3C88: 11 4D 29
    CALL 3BD1               ; 3C8B: CD D1 3B
    LXI D, 2954             ; 3C8E: 11 54 29
    CALL 3BD1               ; 3C91: CD D1 3B
    LXI D, 295B             ; 3C94: 11 5B 29
    CALL 3BD1               ; 3C97: CD D1 3B
    LXI D, 2962             ; 3C9A: 11 62 29
    CALL 3BD1               ; 3C9D: CD D1 3B
    LXI D, 2969             ; 3CA0: 11 69 29
    CALL 3BD1               ; 3CA3: CD D1 3B
    LXI D, 2970             ; 3CA6: 11 70 29
    CALL 3BD1               ; 3CA9: CD D1 3B
; DI + LXI H,3738 (screen buffer base?) + LXI D,7C00
label_frame_end_di:
    DI                      ; 3CAC: F3
    LXI H, 3738             ; 3CAD: 21 38 37
    LXI D, 7C00             ; 3CB0: 11 00 7C
    CALL 2C2B               ; 3CB3: CD 2B 2C
    LXI H, 36E9             ; 3CB6: 21 E9 36
    LXI D, 7D00             ; 3CB9: 11 00 7D
    CALL 2E0E               ; 3CBC: CD 0E 2E
    LXI H, 3691             ; 3CBF: 21 91 36
    LXI D, 7E00             ; 3CC2: 11 00 7E
    CALL 2FF1               ; 3CC5: CD F1 2F
    CALL 2AC0               ; 3CC8: CD C0 2A
    CALL 2CA3               ; 3CCB: CD A3 2C
    CALL 2E86               ; 3CCE: CD 86 2E
    LXI H, EF3C             ; 3CD1: 21 3C EF
    CALL 2C65               ; 3CD4: CD 65 2C
    LXI H, F03C             ; 3CD7: 21 3C F0
    CALL 2E48               ; 3CDA: CD 48 2E
    LXI H, F13C             ; 3CDD: 21 3C F1
    CALL 302B               ; 3CE0: CD 2B 30
    CALL 2AC0               ; 3CE3: CD C0 2A
    CALL 2CA3               ; 3CE6: CD A3 2C
    CALL 2E86               ; 3CE9: CD 86 2E
    CALL 2C6C               ; 3CEC: CD 6C 2C
    CALL 2E4F               ; 3CEF: CD 4F 2E
    CALL 3032               ; 3CF2: CD 32 30
    MVI A, 14               ; 3CF5: 3E 14
    DCR A                   ; 3CF7: 3D
    JNZ 3CF7                ; 3CF8: C2 F7 3C
    IN 01                   ; 3CFB: DB 01
    ANI 40                  ; 3CFD: E6 40
    JNZ 3CE3                ; 3CFF: C2 E3 3C
    CALL 2C57               ; 3D02: CD 57 2C
    CALL 2E3A               ; 3D05: CD 3A 2E
    CALL 301D               ; 3D08: CD 1D 30
    MVI A, 10               ; 3D0B: 3E 10
    PUSH PSW                ; 3D0D: F5
    CALL 2C6C               ; 3D0E: CD 6C 2C
    CALL 2E4F               ; 3D11: CD 4F 2E
    CALL 3032               ; 3D14: CD 32 30
    POP PSW                 ; 3D17: F1
    DCR A                   ; 3D18: 3D
    JNZ 3D0D                ; 3D19: C2 0D 3D
    LXI SP, 7FFF            ; 3D1C: 31 FF 7F
    XRA A                   ; 3D1F: AF
    STA 3C17                ; 3D20: 32 17 3C
    EI                      ; 3D23: FB
    CALL 382F               ; 3D24: CD 2F 38
    JMP 3860                ; 3D27: C3 60 38

