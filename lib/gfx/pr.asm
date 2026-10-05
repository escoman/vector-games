;
; graphpr.asm — быстрый вывод текста шрифтом 8x8 (Вектор-06Ц).
;
; Заменяет C-функции gfx_put_char и gfx_print (graph.c).
;
;   void gfx_put_char(unsigned char x, unsigned char y, char ch,
;                       unsigned char color);
;   void gfx_print(unsigned char x, unsigned char y, const char *s,
;                    unsigned char color);
;
; Соглашение вызова z88dk classic — по выводу компилятора этих функций
; (zcc -S): аргументы лежат в стеке в 16-битных слотах, значение в
; младшем байте. gfx_put_char: color sp+2, ch sp+4, y sp+6, x sp+8;
; gfx_print: color sp+2, s sp+4 (слово), y sp+6, x sp+8. Стек чистит
; вызывающий, поэтому функции НЕ трогают SP (никаких push/pop) и
; просто делают ret.
;
; Ячейка 8x8: пиксели глифа — цвет color (0-15), фон ячейки
; затирается. x должно быть кратно 8, y — верхняя строка ячейки.
; Неизвестный символ шрифта с таблицей имён рисуется глифом 0.
;
; Шрифт подключается во время работы: gfx_select_font() меняет
; текущий дескриптор (см. gfx_font_t в v06.h), поэтому одним и тем
; же вызовом gfx_print можно напечатать разными шрифтами. До
; первого вызова работает шрифт, собранный в ROM (_gfx_font_8x8).
;
; Дескриптор с chars = 0 вместо таблицы имён задаёт прямой индекс по
; коду символа в диапазоне first_code..last_code; коды вне диапазона
; не рисуются совсем (клетка остаётся нетронутой).
;
; Видеопамять: блок символа = (x/8)*256 байт внутри каждой плоскости
; (0x8000 + n*0x2000); строка y блока — по адресу (256-y)&0xFF, строки
; вниз — уменьшение адреса.
;
; ОПТИМИЗАЦИИ:
;   1. LUT 256 байт (font_lut) — O(1) lookup вместо O(n) поиска.
;   2. Дескриптор читается один раз (build_lut), не на каждый символ.
;   3. Single-plane fast path для 256x256x2 (active_planes=0x01).
;
; Только 8080-инструкции: без jr/djnz и без префиксов CB/DD/ED/FD.
;

        SECTION code_clib

        PUBLIC  _gfx_put_char
        PUBLIC  _gfx_print
        PUBLIC  _gfx_select_font
        PUBLIC  _gfx_font_8x8

        EXTERN  _gfx_active_planes

; ---------------------------------------------------------------
; void gfx_put_char(unsigned char x, unsigned char y,
;                     char ch, unsigned char color)
;   __z88dk_callee
; ---------------------------------------------------------------

_gfx_put_char:

        pop     de
        pop     hl
        ld      a, l
        ld      (tmp_color), a
        pop     hl
        ld      a, l
        ld      (tmp_ch), a
        pop     hl
        ld      a, l
        ld      (tmp_y), a
        pop     hl
        ld      a, l
        ld      (tmp_x), a
        push    de

        ; Построить LUT при первом обращении
        ld      a, (lut_valid)
        or      a
        jp      nz, pc_lut_ok
        call    build_lut
pc_lut_ok:
        jp      draw_char


; ---------------------------------------------------------------
; draw_char — отрисовка одного символа.
;
; Вход: tmp_x, tmp_y, tmp_ch, tmp_color, font_lut, tmp_glyphs.
; LUT уже построен (lut_valid=1). tmp_glyphs содержит адрес данных.
; ---------------------------------------------------------------

draw_char:

        ; --- LUT lookup: O(1) ---
        ld      a, (tmp_ch)
        ld      e, a
        ld      d, 0
        ld      hl, font_lut          ; LXI (linker resolves 16-bit)
        add     hl, de                ; HL = &font_lut[char]
        ld      a, (hl)               ; A = glyph index или 0xFF
        cp      0FFh
        jp      z, dc_range_out

        ; --- Адрес глифа: tmp_glyphs + A*8 ---
        ld      e, a
        ld      h, 0
        ld      l, e
        add     hl, hl
        add     hl, hl
        add     hl, hl                ; HL = index × 8
        xchg                          ; DE = index×8
        ld      hl, (tmp_glyphs)      ; HL = base глифов (LHLD)
        add     hl, de                ; HL = адрес глифа
        ld      (tmp_glyph), hl       ; SHLD — сохранить

        ; --- VRAM: H = 80h+x, L = 255-y ---
        ld      a, (tmp_x)
        and     31
        add     a, 80h
        ld      h, a
        ld      a, (tmp_y)
        cpl
        ld      l, a

        ; --- C = color ---
        ld      a, (tmp_color)
        ld      c, a

        ; --- Single-plane check: active == 0x01 → E000 ---
        ld      a, (_gfx_active_planes)
        cpi     01h
        jp      nz, dc_multi

        ; E000: сдвиг H += 60h
        ld      a, h
        adi     60h
        ld      h, a

        ; Загрузить DE = адрес глифа (сохраняет HL=VRAM)
        ld      de, (tmp_glyph)

        ; Цветовой бит: C & 01
        ld      a, c
        and     01h
        jp      z, dc_clear_1p

        ; --- Запись 8 строк ---
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        ret

