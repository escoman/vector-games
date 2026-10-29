/*
 * main.c — spr-speed: бенчмарк РЕАЛ-РАСТР стоимости вывода подсистемы
 * beam-sprites (lib/gfx/spr.asm + lib/gfx/spr.c). Baseline перед переводом
 * spr на asm и сменой формата данных спрайтов на «готовый к выводу».
 *
 * Методика (как Э0-калибровка demo-spr, ТЗ putup/BEAM_TZ.MD §4):
 *   КР580ВИ53 канал 2 = «секундомер растра», 96 тиков/строку, пущен в VBlank
 *   (frame_handler -> timer_start). Пачка из R_<x> однотипных операций стартует
 *   сразу после v06_wait_frame (таймер обнулён), timer_elapsed() до/после =>
 *   тики. Итог в volatile bm_<x>. Строки/операцию = bm_<x> / R_<x> / 96.
 *   ВАЖНО: пачка обязана уместиться в один кадр (< ~280 строк), иначе таймер
 *   перезагрузится на следующем VBlank и замер завернётся — репы R_<x> выбраны
 *   под это. Офлайн v06_emu НЕ годится (не считает VRAM-wait-states) — только
 *   живой растр через отладчик.
 *
 * Что меряем (матрица «размер × плоскости × flat/OR», плюс накладные):
 *   bm_flat_raw    — spr_glyph_at, raw 4-плоскости (8x8). Пол за вызов.
 *   bm_flat_compact— spr_glyph_at, compact-тег (1 плоск. источника, 3 нуля).
 *                    Разница с raw => цена записи пустых плоскостей (бит наличия
 *                    в новом формате их ПРОПУСТИТ).
 *   bm_or_raw      — spr_glyph_at_or, OR 4-плоскости (герой-класс).
 *   bm_2x2_flat    — 16x16 (2x2 глифа) четырьмя ОТДЕЛЬНЫМИ spr_glyph_at. Если
 *                    ≈ 4×bm_flat_raw => весь setup платится N раз (нет
 *                    амортизации) — это и режет новый формат (1 setup/спрайт).
 *   bm_bg_cell     — путь фона: cell_dst + lookup слова + spr_glyph_at на клетку
 *                    (адресация+таблица+blit), ×8 клеток.
 *   bm_update      — spr_update(): скан/дифференциал O(SPR_MAX) на кадр.
 *
 * После замера ROM крутится в v06_wait_frame, значения bm_* стабильны — читаем
 * из отладчика (debug_read_memory_range по адресам из spr-speed.map).
 */

#include "v06.h"

/* Blit-примитивы из spr.asm (z88dk classic, caller-cleanup, args: dst, glyph). */
extern void spr_glyph_at(unsigned int dst, unsigned int glyph);
extern void spr_glyph_at_or(unsigned int dst, unsigned int glyph);

/* Прототип нового dense-ядра (spr_new.asm, формат docs/SPR_FORMAT.MD §3/§4):
 * один setup на спрайт, пропуск отсутствующих плоскостей, вертикальный прогон
 * на столбец. dense-путь: [0]FLAGS [1]COLS [2]DEPTH(тайл-ряды) [3..]DATA. */
extern void spr_blit_dense(unsigned int dst, unsigned int desc);

/* SMC-прототип (spr_smc.asm): специализировать ядро под дескриптор ОДИН раз
 * (spr_patch8), затем гонять запечённый 8x8-блит (spr_blit8_smc) без разбора
 * флагов/указателей. absent-плоскости заблокированы (jmp), после последней
 * наличной — ранний ret. */
extern void spr_patch8(unsigned int desc);
extern void spr_blit8_smc(unsigned int dst);

/* Боевое dense-ядро Фазы 1 (lib/gfx/spr_fmt.asm, docs/SPR_FORMAT.MD §4):
 * register-resident, развёрнутый 8-байтовый копир, пропуск absent-плоскостей,
 * БЕЗ самомодификации (SMC/RST — Фаза 3). dst = ВЕРХ левого столбца (база П3),
 * прогон СВЕРХУ ВНИЗ (dcx h). То же API (dst, desc), что spr_blit_dense. */
extern void spr_blit(unsigned int dst, unsigned int desc);

/* ------------------------------ ПАЛИТРА -------------------------------- */
static unsigned char pal16[16] = {
    V06_RGB(0, 0, 0), V06_RGB(0, 0, 0), V06_RGB(0, 0, 0), V06_RGB(0, 0, 0),
    V06_RGB(6, 2, 1), V06_RGB(2, 5, 0), V06_RGB(7, 7, 0), V06_RGB(1, 1, 3),
    V06_RGB(7, 2, 2), V06_RGB(2, 7, 3), V06_RGB(7, 1, 3), V06_RGB(4, 4, 2),
    V06_RGB(7, 7, 3), V06_RGB(0, 0, 0), V06_RGB(0, 0, 0), V06_RGB(0, 0, 0)
};

