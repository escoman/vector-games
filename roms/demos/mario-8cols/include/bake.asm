; bake.asm — запекание RAM-окна тайлкарты (Mario 8-цвет, 8080).
;
;   void bake_clear(unsigned char cstart, unsigned char cend)
;       — занулить локальные колонки окна [cstart, cend).
;   void bake_groups(unsigned int wstart, unsigned int wend)
;       — запечь в окно МИРОВЫЕ колонки [wstart, wend) из словаря вариантов
;         (pf_data/pf_rects/pf_var_ofs/pf_var_n/pf_var_bb/pf_start).
;   void bake_window(void)
;       — полная перепечка окна [tile_win_base, tile_win_base+OBJ_WIN_COLS):
;         обнуление + bake_groups. Стартовый bake и прыжок камеры (респаун).
;   void bake_shift(unsigned int nb)
;       — переход границы окна: ставит tile_win_base = nb и печёт окно заново.
;         При сдвиге ВПЕРЁД дополнительно сохраняет в tile_win_prevcol уехавшую
;         за левый край колонку (страж для diff-рендера кадра перехода).
;
; ОКНО. tile_win — OBJ_WIN_COLS (64) колонок по LEVEL_ROWS (64) строк,
; КОЛОНКА-МАЖОР: tile_win[(col - tile_win_base)*stride + row]. Читают его
; mario.asm (рендер), solid_at (коллизии) и этот файл (запекание).
;
; ЗАЧЕМ ASM. C-версия на sccz80 на каждую клетку/прямоугольник зовёт
; 16-битные хелперы (l_gint/l_pint/l_uge) — сдвиг окна стоил 2 027 560 T,
; то есть 34 кадра, и на границе «запечённого» экрана картинка замирала
; на полсекунды.
;
; ЧТО ИЗМЕНИЛОСЬ ПО СРАВНЕНИЮ С C-ВЕРСИЕЙ:
;   * обнуление — заливка через SP (PUSH HL пишет 2 байта нуля за 16 T,
;     ~9 T/байт вместо ~270 T/байт у sccz80), как в lib/gfx/clr.asm;
;   * bake_shift больше НЕ сдвигает выжившую половину memmove'ом: на 8080
;     копирование стоит ~37 T/байт (2048 байт = 75k T), а перепечка окна
;     целиком (обнуление 4096 + скан словаря) выходит дешевле;
;   * скан экземпляров отсекается по bbox варианта (pf_var_bb, генерит
;     gen_assets.py): в полосу сдвига реально попадает ~14 экземпляров из 53;
;   * прямоугольники тестируются и клипаются в ЛОКАЛЬНЫХ 8-битных координатах
;     q = x + dx - wstart со смещением +128 (0..64), без 16-битных сравнений.
;     Это законно, потому что скан идёт по группам блоков pf_start[b0..b1]:
;     экземпляр группы g имеет x>>5 == g, поэтому x - wstart ∈ [-96, 63]
;     и в байт со смещением 128 ложится без потерь.
;
; Соглашение вызова z88dk classic (__z88dk_callee): аргументы в 16-битных
; слотах, слева направо (последний ближе к SP), callee чистит стек.
; Только инструкции Intel 8080.
;
; ВАЖНО: формат экземпляра держит вариант в 7 битах (p0) плюс p3 = v>>7.
; Здесь читается только p0, то есть PF_VARIANTS обязан быть < 128 —
; это проверяет tools/gen_assets.py.

        SECTION code_clib

        PUBLIC  _bake_clear
        PUBLIC  _bake_groups
        PUBLIC  _bake_window
        PUBLIC  _bake_shift

        EXTERN  _mulshift        ; HL = DE * stride (mario.asm)
        EXTERN  _tile_win        ; RAM-окно тайлкарты (объявлено в main.c)
        EXTERN  _tile_win_base   ; unsigned int: мировая колонка окна[0]
        EXTERN  _tile_win_prevcol; колонка-страж перед окном (main.c)
        EXTERN  _tile_stride     ; unsigned char: LEVEL_ROWS (шаг колонки окна)
        EXTERN  _pf_data         ; экземпляры уровня, 4 байта на экземпляр
        EXTERN  _pf_rects        ; прямоугольники вариантов, 5 байт на rect
        EXTERN  _pf_var_ofs      ; вариант -> первый rect (u16)
        EXTERN  _pf_var_n        ; вариант -> число rect'ов (u8)
        EXTERN  _pf_var_bb       ; вариант -> bbox по dx: {dx_min, dx_max+w_max}
        EXTERN  _pf_start        ; блок (x>>5) -> первый экземпляр группы (u16)

