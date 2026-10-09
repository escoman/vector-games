; mario.asm — горячий путь демки Mario 16-цвет для Вектора-06Ц.
;
;   void render_window(unsigned int cam, unsigned int old_cam,
;                      unsigned char blk0, unsigned char nblk)
;       — дорисовка nblk экранных блоков (столбцов по 8 пикселей) начиная с
;         blk0. cam — мировой тайловый столбец у левого края экрана, old_cam —
;         тот, что уже нарисован в VRAM. Отрисовывается РАЗНОСТЬ: блок не
;         трогается, если тайл совпал, а плоскость блока не трогается, если она
;         пуста и в старом, и в новом тайле (карта tile_nz). old_cam ==
;         CAM_NO_REF означает «в VRAM пусто» (первый экран) — эталоном служит
;         тайл 0 = чистое небо.
;
;   void mario_draw(unsigned char x, unsigned char y, const unsigned char *spr)
;       — снять слепок VRAM под спрайтом (128 байт) и наложить спрайт 16x16.
;   void mario_undraw(void)
;       — вернуть снятый слепок (стирает Марио). Порядок кадра:
;         undraw -> render_window -> mario_draw.
;
; Формат Вектора: плоскости вес 8/4/2/1 в 0x8000/0xA000/0xC000/0xE000; блок =
; x/8 (256 байт), байт i хранит строку y = 255 - i (строки сверху вниз идут по
; УБЫВАЮЩЕМУ адресу), старший бит байта = левый пиксель.
;
; Тайл 8x8 (tileset): 4 плоскости по 8 байт, порядок весов 8,4,2,1; в плоскости
; строки 0..7 сверху вниз. 32 байта на тайл. Тайл 0 = пустой (небо) => его
; первые 32 байта — нули, их используем как эталон «пусто» для первого экрана.
; Тайлкарта (tilemap): tilemap[мировой_столбец*32 + строка] — индекс тайла.
; tile_nz[t]: бит p = 1, если плоскость p тайла непустая.
; pair_top[c] = min(col_top[c], col_top[c+1]) — самая верхняя строка, где в паре
; соседних колонок есть содержимое; строки выше — небо в обеих колонках.
;
; Спрайт 16x16 (mario.inc): 8 прогонов (плоскость 0..3 x колонка блока 0..1) по
; 16 пар (keep, set), res = (old & keep) ^ set. Прогон идёт по адресам VRAM,
; убывающим на 1 за строку, поэтому цикл наложения — на двух указателях.
;
; Соглашение вызова z88dk classic (__z88dk_callee): аргументы в 16-битных
; слотах, callee чистит стек. Только инструкции Intel 8080.

        SECTION code_clib

        PUBLIC  _render_window
        PUBLIC  _mario_draw
        PUBLIC  _mario_undraw

        EXTERN  _tileset
        EXTERN  _tilemap
        EXTERN  _tile_nz
        EXTERN  _pair_top

ROWS EQU 32                 ; тайлов по высоте экрана (256/8)
CAM_NO_REF EQU 0FFFFh       ; old_cam: в VRAM пусто (первый экран)
MARIO_RUNS EQU 8            ; прогонов спрайта: 4 плоскости x 2 колонки
MARIO_ROWS EQU 16           ; байт VRAM в прогоне

; ---------------------------------------------------------------
; BSS — рабочие переменные.
; ---------------------------------------------------------------
        SECTION bss_clib

