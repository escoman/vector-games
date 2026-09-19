;
; drums.asm — синтезатор ударных на AY-3-8910, только канал шума.
;
; Тоновые каналы синтезатора ударных не используются: шум живёт на
; канале C в режиме «noise C on». При этом Tone C в микшере НЕ
; глушится — мелодия на канале C продолжает звучать параллельно
; удару (аппаратный микшер AY складывает тон и шум на выходе C;
; общий R10 при этом разделяется — огибающая удара модулирует и
; тон, и шум). Библиотека:
;   - НЕ пишет в R0-R5 (периоды тонов), R8/R9 (громкости A/B),
;     R11-R13 (аппаратная огибающая);
;   - пишет в микшер R7 один раз (drum_init);
;   - управляет звуком через R6 (период шума) и R10 (громкость
;     канала C, программная огибающая в drum_tick).
;
; При маршруте Tape Out (drum_route == 0) шум выводится не через
; AY, а через Tape Out — 1-битный бипер PIA1 Port C bit 0 (порт 01h,
; BSR порт 00h): программный Galois LFSR 16 бит (маска 0xB400); каждый
; сдвиг за кадр переключает PC0 в бит шума, число сдвигов задаёт R6
; (tape_shifts[]), громкость R10 — duty-окно (0 = тишина, 15 = почти
; всегда). Табличные удары, семплы .smp и огибающие работают в обоих
; режимах; R6/R10 — параметры и для AY, и для маппинга сдвигов LFSR.
;
; Порты AY на Векторе-06Ц: эмулятор декодирует ay.write(port & 1, v),
; в ay.h addr == 1 — выбор регистра, addr == 0 — запись данных.
; Поэтому выбор регистра — НЕЧЁТНЫЙ порт 0x15, данные — 0x14.
; Микшер R7: бит 1 = источник выключен; канал C — бит 2 (тон),
; бит 5 (шум).
;
; Интерфейс (вызывается из C, z88dk cdecl, аргументов нет):
;   drum_init()  — настройка микшера и тишина;
;   drum_kick() drum_snare() drum_hat_c() drum_hat_o()
;   drum_tom()  drum_clap()  drum_rim()  — запустить удар;
;   drum_tick()  — вызывается из кадрового прерывания 50 Гц;
;   drum_mute()  — оборвать звучащий удар;
;   drum_sample_play(ptr) — запустить семпл .smp (формат в v06.h);
;
; Параметры инструментов:
;   R6    — период шума (больше значение — ниже шум);
;   vol0  — начальная громкость 0-15;
;   dur   — длительность в тиках 50 Гц;
;   decay — тиков на decrement громкости на 1 (программная огибающая);
;   prio  — приоритет: более высокий перезапускает звучащий, равный
;           перезапускается, более низкий игнорируется.
;
;       инструмент    R6  vol0  dur  decay  prio
;       kick          31   15    25    2     3
;       snare         10   15    10    1     2
;       hat closed     4   12     4    1     1
;       hat open       4   12    16    1     1
;       tom           18   15    14    1     2
;       clap          12   12    22    1     2
;       rim            2   10     2    1     1
;
; Clap — три вспышки шума: вкл(3) выкл(2) вкл(3) выкл(2), затем
; хвост с линейным спадом; громкость считается по номеру тика.
;
; Только 8080-инструкции; OUT с немедленным номером порта, поэтому
; кадровое прерывание не может подменить порт.
;

        SECTION code_clib
        PUBLIC  _drum_init
        PUBLIC  _drum_kick
        PUBLIC  _drum_snare
        PUBLIC  _drum_hat_c
        PUBLIC  _drum_hat_o
        PUBLIC  _drum_tom
        PUBLIC  _drum_clap
        PUBLIC  _drum_rim
        PUBLIC  _drum_tick
        PUBLIC  _drum_mute
        PUBLIC  _drum_sample_play
        PUBLIC  _drum_route_tape
        PUBLIC  _drum_route_ay
# ifndef MUSIC_AY_DRUMS_AY
        ; Гибкая генерация Tape Out (ТЗ §4-§8): разделение drum engine /
        ; output route / scheduler. Низкоуровневые примитивы LFSR и
        ; переключатели планировщика. AY-маршрут их не использует.
        PUBLIC  _drum_tape_step           ; один шаг LFSR + запись PC0
        PUBLIC  _drum_tape_generate       ; пакет из N шагов (batch)
        PUBLIC  _drum_tape_mode_frame     ; планировщик: из interrupt (умолч.)
        PUBLIC  _drum_tape_mode_manual    ; планировщик: только вручную
        PUBLIC  _drum_tape_mode_manual_env ; планировщик: вручную + огибающая ISR
        PUBLIC  _drum_tape_running         ; гейт: слышим ли кадр (manual_env)
        PUBLIC  _drum_tape_set_steps_per_tick
# endif
        PUBLIC  _g_ay_r7        ; зеркало R7: определение здесь, читает ay.c
        PUBLIC  _g_ay_r10_melody ; мелодийная громкость C: определение здесь, пишет ay.c
        PUBLIC  _drum_r10_current ; для ay.c: синхронизировать с прямой записью R10
        PUBLIC  _drum_r10_release ; для ay.c: снять пост-релиз на новой атаке

AY_SEL  equ     0x15            ; AY: выбор регистра (нечётный порт)
AY_DAT  equ     0x14            ; AY: запись данных (чётный порт)
PIA_CW  equ     0x00            ; PIA1: CW (бит 7 = 1) / BSR (бит 7 = 0)

