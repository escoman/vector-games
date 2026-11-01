;
; mission.asm — движок рельефа миссии H.A.T.E. для Вектора-06Ц.
;
; ЧТО ДЕЛАЕТ. Лента ландшафта (32 байтовых столбца) плывёт справа налево.
; Один «тик» камеры = один новый столбец мира на входе ленты. По завершении
; уровня (скрипт дошёл до $FF) движок выставляет флаг, а цвет рельефа меняет
; вызывающая сторона — палитрой, не перерисовкой (см. main.c).
;
; ДАННЫЕ — оригинальные байт-коды (include/levels.inc, tools/gen_levels.py):
;
;   скрипт уровня -> коды частей -> списки указателей ($C8EA + 2*код) ->
;   байт-код клетки: lv_data[q[base + i] + i] -> банк шаблонов по 8 байт.
;
; Кольцо оригинала ($8000, 128-байтные страницы-столбцы) перенесено один в
; один, только страница здесь 256 байт (столбцу VRAM ровно 256) и заполнена
; нижняя половина. Страница собирается на ходу: m_assemble берёт очередной
; указатель очереди, дочитывает код клетки по нему и раскрывает клетку через
; банк, 16 клеток = 128 байт.
;
; УКЛОН ЛЕНТЫ. В оригинале off(x+1) = off(x) + $1FC, то есть каждый следующий
; столбец начинается на 4 байта выше предыдущего — отсюда диагональ ленты.
; Здесь уклон задан не данными, а стартом блита: lv_geom[x] = (4x, 16).
;
; КУДА РИСУЕТ. Только в back-буфер: плоскость веса 1 буфера A (0xE000) либо
; веса 4 буфера B (0xA000) — её выбирает gfx_dblbuf_back(). Вторая плоскость
; того же буфера (веса 2/8) рельефом не пишется и обязана быть нулевой,
; иначе логический цвет 1 перестанет быть единичным битом маски.
;
; ЦЕНА И ЧАНКИНГ (замерено в эмуляторе, TZ §9). Полоса = 4096 байт, тик
; камеры = полный переблит. Копирование (HL)->(BC) стоит 24 базовых такта на
; байт, но доступ к ОЗУ/VRAM рядом с лучом даёт wait states: по факту ~42 T на
; байт. Кадр с M_CHUNK=8 (1024 байта) = 43 196 T = 72 % кадра (кадр 59 904 T
; при 3 МГц, BEAM_TIMING.MD §1); кадр с тиком (в нём ещё m_assemble +
; present) = 51 416 T = 86 %. За 4 кадра периода уходит 180 004 T = 75 %, ни
; один кадр не вылез за VBlank (проверено по лучу: входы в mission_frame идут
; строго через кадр). Тик раз в 4 кадра => те же 2 пикселя за кадр, что и в
; оригинале. Больше 8 столбцов брать некуда: 9-й оставляет тиковому кадру
; 94 % бюджета, а 32 на 9 не делится; 16 уже не влезает (замер — TZ §9.1).
; Писать в back-буфер можно в любой момент кадра: его биты закрыты маской
; палитры front-буфера, луч их показывает — окно гашения (§5) нужно только
; перерисовке front, у нас её нет.
;
; Только 8080: без LDIR/LDDR/JR/DJNZ/IX/IY и префиксов CB/DD/ED/FD.

        SECTION code_clib
        PUBLIC  _mission_start
        PUBLIC  _mission_frame
        PUBLIC  _mission_level

        EXTERN  _gfx_dblbuf_back
        EXTERN  _gfx_dblbuf_present

M_COLS  EQU     32              ; столбцов кольца (и экрановых колонок)
M_CHUNK EQU     8               ; столбцов полосы за кадр (72 % кадра, см. TZ §9)
REC_LEN EQU     15              ; клеток в столбце кроме дорожной
WIN     EQU     16              ; ячеек окна указателей (15 нужны, маска 15)
TERM    EQU     0FFh            ; терминатор скрипта и списка частей

