; Функция: func_isr_rearm_and_exit
; Адрес: 0x0172
; Размер: 5 байт
; Описание: ISR exit and rearm. LXI SP,00FEh resets SP to fixed location.
;           EI re-enables interrupts for next VBlank. RET dual purpose:
;           (1) first invocation: pops 0172h → loops back to self;
;           (2) after func_isr_palette_cycle RET: pops next return address.

    org 0172h

func_isr_rearm_and_exit:
    LXI SP, 00FEh               ; 0x0172
    EI                          ; 0x0175
    RET                         ; 0x0176
