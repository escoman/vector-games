; Данные: data_egg_speed_table
; Адрес: 0x1BFA
; Размер: 20 байт
; Описание: Кривая скорости/фаз яйца (FF-терминатор); читается func_collision_death.
data_egg_speed_table:
    DEFB 010h, 09h, 04h, 01h, 00h, 01h, 04h, 09h
    DEFB 010h, 019h, 024h, 031h, 040h, 051h, 064h, 079h
    DEFB 090h, 0A9h, 0C4h, 0FFh
