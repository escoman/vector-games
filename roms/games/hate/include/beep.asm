; beep.asm — бипер заставки H.A.T.E. на TapeOut (PC0 ПИА1, порт 01h).
;
; Оригинал озвучен 1-битным бипером ZX (порт $FE). Здесь тот же бит и тот
; же приём: уровень PC0 пишется в BSR-регистр ПИА (порт 00h, D7=0): A=01h —
; SET PC0, A=00h — RESET (см. lib/snd/drums.asm, pc0_set). ВИ53 в озвучке
; не участвует (TZ §3.8).
;
; ЧТО ИГРАЕТ. Партитура (include/title_music.asm, генерируется
; tools/gen_title_music.py из лога AY-архива, SOUND_FIX.MD §2) — семь
; независимых голосов: A и B — узкоимпульсные генераторы мелодии, C — клик,
; N — вспышки шума, S1/S2/S3 — свипы «пиу». У каждого свой счётчик до
; следующего события и свой скрипт записей (3 байта: delay, n).
;
; ФОРМАТ ЗАПИСИ — ЗАДЕРЖКА ДО ИМПУЛЬСА:
;
;         defw    delay   ; единиц по 128 такта; 0 = терминатор скрипта
;         defb    n       ; A/B/C: сколько импульсов; N/S: 1 = пуск; 0 = пауза
;
; Счётчик заряжается delay записи, по его истечении — импульс и n--; когда n
; кончилось, следующая запись подхватывается ТУТ ЖЕ (fire_x), а не на
; следующем шаге: иначе каждый голос съезжал бы на период первой записи
; (SOUND_FIX.MD §4.2). n = 0 — пауза длиной delay: импульса нет, после неё
; подхват. delay = 0 — терминатор: указатель СВОЕГО голоса отматывается на
; начало скрипта, запись перечитывается. Каждый скрипт длится ровно
; LOOP_UNITS = 1310400 ед. (2800 кадров = 56.00 с), поэтому все семь голосов
; смыкаются на терминаторе на одном шаге — это и есть цикл, как в оригинале.
;
; n ЗАПИСЫВАЕТСЯ В СЧЁТЧИК ДО ПРОВЕРКИ delay. Проверка терминатора — ora d /
; ora e — портит A; если sta cnt_x стоит после неё, в счётчик попадает
; n | delay (для паузы 16 383 — 255) и голос выдаёт событие на каждом отрезке.
; Именно на этом свипы звучали каждые 0.7 с, а ударные — на каждой паузе
; (найдено по порту: 86 шагов = 49+18+19 тремя залпами каждые 35 кадров).
;
; ПРЕДЕЛ ЗАДЕРЖКИ — 16 383 ЕД. Счётчик каждой задержки 16-битный, а перед
; выжиданием он умножается на 4 (dad h ×2) — задержка сверх 16 383 даёт
; переполнение и играется короче. Именно на этом уезжали ударные (пропуск
; 120 кадров), клик (95 кадров) и группы свипов: генератор режет длинные
; паузы на цепочку записей по 16 383 ед. Подхват записи стоит PICKUP_B и
; компенсируется, так что сумма пауз равна исходной задержке до единицы.
;
; ПОЧЕМУ НЕ ЦЕПОЧКА ФРОНТОВ. Прежний экспорт был цепочкой (задержка,
; уровень) на каждый фронт PC0: 3 байта на фронт, 22138 фронтов — 65 КБ, и
; в ROM влезал только первый цикл (3.2 с). Здесь интервалы вычисляет сам
; плеер, поэтому весь цикл (56 с, семь голосов) занимает 7.2 КБ.
;
; ЕДИНИЦА ВРЕМЕНИ — 128 тактов (42.7 мкс), одна на все голоса: счётчики
; приходится сравнивать между собой, а пауза клика в 1.9 с в 16 бит по 32
; такта не влезает. Шаг счётчиков при этом 0.6 % от самого короткого
; периода (81 ед.) — это 10 центов, на слух неразличимо.
;
; ТАКТЫ ЗДЕСЬ — НЕ НОМИНАЛЬНЫЕ 8080. Контроллер видео придерживает
; процессор, поэтому команда занимает целое число 4-тактовых окон:
; 4->4, 5->8, 7->8, 10->12, 13->16, 16->20, 17->24 (v06c-emu, i8080.cpp,
; cpu_cycles -> v_cycles; проверено на эмуляторе по лучу: 1 такт =
; 4 v_cycle). Поэтому цикл задержки ниже (dcx d / mov a,e / ora d / jnz)
; = 8+8+4+12 = 32 такта, а не 24.
;
; ПЛАНИРОВЩИК. Шаг = «дождаться ближайшего события»: берётся минимум из
; семи счётчиков, выжидается ровно он, из всех счётчиков он вычитается;
; у кого получился ноль — выдаёт событие и заряжает счётчик следующей
; записью. Джиттера кадровой синхронизации оригинала (и его «пропущенных
; проходов») здесь нет: время считает таймер, а не кадр.
;
; НАКЛАДНЫЕ РАСХОДЫ КОМПЕНСИРУЮТСЯ. Выдача события занимает время, и без
; компенсации голоса разъехались бы: A (4482 импульса) и B (8123) — на
; полсекунды. Поэтому каждое событие добавляет свою цену в `spent`
; (импульс — MUS_FIRE_x, вспышка — MUS_BURST_B, свип — MUS_CHIRP_Bx,
; подхват записи — PICKUP_B), а следующая задержка укорачивается на неё.
; Цена шага (C_STEP) тоже вычтена и выровнена NOP до целого числа
; 32-тактовых бит: иначе остаток стал бы постоянным сдвигом темпа.
;
; ШУМ ТОЖЕ КОМПЕНСИРУЕТСЯ — как импульс, только крупнее. Вспышка
; занимает ~13 мс (MUS_BURST_B, считает генератор по рисунку шума) и
; замораживает все счётчики разом; без компенсации 65 вспышек утаскивали
; бы всю партитуру на полсекунды (клик уезжал на 9 мс после каждой —
; слышно как «плавающий» бит). Поэтому fire_n добавляет её цену в `spent`,
; и следующие шаги её отрабатывают, как обычный долг. Свипы — так же.
;
; ПРЕРЫВАНИЯ РАЗРЕШЕНЫ, ИХ ЦЕНА КОМПЕНСИРУЕТСЯ. Кадровый ISR (startup.asm)
; тратит ~250 тактов на обёртку; внутри цикла он растянул бы шаг на 0.4 %,
; поэтому он сам добавляет свою полную цену (ISR_CHARGE) в `spent`, как
; импульс. Время считает таймер, а не кадр, так что это только долг следующему
; шагу, а не сдвиг темпа.
;
; КЛАВИАТУРА ОПРАШИВАЕТСЯ В НАЧАЛЕ КАДРОВОГО ПЕРЕРЫВАНИЯ (beep_kbd_isr), а не
; в цикле планировщика. Прерывание приходит на строке 0, такт 174 — луч в
; гашении, и до защёлки скролла (строка 40, такт 150) остаётся ~30 600 тактов,
; а весь обработчик вместе с обёрткой стоит ~1750 (мерено по лучу,
; BEAM_TIMING.MD §4, §8). Прежний kbd_tick — одна
; строка матрицы за шаг — писал порт 03h в произвольный момент кадра; совпадение
; с защёлкой случалось примерно на одном кадре из ста, и картинка дёргалась.
; Заодно матрица читается ЦЕЛИКОМ (kbd_scan_now, вход без EI;HLT): восемь
; строк один раз за кадр дешевле, чем ~300 строк в секунду, а нажатие ловится
; за 20 мс вместо 8..30 мс.
;
; ПОРТЫ 03h/02h НА ВРЕМЯ ОПРОСА. Режим-set в ПИА (CW) обнуляет защёлки
; выходов, поэтому kbd_scan_now сам возвращает бордюр/режим (порт 02h) и
; регистр строки экрана (порт 03h); весь опрос укладывается в гашение, так что
; кадр про него не узнаёт.
;
; СОСТОЯНИЕ — сама собой, без прерываний: PC0 держит последний записанный
; уровень, между импульсами процессор только считает такты.
;
; КОНСТАНТЫ C_STEP/ISR_CHARGE/PICKUP_B ПОВТОРЕНЫ в tools/gen_title_music.py
; (FIRE_BASE и MUS_DUTY_x; BURST_STEP/CHIRP_STEP). Правишь цикл здесь —
; сверься по лучу (docs/BEAM_TIMING.MD §4, §8).
;

        SECTION code_clib

        PUBLIC  _beep_play_title

        EXTERN  mus_a, mus_b, mus_c
        EXTERN  mus_n, mus_s1, mus_s2, mus_s3
        EXTERN  mus_nz, mus_cz1, mus_cz2, mus_cz3
        EXTERN  MUS_DUTY_A, MUS_DUTY_B, MUS_DUTY_C
        EXTERN  MUS_FIRE_A, MUS_FIRE_B, MUS_FIRE_C
        EXTERN  MUS_BURST_B
        EXTERN  MUS_CHIRP_B1, MUS_CHIRP_B2, MUS_CHIRP_B3
        EXTERN  _kbd_scan_now
        EXTERN  _kbd_rows
        EXTERN  _frame_handler