/* --------------------- SCRATCH-ГЛИФЫ (32B plane-major) ----------------- */
/* Чётная база обязательна: бит0 слова = compact-тег. */
#define TG_SOLID  0
#define TG_OR     1
#define TILES_N   2
static unsigned char tiles_mem[TILES_N * 32 + 1];
static unsigned char *tiles;

static const unsigned char m_solid[8] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};
static const unsigned char m_ball[8]  = {0x3C,0x7E,0xFF,0xFF,0xFF,0xFF,0x7E,0x3C};

static void build_tile(unsigned char idx, const unsigned char *rows, unsigned char col)
{
    unsigned char *t = tiles + (unsigned int)idx * 32u;
    unsigned char r;
    for (r = 0; r < 8; ++r) {
        t[r]       = (col & 0x08) ? rows[r] : 0;
        t[8u + r]  = (col & 0x04) ? rows[r] : 0;
        t[16u + r] = (col & 0x02) ? rows[r] : 0;
        t[24u + r] = (col & 0x01) ? rows[r] : 0;
    }
}

/* OR-формат: П0 = ¬S (маска), П1/П2 = S (цвет), П3 = 0. */
static void build_tile_or(unsigned char idx, const unsigned char *rows, unsigned char col)
{
    unsigned char *t = tiles + (unsigned int)idx * 32u;
    unsigned char r;
    for (r = 0; r < 8; ++r) {
        t[r]       = (col & 0x08) ? rows[r] : 0;
        t[8u + r]  = (col & 0x04) ? rows[r] : 0;
        t[16u + r] = (col & 0x02) ? rows[r] : 0;
        t[24u + r] = (unsigned char)~rows[r];
    }
}

/* --------------------- МИНИ-УРОВЕНЬ (для spr_update) ------------------- */
#define WORLD_COLS  32
#define WORLD_ROWS  64
static unsigned char mapbuf[WORLD_ROWS * WORLD_COLS];
static const spr_pat_t upats[] = {
    {0, 0, TG_SOLID, 0},
    {0, 0, TG_OR,    0x42}          /* приор 2 | OR */
};
static const unsigned int upat_off[] = {0, 1, 2};
static spr_level_t lvl;

/* ------------- ДЕСКРИПТОРЫ НОВОГО ФОРМАТА (dense, spr_new.asm) ---------- */
/* [0]FLAGS [1]COLS [2]DEPTH(тайл-ряды) [3..]DATA (по наличным плоскостям).
 * Данные те же байты, что raw-тайл => apples-to-apples с baseline-сценами. */
static unsigned char desc_bg[3 + 32];        /* 1x1 тайл-ряд, 4 плоскости   */
static unsigned char desc_bg1[3 + 8];        /* 1x1 тайл-ряд, 1 плоскость   */
static unsigned char desc_spr16[3 + 128];    /* 2x2 тайл-ряда, 4 плоскости  */
static unsigned char desc_rt[3 + 64];        /* round-trip: 4 пл. x DEPTH=2, различимые байты */
static unsigned char desc_or8[3 + 24];       /* 8x8 OR: П2,П1 цвет + П0 маска (П3 пропущен) */
static unsigned char desc_or16[3 + 96];      /* 16x16 OR: COLS=2 DEPTH=2, П2/П1 цвет + П0 маска */
static unsigned char desc_or_rt[3 + 24];     /* OR round-trip: color=0x30, mask=0x0F */
/* SPARSE (FLAGS bit5): per-column TABLE (TOP,LEN) в тайл-рядах, DATA = desc+3+COLS*2.
 * COLS=2: col0 (TOP=0,LEN=2)=16B, col1 (TOP=1,LEN=1)=8B. Одна плоскость П3.
 * Проверяет sparse-ветку + sbf_sub_top_o (TOP=1) + непрерывный DATA-курсор. */
static unsigned char desc_sparse[3 + 4 + 24];
static unsigned char *bg_desc_tab[2];        /* код карты -> дескриптор      */

