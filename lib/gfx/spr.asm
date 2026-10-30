;
; spr.asm — стандартные ядра вывода спрайтов формата SPR_FORMAT (8080).
;
; Пара методов «чистый битблит / битблит с маской», выбранная замерами
; roms/tests/spr-speed (методика: КР580ВИ53, 96 тиков/строку растра):
;   16×24-пикс спрайт Марио (3 столбца, 2 плоскости, ~168 записей в VRAM):
;     spr_blit      = 4208 тиков = 43.8 строки растра
;     spr_blit_mask = 7274 тиков = 75.8 строки растра
;   (tile-prefab-движок: 142.7 строки; generic-интерпретатор: 55.2 / 111.5).
; Полная спека формата — docs/SPR_FORMAT.MD.
;
; Формат дескриптора:
;   [FLAGS, COLS, DEPTH] + (TABLE) + DATA
;   FLAGS: bit0=П3, bit1=П2, bit2=П1, bit3=П0, bit4=маска, bit6=OR-композит
;
;   spr_blit (без маски): для каждой присутствующей плоскости (по порядку
;     П3,П2,П1,П0) подряд по COLS столбцов; столбец = [SHIFT, LEN] + LEN байт:
;     SHIFT — сдвиг от верхней строки спрайта до первой выводимой строки,
;     LEN   — число выводимых байтов (0 = столбец пуст). Выводятся только
;     строки с первой по последнюю ненулевую — головные и хвостовые нули
;     не хранятся и не пишутся в VRAM. DEPTH в заголовке пропускается
;     (геометрия — из по-столбцовых SHIFT/LEN).
;
;   spr_blit_mask (FLAGS bit4): [FLAGS, COLS, DEPTH] + TABLE + DATA;
;     TABLE = COLS пар [SHIFT, LEN] — общая для маски и всех плоскостей;
;     DATA = [блок маски][прогоны П3..П0] — маска лежит ПЕРВОЙ
;     (mask_base = DATA, арифметики нет), цветные блоки идут за ней линейно.
;     Композиция строки: dst = (dst AND mask) OR color — фон вне силуэта
;     сохраняется, отдельный erase под спрайтом не нужен.
;
; Технология: обработчик столбца (col_copy / col_or) + развёрнутая в ОЗУ
; «лесенка» — straight-line тело из 4-байтовых (копирование: ldax d /
; mov m,a / inx d / dcx h, 24 такта на строку) или 9-байтовых (композиция,
; 53 такта на строку) строк вместо цикла DCR/JNZ (~39/94 тактов). Вход в
; лесенку = 0x7000 + 0x80 − 4·LEN (или 0x7100 + 0xFC − 9·LEN): исполнив
; LEN строк, поток проваливается в хвост pop h / ret, который возвращает
; HL вызывающего. В кадре нет ни загрузки флагов, ни ветвлений — только
; CALL столбца (17 тактов) и INR H между столбцами.
;
; Кольцо 256 строк (аппаратный скролл): y спрайта — мировая координата по
; mod 256, столбец VRAM (256 байт, страница H) — кольцо. Старт прогона
; (255−y−SHIFT) берётся по mod 256 БЕЗ займа страницы, а прогон, уходящий
; за нуль столбца, разбивается на два входа в лесенку: seg1 = L+1 строка до
; offset 0x00, seg2 = LEN−L−1 строк с offset 0xFF того же блока (курсоры
; данных DE и маски BC линейны — второй проход продолжает первый; хвост
; seg1 возвращается в промежуточный обработчик, а не вызывающему).
; LEN ≤ 32 < 256 ⇒ шов на столбец максимум один. Цена проверки шва:
; ~+14 тактов на столбец у col_copy, ~+10 у col_or; само разбиение —
; только на шовных столбцах. Спрайт, целиком лежащий в 0..255, шва не имеет.
;
; ВАЖНО — собственность на ОЗУ: spr_init() собирает лесенки по адресам
;   0x7000..0x7081 — копирование: 32 строки по 4 байта + хвост pop h/ret;
;   0x7100..0x7203 — композиция: 28 строк по 9 байт + хвост 8 байт.
; Пределы: LEN <= 32 у spr_blit, LEN <= 28 у spr_blit_mask.
; Проект, держащий кучу (heap_top = 0x8000), обязан не давать ей
; дорасти до 0x7000. spr_init() вызывается ОДИН раз до первого вывода.
;
; Вызов (__z88dk_callee, как lib/gfx/pr.asm):
;   void spr_init(void);
;   void spr_blit(unsigned char x, unsigned int y, const unsigned char *desc);
;   void spr_blit_mask(unsigned char x, unsigned int y,
;                      const unsigned char *desc);
;   x — пиксельная координата X (кратна 8), y — верх спрайта,
;   desc — указатель на дескриптор.
;
; Обработчики col_copy / col_or / col_or_plane / mask_state / mask_span —
; PUBLIC: на них собираются per-class «стабы», где раскладка плоскостей
; развёрнута при сборке (пример — spr_stub.asm в roms/tests/spr-speed).
;
; Только 8080-инструкции: без LDIR/LDDR/JR/DJNZ и префиксов CB/DD/ED/FD.
;

        SECTION code_clib
        PUBLIC  _spr_init
        PUBLIC  _spr_blit
        PUBLIC  _spr_blit_mask
        PUBLIC  mask_span
        PUBLIC  mask_state
        PUBLIC  col_copy
        PUBLIC  col_or
        PUBLIC  col_or_plane

        SECTION bss_clib