PIA_CW  equ     0x00            ; ПИА1: CW (D7=1) / BSR (D7=0), общий порт PC0
                                ; порты 02h/03h (бордюр/скролл-строка) трогает
                                ; только kbd_scan_now — см. lib/kbd/kbdscan.asm

C_STEP  equ     49              ; цена шага без задержки и событий, биты по 32
                                ; такта (сумма всех команд шага ≈ 1568 такта:
                                ; опрос клавиатуры 32 + планировщик 636 +
                                ; вычитание 528 + проверки 320; NOP в pl_loop
                                ; дополняет до целых бит). Предварительная
                                ; оценка — перекаллибровать по лучу на полном
                                ; проходе (BEAM_TIMING.MD §4).

ISR_CHARGE equ  55              ; цена прерывания целиком, биты по 32 такта.
                                ; Мерено по лучу: от строки 0/такт 174 (запрос)
                                ; до isr_done = 6658 v-циклов = 1664 T, плюс
                                ; поп-эпилог обёртки ~84 T -> ~1750 T = 54.6 бит.

PICKUP_B equ    7               ; цена подхвата следующей записи, биты по 32
                                ; такта (чтение трёх байт + сохранение + spent
                                ; ≈ 224 такта). Подхватов ~2400 за цикл —
                                ; 0.13 с, без компенсации утаскивали бы сетку
                                ; ударных на 6 кадров к концу цикла.

