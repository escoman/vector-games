;
; bake.asm — запекание RAM-окна тайлкарты (Mario 8-col, Vector-06Ц).
;
;   void bake_clear(unsigned char cstart, unsigned char cend)
;       — занулить локальные колонки окна [cstart, cend).
;   void bake_cols(unsigned int wstart, unsigned int wend)
;       — запечь в окно МИРОВЫЕ колонки [wstart, wend) из таблицы спанов
;         (pf_spans/pf_span_ofs).
;   void bake_window(void)
;       — полная перепечка окна [tile_win_base, tile_win_base+OBJ_WIN_COLS):
;         обнуление + bake_cols. Стартовый bake и прыжок камеры (респаун).
;   void bake_shift(unsigned int nb)
;       — переход границы окна: ставит tile_win_base = nb и печёт окно заново.
;         При сдвиге ВПЕРЁД дополнительно сохраняет в tile_win_prevcol уехавшую
;         за левый край колонку (страж для diff-рендера кадра перехода).
;
; ОКНО. tile_win — OBJ_WIN_COLS (64) колонок по LEVEL_ROWS (64) строк,
; КОЛОНКА-МАЖОР: tile_win[(col - tile_win_base)*stride + row]. Читают его
; mario.asm (рендер), solid_at (коллизии) и этот файл (запекание).
;
; ЧТО ЛЕЖИТ В ROM. Не описание уровня, а готовый его результат: по-колоночные
; СПАНЫ — максимальные вертикальные прогоны одинакового непустого тайла
; (pf_spans + pf_span_ofs, генерит tools/gen_assets.py через
; prefablib.spans_of). Запись спана:
;
;     {tile, 2*row}            одиночная клетка
;     {tile, 2*row|1, len}     прогон, len >= 2
;     {0xFF}                   конец колонки
;
; Бит 0 «байта строки» — признак прогона, поэтому ANA A + RAR дают обратно
; row и кладут признак в перенос: ANA A гасит перенос от CPI, RAR сдвигает
; туда признак (а в бит 7 — ноль, row < 64). 0xFF вместо тайла — конец
; колонки (тайла 0xFF не бывает: tile < TILESET_N, небо = 0 в спаны не
; пишется). Спаны колонки c лежат в pf_spans[ofs[c] .. ofs[c+1]).
;
; ПОЧЕМУ ТАК. Раньше в ROM лежал словарь вариантов префаба (pf_data/pf_rects/
; pf_var_*/pf_start), и печка разворачивала экземпляры в тайлы на лету: клип
; прямоугольника по полосе, bbox-отсев, умножение локальной колонки на stride.
; Стоило это 2 027 560 T на C и 410 668 T на ASM — то есть 6.9 кадра на
; границе «запечённого» экрана. Словарь читает ТОЛЬКО печка (рендер и коллизии
; читают готовое окно), поэтому его заменили результатом: печка стала
; «скопировать спаны колонки», без клипа и без умножений (~одна клетка на
; инструкцию), а сам словарь из ROM исчез.
;
; ПЕРЕНОС В БАЙТЕ АДРЕСА. Адрес клетки считается как (base_hi, base_lo + row)
; — одной 8-битной суммой, потому что H (старший байт базы колонки) живёт в
; регистре весь проход колонки. Если tile_win не выровнен на 64, сумма может
; переполнить байт: это не ошибка (ветка bp_hi), просто +10 T на спан. Выравнивать
; не обязательно, но выровненное окно чуть дешевле.
;
; Соглашение вызова z88dk classic (__z88dk_callee): аргументы в 16-битных
; слотах, слева направо (последний ближе к SP), callee чистит стек.
; Только инструкции Intel 8080.

        SECTION code_clib

        PUBLIC  _bake_clear
        PUBLIC  _bake_cols
        PUBLIC  _bake_window
        PUBLIC  _bake_shift

        EXTERN  _mulshift        ; HL = DE * stride (mario.asm)
        EXTERN  _tile_win        ; RAM-окно тайлкарты (объявлено в main.c)
        EXTERN  _tile_win_base   ; unsigned int: мировая колонка окна[0]
        EXTERN  _tile_win_prevcol; колонка-страж перед окном (main.c)
        EXTERN  _tile_stride     ; unsigned char: LEVEL_ROWS (шаг колонки окна)
        EXTERN  _pf_spans        ; по-колоночные спаны: {tile, 2*row[|1[,len]]}, 0xFF
        EXTERN  _pf_span_ofs     ; колонка -> смещение в pf_spans (u16, +1 sentinel)

ROWS        EQU 64          ; = LEVEL_ROWS (level.inc): строк в колонке окна
WIN_COLS    EQU 64          ; = OBJ_WIN_COLS
WIN_STEP    EQU 32          ; = OBJ_WIN_STEP (шаг сдвига базы окна)
ROWS_WORDS  EQU 32          ; ROWS/2 — страж копируется словами
SPAN_END    EQU 0FFh        ; конец списка спанов колонки

; ---------------------------------------------------------------
; BSS — рабочие переменные.
; ---------------------------------------------------------------
        SECTION bss_clib

; --- bake_clear ---
bcl_sp:     defw 0          ; стек вызывающего на время заливки через SP
bcl_start:  defw 0          ; адрес начала заливки
bcl_len:    defw 0          ; длина в байтах

; --- bake_cols ---
bp_dst:     defw 0          ; адрес первой клетки запекаемой колонки
bp_cnt:     defb 0          ; сколько колонок осталось

