; mario.asm — горячий путь демки Mario 8-цвет (сплит по плоскостям) для Вектора-06Ц.
;
;   void render_window(unsigned int cam, unsigned int old_cam,
;                      unsigned char blk0, unsigned char nblk)
;       — дорисовка nblk экранных блоков (столбцов по 8 пикселей) начиная с
;         blk0. cam — мировой тайловый столбец у левого края экрана, old_cam —
;         тот, что уже нарисован в VRAM. Отрисовывается РАЗНОСТЬ: блок не
;         трогается, если тайл совпал, а плоскость блока не трогается, если она
;         пуста и в старом, и в новом тайле (карта tile_nz). old_cam ==
;         CAM_NO_REF означает «в VRAM пусто» (первый экран) — эталоном служит
;         тайл 0 = чистое небо. Пишутся ТОЛЬКО фоновые плоскости (вес 8, вес 4).
;
;   void render_rowband(unsigned int world_row, unsigned int cam)
;       — полная (без разности) зарисовка ОДНОЙ мировой тайловой строки
;         world_row по всем 32 экраным колонкам для текущего cam. Используется
;         при вертикальном скролле: Hardware сдвигает готовые 31 строку, а эта
;         функция дорисовывает только что открытую полосу (8 px). Пишет только
;         фоновые плоскости.
;
;   void mario_draw(unsigned char x, unsigned char y, const unsigned char *spr)
;       — наложить спрайт 16x16 ПРЯМОЙ ЗАПИСЬЮ в плоскости персонажа (вес 2,
;         вес 1). Маскирования и слепка VRAM нет: спрайт не трогает фон.
;   void mario_undraw(void)
;       — стереть Марио: обнулить те же 2 плоскости персонажа в прямоугольнике
;         прошлого кадра (фон под ним не восстанавливаем — он не затирается).
;         Порядок кадра: undraw -> render_window/render_rowband -> mario_draw.
;
; РАЗНЕСЕНИЕ ПО ПЛОСКОСТЯМ (сплит). Индекс палитры = bg*4 + ch:
;   * ФОН      — старшие 2 бита: плоскости 0x8000 (вес 8) и 0xA000 (вес 4).
;   * ПЕРСОНАЖ — младшие 2 бита: плоскости 0xC000 (вес 2) и 0xE000 (вес 1).
; Палитра разложена так, что спрайт побеждает фон без маскирования: ch=0 ->
; цвет фона, ch=1..3 -> цвет спрайта. Поэтому фоновые рендеры ходят строго по
; vram_bases (вес 8,4), спрайт — строго по char_bases (вес 2,1), пересечений по
; плоскостям нет. ch=0 == прозрачность спрайта == фон показывает своё.
;
; Формат Вектора: блок = x/8 (256 байт), байт i хранит строку y = 255 - i
; (строки сверху вниз идут по УБЫВАЮЩЕМУ адресу), старший бит = левый пиксель.
;
; ВЕРТИКАЛЬНЫЙ КОЛЬЦЕВОЙ БУФЕР (скролл по обеим осям). Регистр строки порта 03h
; (gfx_scroll_row) — аппаратный вертикальный скролл; измерено в spike:
;     смещение_вниз_px = (gfx_scroll_row + 1) & 0xFF   (кольцо по 256 строк)
;     => gfx_set_scroll(d2scroll(cam_y))  где  d2scroll(cam_y) = 0xFF - (cam_y & 0xFF)
; Мирный пиксельный ряд wy кладём в линию VRAM (wy mod 256), т.е. байт в блоке =
; 255 - (wy mod 256). Экранная строка s показывает мировую строку cam_y + s.
; cam_row (мировая тайловая строка верха экрана, _cam_row) и TILE_STRIDE
; (_tile_stride = LEVEL_ROWS) приходят из C. При cam_row=0 и stride=32 адресация
; сводится к прежней (обратная совместимость регрессии).
;
; Тайл 8x8 (tileset): 2 фоновые плоскости по 8 байт, порядок весов 8,4; в
; плоскости строки 0..7 сверху вниз. 16 байт на тайл. Тайл 0 = пустой (небо) =>
; его первые 16 байт — нули, их используем как эталон «пусто» для первого экрана.
; Младшие 2 бита в тайлах фона всегда 0 (фон = 4 цвета с дизерингом).
; Тайлкарта — КОЛЬЦЕВОЕ RAM-ОКНО tile_win (Фаза 3): tile_win[локальный_столбец*
; stride + строка], локальный_столбец = мировой_столбец - tile_win_base (0..63,
; stride = LEVEL_ROWS). Окно печёт main.c: bake_window() из списка объектов. Рендер
; идёт по локальным колонкам (шаг +stride contiguous, без wrap — окно 64 колонок
; всегда шире экрана). tile_nz[t]: бит0 = непуста плоскость веса 8, бит1 = веса 4.
; pair_top[c] (в ROM, по МИРОВОЙ колонке) = min(col_top[c], col_top[c+1]) — самая
; верхняя МИРОВАЯ строка, где в паре соседних колонок есть содержимое.
;
; Спрайт 16x16 (mario.inc): 4 прогона (плоскость вес 2, вес 1 x колонка блока
; 0,1) по 16 байт. Порядок прогонов: [w2 лев.][w2 прав.][w1 лев.][w1 прав.],
; внутри байты = строки 0..15 сверху вниз. Прямая запись (без keep/set). Прогон
; идёт по адресам VRAM, убывающим на 1 за строку (dcr e — кольцевой переход
; 0->255 внутри блока). 16-px спрайт может пересечь шов кольца; dcr e держит
; старший байт (столбец), заворачивая только младший.
;
; Соглашение вызова z88dk classic (__z88dk_callee): аргументы в 16-битных
; слотах, callee чистит стек. Только инструкции Intel 8080.

        SECTION code_clib

        PUBLIC  _render_window
        PUBLIC  _render_rowband
        PUBLIC  _mario_draw
        PUBLIC  _mario_undraw

        EXTERN  _tileset
        EXTERN  _rw_run_ofs     ; u16: смещение ранов разности на колонку
        EXTERN  _rw_run_data    ; пары (row,count), терминатор (0,0)
        EXTERN  _tile_win       ; RAM-окно тайлкарты (bake_window в main.c)
        EXTERN  _tile_win_base  ; unsigned int: мировая колонка окна[0]
        EXTERN  _tile_nz
        EXTERN  _pair_top
        EXTERN  _cam_row        ; unsigned char: мировая тайловая строка верха экрана
        EXTERN  _tile_stride    ; unsigned char: LEVEL_ROWS (шаг колонки тайлкарты)
        EXTERN  _tile_stride_shl ; log2(LEVEL_ROWS) либо 0xFF (см. _mulshift)

