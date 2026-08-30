/*
 * 512x256.c — тест режима 512x256 (4 цвета) Вектора-06Ц.
 *
 * Все 4 плоскости задействованы:
 *   Первая плоскость (бит 0 цвета):
 *     чётные X:  E000h-FFFFh
 *     нечётные X: A000h-BFFFh
 *   Вторая плоскость (бит 1 цвета):
 *     чётные X:  C000h-DFFFh
 *     нечётные X: 8000h-9FFFh
 */

#include "v06.h"

/* Вывод текста шрифтом 16x8 в режиме 512x256 (graphpr512.asm) */
extern void graph_print_512(unsigned char x, unsigned char y, const char *s,
                            unsigned char color);

/* Вывод тонкого текста 4x8 в режиме 512x256 (graphpr512t.asm) */
extern void graph_print_512t(unsigned char x, unsigned char y, const char *s,
                             unsigned char color);

static void set_palette(void)
{
    unsigned char _pal16[16];

    unsigned char bg = 0x00;
    unsigned char fg = 0xFF;

    _pal16[0x00] = bg;
    _pal16[0x01] = fg;
    _pal16[0x02] = fg;
    _pal16[0x03] = fg;
    _pal16[0x04] = fg;
    _pal16[0x05] = fg;
    _pal16[0x06] = fg;
    _pal16[0x07] = fg;
    _pal16[0x08] = fg;
    _pal16[0x09] = fg;
    _pal16[0x0A] = fg;
    _pal16[0x0B] = fg;
    _pal16[0x0C] = fg;
    _pal16[0x0D] = fg;
    _pal16[0x0E] = fg;
    _pal16[0x0F] = fg;
    /*for (int i = 1; i < 16; i++)
        _pal16[i] = fg;*/

    v06_set_palette_asm(_pal16);
}



/* Переключение в режим 512x256 */
static void graph_set_mode_512(void)
{
#asm
        di
        ld      a, 0x88
        out     (0x00), a           ; ПИА (сбрасывает PA/PB/PC в 0)
        ld      a, 0xFF
        out     (0x03), a           ; скролл = 0xFF (компенсация направления)
        ld      a, 0x10
        out     (0x02), a           ; Режим 512x256
        ei
#endasm
}

/* Заполнение 8 КБ плоскости по начальному адресу. */
static void fill_plane(unsigned int addr, unsigned char fill)
{
    unsigned char *p = (unsigned char *)addr;
    unsigned int i;
    for (i = 0; i < 0x2000; i++)
        *p++ = fill;
}

/* Очистка плоскостей по маске.
 * bit 0 (0x01) → E000h-FFFFh
 * bit 1 (0x02) → A000h-BFFFh
 * bit 2 (0x04) → C000h-DFFFh
 * bit 3 (0x08) → 8000h-9FFFh
 * 0x0F → все 4 плоскости. */
static void graph_clear_512(unsigned char mask, unsigned char fill)
{
    unsigned int addr = 0xE000;
    unsigned char m;
    for (m = 0x01; m != 0x10; m <<= 1) {
        if (mask & m)
            fill_plane(addr, fill);
        addr -= 0x2000;
    }
}

/* Запись count байт: val по адресам addr, addr+step, addr+2*step, ... */
static void fill_stride(unsigned int addr, unsigned char val,
                        unsigned int step, unsigned char count)
{
    unsigned char *p = (unsigned char *)addr;
    while (count--) {
        *p = val;
        p += step;
    }
}

int main(void)
{
    /* Формируем и загружаем палитру */
    set_palette();

    /* Переключаем в 512x256 */
    graph_set_mode_512();
    graph_clear_512(0x0F, 0x00);
    graph_clear_512(0x01, 0xFF);
    graph_clear_512(0x04, 0xFF);
    //graph_clear_512(0x02, 0xFF);

    while(1);

    /* Левый столбец (X=0): E001h..E0FEh, бит 7 */
    fill_stride(0xE001, 0x80, 1, 254);

    /* Правый столбец (X=511): BF01h..BFFEh, бит 0 */
    fill_stride(0xBF01, 0x01, 1, 254);

    /* Верхняя строка (Y=0): A000h..BF00h + E000h..FF00h */
    fill_stride(0xA000, 0xFF, 0x100, 32);
    fill_stride(0xE000, 0xFF, 0x100, 32);

    /* Нижняя строка (Y=255): A0FFh..BFFFh + E0FFh..FFFFh */
    fill_stride(0xA0FF, 0xFF, 0x100, 32);
    fill_stride(0xE0FF, 0xFF, 0x100, 32);

    /* Вывод текста */
    graph_print_512(1, 10, "VECTOR-06C", 0x1);
    graph_print_512(1, 20, "512x256 MODE", 0xF);
    graph_print_512t(1, 40, "THIN TEXT TEST", 0xF);

    while(1);

    return 0;
}
