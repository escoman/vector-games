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
;   скрипт уровня -> коды частей -> список записей столбцов ->
;   запись = 15 кодов клеток -> банк шаблонов по 8 байт.
;
; Кольцо оригинала ($8000, 128-байтные страницы-столбцы) перенесено один в
; один, только страница здесь 256 байт (столбцу VRAM ровно 256) и заполнена
; нижняя половина. Страница собирается на ходу: m_assemble читает очередную
; запись и раскрывает коды клеток через банк, 16 клеток = 128 байт.
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
REC_LEN EQU     15              ; кодов клеток в записи столбца

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
        lxi     h, m_ff         ; «список кончился» -> первый код из скрипта
        shld    m_partp

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
; Столбец = дорожная клетка + 15 клеток из записи. Дорожная клетка в
; оригинале чередуется ($C4B8 / $C4C0, ENGINE.MD §3.3): вариант B каждые
; восемь столбцов — правило смотрит в абсолютный номер столбца, поэтому на
; переходе уровня шов не появляется.
; ---------------------------------------------------------------------------
m_assemble:
        call    m_nextrec                   ; HL = запись столбца
        shld    m_rec
        lxi     d, lv_bank                  ; DE — база банка, m_cell её читает

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
        cmc
        rra                                 ; m_col/2
        inr     a
        ani     03h
        lda     lv_cfg + 1                  ; LDA флаги не трогает
        jnz     m_as_road
        lda     lv_cfg + 2
m_as_road:
        call    m_cell

        ; --- 15 клеток записи
        mvi     a, REC_LEN
        sta     m_cnt
m_as_cells:
        lhld    m_rec
        mov     a, m
        inx     h
        shld    m_rec
        call    m_cell
        lda     m_cnt
        dcr     a
        sta     m_cnt
        jnz     m_as_cells

        lda     m_col                       ; столбец мира занят
        inr     a
        sta     m_col
        ret

; ---------------------------------------------------------------------------
; m_cell: 8 байт шаблона с кодом A -> (BC), BC += 8.
; Вход: DE = lv_bank. Выход: BC следующий свободный байт страницы.
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
; m_nextrec: следующая запись столбца из скрипта уровня.
;
; Байт-коды читаются ровно как в оригинале: скрипт — поток кодов частей
; через $FF, часть — список номеров записей через $FF. Конец скрипта = конец
; уровня: m_newlevel выставляет флаг и переводит курсор на первый уровень
; (кольцевая миссия, как в демо-ленте оригинала).
;
; Выход: HL = lv_recs + 16*номер (шаг — степень двойки, умножение сдвигами).
; ---------------------------------------------------------------------------
m_nextrec:
        lhld    m_partp
        mov     a, m
        cpi     0FFh
        jnz     mnr_got
mnr_code:
        lhld    m_scriptp
        mov     a, m
        inx     h
        shld    m_scriptp
        cpi     0FFh
        jnz     mnr_list
        call    m_newlevel                  ; курсор уже на новом скрипте
        lhld    m_scriptp
        mov     a, m                        ; первый код нового уровня
        inx     h
        shld    m_scriptp                   ; ...и сдвигаем его, как выше
mnr_list:
        ; --- m_partp = lv_pofs[A]
        mov     l, a
        mvi     h, 0
        dad     h                           ; слова по 2 байта
        push    d
        lxi     d, lv_pofs
        dad     d
        pop     d
        mov     a, m
        inx     h
        mov     h, m
        mov     l, a                        ; HL = список записей части
        shld    m_partp
        mov     a, m
        cpi     0FFh
        jz      mnr_code                    ; пустая часть — берём следующую
mnr_got:
        inx     h
        shld    m_partp                     ; курсор на следующий номер
        ; --- HL = lv_recs + 16*A
        mov     l, a
        mvi     h, 0
        dad     h
        dad     h
        dad     h
        dad     h
        push    d
        lxi     d, lv_recs
        dad     d
        pop     d
        ret

; ---------------------------------------------------------------------------
; m_newlevel: уровень пройден — курсор на следующий (по модулю числа уровней)
; и его скрипт. Флаг m_changed читает main.c: цвет рельефа — свой на уровень.
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
        ret

; $FF там, где у движка «списка больше нет»: первый код берётся из скрипта.
m_ff:
        defb    0FFh

; ---------------------------------------------------------------------------
; Рабочие переменные.
; ---------------------------------------------------------------------------
        SECTION bss_clib

m_ring:     defs    2       ; кольцо из кучи, M_COLS*256 байт
m_rec:      defs    2       ; текущая запись столбца
m_scriptp:  defs    2       ; курсор скрипта уровня
m_partp:    defs    2       ; курсор списка записей текущей части
m_pbase:    defb    0       ; старший байт плоскости back-буфера (E0/A0)
m_level:    defb    0       ; текущий уровень
m_cam:      defb    0       ; столбец мира у левого края экрана
m_col:      defb    0       ; следующий столбец мира для сборки
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
