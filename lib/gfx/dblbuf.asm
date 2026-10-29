;
; dblbuf.asm — модуль двойной буферизации для Вектора-06Ц.
;
; Двойная буферизация (Double Buffer) — техника устранения tearing и обеспечения
; плавной покадровой анимации. Экран 256×256×16 разбит на две пары битовых
; плоскостей:
;
;   Буфер A = плоскости веса 1 (0xE000) и веса 2 (0xC000) → биты 0–1 палитры.
;   Буфер B = плоскости веса 4 (0xA000) и веса 8 (0x8000) → биты 2–3 палитры.
;
; Каждый буфер несёт 4 логических цвета. Маскировка палитрой (16 слотов):
;   Видим A: pal[i] = c4[i & 3]        — биты 2–3 игнорируются, B не видно.
;   Видим B: pal[i] = c4[(i >> 2) & 3] — биты 0–1 игнорируются, A не видно.
;
; Смена палитры = смена активного буфера, синхронизирована с VSync.
;
; Основан на технологии из демки roms/demos/mario-dbl.
;
; Только 8080-инструкции: без LDIR/LDDR/JR/DJNZ и префиксов CB/DD/ED/FD.
;

        SECTION code_clib
        PUBLIC  _gfx_dblbuf_init
        PUBLIC  _gfx_dblbuf_present
        PUBLIC  _gfx_dblbuf_show
        PUBLIC  _gfx_dblbuf_set_planes
        PUBLIC  _gfx_dblbuf_copy_ab
        PUBLIC  _gfx_dblbuf_copy_ba
        PUBLIC  _gfx_dblbuf_isr
        PUBLIC  _gfx_dblbuf_front
        PUBLIC  _gfx_dblbuf_back
        PUBLIC  _gfx_dblbuf_front_pal
        PUBLIC  _gfx_dblbuf_back_pal
        PUBLIC  _gfx_dblbuf_invalidate
        PUBLIC  _gfx_dblbuf_set_front

        EXTERN  _v06_set_palette_asm
        EXTERN  _v06_set_palette_isr
        EXTERN  _gfx_active_planes

; ---------------------------------------------------------------
; void gfx_dblbuf_init(const unsigned char *c4) __z88dk_callee;
;
; Инициализировать палитры-маски double buffer по 4-цветной палитре c4[4].
; Строит 16-слотовые маски:
;   db_pal_a[i] = c4[i & 3]        (показывает буфер A, скрывает B)
;   db_pal_b[i] = c4[(i >> 2) & 3] (показывает буфер B, скрывает A)
;
; Вызывается ОДИН раз при старте, до первого gfx_dblbuf_present().
; После вызова db_active = 1, db_front = 0, db_pal_dirty = 0.
; НЕ загружает палитру в железо — это делает show/present.
;
; Вход (callee): стек содержит [c4_lo, c4_hi, return_address].
; ---------------------------------------------------------------
_gfx_dblbuf_init:
        pop     de              ; DE = return address
        pop     hl              ; HL = c4 (указатель на 4 байта)
        push    de              ; вернуть return address

        ; Сохраняем c4[0..3] в _db_c4_tmp (4 байта в BSS).
        lxi     d, _db_c4_tmp
        mvi     b, 4
init_copy_c4:
        mov     a, m
        stax    d
        inx     h
        inx     d
        dcr     b
        jnz     init_copy_c4

        ; Строим pal_a[16] и pal_b[16] циклом i=0..15.
        ; Используем C как счётчик (16..1), B как временный регистр.
        mvi     c, 16
