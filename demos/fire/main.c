/*
 * fire.c — демонстрация алгоритма горения огня для Вектора-06Ц.
 *
 * Зона огня 256×128, прижата к нижнему краю экрана.
 *
 * Алгоритм — скользящее окно (256 байт RAM):
 *   - Два буфера по 256 байт (fire_row_a, fire_row_b).
 *   - Каждый пиксель — индекс интенсивности 0..15.
 *   - Строка за строкой снизу вверх: читаем из строки ниже
 *     (src), применяем случайный сдвиг и вычитание затухания,
 *     записываем в dst, рендерим в VRAM.
 *   - После 127 строк буферов достаточно — каждая строка
 *     зависит только от строки непосредственно ниже.
 *
 * Рендер: 8 пикселей (байт) → 4 байта битовых плоскостей VRAM.
 * Один столбец (32 шт.) обрабатывается целиком за проход.
 */

#include <intrinsic.h>
#include "v06.h"

/* ----------------------------- ПАЛИТРА --------------------------------
 * 16 цветов огня. Формат V06: BB_GGG_RRR.
 * Конвертация из HTML: R=ROUND(R_html/36), G=ROUND(G_html/36),
 *                       B=ROUND(B_html/85).
 * --------------------------------------------------------------- */

static const unsigned char fire_palette[16] = {
    V06_RGB(0, 0, 0),   /*  0: 0x00  чёрный                */
    V06_RGB(1, 0, 0),   /*  1: 0x01  тёмный дым             */
    V06_RGB(1, 0, 0),   /*  2: 0x01  бордовой дым           */
    V06_RGB(2, 1, 0),   /*  3: 0x0A  тёмно-красный          */
    V06_RGB(4, 1, 0),   /*  4: 0x0C  красный                */
    V06_RGB(5, 1, 0),   /*  5: 0x0D  ярко-красный           */
    V06_RGB(6, 2, 0),   /*  6: 0x1E  тёмно-оранжевый        */
    V06_RGB(7, 3, 0),   /*  7: 0x27  оранжевый              */
    V06_RGB(7, 4, 0),   /*  8: 0x2F  светло-оранжевый       */
    V06_RGB(7, 5, 0),   /*  9: 0x37  жёлто-оранжевый        */
    V06_RGB(7, 6, 0),   /* 10: 0x3F  насыщенный жёлтый      */
    V06_RGB(7, 6, 1),   /* 11: 0x7F  жёлтый                 */
    V06_RGB(7, 7, 2),   /* 12: 0xBF  светло-жёлтый          */
    V06_RGB(6, 7, 3),   /* 13: 0xFE  почти белый (корр.)    */
    V06_RGB(7, 7, 3),   /* 14: 0xFF  белёсый                */
    V06_RGB(7, 7, 3)    /* 15: 0xFF  белое пламя             */
};

/* ------------------------------ ГСЧ -----------------------------------
 * Предгенерированная таблица случайных чисел (256 байт).
 * Заполняется один раз при старте; в цикле огня — чтение по указателю
 * с wraparound через unsigned char индекс.
 * --------------------------------------------------------------- */

static unsigned char rnd_table[256];
static unsigned char rnd_idx;

static void rnd_init(void)
{
    unsigned int seed = 0x1234;
    unsigned char i = 0;
    do {
        seed = seed * 251 + 73;
        rnd_table[i] = (unsigned char)(seed >> 8);
    } while (++i != 0);
    rnd_idx = 0;
}

/* Быстрое случайное число — просто читаем из таблицы. */
#define rnd_next()  (rnd_table[rnd_idx++])

/* -------------------------- БУФЕРНЫЕ СТРОКИ ---------------------------
 * Два буфера по 256 байт — скользящее окно алгоритма огня.
 * Каждый пиксель — интенсивность 0..15.
 * --------------------------------------------------------------- */

static unsigned char fire_row_a[256];
static unsigned char fire_row_b[256];

/* ----------------------- РЕНДЕР СТРОКИ В VRAM -------------------------
 * Преобразует 256 байт интенсивностей (8 пикселей × 32 столбца)
 * в 4 битовых плоскости VRAM.
 *
 * VRAM-адреса плоскостей:
 *   Plane 3 (бит 3): 0x8000 + col*256 + ofs
 *   Plane 2 (бит 2): 0xA000 + col*256 + ofs
 *   Plane 1 (бит 1): 0xC000 + col*256 + ofs
 *   Plane 0 (бит 0): 0xE000 + col*256 + ofs
 *
 * ofs = 0 — нижняя строка экрана, ofs = 127 — верхняя строка зоны.
 * --------------------------------------------------------------- */

