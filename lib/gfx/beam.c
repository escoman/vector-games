/*
 * beam.c — beam-подсистема: планировщик/пейсер спрайтов (BEAM_TZ.MD ред.2).
 *
 * Аналог OAM NES: игра объявляет дескрипторы SPR_FORMAT один раз (загрузка
 * уровня) и в цикле меняет только позиции/кадры (beam_move/show/hide/bg_put).
 * Всю растер-магию — тени, diff→план по рядам, erase-до-фона, behind-the-beam
 * пейсинг, бюджет, атомарность — подсистема делает сама. Пиксели пишут ядра
 * spr_blit/spr_blit_mask (единственный writer, ТФ-1).
 *
 * КОНТРАКТ ЦИКЛА (ТЗ §2.2):
 *   frame_handler = свой ISR-хук: timer_start() [+ kbd_scan_now()];
 *   for (;;) {
 *       v06_wait_frame();
 *       game_logic();      // ТОЛЬКО beam_move/show/hide/bg_put/set_cam
 *       beam_update();     // diff экземпляры vs тени -> план по рядам
 *       beam_render();     // исполнение в такт лучу; возврат = конец кадра
 *   }
 *
 * ГЕОМЕТРИЯ. Кольцо VRAM = 256 px = 32 полосы по 8 px = 16 рядов клеток 16px.
 * Адресация контента МИРОВАЯ: ring y = world_y & 0xFF, поэтому при аппаратном
 * скролле (регистр строки, порт 03h) содержимое кольца остаётся на месте —
 * перерисовывается только открывшаяся полоса. Экран (256px) показывает кольцо
 * ЦЕЛИКОМ; скролл лишь вращает его: screen_band = (ring_band − cam_band) & 31.
 * Уровень может быть выше 256px (y экземпляров — мировые, unsigned int), но
 * АКТИВНЫЕ экземпляры игра обязана держать в текущем окне 256px и скрывать
 * остальные (beam_hide): мир на 256px дальше по вертикали — алиас того же
 * кольца.
 *
 * КАМЕРА (beam_set_cam, расширение ТЗ §5). Шаг 8px (полоса). При сдвиге окна
 * открывается одна полоса с алиас-содержимым 256-пиксельной давности: её
 * клетки (целиком, 16px, с пропуском совпадающих по тени ring_cells)
 * перерисовываются в ТОМ ЖЕ кадре в фазе B — в бланкинге после строки 288,
 * когда луч уже вне видимого поля. Запись регистра скролла делает
 * gfx_set_scroll, а в порт 03h он попадает на следующем VBlank (хук
 * kbd_scan_now в frame_handler) — строго ПОСЛЕ фазы B, поэтому полоса
 * становится видимой уже новой. Пейсинг обычных рядов фазы A считает
 * экранные позиции по СТАРОЙ камере (во время кадра регистр ещё не сменён).
 *
 * ПЕЙСИНГ (ТЗ §3.1). Полоса пишется только при elapsed >= bot(s) =
 * TIMER_LINES(48+8s+8) («позади луча») ИЛИ когда top(s) − elapsed −
 * BEAM_LEAD > cost + MARGIN_MIN («успеем до луча»); сомнительная оценка —
 * всегда деградация к behind-the-beam. Решение принимается ОДИН раз на
 * спрайт по его НИЖНЕЙ полосе (ряд-атомарность), целый спрайт при нехватке
 * бюджета переносится в следующий кадр (beam_overbudget++). Mask-путь
 * (attr бит4) — не более BEAM_MASK_LIMIT=2 инстансов на кадр (ТЗ §3.2).
 *
 * RAM: экземпляры/тени/план/тайлмап — статические массивы ниже (BSS вне
 * 0x7000..0x7203 — собственности spr.asm); куча не должна дорастать до
 * 0x7000.
 */

#include "v06.h"

#define BEAM_INST_MAX     16u  /* экземпляров (ТЗ §10.1)                  */
#define BEAM_BANDS        32u  /* 8px-полос кольца                        */
#define BEAM_RING_ROWS    16u  /* 16px-рядов клеток кольца                */
#define BEAM_MAX_CELLS   512u  /* RAM-тайлмап: не более 32x16 клеток      */
#define BEAM_MAX_COLS     16u

