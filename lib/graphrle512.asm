;
; graphrle512.asm — RLE-распаковка для режима 512x256.
;
;   void graph_rle_expand_512(const unsigned char *src);
;
; Двухцветный режим 512x256 — расширенная плоскость:
;   plane 1 (A000h-BFFFh): бит 1, нечётные X
;   plane 0 (E000h-FFFFh): бит 0, чётные X
;
; RLE-поток содержит данные для обеих плоскостей:
;   первые 32 блока — плоскость 1 (A000h),
;   следующие 32 блока — плоскость 0 (E000h).
; HL инкрементируется на каждом блоке: A0→BF (плоскость 1),
; затем E0→FF (плоскость 0).
;
; Заголовок RLE: (64, высота), далее пары (count, byte), конец — 0.
;
; Только 8080-инструкции.
;

        SECTION code_clib
        PUBLIC  _graph_rle_expand_512

; ---------------------------------------------------------------
; Распаковка RLE: плоскость 1 (A000h) + плоскость 0 (E000h).
; 64 блока, HL инкрементируется от A0 до FF.
; Параметр src передаётся через стек (cdecl).
; ---------------------------------------------------------------
_graph_rle_expand_512:
        di
        ; --- адрес RLE из стека -> DE ---
        ld      hl, 2
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        ; --- заголовок: ширина в блоках (64), высота ---
        ld      a, (de)
        inc     de
        ld      (rle_cols_max), a
        ld      (rle_brem), a
        ld      a, (de)
        inc     de
        ld      (rle_rows), a
        or      a               ; 0 означает 256 строк
        ld      c, 0xFF         ; если 0 → C = 255 (dec c дойдёт до 0 за 256 шагов)
        jp      nz, rle_rows_ok
        ld      c, a            ; иначе C = rle_rows
rle_rows_ok:
        ; --- HL = верхняя строка первого блока ---
        ld      h, 0xA0         ; плоскость 1 → A000h, плоскость 0 → E000h
        ld      l, 0xFF

rle_loop:
        ld      a, (de)
        inc     de
        or      a
        jp      nz, rle_cont
        ei              ; прерывания включаем только перед возвратом
        ret
rle_cont:
        ld      b, a
        ld      a, (de)
        inc     de
        ld      (rle_val), a

rle_run:
        ld      a, (rle_val)
        ld      (hl), a
        dec     l
        dec     c
        jp      nz, rle_chk
        ; граница блока: inc h переводит на следующий блок
        ; плоскость 1: A0→A1→...→BF (32 блока)
        ; плоскость 0: E0→E1→...→FF (32 блока)
        ld      a, (rle_brem)
        dec     a
        jp      nz, rle_brem_ok
        ld      a, (rle_cols_max)
rle_brem_ok:
        ld      (rle_brem), a
        inc     h
        ld      a, h
        cp      0xC0            ; конец плоскости 1 (A000h)?
        jp      nz, rle_no_jump
        ld      h, 0xE0         ; прыжок на плоскость 0 (E000h)
rle_no_jump:
        ld      a, (rle_rows)
        or      a               ; 0 означает 256
        ld      c, 0xFF
        jp      nz, rle_reload_ok
        ld      c, a
rle_reload_ok:
        ld      l, 0xFF
rle_chk:
        dec     b
        jp      nz, rle_run
        jp      rle_loop

        ; --- рабочие переменные ---
rle_cols_max:   defb    0
rle_brem:       defb    0
rle_rows:       defb    0
rle_val:        defb    0