ROWS EQU 32                 ; экранных тайлов по высоте (256/8) — всегда 32
CAM_NO_REF EQU 0FFFFh       ; old_cam: в VRAM пусто (первый экран)
MARIO_RUNS EQU 4            ; прогонов спрайта: 2 плоскости персонажа x 2 колонки
MARIO_ROWS EQU 16           ; байт VRAM в прогоне
HALF_TILE EQU 8             ; байт в одной половине _rw_tile16 (плоскость A/B)

; ---------------------------------------------------------------
; BSS — рабочие переменные.
; ---------------------------------------------------------------
        SECTION bss_clib

; --- render_window ---
rw_cam:     defw    0           ; новый мировой столбец у левого края (+blk0)
rw_ref:     defw    0           ; old_cam (+blk0) (или CAM_NO_REF)
rw_blk:     defb    0           ; текущий экранный блок
rw_end:     defb    0           ; последний блок (exclusive)
rw_newwalk: defw    0           ; &tile_win[local*stride + cam_row], шаг +stride на блок
rw_refwalk: defw    0           ; &tile_win[local*stride + cam_row] (или _tileset = «пусто»)
rw_refstep: defb    0           ; stride или 0 для CAM_NO_REF
rw_pairwalk:defw    0           ; &pair_top[min(cam,old)], шаг +1 на блок
rw_pairstep:defb    0           ; 1 или 0 для CAM_NO_REF
rw_top:     defb    0           ; первая ЭКРАННАЯ строка сканирования текущего блока
rw_dsthi:   defb    0,0         ; старшие байты VRAM для 2 фоновых плоскостей блока

; --- render_window, быстрый путь по таблице ранов ---
rw_w0:      defw    0           ; cam + blk0 (мировая колонка блока 0)
rwf_adj:    defb    0           ; +1: эталон блока — колонка w0+1 (скролл назад)
rwf_pnew:   defw    0           ; &tile_win[локальная колонка w0], шаг +stride
rwf_rp:     defw    0           ; бегущий указатель ранов (rw_run_data)
rwf_hi0:    defb    0           ; старший байт VRAM плоскости веса 8 текущего блока
rwf_cnt:    defb    0           ; остаток строк рана (вес 4 держит B)

; --- render_rowband ---
rb_blk:     defb    0           ; текущая экранная колонка 0..31
rb_row:     defb    0           ; мировая тайловая строка
rb_dstlow:  defb    0           ; кольцевой dst_low строки (одинаков для всех колонок)
rb_walk:    defw    0           ; &tile_win[local*stride + world_row], шаг +stride

; --- mulstride / mulshift (HL = DE * stride) ---
; только регистры, без памяти.

; --- mario_draw / mario_undraw ---
md_blk:     defb    0           ; левый блок Марио (x/8)
md_ytop:    defb    0           ; 255 - (y mod 256) = адрес верхнего байта прогона
md_runs:    defb    0           ; сколько прогонов спрайта осталось
md_vtab:    defs    MARIO_RUNS * 2  ; 4 начальных адреса VRAM под спрайтом
md_vtab_cur:defw    0           ; бегущий указатель md_vtab
md_spr_cur: defw    0           ; бегущий указатель спрайта (плоскости персонажа)

; Старшие байты баз ФОНОВЫХ плоскостей по весам 8,4 (адрес = base<<8 | смещение).
vram_bases: defb    080h, 0A0h
; Старшие байты баз плоскостей ПЕРСОНАЖА по весам 2,1.
char_bases: defb    0C0h, 0E0h

; ---------------------------------------------------------------
; _mulstride: HL = DE * C   (C — 8-битный множитель stride, DE — 16-битное
; значение столбца). Сдвиг-сложение, 8 итераций. Портит A,B,C,D,E,HL.
; Результат заведомо < 4K (local*stride < размер окна tile_win).
; ---------------------------------------------------------------
        SECTION code_clib
_mulstride:
        mvi     h,0
        mvi     l,0             ; HL = накопитель
        mvi     b,8             ; 8 бит множителя
ms_loop:
        mov     a,c
        ani     1
        jz      ms_shift        ; бит сброшен — не прибавляем
        dad     d               ; HL += DE
ms_shift:
        mov     a,e
        add     a               ; DE <<= 1 (перенос из бита 7 E)
        mov     e,a
        mov     a,d
        adc     a
        mov     d,a
        mov     a,c
        rra                     ; C >>= 1
        ani     7Fh             ; логический сдвиг (убрать занесённый перенос)
        mov     c,a
        dcr     b
        jnz     ms_loop
        ret