_sb_dst:  defw    0          ; базовый адрес VRAM (верх левого столбца)
_sb_desc: defw    0
_sb_flags: defb   0
_sb_cols: defb    0
_sb_depth: defb   0
_sb_data: defw    0
_sb_x:    defb    0
_sb_y:    defb    0

; --- вариант с маской ---
_sb_mask: defw    0          ; база блока маски = DATA (маска лежит первой)
_sb_mcur: defw    0          ; курсор маски (линейно по блоку)
_sb_tab:  defw    0          ; база TABLE [SHIFT, LEN]
_sb_tcur: defw    0          ; курсор TABLE

; --- разбиение прогона на шве кольца 256 строк (общие col_copy/col_or) ---
_sb_seg2: defb    0          ; число строк seg2 (с offset 0xFF)
_sb_start: defw   0          ; старт seg1 (страница = блок столбца)
_sb_entry: defw   0          ; адрес входа seg1 в лесенку

        SECTION code_clib

SPR_COPY_LADDER EQU     7000h   ; страница лесенки копирования (кратна 0x100!)
SPR_COPY_PAGE   EQU     70h     ; = SPR_COPY_LADDER >> 8
SPR_COPY_LAST   EQU     80h     ; младший байт хвоста (SPR_COPY_LADDER + 128)
SPR_COPY_ROWS   EQU     32      ; строк лесенки = максимальный LEN

SPR_OR_LADDER   EQU     7100h   ; страница лесенки композиции (кратна 0x100!)
SPR_OR_PAGE     EQU     71h     ; = SPR_OR_LADDER >> 8
SPR_OR_LAST     EQU     0FCh    ; младший байт хвоста (SPR_OR_LADDER + 9*ROWS)
SPR_OR_ROWS     EQU     28      ; строк лесенки = максимальный LEN маски
SPR_OR_ROW_LEN  EQU     9       ; байт в строке лесенки композиции

; ===============================================================
; ЯДРО ВЫВОДА СТОЛБЦА: обработчики col_copy / col_or + «лесенки»
; ===============================================================
; Столбец спрайта копирует ОДНА короткая подпрограмма col_copy.
; Вызывающий держит DE = указатель на столбец данных [SHIFT][LEN][байты],
; HL = адрес верха столбца в VRAM; после CALL нужен только INR H — и
; следующий столбец (DE уже за байтами столбца). Обработчик сам
; сохраняет/восстанавливает HL, читает SHIFT/LEN и уходит в «лесенку».
;
; Вызов — обычный CALL (17 тактов, 3 байта): обработчик живёт в обычном
; коде ROM по своему адресу, нулевая страница не нужна, инициализация
; сводится к сборке лесенки. Вариант с RST 1 (11 тактов, 1 байт на вызов)
; экономил 8 реальных тактов на столбец — на спрайт это 24 тика VI53
; (0,6 %), поэтому вектор не занимаем.
;
; Стек на один столбец (popов в обработчике нет — они в хвосте лесенки):
;   CALL      -2  адрес возврата в ps_col
;   push h    -2  верх столбца (HL входа)
;   push h    -2  начало столбца (HL после SHIFT)
;   XTHL       0  начало уходит в HL, в стеке остаётся адрес входа
;   ret       +2  прыжок в лесенку; верх стека — верх столбца
;   хвост 0x7080: pop h +2 (HL = верх столбца), ret +2 (назад в ps_col)
; Баланс нулевой: SP на входе в столбец равен SP после хвоста.

