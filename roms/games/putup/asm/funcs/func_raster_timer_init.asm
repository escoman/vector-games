; Функция: func_raster_timer_init
; Адрес: 0x1B90
; Размер: ~20 байт
; Описание: Включает «секундомер растра» на старте уровня. Ставит var_raster_flag=1
;           (разрешает перезагрузку счётчика 1 в конце VBlank ISR) и сразу праймит
;           сам счётчик, чтобы первое же чтение func_beam_count было корректным
;           (не ждать следующего VBlank).
;
;           КР580ВИ53 (клон i8253): OUT raster_ctrl_port=08h с управляющим словом
;           raster_w_load1=70h (SC=cnt1, RL=load lo+hi, mode0), затем два OUT
;           raster_cnt1_port=0Ah: низ (00h), верх (75h) => загрузка 0x7500=29952
;           отсчётов (длина кадра). На уровне мелодии нет, SFX на ch2 (09h) — ch1
;           (0Ah) свободен и не конфликтует ни с чем.

func_raster_timer_init:
    MVI A, 01h                  ; активировать растр-секундомер (ISR будет грузить cnt1)
    STA var_raster_flag
    MVI A, raster_w_load1       ; 70h: cnt1, load lo+hi, mode0
    OUT raster_ctrl_port        ; 08h
    MVI A, raster_frame_lo      ; 00h
    OUT raster_cnt1_port        ; 0Ah (низ)
    MVI A, raster_frame_hi      ; 75h
    OUT raster_cnt1_port        ; 0Ah (верх) -> счётчик стартует с 0x7500
    RET
