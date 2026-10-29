;
; spr_smc.asm — ПРОТОТИП SMC-ядра (самомодифицирующийся код) для бенчмарка
; spr-speed. Живёт ТОЛЬКО в roms/tests/spr-speed (не трогает lib/gfx/spr.asm).
;
; Идея (предложение пользователя): ОДИН раз прочитать флаги дескриптора и путём
; самомодификации кода (а) запечь указатель DATA непосредственным operand'ом,
; (б) заблокировать отрисовку отсутствующих плоскостей (jmp через copy),
; (в) нужным плоскостям оставить nop-слоты (падают straight в copy),
; (г) после ПОСЛЕДНЕЙ наличной плоскости сделать ранний ret — не ходить по
;     хвостовым пустым плоскостям.
; Код грузится в RAM 0x0100 => самомодификация легальна (проверено: запись
; 0xC9 в адрес ядра читается обратно; BASIC 2.997 тоже патчит свой код).
;
; Конвенция z88dk classic: аргументы на стеке, caller-cleanup, SP не трогаем.
;   void spr_patch8(unsigned int desc)      — arg1 desc в sp+2
;   void spr_blit8_smc(unsigned int dst)    — arg1 dst  в sp+2
;
; Формат дескриптора (docs/SPR_FORMAT.MD §3, 8x8 случай COLS=1 DEPTH=1):
;   [0]FLAGS [1]COLS [2]DEPTH [3..]DATA. FLAGS bit0..3 = наличие П3/П2/П1/П0.
;   DATA упакована ТОЛЬКО наличными плоскостями в порядке П3,П2,П1,П0 по 8 байт.
; Геометрия (apples-to-apples с spr_glyph_at): приёмник шагает +8 (inx h) внутри
;   copy, затем +0x1FF8 (dad b) = net +0x2000 на следующую плоскость. Пропуск
;   плоскости: +0x2000 напрямую (inx/de источника НЕ трогаем — DE остаётся
;   выровнен по упакованной DATA).
;

        SECTION code_clib
        PUBLIC  _spr_patch8
        PUBLIC  _spr_blit8_smc

; =====================================================================
;  void spr_blit8_smc(unsigned int dst)   — 8x8, до 4 плоскостей, SMC
; =====================================================================
_spr_blit8_smc:
        lxi     h,2
        dad     sp
        mov     a,m
        inx     h
        mov     h,m
        mov     l,a             ; HL = dst (arg1, sp+2) = верх левого столбца П3
smc_src:
        lxi     d,0             ; [PATCH] DE = DATA base (imm запечён spr_patch8)

; ---------------------------- plane П3 ----------------------------
smc_p3:
        nop
        nop
        nop                     ; [PATCH] present=nop3 / absent=jmp smc_s3
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
smc_a3:
        lxi     b,0FF8h         ; [PATCH] stride present / ret (last present)
        dad     b

; ---------------------------- plane П2 ----------------------------
smc_p2:
        nop
        nop
        nop                     ; [PATCH]
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
smc_a2:
        lxi     b,0FF8h         ; [PATCH]
        dad     b

; ---------------------------- plane П1 ----------------------------
smc_p1:
        nop
        nop
        nop                     ; [PATCH]
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
smc_a1:
        lxi     b,0FF8h         ; [PATCH]
        dad     b

; ---------------------------- plane П0 ----------------------------
smc_p0:
        nop
        nop
        nop                     ; [PATCH] present=nop3 / absent=jmp smc_s0(ret)
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
        ldax    d
        mov     m,a
        inx     d
        inx     h
smc_a0:
        ret                     ; П0 — физически последняя, всегда ret

; ------------------- skip-заглушки отсутствующих плоскостей ---------
; (HL += 0x2000 к базе следующей плоскости; DE не трогаем; jmp дальше)
smc_s3:
        lxi     b,2000h
        dad     b
        jmp     smc_p2
smc_s2:
        lxi     b,2000h
        dad     b
        jmp     smc_p1
smc_s1:
        lxi     b,2000h
        dad     b
        jmp     smc_p0