; Мелодийная громкость канала C (R10), зеркало из ay.c: drum_live()/
; tick_smp()/drum_trig() берут max(drum_vol, g_ay_r10_melody), чтобы нота
; не «проваливалась» под огибающей удара; tick_end()/drum_mute() пишут
; её обратно вместо 0, чтобы не было «прыжка» после удара.
; Определение — ниже, в разделе состояния (рядом с g_ay_r7).

; Переключатель PC0 (Tape Out) через BSR: A = уровень 0/1.
; BSR (бит 7 = 0): номер бита в битах 3-1 (000 = PC0), бит 0 = set/reset.
; Поэтому уровень 1 -> 0x01 (SET PC0), уровень 0 -> 0x00 (RESET PC0):
; значение = A & 1, ровно как декодирует ядро/SoundLog (bit=(v>>1)&7).
# ifdef MUSIC_AY_DRUMS_AY
; AY-сборка: весь Tape Out не линкуется; tape_on остаётся заглушкой —
; на него ссылается общий tick_end (в AY-маршруте не выполняется).
tape_on:
        ret
# else
pc0_set:
        and     0x01            ; 0x01 = SET PC0, 0x00 = RESET PC0
        out     (PIA_CW), a
        ret

; Принудительная тишина Tape Out: PC0 = 0 (RESET бипера).
tape_on:
        xor     a
        jp      pc0_set         ; принудительный RESET PC0 (0x00 = BSR сброс)

; Кадровый тик Tape Out (FRAME-планировщик, вызов из drum_tick). Дешёвая
; генерация шума из interrupt: сначала duty-окно громкости (R10), затем
; пачка сдвигов LFSR — каждый переключает PC0. Число сдвигов за кадр:
; таблица tape_shifts[R6] (умолч., прежнее поведение ТЗ §12) или фиксированный
; порог tape_steps (drum_tape_set_steps_per_tick, ТЗ §6/§11). Сами сдвиги
; делает общий core tape_batch (его же зовёт drum_tape_generate из main loop),
; поэтому LFSR/семя/порядок сдвигов/выходной бит не меняются (ТЗ §10).
tape_tick:
        ; --- duty-окно громкости: активен ли этот кадр ---
        ld      a, (drum_vol)
        or      a
        jp      z, tape_mute    ; vol=0 — тишина
        ld      c, a            ; C = vol 1..15
        ld      a, (duty_phase)
        inc     a
        cp      16
        jp      c, tape_duty_ok
        xor     a               ; досчитали до 16 — фаза в начало
        ld      (duty_phase), a
        jp      tape_mute       ; за окном duty — тишина в этом кадре
tape_duty_ok:
        ld      (duty_phase), a
        cp      c               ; фаза < громкость?
        jp      nc, tape_mute
        ; --- кадр слышимый. manual_env: шаги делает main loop, не здесь ---
        ld      a, (tape_sched) ; режим 2: открыть гейт и выйти (PC0 не трогать)
        cp      2
        jp      nz, tc_framesel
        ld      a, 1
        ld      (tape_run), a
        ret
tc_framesel:
        ; --- число сдвигов за кадр: фиксированный порог или таблица R6 ---
        ld      a, (tape_steps) ; настройка drum_tape_set_steps_per_tick
        or      a
        jp      nz, tape_tick_n ; >0 — независимый frame-mode порог (ТЗ §11)
        ld      a, (drum_noise) ; 0 (умолч.) — прежний расчёт по tape_shifts[R6]
        and     0x1F
        ld      hl, tape_shifts
        ld      c, a
        ld      b, 0
        add     hl, bc
        ld      b, (hl)         ; B = сдвигов/переключений PC0 за кадр
        jp      tape_batch
tape_tick_n:
        ld      b, a            ; B = фиксированное число шагов за кадр
        jp      tape_batch
tape_mute:
        xor     a
        ld      (tape_run), a    ; кадр тишины: закрыть гейт manual_env
        jp      pc0_set          ; PC0 = 0

; ------------------------- ядро LFSR (drum engine) ----------------------
; Пакет из B (>0) сдвигов Galois 16 бит (маска 0xB400, taps 15/14/12/3);
; каждый сдвиг переключает PC0 в бит 0 состояния (он же обратная связь).
; Вход:  B = число сдвигов (1..255, nonzero); состояние читается из
;        lfsr_state и по окончании обратно. Выход: PC0 = бит последнего
;        сдвига; AF/BC/DE/HL — scratch (вне ISR вызывается при EI).
; Только 8080-инструкции (КР580ВМ80А: нет JR/DJNZ/SBC HL). OUT — прямая
; команда в теле цикла (без call pc0_set), чтобы batch был максимально
; дешёвым (ТЗ §14). Алгоритм/семя/порядок сдвигов прежние (ТЗ §10).
tape_batch:
        ld      hl, lfsr_state
        ld      e, (hl)
        inc     hl
        ld      d, (hl)         ; DE = состояние LFSR
        ld      a, e
        or      d
        jp      nz, tb_loop
        ld      de, 0xACE1      ; 0 = вечная тишина — перезагрузить семя