; ---------------------------------------------------------------------------
; void beep_play_title(void)
;
; Блокирующий проигрыватель: играет партитуру заставки циклом (56.00 с,
; как в оригинале) до тех пор, пока не нажата ЛЮБАЯ клавиша — тогда
; возвращается в main, вход в меню. Отпускания не ждём: следующая
; остановка будет только у пунктов меню.
;
; ЛЮБАЯ КЛАВИША ОБРЫВАЕТ ПАРТИТУРУ СРАЗУ. Надпись «PRESS ANY KEY WHEN
; READY» видна с первого кадра, поэтому ждать финала цикла нельзя: зритель
; видит приглашение, жмёт — и решает, что игра зависла. Опрос делает
; кадровое прерывание (beep_kbd_isr), цикл планировщика только читает
; kbd_any.
; ---------------------------------------------------------------------------
_beep_play_title:
        di
        lxi     h, beep_kbd_isr     ; опрос матрицы — из начала INT
        shld    _frame_handler      ; (startup.asm: вызывает его после счётчика)
        xor     a
        sta     kbd_any             ; свежий опрос ещё не успел ничего сказать
        out     (PIA_CW), a         ; PC0 = 0 (BSR: сброс), динамик молчит
        call    mus_restart
        ei

; --- шаг планировщика ---------------------------------------------------
pl_loop:
        nop                         ; выравнивание шага до целых бит (C_STEP)
        lda     kbd_any             ; 16  результат опроса из кадрового INT
        ora     a                   ; 4
        jnz     pl_skip             ; 12  нажали — партитура на этом кончается
        call    sched_delay         ; 24  выждать ближайшее событие...
        ; --- ...и вычесть выжданное из всех счётчиков ---
        lhld    dmin                ; 20
        xchg                        ; 4   DE = dmin
        lxi     h, cd_a             ; 12
        mvi     b, 7                ; 8
cd_sub:
        mov     a,m                 ; 8   мл. байт
        sub     e                   ; 4
        mov     m,a                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8   ст. байт
        sbb     d                   ; 4
        mov     m,a                 ; 8
        inx     h                   ; 8
        dcr     b                   ; 8
        jnz     cd_sub              ; 12
        ; --- у кого ноль — тому событие ---
chk_a:
        lhld    cd_a                ; 20
        mov     a,h                 ; 8
        ora     l                   ; 4
        jz      fire_a              ; 12
chk_b:
        lhld    cd_b                ; 20
        mov     a,h                 ; 8
        ora     l                   ; 4
        jz      fire_b              ; 12
chk_c:
        lhld    cd_c                ; 20
        mov     a,h                 ; 8
        ora     l                   ; 4
        jz      fire_c              ; 12
chk_n:
        lhld    cd_n                ; 20
        mov     a,h                 ; 8
        ora     l                   ; 4
        jz      fire_n              ; 12
chk_s1:
        lhld    cd_s1               ; 20
        mov     a,h                 ; 8
        ora     l                   ; 4
        jz      fire_s1             ; 12
chk_s2:
        lhld    cd_s2               ; 20
        mov     a,h                 ; 8
        ora     l                   ; 4
        jz      fire_s2             ; 12
chk_s3:
        lhld    cd_s3               ; 20
        mov     a,h                 ; 8
        ora     l                   ; 4
        jz      fire_s3             ; 12
        jmp     pl_loop             ; 12

; Клавиша нажата на шаге партитуры — обрываем её на середине. Динамик в
; тишину; клавиатурный обработчик снимаем, дальше кадрами владеет main.
pl_skip:
        xor     a
        out     (PIA_CW), a         ; PC0 = 0 (BSR: сброс), динамик молчит