; --- render_window ---
rw_cam:     defw    0           ; новый мировой столбец у левого края
rw_ref:     defw    0           ; old_cam (или CAM_NO_REF)
rw_blk:     defb    0           ; текущий экранный блок
rw_end:     defb    0           ; последний блок (exclusive)
rw_newwalk: defw    0           ; &tilemap[cam*32], шаг +32 на блок
rw_refcell: defw    0           ; &tilemap[old*32] + top (временный)
rw_refwalk: defw    0           ; &tilemap[old*32] (или _tileset = «пусто»)
rw_refstep: defb    0           ; 32 или 0 для CAM_NO_REF
rw_pairwalk:defw    0           ; &pair_top[min(cam,old)], шаг +1 на блок
rw_pairstep:defb    0           ; 1 или 0 для CAM_NO_REF
rw_top:     defb    0           ; первая строка сканирования текущего блока
rw_const:   defb    0           ; dst_low = rw_const - 8*lo(tilemap-указателя)
rw_dsthi:   defb    0,0,0,0     ; старшие байты VRAM для 4 плоскостей блока
rw_dstlow:  defb    0           ; младший байт VRAM для строки тайла
rw_nzmask:  defb    0           ; bit p = 1: плоскость p надо писать
rw_tnew:    defb    0           ; индекс нового тайла ячейки
rw_tref:    defb    0           ; индекс старого тайла ячейки

; --- mario_draw / mario_undraw ---
md_blk:     defb    0           ; левый блок Марио (x/8)
md_ytop:    defb    0           ; 255 - y (адрес верхнего байта прогона)
md_runs:    defb    0           ; сколько прогонов спрайта осталось
md_vtab:    defs    MARIO_RUNS * 2  ; 8 начальных адресов VRAM под спрайтом
md_vrun:    defw    0           ; текущий адрес VRAM (между двумя проходами)
md_snap_cur:defw    0           ; бегущий указатель md_snap
md_vtab_cur:defw    0           ; бегущий указатель md_vtab
md_spr_cur: defw    0           ; бегущий указатель спрайта (пары keep,set)
md_snap:    defs    MARIO_RUNS * MARIO_ROWS   ; слепок VRAM под спрайтом

; Старшие байты баз плоскостей по весам 8,4,2,1 (адрес = base<<8 | смещение).
vram_bases: defb    080h, 0A0h, 0C0h, 0E0h

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
        ; rw_newwalk/rw_refwalk = tilemap + (cam+blk0)*32, а min() ниже дал
        ; min(cam,old)+blk0 — ровно то, что нужно для pair_top.
        lda     rw_blk
        mov     c,a
        lhld    rw_cam
        mov     a,l
        add     c
        mov     l,a
        mvi     a,0
        adc     h
        mov     h,a
        shld    rw_cam
        ; rw_newwalk = _tilemap + cam*32
        lhld    rw_cam
        dad     h
        dad     h
        dad     h
        dad     h
        dad     h               ; cam*32
        lxi     d,_tilemap
        dad     d
        shld    rw_newwalk

        ; CAM_NO_REF? (h и l оба 0FFh => h & l == 0FFh)
        lhld    rw_ref
        mov     a,h
        ana     l
        cpi     0FFh
        jnz     rw_have_ref

        ; Первый экран: эталон — тайл 0 (32 нуля в начале tileset), шаг 0,
        ; верх сканирования 0 (тоже байт 0 из tileset — тайл пустой).
        lxi     h,_tileset
        shld    rw_refwalk
        shld    rw_pairwalk
        xra     a
        sta     rw_refstep
        sta     rw_pairstep
        jmp     rw_walk_done