ROWS        EQU 64          ; = LEVEL_ROWS (level.inc): строк в колонке окна
WIN_COLS    EQU 64          ; = OBJ_WIN_COLS
WIN_STEP    EQU 32          ; = OBJ_WIN_STEP (шаг сдвига базы окна)
WIN_BLOCKS  EQU 10          ; = OBJ_WIN_BLOCKS
PF_BACK     EQU 3           ; = PF_BACK (блоков назад за широкие экземпляры)
ROWS_WORDS  EQU 32          ; ROWS/2 — страж копируется словами

; ---------------------------------------------------------------
; BSS — рабочие переменные.
; ---------------------------------------------------------------
        SECTION bss_clib

; --- bake_clear ---
bcl_sp:     defw 0          ; стек вызывающего на время заливки через SP
bcl_start:  defw 0          ; адрес начала заливки
bcl_len:    defw 0          ; длина в байтах

; --- bake_groups: параметры вызова ---
bg_ws:      defw 0          ; wstart (мировая колонка)
bg_we:      defw 0          ; wend
bg_hiq:     defb 0          ; wend - wstart (32 или 64)
bg_hib:     defb 0          ; 128 + hiq — правая граница полосы в смещённом байте
bg_qoff:    defb 0          ; wstart - tile_win_base (локальная колонка wstart)
bg_b0:      defb 0          ; первый блок скана
bg_b1:      defb 0          ; последний блок скана

; --- bake_groups: ход скана ---
bg_p:       defw 0          ; &pf_data[i] текущего экземпляра
bg_pend:    defw 0          ; &pf_data[end] (за последним)
bg_p0:      defb 0          ; p0 экземпляра: вариант | (x>>8)<<7
bg_v:       defb 0          ; вариант текущего экземпляра
bg_x:       defb 0          ; x экземпляра, младший байт
bg_y:       defb 0          ; y экземпляра
bg_bb_lo:   defb 0          ; bbox варианта: dx_min
bg_bb_hi:   defb 0          ; bbox варианта: dx_max + w_max
bg_o:       defw 0          ; &pf_rects[rect] текущего прямоугольника

; --- bake_groups: текущий прямоугольник ---
bg_qb:      defb 0          ; левый край в смещённом байте (q + 128)
bg_t:       defb 0          ; тайл
bg_dy:      defb 0          ; dy
bg_w:       defb 0          ; w
bg_nr:      defb 0          ; строк в прогоне (после клипа по ROWS)
bg_nc:      defb 0          ; колонок в прогоне (после клипа по полосе)
bg_cnt:     defb 0          ; счётчик колонок заливки
bg_lcol:    defb 0          ; локальная колонка левого края
bg_dst:     defw 0          ; адрес первой клетки прямоугольника в окне

; --- bake_shift ---
bg_nb:      defw 0          ; новая база окна

; ---------------------------------------------------------------
; void bake_clear(unsigned char cstart, unsigned char cend)
; ---------------------------------------------------------------
        SECTION code_clib

