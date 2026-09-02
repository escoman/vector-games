/*
 * about.c — экран "О программе" (F5).
 */
#include "v06.h"
#include "screens.h"

/* Подсчёт ненулевых байт в диапазоне 0x8000-0xDFFF.
 * В режиме 256x256x2 все эти плоскости должны быть пусты.
 * Если не ноль — какая-то функция пишет не в ту плоскость. */
static unsigned int count_nonzero_vram(void)
{
    volatile unsigned char *p = (volatile unsigned char *)0x8000;
    unsigned int count = 0;
    unsigned int i;
    for (i = 0; i < 0x6000; i++) {
        if (p[i])
            count++;
    }
    return count;
}

/* Вывод 16-битного числа в hex-виде */
static void hex4(char *buf, unsigned int val)
{
    static const char hex[] = "0123456789ABCDEF";
    buf[0] = hex[(val >> 12) & 0x0F];
    buf[1] = hex[(val >> 8)  & 0x0F];
    buf[2] = hex[(val >> 4)  & 0x0F];
    buf[3] = hex[val & 0x0F];
    buf[4] = 0;
}

void draw_about(void)
{
    unsigned int nz;
    char hexbuf[5];
    char line[33];
    unsigned char i;

    init_screen();
    graph_print(0, 0,  "COMPOSER", 1);
    graph_print(0, 24, "MUSIC EDITOR FOR VECTOR-06C", 1);
    graph_print(0, 40, "VERSION 1.0", 1);

    /* Диагностика: ненулевые байты в неактивных плоскостях */
    nz = count_nonzero_vram();
    hex4(hexbuf, nz);

    /* "VRAM 8000-DFFF NONZERO: XXXX" */
    {
        const char *src = "VRAM 8000-DFFF NONZERO: ";
        i = 0;
        while (src[i] && i < 26) {
            line[i] = src[i];
            i++;
        }
        line[i++] = hexbuf[0];
        line[i++] = hexbuf[1];
        line[i++] = hexbuf[2];
        line[i++] = hexbuf[3];
        line[i] = 0;
    }
    graph_print(0, 64, line, 1);

    graph_print(0, 88, "AP2-RETURN", 1);
}

void screen_about(void)
{
    draw_about();
    kbd_wait_key(27);
}