tb_loop:
        ; один сдвиг Galois вправо: out = feedback = бит 0 до сдвига
        ld      a, e
        and     0x01            ; CY=0, A = бит 0 (обратная связь = выход)
        ld      c, a            ; C = уровень PC0 этого сдвига (0/1)
        ld      a, d
        rra                     ; D >>= 1 (бит 7 = 0, CY был 0), CY = D bit0
        ld      d, a
        ld      a, e
        rra                     ; E >>= 1, бит 7 = D bit0, CY = E bit0 = out
        ld      e, a
        ld      a, c            ; восстановить out
        or      a
        jp      z, tb_pc0       ; без обратной связи
        ld      a, d
        xor     0xB4            ; DE ^= 0xB400 (младший байт маски = 0)
        ld      d, a
tb_pc0:
        ld      a, c            ; PC0 = выходной бит сдвига
        out     (PIA_CW), a     ; переключение бипера (BSR: A = 0/1)
        dec     b
        jp      nz, tb_loop
        ; --- состояние обратно: HL на &старший, старший в (HL), младший ниже
        ld      a, d
        ld      (hl), a
        dec     hl
        ld      a, e
        ld      (hl), a
        ret
# endif

; Запись в регистр AY: A = номер регистра, E = значение.
; БЕЗ di/ei: вызывается из кадрового ISR (drum_tick), где прерывания уже
; замаскированы (8080 сам сбрасывает IFF, isr_frame делает ei только перед
; ret). Лишний ei разрешил бы прерывания посреди ISR → повторный вход →
; рекурсия → переполнение стека. Каждый out (n),a атомарен сам по себе.
ay_write:
        out     (AY_SEL), a
        ld      a, e
        out     (AY_DAT), a
        ret

; ------------------------------ состояние ------------------------------

; Зеркало R7 — здесь (drums.asm единственный автор бит шума/тона C);
; music.c обновляет его через ay_set_r7() и объявляет extern.
; Двойная метка: на ссылки SECTION code_clib распространяются правила
g_ay_r7:
_g_ay_r7:
        defb    0xF8    ; тоны A/B/C вкл, шум ABC выкл

; Мелодийная громкость канала C (R10) — тоже здесь, drums.asm линкуется
; всегда (даже в VI53-only сборке, где ay.c выпадает); ay.c пишет её
; через extern unsigned char g_ay_r10_melody.
g_ay_r10_melody:
_g_ay_r10_melody:
        defb    0x00    ; 0 = мелодия на C молчит

; Маршрут физического вывода шума — внутреннее состояние модуля
; (ТЗ §13/§19: никакого глобального «режима звука»). 0 = Tape Out
; (PC0, LFSR), 1 = шумовой генератор AY (канал C). По умолчанию лента.
drum_route:     defb    0

; Планировщик генерации Tape Out (ТЗ §3/§6/§7) — отдельно от маршрута и
; от drum engine. Касается ТОЛЬКО Tape Out; AY-маршрут его не читает.
;   0 = FRAME  (умолч.) — drum_tick из interrupt ведёт генерацию (ТЗ §12);
;   1 = MANUAL — drum_tick не трогает PC0 и не ведёт огибающую ленты — шум
;       генерирует программа из main loop вызовами drum_tape_step()/generate();
;   2 = MANUAL + огибающая — drum_tick из interrupt ведёт огибающую громкости
;       и тайминг семплов (duty-окно), но НЕ переключает PC0: плотность
;       LFSR-шагов задаёт main loop через drum_tape_generate(), а гейт кадра
;       читается drum_tape_running(). Даёт «макс. частоту» шума без потери
;       огибающей (§7/§8).
# ifndef MUSIC_AY_DRUMS_AY
tape_sched:     defb    0
; Число сдвигов Tape Out за кадр в FRAME-режиме: 0 (умолч.) — из таблицы
; tape_shifts[R6] (полное прежнее поведение); >0 — фиксированный порог
; (настройка для игры: малое n ≈ минимальная нагрузка на CPU, ТЗ §6).
tape_steps:     defb    0
# endif

drum_active:    defb    0       ; 0 = тишина, ничего не звучит
drum_prio:      defb    0       ; приоритет звучащего инструмента
; Пост-релиз R10: после tick_end_ay() плавно ведём R10 к g_ay_r10_melody
; по ±1 за кадр — иначе слышен «щелчок» вверх на конце удара (было
; avg(drum,mel), стало mel за один кадр).
drum_r10_current:
_drum_r10_current:
        defb    0       ; R10, записанный модулем в прошлом кадре
drum_r10_release:
_drum_r10_release:
        defb    0       ; 1 = идёт плавный возврат

; Рабочие параметры удара (копируются из таблицы при запуске):
drum_noise:     defb    0       ; период шума (R6)
drum_vol:       defb    0       ; текущая громкость (R10)
drum_dur:       defb    0       ; длительность в тиках
drum_decay:     defb    0       ; тиков на шаг спада громкости
drum_clap:      defb    0       ; 1 = режим вспышек clap
drum_r7_save:   defb    0       ; сохранённый R7 (восстановить при конце)

; Программный шум для Tape Out (маршрут drum_route == 0):
; Galois LFSR 16 бит (маска 0xB400, taps 15/14/12/3); каждый сдвиг
; за кадр переключает PC0 в бит 0 состояния (он же обратная связь).
# ifndef MUSIC_AY_DRUMS_AY
lfsr_state:     defw    1       ; состояние сдвигового регистра (0 запрещён)
duty_phase:     defb    0       ; фаза счётчика громкости 0-15 (duty-окно)
tgen_rem:       defw    0       ; scratch: остаток count в drum_tape_generate
tape_run:       defb    0       ; manual_env: 1 = кадр внутри duty-окна (шум слышим)
# endif