/* Калибровки ТЗ §3.1/§4 (BLINK.MD, spr-speed). */
#define BEAM_LEAD_LINES    6u  /* фазовая поправка ISR (+5,3), с запасом   */
#define BEAM_MARGIN_LINES  8u  /* MARGIN_MIN ветки «успеем до луча»       */
#define BEAM_BLANK_LINE  288u  /* бланкинг: видимое поле кончается на 280 */
#define BEAM_MASK_LIMIT    2u  /* mask-инстансов на кадр (ТЗ §3.2)        */

/* Экземпляр (аналог OAM-записи) и его тень последнего commit. */
typedef struct {
    unsigned int y;              /* МИРОВАЯ пиксельная строка верха       */
    unsigned char x;             /* пиксельный x, кратен 8 (кольцо=экран) */
    const beam_pat_t *pat;       /* 0 = скрыт                             */
} beam_slot_t;

static beam_slot_t beam_inst[BEAM_INST_MAX];
static beam_slot_t beam_shad[BEAM_INST_MAX];
static unsigned char beam_committed[BEAM_INST_MAX]; /* тень валидна       */

static const beam_level_t *beam_lvl;
static unsigned char beam_cellmap[BEAM_MAX_CELLS];  /* RAM-копия тайлмапа */

/* Тень содержимого кольца: какой код фона последним нарисован в слоте
 * (ring_row, col). 0xFF = слот испорчен (спрайт/алиас) — перерисовать.
 * По ней открытая скроллом полоса пропускает клетки, совпадающие с алиасом
 * (уровень вертикально повторяется — это почти весь бюджет полосы). */
static unsigned char beam_ring_cells[BEAM_RING_ROWS * BEAM_MAX_COLS];

/* План текущего кадра. */
static unsigned int  beam_erase_mask[BEAM_RING_ROWS]; /* биты колонок клеток */
static unsigned char beam_strip_row[BEAM_RING_ROWS];  /* открытая скроллом  */
static unsigned char beam_band_cost[BEAM_BANDS];      /* строки растра, ~   */
static unsigned char beam_dirty[BEAM_INST_MAX];
static unsigned char beam_inst_band[BEAM_INST_MAX];   /* commit-полоса &31  */
static unsigned char beam_inst_strip[BEAM_INST_MAX];  /* отлож. в фазу B    */

static unsigned int  beam_cam_cur;      /* мировые px, активна в этом кадре */
static unsigned int  beam_cam_pending;  /* новая (gfx_set_scroll уже сделан)*/
static unsigned char beam_overbudget_cnt;
static unsigned char beam_init_pending; /* первая отрисовка — без пейсинга  */

/* ------------------------------------------------------------------ */
/* Вспомогательные                                                     */
/* ------------------------------------------------------------------ */

static unsigned char beam_popcount4(unsigned char m)
{
    unsigned char n = 0;
    while (m) { n += m & 1; m >>= 1; }
    return n;
}

/* Сколько байт VRAM пишет дескриптор (ΣLEN всех прогонов). */
static unsigned int beam_desc_bytes(const unsigned char *d)
{
    unsigned char flags = d[0], cols = d[1], c, p, nblk;
    unsigned int pos = 3, tot = 0, len;

    if (flags & 0x10) {
        /* mask: TABLE (COLS пар [SHIFT,LEN]) общая, блоки = маска +
         * присутствующие плоскости, данные каждого блока = ΣLEN. */
        nblk = 1 + beam_popcount4(flags & 0x0F);
        for (c = 0; c < cols; c++) {
            tot += (unsigned int)d[pos + 1] * nblk;
            pos += 2;
        }
    } else {
        for (p = 0; p < 4; p++) {
            if (!(flags & (1u << p))) continue;
            for (c = 0; c < cols; c++) {
                len = d[pos + 1];
                tot += len;
                pos += 2 + len;
            }
        }
    }
    return tot;
}

/* Стоимость операции в строках растра (ТЗ §4: ≈25T/байт blit, ≈43T mask,
 * 96 тиков таймера на строку; +2 строки накладных плана/guard). */