; ---------------------------------------------------------------
; col_copy — скопировать один столбец в VRAM (вызов: CALL col_copy).
; Вход: DE = [SHIFT][LEN][LEN байт], HL = верх столбца в VRAM.
; Выход: DE — за байтами столбца, HL = верх столбца (как на входе).
; Старт прогона — по кольцу mod 256 (страница H не меняется); при LEN >
; L+1 прогон бьётся на seg1/seg2 вокруг шва (см. шапку файла).
; ---------------------------------------------------------------
col_copy:
        push    h               ; [top] верх столбца — вернётся из хвоста лесенки
        ldax    d               ; A = SHIFT
        inx     d
        mov     c, a
        mov     a, l            ; L = (255−y−SHIFT) mod 256 — кольцо,
        sub     c               ; займа страницы нет
        mov     l, a
        ldax    d               ; A = LEN
        inx     d
        mov     c, a            ; C = LEN
        mov     a, l            ; шов: прогон уходит за нуль столбца?
        sub     c               ; CY ⇔ L < LEN
        jnc     cc_plain        ; L ≥ LEN — шва нет заведомо
        inr     a               ; L−LEN+1 = 0 ⇔ L = LEN−1: прогон упёрся в нуль
        jz      cc_plain
cc_seam:
        ; seg1 = L+1 строк от старта, seg2 = LEN−L−1 строк с 0xFF того же
        ; блока; DE линеен — seg2 продолжает байты seg1.
        mov     a, c
        dcr     a
        sub     l               ; A = seg2_len (на шве L ≤ LEN−2, CY=0)
        sta     _sb_seg2
        shld    _sb_start       ; старт seg1 (страница = блок столбца)
        mov     a, l
        inr     a               ; seg1_len = L+1 ≤ 31
        add     a
        add     a               ; 4*seg1_len
        cma
        inr     a
        adi     SPR_COPY_LAST
        mov     l, a
        mvi     h, SPR_COPY_PAGE
        shld    _sb_entry       ; вход seg1 в лесенку
        ; стек для seg1: [entry1][мусор][cc_seg2][top][ret вызывающего];
        ; хвост seg1: pop h (мусор), ret → cc_seg2.
        lxi     h, cc_seg2
        push    h               ; [cc_seg2][top][ret]
        lhld    _sb_start
        push    h               ; [мусор][cc_seg2][top][ret] — снимет pop h хвоста
        lhld    _sb_entry
        push    h               ; [entry1][мусор][cc_seg2][top][ret]
        lhld    _sb_start       ; HL = начало seg1
        ret                     ; лесенка seg1; её ret-jump снимает entry1
cc_seg2:
        ; стек [top][ret]; DE уже за байтами seg1, HL не нужен
        lhld    _sb_start
        mvi     l, 0FFh         ; seg2 начинается с offset 0xFF того же блока
        push    h               ; [seg2_start][top][ret]
        lda     _sb_seg2
        add     a
        add     a               ; 4*seg2_len
        cma
        inr     a
        adi     SPR_COPY_LAST
        mov     l, a
        mvi     h, SPR_COPY_PAGE ; HL = вход seg2
        xthl                    ; HL = seg2_start, в стеке — адрес входа
        ret                     ; лесенка seg2; хвост: pop h → HL=top, ret → вызывающий
cc_plain:
        push    h               ; [start][top] начало данных в VRAM; снимает XTHL ниже
        mov     a, c            ; A = LEN
        add     a               ; A = 4*LEN
        add     a
        cma                     ; A = 0x80 - 4*LEN — младший байт входа
        inr     a
        adi     SPR_COPY_LAST
        mov     l, a
        mvi     h, SPR_COPY_PAGE
        xthl                    ; HL = начало столбца, в стеке — адрес входа
        ret                     ; ret-прыжок: PC = вход, HL = начало столбца