/* --------------------------- РЕЗУЛЬТАТЫ (volatile) --------------------- */
/* Объявлены подряд — в bss лежат рядом, удобно читать одним range. */
volatile unsigned int bm_flat_raw;
volatile unsigned int bm_flat_compact;
volatile unsigned int bm_or_raw;
volatile unsigned int bm_2x2_flat;
volatile unsigned int bm_bg_cell;
volatile unsigned int bm_update;
volatile unsigned int bm_bg_dense;   /* НОВЫЙ dense-путь клетки фона       */
volatile unsigned int bm_spr16_new;  /* НОВЫЙ sprite-major 16x16 (1 вызов)  */
volatile unsigned int bm_dense_iso;  /* НОВЫЙ изолированный dense-блит (4 пл.) */
volatile unsigned int bm_dense1_iso; /* НОВЫЙ изолированный dense-блит (1 пл.) */
volatile unsigned int bm_smc4_iso;   /* SMC 8x8, 4 плоскости (patch desc_bg)   */
volatile unsigned int bm_smc1_iso;   /* SMC 8x8, 1 плоскость (patch desc_bg1)  */
volatile unsigned int bm_smc_patch;  /* цена ОДНОГО spr_patch8 (×R_PATCH)      */
volatile unsigned int bm_fmt4_iso;   /* spr_blit 8x8, 4 плоскости (vs bm_flat_raw)   */
volatile unsigned int bm_fmt1_iso;   /* spr_blit 8x8, 1 плоскость (vs bm_flat_compact) */
volatile unsigned int bm_fmt16;      /* spr_blit 16x16 (vs bm_2x2_flat)              */
volatile unsigned int bm_rt_dst;     /* TOP-адрес round-trip блита (читаем VRAM оттуда) */
volatile unsigned int bm_or8_new;    /* spr_blit OR 8x8 (П3 пропущен) vs bm_or_raw */
volatile unsigned int bm_or16_new;   /* spr_blit OR 16x16 (1 вызов) vs bm_or2x2_raw */
volatile unsigned int bm_or2x2_raw;  /* baseline: 4× spr_glyph_at_or на 2x2-блок */
volatile unsigned int bm_or16_rt_dst;/* TOP-адрес OR 16x16 round-trip (читаем VRAM) */
volatile unsigned int bm_or_rt_dst;  /* TOP-адрес OR round-trip (читаем VRAM) */
volatile unsigned int bm_iso_old_dst;/* база 2x2 блока, старый путь (4× spr_glyph_at_or) */
volatile unsigned int bm_iso_new_dst;/* TOP-база 2x2, новый путь (1× spr_blit desc_or16) */
volatile unsigned int bm_sparse_rt_dst;/* TOP-адрес sparse round-trip (читаем VRAM) */
volatile unsigned int bm_seam_rt_dst;/* TOP-адрес flat seam round-trip (grow&31=31) */
volatile unsigned int bm_seam_or_rt_dst;/* TOP-адрес OR seam round-trip (grow&31=31) */
volatile unsigned int bm_iso_flat_dst;/* TOP-база одиночного flat spr_blit (преамбула) */
volatile unsigned int bm_magic;      /* 0xBEEF = замер выполнен            */

/* Репы (делим на них при пересчёте тиков в строки). */
#define R_FLAT     24u
#define R_COMPACT  30u
#define R_OR       14u
#define R_2X2       6u               /* юнит = 4 вызова                    */
#define R_BGCELL   12u              /* юнит = 1 клетка (адрес+lookup+blit); арифметика 8080 *32/сдвиг ~ +500т/клетку => 24 репа переборщили бы кадр */
#define R_UPDATE   24u
#define R_BGDENSE   4u              /* scene 7: dense-клетка; репы урезаны — прототип ядра дороже spr_glyph_at, пачка должна влезть в кадр */
#define R_SPR16     3u              /* scene 8: 1 вызов spr_blit_dense на 16x16 (128 записей) */
#define R_DENSE_ISO 6u              /* scene 9: изолированный dense-блит (прямое сравнение с bm_flat_raw) */
#define R_DENSE1    8u              /* scene 10: изолированный dense-блит, 1 плоскость (выигрыш plane-skip) */
#define R_SMC4     24u              /* scene 11: SMC 8x8 4-плоскости (сравнение с bm_flat_raw) */
#define R_SMC1     40u              /* scene 12: SMC 8x8 1-плоскость (сравнение с bm_flat_compact) */
#define R_PATCH    20u              /* scene 13: стоимость spr_patch8 (амортизируется на спрайт) */
#define R_FMT4      8u              /* scene 14: spr_blit 8x8 4-плоскости (репы урезаны — ядро general, пачка влезает в кадр) */
#define R_FMT1     24u              /* scene 15: spr_blit 8x8 1-плоскость */
#define R_FMT16     4u              /* scene 16: spr_blit 16x16 (COLS=2,DEPTH=2,4 пл.) */
#define R_OR8      14u              /* scene 18: spr_blit OR 8x8 (против bm_or_raw, R_OR=14) */
#define R_OR2X2     3u              /* scene 20: baseline 4× spr_glyph_at_or (юнит = 4 вызова) */
#define R_OR16      4u              /* scene 21: spr_blit OR 16x16 (1 вызов) */

