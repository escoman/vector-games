;
; nextframe.asm — ожидание следующего кадра (синхронизация с VBlank 50 Гц).
;
; gfx_next_frame(void):
;   1. Запоминает текущее значение frame_count.
;   2. В цикле: HLT (процессор спит до прерывания),
;      читает frame_count, сравнивает с сохранённым.
;   3. Если изменился — возврат.
;
; HLT останавливает процессор до следующего прерывания,
; не расходуя такты на пустой цикл ожидания.
;

        PUBLIC  _gfx_next_frame
        EXTERN  _frame_count

_gfx_next_frame:
        ld      hl, (_frame_count)      ; HL = текущий счётчик кадров
wait_loop:
        halt                             ; спать до кадрового прерывания
        ld      a, (_frame_count + 1)   ; старший байт frame_count
        cp      h
        jr      nz, done                ; изменился → выход
        ld      a, (_frame_count)       ; младший байт frame_count
        cp      l
        jr      z, wait_loop            ; не изменился → ждём дальше
done:
        ret
