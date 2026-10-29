;
; spr_new.asm — ПРОТОТИП нового блит-ядра beam-sprites для бенчмарка spr-speed.
; Живёт ТОЛЬКО в roms/tests/spr-speed (не трогает lib/gfx/spr.asm). Реализует
; dense-путь формата из docs/SPR_FORMAT.MD: один setup на спрайт, пропуск
; отсутствующих плоскостей (не затираем нулями), длинный вертикальный прогон
; на столбец (адрес убывает вниз по экрану — dec H).
;
; Конвенция z88dk classic (как _spr_glyph_at): аргументы на стеке, caller-cleanup,
; SP не трогаем, ret. arg1 (dst) в sp+4, arg2 (desc) в sp+2.
;
; void spr_blit_dense(unsigned int dst, unsigned int desc)
;   dst  = адрес ВЕРХНЕЙ строки левого столбца, база плоскости П3 (0x8000+...)
;   desc = [0]FLAGS [1]COLS [2]DEPTH(тайл-ряды) [3..]DATA
;          FLAGS bit0..3 = наличие П3/П2/П1/П0; bit4 маска; bit5 sparse; bit6 OR
;          (dense-прототип чтит только биты наличия плоскостей bit0..3)
;          DATA: по плоскостям (П3,П2,П1,П0) x по столбцам, прогон = DEPTH*8 байт
;
; Геометрия (docs/SPR_FORMAT.MD §2): шаг в соседний столбец +0x100 (inr H),
; шаг в следующую плоскость +0x2000 (H += 20h); внутри прогона адрес УБЫВАЕТ
; (dcx H) — экранная строка Y вниз => смещение 255-Y.
;

        SECTION code_clib
        PUBLIC  _spr_blit_dense

; --- рабочие переменные (bss при --no-crt не зануляется, но все инициализируются
;     на входе до первого использования) ---
        SECTION bss_clib
sbd_vram:   defw    0       ; база текущей плоскости (VRAM-курсор)
sbd_cdst:   defw    0       ; курсор столбца (верх)
sbd_data:   defw    0       ; курсор блока данных
sbd_flags:  defb    0       ; FLAGS
sbd_cols:   defb    0       ; COLS
sbd_cc:     defb    0       ; счётчик столбцов
sbd_runlen: defb    0       ; DEPTH*8 — байт на прогон
sbd_pmask:  defb    0       ; маска наличия текущей плоскости (1,2,4,8)
sbd_pc:     defb    0       ; счётчик плоскостей 4..1

        SECTION code_clib
_spr_blit_dense:
        lxi     h,2
        dad     sp
        mov     e,m
        inx     h
        mov     d,m             ; DE = desc (arg2, sp+2)
        lxi     h,4
        dad     sp
        mov     a,m
        inx     h
        mov     h,m
        mov     l,a             ; HL = dst (arg1, sp+4)
        shld    sbd_vram        ; база плоскости П3 = верх левого столбца
        xchg                    ; HL = desc
        mov     a,m
        sta     sbd_flags       ; [0] FLAGS
        inx     h
        mov     a,m
        sta     sbd_cols        ; [1] COLS
        inx     h
        mov     a,m             ; [2] DEPTH (тайл-ряды)
        rlc
        rlc
        rlc                     ; *8 -> байт на прогон
        sta     sbd_runlen
        inx     h               ; HL = DATA
        shld    sbd_data
        mvi     a,01h
        sta     sbd_pmask       ; бит наличия П3
        mvi     a,04h
        sta     sbd_pc          ; 4 плоскости

sbd_plane:
        lda     sbd_flags
        mov     b,a
        lda     sbd_pmask
        ana     b
        jz      sbd_adv         ; плоскость отсутствует: данных нет, пропуск
        ; --- COLS прогонов текущей плоскости ---
        lhld    sbd_vram
        shld    sbd_cdst        ; курсор столбцов = база плоскости
        lda     sbd_cols
        sta     sbd_cc
sbd_col:
        lhld    sbd_data
        xchg                    ; DE = src (данные прогона)
        lhld    sbd_cdst        ; HL = dst (верх столбца)
        lda     sbd_runlen
        mov     b,a             ; B = счётчик байт прогона
sbd_run:
        ldax    d
        mov     m,a
        inx     d               ; src++
        dcx     h               ; dst-- (адрес вниз по экрану)
        dcr     b
        jnz     sbd_run
        ; DE = sbd_data + runlen -> следующий прогон
        mov     a,e
        sta     sbd_data
        mov     a,d
        sta     sbd_data+1
        ; курсор столбца += 0x100 (соседний столбец)
        lhld    sbd_cdst
        inr     h
        shld    sbd_cdst
        ; счётчик столбцов
        lda     sbd_cc
        dcr     a
        sta     sbd_cc
        jnz     sbd_col

sbd_adv:
        ; база плоскости += 0x2000
        lhld    sbd_vram
        mov     a,h
        adi     20h
        mov     h,a
        shld    sbd_vram
        ; маска наличия <<= 1
        lda     sbd_pmask
        rlc
        sta     sbd_pmask
        ; счётчик плоскостей
        lda     sbd_pc
        dcr     a
        sta     sbd_pc
        jnz     sbd_plane
        ret
