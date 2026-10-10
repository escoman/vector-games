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
; Тайлкарта (tilemap): tilemap[мировой_столбец*stride + строка] — индекс тайла
; (stride = LEVEL_ROWS). tile_nz[t]: бит0 = непуста плоскость веса 8, бит1 = веса 4.
; pair_top[c] = min(col_top[c], col_top[c+1]) — самая верхняя МИРОВАЯ строка, где
; в паре соседних колонок есть содержимое; строки выше — небо в обеих колонках.
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
        EXTERN  _tilemap
        EXTERN  _tile_nz
        EXTERN  _pair_top
        EXTERN  _cam_row        ; unsigned char: мировая тайловая строка верха экрана
        EXTERN  _tile_stride    ; unsigned char: LEVEL_ROWS (шаг колонки тайлкарты)

ROWS EQU 32                 ; экранных тайлов по высоте (256/8) — всегда 32
CAM_NO_REF EQU 0FFFFh       ; old_cam: в VRAM пусто (первый экран)
MARIO_RUNS EQU 4            ; прогонов спрайта: 2 плоскости персонажа x 2 колонки
MARIO_ROWS EQU 16           ; байт VRAM в прогоне

; ---------------------------------------------------------------
; BSS — рабочие переменные.
; ---------------------------------------------------------------
        SECTION bss_clib

; --- render_window ---
rw_cam:     defw    0           ; новый мировой столбец у левого края (+blk0)
rw_ref:     defw    0           ; old_cam (+blk0) (или CAM_NO_REF)
rw_blk:     defb    0           ; текущий экранный блок
rw_end:     defb    0           ; последний блок (exclusive)
rw_newwalk: defw    0           ; &tilemap[cam*stride + cam_row], шаг +stride на блок
rw_refcell: defw    0           ; &tilemap[old*stride + cam_row] + top (временный)
rw_refwalk: defw    0           ; &tilemap[old*stride + cam_row] (или _tileset = «пусто»)
rw_refstep: defb    0           ; stride или 0 для CAM_NO_REF
rw_pairwalk:defw    0           ; &pair_top[min(cam,old)], шаг +1 на блок
rw_pairstep:defb    0           ; 1 или 0 для CAM_NO_REF
rw_top:     defb    0           ; первая ЭКРАННАЯ строка сканирования текущего блока
rw_dstlow_cur:defb  0           ; кольцевой dst_low текущей сканируемой строки
rw_dsthi:   defb    0,0         ; старшие байты VRAM для 2 фоновых плоскостей блока
rw_dstlow:  defb    0           ; младший байт VRAM для строки тайла
rw_nzmask:  defb    0           ; bit p = 1: фоновая плоскость p надо писать
rw_tnew:    defb    0           ; индекс нового тайла ячейки
rw_tref:    defb    0           ; индекс старого тайла ячейки

; --- render_rowband ---
rb_blk:     defb    0           ; текущая экранная колонка 0..31
rb_row:     defb    0           ; мировая тайловая строка
rb_dstlow:  defb    0           ; кольцевой dst_low строки (одинаков для всех колонок)
rb_walk:    defw    0           ; &tilemap[cam*stride + world_row], шаг +stride

; --- mulstride (HL = DE * C) ---
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
; Результат заведомо < 64K (cam*stride < размер tilemap).
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

        ; --- начальные указатели колонок ---
        ; окно может начинаться не с нуля: cam и old сдвигаем на blk0, чтобы
        ; rw_newwalk/rw_refwalk = tilemap + (cam+blk0)*stride + cam_row, а min()
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
        ; rw_newwalk = _tilemap + cam*stride + cam_row
        lhld    rw_cam
        xchg                    ; DE = cam(+blk0)
        lda     _tile_stride
        mov     c,a
        call    _mulstride      ; HL = cam*stride
        lxi     d,_tilemap
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
        ; rw_refwalk = _tilemap + (old+blk0)*stride + cam_row
        lda     rw_blk
        mov     c,a
        lhld    rw_ref
        mov     a,l
        add     c
        mov     l,a
        mvi     a,0
        adc     h
        mov     h,a
        shld    rw_ref          ; old += blk0: min() ниже даёт min+blk0
        xchg                    ; DE = old+blk0
        lda     _tile_stride
        mov     c,a
        call    _mulstride      ; HL = old*stride
        lxi     d,_tilemap
        dad     d
        lda     _cam_row
        add     l
        mov     l,a
        mvi     a,0
        adc     h
        mov     h,a
        shld    rw_refwalk
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
; Сравнивает tilemap[cam+blk] с tilemap[old+blk] построчно; строки экрана, чьи
; МИРОВЫЕ ряды лежат выше pair_top, заведомо небо в обеих колонках — пропускаем.
; Кольцевой dst_low строки держим в rw_dstlow_cur (стартует от 255-8*(cam_row+top)
; и уменьшается на 8 за строку; 8-битное sui даёт естественное закольцовывание).
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
        ; rw_dstlow_cur = 255 - 8*((cam_row + rw_top) & 31) = cpl((cam_row+top)*8 mod 256)
        mov     b,a             ; B = rw_top
        lda     _cam_row
        add     b               ; cam_row + rw_top  (< 256)
        add     a
        add     a
        add     a               ; *8 (младший байт == (cam_row+top)*8 mod 256)
        cma                     ; 255 - x
        sta     rw_dstlow_cur

        ; dsthi[p] = vram_bases[p] + blk (адрес = hi<<8 | смещение в блоке)
        lda     rw_blk
        mov     c,a
        lda     vram_bases
        add     c
        sta     rw_dsthi
        lda     vram_bases+1
        add     c
        sta     rw_dsthi+1

        ; BC = счётчик строк, C = top
        lda     rw_top
        mov     c,a
        mvi     a,ROWS
        sub     c
        mov     b,a             ; B = 32 - top

        ; DE = rw_refwalk + top, HL = rw_newwalk + top
        ; (оба rw_*walk уже содержат cam_row; top — экранное смещение)
        lhld    rw_refwalk
        mvi     d,0
        mov     e,c
        dad     d
        shld    rw_refcell      ; ref+top
        lhld    rw_newwalk
        mvi     d,0
        mov     e,c
        dad     d               ; HL = new+top
        xchg                    ; DE = new+top, HL = 0:top
        lhld    rw_refcell
        xchg                    ; DE = ref+top, HL = new+top

        ; --- построчное сравнение ---