static unsigned char beam_cost_lines(const unsigned char *d, unsigned char mask)
{
    unsigned int t = beam_desc_bytes(d);
    unsigned int lines = mask ? (t * 43u) / 96u : (t * 25u) / 96u;
    lines += 2;
    return lines > 255u ? 255u : (unsigned char)lines;
}

static void beam_cost_add(unsigned char band, unsigned char add)
{
    unsigned int v = (unsigned int)beam_band_cost[band] + add;
    beam_band_cost[band] = v > 255u ? 255u : (unsigned char)v;
}

/* Мировой ряд клеток (0..rows-1), занимающий слот кольца r при камере cam. */
static unsigned char beam_ring_row_world(unsigned char r, unsigned int cam)
{
    unsigned int base = cam >> 4;
    unsigned int w = base + ((r - ((unsigned char)base & 15u)) & 15u);
    if (w >= beam_lvl->rows) w = beam_lvl->rows - 1;
    return (unsigned char)w;
}

static unsigned char beam_cell_code(unsigned char r, unsigned char c,
                                    unsigned int cam)
{
    unsigned int w = beam_ring_row_world(r, cam);
    return beam_cellmap[w * beam_lvl->cols + c];
}

/* Прямоугольник клеток 16px, накрытых спрайтом (мировые координаты). */
static void beam_footprint(unsigned int y, unsigned char x,
                           const unsigned char *d,
                           unsigned int *r0, unsigned int *r1,
                           unsigned char *c0, unsigned char *c1)
{
    unsigned char w = (unsigned char)(d[1] * 8u);
    unsigned char h = d[2];
    *r0 = y >> 4;
    *r1 = (y + h - 1u) >> 4;
    *c0 = x >> 4;
    *c1 = (unsigned char)((x + w - 1u) >> 4);
}

/* Пометить клетки под спрайтом к erase-до-фона. */
static void beam_mark_footprint(unsigned int y, unsigned char x,
                                const unsigned char *d)
{
    unsigned int r0, r1, r, m;
    unsigned char c0, c1, c;
    beam_footprint(y, x, d, &r0, &r1, &c0, &c1);
    m = 0;
    for (c = c0; c <= c1; c++) m |= 1u << (c & 15u);
    for (r = r0; r <= r1; r++) beam_erase_mask[r & 15u] |= m;
}

/* Пересекается ли спрайт с помеченными клетками / strip-рядами. */
static unsigned char beam_overlaps_marked(unsigned int y, unsigned char x,
                                          const unsigned char *d)
{
    unsigned int r0, r1, r, m;
    unsigned char c0, c1, c;
    beam_footprint(y, x, d, &r0, &r1, &c0, &c1);
    m = 0;
    for (c = c0; c <= c1; c++) m |= 1u << (c & 15u);
    for (r = r0; r <= r1; r++) {
        if (beam_strip_row[r & 15u]) return 1;
        if (beam_erase_mask[r & 15u] & m) return 1;
    }
    return 0;
}

static void beam_draw_cell(unsigned char r, unsigned char c, unsigned int cam)
{
    unsigned char code = beam_cell_code(r, c, cam);
    spr_blit((unsigned char)(c * 16u), (unsigned int)(r * 16u),
             beam_lvl->bg_tiles[code]);
    beam_ring_cells[r * BEAM_MAX_COLS + c] = code;
}

/* Отрисовка + commit тени; ring_cells под силуэтом портятся (0xFF). */
static void beam_draw_inst(unsigned char i)
{
    const beam_pat_t *p = beam_inst[i].pat;
    const unsigned char *d = p->desc;
    unsigned int r0, r1, r;
    unsigned char c0, c1, c;

    if (p->attr & 0x10u)
        spr_blit_mask(beam_inst[i].x, beam_inst[i].y & 0xFFu, d);
    else
        spr_blit(beam_inst[i].x, beam_inst[i].y & 0xFFu, d);

    beam_shad[i] = beam_inst[i];
    beam_committed[i] = 1;
    beam_dirty[i] = 0;
    beam_footprint(beam_inst[i].y, beam_inst[i].x, d, &r0, &r1, &c0, &c1);
    for (r = r0; r <= r1; r++)
        for (c = c0; c <= c1; c++)
            beam_ring_cells[(r & 15u) * BEAM_MAX_COLS + (c & 15u)] = 0xFFu;
}