smc_s0:
        ret

; =====================================================================
;  void spr_patch8(unsigned int desc) — специализировать ядро под дескриптор
; =====================================================================
_spr_patch8:
        lxi     h,2
        dad     sp
        mov     a,m
        inx     h
        mov     h,m
        mov     l,a             ; HL = desc (arg1, sp+2)
        mov     b,m             ; B = FLAGS
        inx     h
        inx     h
        inx     h               ; HL = desc+3 = DATA base
        shld    smc_src+1       ; запечь immediate в "lxi d,imm" (L->+1, H->+2)

        ; --- вычислить маску ПОСЛЕДНЕЙ наличной плоскости -> C ---
        ;     порядок обхода П3(bit0)..П0(bit3); последняя = старший set-бит
        mvi     c,0
        mov     a,b
        ani     01h
        jz      lpc2
        mvi     c,01h
lpc2:
        mov     a,b
        ani     02h
        jz      lpc1
        mvi     c,02h
lpc1:
        mov     a,b
        ani     04h
        jz      lpc0
        mvi     c,04h
lpc0:
        mov     a,b
        ani     08h
        jz      lpdone
        mvi     c,08h
lpdone:

        ; --- П3 (mask 01h) ---
        mov     a,b
        ani     01h
        jz      p3abs
        lxi     h,smc_p3
        mvi     m,00h
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        lxi     h,smc_a3
        mov     a,c
        cpi     01h
        jz      p3last
        mvi     m,01h           ; lxi b,0FF8h
        inx     h
        mvi     m,0F8h
        inx     h
        mvi     m,0FFh
        inx     h
        mvi     m,09h           ; dad b
        jmp     p2start
p3last:
        mvi     m,0C9h          ; ret (ранний выход)
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        jmp     p2start
p3abs:
        lxi     h,smc_p3
        mvi     m,0C3h          ; jmp smc_s3
        lxi     d,smc_s3
        inx     h
        mov     m,e
        inx     h
        mov     m,d

        ; --- П2 (mask 02h) ---
p2start:
        mov     a,b
        ani     02h
        jz      p2abs
        lxi     h,smc_p2
        mvi     m,00h
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        lxi     h,smc_a2
        mov     a,c
        cpi     02h
        jz      p2last
        mvi     m,01h
        inx     h
        mvi     m,0F8h
        inx     h
        mvi     m,0FFh
        inx     h
        mvi     m,09h
        jmp     p1start
p2last:
        mvi     m,0C9h
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        jmp     p1start
p2abs:
        lxi     h,smc_p2
        mvi     m,0C3h          ; jmp smc_s2
        lxi     d,smc_s2
        inx     h
        mov     m,e
        inx     h
        mov     m,d

        ; --- П1 (mask 04h) ---
p1start:
        mov     a,b
        ani     04h
        jz      p1abs
        lxi     h,smc_p1
        mvi     m,00h
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        lxi     h,smc_a1
        mov     a,c
        cpi     04h
        jz      p1last
        mvi     m,01h
        inx     h
        mvi     m,0F8h
        inx     h
        mvi     m,0FFh
        inx     h
        mvi     m,09h
        jmp     p0start
p1last:
        mvi     m,0C9h
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        jmp     p0start
p1abs:
        lxi     h,smc_p1
        mvi     m,0C3h          ; jmp smc_s1
        lxi     d,smc_s1
        inx     h
        mov     m,e
        inx     h
        mov     m,d

        ; --- П0 (mask 08h): только слот; smc_a0 всегда ret ---
p0start:
        mov     a,b
        ani     08h
        jz      p0abs
        lxi     h,smc_p0
        mvi     m,00h
        inx     h
        mvi     m,00h
        inx     h
        mvi     m,00h
        ret
p0abs:
        lxi     h,smc_p0
        mvi     m,0C3h          ; jmp smc_s0 (= ret)
        lxi     d,smc_s0
        inx     h
        mov     m,e
        inx     h
        mov     m,d
        ret