init_build_loop:
        ; Вычисляем индекс для pal_a: idx_a = i & 3 = (16 - C) & 3.
        mov     a, c
        cma
        adi     17              ; A = 16 - C = i (0..15)
        mov     b, a            ; B = i
        ani     03h             ; A = i & 3
        mov     e, a            ; E = idx_a
        ; Загружаем c4[idx_a].
        lxi     h, _db_c4_tmp
        mvi     d, 0            ; DE = idx_a (E уже содержит idx_a)
        dad     d               ; HL = c4 + idx_a
        mov     a, m            ; A = c4[idx_a]
        ; Записываем в pal_a[i].
        lxi     h, _db_pal_a
        mov     e, b            ; E = i
        mvi     d, 0            ; DE = i
        dad     d               ; HL = pal_a + i
        mov     m, a            ; pal_a[i] = A

        ; Вычисляем индекс для pal_b: idx_b = (i >> 2) & 3.
        mov     a, b            ; A = i
        ani     0Ch             ; A = i & 0x0C (биты 2 и 3)
        rrc
        rrc                     ; A = (i & 0x0C) >> 2 (логический сдвиг через маску)
        ; Результат: (i >> 2) & 3
        mov     e, a            ; E = idx_b
        ; Загружаем c4[idx_b].
        lxi     h, _db_c4_tmp
        mvi     d, 0            ; DE = idx_b (E уже содержит idx_b)
        dad     d               ; HL = c4 + idx_b
        mov     a, m            ; A = c4[idx_b]
        ; Записываем в pal_b[i].
        lxi     h, _db_pal_b
        mov     e, b            ; E = i
        mvi     d, 0            ; DE = i
        dad     d               ; HL = pal_b + i
        mov     m, a            ; pal_b[i] = A

        dcr     c
        jnz     init_build_loop

        ; Инициализация состояния.
        xra     a
        sta     _db_front       ; front = 0 (виден A)
        sta     _db_pal_dirty   ; pal_dirty = 0
        mvi     a, 1
        sta     _db_active      ; active = 1
        ; show_pal = &db_pal_a (по умолчанию).
        lxi     h, _db_pal_a
        shld    _db_show_pal

        ret

; ---------------------------------------------------------------
; unsigned char gfx_dblbuf_present(void);
;
; Показать наполненный буфер: переключить палитру-маску (VSync-синхронно).
; Алгоритм:
;   1. front ^= 1  (текущий back становится front)
;   2. show_pal = (front == 0) ? db_pal_a : db_pal_b
;   3. pal_dirty = 1  (ISR загрузит палитру на ближайшем VBlank)
;   4. gfx_active_planes = 0x0F  (все 4 плоскости видимы)
;
; Возвращает новый front (0 = A, 1 = B) в регистре A.
; ---------------------------------------------------------------
_gfx_dblbuf_present:
        ; Инвертируем front.
        lda     _db_front
        xri     01h
        sta     _db_front       ; front ^= 1

        ; Выбираем палитру по front.
        ora     a               ; проверить A == 0
        jz      present_a
        lxi     h, _db_pal_b
        jp      present_set
present_a:
        lxi     h, _db_pal_a
present_set:
        shld    _db_show_pal    ; show_pal = &pal_a или &pal_b

        ; pal_dirty = 1.
        mvi     a, 1
        sta     _db_pal_dirty

        ; gfx_active_planes = 0x0F (все 4 плоскости видимы).
        mvi     a, 0x0F
        sta     _gfx_active_planes

        ; Возвращаем front в A (и L для sccz80: char-функция).
        lda     _db_front
        mov     l, a
        ret

; ---------------------------------------------------------------
; void gfx_dblbuf_show(void);
;
; Загрузить палитру показа НЕМЕДЛЕННО (без ожидания VBlank через ISR).
; Используется для стартового кадра, fade-in и других ситуаций.
;
; Алгоритм:
;   1. show_pal = (front == 0) ? db_pal_a : db_pal_b
;   2. Вызывает v06_set_palette_asm(show_pal) (ei/halt + запись 16 слотов).
;   3. gfx_active_planes = 0x0F
;   4. pal_dirty = 0 (палитра уже загружена).
;
; ВАЖНО: функция делает ei/halt внутри v06_set_palette_asm, поэтому НЕ
; вызывается из ISR.
; ---------------------------------------------------------------
_gfx_dblbuf_show:
        ; Выбираем палитру по front.
        lda     _db_front
        ora     a
        jz      show_a
        lxi     h, _db_pal_b
        jp      show_call
show_a:
        lxi     h, _db_pal_a
