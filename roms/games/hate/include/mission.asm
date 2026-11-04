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
; Промежуточного кольца в RAM нет. Готовое изображение хранится прямо в
; двух плоскостях VRAM. При прокрутке 31 столбец копируется из front[x+1]
; в back[x], а новый правый столбец берётся из банка шаблонов напрямую.
; Для сохранения фазы первого кадра используется только временный
; буфер одного столбца (128 байт) в обычной RAM, а не кольцо на 8 КБ.
;
; УКЛОН ЛЕНТЫ. Каждый следующий столбец начинается на 4 байта выше
; предыдущего: экранный адрес столбца x = (plane+x)*256 + 4*x.
;
; КУДА РИСУЕТ. Только в back-буфер: плоскость веса 1 буфера A (0xE000) либо
; веса 4 буфера B (0xA000) — её выбирает gfx_dblbuf_back(). Вторая плоскость
; того же буфера (веса 2/8) рельефом не пишется и обязана быть нулевой,
; иначе логический цвет 1 перестанет быть единичным битом маски.
;
; ЦЕНА И ЧАНКИНГ. За кадр переносится 8 столбцов по 128 байт (1024 байта).
; Четыре кадра собирают полосу шириной 32 столбца. При последнем столбце
; дополнительно переносится scratch-колонка и генерируется следующая.
; Первый вызов после старта только генерирует scratch и делает исходный
; present без сдвига — это сохраняет фазу камеры оригинала. Весь вывод идёт
; в back-плоскость; front остаётся нетронутым до present.
;
; Только 8080: без LDIR/LDDR/JR/DJNZ/IX/IY и префиксов CB/DD/ED/FD.

        SECTION code_clib
        PUBLIC  _mission_start
        PUBLIC  _mission_frame
        PUBLIC  _mission_level

        EXTERN  _gfx_dblbuf_back
        EXTERN  _gfx_dblbuf_present

M_COLS  EQU     32              ; экрановых столбцов
M_CHUNK EQU     8               ; столбцов полосы за кадр (72 % кадра, см. TZ §9)
REC_LEN EQU     15              ; клеток в столбце кроме дорожной
WIN     EQU     16              ; ячеек окна указателей (15 нужны, маска 15)
TERM    EQU     0FFh            ; терминатор скрипта и списка частей

; ---------------------------------------------------------------------------
; void mission_start(void);
;
; Построить исходные 32 столбца в обеих плоскостях VRAM. Первый вызов
; mission_frame подготовит скрытый следующий столбец и выполнит исходный
; present без сдвига, сохраняя фазу камеры оригинального движка.
; ---------------------------------------------------------------------------
_mission_start:
        xra     a
        sta     m_level
        sta     m_col
        sta     m_lcol
        sta     m_draw
        sta     m_changed

        lxi     h, lv_sofs
        mov     a, m
        inx     h
        mov     h, m
        mov     l, a
        shld    m_scriptp
        call    m_prime

        ; Сначала построить исходные 32 столбца в плоскости A.
        mvi     a, 0E0h
        sta     m_pbase
        mvi     a, M_COLS
        sta     m_loop
ms_build_a:
        call    m_assemble
        lda     m_loop
        dcr     a
        sta     m_loop
        jnz     ms_build_a

        ; Скопировать готовую полосу A в плоскость B без сдвига.
        mvi     a, 0A0h
        sta     m_pbase
        mvi     a, 0E0h
        sta     m_fbase
        xra     a
        sta     m_draw
        mvi     a, M_COLS
        sta     m_loop
ms_copy_b:
        call    m_copy_initial
        lda     m_loop
        dcr     a
        sta     m_loop
        jnz     ms_copy_b
        ; m_draw=32: первый mission_frame генерирует первый scratch-столбец
        ; и делает исходный (не сдвигающий) present, как оригинал.
        xra     a
        sta     m_scroll
        ret

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
        call    _gfx_dblbuf_back            ; A=0: back A/front B; A=1: back B/front A
        ora     a
        jz      mf_back_a
        mvi     a, 0A0h
        sta     m_pbase
        mvi     a, 0E0h
        sta     m_fbase
        jmp     mf_copy_setup
mf_back_a:
        mvi     a, 0E0h
        sta     m_pbase
        mvi     a, 0A0h
        sta     m_fbase
mf_copy_setup:
        ; Первый вызов после старта: исходный экран уже готов в обеих
        ; плоскостях. Как оригинал, только подготовить новый столбец и
        ; выполнить первый present без сдвига картинки.
        lda     m_scroll
        ora     a
        jnz     mf_normal
        mvi     a, 1
        sta     m_destmode
        call    m_assemble
        xra     a
        sta     m_destmode
        sta     m_draw
        jmp     mf_present
mf_normal:
        mvi     a, M_CHUNK
        sta     m_left
mf_step:
        lda     m_draw
        cpi     M_COLS - 1
        jz      mf_new_column
        call    m_copy_shifted
        jmp     mf_step_done
