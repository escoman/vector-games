; Данные: data_rst7_vector
; Адрес: 0x0038
; Размер: 3 байта
; Описание: RST 7 hardware interrupt vector (VBlank). Initialized at runtime
;           by func_setup_and_halt: STA 0038h=C3h (JP opcode),
;           SHLD 0039h writes target address 013Fh.
;           When VBlank fires (~50Hz), CPU executes JP 013Fh.
;           RAM data — not part of ROM, shown as runtime content.

    org 0038h

data_rst7_vector:
    defb C3h                        ; JP opcode
    defw func_isr_delay_and_setup   ; 0x013F — ISR entry point
