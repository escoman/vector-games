;
; graphlz.asm — распаковка LZ-сжатых тайлов в видеопамять Вектора-06Ц.
;
;   void graph_lz_expand(const unsigned char *src);
;
; Формат данных (готовит utils/bmp2inc_lz.py):
;   Заголовок: 4 байта — w8, h (0=256), n_tiles (16 бит LE).
;   Словарь тайлов: n_tiles * 8 байт.
;   4 LZ-потока (по одному на плоскость в порядке весов 8,4,2,1).
;
; LZ-формат (на тайлах):
;   flag_byte: 8 бит, каждый = literal(1) или reference(0).
;   literal: 2 байта (индекс тайла 0-511).
;   reference: 2 байта (offset 12 бит, length 4 бита).
;
; Только 8080-инструкции.
;

DICT_BASE       EQU     0x2000

        SECTION code_clib
        PUBLIC  _graph_lz_expand

_graph_lz_expand:
        di
        ; --- src (sp+2) -> DE ---
        ld      hl, 2
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        ; --- заголовок: w8, h, n_tiles ---
        ld      a, (de)
        inc     de
        ld      (lz_w8), a
        ld      a, (de)
        inc     de
        or      a
        jp      nz, lz_h_nz
        ld      a, 32                   ; h=256 → h/8=32
        jp      lz_h_set
lz_h_nz:
        rrca                            ; h/8
        rrca
        rrca
        and     0x1F
lz_h_set:
        ld      (lz_h_div8), a
        ld      a, (de)
        inc     de
        ld      (lz_n_tiles), a
        ld      a, (de)
        inc     de
        ld      (lz_n_tiles+1), a
        ; --- копирование словаря в RAM ---
        ld      hl, DICT_BASE
        ld      (lz_dict_base), hl
        ld      a, (lz_n_tiles)
        ld      l, a
        ld      a, (lz_n_tiles+1)
        ld      h, a
        add     hl, hl                  ; *8
        add     hl, hl
        add     hl, hl
        ld      b, h
        ld      c, l                    ; BC = байт словаря
        ld      hl, DICT_BASE
lz_cd_lp:
        ld      a, (de)
        inc     de
        ld      (hl), a
        inc     hl
        dec     bc
        ld      a, b
        or      c
        jp      nz, lz_cd_lp
        ; --- инициализация ---
        ld      (lz_src), de
        xor     a
        ld      (lz_plane), a
        ; --- цикл плоскостей ---
lz_pl_lp:
        ld      a, (lz_plane)
        cp      4
        jp      z, lz_done
        ; tpp = w8 * h_div8
        ld      a, (lz_h_div8)
        ld      b, a
        ld      a, (lz_w8)
        call    mul_ab                  ; HL = tpp
        ld      (lz_tpp), hl
        xor     a
        ld      (lz_cur), a
        ld      (lz_cur+1), a
        ld      (lz_nbits), a
        ; --- цикл тайлов ---
lz_t_lp:
        ; сравниваем lz_cur (16 бит) с lz_tpp (16 бит)
        ; продолжаем пока cur < tpp
        ld      a, (lz_tpp+1)
        ld      b, a
        ld      a, (lz_cur+1)
        cp      b                       ; cur_hi - tpp_hi
        jp      nz, lz_cmp_done         ; не равны → результат готов
        ld      a, (lz_tpp)
        ld      b, a
        ld      a, (lz_cur)
        cp      b                       ; cur_lo - tpp_lo
lz_cmp_done:
        jp      c, lz_cont              ; carry = cur < tpp → продолжаем
        ; плоскость кончена
        ld      a, (lz_plane)
        inc     a
        ld      (lz_plane), a
        jp      lz_pl_lp
lz_cont:
        ; нужен новый flag_byte?
        ld      a, (lz_nbits)
        or      a
        jp      nz, lz_have_fl
        ld      hl, (lz_src)
        ld      a, (hl)
        inc     hl
        ld      (lz_src), hl
        ld      (lz_flag), a
        ld      a, 8
