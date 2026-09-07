; clrs.asm — смена палитры во время развёртки (дизассемблирован из clrs.rom, 119 байт).

        org     0x0100

; === Основной код (0x0100-0x013E, 63 байта) ===
        di
        ld      hl, 0x8000
clear_loop:
        ld      (hl), 0
        inc     l
        jp      nz, clear_loop
        inc     h
        jp      nz, clear_loop

        ld      a, 0xC3
        ld      (0x0038), a
        ld      hl, isr_vector
        ld      (0x0039), hl

        ld      sp, 0x0577

        ld      hl, 0x0172
        push    hl
        ld      hl, 0x0152
        ld      a, 0xF8
        push    af
        ld      b, 7
combined_loop:
        push    hl
        push    af
        dec     b
        jp      nz, combined_loop
        ld      b, 8
        sub     b
        jp      nc, combined_loop

        xor     a
        out     (0x02), a

        ld      sp, 0x0100

        ei
halt_loop:
        halt
        jp      halt_loop

; === Данные ISR (0x013F-0x0141, 3 байта) ===
isr_vector:
        db      0x01, 0xEC, 0x00

; === Код ISR (0x0142-0x0171, 48 байт) ===
isr_code:
        dec     bc
        ld      a, b
        or      c
        jp      nz, isr_code
        nop
        nop
        db      0x01, 0x03, 0x07, 0x16, 0x01, 0x31, 0x77, 0x01
        db      0xF1, 0xBE, 0xBE, 0xBE, 0x00, 0xD3, 0x0C, 0xAA
        db      0xD3, 0x0C, 0xA9, 0xD3, 0x0C, 0xAA, 0xD3, 0x0C
        db      0xA8, 0xD3, 0x0C, 0xAA, 0xD3, 0x0C, 0xA9, 0xD3
        db      0x0C, 0xAA, 0xD3, 0x0C, 0xAF, 0xD3, 0x0C, 0xC9

; === Хвостовой код (0x0172-0x0176, 5 байт) ===
        ld      sp, 0x00FE
        ei
        ret