/* Сортировка id инстансов полосы по приоритету (attr бит0-3, мл. раньше). */
static void beam_sort_ids(unsigned char *ids, unsigned char n)
{
    unsigned char i, j, t;
    for (i = 1; i < n; i++) {
        t = ids[i];
        j = i;
        while (j > 0 &&
               (beam_inst[ids[j - 1]].pat->attr & 0x0Fu) >
               (beam_inst[t].pat->attr & 0x0Fu)) {
            ids[j] = ids[j - 1];
            j--;
        }
        ids[j] = t;
    }
}

/* ------------------------------------------------------------------ */
/* Загрузка уровня                                                     */
/* ------------------------------------------------------------------ */

void beam_init(const beam_level_t *lvl)
{
    unsigned int i;
    unsigned char r, c;
    unsigned int colmask = (lvl->cols >= BEAM_MAX_COLS)
                               ? 0xFFFFu
                               : (unsigned int)((1u << lvl->cols) - 1u);

    beam_lvl = lvl;
    spr_init();                     /* единственный вызов — из beam (ТФ-1) */

    for (i = 0; i < (unsigned int)lvl->rows * lvl->cols && i < BEAM_MAX_CELLS; i++)
        beam_cellmap[i] = lvl->map[i];

    for (i = 0; i < BEAM_INST_MAX; i++) {
        beam_inst[i].pat = 0;
        beam_shad[i].pat = 0;
        beam_committed[i] = 0;
        beam_dirty[i] = 0;
    }
    for (r = 0; r < BEAM_RING_ROWS; r++) {
        beam_erase_mask[r] = colmask;  /* первое окно — целиком */
        beam_strip_row[r] = 0;
        for (c = 0; c < lvl->cols; c++)
            beam_ring_cells[r * BEAM_MAX_COLS + c] = 0xFFu;
    }
    for (i = 0; i < BEAM_BANDS; i++) beam_band_cost[i] = 0;

    beam_cam_cur = 0;
    beam_cam_pending = 0;
    beam_overbudget_cnt = 0;
    beam_init_pending = 1;   /* первое окно — целиком, в бланкинг/без пейсинга */
}

/* ------------------------------------------------------------------ */
/* Мутаторы игрового цикла (ТФ-4: игра пишет только таблицы)           */
/* ------------------------------------------------------------------ */

void beam_move(unsigned char id, unsigned char x, unsigned int y)
{
    if (id >= BEAM_INST_MAX) return;
    beam_inst[id].x = x;
    beam_inst[id].y = y;
}

void beam_show(unsigned char id, const beam_pat_t *p)
{
    if (id >= BEAM_INST_MAX) return;
    beam_inst[id].pat = p;
}

void beam_hide(unsigned char id)
{
    if (id >= BEAM_INST_MAX) return;
    /* тень committed — клетки под ней восстановить до фона */
    if (beam_committed[id] && beam_shad[id].pat)
        beam_mark_footprint(beam_shad[id].y, beam_shad[id].x,
                            beam_shad[id].pat->desc);
    beam_inst[id].pat = 0;
    beam_shad[id].pat = 0;
    beam_committed[id] = 0;
    beam_dirty[id] = 0;
}

void beam_bg_put(unsigned char col, unsigned char row, unsigned char code)
{
    if (row >= beam_lvl->rows || col >= beam_lvl->cols) return;
    beam_cellmap[row * beam_lvl->cols + col] = code;
    beam_erase_mask[row & 15u] |= 1u << (col & 15u);
}

void beam_set_cam(unsigned int cam_y)
{
    int db = (int)(cam_y >> 3) - (int)(beam_cam_cur >> 3);
    unsigned int wb;

    beam_cam_pending = cam_y;
    gfx_set_scroll((unsigned char)(0xFFu - (cam_y & 0xFFu)));

    if (db >= 32 || db <= -32) {
        for (wb = 0; wb < BEAM_RING_ROWS; wb++) beam_strip_row[wb] = 1;
    } else if (db > 0) {
        /* открылись нижние полосы: (cam_cur>>3)+32 .. (cam_y>>3)+31 */
        for (wb = (beam_cam_cur >> 3) + 32u;
             wb <= (unsigned int)((cam_y >> 3) + 31); wb++)
            beam_strip_row[(wb >> 1) & 15u] = 1;
    } else if (db < 0) {
        /* открылись верхние полосы: (cam_y>>3) .. (cam_cur>>3)-1 */
        for (wb = cam_y >> 3; wb < beam_cam_cur >> 3; wb++)
            beam_strip_row[(wb >> 1) & 15u] = 1;
    }
}