dc_clear_1p:
        xor     a
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        ret


; ---------------------------------------------------------------
; Multi-plane loop: для режимов 4 плоскостей или 0x05.
; ---------------------------------------------------------------

dc_multi:

        ld      b, 08h

dc_plane:

        ; Пропуск неактивных плоскостей
        ld      a, (_gfx_active_planes)
        and     b
        jp      z, dc_skip

        ; Загрузить DE = глиф (XCHG+LHLD+XCHG — сохраняет HL)
        ld      de, (tmp_glyph)

        ; Цветовой бит
        ld      a, c
        and     b
        jp      z, dc_clear

        ; --- Запись 8 строк ---
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        inc     de
        dec     hl
        ld      a, (de)
        ld      (hl), a
        dec     hl

        jp      dc_plane_next


dc_clear:

        xor     a
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl
        ld      (hl), a
        dec     hl


dc_plane_next:

        ; +2008h (компенсация -8 от записей + переход к следующей пл.)
        ld      a, l
        adi     08h
        ld      l, a
        ld      a, h
        aci     20h
        ld      h, a

        jp      dc_mask_next


dc_skip:

        ; Плоскость неактивна: +2000h
        ld      a, h
        adi     20h
        ld      h, a


dc_mask_next:

        ; Следующая маска: 08→04→02→01→80(выход)
        ld      a, b
        rrca
        ld      b, a
        cp      80h
        jp      nz, dc_plane
        ret


dc_range_out:
        ret


; ---------------------------------------------------------------
; void gfx_print(unsigned char x, unsigned char y,
;                  const char *s, unsigned char color)
;   __z88dk_callee
; ---------------------------------------------------------------

_gfx_print:

        pop     de
        pop     hl
        ld      a, l
        ld      (tmp_color), a
        pop     hl
        ld      (tmp_s), hl
        pop     hl
        ld      a, l
        ld      (tmp_y), a
        pop     hl
        ld      a, l
        ld      (tmp_x), a
        push    de

        ; LUT: построить при первом обращении
        ld      a, (lut_valid)
        or      a
        jp      nz, pr_lut_ok
        call    build_lut
pr_lut_ok:

        ; DE = строка (LHLD+XCHG: сохраняет HL)
        ld      hl, (tmp_s)
        xchg


dp_loop:

        ld      a, (de)
        or      a
        jp      z, dp_done
        inc     de
        push    de
        ld      (tmp_ch), a
        call    draw_char
        pop     de
        ld      a, (tmp_x)
        inc     a
        ld      (tmp_x), a
        jp      dp_loop

dp_done:
        ret


; ---------------------------------------------------------------
; void gfx_select_font(const gfx_font_t *font)
;   __z88dk_callee
; ---------------------------------------------------------------

_gfx_select_font:

        pop     de
        pop     hl

        ld      a, h
        or      l
        jp      nz, sel_user

        ld      hl, _gfx_font_8x8

sel_user:
        ld      (tmp_font), hl

        ; Сбросить LUT — будет перестроен при ближайшей печати
        xor     a
        ld      (lut_valid), a

        push    de
        ret


; ---------------------------------------------------------------
; build_lut — построить font_lut из дескриптора tmp_font.
; Сохраняет tmp_glyphs. Устанавливает lut_valid=1.
; Вызывается один раз на шрифт.
; ---------------------------------------------------------------