col_copy_end:

; ---------------------------------------------------------------
; col_or — скомпоновать один столбец в VRAM (вызов: CALL col_or).
; Пара к col_copy: строка не копируется, а компонуется
;   dst = (dst AND mask) OR color
; Отличие от col_copy: в маске-дескрипторе заголовков [SHIFT][LEN] в потоке
; цвета НЕТ — они берутся из общей TABLE (курсор _sb_tcur), а маска — из
; _sb_mcur. Поэтому DE растёт ровно на LEN байт.
; Вход: DE = курсор цвета (LEN байт), HL = верх столбца в VRAM.
; Выход: DE — за байтами цвета, HL = верх столбца (как на входе),
;        _sb_tcur / _sb_mcur — продвинуты, B сохранён (C — нет).
; Перед каждой плоскостью курсоры сбрасывает col_or_plane.
; Старт прогона — по кольцу mod 256 (страница H не меняется); при LEN >
; L+1 прогон бьётся на seg1/seg2 вокруг шва; хвост seg1 сам сохраняет
; продвинутый курсор маски в _sb_mcur — seg2 подхватывает его оттуда.
;
; Стек на столбец: CALL -2; push b -2 (счётчик вызывающего); push h x2 -4
; (верх и рабочий экземпляр); push h -2 (начало столбца); push h -2 (адрес
; входа). Дальше XTHL (начало уходит в HL, вход остаётся под RET) + RET —
; поток проваливается в хвост 0x71FC: mov h,b / mov l,c / shld _sb_mcur /
; pop h / pop b / ret — баланс нулевой, SP возвращается к уровню после CALL.
; ---------------------------------------------------------------
col_or:
        push    b               ; B вызывающего — счётчик столбцов — не трогаем
        push    h               ; [top] верх столбца — вернётся из хвоста
        push    h               ; второй экземпляр: снимаемым получим начало
        lhld    _sb_tcur
        mov     a, m            ; SHIFT
        inx     h
        mov     c, a
        mov     a, m            ; LEN
        inx     h
        shld    _sb_tcur        ; TABLE продвинута
        mov     b, a            ; B = LEN (BC пока свободен)
        pop     h               ; HL = верх столбца
        mov     a, l            ; L = (255−y−SHIFT) mod 256 — кольцо,
        sub     c               ; займа страницы нет
        mov     l, a
        mov     a, l            ; шов: прогон уходит за нуль столбца?
        sub     b               ; CY ⇔ L < LEN
        jnc     or_plain        ; L ≥ LEN — шва нет заведомо
        inr     a               ; L−LEN+1 = 0 ⇔ L = LEN−1: прогон упёрся в нуль
        jz      or_plain
or_seam:
        ; seg1 = L+1 строк от старта, seg2 = LEN−L−1 строк с 0xFF того же
        ; блока; DE (цвет) линеен, курсор маски seg1 сохраняет в _sb_mcur.
        mov     a, b
        dcr     a
        sub     l               ; A = seg2_len (на шве L ≤ LEN−2, CY=0)
        sta     _sb_seg2
        shld    _sb_start       ; старт seg1 (страница = блок столбца)
        mov     a, l
        inr     a               ; seg1_len = L+1 ≤ 27
        mov     c, a
        add     a
        add     a
        add     a               ; 8*seg1_len
        add     c               ; 9*seg1_len
        cma
        inr     a
        adi     SPR_OR_LAST
        mov     l, a
        mvi     h, SPR_OR_PAGE
        shld    _sb_entry       ; вход seg1 в лесенку
        ; стек для seg1: [entry1][мусор-h][мусор-b][or_seg2][top][B][ret];
        ; хвост seg1: shld _sb_mcur; pop h (мусор); pop b (мусор); ret → or_seg2.
        lxi     h, or_seg2
        push    h               ; [or_seg2][top][B][ret]
        lhld    _sb_start
        push    h               ; мусор для pop b хвоста
        push    h               ; мусор для pop h хвоста
        lhld    _sb_entry
        push    h               ; [entry1][мусор-b][мусор-h][or_seg2][top][B][ret]
        lhld    _sb_mcur
        mov     c, l
        mov     b, h            ; BC = курсор маски seg1
        lhld    _sb_start       ; HL = начало seg1
        ret                     ; лесенка seg1; её ret-jump снимает entry1