_bake_clear:
        ; sccz80: cend (sp+2), cstart (sp+4); старшие байты аргументов — мусор.
        lxi     h,2
        dad     sp
        mov     a,m             ; cend
        mov     b,a
        lxi     h,4
        dad     sp
        mov     a,m             ; cstart
        mov     c,a
        mov     a,b
        sub     c               ; A = cend - cstart
        jz      bcl_ret         ; пустой диапазон
        ; --- длина в байтах = ncols * stride ---
        mov     e,a
        mvi     d,0
        lda     _tile_stride
        mov     c,a
        call    _mulshift       ; HL = ncols * stride
        shld    bcl_len
        ; --- адрес начала = tile_win + cstart * stride ---
        lxi     h,4
        dad     sp
        mov     e,m
        mvi     d,0
        lda     _tile_stride
        mov     c,a
        call    _mulshift
        lxi     d,_tile_win
        dad     d
        shld    bcl_start

        ; --- заливка: SP уводится в конец диапазона, PUSH HL пишет 2 байта
        ; нуля ВНИЗ по адресам. Внутри цикла нет CALL/RET, прерывания
        ; запрещены (иначе вектор прерывания положит PC на место окна). ---
        di
        lxi     h,0
        dad     sp
        shld    bcl_sp          ; стек вызывающего
        lhld    bcl_start
        xchg                    ; DE = начало (адрес!)
        lhld    bcl_len
        dad     d               ; HL = начало + длина = конец (исключительно)
        sphl                    ; SP = конец диапазона
        ; нечётный хвост пишем отдельным байтом на ВЕРХНЕМ конце, чтобы
        ; оставшаяся длина была чётной (SP тогда тоже на чётной границе)
        lhld    bcl_len
        mov     a,l
        ani     1
        jz      bcl_even
        dcx     h               ; длина стала чётной
        shld    bcl_len
        dad     d               ; HL = начало + (длина - 1) = адрес хвоста
        mvi     m,0
        sphl                    ; SP = конец парного диапазона
        jmp     bcl_words
bcl_even:
        dad     d
        sphl
bcl_words:
        ; --- DE = число слов = чётная длина / 2 (DE — уже не адрес!) ---
        lhld    bcl_len
        mov     a,h
        ora     a
        rar
        mov     d,a
        mov     a,l
        rar
        mov     e,a
        lxi     h,0             ; HL = 0 -> PUSH пишет два нулевых байта
        ; пачки по 32 PUSH = 64 байта (ровно колонка при stride = ROWS)
bcl_batch:
        mov     a,d
        ora     a
        jnz     bcl_do32        ; DE >= 256 — пачка точно влезает
        mov     a,e
        cpi     32
        jc      bcl_tail
bcl_do32:
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        push    h
        mov     a,e
        sui     32
        mov     e,a
        mov     a,d
        sbi     0
        mov     d,a
        jmp     bcl_batch
bcl_tail:
        mov     a,d
        ora     e
        jz      bcl_fin
        push    h
        dcx     d
        jmp     bcl_tail
bcl_fin:
        lhld    bcl_sp
        sphl
        ei
bcl_ret:
        pop     d               ; адрес возврата
        inx     sp
        inx     sp
        inx     sp
        inx     sp              ; съесть cstart, cend (4 байта)
        push    d
        ret

; ---------------------------------------------------------------
; void bake_groups(unsigned int wstart, unsigned int wend)
; ---------------------------------------------------------------
        SECTION code_clib

_bake_groups:
        ; sccz80: wend (sp+2), wstart (sp+4)
        lxi     h,4
        dad     sp
        mov     a,m
        sta     bg_ws
        inx     h
        mov     a,m
        sta     bg_ws+1
        lxi     h,2
        dad     sp
        mov     a,m
        sta     bg_we
        inx     h
        mov     a,m
        sta     bg_we+1

        ; --- hiq = wend - wstart (32 или 64; младших байт достаточно),
        ;     hib = 128+hiq — всё, что правее смещённого байта hib, вне полосы ---
        lda     bg_we
        mov     b,a
        lda     bg_ws
        mov     c,a
        mov     a,b
        sub     c
        sta     bg_hiq
        ori     80h
        sta     bg_hib

        ; --- qoff = wstart - tile_win_base (0 или 32) ---
        lhld    _tile_win_base
        lda     bg_ws
        sub     l
        sta     bg_qoff

        ; --- b0 = max((wstart>>5) - PF_BACK, 0) ---
        lhld    bg_ws
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,l
        cpi     PF_BACK+1
        jc      bg_b0_zero
        sui     PF_BACK
        jmp     bg_b0_set
bg_b0_zero:
        mvi     a,0