; Снять клавиатурный обработчик: без потребителя крутить опрос — значит
; подставлять записи в порт 02h сохранённым значением ПИА (scan читает PB
; до режима-set и пишет его обратно после; если main успел сменить
; бордюр/режим внутри этого окна, его запись потерялась бы).
beep_kbd_off:
        lxi     h, 0                ; SHLD — одна инструкция, прерывание
        shld    _frame_handler      ; между её байтами не влезает
        ei                          ; в main идём с разрешёнными прерываниями
        ret

; ---------------------------------------------------------------------------
; sched_delay — DE = 4*минимум(cd) - spent - C_STEP (биты по 32 такта),
; spent = 0, затем задержка. Выходит по ret из beat_delay — сразу в pl_loop.
; ---------------------------------------------------------------------------
sched_delay:
        lhld    cd_a                ; 20  текущий минимум — в DE
        mov     d,h                 ; 8
        mov     e,l                 ; 8
sd_b:
        lhld    cd_b                ; 20  кандидат — в HL
        mov     a,l                 ; 8
        sub     e                   ; 4
        mov     a,h                 ; 8
        sbb     d                   ; 4
        jnc     sd_c                ; 12  кандидат не меньше
        xchg                        ; 4   меньше — он и есть минимум
sd_c:
        lhld    cd_c                ; 20
        mov     a,l                 ; 8
        sub     e                   ; 4
        mov     a,h                 ; 8
        sbb     d                   ; 4
        jnc     sd_n                ; 12
        xchg                        ; 4
sd_n:
        lhld    cd_n                ; 20
        mov     a,l                 ; 8
        sub     e                   ; 4
        mov     a,h                 ; 8
        sbb     d                   ; 4
        jnc     sd_s1               ; 12
        xchg                        ; 4
sd_s1:
        lhld    cd_s1               ; 20
        mov     a,l                 ; 8
        sub     e                   ; 4
        mov     a,h                 ; 8
        sbb     d                   ; 4
        jnc     sd_s2               ; 12
        xchg                        ; 4
sd_s2:
        lhld    cd_s2               ; 20
        mov     a,l                 ; 8
        sub     e                   ; 4
        mov     a,h                 ; 8
        sbb     d                   ; 4
        jnc     sd_s3               ; 12
        xchg                        ; 4
sd_s3:
        lhld    cd_s3               ; 20
        mov     a,l                 ; 8
        sub     e                   ; 4
        mov     a,h                 ; 8
        sbb     d                   ; 4
        jnc     sd_min              ; 12
        xchg                        ; 4
sd_min:
        mov     h,d                 ; 8
        mov     l,e                 ; 8
        shld    dmin                ; 20
        dad     h                   ; 12  x2
        dad     h                   ; 12  x4 = биты по 32 такта
        xchg                        ; 4   DE = 4*dmin
        lhld    spent               ; 20
        lxi     b, C_STEP           ; 12
        dad     b                   ; 12  HL = spent + цена шага
        mov     a,e                 ; 8
        sub     l                   ; 4
        mov     e,a                 ; 8
        mov     a,d                 ; 8
        sbb     h                   ; 4
        mov     d,a                 ; 8   DE = 4*dmin - spent - C_STEP
        jnc     sd_clear            ; 12
        ; Шаг короче своих же накладных расходов (два голоса почти совпали):
        ; ждать нечего — задержка 0, а недобранное остаётся долгом в spent и
        ; вычитается из следующих, длинных шагов. Без этого DE ушёл бы в
        ; минус и задержка (до 65535 бит = 0.7 с) растянула бы весь такт.
        mov     a,e                 ; 8
        cma                         ; 4
        mov     l,a                 ; 8
        mov     a,d                 ; 8
        cma                         ; 4
        mov     h,a                 ; 8
        inx     h                   ; 8   HL = -DE = долг
        shld    spent               ; 20
        lxi     d, 0                ; 12
        jmp     beat_delay          ; 12
sd_clear:
        lxi     h, 0                ; 12
        shld    spent               ; 20
        jmp     beat_delay          ; 12  ret вернёт прямо в pl_loop

; ---------------------------------------------------------------------------
; События голосов. У голосов A/B/C — узкий импульс: n-- после выдачи, и
; пока n > 0 счётчик заряжается тем же delay (per_x). Когда n == 0 —
; подхват следующей записи здесь же (иначе голос съедет на период первой
; записи, SOUND_FIX.MD §4.2): n = 0 — пауза (импульса нет), delay = 0 —
; терминатор, указатель своего голоса отматывается на начало скрипта.
; Цена импульса (биты) = скважность + FIRE_BASE, её считает генератор и
; кладёт в MUS_FIRE_x. Цена подхвата — PICKUP_B, в spent, как событие.
; ---------------------------------------------------------------------------
fire_a:
        lda     cnt_a               ; 16
        ora     a                   ; 4
        jz      fa_pick             ; 12  пауза (n = 0): импульса нет
        mvi     a, 1                ; 8
        out     (PIA_CW), a         ; 12  фронт: PC0 = 1
        lxi     d, MUS_DUTY_A       ; 12
        call    beat_delay          ; 24 + 32*скважность
        xra     a                   ; 4
        out     (PIA_CW), a         ; 12  спад: PC0 = 0
        lhld    spent               ; 20  цена импульса — в долг шагу
        lxi     d, MUS_FIRE_A       ; 12
        dad     d                   ; 12
        shld    spent               ; 20
        lda     cnt_a               ; 16
        dcr     a                   ; 8
        sta     cnt_a               ; 16
        jnz     fa_reload           ; 12  в записи ещё импульсы — тот же delay