or_seg2:
        ; стек [top][B][ret]; DE = цвет за seg1, _sb_mcur = курсор маски seg2
        lhld    _sb_start
        mvi     l, 0FFh         ; seg2 начинается с offset 0xFF того же блока
        push    h               ; [seg2_start][top][B][ret]
        lda     _sb_seg2
        mov     c, a
        add     a
        add     a
        add     a               ; 8*seg2_len
        add     c               ; 9*seg2_len
        cma
        inr     a
        adi     SPR_OR_LAST
        mov     l, a
        mvi     h, SPR_OR_PAGE  ; HL = вход seg2
        push    h               ; [entry2][seg2_start][top][B][ret]
        lhld    _sb_mcur
        mov     c, l
        mov     b, h            ; BC = курсор маски seg2
        pop     h               ; HL = адрес входа
        xthl                    ; HL = начало seg2, в стеке — адрес входа
        ret                     ; лесенка seg2; хвост: shld _sb_mcur;
                                ; pop h → HL=top; pop b → B=счётчик; ret → вызывающий
or_plain:
        push    h               ; [start][top][B] начало данных в VRAM
        mov     a, b            ; A = LEN
        add     a               ; 2*LEN
        add     a               ; 4*LEN
        add     a               ; 8*LEN
        add     b               ; 9*LEN
        cma
        inr     a               ; A = -9*LEN — младший байт входа
        adi     SPR_OR_LAST
        mov     l, a
        mvi     h, SPR_OR_PAGE  ; HL = адрес входа в лесенку
        push    h               ; [entry][start][top][B]
        lhld    _sb_mcur
        mov     c, l
        mov     b, h            ; BC = курсор маски
        pop     h               ; HL = адрес входа
        xthl                    ; HL = начало столбца, в стеке — адрес входа
        ret                     ; ret-прыжок: PC = вход, HL = начало столбца
col_or_end:

; ---------------------------------------------------------------
; col_or_plane — сбросить курсоры композиции на начало блоков.
; Маска и TABLE общие для всех плоскостей, цвет идёт линейно — поэтому
; перед каждой плоскостью их курсоры возвращаются назад. HL и DE не трогает.
; ---------------------------------------------------------------
col_or_plane:
        push    h
        push    d
        lhld    _sb_mask
        shld    _sb_mcur        ; маска — с начала блока
        lhld    _sb_tab
        shld    _sb_tcur        ; TABLE — с первого столбца
        pop     d
        pop     h
        ret

; ---------------------------------------------------------------
; void spr_init(void) — собрать обе «лесенки» в ОЗУ.
; Зовётся один раз до первого вызова ядер с маской или без.
;   0x7000 — строки копирования (4 байта x 32) + хвост pop h / ret;
;   0x7100 — строки композиции (9 байт x 28) + хвост mov h,b / mov l,c /
;            shld _sb_mcur / pop h / pop b / ret (8 байт, 0x71FC..0x7203).
; ---------------------------------------------------------------
_spr_init:
        ; лесенка -> 0x7000: SPR_COPY_ROWS строк по 4 байта + хвост pop h / ret
        lxi     d, SPR_COPY_LADDER
        mvi     b, SPR_COPY_ROWS
sc_row:
        lxi     h, ladder_row
        mvi     c, 4
sc_b:
        mov     a, m
        stax    d
        inx     h
        inx     d
        dcr     c
        jnz     sc_b
        dcr     b
        jnz     sc_row
        mvi     a, 0E1h         ; pop h — вернуть вызывающему верх столбца
        stax    d
        inx     d
        mvi     a, 0C9h         ; ret — назад в цикл по столбцам
        stax    d

        ; лесенка композиции -> 0x7100: SPR_OR_ROWS строк по 9 байт + хвост
        lxi     d, SPR_OR_LADDER
        mvi     b, SPR_OR_ROWS
oc_row:
        lxi     h, ladder_or_row
        mvi     c, SPR_OR_ROW_LEN
