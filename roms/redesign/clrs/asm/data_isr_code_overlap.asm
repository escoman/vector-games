; Данные: data_isr_code_overlap
; Адрес: 0x014A
; Размер: 8 байт
; Описание: Code overlap artifact. These bytes overlap with executable code
;           inside func_isr_delay_and_setup (LXI B,0703h / MVI D,01h /
;           LXI SP,0177h). NOT a color table — the bytes are instruction
;           opcodes. Actual palette values are on the stack at var_palette_stack.

    org 014Ah

data_isr_code_overlap:
    defb 01h, 03h, 07h            ; Байты инструкции LXI B, 0703h
    defb 16h, 01h                 ; Байты инструкции MVI D, 01h
    defb 31h, 77h, 01h            ; Байты инструкции LXI SP, 0177h
