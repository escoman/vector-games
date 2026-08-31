/*
 * graphlz.c — LZ-распаковщик тайлов в видеопамять Вектора-06Ц.
 *
 *   void graph_lz_expand(const unsigned char *src);
 *
 * Формат данных (bmp2inc_lz.py):
 *   Заголовок: tpp_lo, tpp_hi, ntiles_lo, ntiles_hi (4 байта).
 *   Словарь: ntiles * 8 байт.
 *   4 LZ-потока (плоскости с весами 8, 4, 2, 1).
 *
 * Тайлы в потоке — в порядке VRAM постолбцово:
 * сначала все тайлы столбца 0 (снизу вверх), затем столбца 1 и т.д.
 * Базы плоскостей: 0x8000, 0xA000, 0xC000, 0xE000.
 * Байты тайла пишутся по убывающему адресу.
 */

#include <string.h>

/* Базы VRAM плоскостей: 0x8000 + plane * 0x2000.
 * Plane 0 -> 0x8000, 1 -> 0xA000, 2 -> 0xC000, 3 -> 0xE000 */

/* Адрес VRAM для тайла #tile_idx на плоскости plane.
 * Порядок постолбцово: col = tile_idx / h_div8, row = tile_idx % h_div8.
 * Возвращает адрес ПЕРВОГО байта (самого старшего адреса тайла). */
static unsigned int tile_vram(unsigned int plane, unsigned int tile_idx,
                              unsigned int h_div8)
{
    unsigned int base = 0x8000 + plane * 0x2000;
    unsigned int col = tile_idx / h_div8;
    unsigned int row = tile_idx % h_div8;
    return base + col * 256 + (255 - row * 8);
}

/* Записать 8 байт из src по убывающему VRAM-адресу addr. */
static void write_tile(unsigned int addr, const unsigned char *src)
{
    volatile unsigned char *vram = (volatile unsigned char *)addr;
    for (int i = 0; i < 8; i++) {
        *vram = src[i];
        vram--;
    }
}

void graph_lz_expand(const unsigned char *src)
{
    unsigned int tpp;       /* тайлов на плоскость */
    unsigned int ntiles;    /* уникальных тайлов в словаре */
    unsigned int h_div8;    /* высота в тайлах (тайлов в столбце) */
    const unsigned char *dict;  /* словарь (указатель в src) */
    const unsigned char *p;     /* текущая позиция в LZ-потоке */

    /* Заголовок: tpp(16), ntiles(16), h_div8(8) */
    tpp     = src[0] | ((unsigned int)src[1] << 8);
    ntiles  = src[2] | ((unsigned int)src[3] << 8);
    h_div8  = src[4];
    dict    = src + 5;
    p       = dict + ntiles * 8;    /* начало LZ-потоков */

    /* Для каждой плоскости */
    for (unsigned int pl = 0; pl < 4; pl++) {
        unsigned int cur = 0;       /* номер текущего тайла */
        unsigned char flag = 0;
        unsigned char nbits = 0;

        /* Крутимся, пока есть непрочитанные биты или тайлы */
        for (;;) {
            /* Нужен новый flag_byte? */
            if (nbits == 0) {
                /* Если все тайлы обработаны и нечего читать — выходим */
                if (cur >= tpp) break;
                flag = *p++;
                nbits = 8;
            }

            if (flag & 1) {
                /* Literal: 2 байта — индекс тайла */
                unsigned int idx = (p[0] & 1) * 256 + p[1];
                p += 2;
                if (cur < tpp)
                    write_tile(tile_vram(pl, cur, h_div8), dict + idx * 8);
            } else {
                /* Reference: offset 12 бит, length 4 бита */
                unsigned int offset = ((p[0] & 0x0F) << 8) | p[1];
                unsigned int length = (p[0] >> 4) + 3;
                p += 2;
                for (unsigned int k = 0; k < length; k++) {
                    if (cur < tpp) {
                        unsigned int src_tile = cur - offset;
                        unsigned int src_addr = tile_vram(pl, src_tile, h_div8);
                        unsigned int dst_addr = tile_vram(pl, cur, h_div8);
                        volatile unsigned char *sv = (volatile unsigned char *)src_addr;
                        volatile unsigned char *dv = (volatile unsigned char *)dst_addr;
                        for (int i = 0; i < 8; i++) {
                            *dv = *sv;
                            sv--;
                            dv--;
                        }
                    }
                    cur++;
                }
                flag >>= 1;
                nbits--;
                continue;
            }
            cur++;
            flag >>= 1;
            nbits--;
        }
    }
}