; Счётчики:
drum_pos:       defb    0       ; тиков с момента удара
drum_div:       defb    0       ; счётчик делителя спада

; Проигрыватель семплов .smp (music.c, mus2inc.py):
smp_ptr:        defw    0       ; адрес семпла (0 = семпл не звучит)
smp_left:       defb    0       ; осталось кадров семпла
smp_pos:        defb    0       ; смещение текущего кадра (пара байт)
cur_r6:         defb    0       ; пара кадра семпла (R6, R10) до вывода
cur_r10:        defb    0

; число сдвигов/переключений PC0 за кадр 50 Гц по периоду R6 (0..31).
; Направление как у AY-шума: R6 больше → шум темнее → меньше сдвигов.
; Логарифмическая шкала 64..1 ≈ частота переключений 3200..50 Гц на PC0
; (в SoundLog Tape Out (PC0) = количество перепадов в секунду)
# ifndef MUSIC_AY_DRUMS_AY
tape_shifts:    defb    64, 64, 64, 64, 56, 47, 40, 34
                defb    28, 24, 20, 17, 14, 12, 10, 8
                defb    7, 6, 5, 4, 4, 3, 3, 2
                defb    2, 2, 1, 1, 1, 1, 1, 1
# endif

; Таблицы инструментов: prio, R6, vol0, dur, decay, clap
tab_kick:       defb    3, 31, 15,  7, 1, 0
tab_snare:      defb    2, 10, 15,  5, 1, 0
tab_hat_c:      defb    1,  4, 12,  2, 1, 0
tab_hat_o:      defb    1,  4, 12,  6, 1, 0
tab_tom:        defb    2, 18, 15,  5, 1, 0
tab_clap:       defb    2, 12, 12, 22, 1, 1
tab_rim:        defb    1,  2, 10,  1, 1, 0

; ------------------------------ запуск ---------------------------------

_drum_init:
        xor     a
        ld      (drum_active), a
        ld      (smp_ptr), a    ; семпл не звучит
        ld      (smp_ptr + 1), a
        ld      (smp_left), a
        jp      _drum_mute      ; R10 = 0 + восстановление R7 (идемпотентно)

; Явный выбор физического выхода шума (без глобального «режима звука»,
; ТЗ §13/§19): drum_route — внутреннее состояние модуля ударных.
;   _drum_route_tape — Tape Out (PC0), LFSR-шум (вывод ВИ53-мелодии);
;   _drum_route_ay   — шумовой генератор AY, канал C (вывод AY-мелодии).
; Аргументов нет. Каждый вызов глушит звучащий удар на старом выходе,
; как прежний переключатель выхода шума.
_drum_route_tape:
        xor     a               ; 0 = Tape Out
        ld      (drum_route), a
        jp      _drum_mute      ; заглушить удар на старом выходе
_drum_route_ay:
        ld      a, 1            ; 1 = шум AY
        ld      (drum_route), a
        jp      _drum_mute

# ifndef MUSIC_AY_DRUMS_AY
; --------------------- гибкая генерация Tape Out ------------------------
; Разделение (ТЗ §3): drum engine (нижний tape_batch и примитивы) отдельно
; от маршрута вывода (drum_route) и отдельно от планировщика (tape_sched).
; AY-маршрут эти функции не использует (§13).

; Планировщик FRAME (умолч.): Tape Out ведётся из drum_tick (кадровый
; interrupt); прежняя табличная/семпловая огибающая сохранена (§12).
_drum_tape_mode_frame:
        xor     a
        ld      (tape_sched), a
        ret

; Планировщик MANUAL: drum_tick не трогает PC0 на ленточном маршруте —
; Tape Out меняется только явными drum_tape_step()/drum_tape_generate().
; Для музыкальных ROM, расходующих заметную долю CPU на плотный шум (§7/§8).
_drum_tape_mode_manual:
        ld      a, 1
        ld      (tape_sched), a
        ret

; Планировщик MANUAL + огибающая (ТЗ §7/§8, для музыкальных ROM): drum_tick
; из interrupt продолжает вести огибающую громкости/тайминг семплов и duty-
; окно, но НЕ переключает PC0 — плотность LFSR-шагов задаёт main loop
; вызовами drum_tape_generate(), а drum_tape_running() говорит, слышим ли
; этот кадр. Даёт «максимальную частоту» шума при сохранённой огибающей.
_drum_tape_mode_manual_env:
        ld      a, 2
        ld      (tape_sched), a
        ret

; Гейт текущего кадра в режиме manual_env: 1, если кадр внутри duty-
; окна громкости (шум слышим) — main loop крутит drum_tape_generate();
; 0 — тишина (PC0 уже 0 из прерывания). Только для чтения из main loop.
; ВАЖНО: sccz80 продвигает unsigned char до int и в условии if(running())
; тестирует ВЕСЬ HL (`ld a,h / or l`), а не только L. Поэтому обнуляем H:
; иначе старший байт остаётся мусором от предыдущих вызовов и гейт
; зависит от него (ложно «не играет»/«запустилось через пару секунд»). Возврат 0/1 в HL.
_drum_tape_running:
        ld      a, (tape_run)
        ld      l, a
        ld      h, 0            ; H = 0 — чистый 16-битный 0/1 (сброс мусора)
        ret

; Число шагов Tape Out за кадр в FRAME-режиме (ТЗ §6). Аргумент — 16-битное
; беззнаковое в стеке (SP+2 — младший байт), читается как drum_sample_play;
; 0 = авторежим по tape_shifts[R6]. Не горячий путь (раз при настройке).
_drum_tape_set_steps_per_tick:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)         ; младший байт аргумента (0..255)
        ld      (tape_steps), a
        ret