oc_b:
        mov     a, m
        stax    d
        inx     h
        inx     d
        dcr     c
        jnz     oc_b
        dcr     b
        jnz     oc_row
        mvi     a, 60h          ; mov h,b — продвинутый курсор маски...
        stax    d
        inx     d
        mvi     a, 69h          ; mov l,c
        stax    d
        inx     d
        mvi     a, 22h          ; shld — ...в _sb_mcur
        stax    d
        inx     d
        lxi     h, _sb_mcur
        mov     a, l
        stax    d
        inx     d
        mov     a, h
        stax    d
        inx     d
        mvi     a, 0E1h         ; pop h — вернуть вызывающему верх столбца
        stax    d
        inx     d
        mvi     a, 0C1h         ; pop b — вернуть счётчик столбцов
        stax    d
        inx     d
        mvi     a, 0C9h         ; ret — назад в цикл по столбцам
        stax    d
        ret

; Шаблон одной строки лесенки (только копируется, не исполняется).
ladder_row:
        ldax    d               ; байт данных
        mov     m, a            ; -> VRAM
        inx     d               ; следующая строка данных
        dcx     h               ; адрес в VRAM убывает вниз по экрану

; Шаблон одной строки лесенки композиции (только копируется, не исполняется).
; 53 такта против 94 у цикла por_run (тот же композит + счётчик строк в ОЗУ).
ladder_or_row:
        ldax    b               ; A = маска строки
        ana     m               ; A = фон AND маска
        xchg                    ; HL = цвет, DE = VRAM
        ora     m               ; A = (фон AND маска) OR цвет
        xchg                    ; HL = VRAM, DE = цвет
        mov     m, a            ; -> VRAM
        inx     b               ; следующая строка маски
        inx     d               ; следующая строка цвета
        dcx     h               ; адрес в VRAM убывает вниз по экрану

; ---------------------------------------------------------------
; mask_span — разбор блока маски по TABLE
; Вход: HL = TABLE ([SHIFT, LEN] x COLS), B = COLS.
; Выход: HL = DATA = TABLE + 2*COLS (база блока маски), DE = Σ LEN.
; Σ LEN — длина маски: цвет начинается сразу за ней.
; ---------------------------------------------------------------
mask_span:
        lxi     d, 0
ms_sum:
        inx     h               ; пропустить SHIFT
        mov     a, m            ; LEN
        add     e
        mov     e, a
        mvi     a, 0
        adc     d
        mov     d, a
        inx     h
        dcr     b
        jnz     ms_sum
        ret

; ---------------------------------------------------------------
; mask_state — разбор заголовка дескриптора с маской.
; Вход: HL = TABLE = desc+3 ([SHIFT, LEN] x COLS), B = COLS.
; Выход: _sb_tab = TABLE, _sb_mask = база маски, HL = _sb_data = цвет.
; Маска лежит ПЕРВЫМ блоком DATA, поэтому цвет = маска + Σ LEN.
; ---------------------------------------------------------------
mask_state:
        shld    _sb_tab         ; TABLE — общая для маски и цвета
        call    mask_span       ; HL = DATA (маска), DE = Σ LEN
        shld    _sb_mask        ; mask_base = DATA
        dad     d
        shld    _sb_data        ; цвет = маска + Σ LEN
        ret

; ---------------------------------------------------------------
; void spr_blit(unsigned char x, unsigned int y,
;               const unsigned char *desc)
; Чистый битблит (плоская запись) через col_copy; формат дескриптора —
; см. шапку файла. Аргументы — на стеке, каллее сам снимает (pr.asm).
; ---------------------------------------------------------------
_spr_blit:
        ; Стек: ret(2), desc(2), y(2), x(2).
        pop     d               ; ret
        pop     h
        shld    _sb_desc        ; desc — последний аргумент, снимается первым
        pop     h
        mov     a, l
        sta     _sb_y           ; y
        pop     h
        mov     a, l
        sta     _sb_x           ; x — первый аргумент, снимается последним
        push    d

        ; dst = 0x8000 + (x/8)*256 + (255-y) — база П3 (верх левого столбца)
        lda     _sb_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     _sb_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     sb1
        inr     h