; ---------------------------------------------------------------------------
; void mission_start(void *ring) __z88dk_callee;
;
; Кольцо — M_COLS*256 байт из кучи (heap_alloc). Собрать первые 32 столбца
; мира и нарисовать полосу ЦЕЛИКОМ в оба буфера: пока не сделан первый
; present, на экране висит front, и он обязан быть кадровым, а не «половина
; полосы». Дальше движок сам выбирает back по gfx_dblbuf_back().
; ---------------------------------------------------------------------------
_mission_start:
        pop     de              ; DE = return address
        pop     hl              ; HL = кольцо
        push    de
        shld    m_ring

        xra     a               ; старт: камера и счётчик столбцов с нуля
        sta     m_level
        sta     m_cam
        sta     m_col
        sta     m_draw
        sta     m_changed

        lxi     h, lv_sofs      ; скрипт нулевого уровня
        mov     a, m
        inx     h
        mov     h, m
        mov     l, a
        shld    m_scriptp
        call    m_prime         ; окно указателей: q[0..14] уровня 0

        mvi     a, M_COLS                   ; кольцо набито заранее, на ходу
        sta     m_loop                      ; только хвост; счётчик в RAM,
ms_ring:                                    ; m_assemble живёт регистрами
        call    m_assemble
        lda     m_loop
        dcr     a
        sta     m_loop
        jnz     ms_ring

        mvi     a, 0E0h         ; буфер A: плоскость веса 1
        sta     m_pbase
        call    m_full
        mvi     a, 0A0h         ; буфер B: плоскость веса 4
        sta     m_pbase
        call    m_full
        ret

; Полоса целиком в текущий m_pbase.
m_full:
        xra     a
        sta     m_draw
        mvi     a, M_COLS
        sta     m_left
        jmp     m_blit

; ---------------------------------------------------------------------------
; unsigned char mission_frame(void)
;
; Кадр: дописать M_CHUNK столбцов полосы в back-буфер. Когда полоса готова,
; собрать новый столбец мира, сдвинуть камеру и вызвать present() — своп на
; ближайшем VBlank сделает перерисованную полосу видимой целиком, без разрыва.
;
; Возврат: L = 1 — кадр презентован, 2 — сменился уровень (цвет по lv_col4
; правит вызывающая сторона: обе маски палитры + gfx_dblbuf_invalidate).
; ---------------------------------------------------------------------------
_mission_frame:
        call    _gfx_dblbuf_back            ; A = 0 -> back есть A, 1 -> B
        ora     a
        jz      mf_a
        mvi     a, 0A0h
        jmp     mf_base
mf_a:
        mvi     a, 0E0h
mf_base:
        sta     m_pbase
        mvi     a, M_CHUNK
        sta     m_left
        call    m_blit

        lda     m_draw
        cpi     M_COLS
        jnz     mf_idle
        ; --- тик камеры
        xra     a
        sta     m_draw
        lda     m_cam                       ; камера на столбец вперёд:
        inr     a                           ; левый уходит за край, правый
        sta     m_cam                       ; приходит с нового m_col
        call    m_assemble                  ; столбец m_col -> slot m_col&31
        lda     m_changed
        add     a
        adi     1                           ; бит0: Presented, бит1: уровень
        push    psw
        call    _gfx_dblbuf_present
        lda     m_changed
        ora     a
        jz      mf_flags
        xra     a
        sta     m_changed                   ; флаг живёт один кадр
mf_flags:
        pop     psw
        mov     l, a
        ret

mf_idle:
        xra     a
        mov     l, a
        ret

; ---------------------------------------------------------------------------
; unsigned char mission_level(void)
;
; Номер текущего уровня — по нему main.c берёт цвет из lv_col4.
; ---------------------------------------------------------------------------
_mission_level:
        lda     m_level
        mov     l, a
        ret

; ---------------------------------------------------------------------------
; m_blit: нарисовать до m_left столбцов полосы в буфер с базой m_pbase.
;
; Состояние — только m_draw (сколько столбцов уже нарисовано), всё остальное
; вычисляется заново на каждый столбец: адресов страницы кольца, колонки
; экрана и пары геометрии. Никаких «обновить указатель и проверить перенос» —
; переход через конец кольца случается в произвольном месте полосы, а здесь
; он вычитается из m_cam + x маскированием.
; ---------------------------------------------------------------------------
m_blit:
        lda     m_draw
        cpi     M_COLS
        rz                                  ; полоса готова
        mov     c, a
        lda     m_left
        mov     b, a                        ; B = m_left
        mvi     a, M_COLS
        sub     c                           ; A = сколько осталось в полосе
        mov     e, a
        mov     a, b
        sub     e
        jc      m_bl_few                    ; m_left меньше остатка — занимаемся
        mov     a, e                        ; иначе дорисовываем полосу
        jmp     m_bl_todo
