;
; drums.asm — синтезатор ударных на AY-3-8910, только канал шума.
;
; Тоновые каналы не используются вовсе: ударные живут на канале C в
; режиме «tone C off, noise C on». Библиотека:
;   - НЕ пишет в R0-R5 (периоды тонов), R8/R9 (громкости A/B),
;     R11-R13 (аппаратная огибающая);
;   - пишет в микшер R7 один раз (drum_init);
;   - управляет звуком через R6 (период шума) и R10 (громкость
;     канала C, программная огибающая в drum_tick).
;
; В режиме MUSIC_MODE_VI53 (г_music_mode == 0) шум выводится не через
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
        PUBLIC  _drum_mode
        PUBLIC  _g_ay_r7        ; зеркало R7: определение здесь, читает music.c
        EXTERN  _g_music_mode   ; MUSIC_MODE_VI53 = 0 / MUSIC_MODE_AY = 1

AY_SEL  equ     0x15            ; AY: выбор регистра (нечётный порт)
AY_DAT  equ     0x14            ; AY: запись данных (чётный порт)
PIA_CW  equ     0x00            ; PIA1: CW (бит 7 = 1) / BSR (бит 7 = 0)

; Переключатель PC0 (Tape Out) через BSR: A = уровень 0/1.
; BSR (бит 7 = 0): номер бита в битах 3-1 (000 = PC0), бит 0 = set/reset.
; Поэтому уровень 1 -> 0x01 (SET PC0), уровень 0 -> 0x00 (RESET PC0):
; значение = A & 1, ровно как декодирует ядро/SoundLog (bit=(v>>1)&7).
pc0_set:
        and     0x01            ; 0x01 = SET PC0, 0x00 = RESET PC0
        out     (PIA_CW), a
        ret

; Звуковой тик Tape Out (режим VI53): программный Galois LFSR 16 бит,
; маска 0xB400 (taps 15/14/12/3, максимальная длина 65535). За тик
; 50 Гц делается tape_shifts[R6] сдвигов, и КАЖДЫЙ сдвиг переключает
; PC0 в выходной бит LFSR (бит 0 до сдвига) — только так бипер даёт
; шум: SoundLog считает перепады, а их максимум = сдвигов_за_тик * 50 Гц
; (1..64 → 50..3200 Гц). Направление как у AY: R6 больше → шума темнее
; → меньше сдвигов. Громкость R10 — окно duty (раз на кадр): вне окна
; и при vol=0 тик молчит (PC0 = 0), так столбик SoundLog следует
; огибающей. Вызов строго из drum_tick (кадровое прерывание).
tape_on:
        xor     a
        jp      pc0_set         ; принудительный RESET PC0 (0x00 = BSR сброс)
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
        ; --- число сдвигов по R6 ---
        ld      hl, drum_noise
        ld      a, (hl)         ; R6 0..31 — тот же параметр, что и для AY
        and     0x1F
        ld      hl, tape_shifts
        ld      c, a
        ld      b, 0
        add     hl, bc
        ld      b, (hl)         ; сдвигов/переключений PC0 за кадр
        ; --- DE = состояние LFSR, HL = &старший байт ---
        ld      hl, lfsr_state
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        ld      a, e
        or      d
        jp      nz, tape_run
        ld      de, 0xACE1      ; 0 = вечная тишина — перезагрузить семя
tape_run:
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
        jp      z, tape_pc0     ; без обратной связи
        ld      a, d
        xor     0xB4            ; DE ^= 0xB400 (младший байт маски = 0)
        ld      d, a
tape_pc0:
        ld      a, c            ; PC0 = выходной бит сдвига
        call    pc0_set         ; переключение бипера
        dec     b
        jp      nz, tape_run
        ; --- состояние обратно: HL на &старший, старший в (HL), младший ниже
        ld      a, d
        ld      (hl), a
        dec     hl
        ld      a, e
        ld      (hl), a
        ret
tape_mute:
        xor     a
        jp      pc0_set         ; кадр тишины: PC0 = 0

; Запись в регистр AY: A = номер регистра, E = значение.
; DI/EI защищает пару OUT от прерывания ISR (общий лач AY-регистра).
ay_write:
        di
        out     (AY_SEL), a
        ld      a, e
        out     (AY_DAT), a
        ei
        ret

; ------------------------------ состояние ------------------------------

; Зеркало R7 — здесь (drums.asm единственный автор бит шума/тона C);
; music.c обновляет его через ay_set_r7() и объявляет extern.
; Двойная метка: на ссылки SECTION code_clib распространяются правила
g_ay_r7:
_g_ay_r7:
        defb    0xF8    ; тоны A/B/C вкл, шум ABC выкл

drum_active:    defb    0       ; 0 = тишина, ничего не звучит
drum_prio:      defb    0       ; приоритет звучащего инструмента

; Рабочие параметры удара (копируются из таблицы при запуске):
drum_noise:     defb    0       ; период шума (R6)
drum_vol:       defb    0       ; текущая громкость (R10)
drum_dur:       defb    0       ; длительность в тиках
drum_decay:     defb    0       ; тиков на шаг спада громкости
drum_clap:      defb    0       ; 1 = режим вспышек clap
drum_r7_save:   defb    0       ; сохранённый R7 (восстановить при конце)

; Программный шум для Tape Out (MUSIC_MODE_VI53):
; Galois LFSR 16 бит (маска 0xB400, taps 15/14/12/3); каждый сдвиг
; за кадр переключает PC0 в бит 0 состояния (он же обратная связь).
lfsr_state:     defw    1       ; состояние сдвигового регистра (0 запрещён)
duty_phase:     defb    0       ; фаза счётчика громкости 0-15 (duty-окно)

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
tape_shifts:    defb    64, 64, 64, 64, 56, 47, 40, 34
                defb    28, 24, 20, 17, 14, 12, 10, 8
                defb    7, 6, 5, 4, 4, 3, 3, 2
                defb    2, 2, 1, 1, 1, 1, 1, 1

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