fa_pick:
        lhld    ptr_a               ; 20
fa_read:
        mov     e,m                 ; 8   delay, мл.
        inx     h                   ; 8
        mov     d,m                 ; 8   delay, ст.
        inx     h                   ; 8
        mov     a,m                 ; 8   n (число импульсов; 0 — пауза)
        inx     h                   ; 8
        sta     cnt_a               ; 16  n — в счётчик ДО проверки: ora ниже
                                    ;      портит A, и cnt получал n|delay
        ora     d                   ; 4   delay = 0 — терминатор?
        ora     e                   ; 4
        jnz     fa_have             ; 12
        lxi     h, mus_a            ; 12  перемотка своего голоса на начало
        jmp     fa_read             ; 12
fa_have:
        shld    ptr_a               ; 20
        xchg                        ; 4
        shld    per_a               ; 20
        lhld    spent               ; 20  подхват тоже стоит времени
        lxi     d, PICKUP_B         ; 12
        dad     d                   ; 12
        shld    spent               ; 20
fa_reload:
        lhld    per_a               ; 20
        shld    cd_a                ; 20
        jmp     chk_b               ; 12

fire_b:
        lda     cnt_b               ; 16
        ora     a                   ; 4
        jz      fb_pick             ; 12
        mvi     a, 1                ; 8
        out     (PIA_CW), a         ; 12
        lxi     d, MUS_DUTY_B       ; 12
        call    beat_delay          ; 24 + 32*скважность
        xra     a                   ; 4
        out     (PIA_CW), a         ; 12
        lhld    spent               ; 20
        lxi     d, MUS_FIRE_B       ; 12
        dad     d                   ; 12
        shld    spent               ; 20
        lda     cnt_b               ; 16
        dcr     a                   ; 8
        sta     cnt_b               ; 16
        jnz     fb_reload           ; 12
fb_pick:
        lhld    ptr_b               ; 20
fb_read:
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        sta     cnt_b               ; 16  n — в счётчик до проверки delay
        ora     d                   ; 4
        ora     e                   ; 4
        jnz     fb_have             ; 12
        lxi     h, mus_b            ; 12
        jmp     fb_read             ; 12
fb_have:
        shld    ptr_b               ; 20
        xchg                        ; 4
        shld    per_b               ; 20
        lhld    spent               ; 20
        lxi     d, PICKUP_B         ; 12
        dad     d                   ; 12
        shld    spent               ; 20
fb_reload:
        lhld    per_b               ; 20
        shld    cd_b                ; 20
        jmp     chk_c               ; 12

fire_c:
        lda     cnt_c               ; 16
        ora     a                   ; 4
        jz      fc_pick             ; 12
        mvi     a, 1                ; 8
        out     (PIA_CW), a         ; 12
        lxi     d, MUS_DUTY_C       ; 12
        call    beat_delay          ; 24 + 32*скважность
        xra     a                   ; 4
        out     (PIA_CW), a         ; 12
        lhld    spent               ; 20
        lxi     d, MUS_FIRE_C       ; 12
        dad     d                   ; 12
        shld    spent               ; 20
        lda     cnt_c               ; 16
        dcr     a                   ; 8
        sta     cnt_c               ; 16
        jnz     fc_reload           ; 12
fc_pick:
        lhld    ptr_c               ; 20
fc_read:
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        sta     cnt_c               ; 16  n — в счётчик до проверки delay
        ora     d                   ; 4
        ora     e                   ; 4
        jnz     fc_have             ; 12
        lxi     h, mus_c            ; 12
        jmp     fc_read             ; 12
fc_have:
        shld    ptr_c               ; 20
        xchg                        ; 4
        shld    per_c               ; 20
        lhld    spent               ; 20
        lxi     d, PICKUP_B         ; 12
        dad     d                   ; 12
        shld    spent               ; 20
fc_reload:
        lhld    per_c               ; 20
        shld    cd_c                ; 20
        jmp     chk_n               ; 12

