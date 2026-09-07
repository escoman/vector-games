/*
 * fire.c — демонстрация алгоритма горения огня для Вектора-06Ц.
 *
 * Зона огня 256×128, прижата к нижнему краю экрана.
 * Вся работа — напрямую через VRAM (без RAM-буферов).
 *
 * Алгоритм обрабатывает одну битовую плоскость за вызов.
 * Каждый пиксель — 1 бит; 8 пикселей обрабатываются
 * побитово за одну операцию (байтовый уровень).
 *
 *   1. Сид строки base_ht случайными байтами.
 *   2. Строки base_ht+1 .. base_ht+height-1: мажоритарное
 *      усреднение 3 соседей строки ниже, затухание.
 *
 * Вызов fire_frame(base) для каждой плоскости позволяет
 * комбинировать 1–4 плоскости для разной глубины цвета.
 */

#include "v06.h"

/* ----------------------------- ПАЛИТРА --------------------------------
 * 16 цветов. Формат V06: BB_GGG_RRR.
 * Для одноплоскостного режима достаточно цветов 0 и 1.
 * --------------------------------------------------------------- */

static const unsigned char fire_palette[16] = {
    V06_RGB(0, 0, 0),   /*  0: чёрный                */
    V06_RGB(7, 3, 0),   /*  1: оранжевый             */
    V06_RGB(7, 6, 0),   /*  2: жёлто-оранжевый       */
    V06_RGB(7, 7, 2),   /*  3: светло-жёлтый         */
    V06_RGB(4, 1, 0),   /*  4: красный               */
    V06_RGB(6, 2, 0),   /*  5: тёмно-оранжевый       */
    V06_RGB(7, 5, 0),   /*  6: ярко-красный          */
    V06_RGB(7, 7, 3),   /*  7: белёсый               */
    V06_RGB(1, 0, 0),   /*  8: тёмный дым            */
    V06_RGB(2, 1, 0),   /*  9: бордовой дым          */
    V06_RGB(5, 1, 0),   /* 10: ярко-красный доп.     */
    V06_RGB(6, 7, 3),   /* 11: почти белый           */
    V06_RGB(7, 4, 0),   /* 12: светло-оранжевый      */
    V06_RGB(7, 6, 1),   /* 13: жёлтый                */
    V06_RGB(6, 7, 3),   /* 14: почти белый (корр.)   */
    V06_RGB(7, 7, 3)    /* 15: белое пламя            */
};

/* ------------------------------ ГСЧ -----------------------------------
 * Предгенерированная таблица случайных чисел (256 байт).
 * --------------------------------------------------------------- */

unsigned char rnd_table[256];
unsigned char rnd_idx;

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

#define rnd_next()  (rnd_table[rnd_idx++])

/* ----------------------- VRAM-адреса плоскостей ----------------------- */

#define PLANE3_BASE  0x8000u   /* бит 3 */
#define PLANE2_BASE  0xA000u   /* бит 2 */
#define PLANE1_BASE  0xC000u   /* бит 1 */
#define PLANE0_BASE  0xE000u   /* бит 0 */

/* ----------------------- ПОБИТОВОЕ УСРЕДНЕНИЕ -------------------------
 * Мажоритарная функция: бит результата = 1, если хотя бы
 * два из трёх входных битов = 1.
 * --------------------------------------------------------------- */

#define MAJORITY(l, c, r)  (((l) & (c)) | ((l) & (r)) | ((c) & (r)))

/* ----------------------------- КАДАР ОГНЯ -----------------------------
 * Обрабатывает одну битовую плоскость.
 *
 * plane_base — базовый адрес плоскости (0x8000, 0xA000, 0xC000, 0xE000).
 * decay — сила затухания (0x00 = макс., 0xFF = нет затухания).
 * base_ht — высота нижней строки огня (0 = низ экрана).
 * height — сколько строк обрабатывать вверх от base_ht.
 *
 * Адресация: byte_col × 256 + ofs. ofs = 0 — низ, +256 — след. столбец.
 *
 * Алгоритм (байтовый, 8 пикселей за операцию):
 *   1. Сид строки base_ht случайными байтами.
 *   2. Строки base_ht+1 .. base_ht+height-1: мажоритарное
 *      усреднение 3 соседей (left, center, right) строки ниже,
 *      затухание.
 * --------------------------------------------------------------- */

