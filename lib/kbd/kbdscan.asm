;
; kbdscan.asm — опрос матрицы клавиатуры Вектора-06Ц (библиотека lib).
;
; Последовательность проверена на эмуляторе PPSSPP (совпадает с
; castmus.rom и ISR z88dk): управляющее слово 0x8A в порт 0, маски
; строк в порт 3, столбцы читаются из порта 2. После опроса
; восстанавливается CW 0x88 и регистр строки экрана graph_scroll_row.
;
; Результат — 8 байт в _kbd_rows, бит 1 = клавиша нажата (инверсия
; порта). Декодирование в ASCII делает keyboard.c.
;
;   void kbd_scan_rows(void);
;   extern unsigned char kbd_rows[8];
;
; Только 8080-инструкции (никаких jr/djnz).
;

        SECTION code_clib
        EXTERN  _graph_scroll_row
        PUBLIC  kbd_scan_rows
        PUBLIC  _kbd_scan_rows
        PUBLIC  _kbd_rows
        PUBLIC  _kbd_shift_state
        PUBLIC  _kbd_port_c_raw

kbd_scan_rows:
_kbd_scan_rows:
        ei
        halt                    ; синхронизация с VBLANK: весь опрос
                                ; проходит в гасящем интервале, порт 0x03
                                ; (скролл) не дёргает экран
        in      a, (0x02)              ; сохранить PB (бордюр + режим)
        push    af
        ld      a, 0x8A                 ; порт B — ввод столбцов
        out     (0x00), a
        ld      hl, _kbd_rows
        ld      b, 0xFE                 ; маска строки (0 активен)
        ld      c, 8                    ; счётчик строк
        scf                             ; carry=1: rlca вносит 1 в бит 0
row_loop:
        ld      a, b
        out     (0x03), a               ; выбрать строку
        in      a, (0x02)               ; столбцы (0 = нажата)
        cpl                             ; приводим к 1 = нажата
        ld      (hl), a
        inc     hl
        ld      a, b
        rlca
        ld      b, a
        dec     c
        jp      nz, row_loop
        ld      a, 0x88                 ; вернуть обычное управляющее слово
        out     (0x00), a
        in      a, (0x01)         ; порт C (все биты — вход): СС = бит 5
        ld      (_kbd_port_c_raw), a ; сырое (active low: 0 = нажата)
        cpl                       ; инверсия: 1 = нажата
        and     0x20              ; маска бита 5 (Shift/СС)
        ld      (_kbd_shift_state), a
        pop     af
        out     (0x02), a               ; восстановить PB (бордюр + режим)
        ld      a, (_graph_scroll_row)
        out     (0x03), a               ; вернуть регистр строки экрана
        ret

_kbd_rows:
        defs    8
_kbd_shift_state:
        defs    1
_kbd_port_c_raw:
        defs    1
