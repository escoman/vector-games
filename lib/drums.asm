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

AY_SEL  equ     0x15            ; AY: выбор регистра (нечётный порт)
AY_DAT  equ     0x14            ; AY: запись данных (чётный порт)

; Запись в регистр AY: A = номер регистра, E = значение.
ay_write:
        out     (AY_SEL), a
        ld      a, e
        out     (AY_DAT), a
        ret

; ------------------------------ состояние ------------------------------

drum_active:    defb    0       ; 0 = тишина, ничего не звучит
drum_prio:      defb    0       ; приоритет звучащего инструмента

; Рабочие параметры удара (копируются из таблицы при запуске):
drum_noise:     defb    0       ; период шума (R6)
drum_vol:       defb    0       ; текущая громкость (R10)
drum_dur:       defb    0       ; длительность в тиках
drum_decay:     defb    0       ; тиков на шаг спада громкости
drum_clap:      defb    0       ; 1 = режим вспышек clap

; Счётчики:
drum_pos:       defb    0       ; тиков с момента удара
drum_div:       defb    0       ; счётчик делителя спада

; Проигрыватель семплов .smp (music.c, mus2inc.py):
smp_ptr:        defw    0       ; адрес семпла (0 = семпл не звучит)
smp_left:       defb    0       ; осталось кадров семпла
smp_pos:        defb    0       ; смещение текущего кадра (пара байт)

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
        ld      a, 7            ; микшер: тоны A/B/C выкл, шум A/B выкл,
        ld      e, 0xDF         ; шум C вкл (бит 5 = 0)
        call    ay_write
        ld      a, 10           ; громкость канала C: тишина
        ld      e, 0
        call    ay_write
        ret

_drum_mute:
        xor     a
        ld      (drum_active), a        ; сбросить звучащий удар
        ld      (smp_ptr), a            ; оборвать и семпл .smp
        ld      (smp_ptr + 1), a
        ld      (smp_left), a
        ld      a, 10           ; громкость канала C: тишина
        ld      e, 0
        call    ay_write
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
        ld      a, 6            ; R6 = период шума
        ld      hl, drum_noise
        ld      e, (hl)
        call    ay_write
        ld      a, 10           ; R10 = начальная громкость
        ld      hl, drum_vol
        ld      e, (hl)
        call    ay_write
        ld      a, 1
        ld      (drum_active), a
        ret

; ------------------------------ drum_tick ------------------------------

_drum_tick:
        ld      a, (smp_ptr)    ; звучит семпл .smp — ведём его
        ld      hl, smp_ptr + 1
        or      (hl)
        jp      nz, tick_smp
        ld      a, (drum_active)
        or      a
        ret     z
        ld      hl, drum_pos
        inc     (hl)
        ld      a, (drum_dur)
        cp      (hl)            ; dur - pos
        jp      nc, drum_live   ; pos <= dur — удар ещё звучит
        xor     a               ; удар закончился: R10 = 0, тишина
        ld      (drum_active), a
        ld      e, a
        ld      a, 10
        call    ay_write
        ret
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
        ret     z               ; уже тишина, в R10 писать нечего
        dec     a
        ld      (hl), a
        ld      e, a
        ld      a, 10
        jp      ay_write        ; R10 = новая громкость

; Семпл .smp важнее табличной огибающей: пока звучат кадры семпла,
; каждый тик пишет его пару (R6, R10), табличный спад заморожен.
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
        ld      e, a
        push    hl
        ld      a, 6
        call    ay_write
        pop     hl
        inc     hl
        ld      a, (hl)         ; R10 кадра
        ld      e, a
        ld      a, 10
        call    ay_write
        ld      hl, smp_left
        dec     (hl)
        ret     nz
        xor     a               ; кадры кончились: тишина
        ld      (smp_ptr), a
        ld      (smp_ptr + 1), a
        ld      e, a
        ld      a, 10
        jp      ay_write

; Запустить семпл .smp (cdecl: указатель в стеке, SP+2).
; Формат: байт N — число кадров, затем N пар (R6, R10); 0 = ничего.
; Первый кадр выводится сразу — атака слышна в тот же тик.
_drum_sample_play:
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
        ld      e, a
        ld      a, 6
        call    ay_write
        inc     hl
        ld      a, (hl)         ; R10 первого кадра
        ld      e, a
        ld      a, 10
        jp      ay_write

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
        ret     z               ; громкость не изменилась
        ld      a, e
        ld      (drum_vol), a
        ld      a, 10
        jp      ay_write