; ---------------------------------------------------------------
; _mulshift: HL = DE * stride. Когда stride — степень двойки, умножение это
; просто сдвиг: HL = DE, затем _tile_stride_shl раз «dad h» (HL += HL, 11 T и
; НЕ трогает флаги) — ~90 T вместо ~700 T на 8-итерационном сдвиг-сложении.
; Показатель степени считает main.c один раз на старте. Если LEVEL_ROWS не
; степень двойки, _tile_stride_shl = 0xFF и уходим в общий _mulstride.
; Контракт тот же, что у _mulstride: DE — множится, C = stride (нужен только
; для fallback). Портит A,B,C,D,E,HL.
; ---------------------------------------------------------------
        SECTION code_clib
_mulshift:
        lda     _tile_stride_shl
        cpi     0FFh
        jz      _mulstride              ; не степень двойки — общий умножитель
        mov     h,d
        mov     l,e                     ; HL = DE
        mov     b,a                     ; B = число сдвигов
        mvi     a,0
        ora     b
        jz      msh_done                ; stride == 1
msh_loop:
        dad     h               ; HL <<= 1
        dcr     b
        jnz     msh_loop
msh_done:
        ret

; ---------------------------------------------------------------
; void render_window(unsigned int cam, unsigned int old_cam,
;                    unsigned char blk0, unsigned char nblk)
; ---------------------------------------------------------------
        SECTION code_clib

_render_window:
        ; sccz80 classic: аргументы пушатся слева направо, поэтому arg1 (cam)
        ; дальше всего от SP: nblk (sp+2), blk0 (sp+4), old_cam (sp+6), cam (sp+8).
        lxi     h,8
        dad     sp
        mov     a,m             ; cam lo
        mov     c,a
        inx     h
        mov     h,m             ; cam hi
        mov     l,a
        shld    rw_cam
        lxi     h,6
        dad     sp
        mov     a,m             ; old_cam lo
        mov     c,a
        inx     h
        mov     h,m             ; old_cam hi
        mov     l,a
        shld    rw_ref
        lxi     h,4
        dad     sp
        mov     a,m             ; blk0
        sta     rw_blk
        mov     c,a
        lxi     h,2
        dad     sp
        mov     a,m             ; nblk
        add     c               ; end = blk0 + nblk
        sta     rw_end

        ; --- выбор пути ---
        ; CAM_NO_REF (первый экран) и дальний прыжок камеры требуют сравнения
        ; tile_win с ПРОИЗВОЛЬНЫМ эталоном — это общий путь ниже. Штатный скролл
        ; всегда идёт с |old_cam - cam| == 1 (main.c), и тогда разность колонок
        ; целиком запечена в rw_run_ofs/rw_run_data: построчное сравнение не нужно.
        lhld    rw_ref
        mov     a,h
        ana     l
        cpi     0FFh
        jz      rw_slow         ; CAM_NO_REF
        lhld    rw_cam
        xchg                    ; DE = cam
        lhld    rw_ref          ; HL = old_cam
        mov     a,l
        sub     e
        mov     c,a
        mov     a,h
        sbb     d               ; A = (old_cam - cam) >> 8
        ora     a
        jnz     rw_dn
        mov     a,c
        cpi     01h
        jz      rwf_tbl1        ; old = cam+1 (скролл назад)
        jmp     rw_slow
rw_dn:
        cpi     0FFh
        jnz     rw_slow
        mov     a,c
        cpi     0FFh
        jz      rwf_tbl0        ; old = cam-1 (скролл вперёд)

rw_slow:
        ; --- начальные указатели колонок ---
        ; окно может начинаться не с нуля: cam и old сдвигаем на blk0, чтобы
        ; rw_newwalk/rw_refwalk = tile_win + (cam+blk0-base)*stride + cam_row, а min()
        ; ниже дал min(cam,old)+blk0 — ровно то, что нужно для pair_top.
        lda     rw_blk
        mov     c,a
        lhld    rw_cam
        mov     a,l
        add     c
        mov     l,a
        mvi     a,0
        adc     h
        mov     h,a
        shld    rw_cam          ; cam += blk0
        ; rw_newwalk = _tile_win + (cam+blk0 - base)*stride + cam_row
        lhld    rw_cam          ; HL = cam+blk0 (мировая)
        lda     _tile_win_base
        mov     c,a
        lda     _tile_win_base+1
        mov     b,a             ; BC = base
        mov     a,l
        sub     c
        mov     l,a
        mov     a,h
        sbb     b
        mov     h,a             ; HL = local = cam+blk0 - base
        xchg                    ; DE = local
        lda     _tile_stride
        mov     c,a
        call    _mulshift       ; HL = local*stride
        lxi     d,_tile_win
        dad     d
        lda     _cam_row        ; + cam_row (смещение мировой строки верха экрана)
        add     l
        mov     l,a
        mvi     a,0
        adc     h
        mov     h,a
        shld    rw_newwalk

        ; CAM_NO_REF? (h и l оба 0FFh => h & l == 0FFh)
        lhld    rw_ref
        mov     a,h
        ana     l
        cpi     0FFh
        jnz     rw_have_ref

        ; Первый экран: эталон — тайл 0 (16 нулей в начале tileset), шаг 0,
        ; верх сканирования 0 (тоже байт 0 из tileset — тайл пустой).
        lxi     h,_tileset
        shld    rw_refwalk
        shld    rw_pairwalk
        xra     a
        sta     rw_refstep
        sta     rw_pairstep
        jmp     rw_walk_done