lz_have_fl:
        ld      (lz_nbits), a
        ; младший бит flag → literal/reference
        ld      a, (lz_flag)
        and     1
        jp      nz, lz_literal
        jp      lz_reference
lz_literal:
        ; 2 байта: индекс тайла
        ld      hl, (lz_src)
        ld      a, (hl)
        inc     hl
        and     1
        ld      (lz_idx_hi), a
        ld      a, (hl)
        inc     hl
        ld      (lz_src), hl
        ld      (lz_idx_lo), a
        call    copy_dict_tile
        jp      lz_next
lz_reference:
        ; 2 байта: offset + length
        ld      hl, (lz_src)
        ld      a, (hl)
        inc     hl
        ld      (lz_ref0), a
        ld      a, (hl)
        inc     hl
        ld      (lz_src), hl
        ld      (lz_ref1), a
        ; offset = ((ref0 & 0x0F) << 8) | ref1
        ld      a, (lz_ref0)
        and     0x0F
        ld      d, a
        ld      a, (lz_ref1)
        ld      e, a                    ; DE = offset
        push    de
        ; length = (ref0 >> 4) + 3
        ld      a, (lz_ref0)
        rrca
        rrca
        rrca
        rrca
        and     0x0F
        add     a, 3
        ld      (lz_len), a
        call    copy_backref
        pop     de
lz_next:
        ; cur++, flag>>=1, nbits--
        ld      hl, (lz_cur)
        inc     hl
        ld      (lz_cur), hl
        ld      a, (lz_flag)
        rrca
        ld      (lz_flag), a
        ld      a, (lz_nbits)
        dec     a
        ld      (lz_nbits), a
        jp      lz_t_lp
lz_done:
        ei
        ret

; ---------------------------------------------------------------
; Копирование тайла из словаря в VRAM (индекс в lz_idx_hi/lo).
; ---------------------------------------------------------------
copy_dict_tile:
        push    de
        push    hl
        ; HL = idx * 8
        ld      a, (lz_idx_lo)
        ld      l, a
        ld      a, (lz_idx_hi)
        ld      h, a
        add     hl, hl
        add     hl, hl
        add     hl, hl
        ld      de, (lz_dict_base)
        add     hl, de                  ; HL = словарь
        push    hl
        call    cur_vram                ; DE = VRAM (D=старший байт, E=младший)
        pop     hl                      ; HL = словарь
        ld      b, 8
lz_ct_lp:
        ld      a, (hl)
        inc     hl
        ld      (de), a
        dec     e                       ; VRAM адрес уменьшается (строки сверху вниз)
        dec     b
        jp      nz, lz_ct_lp
        pop     hl
        pop     de
        ret

; ---------------------------------------------------------------
; Копирование back-reference (DE = offset, lz_len = length).
; ---------------------------------------------------------------
copy_backref:
        push    de
        push    hl
        push    bc
        ld      a, (lz_len)
        ld      b, a
lz_cb_lp:
        push    bc
        push    de                      ; сохраняем offset
        ; source = cur - offset
        ld      a, (lz_cur)
        ld      l, a
        ld      a, (lz_cur+1)
        ld      h, a
        pop     de                      ; DE = offset
        push    de
        ld      a, l
        sub     e
        ld      l, a
        ld      a, h
        sbc     a, d
        ld      h, a
        call    tile_vram               ; DE = source VRAM
        push    de
        call    cur_vram                ; DE = dest VRAM
        pop     hl                      ; HL = source
        ld      b, 8
lz_cb_copy:
        ld      a, (hl)
        inc     hl
        ld      (de), a
        dec     e                       ; VRAM адрес уменьшается
        dec     b
        jp      nz, lz_cb_copy
        ; Для следующего тайла reference нужен cur+1, поэтому
        ; увеличиваем lz_cur между итерациями, но не после последней.
        pop     de                      ; offset
        pop     bc
        dec     b
        jp      z, lz_cb_done
        ld      hl, (lz_cur)
        inc     hl
        ld      (lz_cur), hl
        jp      lz_cb_lp
