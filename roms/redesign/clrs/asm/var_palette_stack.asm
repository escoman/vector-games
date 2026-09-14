; Переменная: var_palette_stack
; Адрес: 0x055A
; Размер: 29 байт
; Описание: Palette stack area in RAM. SP initialized to 0577h by
;           func_setup_and_halt. Contains 12 word-pairs (24 bytes) pushed
;           during init: return addresses (0152h = func_isr_palette_cycle)
;           and palette colors (F8h..FCh). Consumed by POP PSW in
;           func_isr_palette_cycle.

    org 055Ah

var_palette_stack:
    defs 29                       ; Резерв 29 байт под стек палитры