; Выбор выхода шума (cdecl: аргумент в стеке, SP+2):
; 0 (MUSIC_MODE_VI53) — Tape Out PC0, 1 (MUSIC_MODE_AY) — шум AY.
; Пишет g_music_mode — общий флаг с мелодией, поэтому music_mode()
; и drum_mode() взаимозаменяемы; ROM без music.c настраивает ударные
; только через drum_mode().
_drum_mode:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)
        and     0x01            ; A = новый режим (0/1)
        ld      hl, _g_music_mode
        cp      (hl)            ; режим не изменился — ничего не делаем
        ret     z
        ld      (hl), a         ; сохранить новый режим в байт флага
        jp      _drum_mute      ; заглушить удар на старом выходе

_drum_mute:
        xor     a
        ld      (drum_active), a        ; сбросить звучащий удар
        ld      (smp_ptr), a            ; оборвать и семпл .smp
        ld      (smp_ptr + 1), a
        ld      (smp_left), a
        ld      (duty_phase), a         ; duty-фазу LFSR — в начало
        call    tape_on                 ; PC0 = 0 (безопасно и в AY-режиме:
                                        ; удары туда не идут, бипер молчит)
        ld      a, 10           ; громкость канала C: тишина
        ld      e, 0
        call    ay_write
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
        ld      a, (_g_music_mode)
        or      a
        jp      z, trig_tape
        ; ---- AY (MUSIC_MODE_AY): R6 = период шума ----
        ld      a, 6
        ld      hl, drum_noise
        ld      e, (hl)
        call    ay_write
        ; R10 = начальная громкость
        ld      a, 10
        ld      hl, drum_vol
        ld      e, (hl)
        call    ay_write
        ; Включить Noise C, выключить Tone C (канал C — общий):
        ld      a, (_g_ay_r7)   ; текущий R7 из music.c
        ld      (drum_r7_save), a  ; сохранить для восстановления
        and     0xDF            ; бит 5 (Noise C) = 0 → включён
        or      0x04            ; бит 2 (Tone C) = 1 → выключён
        ld      e, a
        ld      a, 7
        call    ay_write
        ld      a, 1
        ld      (drum_active), a
        ret

; ---- Tape Out (MUSIC_MODE_VI53): LFSR-шум на PC0, AY не трогаем ----
; pos/div уже обнулены выше — остаётся включить удар
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

; ------------------------------ drum_tick ------------------------------

_drum_tick:
        ld      a, (_g_music_mode)      ; режим шума: AY или Tape Out (PC0)
        or      a
        jp      z, tick_tape
        ld      a, (smp_ptr)    ; звучит семпл .smp — ведём его
        ld      hl, smp_ptr + 1
        or      (hl)
        jp      nz, tick_smp
tick_ay:
        ld      a, (drum_active)
        or      a
        ret     z
        ld      hl, drum_pos
        inc     (hl)
        ld      a, (drum_dur)
        cp      (hl)            ; dur - pos
        jp      nc, drum_live   ; pos <= dur — удар ещё звучит
        jp      tick_end        ; удар закончился: тишина

; ---- Tape Out: LFSR-шум на PC0, AY не трогаем ----
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

; Общий конец события: тишина на активном выходе + восстановление R7
; (в ленточном режиме drum_r7_save = 0 → R7 не трогаем).
tick_end:
        xor     a               ; удар закончился: тишина
        ld      (drum_active), a
        ld      a, (_g_music_mode)
        or      a
        jp      nz, tick_end_ay
        call    tape_on         ; PC0 = 0
        ret
tick_end_ay:
        xor     a               ; R10 = 0 — тишина канала C
        ld      e, a
        ld      a, 10
        call    ay_write
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
        ld      e, a                    ; новая громкость
        ld      a, (_g_music_mode)
        or      a
        jp      z, tape_vol_off         ; ленточный спад: R10 не пишем
        ld      a, 10
        jp      ay_write        ; R10 = новая громкость

; Лента: громкость (duty-окно) обновлена, вывод сделает tape_tick
; на следующем тике — в прерывании достаточно одного адреса порта.
tape_vol_off:
        or      e
        jp      nz, tape_vol_keep
        jp      tape_on                 ; спала до нуля — PC0 в тишину
tape_vol_keep:
        ret

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
        ld      a, (_g_music_mode)
        or      a
        jp      z, smp_tape
        ; ---- AY: R6 и R10 кадра ----
        ld      a, 6
        ld      hl, cur_r6
        ld      e, (hl)
        call    ay_write
        ld      a, 10
        ld      hl, cur_r10
        ld      e, (hl)
        call    ay_write
        jp      smp_advance
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
        ld      a, (_g_music_mode)
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
        ld      e, a
        ld      a, 10
        call    ay_write
        ; Включить Noise C, выключить Tone C (канал C — общий) так же,
        ; как табличный удар: сохранить базовый R7 для восстановления
        ; в tick_end и включить шум в микшере на время семпла.
        ld      a, (_g_ay_r7)
        ld      (drum_r7_save), a
        and     0xDF            ; бит 5 (Noise C) = 0 → включён
        or      0x04            ; бит 2 (Tone C) = 1 → выключён
        ld      e, a
        ld      a, 7
        call    ay_write
        ret

; Ленточный вариант: HL = &arg (SP+2), DE = адрес семпла.
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
        ld      a, (_g_music_mode)
        or      a
        jp      z, tape_vol_off
        ld      a, 10
        jp      ay_write
set_vol_same:
        ret