; --- слот шума: n = 1 — вспышка, n = 0 — тишина в этом слоте -------------
fire_n:
        lda     cnt_n               ; 16
        ora     a                   ; 4
        jz      fn_pick             ; 12  пауза: вспышки нет
        call    mus_burst           ; 24  вспышка шума
        lhld    spent               ; 20  её время тоже прошло для всех голосов
        lxi     d, MUS_BURST_B      ; 12
        dad     d                   ; 12
        shld    spent               ; 20
        lda     cnt_n               ; 16
        dcr     a                   ; 8
        sta     cnt_n               ; 16
        jnz     fn_reload           ; 12
fn_pick:
        lhld    ptr_n               ; 20
fn_read:
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        sta     cnt_n               ; 16  n — в счётчик до проверки delay
        ora     d                   ; 4
        ora     e                   ; 4
        jnz     fn_have             ; 12
        lxi     h, mus_n            ; 12
        jmp     fn_read             ; 12
fn_have:
        shld    ptr_n               ; 20
        xchg                        ; 4
        shld    per_n               ; 20
        lhld    spent               ; 20
        lxi     d, PICKUP_B         ; 12
        dad     d                   ; 12
        shld    spent               ; 20
fn_reload:
        lhld    per_n               ; 20
        shld    cd_n                ; 20
        jmp     chk_s1              ; 12

; --- свипы «пиу»: n = 1 — пуск, n = 0 — пауза ----------------------------
fire_s1:
        lda     cnt_s1              ; 16
        ora     a                   ; 4
        jz      f1_pick             ; 12
        lxi     h, mus_cz1          ; 12
        call    mus_chirp           ; 24  свип
        lhld    spent               ; 20  его время — в долг шагу
        lxi     d, MUS_CHIRP_B1     ; 12
        dad     d                   ; 12
        shld    spent               ; 20
        lda     cnt_s1              ; 16
        dcr     a                   ; 8
        sta     cnt_s1              ; 16
        jnz     f1_reload           ; 12
f1_pick:
        lhld    ptr_s1              ; 20
f1_read:
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        sta     cnt_s1              ; 16  n — в счётчик до проверки delay
        ora     d                   ; 4
        ora     e                   ; 4
        jnz     f1_have             ; 12
        lxi     h, mus_s1           ; 12
        jmp     f1_read             ; 12
f1_have:
        shld    ptr_s1              ; 20
        xchg                        ; 4
        shld    per_s1              ; 20
        lhld    spent               ; 20
        lxi     d, PICKUP_B         ; 12
        dad     d                   ; 12
        shld    spent               ; 20
f1_reload:
        lhld    per_s1              ; 20
        shld    cd_s1               ; 20
        jmp     chk_s2              ; 12

fire_s2:
        lda     cnt_s2              ; 16
        ora     a                   ; 4
        jz      f2_pick             ; 12
        lxi     h, mus_cz2          ; 12
        call    mus_chirp           ; 24
        lhld    spent               ; 20
        lxi     d, MUS_CHIRP_B2     ; 12
        dad     d                   ; 12
        shld    spent               ; 20
        lda     cnt_s2              ; 16
        dcr     a                   ; 8
        sta     cnt_s2              ; 16
        jnz     f2_reload           ; 12
f2_pick:
        lhld    ptr_s2              ; 20
f2_read:
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        sta     cnt_s2              ; 16  n — в счётчик до проверки delay
        ora     d                   ; 4
        ora     e                   ; 4
        jnz     f2_have             ; 12
        lxi     h, mus_s2           ; 12
        jmp     f2_read             ; 12
f2_have:
        shld    ptr_s2              ; 20
        xchg                        ; 4
        shld    per_s2              ; 20
        lhld    spent               ; 20
        lxi     d, PICKUP_B         ; 12
        dad     d                   ; 12
        shld    spent               ; 20
f2_reload:
        lhld    per_s2              ; 20
        shld    cd_s2               ; 20
        jmp     chk_s3              ; 12

fire_s3:
        lda     cnt_s3              ; 16
        ora     a                   ; 4
        jz      f3_pick             ; 12
        lxi     h, mus_cz3          ; 12
        call    mus_chirp           ; 24
        lhld    spent               ; 20
        lxi     d, MUS_CHIRP_B3     ; 12
        dad     d                   ; 12
        shld    spent               ; 20
        lda     cnt_s3              ; 16
        dcr     a                   ; 8
        sta     cnt_s3              ; 16
        jnz     f3_reload           ; 12
f3_pick:
        lhld    ptr_s3              ; 20
f3_read:
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        sta     cnt_s3              ; 16  n — в счётчик до проверки delay
        ora     d                   ; 4
        ora     e                   ; 4
        jnz     f3_have             ; 12
        lxi     h, mus_s3           ; 12
        jmp     f3_read             ; 12
f3_have:
        shld    ptr_s3              ; 20
        xchg                        ; 4
        shld    per_s3              ; 20
        lhld    spent               ; 20
        lxi     d, PICKUP_B         ; 12
        dad     d                   ; 12
        shld    spent               ; 20