static void render_row(const unsigned char *row, unsigned char ofs)
{
    unsigned char col, x;
    unsigned char c, p3, p2, p1, p0;

    for (col = 0; col < 32; col++) {
        p3 = p2 = p1 = p0 = 0;
        for (x = 0; x < 8; x++) {
            c = row[col * 8 + x];
            if (c & 8) p3 |= (unsigned char)(1 << (7 - x));
            if (c & 4) p2 |= (unsigned char)(1 << (7 - x));
            if (c & 2) p1 |= (unsigned char)(1 << (7 - x));
            if (c & 1) p0 |= (unsigned char)(1 << (7 - x));
        }
        ((unsigned char *)0x8000)[col * 256 + ofs] = p3;
        ((unsigned char *)0xA000)[col * 256 + ofs] = p2;
        ((unsigned char *)0xC000)[col * 256 + ofs] = p1;
        ((unsigned char *)0xE000)[col * 256 + ofs] = p0;
    }
}

/* ------------------------- SEED НИЖНЕЙ СТРОКИ -------------------------
 * Заполняет буфер случайными интенсивностями 0..15.
 * --------------------------------------------------------------- */

static void fire_seed_bottom(unsigned char *dst)
{
    unsigned char x = 0;

    do {
        dst[x] = rnd_next() & 15;
    } while (++x != 0);
}

/* ----------------------------- КАДАР ОГНЯ -----------------------------
 * Алгоритм скользящего окна:
 *   1. Seed строки 127 (низ экрана) в src.
 *   2. Рендер src в VRAM (ofs = 0).
 *   3. Строки 126..0: swap(src,dst) → вычисление dst из src →
 *      рендер dst в VRAM.
 *
 * Вычисление: сдвиг ±1 пиксель + вычитание затухания (0 или 1).
 * В верхней трети (r < 64) добавляется дополнительное затухание.
 * --------------------------------------------------------------- */

static void fire_frame(void)
{
    unsigned char *src = fire_row_a;
    unsigned char *dst = fire_row_b;
    unsigned char r, x;
    unsigned char col;
    unsigned char p3, p2, p1, p0;

    /* --- Нижняя строка (r = 127): случайные очаги --- */
    fire_seed_bottom(src);

    /* Рендер нижней строки: VRAM ofs = 0 */
    render_row(src, 0);

    /* --- Строки 126..0: swap, вычисление из src, рендер dst --- */
    for (r = 126; ; r--) {
        unsigned char dst_ofs = 127 - r;

        /* Смена буферов: src содержит строку ниже, dst — для текущей */
        {
            unsigned char *tmp = src;
            src = dst;
            dst = tmp;
        }

        /* Вычисление строки от строки ниже (src) */
        x = 0;
        do {
            unsigned char shift = rnd_next() % 5;   /* 0..4 */
            unsigned char sx = (unsigned char)(x + shift - 2);
            unsigned char below = src[sx];
            unsigned char decay = (rnd_next() < 64) ? 1 : 0;  /* ~25% */
            dst[x] = (below > decay) ? (unsigned char)(below - decay) : 0;
        } while (++x != 0);

        /* Рендер dst в VRAM */
        for (col = 0; col < 32; col++) {
            p3 = p2 = p1 = p0 = 0;
            for (x = 0; x < 8; x++) {
                unsigned char c = dst[col * 8 + x];
                if (c & 8) p3 |= (unsigned char)(1 << (7 - x));
                if (c & 4) p2 |= (unsigned char)(1 << (7 - x));
                if (c & 2) p1 |= (unsigned char)(1 << (7 - x));
                if (c & 1) p0 |= (unsigned char)(1 << (7 - x));
            }
            ((unsigned char *)0x8000)[col * 256 + dst_ofs] = p3;
            ((unsigned char *)0xA000)[col * 256 + dst_ofs] = p2;
            ((unsigned char *)0xC000)[col * 256 + dst_ofs] = p1;
            ((unsigned char *)0xE000)[col * 256 + dst_ofs] = p0;
        }

        if (r == 0) break;
    }
}

/* ----------------------------- MAIN ---------------------------------- */

int main(void)
{
    /* Инициализация: чёрный экран, затем палитра огня. */
    graph_set_black_palette();
    gfx_clear(0);
    graph_set_palette(fire_palette);

    rnd_init();

    /* Основной цикл: один кадр огня за фрейм (50 Гц). */
    for (;;) {
        unsigned int cur = frame_count;
        while (frame_count == cur)
            intrinsic_halt();

        fire_frame();

        /* Сбиваем индекс ГСЧ, чтобы кадры не повторялись.
         * fire_frame делает 65280 вызовов rnd_next (255 × 256),
         * поэтому rnd_idx возвращается в ту же позицию каждый кадр. */
        rnd_idx += frame_count & 0x37;
    }

    return 0;
}
