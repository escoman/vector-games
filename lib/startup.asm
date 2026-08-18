;
; startup.asm — общий стартовый код ROM Вектора-06Ц (библиотека lib).
;
; ROM загружается по адресу 0x0100. Первый блок памяти 0x0000-0x00FF —
; ОЗУ, в нём размещаются векторы прерываний; здесь при старте
; прописывается переход на кадровый обработчик (0x0038).
;
; Кадровое прерывание 50 Гц ведёт счётчик кадров (frame_count) и
; вызывает функцию frame_handler, если она назначена. Обработчик
; задаётся из C: frame_handler = my_func; (0 = обработчика нет).
;

        EXTERN  _main
        PUBLIC  _frame_count
        PUBLIC  _frame_handler

        org     0x0100

start:
        di
        ld      sp, 0x8000              ; стек растёт вниз из-под видеопамяти
        ; --- векторы прерываний (блок 0x0000-0x00FF, ОЗУ) ---
        ld      a, 0xC3                 ; инструкция jp
        ld      (0x0038), a             ; вектор кадрового прерывания
        ld      hl, isr_frame
        ld      (0x0039), hl
        ei
        call    _main
exit:
        di                              ; по выходе из main — вечный стоп
exit_loop:
        halt
        jp      exit_loop

; ---------------------------------------------------------------
; Кадровое прерывание 50 Гц: счётчик кадров + вызов обработчика.
; Вызывается через вектор 0x0038. 8080 сам ничего не сохраняет —
; сохраняем все регистры.
; ---------------------------------------------------------------
isr_frame:
        push    af
        push    bc
        push    de
        push    hl

        ld      hl, (_frame_count)
        inc     hl
        ld      (_frame_count), hl

        ld      hl, (_frame_handler)
        ld      a, h
        or      l
        call    nz, call_hl             ; вызов обработчика
isr_done:
        pop     hl
        pop     de
        pop     bc
        pop     af
        ei
        ret

; Трамплин: call кладёт адрес возврата в ISR, jp (hl) передаёт
; управление обработчику; его ret вернётся сюда, в isr_done.
call_hl:
        jp      (hl)

_frame_count:
        defw    0
_frame_handler:
        defw    0