; --- bake_shift ---
bp_nb:      defw 0          ; новая база окна

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
; void bake_cols(unsigned int wstart, unsigned int wend)
;   Печёт МИРОВЫЕ колонки [wstart, wend) в окно, начиная с локальной
;   колонки wstart - tile_win_base. Вызывается только с окном целиком:
;   [base, base+OBJ_WIN_COLS).
;
;   Регистры внутри цикла (горячая часть):
;       DE — поток спанов текущей колонки
;       H  — старший байт адреса базы колонки (живёт весь проход колонки)
;       C  — младший байт базы колонки
;       B  — тайл текущего спана
;       L  — младший байт адреса клетки (base_lo + row)
;       A  — рабочая
;   Счётчик колонок — в BSS: он нужен раз на колонку, а регистры в цикле
;   заняты (7 регистров на 7 значений).
; ---------------------------------------------------------------
        SECTION code_clib

_bake_cols:
        ; sccz80: wend (sp+2), wstart (sp+4)
        lxi     h,2
        dad     sp
        mov     a,m             ; wend lo
        mov     b,a
        lxi     h,4
        dad     sp
        mov     a,m             ; wstart lo
        mov     c,a
        mov     a,b
        sub     c               ; A = сколько колонок (32 или 64)
        jz      bp_ret
        sta     bp_cnt
        ; --- bp_dst = tile_win + (wstart - base) * ROWS ---
        lhld    _tile_win_base
        mov     a,c
        sub     l               ; A = локальная колонка wstart (0 или 32)
        mov     l,a
        mvi     h,0
        dad     h
        dad     h
        dad     h
        dad     h
        dad     h
        dad     h               ; HL = локальная колонка * ROWS
        lxi     d,_tile_win
        dad     d
        shld    bp_dst
        ; --- DE = &pf_spans[pf_span_ofs[wstart]] ---
        lxi     h,4
        dad     sp
        mov     e,m
        inx     h
        mov     d,m             ; DE = wstart
        mov     h,d
        mov     l,e
        dad     h               ; HL = 2 * wstart
        lxi     d,_pf_span_ofs
        dad     d
        mov     e,m
        inx     h
        mov     d,m             ; DE = смещение потока для этой колонки
        lxi     h,_pf_spans
        dad     d
        xchg                    ; DE = поток спанов
        ; --- база первой колонки ---
        lhld    bp_dst
        mov     c,l             ; C = base_lo; H уже = base_hi

; ===========================================================
; Цикл по спанам колонки. Запись {tile, 2*row|признак_прогона}
; [ , len]. Тайл 0xFF — конец колонки.
; ===========================================================
bp_col:
        ldax    d               ; тайл
        inx     d
        cpi     SPAN_END
        jz      bp_next         ; колонка кончилась
        mov     b,a             ; B = тайл
        ldax    d               ; 2*row | признак прогона
        inx     d
        ana     a               ; сбросить перенос от CPI — иначе RAR затолкает его в бит 7
        rar                     ; A = row, перенос = признак прогона
        jc      bp_run
        add     c               ; A = row + base_lo
        mov     l,a
        jc      bp_hi           ; переполнился байт адреса — H на единицу выше
        mov     a,b
        mov     m,a
        jmp     bp_col
bp_hi:
        inr     h
        mov     a,b
        mov     m,a
        dcr     h
        jmp     bp_col

; --- прогон: первая клетка уже посчитана, дальше len клеток подряд ---
bp_run:
        add     c               ; A = row + base_lo
        mov     l,a
        jc      bp_run_hi
bp_run_cells:
        ldax    d               ; len >= 2
        inx     d
        mov     c,a             ; C = счётчик (base_lo вернём из bp_dst)
        mov     a,b
bp_run_loop:
        mov     m,a
        inx     h               ; перенос в H законен: клетки идут подряд
        dcr     c
        jnz     bp_run_loop
        lhld    bp_dst          ; H/C — снова база колонки
        mov     c,l
        jmp     bp_col
bp_run_hi:
        inr     h
        jmp     bp_run_cells

; --- следующая колонка: база += ROWS.
; DE здесь — указатель на спаны следующей колонки, поэтому шаг прибавляем
; через BC (B в этот момент мёртв: тайл перечитывается каждым спаном).
; ---
bp_next:
        lhld    bp_dst
        lxi     b,ROWS
        dad     b
        shld    bp_dst
        mov     c,l             ; H уже = base_hi новой колонки
        lda     bp_cnt
        dcr     a
        sta     bp_cnt
        jnz     bp_col
bp_ret:
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
        call    _bake_cols
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
;
;   Перепекается ВСЁ окно, а не половина: на 8080 memmove выживших 2 КиБ
;   (~70k T) дороже, чем обнулить окно заливкой через SP (39.5k T) и скопировать
;   спаны всех 64 колонок (~65k T): половина окна не сдвигается, а меняет
;   локальный номер, то есть её всё равно пришлось бы переносить.
; ---------------------------------------------------------------
        SECTION code_clib

_bake_shift:
        ; sccz80: nb (sp+2)
        lxi     h,2
        dad     sp
        mov     a,m
        sta     bp_nb
        inx     h
        mov     a,m
        sta     bp_nb+1
        ; --- сдвиг ровно на шаг? (иначе прыжок камеры — страж не нужен) ---
        lhld    _tile_win_base
        mov     a,l
        mov     e,a             ; E = base_lo
        lda     bp_nb
        mov     c,a             ; C = nb_lo
        mov     a,h
        mov     d,a             ; D = base_hi
        lda     bp_nb+1
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
        lhld    bp_nb
        shld    _tile_win_base
        call    _bake_window
        pop     d               ; адрес возврата
        inx     sp
        inx     sp              ; съесть nb (2 байта)
        push    d
        ret