rw_have_ref:
        ; old += blk0 (мировая — нужна и для min/pair_top, и для разницы с cam)
        lda     rw_blk
        mov     c,a
        lhld    rw_ref
        mov     a,l
        add     c
        mov     l,a
        mvi     a,0
        adc     h
        mov     h,a
        shld    rw_ref          ; old += blk0
        ; refwalk = newwalk + (old - cam)*stride. При обычном скролле
        ; |old-cam| == 1, поэтому умножать не нужно вовсе: refwalk =
        ; newwalk ∓ один шаг окна (со знаком, обратным ходу камеры). Это
        ; ~40 T вместо ~750 T на каждый кадр скролла; на границе перепечки
        ; newwalk - stride указывает ровно в колонку-страж tile_win_prevcol.
        lhld    rw_cam
        xchg                    ; DE = cam+blk0
        lhld    rw_ref          ; HL = old+blk0
        mov     a,l
        sub     e
        mov     c,a             ; C = младшая разница
        mov     a,h
        sbb     d
        mov     b,a             ; B = старшая разница: BC = old - cam
        cpi     0FFh
        jnz     rw_ref_hi
        mov     a,c
        cpi     0FFh
        jnz     rw_ref_slow     ; это не -1
        ; delta = -1 (скролл вперёд): refwalk = newwalk - stride
        lda     _tile_stride
        mov     c,a
        lhld    rw_newwalk
        mov     a,l
        sub     c
        mov     l,a
        mov     a,h
        sbi     0
        mov     h,a
        shld    rw_refwalk
        jmp     rw_ref_step
rw_ref_hi:
        ora     a               ; hi != 0 -> редкий случай (дальний прыжок)
        jnz     rw_ref_slow
        mov     a,c
        cpi     01h
        jnz     rw_ref_slow     ; delta = +1 только при lo == 1
        ; delta = +1 (скролл назад): refwalk = newwalk + stride
        lda     _tile_stride
        mov     c,a
        lhld    rw_newwalk
        mov     a,l
        add     c
        mov     l,a
        mov     a,h
        aci     0
        mov     h,a
        shld    rw_refwalk
        jmp     rw_ref_step
rw_ref_slow:
        ; общий случай: refwalk = _tile_win + (old+blk0 - base)*stride + cam_row
        lda     _tile_win_base
        mov     c,a
        lda     _tile_win_base+1
        mov     b,a             ; BC = base
        lhld    rw_ref          ; HL = old+blk0 (мировая)
        mov     a,l
        sub     c
        mov     l,a
        mov     a,h
        sbb     b
        mov     h,a             ; HL = local = old+blk0 - base
        xchg                    ; DE = local
        lda     _tile_stride
        mov     c,a
        call    _mulshift       ; HL = local*stride
        lxi     d,_tile_win
        dad     d
        lda     _cam_row
        add     l
        mov     l,a
        mvi     a,0
        adc     h
        mov     h,a
        shld    rw_refwalk
rw_ref_step:
        lda     _tile_stride
        sta     rw_refstep
        ; rw_pairwalk = _pair_top + min(cam, old) — оба уже с учётом blk0
        lhld    rw_ref          ; HL = old+blk0
        xchg                    ; DE = old+blk0
        lhld    rw_cam          ; HL = cam+blk0, DE = old+blk0
        mov     a,h
        cmp     d               ; старшие байты
        jc      rw_min_done     ; cam < old
        jnz     rw_min_swap     ; cam > old -> min = old
        mov     a,l
        cmp     e               ; равные старшие -> решают младшие
        jc      rw_min_done
rw_min_swap:
        xchg                    ; HL = min (old_cam)
rw_min_done:
        lxi     d,_pair_top
        dad     d
        shld    rw_pairwalk
        mvi     a,1
        sta     rw_pairstep

rw_walk_done:
        ; --- цикл по блокам ---
rw_block_loop:
        call    _rw_block
        ; шаг указателями на следующий блок (+stride для тайлкарты, +1 для pair_top)
        lhld    rw_newwalk
        lda     _tile_stride
        mov     e,a
        mvi     d,0
        dad     d
        shld    rw_newwalk
        lhld    rw_refwalk
        lda     rw_refstep
        mov     e,a
        mvi     d,0
        dad     d
        shld    rw_refwalk
        lhld    rw_pairwalk
        lda     rw_pairstep
        mov     e,a
        mvi     d,0
        dad     d
        shld    rw_pairwalk
        ; blk++
        lda     rw_blk
        inr     a
        sta     rw_blk
        mov     e,a
        lda     rw_end
        cmp     e
        jnz     rw_block_loop

rw_epilog:
        pop     de              ; адрес возврата
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp              ; съесть cam, old_cam, blk0, nblk (8 байт)
        push    de
        ret

; ---------------------------------------------------------------
; _rw_block: дорисовать ОДИН экранный блок (столбец из 32 тайлов экрана).
;
; Сравнивает tile_win[local(cam+blk)] с tile_win[local(old+blk)] построчно; строки экрана, чьи
; МИРОВЫЕ ряды лежат выше pair_top, заведомо небо в обеих колонках — пропускаем.
; Кольцевой dst_low строки живёт в C (стартует от 255-8*(cam_row+top) и
; уменьшается на 8 за строку; 8-битное sui даёт естественное закольцовывание),
; счётчик строк — в B, поэтому вызывающий пушит пару BC вокруг грязной клетки.
; (~=_rw_put_cell упразднён: его тело инлайнено в _rw_block под метками
;  rw_p0w/rw_p1w, чтобы не платить call/ret на клетку. Семантика та же: A=ref,
;  HL=&new, C=dst_low, плоскости весов 8 и 4 пишутся по маске _tile_nz.)
; ---------------------------------------------------------------
        SECTION code_clib
_rw_block:
        ; --- rw_top из pair_top с учётом cam_row ---
        lhld    rw_pairwalk
        mov     a,m             ; pt = верхняя содержимая МИРОВАЯ строка пары
        mov     c,a             ; C = pt
        lda     _cam_row
        mov     b,a             ; B = cam_row
        adi     32              ; cam_row + 32 = нижняя граница экрана (мировые строки)
        cmp     c               ; (cam_row+32) - pt
        jc      rw_blk_ret      ; pt > cam_row+32: содержимое ниже экрана -> блок пуст
        jz      rw_blk_ret      ; pt == cam_row+32: rw_top=32 -> B=0 -> 256 мусорных строк
        mov     a,c
        sub     b               ; pt - cam_row
        jc      rw_top0         ; pt < cam_row: содержимое выше экрана -> top = 0
        jmp     rw_topset
