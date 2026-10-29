;
; spr_stub.asm — STUB-ядро вывода спрайтов (SPR_FORMAT): пара stub / stub_mask.
;
; Технология: стаб класса — ЛИНЕЙНЫЙ код, развёрнутый при сборке. Маска
; плоскостей (FLAGS) и число столбцов у класса спрайтов постоянны, поэтому
; вся раскладка «плоскость -> столбцы -> плоскость» эмитится навылет:
; отсутствующие плоскости не попадают в код вовсе, в кадре нет ни загрузки
; флагов, ни ветвлений, ни счётчиков. Развёрнутые столбцы (REPT STUB_COLS-1)
; убирают и пару DCR B / JNZ — 15 тактов на столбец.
;
; Пара:
;   stub_tab      / stub_1_0      — draw_sprite_stub      (плоская запись);
;   stub_mask_tab / stub_mask_1_0 — draw_sprite_stub_mask (OR-композит с маской).
; Обработчики столбца (col_copy / col_or) с их «лесенками» и разбор блока
; маски (mask_state / col_or_plane) живут в spr_smc.asm — здесь только
; раскладка плоскостей и разбор заголовка дескриптора.
; smc_init() (spr_smc.asm) обязан быть вызван до первого вывода.
;
; ИНВАРИАНТ: стаб обязан соответствовать паре (FLAGS, COLS) дескриптора.
; Таблица индексируется по FLAGS & 0x0F, COLS зашит в стаб через STUB_COLS;
; класс с другим числом столбцов = ещё одна инстанция стаба + своя запись
; в таблице (или общий путь через draw_sprite_smc / draw_sprite_smc_mask).
;
; Вход (готовят draw_sprite_stub / draw_sprite_stub_mask):
;   HL = верх левого столбца П3, DE = данные. На выходе HL/DE не нормируются —
;   вызов всё равно один на спрайт.

        SECTION code_clib
        PUBLIC  _draw_sprite_stub
        PUBLIC  _draw_sprite_stub_mask

        EXTERN  col_copy
        EXTERN  col_or
        EXTERN  col_or_plane    ; сброс курсоров маски и TABLE на плоскость
        EXTERN  mask_state      ; заголовок дескриптора с маской

        SECTION bss_compiler
st_desc:  defw    0             ; дескриптор SPR_FORMAT
st_x:     defb    0             ; x — пиксельная координата (кратна 8)
st_y:     defb    0             ; y — верх спрайта
st_dst:   defw    0             ; верх левого столбца в П3
st_flags: defb    0             ; FLAGS (плоскости) — младшие 4 бита
st_data:  defw    0             ; курсор данных цвета

        SECTION code_clib

STUB_COLS       EQU     3       ; COLS класса mario_new (все 3 фазы)

; ===============================================================
; Стабы: раскладка «плоскость -> столбцы» навылет
; ===============================================================

stub_tab:                       ; 16 входов по FLAGS & 0x0F (bit0=П3 ... bit3=П0)
        defw    stub_none       ;  0 — ни одной плоскости
        defw    stub_none       ;  1 П3
        defw    stub_none       ;  2 П2
        defw    stub_none       ;  3 П3+П2
        defw    stub_none       ;  4 П1
        defw    stub_none       ;  5 П3+П1
        defw    stub_none       ;  6 П2+П1
        defw    stub_none       ;  7 П3+П2+П1
        defw    stub_none       ;  8 П0
        defw    stub_none       ;  9 П3+П0
        defw    stub_none       ; 10 П2+П0
        defw    stub_none       ; 11 П3+П2+П0
        defw    stub_1_0        ; 12 П1+П0 — все кадры mario_new.inc
        defw    stub_none       ; 13 П3+П1+П0
        defw    stub_none       ; 14 П2+П1+П0
        defw    stub_none       ; 15 все четыре

stub_mask_tab:                  ; то же для дескрипторов с маской
        defw    stub_none       ;  0 — ни одной плоскости
        defw    stub_none       ;  1 П3
        defw    stub_none       ;  2 П2
        defw    stub_none       ;  3 П3+П2
        defw    stub_none       ;  4 П1
        defw    stub_none       ;  5 П3+П1
        defw    stub_none       ;  6 П2+П1
        defw    stub_none       ;  7 П3+П2+П1
        defw    stub_none       ;  8 П0
        defw    stub_none       ;  9 П3+П0
        defw    stub_none       ; 10 П2+П0
        defw    stub_none       ; 11 П3+П2+П0
        defw    stub_mask_1_0   ; 12 П1+П0 — все кадры mario_new_mask.inc
        defw    stub_none       ; 13 П3+П1+П0
        defw    stub_none       ; 14 П2+П1+П0
        defw    stub_none       ; 15 все четыре

stub_none:
        ret                     ; таких плоскостей в формате нет

; FLAGS = 0x0C: П1 + П0 (как у всех кадров mario_new.inc)
stub_1_0:
        mov     a, h            ; база П3 -> П1: +2 плоскости
        adi     40h
        mov     h, a

        rept    STUB_COLS-1     ; --- П1: столбцы 0..COLS-2
        call    col_copy        ; столбец целиком (3 байта — цена CALL)
        inr     h               ; следующий столбец +0x100
        endr
        call    col_copy        ; последний столбец П1
        rept    STUB_COLS-1     ; H вырос на COLS-1 (после последнего столбца
        dcr     h               ; INR H нет) — возвращаемся к левому столбцу
        endr

        mov     a, h            ; база П1 -> П0
        adi     20h
        mov     h, a

        rept    STUB_COLS-1     ; --- П0: столбцы 0..COLS-2
        call    col_copy
        inr     h
        endr
        call    col_copy        ; последний столбец П0
        ret