show_call:
        shld    _db_show_pal

        ; Вызываем v06_set_palette_asm(show_pal).
        ; Передаём HL как аргумент (cdecl: push hl; call).
        push    h
        call    _v06_set_palette_asm
        pop     h               ; очистить стек от аргумента

        ; gfx_active_planes = 0x0F.
        mvi     a, 0x0F
        sta     _gfx_active_planes

        ; pal_dirty = 0.
        xra     a
        sta     _db_pal_dirty

        ret

; ---------------------------------------------------------------
; unsigned char gfx_dblbuf_set_planes(unsigned char mask) __z88dk_callee;
;
; Установить маску плоскостей, в которые разрешён вывод.
; mask = 0x03 → только A, 0x0C → только B, 0x0F → все.
;
; Возвращает предыдущее значение маски в A.
; Вход (callee): L = mask.
; ---------------------------------------------------------------
_gfx_dblbuf_set_planes:
        pop     de              ; DE = return address
        pop     hl              ; HL = mask (младший байт L)
        push    de              ; вернуть return address

        ; Сохраняем старое значение.
        lda     _gfx_active_planes
        mov     b, a            ; B = старая маска

        ; Устанавливаем новую.
        mov     a, l
        sta     _gfx_active_planes

        ; Возвращаем старое в A (и L для sccz80: char-функция).
        mov     a, b
        mov     l, a
        ret

; ---------------------------------------------------------------
; void gfx_dblbuf_copy_ab(void);
;
; Скопировать буфер A в буфер B (16 КБ: 2 плоскости × 8 КБ).
;   E000 → A000  (плоскость веса 1)
;   C000 → 8000  (плоскость веса 2)
;
; Реализация — ручной цикл 8080: MOV A,M / STAX D / INX H / INX D.
; ~0.3 с на 16 КБ — приемлемо для стартовой инициализации.
; ---------------------------------------------------------------
_gfx_dblbuf_copy_ab:
        ; Плоскость веса 1: E000 → A000.
        lxi     h, 0E000h
        lxi     d, 0A000h
        mvi     b, 020h         ; 32 блока по 256 байт
        call    copy_block

        ; Плоскость веса 2: C000 → 8000.
        lxi     h, 0C000h
        lxi     d, 08000h
        mvi     b, 020h
        call    copy_block
        ret

; ---------------------------------------------------------------
; void gfx_dblbuf_copy_ba(void);
;
; Скопировать буфер B в буфер A (зеркальная операция).
;   A000 → E000  (плоскость веса 1)
;   8000 → C000  (плоскость веса 2)
; ---------------------------------------------------------------
_gfx_dblbuf_copy_ba:
        ; Плоскость веса 1: A000 → E000.
        lxi     h, 0A000h
        lxi     d, 0E000h
        mvi     b, 020h
        call    copy_block

        ; Плоскость веса 2: 8000 → C000.
        lxi     h, 08000h
        lxi     d, 0C000h
        mvi     b, 020h
        call    copy_block
        ret

; copy_block: копировать B*256 байт (HL) → (DE).
; C — внутренний счётчик (256).
copy_block:
        mvi     c, 0
copy_inner:
        mov     a, m
        stax    d
        inx     d
        inx     h
        dcr     c
        jnz     copy_inner
        dcr     b
        jnz     copy_block
        ret

; ---------------------------------------------------------------
; void gfx_dblbuf_isr(void);
;
; Обработчик палитры для кадрового ISR. Вызывается ПЕРВЫМ в пользовательском
; frame_handler, до любой другой работы (звук, логика).
;
; Алгоритм:
;   if (db_pal_dirty) {
;       v06_set_palette_isr(db_show_pal);   // без ei/halt, мы уже в ПР
;       db_pal_dirty = 0;
;   }
;
; Функция легковесная: ~15 тактов в холостом ходу (pal_dirty=0),
; ~200 тактов при dirty (16 записей в порт 0x0C).
; ---------------------------------------------------------------
_gfx_dblbuf_isr:
        lda     _db_pal_dirty
        ora     a
        rz                      ; return if Z (dirty == 0)

        ; Медленный путь: загрузить палитру через v06_set_palette_isr.
        lhld    _db_show_pal
        push    h               ; аргумент для v06_set_palette_isr (cdecl)
        call    _v06_set_palette_isr
        pop     h               ; очистить стек от аргумента

        xra     a
        sta     _db_pal_dirty   ; ack: dirty = 0
        ret

