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

/* Вывод текста шрифтом 16x8 в режиме 512x256 (pr512.asm) */
extern void graph_put_char_512(unsigned char x, unsigned char y, char ch,
                               unsigned char color) __z88dk_callee;
extern void graph_print_512(unsigned char x, unsigned char y, const char *s,
                            unsigned char color) __z88dk_callee;

/* Вывод тонкого текста 4x8 в режиме 512x256 (pr512t.asm) */
extern void graph_print_512t(unsigned char x, unsigned char y, const char *s,
                             unsigned char color) __z88dk_callee;

const unsigned char _pal4[4] = {
    0x00, V06_RGB(7, 0, 0), V06_RGB(0, 7, 0), V06_RGB(7, 7, 3)
};

/* Загрузка 16 цветов палитры (v06pal.asm) */
extern void v06_set_palette_asm(const unsigned char *pal);

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
    /* Переключаем в 512x256 через новый API */
    gfx_set_mode(GFX_MODE_512_4);

    /* Загружаем палитру (до переключения режима) */
    gfx_set_palette(_pal4);

    /* Очистка через новый API: заполняет плоскости по маске режима */
    gfx_clear(0x00);

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

    /* Зелёный прямоугольник (C000 + 8000) с отступом внутрь */

    /* Левая граница (X=1): C000, бит 6, Y=16..239 */
    fill_stride(0xC110, 0x80, 1, 224);

    /* Правая граница (X=510): 8000, бит 1, Y=16..239 */
    fill_stride(0x9E10, 0x01, 1, 224);

    /* Верхняя граница (Y=16): 8000 + C000 */
    fill_stride(0x8110, 0xFF, 0x100, 30);
    fill_stride(0xC110, 0xFF, 0x100, 30);

    /* Нижняя граница (Y=239): 8000 + C000 */
    fill_stride(0x81EF, 0xFF, 0x100, 30);
    fill_stride(0xC1EF, 0xFF, 0x100, 30);

    /* Белый прямоугольник (E000+A000 + C000+8000) с отступом внутрь */

    /* Левая граница (X=2): E000, бит 5, Y=32..223 */
    fill_stride(0xE220, 0x80, 1, 192);
    fill_stride(0xC220, 0x80, 1, 192);

    /* Правая граница (X=509): A000, бит 2, Y=32..223 */
    fill_stride(0xBD20, 0x01, 1, 192);
    fill_stride(0x9D20, 0x01, 1, 192);

    /* Верхняя граница (Y=32): все 4 плоскости */
    fill_stride(0xA220, 0xFF, 0x100, 28);
    fill_stride(0xE220, 0xFF, 0x100, 28);
    fill_stride(0x8220, 0xFF, 0x100, 28);
    fill_stride(0xC220, 0xFF, 0x100, 28);

    /* Нижняя граница (Y=223): все 4 плоскости */
    fill_stride(0xA2DF, 0xFF, 0x100, 28);
    fill_stride(0xE2DF, 0xFF, 0x100, 28);
    fill_stride(0x82DF, 0xFF, 0x100, 28);
    fill_stride(0xC2DF, 0xFF, 0x100, 28);

    graph_print_512(3, 50, "VECTOR-06C", 0x03);
    graph_print_512(3, 60, "512x256 MODE", 0x03);
    graph_print_512t(3, 70, "THIN TEXT TEST", 0x03);

    graph_print_512(3, 100, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 0x01);
    graph_print_512(3, 110, "0123456789", 0x01);
    graph_print_512(3, 120, "-:().,?!@<>=&$#*+%", 0x01);

    graph_print_512t(3, 140, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 0x02);
    graph_print_512t(3, 150, "0123456789-:().,?!@<>=&$#*+%", 0x02);

    graph_print_512t(3, 170, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 0x03);
    graph_print_512t(3, 180, "0123456789-:().,?!@<>=&$#*+%", 0x03);

    while(1);

    return 0;
}