build_lut:

        ; Прочитать дескриптор gfx_font_t из tmp_font:
        ;   +0,+1 = chars (таблица имён или 0 для прямого индекса)
        ;   +2,+3 = glyphs
        ;   +4,+5 = first_code (младший байт значим)
        ;   +6,+7 = last_code (младший байт значим)

        ld      hl, (tmp_font)        ; HL = адрес дескриптора

        ; glyphs (+2,+3) → tmp_glyphs (HL)
        ld      a, l
        adi     2
        ld      l, a
        ld      a, h
        aci     0
        ld      h, a                  ; HL = desc + 2
        ld      a, (hl)               ; A = glyph low
        inc     hl
        ld      h, (hl)               ; H = glyph high
        ld      l, a                  ; HL = glyph address
        ld      (tmp_glyphs), hl      ; SHLD: save

        ; chars (+0,+1): читаем из дескриптора
        ld      hl, (tmp_font)
        ld      a, (hl)               ; chars low
        inc     hl
        ld      h, (hl)               ; H = chars high
        ld      l, a                  ; HL = chars word
        ld      (tmp_chars), hl       ; SHLD: store chars ptr

        ; Проверка: chars == 0? → прямой индекс
        ld      a, h
        or      l
        jp      nz, bl_table

        ; ---- ПРЯМОЙ ИНДЕКС (chars = 0) ----

        ; first_code at descriptor+4
        ld      hl, (tmp_font)
        ld      a, l
        adi     4
        ld      l, a
        ld      a, h
        aci     0
        ld      h, a                  ; HL = desc + 4
        ld      a, (hl)               ; A = first_code
        ld      (bl_first), a
        inc     hl
        inc     hl                    ; HL = desc + 6
        ld      a, (hl)               ; A = last_code
        ld      (bl_last), a

        ; Очистить LUT → 0xFF
        ld      hl, font_lut
        ld      b, 0
bl_clrff:
        ld      (hl), 0FFh            ; MVI M, FF
        inc     hl
        inc     b                     ; INR B → sets Z on 256-wrap
        jp      nz, bl_clrff

        ; Заполнить: font_lut[first+i] = i, для i=0..(last-first)
        ld      a, (bl_first)
        ld      e, a
        ld      d, 0
        ld      hl, font_lut
        add     hl, de                ; HL = &font_lut[first]
        ld      a, (bl_last)
        sub     e                     ; A = last - first
        ld      c, a                  ; C = count-1
        ld      b, 0                  ; B = index

bl_dfill:
        ld      a, b
        ld      (hl), a               ; lut[code] = index
        inc     hl
        inc     b
        dec     c
        jp      nz, bl_dfill

        ; Последний элемент (last_code включительно)
        ld      a, b
        ld      (hl), a

        jp      bl_finish


        ; ---- ТАБЛИЦА ИМЁН (chars != 0) ----

bl_table:

        ; Очистить LUT → 0
        ld      hl, font_lut
        ld      b, 0
bl_clr0:
        ld      (hl), 0               ; MVI M, 00
        inc     hl
        inc     b
        jp      nz, bl_clr0

        ; Сканировать таблицу имён
        ; DE = указатель на таблицу (tmp_chars)
        ld      de, (tmp_chars)
        ; C = 0 (индекс)
        ld      c, 0

bl_fill:
        ld      a, (de)               ; char code (LDAX D)
        or      a                     ; null?
        jp      z, bl_finish          ; конец таблицы

        push    de                    ; сохранить указатель таблицы
        ld      e, a                  ; DE = char offset
        ld      d, 0
        ld      hl, font_lut
        add     hl, de                ; HL = &font_lut[char]
        ld      a, c                  ; A = current index
        ld      (hl), a               ; font_lut[char] = index
        pop     de                    ; восстановить указатель

        inc     de                    ; next entry
        inc     c                     ; next index
        jp      bl_fill


bl_finish:
        ld      a, 1
        ld      (lut_valid), a
        ret


; ---------------------------------------------------------------
; Временные переменные.
; ---------------------------------------------------------------

tmp_x:
        defb    0
tmp_y:
        defb    0
tmp_ch:
        defb    0
tmp_color:
        defb    0
tmp_glyph:
        defw    0
tmp_s:
        defw    0
tmp_font:
        defw    _gfx_font_8x8
tmp_chars:
        defw    0
tmp_glyphs:
        defw    0
lut_valid:
        defb    0
bl_first:
        defb    0
bl_last:
        defb    0

; ---------------------------------------------------------------
; font_lut: 256 байт LUT (char → glyph index или 0xFF).
; Выравнивание не требуется — доступ через 16-битный LXI + DAD.
; ---------------------------------------------------------------

font_lut:
        defs    256

; ---------------------------------------------------------------
; Шрифт 8x8 по умолчанию.
; ---------------------------------------------------------------

        ifdef   FONT_EXTERNAL
        EXTERN  font_chars
        EXTERN  font8x8
        else
        INCLUDE "fonts/default_8x8.inc"
        endif

; ---------------------------------------------------------------
; Дескриптор gfx_font_t:
;   word 0: адрес таблицы имён
;   word 1: адрес данных глифов
;   word 2: first_code (для прямого индекса)
;   word 3: last_code
; ---------------------------------------------------------------

_gfx_font_8x8:
        defw    font_chars
        defw    font8x8
        defw    0
        defw    0