/* ------------------------------------------------------------------ */
/* Планирование                                                        */
/* ------------------------------------------------------------------ */

void beam_update(void)
{
    unsigned char i, r, c;
    unsigned int m;

    /* Strip-ряды перерисовываются ЦЕЛИКОМ в фазе B — из обычного плана
     * их клетки убираем (иначе двойная работа и ложный пейсинг). */
    for (r = 0; r < BEAM_RING_ROWS; r++)
        if (beam_strip_row[r]) beam_erase_mask[r] = 0;

    /* 1. diff экземпляров с тенями; erase-клетки под уехавшими тенями. */
    for (i = 0; i < BEAM_INST_MAX; i++) {
        beam_dirty[i] = 0;
        if (!beam_inst[i].pat) continue;
        if (beam_committed[i] &&
            beam_shad[i].y == beam_inst[i].y &&
            beam_shad[i].x == beam_inst[i].x &&
            beam_shad[i].pat == beam_inst[i].pat)
            continue;                                   /* не изменился */
        if (beam_committed[i] && beam_shad[i].pat)
            beam_mark_footprint(beam_shad[i].y, beam_shad[i].x,
                                beam_shad[i].pat->desc); /* erase по тени */
        beam_dirty[i] = 1;
    }

    /* 2. Стоящие экземпляры над помеченными клетками — тоже перерисовать
     *    (erase/strip уничтожит их пиксели). */
    for (i = 0; i < BEAM_INST_MAX; i++) {
        if (beam_dirty[i] || !beam_inst[i].pat) continue;
        if (beam_overlaps_marked(beam_inst[i].y, beam_inst[i].x,
                                 beam_inst[i].pat->desc))
            beam_dirty[i] = 1;
    }

    /* 3. Commit-полоса инстанса = его нижняя полоса, но НЕ ВЫШЕ нижней
     *    полосы каждой перекрывающейся erase-клетки (клетка 16px рисуется
     *    одной операцией и мажет обе свои полосы — §3.1 ряд-атомарность).
     *    Заодно — флаг отсрочки в фазу B (пересечение со strip). */
    for (i = 0; i < BEAM_INST_MAX; i++) {
        unsigned int r0, r1, r, cb;
        unsigned char c0, c1;
        const unsigned char *d;
        beam_inst_strip[i] = 0;
        if (!beam_dirty[i] || !beam_inst[i].pat) continue;
        d = beam_inst[i].pat->desc;
        beam_footprint(beam_inst[i].y, beam_inst[i].x, d, &r0, &r1, &c0, &c1);
        cb = (beam_inst[i].y + d[2] - 1u) >> 3;          /* мировая полоса */
        for (r = r0; r <= r1; r++) {
            if (beam_strip_row[r & 15u]) beam_inst_strip[i] = 1;
            m = 0;
            for (c = c0; c <= c1; c++) m |= 1u << (c & 15u);
            if (beam_erase_mask[r & 15u] & m) {
                unsigned int cell_cb = (r << 1) + 1u;    /* низ клетки */
                if (cell_cb > cb) cb = cell_cb;
            }
        }
        beam_inst_band[i] = (unsigned char)(cb & 31u);
    }

    /* 4. Стоимость полос: erase-клетки (коммит в нечётной полосе ряда). */
    for (r = 0; r < BEAM_BANDS; r++) beam_band_cost[r] = 0;
    for (r = 0; r < BEAM_RING_ROWS; r++) {
        if (beam_strip_row[r]) continue;
        for (c = 0; c < beam_lvl->cols; c++) {
            if (!(beam_erase_mask[r] & (1u << c))) continue;
            beam_cost_add((unsigned char)((2u * r + 1u) & 31u),
                          beam_cost_lines(
                              beam_lvl->bg_tiles[beam_cell_code(r, c,
                                                                beam_cam_cur)],
                              0));
        }
    }
    /* 5. Стоимость полос: dirty-инстансы (кроме отложенных в фазу B). */
    for (i = 0; i < BEAM_INST_MAX; i++) {
        if (!beam_dirty[i] || !beam_inst[i].pat || beam_inst_strip[i]) continue;
        beam_cost_add(beam_inst_band[i],
                      beam_cost_lines(beam_inst[i].pat->desc,
                                      beam_inst[i].pat->attr & 0x10u));
    }
}

