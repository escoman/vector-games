; Функция: func_beam_count
; Адрес: 0x1BA4
; Размер: ~14 байт
; Описание: Читает ТЕКУЩЕЕ значение счётчика 1 КР580ВИ53 (секундомера растра).
;           ЛATCH-команда (raster_w_latch1=40h: SC=cnt1, RL=00) замораживает
;           счётчик для чтения, затем два IN raster_cnt1_port (0Ah): сначала
;           младший байт, затем старший. count убывает от 0x7500 (начало кадра)
;           к 0, поэтому elapsed = 0x7500 - count = (строка луча)*96.
;           Возврат: DE = count (D=верх, E=низ). Трогает только A/D/E. На время
;           latch+чтений ставит DI (атомарно к перезагрузке в ISR), восстанавливает EI.

func_beam_count:
    DI                          ; атомарная последовательность latch->lo->hi
    MVI A, raster_w_latch1      ; 40h: latch cnt1
    OUT raster_ctrl_port        ; 08h
    IN raster_cnt1_port         ; 0Ah -> младший
    MOV E, A
    IN raster_cnt1_port         ; 0Ah -> старший
    MOV D, A
    EI
    RET