static void fire_frame(unsigned int plane_base, unsigned char decay,
                       unsigned char base_ht, unsigned char height)
{
    unsigned char *p = (unsigned char *)plane_base;
    unsigned char ofs, col;
    unsigned char left, center, right, avg;
    unsigned char top = (unsigned char)(base_ht + height - 1);

    /* 1. Сид строки base_ht — случайные байты */
    for (col = 0; col < 32; col++) {
        p[col * 256 + base_ht] = rnd_next();
    }

    /* 2. Строки base_ht+1 .. top: огонь поднимается */
    for (ofs = (unsigned char)(base_ht + 1); ofs <= top; ofs++) {
        for (col = 0; col < 32; col++) {
            /* Байт из строки ниже */
            center = p[col * 256 + (ofs - 1)];

            /* Левый сосед: сдвиг влево, бит 0 — из левого столбца */
            left = (unsigned char)(center << 1);
            if (col > 0)
                left |= (unsigned char)(p[(col - 1) * 256 + (ofs - 1)] >> 7);

            /* Правый сосед: сдвиг вправо, бит 7 — из правого столбца */
            right = (unsigned char)(center >> 1);
            if (col < 31)
                right |= (unsigned char)(p[(col + 1) * 256 + (ofs - 1)] << 7);

            /* Мажоритарное усреднение */
            avg = MAJORITY(left, center, right);

            /* Затухание */
            avg &= ~(unsigned char)(~decay & rnd_next());

            p[col * 256 + ofs] = avg;
        }
        /* Сдвиг ГСЧ между строками: ломает периодичность
         * таблицы (256 байт). */
        rnd_idx += 7;
    }
}

/* ----------------------- СРАВНЕНИЕ ОГНЁЙ ----------------------------
 * Читает два огня из VRAM и рисует XOR-разницу на 100 строк выше
 * второго огня. Если разница нулевая — огни идентичны. */

static void compare_fires(unsigned int plane_base,
                          unsigned char ht1, unsigned char ht2,
                          unsigned char height)
{
    unsigned char *p = (unsigned char *)plane_base;
    unsigned char ofs, col;
    unsigned char diff_ofs = (unsigned char)(ht2 + height + 10);

    for (ofs = 0; ofs < height; ofs++) {
        for (col = 0; col < 32; col++) {
            unsigned char a = p[col * 256 + (unsigned char)(ht1 + ofs)];
            unsigned char b = p[col * 256 + (unsigned char)(ht2 + ofs)];
            p[col * 256 + (unsigned char)(diff_ofs + ofs)] = a ^ b;
        }
    }
}

/* ----------------------- ASM-КОПИЯ fire_frame -----------------------
 * Реализация в fire.asm (сгенерирована компилятором, далее оптимизируется).
 * Алгоритм идентичен fire_frame(). */

extern void fire_frame_asm(unsigned int plane_base, unsigned char decay,
                           unsigned char base_ht, unsigned char height) __z88dk_callee;

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
        gfx_next_frame();

        /* Сохраняем состояние ГСЧ, чтобы оба огня получили
         * одинаковые случайные данные. */
        {
            unsigned char saved_rnd = rnd_idx;

            /* Огонь C: ofs 0..15 */
            fire_frame(PLANE0_BASE, 128, 0, 16);

            /* Восстанавливаем ГСЧ для ASM-копии */
            rnd_idx = saved_rnd;

            /* Огонь ASM-копия: ofs 100..115 */
            fire_frame_asm(PLANE0_BASE, 128, 100, 16);
        }

        /* Сравнение: XOR-разница на ofs ~126..141 */
        compare_fires(PLANE0_BASE, 0, 100, 16);

        /* Сдвигаем ГСЧ, чтобы кадры не повторялись */
        rnd_idx += 0x37;
    }

    return 0;
}