rw_top0:
        xra     a
rw_topset:
        sta     rw_top
        ; dst_low = 255 - 8*((cam_row + rw_top) & 31) = cpl((cam_row+top)*8 mod 256)
        mov     b,a             ; B = rw_top
        lda     _cam_row
        add     b               ; cam_row + rw_top  (< 256)
        add     a
        add     a
        add     a               ; *8 (младший байт == (cam_row+top)*8 mod 256)
        cma                     ; 255 - x
        mov     c,a             ; C = кольцевой dst_low (дальше по циклу в C)

        ; dsthi[p] = vram_bases[p] + blk (адрес = hi<<8 | смещение в блоке)
        lda     rw_blk
        mov     e,a             ; E = blk (C беречь!)
        lda     vram_bases
        add     e
        sta     rw_dsthi
        lda     vram_bases+1
        add     e
        sta     rw_dsthi+1

        ; DE = rw_refwalk + top, HL = rw_newwalk + top
        ; (оба rw_*walk уже содержат cam_row; top — экранное смещение).
        ; обоих указателей хватает на стеке: это раз в блок, а не раз в клетку
        lda     rw_top
        mov     e,a
        mvi     d,0             ; DE = top
        lhld    rw_newwalk
        dad     d               ; HL = new+top
        push    h
        lhld    rw_refwalk
        dad     d               ; HL = ref+top
        push    h
        pop     d               ; DE = ref+top
        pop     h               ; HL = new+top

        ; B = счётчик строк (32 - top)
        lda     rw_top
        mov     b,a
        mvi     a,ROWS
        sub     b
        mov     b,a

        ; --- построчное сравнение ---
rw_scan:
        ldax    d               ; A = старый тайл
        cmp     m               ; совпал с новым?
        jz      rw_scan_next
        push    b               ; rowcount — инлайн-тело портя B, сохраним
        push    d               ; ref-walk
        push    h               ; new-walk
        ; ===== инлайн рисовка грязной клетки (бывш. _rw_put_cell) =====
        ; Входе: A = СТАРЫЙ тайл, HL = &tile_win[новый], C = кольцевой dst_low.
        ; Убраны call/ret: на плотном экране это ~27 T на каждую грязную клетку.
        mov     b,m             ; B = новый тайл
        ; B = (nz[ref]<<2) | nz[new]: бит0/1 = плоскости НОВОГО (copy), бит2/3 = СТАРОГО (erase)
        mov     l,a             ; A = ref ещё цел
        mvi     h,0
        lxi     d,_tile_nz
        dad     d
        mov     a,m             ; A = nz[ref]
        add     a               ; nzref<<2 в биты 2..3 (освоб. биты 0..1 под nznew)
        add     a
        mov     l,b
        mvi     h,0
        dad     d               ; HL = &nz[new], DE = база не тронута
        ora     m               ; A = (nzref<<2)|nznew
        ; HL = &_tileset[new*16] (плоскость веса 8, строка 0)
        mov     l,b
        mvi     h,0
        dad     h
        dad     h
        dad     h
        dad     h
        lxi     d,_tileset
        dad     d
        mov     b,a             ; B = комбин. маска (новый тайл больше не нужен)

        ; --- плоскость 0 (вес 8) ---
        ani     01h             ; bit0 = nznew.plane0
        jnz     rw_p0w          ; новый содержит плоскость -> copy8
        mov     a,b
        ani     04h             ; bit2 = nzref.plane0
        jz      rw_p0skip       ; пусто в обоих -> пропуск
        ; erase: новый пуст, старый содержал -> залить нулями без чтения tileset
        lda     rw_dsthi
        mov     d,a
        mov     e,c
        xra     a
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        lxi     d,8
        dad     d               ; HL += 8 -> плоскость веса 4
        jmp     rw_p1
rw_p0skip:
        lxi     d,8
        dad     d               ; HL += 8 -> плоскость веса 4 (пропуск)
        jmp     rw_p1
rw_p0w:
        lda     rw_dsthi
        mov     d,a
        mov     e,c               ; dst_low уже в C
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d               ; HL += 8 -> плоскость веса 4

        ; --- плоскость 1 (вес 4) ---
rw_p1:
        mov     a,b
        ani     02h             ; bit1 = nznew.plane1
        jnz     rw_p1w          ; новый содержит -> copy8
        mov     a,b
        ani     08h             ; bit3 = nzref.plane1
        jz      rw_pcell_done   ; пусто в обоих -> готово
        lda     rw_dsthi+1      ; erase: новый пуст, старый содержал -> нули
        mov     d,a
        mov     e,c
        xra     a
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        stax    d
        dcx     d
        jmp     rw_pcell_done
rw_p1w:
        lda     rw_dsthi+1
        mov     d,a
        mov     e,c
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
        mov     a,m
        stax    d
        inx     h
        dcx     d
rw_pcell_done:
        pop     h
        pop     d
        pop     b
rw_scan_next:
        mov     a,c
        sui     8               ; кольцевой переход (0->255) для следующей строки
        mov     c,a
        inx     h
        inx     d
        dcr     b
        jnz     rw_scan
rw_blk_ret:
        ret