; Один шаг генератора Tape Out (базовая операция drum engine, ТЗ §4):
; один сдвиг Galois LFSR (маска 0xB400) + одна запись PC0. Проверок
; маршрута/громкости/огибающей НЕТ — максимально дёшево. Состояние — в
; lfsr_state (продолжает поток с tape_tick/drum_tape_generate). HL
; сохраняется (push/pop) — единственный регистр, который эта функция
; меняет и который имеет смысл беречь; BC/DE/AF — scratch по cdecl.
_drum_tape_step:
        push    hl
        ld      hl, lfsr_state
        ld      e, (hl)
        inc     hl
        ld      d, (hl)         ; DE = состояние LFSR
        ld      a, e
        or      d
        jp      nz, tstep_go
        ld      de, 0xACE1      ; 0 = вечная тишина — перезагрузить семя
tstep_go:
        ld      a, e
        and     0x01            ; CY=0, A = бит 0 = выход/обратная связь
        ld      c, a            ; C = уровень PC0 этого шага (0/1)
        ld      a, d
        rra                     ; D >>= 1 (бит 7 = 0), CY = D bit0
        ld      d, a
        ld      a, e
        rra                     ; E >>= 1, бит 7 = D bit0
        ld      e, a
        ld      a, c
        or      a
        jp      z, tstep_pc0    ; без обратной связи
        ld      a, d
        xor     0xB4            ; DE ^= 0xB400
        ld      d, a
tstep_pc0:
        ld      a, d            ; сохранить состояние в lfsr_state (HL=&hi)
        ld      (hl), a
        dec     hl
        ld      a, e
        ld      (hl), a
        ld      a, c            ; PC0 = выходной бит шага
        out     (PIA_CW), a     ; переключение бипера
        pop     hl
        ret

; Пакетная генерация Tape Out (ТЗ §5): count сдвигов LFSR, каждый
; переключает PC0. Основной API для музыкальных ROM (main loop). count —
; 16-битное беззнаковое в стеке (SP+2 lo, SP+3 hi). count не ограничен
; десятками — позволяет расходовать на звук заметную долю CPU (§8).
; Разбирается на пакеты по 255 шагов общим ядром tape_batch (тот же LFSR,
; поток состояния непрерывен между пакетами через lfsr_state).
_drum_tape_generate:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)         ; count lo
        inc     hl
        ld      h, (hl)         ; count hi
        ld      l, a            ; HL = count
        ld      a, h
        or      l
        ret     z               ; count = 0 — ничего
        ld      (tgen_rem), hl
tgen_loop:
        ld      hl, (tgen_rem)
        ld      a, h
        or      a
        jp      nz, tgen_big
        ld      b, l            ; остаток < 256 — последний пакет, затем выход
        call    tape_batch
        ret
tgen_big:
        ld      b, 255          ; пакет 255 шагов, остаток -= 255, повторить
        ld      de, 0xFF01      ; rem-255 через DAD (8080: нет 16-битного вычитания)
        add     hl, de
        ld      (tgen_rem), hl
        call    tape_batch
        jp      tgen_loop
# endif

_drum_mute:
        xor     a
        ld      (drum_active), a        ; сбросить звучащий удар
        ld      (drum_r10_release), a   ; отменить пост-релиз (mute — резкий)
        ld      (smp_ptr), a            ; оборвать и семпл .smp
        ld      (smp_ptr + 1), a
        ld      (smp_left), a
# ifndef MUSIC_AY_DRUMS_AY
        ld      (duty_phase), a         ; duty-фазу LFSR — в начало
        call    tape_on                 ; PC0 = 0 (безопасно и в AY-режиме:
                                        ; удары туда не идут, бипер молчит)
# endif
        call    drum_restore_r10        ; R10 = мелодийная громкость C
        ld      a, (drum_r7_save)
        or      a               ; 0 = удар не запускался, R7 не трогать
        call    nz, drum_restore_r7
        ret

; Восстановить R7 из drum_r7_save → g_ay_r7 → AY.
; Вызывается при завершении удара (конец, семпл, mute).
drum_restore_r7:
        ld      a, (drum_r7_save)
        ld      (_g_ay_r7), a
        ld      e, a
        ld      a, 7
        jp      ay_write

; Вернуть R10 к «мелодийному» значению (g_ay_r10_melody из ay.c).
; Вызывается на drum_mute() и tick_end_ay(): раньше писался 0, из-за
; чего удерживаемая нота на C глохла до следующей атаки music_tick().
drum_restore_r10:
        ld      a, (_g_ay_r10_melody)
        ld      (drum_r10_current), a
        ld      e, a
        ld      a, 10
        jp      ay_write