bg_b0_set:
        sta     bg_b0

        ; --- b1 = min(((wend-1)>>5), WIN_BLOCKS-1) ---
        lhld    bg_we
        dcx     h
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,h
        ora     a
        rar
        mov     h,a
        mov     a,l
        rar
        mov     l,a
        mov     a,l
        cpi     WIN_BLOCKS
        jc      bg_b1_set
        mvi     a,WIN_BLOCKS-1
bg_b1_set:
        sta     bg_b1

        ; --- bg_p = pf_data + pf_start[b0]*4 ---
        lda     bg_b0
        add     a
        mov     l,a
        mvi     h,0
        lxi     d,_pf_start
        dad     d
        mov     e,m
        inx     h
        mov     d,m             ; DE = pf_start[b0]
        mov     h,d
        mov     l,e
        dad     h
        dad     h               ; HL = 4 * индекс
        lxi     d,_pf_data
        dad     d
        shld    bg_p
        ; --- bg_pend = pf_data + pf_start[b1+1]*4 ---
        lda     bg_b1
        inr     a
        add     a
        mov     l,a
        mvi     h,0
        lxi     d,_pf_start
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        mov     h,d
        mov     l,e
        dad     h
        dad     h
        lxi     d,_pf_data
        dad     d
        shld    bg_pend

        ; ===========================================================
        ; Цикл по экземплярам полосы.
        ; Регистры цикла: DE — &экземпляра, C — q0 (x - wstart + 128),
        ; B — счётчик прямоугольников варианта.
        ; ===========================================================
bg_inst:
        lhld    bg_p
        xchg                    ; DE = текущий экземпляр
        lhld    bg_pend
        mov     a,e
        sub     l
        mov     a,d
        sbb     h
        jnc     bg_done         ; DE >= pend — полоса кончилась
        ; --- p0 (вариант | (x>>8)<<7), x, y ---
        ldax    d
        sta     bg_p0
        inx     d
        ldax    d
        sta     bg_x
        inx     d
        ldax    d
        sta     bg_y
        inx     d
        ; p3 (v>>7) не читаем: PF_VARIANTS < 128 (проверка в gen_assets.py).

        ; --- q0 = x - wstart + 128 (байт; x - wstart ∈ [-96, 63]) ---
        lda     bg_x
        mov     c,a
        lda     bg_ws
        mov     b,a
        mov     a,c
        sub     b
        adi     128
        mov     c,a             ; C = q0

        ; --- bbox варианта: {dx_min, dx_max+w_max} ---
        lda     bg_p0
        ani     7Fh
        sta     bg_v
        add     a
        mov     l,a
        mvi     h,0
        lxi     d,_pf_var_bb
        dad     d
        mov     a,m             ; bb_lo = dx_min
        sta     bg_bb_lo
        inx     h
        mov     a,m             ; bb_hi = dx_max + w_max
        sta     bg_bb_hi
        ; отсев влево: q0 + bb_hi <= 128  (x + dx_max+w_max <= wstart)
        add     c
        jc      bg_bb_lo_test
        cpi     129
        jc      bg_inst_next
bg_bb_lo_test:
        ; отсев вправо: q0 + bb_lo > 128 + hiq  (x + dx_min > wend - 1).
        ; sub даёт заём ровно тогда, когда qb правее полосы; равенство
        ; (qb == hib) пропускаем — нулевую ширину отсечёт клип прямоугольника.
        lda     bg_bb_lo
        add     c
        jc      bg_inst_next
        mov     l,a
        lda     bg_hib
        sub     l
        jc      bg_inst_next

        ; --- bg_o = pf_rects + pf_var_ofs[v]*5 ---
        lda     bg_v
        add     a
        mov     l,a
        mvi     h,0
        lxi     d,_pf_var_ofs
        dad     d
        mov     e,m
        inx     h
        mov     d,m             ; DE = vofs
        mov     h,d
        mov     l,e
        dad     h
        dad     h               ; 4*vofs
        dad     d               ; 5*vofs
        lxi     d,_pf_rects
        dad     d
        shld    bg_o
        ; --- B = число прямоугольников варианта ---
        lda     bg_v
        mov     l,a
        mvi     h,0
        lxi     d,_pf_var_n
        dad     d
        mov     a,m
        ora     a
        jz      bg_inst_next
        mov     b,a
        lhld    bg_o
        xchg                    ; DE = &rect

        ; ===========================================================
        ; Цикл по прямоугольникам. DE — &rect, C — q0, B — счётчик.
        ; Смещённый байт: qb = q0 + dx, q = qb - 128; «в полосе» = qb < 128+hiq.
        ; ===========================================================