; ---------------------------------------------------------------
; БЫСТРЫЙ ПУТЬ render_window: разность колонок по запечённой таблице ранов.
;
; При |old_cam - cam| == 1 эталон блока — соседняя колонка, поэтому набор
; «грязных» строк блока запечён в ROM (rw_run_ofs -> rw_run_data, пары
; (row,count), терминатор (0,0)). Построчное сравнение tile_win (~86 T на
; каждую из ~500 просмотренных строк за шаг) не нужно вовсе.
;
; Направление. Скролл вперёд (old = cam-1): эталон блока i — колонка
; w0+i-1, т.е. таблица колонки w0+i (rwf_tbl0). Скролл назад (old = cam+1):
; эталон — w0+i+1, а разность симметрична — берём таблицу колонки w0+i+1
; (rwf_tbl1, rwf_adj = 1). В обоих случаях таблица идёт на шаг +1 на блок.
;
; Клетка пишется БЕЗ tile_nz: обе фоновые плоскости всегда (пустая плоскость
; — это 8 нулей, для VRAM то же самое, а маска стоила дороже своих 4% байт).
; Регистры: B = страница плоскости веса 4 (на весь блок), C = кольцевой
; dst_low (убывает сам вместе с копированием веса 4), D/E = VRAM веса 8,
; HL = tile_win. Счётчик строк рана живёт в rwf_cnt — именно поэтому B
; свободен под страницу, а копирование идёт dcr e/dcr c: D не портится,
; пересчёт низа на строку не нужен. На время клетки HL уезжает в стек.
; ---------------------------------------------------------------
rwf_tbl0:
        xra     a               ; эталон блока — w0+i-1: таблица колонки w0+i
        jmp     rwf_prep
rwf_tbl1:
        mvi     a,1             ; эталон — w0+i+1: таблица колонки w0+i+1
rwf_prep:
        sta     rwf_adj
        ; w0 = cam + blk0
        lhld    rw_cam
        lda     rw_blk
        mov     e,a
        mvi     d,0
        dad     d
        shld    rw_w0
        ; pnew = &tile_win[локальная колонка w0] (без cam_row)
        lda     _tile_win_base
        mov     c,a
        lda     _tile_win_base+1
        mov     b,a
        mov     a,l
        sub     c
        mov     l,a
        mov     a,h
        sbb     b
        mov     h,a             ; HL = w0 - base
        xchg
        lda     _tile_stride
        mov     c,a
        call    _mulshift
        lxi     d,_tile_win
        dad     d
        shld    rwf_pnew
        ; rwf_rp = _rw_run_data + rw_run_ofs[w0 + adj]
        lhld    rw_w0
        lda     rwf_adj
        mov     e,a
        mvi     d,0
        dad     d               ; HL = w0 + adj
        dad     h               ; *2: rw_run_ofs — u16
        lxi     d,_rw_run_ofs
        dad     d
        mov     e,m
        inx     h
        mov     d,m             ; DE = смещение колонки в rw_run_data
        lxi     h,_rw_run_data
        dad     d
        shld    rwf_rp
        ; страницы VRAM текущего блока: rwf_hi0 = вес 8, B = вес 4 (+20h).
        ; B держится на весь блок, в ране не пересчитывается
        lda     rw_blk
        adi     080h
        sta     rwf_hi0
        adi     020h
        mov     b,a

rwf_col:
        lhld    rwf_rp
rwf_run:
        mov     a,m             ; row
        inx     h
        mov     e,m             ; count
        inx     h
        shld    rwf_rp          ; на следующий ран (или на следующую колонку)
        mov     d,a             ; D = row
        mov     a,e
        ora     a
        jz      rwf_col_done    ; терминатор
        ; --- клип рана в полосу [cam_row, cam_row+ROWS) ---
        ; Быстрый путь: ран целиком внутри полосы (row >= lo и
        ; row-lo+count <= ROWS). Тогда обе обрезки не нужны, а число строк
        ; рана — это count как есть: на ран выходит ~90 T дешевле полного клипа.
        lda     _cam_row
        mov     c,a             ; C = lo
        mov     a,d
        sub     c
        jc      rwf_clip        ; row < lo
        add     e               ; A = row-lo+count — конец рана в полосе
        cpi     ROWS+1
        jnc     rwf_clip        ; хвост рана вылез за полосу
        mov     a,e             ; полоса не режет — строк ровно count
rwf_rows:                       ; A = строк в полосе, D = первая мировая строка
        sta     rwf_cnt         ; остаток строк рана (B занят страницей веса 4)
        ; C = dst_low = cpl(8*row): VRAM адресована МИРОВЫМ рядом, поэтому
        ; cam_row в адрес не входит (сдвиг экрана делает регистр скролла).
        ; Строки рана — мировые: 8*row mod 256 == 8*(row mod 32).
        mov     a,d
        add     a
        add     a
        add     a
        cma
        mov     c,a
        ; HL = src = pnew + row
        mov     a,d
        mov     e,a
        mvi     d,0
        lhld    rwf_pnew
        dad     d               ; HL = pnew + row

        ; --- клетка: обе плоскости тайла, 16 байт ---
        ; Клетка = один вызов общего цикла копирования _rw_tile16: 8 байт в
        ; плоскость A (DE, страница D = rwf_hi0) и 8 в плоскость B (BC,
        ; страница B = вес 8 + 20h, держится на весь блок). Низ — в C:
        ; _rw_tile16 убывает его сам, это и есть низ следующей строки.
rwf_cell:
        push    h               ; src-указатель рана
        mov     l,m             ; тайл
        mvi     h,0
        dad     h
        dad     h
        dad     h
        dad     h               ; HL = тайл*16
        lxi     d,_tileset
        dad     d               ; HL = &tileset[тайл] (DE затирается)
        lda     rwf_hi0
        mov     d,a             ; D = страница веса 8
        mov     e,c             ; E = низ
        call    _rw_tile16
        pop     h
        inx     h
        lda     rwf_cnt
        dcr     a
        sta     rwf_cnt
        jnz     rwf_cell
        jmp     rwf_col          ; HL = tile_win -> перезагрузить указатель ранов

        ; --- холодный путь клипа: ран пересекает край полосы ---
        ; B занят страницей веса 4, поэтому считаем по E.
