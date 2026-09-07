/*
 * check_bugs.c — тест для проверки багов стека.
 *
 * Вызывает ASM-процедуры:
 * 1. Очистка экрана (gfx_fill_planes из clr.asm)
 * 2. Установка палитры (v06_set_palette_asm из v06pal.asm)
 * 3. Рисование на плоскости (plane_fill — inline asm)
 *
 * В plane_fill специально добавлен одиночный PUSH после чтения
 * параметров, который не влияет на работу функции, но сдвигает стек
 * на 2 байта после возврата.
 *
 * После всех вызовов — вечный цикл while(1).
 */

#include "v06.h"

/* Палитра: 16 цветов */
static const unsigned char default_palette[16] = {
    0x00, 0x4A, 0x4A, 0x94, 0x94, 0xB6, 0xB6, 0xDE,
    0xDE, 0xE7, 0xE7, 0xF0, 0xF0, 0xF8, 0xF8, 0xFF
};

/* ================================================================
 *  Ассемблерные процедуры
 * ================================================================ */

#asm
        SECTION code_clib

; ---------------------------------------------------------------
; void plane_fill(unsigned int addr, unsigned char val, unsigned char count)
;   __z88dk_callee
;
; Запись байта val по адресу addr, затем addr+1, addr+2 и т.д.,
; всего count байт.
;
; Параметры (после CALL):
;   SP -> count (16-битный слот, значение в младшем байте)
;          val   (16-битный слот, значение в младшем байте)
;          addr  (16-битный слот)
;          return address
;
; Регистры в цикле: A = val, C = count, HL = текущий адрес.
;
; БАГ: после чтения всех параметров и перед ret добавлен
; одиночный PUSH BC, который не влияет на заполнение VRAM
; (данные уже в регистрах), но сдвигает стек на 2 байта.
; ---------------------------------------------------------------
        PUBLIC  _plane_fill

_plane_fill:
        pop     hl              ; HL = return address
        pop     de              ; DE = count (slot), E = count
        ld      a, e
        ld      (_pf_cnt), a    ; count (сохраняем E до перезаписи)
        pop     bc              ; BC = val (slot),  C = val
        ld      a, c
        ld      (_pf_val), a    ; val
        pop     de              ; DE = addr

        ; БАГ: одиночный PUSH между чтением параметров и возвратом
        ; return address. Не влияет на работу функции (данные уже
        ; сохранены), но сдвигает стек на 2 байта после возврата.
        push    hl

        ; Возвращаем return address на стек
        push    hl

        ; Загружаем рабочие регистры: A = val, C = count, HL = addr
        ld      a, (_pf_cnt)
        ld      c, a
        ld      a, (_pf_val)
        ld      hl, 0
        add     hl, de          ; HL = addr

        ; Проверка count == 0
        ld      a, c
        or      a
        jp      z, pf_done

        ; Загружаем val в A
        ld      a, (_pf_val)

pf_loop:
        ld      (hl), a
        inc     hl
        dec     c
        jp      nz, pf_loop

pf_done:
        ret

_pf_cnt:
        defb    0
_pf_val:
        defb    0

#endasm

/* Объявления функций */
extern void plane_fill(unsigned int addr, unsigned char val, unsigned char count) __z88dk_callee;

/* ================================================================
 *  main
 * ================================================================ */

int main(void)
{
    /* 1. Очистка экрана: чёрная палитра + очистка всех плоскостей */
    gfx_set_black_palette();
    gfx_clear(0);

    /* 2. Установка палитры */
    gfx_set_bmp_palette(default_palette);

    /* 3. Рисование на плоскости 0x8000 (плоскость веса 8):
     *    заполняем 32 байта значением 0xFF */
    plane_fill(0x8000, 0xFF, 32);

    /* 4. Ещё один вызов для проверки: плоскость 0xA000, 16 байт 0xAA */
    plane_fill(0xA000, 0xAA, 16);

    return 0;
}