m_bl_few:
        mov     a, b                        ; заём в A возвращать нельзя
m_bl_todo:
        sta     m_todo

m_bloop:
        ; --- геометрия: пара (старт, клеток) столбца x = m_draw
        lda     m_draw
        mov     l, a
        mvi     h, 0
        dad     h                           ; слова по 2 байта
        lxi     d, lv_geom
        dad     d
        mov     a, m                        ; старт нижней клетки столбца
        sta     m_start
        inx     h
        mov     a, m                        ; клеток в столбце
        sta     m_cnt

        ; --- источник: страница кольца столбца мира (m_cam + x)
        lda     m_cam
        mov     c, a
        lda     m_draw
        add     c
        ani     M_COLS - 1                  ; по модулю кольца
        mov     c, a                        ; C = номер страницы
        lda     m_ring
        mov     e, a                        ; младший байт не меняется
        lda     m_ring + 1
        add     c
        mov     h, a
        mov     l, e                        ; HL = страница источника

        ; --- приёмник: колонка x байтового экрана, старт из геометрии
        lda     m_pbase
        mov     d, a
        lda     m_draw
        add     d
        mov     b, a                        ; B = старший байт колонки
        lda     m_start
        mov     c, a                        ; C = старт в ней

        ; --- 8 клеток за проход (клетка = 8 строк, идёт вверх по экрану).
        ; Пара mov/stax/inx/inx = 24 базовых такта на байт; клетка обходится
        ; 192+41 T, весь кадр блита — 43 196 T реальных (72 %), см. TZ §9.
m_bcell:
        mov     a, m                        ; 7
        stax    b                           ; 7
        inx     b                           ; 5
        inx     h                           ; 5
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        lda     m_cnt                       ; 13
        dcr     a                           ; 5
        sta     m_cnt                       ; 13
        jnz     m_bcell                     ; 10
        ; --- следующий столбец
        lda     m_draw
        inr     a
        sta     m_draw
        lda     m_todo
        dcr     a
        sta     m_todo
        jnz     m_bloop
        ret

; ---------------------------------------------------------------------------
; m_assemble: собрать столбец мира m_col в его страницу кольца.
;
; Столбец = дорожная клетка + 15 клеток, и каждая клетка берётся СВОИМ
; указателем очереди ($D51D, LD4E9_4): клетка i = lv_data[q[base + i] + i].
; Очередь уровня — склейка списков частей по скрипту; на столбец она уходит
; на один указатель вперёд, поэтому m_win хранит 16 последних указателей и
; на столбец читается ровно одно новое слово — как POP HL в оригинале.
;
; Дорожная клетка чередуется ($C4B8 / $C4C0, ENGINE.MD §3.3): вариант B при
; (столбец+1) & 3 = 0 — в оригинале правило считает по $C32E = 2*столбец.
; Счёт идёт по абсолютному номеру столбца, поэтому на переходе уровня шва нет.
; ---------------------------------------------------------------------------
m_assemble:
        lda     m_lcol
        ora     a
        jz      ma_cells                    ; окно набито началом уровня
        call    m_pop                       ; указатель q[base + 14]
        jnc     ma_win
        call    m_newlevel                  ; скрипт кончился: новый уровень
        jmp     ma_cells                    ; ...и его окно уже набито
ma_win:
        shld    m_pair
        lda     m_lcol
        adi     REC_LEN - 1                 ; ячейка окна столбца base + 14
        ani     WIN - 1
        mov     l, a
        mvi     h, 0
        dad     h                           ; слова по 2 байта
        lxi     d, m_win
        dad     d
        push    h                           ; адрес ячейки окна
        lhld    m_pair
        xthl                                ; HL = адрес ячейки, на стеке — q
        pop     d                           ; DE = указатель очереди
        mov     m, e
        inx     h
        mov     m, d