bg_rect:
        inx     d
        ldax    d               ; dx
        add     c               ; A = qb
        jc      bg_rect_skip    ; q >= 128 — правее полосы
        mov     l,a             ; L = qb
        lda     bg_hib
        sub     l
        jc      bg_rect_skip    ; q > hiq — правее полосы
        ; --- прямоугольник задевает полосу: дочитать поля ---
        push    b               ; сохранить счётчик и q0
        mov     a,l
        sta     bg_qb
        dcx     d
        ldax    d               ; t
        sta     bg_t
        inx     d
        inx     d
        ldax    d               ; dy
        sta     bg_dy
        inx     d
        ldax    d               ; w
        sta     bg_w
        inx     d
        ldax    d               ; h
        mov     b,a
        mov     h,d
        mov     l,e
        shld    bg_o            ; DE ещё нужен: в конце вернём &rect

        ; --- nrows = h, но не ниже конца колонки ---
        lda     bg_y
        mov     c,a
        lda     bg_dy
        add     c               ; A = y + dy
        mov     c,a
        mov     a,b
        add     c               ; A = h + y + dy (перенос — заведомо клип)
        jc      bg_clip_rows
        cpi     ROWS+1
        jc      bg_rows_ok      ; h влезает целиком
bg_clip_rows:
        mvi     a,ROWS
        sub     c               ; nrows = ROWS - (y + dy)
        jc      bg_rect_done    ; y + dy > ROWS — прямоугольник ниже окна
        mov     b,a
bg_rows_ok:
        mov     a,b
        ora     a
        jz      bg_rect_done    ; пустой прямоугольник (иначе dcr 0 -> 255 строк)
        sta     bg_nr

        ; --- правый клип: hi_b = min(qb + w, 128 + hiq) ---
        lda     bg_qb
        mov     c,a
        lda     bg_w
        add     c               ; A = qb + w
        jc      bg_hi_full
        mov     l,a
        lda     bg_hib
        sub     l
        jc      bg_hi_full      ; qb + w > 128 + hiq — обрезать по краю
        mov     a,l
        jmp     bg_hi_set
bg_hi_full:
        lda     bg_hib
bg_hi_set:
        mov     l,a             ; L = hi_b
        ; --- левый клип: lo_b = max(qb, 128) ---
        lda     bg_qb
        cpi     128
        jnc     bg_lo_set
        mvi     a,128
bg_lo_set:
        mov     c,a             ; C = lo_b
        mov     a,l
        sub     c               ; A = число колонок
        jz      bg_rect_done
        jc      bg_rect_done
        sta     bg_nc
        ; --- локальная колонка = (lo_b - 128) + qoff ---
        mov     a,c
        sui     128
        mov     c,a
        lda     bg_qoff
        add     c
        sta     bg_lcol

        ; --- dst = tile_win + lcol*stride + y + dy ---
        lda     bg_lcol
        mov     e,a
        mvi     d,0
        lda     _tile_stride
        mov     c,a
        call    _mulshift       ; HL = lcol * stride
        lxi     d,_tile_win
        dad     d
        lda     bg_y
        mov     e,a
        lda     bg_dy
        add     e
        mov     e,a
        mvi     d,0
        dad     d               ; HL = &(первая клетка прямоугольника)
        shld    bg_dst

        ; --- заливка: ncols колонок по nrows байт с шагом stride ---
        lhld    bg_dst
        xchg                    ; DE = первая клетка
        lda     bg_nc
        sta     bg_cnt
bg_col:
        lda     bg_nr
        mov     c,a
        lda     bg_t            ; A = тайл (портится шагом ниже)
        mov     h,d
        mov     l,e