; Записать R10 во время удара. Вход: A = drum_vol (0..15).
; Правила компромисса по общей громкости канала C (R10):
;   мелодия молчит (g_ay_r10_melody = 0x00)   → R10 = drum_vol  (полная
;                                                 огибающая удара, нота
;                                                 не мешает);
;   мелодия на аппаратной огибающей (= 0x1F)  → R10 = 0x1F       (бит 4
;                                                 включает генератор
;                                                 огибающей, AY игнорит
;                                                 нижние биты — мешать
;                                                 бессмысленно);
;   drum = 0, мелодия фиксирована             → R10 = melody_vol (хвост
;                                                 удара не глушит ноту);
;   оба фиксированы и > 0                     → R10 = (drum + melody) >> 1
;                                                 среднее: нота слышна
;                                                 громче половины своей
;                                                 громкости, удар
;                                                 затухает, но не до 0.
; BC/DE — scratch, HL не трогается. Пишет результат в drum_r10_current
; (для пост-релиза) и в AY R10.
drum_set_r10:
        ld      b, a                    ; B = drum_vol
        ld      a, (_g_ay_r10_melody)
        or      a
        jp      z, ds10_drum            ; мелодии нет → удар как есть
        cp      0x1F
        jp      z, ds10_write           ; мелодия на огибающей → 0x1F
        ld      c, a                    ; C = melody_vol (1..15)
        ld      a, b
        or      a
        jp      z, ds10_mel             ; удара нет → мелодия как есть
        add     a, c                    ; A = drum + melody (1..30)
        or      a                       ; CY = 0 (OR A always clears CY)
        rra                             ; A = (drum + melody) >> 1
        jp      ds10_write
ds10_mel:
        ld      a, c                    ; только мелодия (drum=0)
ds10_write:
        ld      (drum_r10_current), a
        ld      e, a
        ld      a, 10
        jp      ay_write
ds10_drum:
        ld      a, b                    ; только удар (мелодия молчит)
        jp      ds10_write

; Шаг пост-релиза R10: сдвигаем drum_r10_current на ±1 к цели
; g_ay_r10_melody. Когда дошли — снимаем флаг drum_r10_release.
; Вызывается из drum_tick, когда drum_active = 0 и семпл не играет.
drum_release_step:
        ld      a, (_g_ay_r10_melody)   ; цель
        ld      b, a                    ; B = target
        ld      a, (drum_r10_current)   ; A = current
        cp      b
        jp      z, drs_done
        jp      nc, drs_dec             ; current > target
        inc     a                       ; current < target
        jp      drs_write
drs_dec:
        dec     a
drs_write:
        ld      (drum_r10_current), a
        ld      e, a
        ld      a, 10
        jp      ay_write
drs_done:
        xor     a
        ld      (drum_r10_release), a
        ret

_drum_kick:
        ld      hl, tab_kick
        jp      drum_trig
_drum_snare:
        ld      hl, tab_snare
        jp      drum_trig
_drum_hat_c:
        ld      hl, tab_hat_c
        jp      drum_trig
_drum_hat_o:
        ld      hl, tab_hat_o
        jp      drum_trig
_drum_tom:
        ld      hl, tab_tom
        jp      drum_trig
_drum_clap:
        ld      hl, tab_clap
        jp      drum_trig
_drum_rim:
        ld      hl, tab_rim
        ; jp drum_trig: следующая инструкция и есть drum_trig

; HL = запись таблицы инструмента. Новый удар ВСЕГДА перезапускает
; звучащий (sound_step_t.noise — моментальное событие, каждый триггер
; обязан дать слышимую атаку); приоритет сохраняется лишь как
; информационное поле.
drum_trig:
drum_go:
        xor     a               ; на время настройки drum_tick не мешает
        ld      (drum_active), a
        ld      (smp_ptr), a    ; табличный удар обрывает семпл .smp
        ld      (smp_ptr + 1), a
        ld      (smp_left), a
        ld      a, (hl)
        ld      (drum_prio), a
        inc     hl
        ld      de, drum_noise  ; копия 5 байт параметров:
        ld      b, 5            ; R6, vol0, dur, decay, clap
drum_cp:
        ld      a, (hl)
        ld      (de), a
        inc     hl
        inc     de
        dec     b
        jp      nz, drum_cp
        xor     a
        ld      (drum_pos), a
        ld      (drum_div), a
        ld      a, (drum_route)
        or      a
        jp      z, trig_tape
        ; ---- AY (drum_route == 1): R6 = период шума ----
        ld      a, 6
        ld      hl, drum_noise
        ld      e, (hl)
        call    ay_write
        ; R10 = начальная громкость (max с мелодией на канале C)
        ld      hl, drum_vol
        ld      a, (hl)
        call    drum_set_r10
        ; Включить Noise C, Tone C НЕ трогать (канал C — общий):
        ; мелодия продолжает звучать параллельно удару, R10 — общая
        ; громкость, её ведёт огибающая удара.
        ld      a, (_g_ay_r7)   ; текущий R7 из music.c
        ld      (drum_r7_save), a  ; сохранить для восстановления
        and     0xDF            ; бит 5 (Noise C) = 0 → включён
        ld      e, a
        ld      a, 7
        call    ay_write
        ld      a, 1
        ld      (drum_active), a
        ret

; ---- Tape Out (drum_route == 0): LFSR-шум на PC0, AY не трогаем ----
; pos/div уже обнулены выше — остаётся включить удар
# ifdef MUSIC_AY_DRUMS_AY
trig_tape:
        ret
# else
trig_tape:
        ld      a, 0xFF         ; ненулевое семя (0 = вечная тишина);
        ld      (lfsr_state), a ; по байтам: 16-битные IMM-записи HL
        ld      (lfsr_state + 1), a ; в sccz80 потенциально косвенные
        xor     a
        ld      (duty_phase), a
        call    tape_on         ; PC0 = 0 на время настройки
        ld      a, 1
        ld      (drum_active), a
        ret
# endif

; ------------------------------ drum_tick ------------------------------