ma_cells:
        lxi     d, lv_data                  ; DE — база данных, m_cell её читает

        ; --- BC = страница кольца: кольцо + 256*(m_col & 31)
        lda     m_col
        ani     M_COLS - 1
        mov     c, a
        lda     m_ring + 1
        add     c
        mov     b, a
        lda     m_ring
        mov     c, a

        ; --- дорожная клетка
        lda     m_col
        inr     a
        ani     03h
        lda     lv_cfg + 1                  ; LDA флаги не трогает
        jnz     ma_road
        lda     lv_cfg + 2
ma_road:
        call    m_cell

        ; --- 15 клеток: код i-й = lv_data[q[base + i] + i]
        xra     a
        sta     m_i
        mvi     a, REC_LEN
        sta     m_cnt
ma_as_cells:
        lda     m_lcol
        mov     l, a                        ; B и C держат приёмник (BC),
        lda     m_i                         ; трогать их нельзя
        add     l                           ; A = база + номер клетки
        ani     WIN - 1
        mov     l, a
        mvi     h, 0
        dad     h                           ; слова по 2 байта
        lxi     d, m_win
        dad     d
        mov     e, m
        inx     h
        mov     d, m                        ; DE = указатель очереди (адрес
                                            ; в lv_data: m_pop уже сложил его
                                            ; с lv_delta)
        lda     m_i
        mov     l, a
        mvi     h, 0
        dad     d                           ; HL = указатель + номер клетки
        mov     a, m                        ; код клетки
        lxi     d, lv_data                  ; DE — банк шаблонов
        call    m_cell
        lda     m_i
        inr     a
        sta     m_i
        lda     m_cnt
        dcr     a
        sta     m_cnt
        jnz     ma_as_cells

        lda     m_col                       ; столбец мира занят
        inr     a
        sta     m_col
        lda     m_lcol
        inr     a
        sta     m_lcol
        ret

; ---------------------------------------------------------------------------
; m_cell: 8 байт шаблона с кодом A -> (BC), BC += 8.
; Вход: DE = lv_data (банк шаблонов — её начало). Выход: BC — следующий
; свободный байт страницы.
; ---------------------------------------------------------------------------
m_cell:
        mov     l, a
        mvi     h, 0
        dad     h
        dad     h
        dad     h                           ; *8 — размер клетки
        dad     d                           ; + lv_bank
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        mov     a, m
        stax    b
        inx     b
        inx     h
        ret

; ---------------------------------------------------------------------------
; m_pop: следующий указатель очереди уровня.
;
; Очередь в оригинале собирает LD4E9: по скрипту уровня склеиваются списки
; указателей частей ($C8EA + 2*код): слово за словом до слова со старшим
; байтом 0. Списки лежат встык, так что список части — «хвост» таблицы.
; Здесь очередь не копируется в память, а читается по одному указателю за
; столбец — то же самое, что POP HL в $D51D.
;
; Скрипт кончается раньше очереди: буфер $CA43 сборщик не чистит, и за
; последним записанным словом остаётся образ программы. Уровень дочитывает
; его как хвост (lv_tail), а конец — слово со старшим байтом $FF (в
; оригинале это проверка на столбец вперёд, LD2E3_20).
;
; Выход: CY = 0 — HL = адрес внутри lv_data (указатель ZX + lv_delta);
;        CY = 1 — очередь уровня кончилась.
; ---------------------------------------------------------------------------
m_pop:
        lhld    m_partp
mp_word:
        mov     e, m
        inx     h
        mov     d, m
        inx     h
        shld    m_partp
        mov     a, d
        ora     a
        jz      mp_code                     ; старший байт 0 — конец списка
        cpi     0FFh
        jz      mp_end                      ; $FF — очередь уровня кончилась
        lhld    lv_delta
        dad     d                           ; указатель ZX -> адрес в lv_data
        ora     a                           ; DAD портит CY: сбрасываем
        ret