; ---------------------------------------------------------------
; unsigned char gfx_dblbuf_front(void);
;
; Вернуть индекс текущего front-буфера (0 = A, 1 = B).
; Возврат: A = _db_front (и L — sccz80 читает char из L).
; ---------------------------------------------------------------
_gfx_dblbuf_front:
        lda     _db_front
        mov     l, a
        ret

; ---------------------------------------------------------------
; unsigned char gfx_dblbuf_back(void);
;
; Вернуть индекс back-буфера (противоположного front).
; back = front ^ 1. Рисовать нужно именно в back.
; Возврат: A = _db_front ^ 1 (и L — sccz80 читает char из L).
; ---------------------------------------------------------------
_gfx_dblbuf_back:
        lda     _db_front
        xri     01h
        mov     l, a
        ret

; ---------------------------------------------------------------
; const unsigned char *gfx_dblbuf_front_pal(void);
;
; Получить указатель на палитру-маску front-буфера.
; Возвращает HL = _db_pal_a (если front=0) или _db_pal_b (если front=1).
; Полезно для gfx_fade_in/out — фейдить нужно палитру видимого буфера.
; ---------------------------------------------------------------
_gfx_dblbuf_front_pal:
        lda     _db_front
        ora     a
        jz      fp_a
        lxi     h, _db_pal_b
        ret
fp_a:
        lxi     h, _db_pal_a
        ret

; ---------------------------------------------------------------
; const unsigned char *gfx_dblbuf_back_pal(void);
;
; Получить указатель на палитру-маску back-буфера.
; Возвращает HL = противоположный front-указатель.
; ---------------------------------------------------------------
_gfx_dblbuf_back_pal:
        lda     _db_front
        ora     a
        jnz     bp_a
        lxi     h, _db_pal_b
        ret
bp_a:
        lxi     h, _db_pal_a
        ret

; ---------------------------------------------------------------
; void gfx_dblbuf_invalidate(void);
;
; Принудительно запросить смену палитры на ближайшем VBlank (без свопа front).
; Полезно, если палитра была изменена извне (например, после fade) и нужно
; перечитать её в ISR. Устанавливает db_pal_dirty = 1.
; ---------------------------------------------------------------
_gfx_dblbuf_invalidate:
        mvi     a, 1
        sta     _db_pal_dirty
        ret

; ---------------------------------------------------------------
; void gfx_dblbuf_set_front(unsigned char front) __z88dk_callee;
;
; Установить индекс front-буфера вручную (0 = A, 1 = B).
; Полезно для инициализации, когда нужно начать с определённого буфера
; (например, перед gfx_fade_in, чтобы показать конкретный буфер).
; НЕ загружает палитру и НЕ меняет pal_dirty — только устанавливает front.
;
; Вход (callee): L = front (0 или 1).
; ---------------------------------------------------------------
_gfx_dblbuf_set_front:
        pop     de              ; DE = return address
        pop     hl              ; HL = front (младший байт L)
        push    de              ; вернуть return address

        mov     a, l
        sta     _db_front       ; db_front = front
        ret

; ---------------------------------------------------------------
; Рабочие переменные (BSS).
; ---------------------------------------------------------------
        SECTION bss_clib

_db_c4_tmp:     defs    4       ; временное хранение c4[4] при инициализации
_db_pal_a:      defs    16      ; палитра-маска буфера A
_db_pal_b:      defs    16      ; палитра-маска буфера B
_db_front:      defb    0       ; 0 = виден A, 1 = виден B
_db_pal_dirty:  defb    0       ; 1 = ISR должен перезагрузить палитру
_db_active:     defb    0       ; 1 = модуль инициализирован
_db_show_pal:   defw    0       ; адрес _db_pal_a или _db_pal_b