_drum_tick:
        ld      a, (drum_route)         ; маршрут шума: AY или Tape Out (PC0)
        or      a
        jp      z, tick_tape_sched
        ld      a, (smp_ptr)    ; звучит семпл .smp — ведём его
        ld      hl, smp_ptr + 1
        or      (hl)
        jp      nz, tick_smp
tick_ay:
        ld      a, (drum_active)
        or      a
        jp      z, tick_ay_release
        ld      hl, drum_pos
        inc     (hl)
        ld      a, (drum_dur)
        cp      (hl)            ; dur - pos
        jp      nc, drum_live   ; pos <= dur — удар ещё звучит
        jp      tick_end        ; удар закончился: тишина

; Удара нет и семпл не играет: если взведён пост-релиз R10 — ведём
; плавный возврат к мелодийной громкости (по ±1 за кадр).
tick_ay_release:
        ld      a, (drum_r10_release)
        or      a
        ret     z
        jp      drum_release_step

; ---- Tape Out: LFSR-шум на PC0, AY не трогаем ----
; Планировщик (ТЗ §6/§7): в MANUAL-режиме drum_tick не трогает PC0 — ленту
; ведёт main loop вызовами drum_tape_step()/drum_tape_generate(). В FRAME
; (умолч.) — прежнее кадровой генерации из interrupt (§12).
# ifdef MUSIC_AY_DRUMS_AY
tick_tape_sched:
        ret
# else
tick_tape_sched:
        ld      a, (tape_sched)
        or      a
        jp      z, tick_tape       ; FRAME: прежнее поведение (§12)
        cp      1
        ret     z                  ; MANUAL: PC0 и огибающая на руках у программы
        ; mode 2 (manual_env): ведём огибающую/тайминг, но PC0 НЕ трогаем —
        ; main loop сделает шаги, пока выставлен гейт tape_run этого кадра.
        xor     a
        ld      (tape_run), a      ; закрыть гейт; tape_tick откроет, если слышно
        jp      tick_tape
tick_tape:
        ld      a, (smp_ptr)    ; семпл важнее табличной огибающей
        ld      hl, smp_ptr + 1
        or      (hl)
        jp      nz, tick_smp
        ld      a, (drum_active)
        or      a
        jp      z, tape_idle
        ld      hl, drum_pos
        inc     (hl)
        ld      a, (drum_dur)
        cp      (hl)
        jp      nc, tape_live
        jp      tick_end        ; конец удара: общий хвост (выберет PC0 reset)
tape_live:
        ld      a, (drum_clap)  ; clap в ленточном режиме меняется так же,
        or      a               ; как обычный: вспышки дают drum_vol, а он
        jp      nz, drum_live   ; уходит в ноль → пауза в звуке
tape_shifts_run:
        call    tape_tick       ; сдвиги LFSR + одно переключение PC0
        ret
tape_idle:
        xor     a
        jp      pc0_set         ; удара нет — удерживать PC0 в тишине
# endif

; Общий конец события: тишина на активном выходе + восстановление R7
; (в ленточном режиме drum_r7_save = 0 → R7 не трогаем).
tick_end:
        xor     a               ; удар закончился: тишина
        ld      (drum_active), a
        ld      a, (drum_route)
        or      a
        jp      nz, tick_end_ay
        call    tape_on         ; PC0 = 0
        ret
tick_end_ay:
        ; Не пишем R10 сразу: запускаем плавный возврат к мелодии
        ; (drum_release_step делает ±1 за кадр из drum_tick).
        ld      a, 1
        ld      (drum_r10_release), a
        jp      drum_restore_r7

drum_live:
        ld      a, (drum_clap)
        or      a
        jp      nz, tick_clap
        ; обычный инструмент: спад громкости на 1 каждые decay тиков
        ld      hl, drum_div
        inc     (hl)
        ld      a, (hl)
        ld      hl, drum_decay
        cp      (hl)
        ret     c               ; шаг спада ещё не подошёл
        xor     a
        ld      (drum_div), a
        ld      hl, drum_vol
        ld      a, (hl)
        or      a
        jp      z, tape_vol_off ; уже тишина: R10 не пишем, PC0 держать в 0
        dec     a
        ld      (hl), a
        ld      e, a                    ; E = новая громкость (для tape_vol_off)
        ld      a, (drum_route)
        or      a
        jp      z, tape_vol_off         ; ленточный спад: R10 не пишем
        ld      a, e                    ; AY: R10 = max(удар, мелодия)
        jp      drum_set_r10

; Лента: громкость (duty-окно) обновлена, вывод сделает tape_tick
; на следующем тике — в прерывании достаточно одного адреса порта.
# ifdef MUSIC_AY_DRUMS_AY
tape_vol_off:
        ret
# else
tape_vol_off:
        or      e
        jp      nz, tape_vol_keep
        jp      tape_on                 ; спала до нуля — PC0 в тишину
tape_vol_keep:
        ret
# endif