/* ------------------------------------------------------------------ */
/* Исполнение                                                          */
/* ------------------------------------------------------------------ */

/* Фаза: erase-клетки ряда r (без strip-рядов — их рисует фаза B). */
static void beam_render_cells(unsigned char r, unsigned int cam)
{
    unsigned char c;
    for (c = 0; c < beam_lvl->cols; c++) {
        if (!(beam_erase_mask[r] & (1u << c))) continue;
        beam_draw_cell(r, c, cam);
        beam_erase_mask[r] &= ~(1u << c);
    }
}

/* Исполнение всего плана без пейсинга: первое окно (beam_init — экран
 * должен быть погашен палитрой; erase_mask помечен целиком) и режим
 * BEAM_OFF (ТЗ §3.5 — записи только в бланкинг, перерасход кадра штатен).
 * Клетки — по НОВОЙ камере: после flush регистра на VBlank окно уже её. */
static void beam_render_all(void)
{
    unsigned char ids[BEAM_INST_MAX];
    unsigned char r, c, i, n;

    for (r = 0; r < BEAM_RING_ROWS; r++) {
        if (!beam_strip_row[r]) {          /* обычный план: erase-клетки */
            beam_render_cells(r, beam_cam_pending);
            continue;
        }
        for (c = 0; c < beam_lvl->cols; c++) {   /* strip-ряд целиком */
            unsigned char code = beam_cell_code(r, c, beam_cam_pending);
            if (beam_ring_cells[r * BEAM_MAX_COLS + c] == code)
                continue;                  /* алиас совпал */
            spr_blit((unsigned char)(c * 16u), (unsigned int)(r * 16u),
                     beam_lvl->bg_tiles[code]);
            beam_ring_cells[r * BEAM_MAX_COLS + c] = code;
        }
        beam_strip_row[r] = 0;
    }

    n = 0;
    for (i = 0; i < BEAM_INST_MAX; i++)
        if (beam_dirty[i] && beam_inst[i].pat) ids[n++] = i;
    beam_sort_ids(ids, n);
    for (i = 0; i < n; i++) beam_draw_inst(ids[i]);

    beam_cam_cur = beam_cam_pending;
    beam_init_pending = 0;
}

/* Фаза: dirty-инстансы полосы b (strip-отложенные — только фаза B). */
static void beam_render_band_insts(unsigned char b, unsigned char *mask_drawn,
                                   unsigned char allow_strip)
{
    unsigned char ids[BEAM_INST_MAX];
    unsigned char i, n = 0;

    for (i = 0; i < BEAM_INST_MAX; i++) {
        if (!beam_dirty[i] || !beam_inst[i].pat) continue;
        if (allow_strip) {
            if (!beam_inst_strip[i]) continue;   /* фаза B: только отложенные */
        } else {
            if (beam_inst_strip[i]) continue;
            if (beam_inst_band[i] != b) continue;
        }
        ids[n++] = i;
    }
    beam_sort_ids(ids, n);
    for (i = 0; i < n; i++) {
        unsigned char id = ids[i];
        if (beam_inst[id].pat->attr & 0x10u) {
            if (*mask_drawn >= BEAM_MASK_LIMIT) {   /* лимит ТЗ §3.2 */
                beam_overbudget_cnt++;
                continue;                           /* перенос в след. кадр */
            }
            (*mask_drawn)++;
        }
        beam_draw_inst(id);
    }
}