f3_reload:
        lhld    per_s3              ; 20
        shld    cd_s3               ; 20
        jmp     pl_loop             ; 12

; ---------------------------------------------------------------------------
; mus_burst — рисунок шума: первый байт — число шагов, далее интервалы в
; тиках по 20 тактов. Уровень инвертируется CMA+ANI 1 (12 тактов):
; инструкции XRI у 8080 нет, а CMA в одиночку дал бы 0xFF/0xFE — в BSR это
; mode-set (D7=1), то есть сброс PC0 и регистра скролла.
; ---------------------------------------------------------------------------
mus_burst:
        lxi     h, mus_nz           ; 12
        mov     c,m                 ; 8   шагов
        inx     h                   ; 8
        xor     a                   ; 4   A = 0: первый CMA+ANI даст 1
bz_step:
        cma                         ; 4
        and     1                   ; 8
        out     (PIA_CW), a         ; 12
        mov     b,m                 ; 8
        inx     h                   ; 8
bz_wait:
        dcr     b                   ; 8
        jnz     bz_wait             ; 12
        dcr     c                   ; 8
        jnz     bz_step             ; 12
        cma                         ; 4   последний фронт вспышки
        and     1                   ; 8
        out     (PIA_CW), a         ; 12
        xor     a                   ; 4
        out     (PIA_CW), a         ; 12  в тишину (PC0 = 0)
        ret                         ; 12

; ---------------------------------------------------------------------------
; mus_chirp — свип «пиу»: вход HL = таблица, первый байт — число шагов,
; далее полупериоды битами по 32 такта (BEAT_T). Уровень PC0 держится
; в B и инвертируется CMA+ANI 1: в A его не удержать — beat_delay
; возвращает A = 0, и без B свип выходил плоской посылкой единиц
; (проверено по порту: все OUT были 1). D нулится один раз на входе:
; beat_delay оставляет DE = 0. В конце — в тишину. Цена пуска целиком
; (MUS_CHIRP_Bx, считает генератор по этому же коду) добавляется в spent
; вызывающим, как у шума.
; ---------------------------------------------------------------------------
mus_chirp:
        mov     c,m                 ; 8   шагов
        inx     h                   ; 8
        mvi     b, 0                ; 8   уровень: cma+ani даст 1
        mvi     d, 0                ; 8   beat_delay оставляет DE = 0 — нулим раз
ch_step:
        mov     a,b                 ; 8
        cma                         ; 4
        and     1                   ; 8
        out     (PIA_CW), a         ; 12
        mov     b,a                 ; 8   уровень на следующий шаг
        mov     e,m                 ; 8   полупериод в битах по 32
        inx     h                   ; 8
        call    beat_delay          ; 24 + 32*бит
        dcr     c                   ; 8
        jnz     ch_step             ; 12
        mov     a,b                 ; 8   последний фронт свипа
        cma                         ; 4
        and     1                   ; 8
        out     (PIA_CW), a         ; 12
        xor     a                   ; 4
        out     (PIA_CW), a         ; 12  в тишину (PC0 = 0)
        ret                         ; 12

; ---------------------------------------------------------------------------
; mus_restart — все голоса в начало партитуры, счётчики — по первым записям.
; Первая запись каждого скрипта — всегда с delay >= 1 (фаза цикла), поэтому
; терминатор первой не будет.
; ---------------------------------------------------------------------------
mus_restart:
        lxi     h, mus_a            ; 12
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        shld    ptr_a               ; 20
        sta     cnt_a               ; 16
        xchg                        ; 4
        shld    per_a               ; 20
        shld    cd_a                ; 20
        lxi     h, mus_b            ; 12
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        shld    ptr_b               ; 20
        sta     cnt_b               ; 16
        xchg                        ; 4
        shld    per_b               ; 20
        shld    cd_b                ; 20
        lxi     h, mus_c            ; 12
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        shld    ptr_c               ; 20
        sta     cnt_c               ; 16
        xchg                        ; 4
        shld    per_c               ; 20
        shld    cd_c                ; 20
        lxi     h, mus_n            ; 12
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        shld    ptr_n               ; 20
        sta     cnt_n               ; 16
        xchg                        ; 4
        shld    per_n               ; 20
        shld    cd_n                ; 20
        lxi     h, mus_s1           ; 12
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        shld    ptr_s1              ; 20
        sta     cnt_s1              ; 16
        xchg                        ; 4
        shld    per_s1              ; 20
        shld    cd_s1               ; 20
        lxi     h, mus_s2           ; 12
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        shld    ptr_s2              ; 20
        sta     cnt_s2              ; 16
        xchg                        ; 4
        shld    per_s2              ; 20
        shld    cd_s2               ; 20
        lxi     h, mus_s3           ; 12
        mov     e,m                 ; 8
        inx     h                   ; 8
        mov     d,m                 ; 8
        inx     h                   ; 8
        mov     a,m                 ; 8
        inx     h                   ; 8
        shld    ptr_s3              ; 20
        sta     cnt_s3              ; 16
        xchg                        ; 4
        shld    per_s3              ; 20
        shld    cd_s3               ; 20
        xra     a                   ; 4
        sta     kbd_any             ; 16  (на всякий случай — вдруг INT успел)
        lxi     h, 0                ; 12
        shld    spent               ; 20
        ret                         ; 12