; Семпл .smp важнее табличной огибающей: пока звучат кадры семпла,
; каждый тик берётся его пара (R6, R10) — в AY они пишутся в регистры,
; в ленточном режиме R6 задаёт число сдвигов LFSR, R10 — duty-окно;
; табличный спад заморожен.
;
; Ритм ленты: шумевое событие — не чаще одного переключения PC0 за тик
; (выход LFSR обновляется раз на тик). Максимальная частота переключений
; ~1600 Гц при 50 Гц тиках; AY-режим этого ограничения не имеет.
tick_smp:
        ld      hl, smp_pos     ; смещение кадра: пара байт
        ld      e, (hl)
        inc     (hl)
        inc     (hl)
        ld      d, 0
        ld      hl, smp_ptr
        ld      a, (hl)
        inc     hl
        ld      h, (hl)
        ld      l, a
        inc     hl              ; пропустить байт-счётчик кадров
        add     hl, de
        ld      a, (hl)         ; R6 кадра
        and     0x1F
        ld      (cur_r6), a
        inc     hl
        ld      a, (hl)         ; R10 кадра
        and     0x0F
        ld      (cur_r10), a
        ld      a, (drum_route)
        or      a
        jp      z, smp_tape
        ; ---- AY: R6 и R10 кадра ----
        ld      a, 6
        ld      hl, cur_r6
        ld      e, (hl)
        call    ay_write
        ld      hl, cur_r10
        ld      a, (hl)
        call    drum_set_r10
        jp      smp_advance
# ifdef MUSIC_AY_DRUMS_AY
smp_tape:
        ret
# else
smp_tape:
        ; ---- Tape Out: параметры кадра в drum_noise/drum_vol и тик LFSR ----
        ld      hl, cur_r6
        ld      de, drum_noise
        ld      a, (hl)
        ld      (de), a
        inc     hl
        inc     de
        ld      a, (hl)
        ld      (de), a
        call    tape_tick
# endif
smp_advance:
        ld      hl, smp_left
        dec     (hl)
        ret     nz
        xor     a               ; кадры кончились: тишина
        ld      (smp_ptr), a
        ld      (smp_ptr + 1), a
        jp      tick_end

; Запустить семпл .smp (cdecl: указатель в стеке, SP+2).
; Формат: байт N — число кадров, затем N пар (R6, R10); 0 = ничего.
; Первый кадр выводится сразу — атака слышна в тот же тик.
_drum_sample_play:
        ld      a, (drum_route)
        or      a
        jp      nz, smp_play_ay
        ; Лента: аргумент читается из стека в обеих ветках отдельно
        jp      smp_play_tape
smp_play_ay:
        ld      hl, 2
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        ld      a, d
        or      e
        ret     z               ; нулевой указатель — тишина
        ex      de, hl
        ld      a, (hl)         ; N — число кадров
        or      a
        ret     z
        xor     a               ; семпл вытесняет табличный удар
        ld      (drum_active), a
        ld      (smp_pos), a
        ld      a, (hl)
        ld      (smp_left), a
        ld      (smp_ptr), hl
        inc     hl
        ld      a, (hl)         ; R6 первого кадра
        and     0x1F
        ld      e, a
        ld      a, 6
        call    ay_write
        inc     hl
        ld      a, (hl)         ; R10 первого кадра
        and     0x0F
        call    drum_set_r10
        ; Включить Noise C, Tone C НЕ трогать (канал C — общий) так же,
        ; как табличный удар: сохранить базовый R7 для восстановления
        ; в tick_end и включить шум в микшере на время семпла, оставив
        ; для мелодии открытым тон канала C.
        ld      a, (_g_ay_r7)
        ld      (drum_r7_save), a
        and     0xDF            ; бит 5 (Noise C) = 0 → включён
        ld      e, a
        ld      a, 7
        call    ay_write
        ret

; Ленточный вариант: HL = &arg (SP+2), DE = адрес семпла.
# ifdef MUSIC_AY_DRUMS_AY
smp_play_tape:
        ret
# else
smp_play_tape:
        ld      hl, 2
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        ld      a, d
        or      e
        jp      z, tape_on      ; нулевой указатель — PC0 в тишину
        ex      de, hl
        ld      a, (hl)         ; N — число кадров
        or      a
        jp      z, tape_on
        xor     a               ; семпл вытесняет табличный удар
        ld      (drum_active), a
        ld      (smp_pos), a
        ld      (duty_phase), a
        ld      a, 0xFF         ; ненулевое семя LFSR (HL занят семплом:
        ld      (lfsr_state), a ; ld hl,imm в sccz80 может быть косвенным)
        ld      (lfsr_state + 1), a
        ld      a, (hl)         ; N — байт счётчика кадров
        ld      (smp_left), a
        ld      (smp_ptr), hl
        inc     hl
        ld      a, (hl)         ; R6 первого кадра
        and     0x1F
        ld      (drum_noise), a
        inc     hl
        ld      a, (hl)         ; R10 первого кадра
        and     0x0F
        ld      (drum_vol), a
        jp      tape_tick       ; первый тик сразу — атака в этом тике
# endif

tick_clap:
        ; вспышки: pos 1-3 вкл, 4-5 выкл, 6-8 вкл, 9-10 выкл,
        ; с pos 11 — хвост со спадом
        ld      a, (drum_pos)
        cp      4
        jp      c, clap_on
        cp      6
        jp      c, clap_off
        cp      9
        jp      c, clap_on
        cp      11
        jp      c, clap_off
        ld      hl, drum_pos    ; хвост: громкость = dur - pos
        ld      a, (drum_dur)
        sub     (hl)
        jp      set_vol
clap_on:
        ld      a, 12
        jp      set_vol
clap_off:
        xor     a
set_vol:
        ld      e, a
        ld      a, (drum_vol)
        cp      e
        jp      z, set_vol_same         ; громкость не изменилась
        ld      a, e
        ld      (drum_vol), a
        ld      a, (drum_route)
        or      a
        jp      z, tape_vol_off
        ld      a, e                    ; AY: R10 = max(вспышка, мелодия)
        jp      drum_set_r10
set_vol_same:
        ret