rwf_clip:
        mov     a,d
        add     e
        mov     e,a             ; E = row + count (<= rows <= 255)
        mov     a,d
        sub     c               ; C = lo
        jnc     rwf_c0
        mov     d,c             ; row < lo -> row = lo
rwf_c0:
        mov     a,c
        adi     ROWS
        mov     c,a             ; C = hi
        mov     a,e
        sub     c
        jc      rwf_c1
        mov     e,c             ; row+count > hi -> обрезать
rwf_c1:
        mov     a,e
        sub     d               ; строк в полосе
        jz      rwf_run         ; пусто -> следующий ран
        jc      rwf_run
        jmp     rwf_rows        ; A = строк

        ; --- колонка кончилась: сдвиг на следующий блок ---
rwf_col_done:
        shld    rwf_rp
        lda     _tile_stride
        mov     e,a
        mvi     d,0
        lhld    rwf_pnew
        dad     d
        shld    rwf_pnew          ; pnew += stride
        lda     rwf_hi0
        inr     a
        sta     rwf_hi0
        adi     020h
        mov     b,a             ; вес 4 = вес 8 + 20h, страница следующего блока
        lda     rw_blk
        inr     a
        sta     rw_blk
        mov     e,a
        lda     rw_end
        cmp     e
        jz      rw_epilog
        jmp     rwf_col

    ; ---------------------------------------------------------------
    ; _rw_tile16: общий цикл копирования — 16 байт тайла вниз по кольцу.
    ;   Первые 8 байт идут в плоскость A (DE), вторые 8 — в плоскость B (BC).
    ;   Низ обеих плоскостей независим, поэтому одна рутина обслуживает все
    ;   четыре места: клетку render_window (страницы весов 8 и 4, низ общий),
    ;   колонку render_rowband (то же), прогон mario_draw и mario_undraw (страница
    ;   персонажа одна, низ B = низ A - 8 — то есть строки 8..15 того же прогона).
    ;   Ветвлений нет: убывание идёт байтом (dcr e/dcr c), а не парой — на
    ;   переходе через шов кольца (0 -> 255) dcr страницу не трогает.
    ;   вход:  HL = src (16 байт), DE = (страница A, низ A), BC = (страница B, низ B)
    ;   выход: HL = src+16, E = низ A - 8, C = низ B - 8
    ; ---------------------------------------------------------------
        SECTION code_clib
_rw_tile16:
        mov     a,m
        stax    d
        inx     h
        dcr     e
        mov     a,m
        stax    d
        inx     h
        dcr     e
        mov     a,m
        stax    d
        inx     h
        dcr     e
        mov     a,m
        stax    d
        inx     h
        dcr     e
        mov     a,m
        stax    d
        inx     h
        dcr     e
        mov     a,m
        stax    d
        inx     h
        dcr     e
        mov     a,m
        stax    d
        inx     h
        dcr     e
        mov     a,m
        stax    d
        inx     h
        dcr     e
        mov     a,m
        stax    b
        inx     h
        dcr     c
        mov     a,m
        stax    b
        inx     h
        dcr     c
        mov     a,m
        stax    b
        inx     h
        dcr     c
        mov     a,m
        stax    b
        inx     h
        dcr     c
        mov     a,m
        stax    b
        inx     h
        dcr     c
        mov     a,m
        stax    b
        inx     h
        dcr     c
        mov     a,m
        stax    b
        inx     h
        dcr     c
        mov     a,m
        stax    b
        inx     h
        dcr     c
        ret

; ---------------------------------------------------------------
; void render_rowband(unsigned int world_row, unsigned int cam)
;
; Полная (без разности) зарисовка одной мировой тайловой строки world_row по
; всем 32 экраным колонкам для текущего cam. Пишем ОБЕ фоновые плоскости
; (включая небо = тайл 0) — при вертикальном скролле в этих кольцевых строках
; лежала другая мировая строка, её надо затереть. Спрайт в этих строках будет
; перерисован mario_draw позже, здесь его не трогаем.
;   sccz80 classic: arg1 world_row (sp+4), arg2 cam (sp+2).
; ---------------------------------------------------------------
        SECTION code_clib
_render_rowband:
        lxi     h,4
        dad     sp
        mov     a,m             ; world_row lo
        sta     rb_row
        lxi     h,2
        dad     sp
        mov     a,m             ; cam lo
        mov     c,a
        inx     h
        mov     h,m             ; cam hi
        mov     l,a             ; HL = cam (мировая)
        lda     _tile_win_base
        mov     c,a
        lda     _tile_win_base+1
        mov     b,a             ; BC = base
        mov     a,l
        sub     c
        mov     l,a
        mov     a,h
        sbb     b
        mov     h,a             ; HL = local = cam - base
        xchg                    ; DE = local
        lda     _tile_stride
        mov     c,a
        call    _mulshift       ; HL = local*stride
        lxi     d,_tile_win
        dad     d
        lda     rb_row
        add     l
        mov     l,a
        mvi     a,0
        adc     h
        mov     h,a
        shld    rb_walk         ; rb_walk = tile_win + local*stride + world_row
        ; rb_dstlow = 255 - 8*(world_row & 31)
        lda     rb_row
        ani     1Fh
        add     a
        add     a
        add     a
        cma
        sta     rb_dstlow
        mvi     a,0
        sta     rb_blk
rb_loop:
        lhld    rb_walk
        mov     a,m             ; индекс тайла
        mov     l,a
        mvi     h,0
        dad     h
        dad     h
        dad     h
        dad     h               ; *16
        lxi     d,_tileset
        dad     d               ; HL = &tileset[tile*16] (плоскость веса 8, строка 0)
        lda     rb_blk
        mov     c,a             ; C = blk
        ; D = страница плоскости A (вес 8), B = плоскость B (вес 4)
        lda     vram_bases
        add     c
        mov     d,a
        lda     vram_bases+1
        add     c
        mov     b,a
        lda     rb_dstlow
        mov     e,a
        mov     c,a             ; C = низ плоскости B = низ A
        call    _rw_tile16       ; HL += 16, E/C -= 8
        ; rb_walk += stride
        lhld    rb_walk
        lda     _tile_stride
        mov     e,a
        mvi     d,0
        dad     d
        shld    rb_walk
        ; blk++
        lda     rb_blk
        inr     a
        sta     rb_blk
        cpi     32
        jnz     rb_loop
        pop     de              ; адрес возврата
        inx     sp
        inx     sp
        inx     sp
        inx     sp              ; съесть world_row, cam (4 байта)
        push    de
        ret

