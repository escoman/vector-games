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
; Порты AY на Векторе-06Ц: выбор регистра 0x14, запись данных 0x15
; (подтверждено исходниками эмулятора, vio.h: ay.write(port & 1, v)).
; Микшер R7: бит 1 = источник выключен; канал C — бит 2 (тон),
; бит 5 (шум).
;
; Интерфейс (вызывается из C, z88dk cdecl, аргументов нет):
;   drum_init()  — настройка микшера и тишина;
;   drum_kick() drum_snare() drum_hat_c() drum_hat_o()
;   drum_tom()  drum_clap()  drum_rim()  — запустить удар;
;   drum_tick()  — вызывается из кадрового прерывания 50 Гц.
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

AY_SEL  equ     0x14            ; AY: выбор регистра
AY_DAT  equ     0x15            ; AY: запись данных

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

; Таблицы инструментов: prio, R6, vol0, dur, decay, clap
tab_kick:       defb    3, 31, 15, 25, 2, 0
tab_snare:      defb    2, 10, 15, 10, 1, 0
tab_hat_c:      defb    1,  4, 12,  4, 1, 0
tab_hat_o:      defb    1,  4, 12, 16, 1, 0
tab_tom:        defb    2, 18, 15, 14, 1, 0
tab_clap:       defb    2, 12, 12, 22, 1, 1
tab_rim:        defb    1,  2, 10,  2, 1, 0

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

; HL = запись таблицы инструмента. Новый удар звучит, если никто не
; звучит либо его приоритет не ниже приоритета звучащего.
drum_trig:
        ld      a, (drum_active)
        or      a
        jp      z, drum_go
        ld      a, (drum_prio)
        cp      (hl)            ; текущий приоритет - новый
        jp      c, drum_go      ; новый выше — перезапуск
        ret     nz              ; новый ниже — удар игнорируется
drum_go:
        xor     a               ; на время настройки drum_tick не мешает
        ld      (drum_active), a
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