sb1:    shld    _sb_dst

        ; Заголовок
        lhld    _sb_desc
        mov     a, m            ; FLAGS
        sta     _sb_flags
        inx     h
        mov     a, m            ; COLS
        sta     _sb_cols
        inx     h
        mov     a, m            ; DEPTH (геометрия — из SHIFT/LEN столбцов)
        sta     _sb_depth
        inx     h
        shld    _sb_data        ; DATA = desc+3

        ; Перебор плоскостей П3..П0, шаг адреса +0x2000
        mvi     c, 01h
sb_plane:
        lda     _sb_flags
        ana     c
        jz      sb_skip
        push    b
        call    plane_smc
        pop     b
sb_skip:
        lhld    _sb_dst
        mov     a, h
        adi     20h
        mov     h, a
        shld    _sb_dst
        mov     a, c
        rlc
        mov     c, a
        ani     10h             ; прошли все 4 плоскости?
        jz      sb_plane
        ret

; ---------------------------------------------------------------
; plane_smc — одна плоскость через col_copy
; Вход: B = cols (счётчик), HL = верх левого столбца, DE = данные.
; ---------------------------------------------------------------
plane_smc:
        lhld    _sb_data
        xchg                    ; DE = курсор данных столбцов
        lhld    _sb_dst         ; HL = верх левого столбца
        lda     _sb_cols
        mov     b, a
ps_col:
        call    col_copy        ; столбец целиком: SHIFT/LEN читает сам
        inr     h               ; следующий столбец +0x100
        dcr     b
        jnz     ps_col
        xchg                    ; HL = DE (продвинутый курсор данных)
        shld    _sb_data
        ret

; ---------------------------------------------------------------
; plane_smc_or — одна плоскость через col_or
; Вход: _sb_data = курсор цвета, _sb_dst = верх левого столбца.
; ---------------------------------------------------------------
plane_smc_or:
        call    col_or_plane    ; маска и TABLE — с начала блоков
        lhld    _sb_data
        xchg                    ; DE = курсор цвета
        lhld    _sb_dst
        lda     _sb_cols
        mov     b, a
pso_col:
        call    col_or          ; столбец: SHIFT/LEN из TABLE, маска из _sb_mcur
        inr     h               ; следующий столбец +0x100
        dcr     b
        jnz     pso_col
        xchg                    ; HL = DE (продвинутый курсор цвета)
        shld    _sb_data
        ret

; ---------------------------------------------------------------
; void spr_blit_mask(unsigned char x, unsigned int y,
;                    const unsigned char *desc)
; Битблит с маской (OR-композит через col_or); дескриптор — вариант с
; маской (FLAGS bit4), маска ПЕРВЫМ блоком DATA, erase не нужен.
; ---------------------------------------------------------------
_spr_blit_mask:
        ; Стек: ret(2), desc(2), y(2), x(2).
        pop     d               ; ret
        pop     h
        shld    _sb_desc
        pop     h
        mov     a, l
        sta     _sb_y
        pop     h
        mov     a, l
        sta     _sb_x
        push    d

        ; dst = 0x8000 + (x/8)*256 + (255-y) — база П3
        lda     _sb_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     _sb_y
        cma
        ora     a               ; CY=0 перед add l
        add     l
        mov     l, a
        jnc     sbm1
        inr     h
sbm1:   shld    _sb_dst

        ; Заголовок + база маски и курсор цвета
        lhld    _sb_desc
        mov     a, m            ; FLAGS
        sta     _sb_flags
        inx     h
        mov     a, m            ; COLS
        sta     _sb_cols
        mov     b, a            ; B = COLS — счётчик для mask_state
        inx     h
        mov     a, m            ; DEPTH
        sta     _sb_depth
        inx     h
        call    mask_state      ; TABLE, _sb_mask и курсор цвета

        ; Перебор плоскостей П3..П0, шаг адреса +0x2000
        mvi     c, 01h
sbm_plane:
        lda     _sb_flags
        ana     c
        jz      sbm_skip
        push    b
        call    plane_smc_or
        pop     b
sbm_skip:
        lhld    _sb_dst
        mov     a, h
        adi     20h
        mov     h, a
        shld    _sb_dst
        mov     a, c
        rlc
        mov     c, a
        ani     10h             ; прошли все 4 плоскости?
        jz      sbm_plane
        ret