mp_code:
        lhld    m_scriptp
        mov     a, m
        inx     h
        shld    m_scriptp
        cpi     TERM
        jz      mp_end
        mov     e, a                        ; A = код части
        mvi     d, 0
        lhld    lv_parts                    ; HL = таблица частей ($C8EA)
        dad     d
        dad     d                           ; + 2*код
        shld    m_partp
        jmp     mp_word
mp_end:
        lda     m_tail                      ; скрипт кончился — дальше хвост
        ora     a
        jnz     mp_stop
        mvi     a, 1
        sta     m_tail
        lxi     h, lv_tail
        shld    m_partp
        jmp     mp_word
mp_stop:
        stc
        ret

; ---------------------------------------------------------------------------
; m_prime: набить окно указателей началом уровня — q[0..14] и снять хвост
; очереди предыдущего уровня.
; ---------------------------------------------------------------------------
m_prime:
        lxi     h, m_ff
        shld    m_partp                     ; пустой список -> первый код
        xra     a
        sta     m_lcol
        sta     m_i
        sta     m_tail
mpr_pop:
        call    m_pop
        jc      mpr_end                     ; части короче окна не бывает
        push    h
        lda     m_i
        mov     l, a
        mvi     h, 0
        dad     h                           ; слова по 2 байта
        lxi     d, m_win
        dad     d
        pop     d                           ; DE = указатель очереди
        mov     m, e
        inx     h
        mov     m, d
        lda     m_i
        inr     a
        sta     m_i
        cpi     REC_LEN
        jnz     mpr_pop
mpr_end:
        ret

; ---------------------------------------------------------------------------
; m_newlevel: уровень пройден — курсор на следующий (по модулю числа уровней),
; его скрипт и окно указателей. Флаг m_changed читает main.c: цвет рельефа —
; свой на уровень.
; ---------------------------------------------------------------------------
m_newlevel:
        mvi     a, 1
        sta     m_changed
        lda     m_level
        inr     a
        lxi     h, lv_cfg
        cmp     m                           ; lv_cfg[0] — число уровней
        jnz     mnl_set
        xra     a
mnl_set:
        sta     m_level
        mov     l, a
        mvi     h, 0
        dad     h                           ; слова по 2 байта
        push    d
        lxi     d, lv_sofs
        dad     d
        pop     d
        mov     a, m
        inx     h
        mov     h, m
        mov     l, a
        shld    m_scriptp
        call    m_prime
        ret

; $FF там, где у движка «списка больше нет»: старший байт 0 — терминатор
; списка указателей, так что первый m_pop сразу берёт код из скрипта.
m_ff:
        defb    0FFh, 00h

; ---------------------------------------------------------------------------
; Рабочие переменные.
; ---------------------------------------------------------------------------
        SECTION bss_clib

m_ring:     defs    2       ; кольцо из кучи, M_COLS*256 байт
m_scriptp:  defs    2       ; курсор скрипта уровня
m_partp:    defs    2       ; курсор списка указателей текущей части
m_tail:     defb    0       ; 1 — очередь дочитывает хвост (lv_tail)
m_pair:     defs    2       ; указатель очереди, пока считается адрес окна
m_win:      defs    2*WIN   ; последние указатели очереди (смещения в lv_data)
m_pbase:    defb    0       ; старший байт плоскости back-буфера (E0/A0)
m_level:    defb    0       ; текущий уровень
m_cam:      defb    0       ; столбец мира у левого края экрана
m_col:      defb    0       ; следующий столбец мира для сборки (с начала миссии)
m_lcol:     defb    0       ; столбец мира внутри уровня (сдвиг окна)
m_i:        defb    0       ; номер клетки в столбце
m_draw:     defb    0       ; столбцов полосы нарисовано в этом проходе
m_left:     defb    0       ; столбцов разрешено нарисовать в этом кадре
m_todo:     defb    0       ; столбцов осталось нарисовать в этом кадре
m_start:    defb    0       ; старт блита текущего столбца
m_cnt:      defb    0       ; счётчик клеток
m_loop:     defb    0       ; счётчик начальной набивки кольца
m_changed:  defb    0       ; уровень сменился, цвет не применён

; Данные уровней — levels.inc открывает SECTION rodata_user сам, и после его
; включения по коду уже ничего быть не должно.
        INCLUDE "levels.inc"