/* Кольцевой адрес приёмника (формула из spr.c cell_dst). */
static unsigned int ring_dst(unsigned char gcol, unsigned char grow)
{
    return 0x8000u + ((unsigned int)gcol << 8) +
           (unsigned int)(248 - 8 * (grow & 31));
}

/* Вариант «ВЕРХ» для нового ядра (top+dec, docs/SPR_FORMAT.MD §2):
 * dst = адрес ВЕРХНЕЙ экранной строки тайл-ряда = 255 - 8*(grow&31)
 * (на +7 выше ring_dst, который даёт НИЗ). Прогон идёт вниз (dcx h). */
static unsigned int ring_dst_top(unsigned char gcol, unsigned char grow)
{
    return 0x8000u + ((unsigned int)gcol << 8) +
           (unsigned int)(255 - 8 * (grow & 31));
}

/* ------------------------------ CADR-ISR ------------------------------- */
static void spr_frame(void)
{
    timer_start();          /* секундомер растра: старт на каждый VBlank */
    kbd_scan_now();
}

/* ------ ИЗОЛИРОВАННЫЕ ОДИНОЧНЫЕ ПРОГОНЫ (замер окна экспозиции VRAM) -------
 * Выполняются ОДИН раз в самом конце measure(). Нужны, чтобы через
 * breakpoint+beam_state снять v_cycle ПЕРВОЙ и ПОСЛЕДНЕЙ записи байта спрайта
 * = окно, в течение которого VRAM спрайта «в потоке» у луча (метрика
 * непрерывности записи, а не полного времени функции). Старый путь рисует 2x2
 * четырьмя ОТДЕЛЬНЫМИ spr_glyph_at_or — подготовка каждого глифа (parse+маска)
 * попадает ВНУТРЬ окна между записями. Новый — ОДНИМ spr_blit: подготовка
 * фронтальная (ДО первой записи), окно = непрерывный залп. */
static void iso_old_2x2(void)
{
    unsigned int g = (unsigned int)(tiles + (unsigned int)TG_OR * 32u);
    unsigned int b = bm_iso_old_dst;
    spr_glyph_at_or(b, g);                  /* (col0,row0) */
    spr_glyph_at_or(b + 0x0100u, g);        /* (col1,row0) */
    spr_glyph_at_or(b - 8u, g);             /* (col0,row1) */
    spr_glyph_at_or(b + 0x00F8u, g);        /* (col1,row1) = +0x100-8 */
}

static void iso_new_2x2(void)
{
    spr_blit(bm_iso_new_dst, (unsigned int)desc_or16);
}

/* Одиночный flat spr_blit 8x8 (4 пл.) — якорь для замера преамбулы
 * SPR_LEAD_BLIT_FLAT (вход -> первая запись VRAM) через breakpoint+beam_state. */
static void iso_new_flat(void)
{
    spr_blit(bm_iso_flat_dst, (unsigned int)desc_bg);
}