; ---------------------------------------------------------------
; void mario_draw(unsigned char x, unsigned char y, const unsigned char *spr)
;
; Прямая запись спрайта 16x16 в 2 плоскости персонажа. 4 прогона (плоскость
; вес 2, вес 1 x колонка блока 0,1) по 16 байт: байт спрайта -> кольцевой адрес
; VRAM, адрес идёт на убывание (dcr e/dcr c — спрайт может пересечь шов кольца).
; Прогон = один вызов общего цикла _rw_tile16: строка в адресе у него — низ
; страницы (D), поэтому обе половины прогона пишутся в одну плоскость, если
; низ B = низ A - 8, а страница B = страница A.
; Слепка VRAM и маскирования нет: спрайт не трогает фоновые плоскости.
; x кратен 8 (левый блок = x/8, правая половина спрайта = блок x/8+1), y —
; МИРОВОЙ пиксельный ряд верха спрайта (младший байт = world_y mod 256).
; ---------------------------------------------------------------
        SECTION code_clib
_mario_draw:
        ; sccz80: spr (sp+2), y (sp+4), x (sp+6)
        lxi     h,6
        dad     sp
        mov     a,m             ; x
        ora     a               ; сброс CY перед rra
        rra
        rra
        rra
        ani     1Fh
        sta     md_blk
        lxi     h,4
        dad     sp
        mov     a,m             ; y (world mod 256)
        cma                     ; 255 - y = адрес верхнего байта прогона
        sta     md_ytop
        lxi     h,2
        dad     sp
        mov     a,m             ; spr lo
        mov     c,a
        inx     h
        mov     h,m             ; spr hi
        mov     l,a
        shld    md_spr_cur

        ; --- старшие байты 4 прогонов: char_bases[p] + blk (+1 для правой) ---
        ; порядок прогонов: [w2 лев.][w2 прав.][w1 лев.][w1 прав.]
        lda     md_blk
        mov     c,a
        lda     char_bases
        add     c
        sta     md_vtab+1       ; run0 hi = вес2, левый блок
        inr     a
        sta     md_vtab+3       ; run1 hi = вес2, правый блок
        lda     char_bases+1
        add     c
        sta     md_vtab+5       ; run2 hi = вес1, левый блок
        inr     a
        sta     md_vtab+7       ; run3 hi = вес1, правый блок
        ; младшие байты (смещение в блоке) — все 255-y
        lda     md_ytop
        sta     md_vtab
        sta     md_vtab+2
        sta     md_vtab+4
        sta     md_vtab+6

        ; --- сброс бегущих указателей ---
        lxi     h,md_vtab
        shld    md_vtab_cur
        mvi     a,MARIO_RUNS
        sta     md_runs

md_run_loop:
        ; адрес начала прогона -> DE
        lhld    md_vtab_cur
        mov     a,m
        mov     e,a
        inx     h
        mov     a,m
        mov     d,a
        inx     h               ; следующий прогон: +2 от начала пары
        shld    md_vtab_cur     ; DE = адрес VRAM (пара из md_vtab)
        mov     b,d             ; плоскость B — та же страница персонажа
        mov     a,e
        sui     HALF_TILE       ; низ B = низ A - 8: строки 8..15 прогона
        mov     c,a
        lhld    md_spr_cur      ; HL = байты спрайта этого прогона
        call    _rw_tile16      ; строки 0..7 в DE, 8..15 в BC
        shld    md_spr_cur      ; HL += 16

        lda     md_runs
        dcr     a
        jz      md_draw_done
        sta     md_runs
        jmp     md_run_loop

md_draw_done:
        pop     de              ; адрес возврата
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp
        inx     sp              ; съесть x, y, spr (6 байт)
        push    de
        ret

; ---------------------------------------------------------------
; void mario_undraw(void)
;
; Обнулить 2 плоскости персонажа в прямоугольнике прошлого кадра (таблица
; md_vtab ещё в силе). Фон под спрайтом НЕ трогаем — он не затирается, поэтому
; слепок не нужен. 4 прогона x 16 байт = 64 записи нуля (~0.4 kT против 113 kT
; на перерисовку двух блоков фоном в прежней схеме). Источник нулей — тайл 0
; (`_tileset`, небо: 16 байт нуля), так что цикл тот же — _rw_tile16.
; ---------------------------------------------------------------
        SECTION code_clib
_mario_undraw:
        lxi     h,md_vtab
        shld    md_vtab_cur
        mvi     a,MARIO_RUNS
        sta     md_runs
md_ud_loop:
        lhld    md_vtab_cur
        mov     a,m
        mov     e,a
        inx     h
        mov     a,m
        mov     d,a
        inx     h               ; следующий прогон: +2 от начала пары
        shld    md_vtab_cur     ; DE = адрес VRAM
        mov     b,d             ; плоскость B — та же страница персонажа
        mov     a,e
        sui     HALF_TILE       ; низ B = низ A - 8: строки 8..15 прогона
        mov     c,a
        lxi     h,_tileset      ; тайл 0 = небо = 16 байт нуля
        call    _rw_tile16
        lda     md_runs
        dcr     a
        jz      md_ud_done
        sta     md_runs
        jmp     md_ud_loop
md_ud_done:
        ret