void beam_render(void)
{
    unsigned char s, b, mask_drawn = 0, stop = 0, any_strip;
    unsigned int cam_band, target, el, top, cost_t;

    if (!beam_lvl) return;

    if (!beam_lvl->beam_sync || beam_init_pending) {
        if (!beam_lvl->beam_sync) beam_blank_wait();  /* BEAM_OFF: бланкинг */
        beam_render_all();
        if (beam_lvl->beam_sync) timer_wait(0);       /* init: темп 50 Гц   */
        return;
    }

    /* --- Фаза A: обычные полосы сверху вниз, behind-the-beam ---
     * Экранная позиция — по СТАРОЙ камере: регистр скролла сменится только
     * на VBlank, весь кадр геометрия отображения прежняя. */
    cam_band = (beam_cam_cur >> 3) & 31u;
    for (s = 0; s < BEAM_BANDS; s++) {
        b = (unsigned char)((s + cam_band) & 31u);
        if (!beam_band_cost[b]) continue;             /* полоса чиста */

        target = TIMER_LINES(48u + 8u * s + 8u);      /* bot(s), ТЗ §3.1 */
        el = timer_elapsed();
        if (el < target) {
            top = TIMER_LINES(48u + 8u * s);
            cost_t = TIMER_LINES(beam_band_cost[b]);
            /* ветка «успеем до луча»: top − elapsed − LEAD > cost + MARGIN */
            if (top > el &&
                (top - el) > cost_t +
                             TIMER_LINES(BEAM_LEAD_LINES + BEAM_MARGIN_LINES)) {
                /* пишем сейчас, луч ещё не дошёл */
            } else {
                timer_wait(TIMER_REMAIN(target));
                if (timer_elapsed() < target) {       /* счётчик перезагрузился */
                    stop = 1;                          /* кадр упущен */
                    beam_overbudget_cnt++;
                    break;
                }
            }
        }
        if (b & 1u) {                                  /* низ ряда клеток */
            unsigned char r = (unsigned char)(b >> 1);
            if (!beam_strip_row[r]) beam_render_cells(r, beam_cam_cur);
        }
        beam_render_band_insts(b, &mask_drawn, 0);
    }

    /* --- Фаза B: полоса, открытая скроллом, — в бланкинге ---
     * Луч вне видимого поля (строка >= 288): записи невидимы, а на VBlank
     * kbd_scan_now сбросит регистр скролла в порт 03h — полоса окажется
     * на новом крае окна уже с новым содержимым (без разрыва, Г1). */
    any_strip = 0;
    for (b = 0; b < BEAM_RING_ROWS; b++) any_strip |= beam_strip_row[b];
    if (any_strip && !stop) {
        timer_wait(TIMER_REMAIN(TIMER_LINES(BEAM_BLANK_LINE)));
        if (timer_elapsed() < TIMER_LINES(BEAM_BLANK_LINE)) {
            stop = 1;                                  /* кадр упущен */
            beam_overbudget_cnt++;
        } else {
            for (b = 0; b < BEAM_RING_ROWS; b++) {
                unsigned char c;
                if (!beam_strip_row[b]) continue;
                for (c = 0; c < beam_lvl->cols; c++) {
                    unsigned char code = beam_cell_code(b, c,
                                                        beam_cam_pending);
                    if (beam_ring_cells[b * BEAM_MAX_COLS + c] == code)
                        continue;                      /* алиас совпал */
                    spr_blit((unsigned char)(c * 16u),
                             (unsigned int)(b * 16u),
                             beam_lvl->bg_tiles[code]);
                    beam_ring_cells[b * BEAM_MAX_COLS + c] = code;
                }
                beam_strip_row[b] = 0;
            }
            /* инстансы, отложенные в фазу B (пересекали strip-ряды) */
            beam_render_band_insts(0, &mask_drawn, 1);
        }
    }

    /* Камера становится активной: следующий кадр считает экран по новой.
     * Даже если фаза B не исполнилась (кадр упущен) — регистр скролла на
     * VBlank всё равно сменится, strip-флаги остались на следующий кадр. */
    beam_cam_cur = beam_cam_pending;

    if (!stop) timer_wait(0);   /* блокируем до конца кадра: темп = 50 Гц */
}

unsigned char beam_overbudget(void)
{
    return beam_overbudget_cnt;
}

void beam_blank_wait(void)
{
    timer_wait(TIMER_REMAIN(TIMER_LINES(BEAM_BLANK_LINE)));
}