/* ------------------------------ ЗАМЕРЫ --------------------------------- */
/* Каждая пачка — строго после v06_wait_frame (таймер обнулён ISR'ом). */
static void measure(void)
{
    unsigned int e0, e1;
    unsigned int g, dst;
    unsigned int d0, d1, d2, d3;
    unsigned int gw;
    unsigned int dp;
    unsigned char i, j;

    g   = (unsigned int)(tiles + (unsigned int)TG_SOLID * 32u);   /* raw-база */
    dst = ring_dst(31, 0);                                        /* scratch  */

    /* 1) flat raw 4-плоскости */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_FLAT; ++i) spr_glyph_at(dst, g);
    e1 = timer_elapsed();
    bm_flat_raw = e1 - e0;

    /* 2) flat compact (тег bit0=1): 1 плоск. источника + 3 нуля */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_COMPACT; ++i) spr_glyph_at(dst, g | 1u);
    e1 = timer_elapsed();
    bm_flat_compact = e1 - e0;

    /* 3) OR 4-плоскости */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_OR; ++i) spr_glyph_at_or(dst, tiles + (unsigned int)TG_OR * 32u);
    e1 = timer_elapsed();
    bm_or_raw = e1 - e0;

    /* 4) 16x16 = 4 отдельных вызова по глифам 2x2-блока (клетки 30,31 x 0,1) */
    d0 = ring_dst(30, 0); d1 = ring_dst(31, 0);
    d2 = ring_dst(30, 1); d3 = ring_dst(31, 1);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_2X2; ++i) {
        spr_glyph_at(d0, g);
        spr_glyph_at(d1, g);
        spr_glyph_at(d2, g);
        spr_glyph_at(d3, g);
    }
    e1 = timer_elapsed();
    bm_2x2_flat = e1 - e0;

    /* 5) путь клетки фона: адрес + lookup слова + blit (1 клетка/реп,
     *    колонка меняется, чтобы не зацикливать кэш на одном месте) */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_BGCELL; ++i) {
        j   = (unsigned char)(24 + (i & 7));
        gw  = (unsigned int)(tiles + (unsigned int)mapbuf[5 * WORLD_COLS + j] * 32u);
        dst = ring_dst(j, 5);
        spr_glyph_at(dst, gw);
    }
    e1 = timer_elapsed();
    bm_bg_cell = e1 - e0;

    /* 6) spr_update: скан/дифференциал O(SPR_MAX) + фазы анимации */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_UPDATE; ++i) spr_update();
    e1 = timer_elapsed();
    bm_update = e1 - e0;

    /* 7) НОВЫЙ dense-путь клетки фона: тот же цикл что (5), но spr_blit_dense
     *    с dense-дескриптором (1x1 тайл-ряд, 4 плоскости). Delta к bm_bg_cell
     *    = выигрыш ядра (1 setup, прогон) + дешёвый lookup указателя. */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_BGDENSE; ++i) {
        j   = (unsigned char)(24 + (i & 7));
        dp  = (unsigned int)bg_desc_tab[mapbuf[5 * WORLD_COLS + j]];
        dst = ring_dst(j, 5);
        spr_blit_dense(dst, dp);
    }
    e1 = timer_elapsed();
    bm_bg_dense = e1 - e0;

    /* 8) НОВЫЙ sprite-major 16x16: ОДИН spr_blit_dense (2 столбца x 2 тайл-ряда
     *    x 4 плоскости) против 4 отдельных spr_glyph_at в (4). Delta к
     *    bm_2x2_flat = экономия setup (1 вместо 4) + длинные прогоны. */
    dst = ring_dst(30, 0);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_SPR16; ++i) spr_blit_dense(dst, (unsigned int)desc_spr16);
    e1 = timer_elapsed();
    bm_spr16_new = e1 - e0;

    /* 9) ИЗОЛИРОВАННЫЙ dense-блит: dst готов (без адресной арифметики),
     *    desc_bg (1x1 тайл-ряд, 4 плоск., 32 записи) — прямое сравнение с
     *    bm_flat_raw (spr_glyph_at изолированно, те же 32 записи). Показывает
     *    чистую цену ядра без lookup/ring_dst. */
    dst = ring_dst(28, 0);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_DENSE_ISO; ++i) spr_blit_dense(dst, (unsigned int)desc_bg);
    e1 = timer_elapsed();
    bm_dense_iso = e1 - e0;

    /* 10) ИЗОЛИРОВАННЫЙ dense-блит, ОДНА плоскость (П3): выигрыш формата от
     *     пропуска absent-плоскостей vs spr_glyph_at compact (887, пишет 32B). */
    dst = ring_dst(26, 0);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_DENSE1; ++i) spr_blit_dense(dst, (unsigned int)desc_bg1);
    e1 = timer_elapsed();
    bm_dense1_iso = e1 - e0;

    /* 11) SMC 8x8, 4 плоскости: patch(desc_bg) ОДИН раз, затем запечённый блит.
     *    Прямое сравнение с bm_flat_raw (spr_glyph_at, те же 32 записи). */
    dst = ring_dst(24, 0);
    spr_patch8((unsigned int)desc_bg);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_SMC4; ++i) spr_blit8_smc(dst);
    e1 = timer_elapsed();
    bm_smc4_iso = e1 - e0;

    /* 12) SMC 8x8, ОДНА плоскость (П3): patch(desc_bg1), ранний ret после П3.
     *    Против bm_flat_compact (spr_glyph_at пишет 32B: 1 маска + 3 нуля). */
    dst = ring_dst(22, 0);
    spr_patch8((unsigned int)desc_bg1);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_SMC1; ++i) spr_blit8_smc(dst);
    e1 = timer_elapsed();
    bm_smc1_iso = e1 - e0;

    /* 13) стоимость spr_patch8 (платится ОДИН раз на дескриптор, не на блит). */
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_PATCH; ++i) spr_patch8((unsigned int)desc_bg);
    e1 = timer_elapsed();
    bm_smc_patch = e1 - e0;

    /* 14) ИЗОЛИРОВАННЫЙ spr_blit (боевое ядро Фазы 1), 8x8 4 плоскости:
     *    прямое сравнение с bm_flat_raw (spr_glyph_at, те же 32 записи). */
    dst = ring_dst_top(20, 0);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_FMT4; ++i) spr_blit(dst, (unsigned int)desc_bg);
    e1 = timer_elapsed();
    bm_fmt4_iso = e1 - e0;

    /* 15) spr_blit 8x8, ОДНА плоскость (П3): против bm_flat_compact (887). */
    dst = ring_dst_top(19, 0);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_FMT1; ++i) spr_blit(dst, (unsigned int)desc_bg1);
    e1 = timer_elapsed();
    bm_fmt1_iso = e1 - e0;

    /* 16) spr_blit 16x16 (COLS=2,DEPTH=2,4 пл.: против bm_2x2_flat (4×spr_glyph_at). */
    dst = ring_dst_top(18, 0);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_FMT16; ++i) spr_blit(dst, (unsigned int)desc_spr16);
    e1 = timer_elapsed();
    bm_fmt16 = e1 - e0;

    /* DEBUG: закомментировано для поиска сцены краха */