rw_have_ref:
        ; rw_refwalk = _tilemap + (old+blk0)*32
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
        dad     h
        dad     h
        dad     h
        dad     h
        dad     h
        lxi     d,_tilemap
        dad     d
        shld    rw_refwalk
        mvi     a,ROWS
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
        ; шаг указателями на следующий блок
        lhld    rw_newwalk
        lxi     d,ROWS
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
; _rw_block: дорисовать ОДИН экранный блок (столбец из 32 тайлов).
;
; Сравнивает tilemap[cam+blk] с tilemap[old+blk] построчно; строки выше
; pair_top заведомо небо в обеих колонках, поэтому пропускаются. Ничего не
; сохраняет (внутри только свои регистры), аргументы берёт из BSS.
; ---------------------------------------------------------------
_rw_block:
        lhld    rw_pairwalk
        mov     a,m             ; top = pair_top[min(cam,old) + blk]
        cpi     ROWS
        jz      rw_blk_ret      ; весь блок — небо в обеих колонках
        sta     rw_top

        ; dsthi[p] = vram_bases[p] + blk (адрес = hi<<8 | смещение в блоке)
        lda     rw_blk
        mov     c,a
        lda     vram_bases
        add     c
        sta     rw_dsthi
        lda     vram_bases+1
        add     c
        sta     rw_dsthi+1
        lda     vram_bases+2
        add     c
        sta     rw_dsthi+2
        lda     vram_bases+3
        add     c
        sta     rw_dsthi+3

        ; rw_const = 8*lo(&tilemap[cam+blk]) + 255  =>  dst_low = 255-8*row
        ; (add a, а не ral: ral заносит вылетевшие биты в младшие)
        lhld    rw_newwalk
        mov     a,l
        add     a
        add     a
        add     a
        adi     255
        sta     rw_const

        ; BC = счётчик строк, C = top
        lda     rw_top
        mov     c,a
        mvi     a,ROWS
        sub     c
        mov     b,a             ; B = 32 - top

        ; DE = rw_refwalk + top, HL = rw_newwalk + top
        ; (после первого xchg DE содержит new+top, поэтому ref+top держим
        ;  отдельно во временной ячейке)
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

        ; --- построчное сравнение: 50 T на чистую строку ---
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
        inx     h
        inx     d
        dcr     b
        jnz     rw_scan
rw_blk_ret:
        ret

; ---------------------------------------------------------------
; _rw_put_cell: нарисовать одну «грязную» клетку.
;
; Входе: A = индекс старого тайла, HL = &tilemap[новый]. BC/DE вызывающий
; сохранил сам; сама routine регистры не сохраняет.
; Плоскость пропускается, если она пуста и в старом, и в новом тайле.
; ---------------------------------------------------------------
_rw_put_cell:
        sta     rw_tref
        mov     a,m
        sta     rw_tnew

        ; dst_low = rw_const - 8*lo(cell)
        mov     a,l
        add     a
        add     a
        add     a
        mov     c,a
        lda     rw_const
        sub     c
        sta     rw_dstlow

        ; nzmask = tile_nz[new] | tile_nz[ref]
        ; HL и DE вызывающий сохранил сам; первый nz держим в C, а не в A:
        ; lda rw_tref затёр бы его, и в маске остались бы только нули эталона.
        lda     rw_tnew
        mov     l,a
        mvi     h,0
        lxi     d,_tile_nz
        dad     d
        mov     c,m             ; nz нового тайла (без масштабирования: 1 байт на тайл)
        lda     rw_tref
        mov     l,a
        mvi     h,0
        lxi     d,_tile_nz
        dad     d
        mov     a,c
        ora     m
        sta     rw_nzmask

        ; HL = &_tileset[new*32]
        lda     rw_tnew
        mov     l,a
        mvi     h,0
        dad     h
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
        jnz     rw_p1w
        lxi     d,8
        dad     d
        jmp     rw_p2
rw_p1w:
        lda     rw_dsthi+1
        mov     d,a
        lda     rw_dstlow
        mov     e,a
        call    _rw_copy8

        ; --- плоскость 2 (вес 2) ---
rw_p2:
        lda     rw_nzmask
        ani     04h
        jnz     rw_p2w
        lxi     d,8
        dad     d
        jmp     rw_p3
rw_p2w:
        lda     rw_dsthi+2
        mov     d,a
        lda     rw_dstlow
        mov     e,a
        call    _rw_copy8

        ; --- плоскость 3 (вес 1) ---
