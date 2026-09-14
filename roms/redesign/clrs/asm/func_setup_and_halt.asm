; Функция: func_setup_and_halt
; Адрес: 0x0100
; Размер: 63 байта
; Описание: ROM entry point. (1) DI. (2) VRAM clear loop: HL=8000h,
;           MVI M,00 / INR L / JNZ clears 256 bytes, INR H / JNZ continues
;           through all 4 planes 8000h-FFFFh. (3) RST 7 vector setup:
;           STA 0038h=C3h, LXI H,013Fh / SHLD 0039h. (4) Palette stack init:
;           SP=0577h, PUSH H(0172h), loop 7x PUSH H(0152h)+PUSH PSW,
;           arithmetic loop 8x. (5) OUT 02h border. (6) LXI SP,0100h / EI / HLT.

    org 0100h

func_setup_and_halt:
    DI                          ; 0x0100
    LXI H, 8000h                ; 0x0101
.loc_0104:
    MVI M, 00h                  ; 0x0104
    INR L                       ; 0x0106
    JNZ .loc_0104               ; 0x0107
    INR H                       ; 0x010A
    JNZ .loc_0104               ; 0x010B
    MVI A, C3h                  ; 0x010E
    STA data_rst7_vector        ; 0x0110
    LXI H, func_isr_delay_and_setup  ; 0x0113
    SHLD 0039h                  ; 0x0116
    LXI SP, 0577h               ; 0x0119
    LXI H, func_isr_rearm_and_exit   ; 0x011C
    PUSH H                      ; 0x011F
    LXI H, func_isr_palette_cycle    ; 0x0120
    MVI A, F8h                  ; 0x0123
    PUSH PSW                    ; 0x0125
    MVI B, 07h                  ; 0x0126
.loc_0128:
    PUSH H                      ; 0x0128
    PUSH PSW                    ; 0x0129
    DCR B                       ; 0x012A
    JNZ .loc_0128               ; 0x012B
    MVI B, 08h                  ; 0x012E
    SUB B                       ; 0x0130
    JNC .loc_0128               ; 0x0131
    XRA A                       ; 0x0134
    OUT 02h                     ; 0x0135
    LXI SP, func_setup_and_halt      ; 0x0137
    EI                          ; 0x013A
.loc_013B:
    HLT                         ; 0x013B
    JMP .loc_013B               ; 0x013C