#if 0
    /* 17) ROUND-TRIP проверка порядка байтов (docs/SPR_FORMAT.MD §8.2 риск №1):
     *    desc_rt (4 пл., COLS=1, DEPTH=2, различимые байты) блитится в VRAM по
     *    адресу bm_rt_dst. После оседания ROM читаем VRAM и сверяем: байт0 =
     *    ВЕРХ, прогон вниз (dcx h), шаг плоскости +0x2000, порядок П3/П2/П1/П0. */
    bm_rt_dst = ring_dst_top(16, 0);
    spr_blit(bm_rt_dst, (unsigned int)desc_rt);
#endif

    /* DEBUG: закомментировано для поиска сцены краха */
#if 0
    /* 18) НОВЫЙ OR-прогон 8x8 (spr_blit, FLAGS bit6): П3 пропущен, П2/П1 =
     *    (dst AND mask) OR color, П0 = dst AND mask. Против bm_or_raw (1563,
     *    spr_glyph_at_or пишет все 4 плоскости). dst — TOP-вариант. */
    dst = ring_dst_top(14, 0);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_OR8; ++i) spr_blit(dst, (unsigned int)desc_or8);
    e1 = timer_elapsed();
    bm_or8_new = e1 - e0;

    /* 19) ROUND-TRIP OR-композита: сначала плотная заливка bg=0xFF во все 4
     *    плоскости (desc_bg), затем OR-блит desc_or_rt. Читаем VRAM по
     *    bm_or_rt_dst: П3=0xFF (absent), П2=П1=0x3F, П0=0x0F. */
    bm_or_rt_dst = ring_dst_top(12, 0);
    spr_blit(bm_or_rt_dst, (unsigned int)desc_bg);      /* bg = 0xFF, 4 пл. */
    spr_blit(bm_or_rt_dst, (unsigned int)desc_or_rt);   /* OR поверх */

    /* 20) BASELINE 16x16 OR: 4 отдельных spr_glyph_at_or на 2x2-блок (клетки
     *    8,9 x 0,1) — столько же раз setup, сколько в плоском пути. */
    d0 = ring_dst(8, 0); d1 = ring_dst(9, 0);
    d2 = ring_dst(8, 1); d3 = ring_dst(9, 1);
    g  = tiles + (unsigned int)TG_OR * 32u;
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_OR2X2; ++i) {
        spr_glyph_at_or(d0, g);
        spr_glyph_at_or(d1, g);
        spr_glyph_at_or(d2, g);
        spr_glyph_at_or(d3, g);
    }
    e1 = timer_elapsed();
    bm_or2x2_raw = e1 - e0;

    /* 21) НОВЫЙ sprite-major OR 16x16: ОДИН spr_blit (COLS=2,DEPTH=2, П3 пропущен)
     *    против 4 отдельных spr_glyph_at_or в (20). Delta = экономия setup (1
     *    вместо 4) + длинные прогоны (16 байт) вместо 8-байтовых. */
    dst = ring_dst_top(10, 0);
    v06_wait_frame();
    e0 = timer_elapsed();
    for (i = 0; i < R_OR16; ++i) spr_blit(dst, (unsigned int)desc_or16);
    e1 = timer_elapsed();
    bm_or16_new = e1 - e0;

    /* 22) ROUND-TRIP OR 16x16: bg=0xFF во все 4 пл. 2x2-блока (desc_spr16), затем
     *    OR desc_or16 (color=0x30, mask=0x0F, COLS=2 DEPTH=2). Проверяет, что
     *    курсоры mask(BC)/color(DE) синхронны на нескольких столбцах и рядах.
     *    Ожид: П3=0xFF, П2=П1=0x3F, П0=0x0F (в обоих столбцах, во всех рядах). */
    bm_or16_rt_dst = ring_dst_top(6, 0);
    spr_blit(bm_or16_rt_dst, (unsigned int)desc_spr16);  /* bg = 0xFF, 4 пл. 2x2 */
    spr_blit(bm_or16_rt_dst, (unsigned int)desc_or16);   /* OR поверх */

    /* 23/24) ИЗОЛИРОВАННЫЕ одиночные прогоны 2x2 OR для замера окна экспозиции
     *    VRAM (первая→последняя запись) через breakpoint+beam_state. */
    bm_iso_old_dst = ring_dst(8, 0);        /* 0x88F8: 2x2 блок, старый путь  */
    bm_iso_new_dst = ring_dst_top(10, 0);   /* 0x8AFF: 2x2 TOP, новый путь    */
    v06_wait_frame();                       /* якорь луча на начале кадра: окно записи не пересечёт VBlank */
    iso_old_2x2();
    iso_new_2x2();

    /* 25) ROUND-TRIP SPARSE (FLAGS bit5): desc_sparse (COLS=2, TABLE col0 TOP=0
     *    LEN=2, col1 TOP=1 LEN=1, одна плоскость П3). Проверяет sparse-ветку:
     *    per-column (TOP,LEN), sbf_sub_top_o (TOP=1), непрерывный DATA-курсор.
     *    Ожид: col0 (gcol 5) 16B 0xC0..0xCF от offset 255 вниз; col1 (gcol 6)
     *    8B 0xD0..0xD7 от offset 247 (TOP=1) вниз. */
    bm_sparse_rt_dst = ring_dst_top(5, 0);
    spr_blit(bm_sparse_rt_dst, (unsigned int)desc_sparse);

    /* 26) ROUND-TRIP SEAM (flat): desc_rt (COLS=1 DEPTH=2) по grow&31=31.
     *    offset=7, seam=1, LEN=2 -> row=1 (offset 7..0), seg=1 (ребаз на 255,
     *    offset 255..248). Проверяет §5 шов кольца в плоском пути. */
    bm_seam_rt_dst = ring_dst_top(4, 31);
    spr_blit(bm_seam_rt_dst, (unsigned int)desc_rt);

    /* 27) ROUND-TRIP SEAM (OR): bg=0xFF (desc_spr16, COLS=2 DEPTH=2) по grow&31=31,
     *    затем OR desc_or16. Шов в OR/AND-ветках (sbf_plane_or/sbf_plane_and).
     *    Ожид: П3=0xFF (absent), П2=П1=0x3F, П0=0x0F, оба тайл-ряда (шов-wrap). */
    bm_seam_or_rt_dst = ring_dst_top(3, 31);
    spr_blit(bm_seam_or_rt_dst, (unsigned int)desc_spr16);   /* bg = 0xFF, 4 пл. */
    spr_blit(bm_seam_or_rt_dst, (unsigned int)desc_or16);    /* OR поверх */

    /* 28) ИЗОЛИРОВАННЫЙ одиночный flat spr_blit (преамбула SPR_LEAD_BLIT_FLAT). */
    bm_iso_flat_dst = ring_dst_top(2, 0);
    v06_wait_frame();
    iso_new_flat();