; FLAGS = 0x0C + маска: П1 + П0, композит через col_or.
; Маска и TABLE общие на все плоскости, поэтому col_or_plane возвращает
; оба курсора на начало перед каждой плоскостью (цвет, наоборот, идёт линейно).
stub_mask_1_0:
        mov     a, h            ; база П3 -> П1: +2 плоскости
        adi     40h
        mov     h, a
        call    col_or_plane    ; маска и TABLE — с первого столбца

        rept    STUB_COLS-1     ; --- П1: столбцы 0..COLS-2
        call    col_or          ; столбец: (dst AND маска) OR цвет
        inr     h               ; следующий столбец +0x100
        endr
        call    col_or          ; последний столбец П1
        rept    STUB_COLS-1
        dcr     h               ; назад к левому столбцу
        endr

        mov     a, h            ; база П1 -> П0
        adi     20h
        mov     h, a
        call    col_or_plane    ; маска и TABLE — снова с первого столбца

        rept    STUB_COLS-1     ; --- П0: столбцы 0..COLS-2
        call    col_or
        inr     h
        endr
        call    col_or          ; последний столбец П0
        ret

; ===============================================================
; Точки входа: разбор аргументов, выбор стаба, прыжок в него
; ===============================================================

; ---------------------------------------------------------------
; void draw_sprite_stub(unsigned char x, unsigned int y,
;                       const unsigned char *desc)
; Результат тот же, что у draw_sprite_smc, но без цикла по плоскостям:
; стаб выбирается по FLAGS и исполняется навылет.
; ---------------------------------------------------------------
_draw_sprite_stub:
        ; Соглашение __z88dk_callee (как lib/gfx/pr.asm): каждый аргумент —
        ; 16-битный слот, значение в младшем байте; последний аргумент сверху.
        ; Стек: ret(2), desc(2), y(2), x(2).
        pop     d               ; ret
        pop     h
        shld    st_desc         ; desc — последний аргумент, снимается первым
        pop     h
        mov     a, l
        sta     st_y            ; y
        pop     h
        mov     a, l
        sta     st_x            ; x — первый аргумент, снимается последним
        push    d

        ; dst = 0x8000 + (x/8)*256 + (255-y) — база П3
        lda     st_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     st_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     stb1
        inr     h
stb1:   shld    st_dst

        ; Заголовок: нужен только FLAGS — COLS зашит в стаб (см. ИНВАРИАНТ)
        lhld    st_desc
        mov     a, m
        sta     st_flags
        inx     h
        inx     h               ; COLS и DEPTH стабу не нужны
        inx     h               ; -> DATA = desc+3
        shld    st_data

        ; Адрес стаба = stub_tab[FLAGS & 0x0F]
        lda     st_flags
        ani     0Fh
        add     a               ; *2 — адреса в таблице 2-байтовые
        mov     l, a
        mvi     h, 0
        lxi     d, stub_tab
        dad     d
        mov     e, m
        inx     h
        mov     d, m
        push    d               ; адрес стаба — его снимет RET ниже

        lhld    st_data
        xchg                    ; DE = курсор данных
        lhld    st_dst          ; HL = верх левого столбца П3
        ret                     ; прыжок в стаб; стаб вернётся к вызывающему

; ---------------------------------------------------------------
; void draw_sprite_stub_mask(unsigned char x, unsigned int y,
;                           const unsigned char *desc)
; То же, но стаб компонует по маске (col_or). Дескриптор — вариант
; с маской (FLAGS bit4): маска ПЕРВЫМ блоком DATA, erase не нужен.
; ---------------------------------------------------------------
_draw_sprite_stub_mask:
        ; Стек: ret(2), desc(2), y(2), x(2).
        pop     d               ; ret
        pop     h
        shld    st_desc
        pop     h
        mov     a, l
        sta     st_y
        pop     h
        mov     a, l
        sta     st_x
        push    d

        ; dst = 0x8000 + (x/8)*256 + (255-y) — база П3
        lda     st_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     st_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     stb2
        inr     h
stb2:   shld    st_dst

        ; FLAGS — для выбора стаба; TABLE — для базы маски и курсора цвета.
        ; COLS стабу не нужен, но нужен mask_state — читаем ради счётчика.
        lhld    st_desc
        mov     a, m            ; FLAGS
        ani     0Fh             ; bit0=П3 ... bit3=П0
        sta     st_flags
        inx     h
        mov     a, m            ; COLS
        mov     b, a
        inx     h
        inx     h               ; DEPTH пропускаем, HL = TABLE = desc+3
        call    mask_state      ; TABLE, _rn_mask и курсор цвета
        shld    st_data

        ; Адрес стаба = stub_mask_tab[FLAGS & 0x0F]
        lda     st_flags
        add     a               ; *2 — адреса в таблице 2-байтовые
        mov     l, a
        mvi     h, 0
        lxi     d, stub_mask_tab
        dad     d
        mov     e, m
        inx     h
        mov     d, m
        push    d               ; адрес стаба — его снимет RET ниже

        lhld    st_data
        xchg                    ; DE = курсор цвета
        lhld    st_dst          ; HL = верх левого столбца П3
        ret                     ; прыжок в стаб; стаб вернётся к вызывающему