lz_cb_done:
        pop     bc
        pop     hl
        pop     de
        ret

; ---------------------------------------------------------------
; VRAM адрес для lz_cur → DE.
; ---------------------------------------------------------------
cur_vram:
        ld      a, (lz_cur)
        ld      l, a
        ld      a, (lz_cur+1)
        ld      h, a
        ; fall through

; ---------------------------------------------------------------
; VRAM адрес для тайла HL → DE.
; ---------------------------------------------------------------
tile_vram:
        push    bc
        ; row = HL / w8, col = HL % w8
        ; H*8 добавляем к row (каждый H=1 = 256 тайлов = 8 рядов)
        ld      a, h
        add     a, a                    ; H * 2
        add     a, a                    ; H * 4
        add     a, a                    ; H * 8
        ld      c, a                    ; C = row (начальное = H * 8)

        ; Делим L на w8 вычитанием
        ld      a, l
lz_div:
        ld      b, a                    ; B = текущее значение
        ld      a, (lz_w8)
        cp      b                       ; w8 - B
        jp      z, lz_div_exact         ; B == w8 → col=0, row++
        jp      c, lz_div_sub           ; B > w8 → вычитаем
        ; B < w8 → готово, col = B
        ld      a, b                    ; A = col
        jp      lz_div_ok
lz_div_exact:
        xor     a                       ; A = 0 = col
        inc     c                       ; row++
        jp      lz_div_ok
lz_div_sub:
        ; A = w8 (из ld a, (lz_w8)), B = текущее значение
        ld      e, b                    ; E = B
        ld      d, a                    ; D = w8
        ld      a, e                    ; A = B
        sub     d                       ; A = B - w8
        inc     c                       ; row++
        jp      lz_div
lz_div_ok:
        ; A = col, C = row
        ld      b, a                    ; B = col (сохраняем для VRAM)
        
        ; VRAM адрес: (0x80 + plane*0x20 + col) * 256 + (255 - row*8)
        ld      a, (lz_plane)
        add     a, a                    ; plane * 2
        add     a, a                    ; plane * 4
        add     a, a                    ; plane * 8
        add     a, a                    ; plane * 16
        add     a, a                    ; plane * 32 = plane * 0x20
        add     a, b                    ; + col
        add     a, 0x80                 ; + base
        ld      d, a                    ; D = 0x80 + plane*0x20 + col
        
        ld      a, c                    ; A = row
        add     a, a                    ; row * 2
        add     a, a                    ; row * 4
        add     a, a                    ; row * 8
        cpl                             ; 255 - row * 8
        ld      e, a                    ; E = 255 - row * 8
        
        pop     bc
        ret

; ---------------------------------------------------------------
; Умножение A * B → HL.
; ---------------------------------------------------------------
mul_ab:
        ld      hl, 0
        or      a
        ret     z
        ld      e, a                    ; E = первый множитель
        ld      a, b
        or      a
        ret     z
        ld      b, a                    ; B = счётчик
lz_mul_lp:
        push    bc
        ld      b, 0
        ld      c, e                    ; BC = E (множитель)
        add     hl, bc
        pop     bc
        dec     b
        jp      nz, lz_mul_lp
        ret

        ; --- рабочие переменные ---
lz_w8:          defb    0
lz_h_div8:      defb    0
lz_n_tiles:     defw    0
lz_dict_base:   defw    0
lz_src:         defw    0
lz_cur:         defw    0
lz_tpp:         defw    0
lz_plane:       defb    0
lz_flag:        defb    0
lz_nbits:       defb    0
lz_idx_hi:      defb    0
lz_idx_lo:      defb    0
lz_ref0:        defb    0
lz_ref1:        defb    0
lz_len:         defb    0