rw_scan:
        ldax    d               ; A = старый тайл
        cmp     m               ; совпал с новым?
        jz      rw_scan_next
        push    b
        push    d
        push    h
        call    _rw_put_cell
        pop     h
        pop     d
        pop     b
rw_scan_next:
        lda     rw_dstlow_cur
        sui     8               ; кольцевой переход (0->255) для следующей строки
        sta     rw_dstlow_cur
        inx     h
        inx     d
        dcr     b
        jnz     rw_scan
rw_blk_ret:
        ret

; ---------------------------------------------------------------
; _rw_put_cell: нарисовать одну «грязную» клетку (2 фоновые плоскости).
;
; Входе: A = индекс старого тайла, HL = &tilemap[новый]. BC/DE вызывающий
; сохранил сам; сама routine регистры не сохраняет. dst_low берётся из
; rw_dstlow_cur (кольцевой адрес строки). Плоскость пропускается, если она
; пуста и в старом, и в новом тайле.
; ---------------------------------------------------------------
        SECTION code_clib
_rw_put_cell:
        sta     rw_tref
        mov     a,m
        sta     rw_tnew

        ; dst_low = кольцевой адрес текущей строки
        lda     rw_dstlow_cur
        sta     rw_dstlow

        ; nzmask = tile_nz[new] | tile_nz[ref]
        lda     rw_tnew
        mov     l,a
        mvi     h,0
        lxi     d,_tile_nz
        dad     d
        mov     c,m             ; nz нового тайла (1 байт на тайл)
        lda     rw_tref
        mov     l,a
        mvi     h,0
        lxi     d,_tile_nz
        dad     d
        mov     a,c
        ora     m
        sta     rw_nzmask

        ; HL = &_tileset[new*16]
        lda     rw_tnew
        mov     l,a
        mvi     h,0
        dad     h
        dad     h
        dad     h
        dad     h
        lxi     d,_tileset
        dad     d

        ; --- плоскость 0 (вес 8) ---
        lda     rw_nzmask
        ani     01h
        jnz     rw_p0w
        lxi     d,8
        dad     d
        jmp     rw_p1
rw_p0w:
        lda     rw_dsthi
        mov     d,a
        lda     rw_dstlow
        mov     e,a
        call    _rw_copy8

        ; --- плоскость 1 (вес 4) ---
rw_p1:
        lda     rw_nzmask
        ani     02h
        jz      rw_pcell_ret
        lda     rw_dsthi+1
        mov     d,a
        lda     rw_dstlow
        mov     e,a
        call    _rw_copy8
rw_pcell_ret:
        ret

; ---------------------------------------------------------------
; _rw_copy8: перенести 8 байт тайла (HL, вверх) в VRAM (DE, вниз).
;
; Байт j плоскости (строка тайла сверху вниз) идёт в адрес 255-8*row-j,
; поэтому VRAM идёт на убывание. Тайл (8 пиксельных строк, кратных 8) НИКОГДА
; не пересекает шов кольца (256 не кратно 8 со сдвигом <8), поэтому dcx d
; безопасен: младший байт доходит до 0, но не занимает перенос в старший.
; 8*24 = 192 T.
; ---------------------------------------------------------------
        SECTION code_clib
_rw_copy8:
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
        mov     l,a             ; HL = cam
        xchg                    ; DE = cam
        lda     _tile_stride
        mov     c,a
        call    _mulstride      ; HL = cam*stride
        lxi     d,_tilemap
        dad     d
        lda     rb_row
        add     l
        mov     l,a
        mvi     a,0
        adc     h
        mov     h,a
        shld    rb_walk         ; rb_walk = tilemap + cam*stride + world_row
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
        ; плоскость 0 (вес 8)
        lda     vram_bases
        add     c
        mov     d,a
        lda     rb_dstlow
        mov     e,a
        call    _rw_copy8       ; HL += 8
        ; плоскость 1 (вес 4)
        lda     vram_bases+1
        add     c
        mov     d,a
        lda     rb_dstlow
        mov     e,a
        call    _rw_copy8
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
; VRAM, адрес идёт на убывание (dcr e — спрайт может пересечь шов кольца).
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
        lhld    md_spr_cur      ; HL = байты спрайта этого прогона
        mvi     b,MARIO_ROWS
md_px:
        mov     a,m             ; байт спрайта (маска пикселей плоскости)
        stax    d               ; прямая запись в плоскость персонажа
        inx     h
        dcr     e               ; вниз по кольцу (столбец = D не трогаем)
        dcr     b
        jnz     md_px
        shld    md_spr_cur

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
; на перерисовку двух блоков фоном в прежней схеме).
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
        mvi     b,MARIO_ROWS
        xra     a               ; A = 0 — прозрачность спрайта (фон покажет своё)
md_ud_px:
        stax    d               ; обнулить плоскость персонажа
        dcr     e               ; вниз по кольцу (столбец = D не трогаем)
        dcr     b
        jnz     md_ud_px
        lda     md_runs
        dcr     a
        jz      md_ud_done
        sta     md_runs
        jmp     md_ud_loop
md_ud_done:
        ret
