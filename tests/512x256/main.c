/*
 * 512x256.c — тест режима 512x256 Вектора-06Ц.
 * Без прерываний, без HALT — всё последовательно.
 */

int main(void)
{
#asm
        di
        ld      sp, 0x8000

        ; Палитра 16 цветов (RRRGGGBB)
        ld      hl, _pal + 15
        ld      b, 16
pl:
        ld      a, b
        dec     a
        out     (0x02), a
        ld      a, (hl)
        out     (0x0C), a
        dec     hl
        dec     b
        jp      nz, pl

        xor     a
        out     (0x02), a           ; бордюр 0

        ; ПИА
        ld      a, 0x88
        out     (0x00), a

        ; Режим 512x256
        ld      a, 0x10
        out     (0x02), a

        ; Очистка VRAM 32 КБ
        ld      hl, 0x8000
        ld      de, 0x8001
        ld      bc, 0x7FFF
        xor     a
        ld      (hl), a
        ldir

        ; Тест: 0xFF по адресу 8110h
        ld      hl, 0x8110
        ld      (hl), 0xFF

        ; Конец — бесконечный цикл
hang:
        jp      hang

; Палитра (RRRGGGBB)
_pal:
        defb    0x00, 0x07, 0x38, 0x3F, 0x1B, 0x24, 0x39, 0x20
        defb    0x04, 0x03, 0x1C, 0x27, 0x3C, 0x1F, 0x3E, 0x00
#endasm

    return 0;
}