bg_row:
        mov     m,a
        inx     h
        dcr     c
        jnz     bg_row
        ; DE += stride
        lda     _tile_stride
        mov     c,a
        mov     a,e
        add     c
        mov     e,a
        mov     a,d
        aci     0
        mov     d,a
        lda     bg_cnt
        dcr     a
        sta     bg_cnt
        jnz     bg_col

bg_rect_done:
        lhld    bg_o
        xchg                    ; DE = &rect (на o[4])
        pop     b
        jmp     bg_rect_next
bg_rect_skip:
        ; отсев из первой проверки: DE ещё на o[1], догнать до o[4]
        inx     d
        inx     d
        inx     d
bg_rect_next:
        inx     d               ; DE = &следующего rect (5 байт на rect)
        dcr     b
        jnz     bg_rect

bg_inst_next:
        lhld    bg_p
        lxi     d,4
        dad     d
        shld    bg_p
        jmp     bg_inst

bg_done:
        pop     d               ; адрес возврата
        inx     sp
        inx     sp
        inx     sp
        inx     sp              ; съесть wstart, wend (4 байта)
        push    d
        ret

; ---------------------------------------------------------------
; void bake_window(void)
;   Полная перепечка окна [tile_win_base, tile_win_base+OBJ_WIN_COLS).
; ---------------------------------------------------------------
        SECTION code_clib

_bake_window:
        lxi     h,0
        push    h               ; cstart = 0
        lxi     h,WIN_COLS
        push    h               ; cend = OBJ_WIN_COLS
        call    _bake_clear     ; аргументы снимает сам
        lhld    _tile_win_base
        push    h               ; wstart = база окна
        lxi     d,WIN_COLS
        dad     d
        push    h               ; wend = база + окно
        call    _bake_groups
        ret

; ---------------------------------------------------------------
; void bake_shift(unsigned int nb)
;   База окна ставится в nb и окно печётся заново. При сдвиге вперёд
;   (nb == base + WIN_STEP) колонка, уехавшая за левый край (мировая nb-1 =
;   старая локальная WIN_STEP-1), копируется в tile_win_prevcol: на кадре
;   перехода diff-рендер берёт её как эталон нулевого блока
;   (ref = tile_win + (old_cam - base)*stride = tile_win - ROWS).
;   При сдвиге назад страж не нужен: old_cam остаётся внутри нового окна,
;   а прыжок камеры рисуется общим путём (rw_slow) — как и раньше.
; ---------------------------------------------------------------
        SECTION code_clib

_bake_shift:
        ; sccz80: nb (sp+2)
        lxi     h,2
        dad     sp
        mov     a,m
        sta     bg_nb
        inx     h
        mov     a,m
        sta     bg_nb+1
        ; --- сдвиг ровно на шаг? (иначе прыжок камеры — страж не нужен) ---
        lhld    _tile_win_base
        mov     a,l
        mov     e,a             ; E = base_lo
        lda     bg_nb
        mov     c,a             ; C = nb_lo
        mov     a,h
        mov     d,a             ; D = base_hi
        lda     bg_nb+1
        mov     b,a             ; B = nb_hi
        mov     a,c
        sub     e
        mov     a,b
        sbb     d
        jnz     bs_go           ; разность не влезает в байт — точно не шаг
        mov     a,c
        sub     e
        cpi     WIN_STEP
        jnz     bs_go
        ; --- колонка WIN_STEP-1 старого окна -> tile_win_prevcol ---
        mvi     e,WIN_STEP-1
        mvi     d,0
        lda     _tile_stride
        mov     c,a
        call    _mulshift       ; HL = (WIN_STEP-1) * stride
        lxi     d,_tile_win
        dad     d
        xchg                    ; DE = &окно[WIN_STEP-1]
        lxi     b,_tile_win_prevcol
        lxi     h,ROWS_WORDS
bs_copy:
        ldax    d
        stax    b
        inx     d
        inx     b
        ldax    d
        stax    b
        inx     d
        inx     b
        dcx     h
        mov     a,l
        ora     h
        jnz     bs_copy
bs_go:
        lhld    bg_nb
        shld    _tile_win_base
        call    _bake_window
        pop     d               ; адрес возврата
        inx     sp
        inx     sp              ; съесть nb (2 байта)
        push    d
        ret