; --- клавиатура на время партитуры: опрос в начале кадрового INT ---------
; beep_kbd_isr — frame_handler на время партитуры (назначается в
; _beep_play_title, его же снимает main). Вызывается из isr_frame
; (lib/sys/startup.asm), который приходит на строке 0, такт 174: луч в
; гашении, регистры основного цикла уже сохранены обёрткой, INTE сброшен —
; вложенного прерывания не будет, так что здесь можно и обычный стек, и
; работа с ПИА.
;
; Опрос — _kbd_scan_now: это kbd_scan_rows без EI;HLT (ждать нечего, мы и так
; в начале кадра, а halt внутри обработчика — это ждём сами себя). Там же
; восстанавливаются порты: режим-set 0x8A обнуляет защёлки выходов, поэтому в
; конце возвращаются бордюр/режим (02h) и регистр строки экрана (03h). Весь
; опрос ~850 тактов при 30 600 доступных до защёлки скролла (BEAM_TIMING.MD §8).
;
; Результат — OR восьми байт матрицы в kbd_any (1 = нажата; СС/УС сидят на
; порту C и сюда не входят). Основному циклу хватает прочитать один байт.
;
; Своя цена (ISR_CHARGE бит) добавляется в spent: прерывание съедает такты и у
; основного цикла, и у задержки, значит следующий шаг обязан быть короче.
; Запись в spent не атомарна: если INT придётся на lhld..shld основного цикла
; (окно ~50 тактов из ~60 000), один charge потеряется — на темп это не влияет.
; ---------------------------------------------------------------------------
beep_kbd_isr:
        call    _kbd_scan_now       ; 24 + ~850  вся матрица, порты возвращены
        lxi     h, _kbd_rows        ; 12
        mvi     b, 8                ; 8
        xra     a                   ; 4
isr_or:
        ora     m                   ; 8
        inx     h                   ; 8
        dcr     b                   ; 8
        jnz     isr_or              ; 12
        sta     kbd_any             ; 16  != 0 — клавиша нажата
        lhld    spent               ; 20  цена прерывания — в долг шагу
        lxi     d, ISR_CHARGE       ; 12
        dad     d                   ; 12
        shld    spent               ; 20
        ret                         ; 12

; ---------------------------------------------------------------------------
; Задержка ровно на DE*32 такта.
; Вход: DE — число единиц (>= 1). Цикл: 8 (DCX D) + 8 (mov a,e) + 4 (ora d)
; + 12 (jnz) = 32 такта на единицу. Проверка DE = 0 — чтобы укороченная
; компенсацией задержка не растянулась на 65536 итераций. A не сохраняется.
; ---------------------------------------------------------------------------
beat_delay:
        mov     a,d                 ; 8
        ora     e                   ; 4
        rz                          ; 8
bd_loop:
        dcx     d                   ; 8
        mov     a,e                 ; 8
        ora     d                   ; 4
        jnz     bd_loop             ; 12
        ret                         ; 12

        SECTION bss_user

; Счётчики до события — вплотную друг к другу: шаг планировщика
; вычитает dmin из всех семи одним циклом по 2 байта. Значение каждого —
; не больше 16 383 ед. (см. ПРЕДЕЛ ЗАДЕРЖКИ в шапке).
cd_a:           defs    2
cd_b:           defs    2
cd_c:           defs    2
cd_n:           defs    2
cd_s1:          defs    2
cd_s2:          defs    2
cd_s3:          defs    2
per_a:          defs    2       ; delay текущей записи голоса
per_b:          defs    2
per_c:          defs    2
per_n:          defs    2
per_s1:         defs    2
per_s2:         defs    2
per_s3:         defs    2
cnt_a:          defs    1       ; остаток событий в текущей записи (0 — пауза)
cnt_b:          defs    1
cnt_c:          defs    1
cnt_n:          defs    1
cnt_s1:         defs    1
cnt_s2:         defs    1
cnt_s3:         defs    1
ptr_a:          defs    2       ; указатель на текущую запись скрипта
ptr_b:          defs    2
ptr_c:          defs    2
ptr_n:          defs    2
ptr_s1:         defs    2
ptr_s2:         defs    2
ptr_s3:         defs    2
dmin:           defs    2       ; выжденное на текущем шаге
spent:          defs    2       ; уже потрачено после задержки, биты по 32
kbd_any:        defs    1       ; OR строк матрицы из кадрового опроса, 1 = нажата