mf_new_column:
        ; Перенести временный столбец в правый край, затем подготовить
        ; следующий в 128-байтном scratch-буфере RAM.
        call    m_copy_scratch_to_col
        mvi     a, 1
        sta     m_destmode
        call    m_assemble
        xra     a
        sta     m_destmode
mf_step_done:
        lda     m_left
        dcr     a
        sta     m_left
        jnz     mf_step

        lda     m_draw
        cpi     M_COLS
        jnz     mf_idle
        xra     a
        sta     m_draw
mf_present:
        lda     m_changed
        add     a
        adi     1
        push    psw
        call    _gfx_dblbuf_present
        mvi     a, 1
        sta     m_scroll
        lda     m_changed
        ora     a
        jz      mf_flags
        xra     a
        sta     m_changed
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
; Копирование одного столбца VRAM.
; m_copy_initial: A -> B, без сдвига (начальная синхронизация).
; m_copy_shifted: front[x+1] -> back[x], для прокрутки на одну колонку.
; В обоих случаях копируются 128 байт полезной части страницы.
; ---------------------------------------------------------------------------
m_copy_initial:
        lda     m_draw
        mov     e, a
        lda     m_fbase
        add     e
        mov     h, a
        lda     m_draw
        add     a
        add     a
        mov     l, a
        lda     m_pbase
        add     e
        mov     b, a
        lda     m_draw
        add     a
        add     a
        mov     c, a
        jmp     m_copy_bytes

m_copy_shifted:
        lda     m_draw
        mov     e, a                    ; E = x
        inr     a
        mov     d, a                    ; D = x+1
        lda     m_fbase
        add     d
        mov     h, a                    ; HL = front page x+1
        mov     a, d
        add     a
        add     a
        mov     l, a                    ; offset 4*(x+1)
        lda     m_pbase
        add     e
        mov     b, a                    ; BC = back page x
        mov     a, e
        add     a
        add     a
        mov     c, a                    ; offset 4*x
        jmp     m_copy_bytes

; Перенести 128-байтный scratch из RAM в последний столбец back
; (page 31, offset 124). m_draw остаётся 31: m_assemble завершит его до 32.
m_copy_scratch_to_col:
        lxi     h, m_scratch
        lda     m_pbase
        adi     M_COLS - 1
        mov     b, a
        mvi     c, 124
        mvi     d, 16
m_copy_scol_loop:
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        dcr     d
        jnz     m_copy_scol_loop
        ret

m_copy_bytes:
        mvi     d, 16
m_copy_loop:
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        mov     a, m
        stax    b
        inx     h
        inx     b
        dcr     d
        jnz     m_copy_loop
        lda     m_draw
        inr     a
        sta     m_draw
        ret

; ---------------------------------------------------------------------------
; m_assemble: собрать новый столбец мира непосредственно в back-плоскость
; VRAM. При m_destmode=1 назначение — 128-байтный временный столбец RAM.
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

        ; --- BC = адрес столбца back-плоскости:
        ;     (m_pbase + m_draw) * 256 + 4*m_draw
        lda     m_destmode
        ora     a
        jnz     ma_scratch
        lda     m_draw
        mov     c, a
        lda     m_pbase
        add     c
        mov     b, a
        lda     m_draw
        add     a
        add     a
        mov     c, a
        jmp     ma_dest_ready
ma_scratch:
        lxi     b, m_scratch
ma_dest_ready:

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
        lda     m_draw
        inr     a
        sta     m_draw
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

m_scriptp:  defs    2       ; курсор скрипта уровня
m_partp:    defs    2       ; курсор списка указателей текущей части
m_tail:     defb    0       ; 1 — очередь дочитывает хвост (lv_tail)
m_pair:     defs    2       ; указатель очереди, пока считается адрес окна
m_win:      defs    2*WIN   ; последние указатели очереди (смещения в lv_data)
m_pbase:    defb    0       ; старший байт back-плоскости (E0/A0)
m_fbase:    defb    0       ; старший байт front-плоскости (A0/E0)
m_destmode: defb    0       ; 1 — m_assemble пишет скрытый scratch
m_scroll:   defb    0       ; 0 — первый кадр без сдвига, 1 — прокрутка
m_level:    defb    0       ; текущий уровень
m_col:      defb    0       ; следующий столбец мира для сборки (с начала миссии)
m_lcol:     defb    0       ; столбец мира внутри уровня (сдвиг окна)
m_i:        defb    0       ; номер клетки в столбце
m_draw:     defb    0       ; столбцов полосы нарисовано в этом проходе
m_left:     defb    0       ; столбцов осталось скопировать в этом кадре
m_cnt:      defb    0       ; счётчик клеток
m_loop:     defb    0       ; счётчик начальной сборки/копирования
m_changed:  defb    0       ; уровень сменился, цвет не применён
m_scratch:  defs    128     ; один временный столбец (вместо кольца 8 КБ)

; Данные уровней — levels.inc открывает SECTION rodata_user сам, и после его
; включения по коду уже ничего быть не должно.
        INCLUDE "levels.inc"