rw_p3:
        lda     rw_nzmask
        ani     08h
        jz      rw_pcell_ret
        lda     rw_dsthi+3
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
; поэтому VRAM идёт на убывание. 8*24 = 192 T.
; ---------------------------------------------------------------
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
; void mario_draw(unsigned char x, unsigned char y, const unsigned char *spr)
;
; Два прохода по 8 прогонам спрайта (плоскость 8,4,2,1 x колонка блока 0,1):
;   A — снять 128 байт VRAM в md_snap (это будущий «фон под Марио»);
;   B — наложить res = (VRAM & keep) ^ set прямо в VRAM.
; x должен быть кратен 8 (марио стоит на границе блока), правая половина
; спрайта попадает в блок x/8+1.
; ---------------------------------------------------------------
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
        mov     a,m             ; y
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

        ; --- старшие байты 8 прогонов: vram_bases[p] + blk (+1 для правой) ---
        lda     md_blk
        mov     c,a
        lda     vram_bases
        add     c
        sta     md_vtab+1
        inr     a
        sta     md_vtab+3
        lda     vram_bases+1
        add     c
        sta     md_vtab+5
        inr     a
        sta     md_vtab+7
        lda     vram_bases+2
        add     c
        sta     md_vtab+9
        inr     a
        sta     md_vtab+11
        lda     vram_bases+3
        add     c
        sta     md_vtab+13
        inr     a
        sta     md_vtab+15
        ; младшие байты (смещение в блоке) — все 255-y
        lda     md_ytop
        sta     md_vtab
        sta     md_vtab+2
        sta     md_vtab+4
        sta     md_vtab+6
        sta     md_vtab+8
        sta     md_vtab+10
        sta     md_vtab+12
        sta     md_vtab+14

        ; --- сброс бегущих указателей ---
        lxi     h,md_vtab
        shld    md_vtab_cur
        mvi     a,MARIO_RUNS
        sta     md_runs
        lxi     h,md_snap
        shld    md_snap_cur

md_run_loop:
        ; адрес начала прогона -> md_vrun
        lhld    md_vtab_cur
        mov     a,m
        mov     e,a
        inx     h
        mov     a,m
        mov     d,a
        inx     h               ; следующий прогон: +2 от начала пары
        shld    md_vtab_cur
        xchg                    ; HL = адрес VRAM (пара из md_vtab)
        shld    md_vrun         ; shld пишет HL, не DE

        ; --- проход A: VRAM -> md_snap ---
        lhld    md_vrun
        xchg                    ; DE = VRAM
        lhld    md_snap_cur     ; HL = куда писать слепок
        mvi     b,MARIO_ROWS
md_snap_px:
        ldax    d
        mov     m,a
        inx     h
        dcx     d
        dcr     b
        jnz     md_snap_px
        shld    md_snap_cur

        ; --- проход B: наложение спрайта ---
        lhld    md_vrun
        xchg                    ; DE = VRAM (с начала прогона)
        lhld    md_spr_cur      ; HL = пары (keep,set)
        mvi     b,MARIO_ROWS
md_comp_px:
        mov     a,m             ; keep
        mov     c,a
        inx     h               ; -> set
        ldax    d               ; old
        ana     c               ; old & keep
        xra     m               ; ^ set
        inx     h               ; -> следующий keep
        stax    d
        dcx     d
        dcr     b
        jnz     md_comp_px
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
; Вернуть слепок md_snap в те же адреса VRAM (таблица md_vtab ещё в силе).
; ~3.3 kT против 113 kT на перерисовку двух блоков фоном.
; ---------------------------------------------------------------
_mario_undraw:
        lxi     h,md_vtab
        shld    md_vtab_cur
        mvi     a,MARIO_RUNS
        sta     md_runs
        lxi     h,md_snap
        shld    md_snap_cur
md_ud_loop:
        lhld    md_vtab_cur
        mov     a,m
        mov     e,a
        inx     h
        mov     a,m
        mov     d,a
        inx     h               ; следующий прогон: +2 от начала пары
        shld    md_vtab_cur     ; DE = адрес VRAM
        lhld    md_snap_cur
        mvi     b,MARIO_ROWS
md_ud_px:
        mov     a,m
        stax    d
        inx     h
        dcx     d
        dcr     b
        jnz     md_ud_px
        shld    md_snap_cur
        lda     md_runs
        dcr     a
        jz      md_ud_done
        sta     md_runs
        jmp     md_ud_loop
md_ud_done:
        ret