#endif

    bm_magic = 0xBEEFu;
}

/* -------------------------------- MAIN --------------------------------- */
int main(void)
{
    unsigned int i;
    unsigned int k;

    /* чётная база тайлов */
    tiles = tiles_mem + ((unsigned int)tiles_mem & 1u);
    build_tile(TG_SOLID, m_solid, 0x0F);     /* все 4 плоскости            */
    build_tile_or(TG_OR, m_ball, 0x06);      /* жёлто-красный OR-герой     */

    /* дескрипторы нового dense-формата (данные = те же байты, что raw-тайл) */
    desc_bg[0] = 0x0F; desc_bg[1] = 1; desc_bg[2] = 1;      /* 1x1, 4 плоск. */
    for (k = 0; k < 32u; ++k) desc_bg[3u + k] = tiles[k];
    bg_desc_tab[TG_SOLID] = desc_bg;

    desc_bg1[0] = 0x01; desc_bg1[1] = 1; desc_bg1[2] = 1;   /* 1x1, 1 плоск. */
    for (k = 0; k < 8u; ++k) desc_bg1[3u + k] = tiles[k];

    desc_spr16[0] = 0x0F; desc_spr16[1] = 2; desc_spr16[2] = 2; /* 2x2, 4 пл. */
    for (k = 0; k < 128u; ++k) desc_spr16[3u + k] = 0xFFu;

    /* round-trip дескриптор: 4 плоскости, COLS=1, DEPTH=2 (16 байт/плоскость).
     * Байты различимы: старший полубайт = плоскость (П3=3,П2=2,П1=1,П0=0),
     * младший = индекс 0..15. Позволяет одним VRAM-дампом проверить и порядок
     * байтов прогона (top+dec), и шаг плоскости +0x2000, и порядок П3/П2/П1/П0. */
    desc_rt[0] = 0x0F; desc_rt[1] = 1; desc_rt[2] = 2;
    for (k = 0; k < 64u; ++k)
        desc_rt[3u + k] = (unsigned char)(((3u - (k >> 4)) << 4) | (k & 0x0Fu));

    /* OR-дескриптор 8x8 (реальный TG_OR: П3=0 пропущен, П2/П1=цвет, П0=маска).
     * FLAGS = bit6 OR | bit1 П2 | bit2 П1 | bit3 П0 = 0x4E. COLS=1 DEPTH=1.
     * DATA: П2(8) П1(8) П0(8) — порядок наличных плоскостей П3,П2,П1,П0. */
    desc_or8[0] = 0x4E; desc_or8[1] = 1; desc_or8[2] = 1;
    for (k = 0; k < 8u; ++k) {
        desc_or8[3u + k]       = tiles[32u + 8u + k];   /* П2 color */
        desc_or8[3u + 8u + k]  = tiles[32u + 16u + k];  /* П1 color */
        desc_or8[3u + 16u + k] = tiles[32u + 24u + k];  /* П0 mask  */
    }

    /* OR round-trip: color=0x30, mask=0x0F (константы). Ожидаемый композит
     * поверх bg=0xFF: П2/П1 = (0xFF&0x0F)|0x30 = 0x3F, П0 = 0xFF&0x0F = 0x0F,
     * П3 = 0xFF (absent, не тронут). */
    desc_or_rt[0] = 0x4E; desc_or_rt[1] = 1; desc_or_rt[2] = 1;
    for (k = 0; k < 8u; ++k) {
        desc_or_rt[3u + k]       = 0x30;   /* П2 color */
        desc_or_rt[3u + 8u + k]  = 0x30;   /* П1 color */
        desc_or_rt[3u + 16u + k] = 0x0F;   /* П0 mask  */
    }

    /* OR 16x16 (COLS=2,DEPTH=2): plane_bytes = 2*2*8 = 32. FLAGS=0x4E (П3 пропущен).
     * DATA: П2 цвет (32) | П1 цвет (32) | П0 маска (32). mask_base = DATA+64.
     * Порядок в плоскости: col0(row0,row1), col1(row0,row1) — по 8 байт. */
    desc_or16[0] = 0x4E; desc_or16[1] = 2; desc_or16[2] = 2;
    for (k = 0; k < 96u; ++k)
        desc_or16[3u + k] = (unsigned char)(k < 64u ? 0x30 : 0x0F);

    /* SPARSE round-trip: FLAGS = bit5(sparse) | bit0(П3) = 0x21. COLS=2, DEPTH=2
     * (footprint, для документации). TABLE (desc+3): col0 (TOP=0,LEN=2),
     * col1 (TOP=1,LEN=1). DATA (desc+7): col0 16B 0xC0..0xCF, col1 8B 0xD0..0xD7.
     * Проверяет sparse-ветку + sbf_sub_top_o (TOP=1) + непрерывный DATA-курсор. */
    desc_sparse[0] = 0x21; desc_sparse[1] = 2; desc_sparse[2] = 2;
    desc_sparse[3] = 0; desc_sparse[4] = 2;   /* col0: TOP=0 LEN=2 */
    desc_sparse[5] = 1; desc_sparse[6] = 1;   /* col1: TOP=1 LEN=1 */
    for (k = 0; k < 16u; ++k)
        desc_sparse[7u + k] = (unsigned char)(0xC0u + k);   /* col0 16B */
    for (k = 0; k < 8u; ++k)
        desc_sparse[23u + k] = (unsigned char)(0xD0u + k);  /* col1 8B  */

    /* тайлмап: сплошной пол (код TG_SOLID) — фон-путь representative */
    for (i = 0; i < WORLD_ROWS * WORLD_COLS; ++i)
        mapbuf[i] = TG_SOLID;

    lvl.pats       = (spr_pat_t *)upats;
    lvl.pat_off    = upat_off;
    lvl.tiles      = (unsigned char *)tiles;
    lvl.map        = mapbuf;
    lvl.rows       = WORLD_ROWS;
    lvl.cols       = WORLD_COLS;
    lvl.beam_sync  = 1;
    lvl.tile_words = 0;                       /* 32B plane-major: code*32   */
    lvl.mask_tab   = 0;
    lvl.anims      = 0;
    lvl.n_anims    = 0;
    lvl.shift_mask = 0;

    gfx_set_mode(GFX_MODE_256_16);
    gfx_set_palette(pal16);

    frame_handler = spr_frame;
    timer_start_sync();

    spr_init(&lvl);
    spr_show(0, 1);  spr_move(0, 16, 16);     /* OR-спрайт поверх (для update)*/
    spr_show(1, 0);  spr_move(1, 8, 10);
    spr_show(2, 0);  spr_move(2, 20, 22);

    measure();

    /* Замер выполнен — держим ROM живым, bm_* стабильны для чтения из RAM. */
    for (;;)
        v06_wait_frame();

    return 0;
}
